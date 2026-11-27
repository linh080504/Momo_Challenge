import base64
import io
import time
from functools import lru_cache
from urllib.parse import urlsplit

import httpx
from PIL import Image

from ..analyzer.providers.llm import QWEN_MODEL, query_qwen
from ..config import ROOT
from .article_capture import capture_article
from .website_report import PageMarkup


ARTICLE_URL = "https://www.kaspersky.com.vn/resource-center/preemptive-safety/scam-websites"
COVER_URL = ("https://content.kaspersky-labs.com/fm/press-releases/b9/b94bcf6a2da412c5747a39544716fba8/"
             "processed/ksy-17-how-to-report-a-website-q75.webp")
PUBLIC_ARTICLES = {ARTICLE_URL: {"publisher": "Kaspersky", "cover": COVER_URL}}
ARTICLE_ASSETS = {
    COVER_URL: "image",
    "https://cdn.kaspersky.com/siterenderer/_next/static/css/common.0a6a5ffbbfeed5702587ec0de3f8b139.css": "stylesheet",
    "https://www.kaspersky.com.vn/api/siterenderer/css/91fbddf93bd3429b16c6dc483e59b691-cdn.css": "stylesheet",
}
ARTICLE_PROMPT = (ROOT / "prompts" / "website_context_v1.md").read_text(encoding="utf-8")


class ArticleMarkup(PageMarkup):
    def __init__(self, url):
        super().__init__(url)
        self.article = False
        self.heading = None
        self.title = ""
        self.sections = []
        self.meta = {}
        self.canonical = ""
        self.has_form = False

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "article":
            self.article = True
        elif tag in {"h1", "h2"} and self.article:
            self.heading = tag
            if tag == "h2":
                self.sections.append("")
        elif tag == "meta":
            field = fields.get("property")
            if field in {"og:type", "og:image"}:
                self.meta[field] = fields.get("content")
        elif tag == "link" and fields.get("rel") == "canonical":
            self.canonical = fields.get("href")
        if self.article or tag == "meta":
            self.has_form |= tag == "form"
            super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == self.heading:
            self.heading = None
        if tag == "article":
            self.article = False

    def handle_data(self, data):
        if self.article and self.heading == "h1":
            self.title = (self.title + data)[:180]
        elif self.article and self.heading == "h2":
            self.sections[-1] = (self.sections[-1] + data)[:160]


def read_bytes(url, content_types, max_bytes):
    with httpx.stream("GET", url, timeout=3.0, follow_redirects=False, trust_env=False) as response:
        response.raise_for_status()
        if response.headers.get("content-type", "").partition(";")[0] not in content_types:
            raise ValueError("unexpected media type")
        data = bytearray()
        for chunk in response.iter_bytes(16384):
            data.extend(chunk)
            if len(data) > max_bytes:
                raise ValueError("preview exceeds size limit")
    return data


def read_cover(url):
    try:
        data = read_bytes(url, {"image/jpeg", "image/png", "image/webp"}, 2_000_000)
        with Image.open(io.BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as image:
            if image.width * image.height > 4_000_000:
                return None
            image.thumbnail((900, 600))
            output = io.BytesIO()
            image.convert("RGB").save(output, format="WEBP", quality=76)
        return base64.b64encode(output.getvalue()).decode("ascii")
    except (httpx.HTTPError, OSError, ValueError, Image.DecompressionBombError):
        return None


@lru_cache(maxsize=8)
def _snapshot(url, _bucket, capture_enabled):
    source = PUBLIC_ARTICLES[url]
    try:
        markup = ArticleMarkup(url)
        html = read_bytes(url, {"text/html"}, 750_000).decode("utf-8")
        markup.feed(html)
        markup.close()
    except (httpx.HTTPError, AssertionError, ValueError):
        return None
    title = " ".join(markup.title.split())
    if not title or markup.canonical != url or markup.meta.get("og:type") != "article":
        return None
    headings = " ".join([title, *markup.sections]).casefold()
    facts = {
        "explains_fraud": "lừa đảo" in headings,
        "has_prevention_guidance": any(marker in headings for marker in ("nhận biết", "làm thế nào để tránh")),
        "has_reporting_guidance": "báo cáo" in headings,
        "form_in_article": markup.has_form or markup.password_field or markup.card_field or markup.verification_field,
        "external_form_or_redirect": markup.external_form or markup.meta_refresh,
    }
    return {
        "publisher": source["publisher"], "host": urlsplit(url).hostname, "title": title,
        "image_webp": read_cover(source["cover"]) if markup.meta.get("og:image") == source["cover"] else None,
        "capture": capture_article(html, url, ARTICLE_ASSETS) if capture_enabled else {},
        "facts": facts,
    }


def read_public_article(url, settings, limits):
    if url not in PUBLIC_ARTICLES:
        return None
    snapshot = _snapshot(url, int(time.monotonic() // 300), settings.website_capture_enabled)
    if snapshot is None:
        return None
    facts = snapshot["facts"]
    eligible = (facts["explains_fraud"] and facts["has_prevention_guidance"] and
                not facts["form_in_article"] and not facts["external_form_or_redirect"])
    result, status = query_qwen(settings, limits, ARTICLE_PROMPT, facts)
    valid = isinstance(result, dict) and set(result) == {"context"} and result["context"] in ("educational", "uncertain")
    educational = eligible and valid and result["context"] == "educational"
    findings = []
    if facts["has_prevention_guidance"]:
        findings.append("Các đề mục hướng dẫn nhận biết và phòng tránh website lừa đảo.")
    if facts["has_reporting_guidance"]:
        findings.append("Có đề mục hướng dẫn cách báo cáo website nghi vấn.")
    if facts["form_in_article"] or facts["external_form_or_redirect"]:
        findings.append("HTML có biểu mẫu hoặc khai báo chuyển hướng cần kiểm tra.")
    return {"publisher": snapshot["publisher"], "host": snapshot["host"], "title": snapshot["title"],
            "image_webp": snapshot["image_webp"], **snapshot.get("capture", {}), "findings": findings,
            "context": "educational" if educational else "uncertain",
            "model": QWEN_MODEL if status == "ok" and valid else None}
