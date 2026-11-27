import asyncio
import io
import ipaddress
import re
import zlib
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from threading import BoundedSemaphore
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpx
from PIL import Image

from ..kit import pii_mask
from .article_capture import capture_article
from .url_gateway import inspect_url
from .website_report import PageMarkup


MAX_HTML_BYTES = 750_000
DNS_ENDPOINT = "https://cloudflare-dns.com/dns-query"
FETCH_SLOTS = BoundedSemaphore(3)
REDIRECTS = {301, 302, 303, 307, 308}
GLOBAL_IPV6 = ipaddress.IPv6Network("2000::/3")
GAMBLING = re.compile(r"\b(?:casino|cá cược|đặt cược|sports betting|nhà cái|nổ hũ)\b", re.I)
DEPOSIT = re.compile(r"\b(?:nạp tiền|nạp đầu|đặt cọc|tiền nạp|deposit|chuyển khoản)\b", re.I)
INCENTIVE = re.compile(r"\b(?:thưởng đăng ký|thưởng nạp|hoàn trả|khuyến mãi|signup bonus|deposit bonus)\b", re.I)
URGENCY = re.compile(r"\b(?:chuyển ngay|nộp ngay|thanh toán ngay|trong vòng \d+ phút|pay immediately)\b", re.I)
EDUCATION = re.compile(r"\b(?:phòng tránh|cách nhận biết|dấu hiệu nhận biết|how to spot|avoid scams?)\b", re.I)
RESTRICTED_PREVIEW = re.compile(r"\b(?:pornography|porn videos?|nội dung người lớn|phim khiêu dâm)\b", re.I)
TEXT_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif", "image/gif"}
FONT_TYPES = {"font/woff2", "application/font-woff2", "application/font-woff", "application/octet-stream"}
CSS_URL = re.compile(r"""url\(\s*['"]?([^'"()\s]+)['"]?\s*\)""", re.I)
ASSET_LIMITS = {"stylesheet": ({"text/css"}, 900_000), "image": (IMAGE_TYPES, 650_000),
                "font": (FONT_TYPES, 150_000)}
SHARED_STATIC_HOSTS = {"cdn.jsdelivr.net", "cdnjs.cloudflare.com", "fonts.googleapis.com", "fonts.gstatic.com"}
PUBLISHER_STATIC_HOSTS = {
    "humanactprize.org": {"minisiteb.qltns.mediacdn.vn", "static.mediacdn.vn", "ims.mediacdn.vn"},
}


class PublicPageMarkup(PageMarkup):
    NON_CONTENT = {"script", "style", "template", "noscript", "svg", "iframe"}

    def __init__(self, url):
        super().__init__(url)
        self.hidden = []
        self.heading = None
        self.labels = {"title": "", "h1": ""}
        self.text = []
        self.text_size = 0
        self.articles = 0
        self.forms = 0
        self.description = ""
        self.paragraph = None
        self.excerpts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.NON_CONTENT:
            self.hidden.append(tag)
        if self.hidden:
            return
        if tag in self.labels and not self.labels[tag]:
            self.heading = tag
        if tag == "p" and self.labels["h1"] and len(self.excerpts) < 8:
            self.paragraph = ""
        if tag == "article":
            self.articles += 1
        if tag == "form":
            self.forms += 1
        if tag == "meta" and not self.description:
            fields = dict(attrs)
            if fields.get("name") == "description" or fields.get("property") == "og:description":
                self.description = (fields.get("content") or "")[:600]
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        if tag == self.heading:
            self.heading = None
        if tag == "p" and self.paragraph is not None:
            if len(self.paragraph) >= 60 and not (RESTRICTED_PREVIEW.search(self.paragraph) or GAMBLING.search(self.paragraph)):
                excerpt = TEXT_URL.sub("[URL]", self.paragraph)
                self.excerpts.append(pii_mask.mask_text(excerpt)["masked"][:440])
            self.paragraph = None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, text):
        if self.hidden:
            return
        text = " ".join(text.split())
        if self.heading:
            self.labels[self.heading] = (self.labels[self.heading] + " " + text).strip()[:140]
        if self.paragraph is not None and text:
            self.paragraph = (self.paragraph + " " + text).strip()[:520]
        if text and self.text_size < 24_000:
            self.text.append(text[:24_000 - self.text_size])
            self.text_size += len(self.text[-1])


def parse_public_page(html, url):
    reader = PublicPageMarkup(url)
    reader.feed(html)
    reader.close()
    text = " ".join(reader.text)
    if not text:
        return None
    heading = reader.labels["h1"] or reader.labels["title"]
    educational = bool(EDUCATION.search(heading))
    gambling_offer = bool(GAMBLING.search(text) and DEPOSIT.search(text) and not educational)
    sensitive_form = reader.password_field or reader.verification_field or reader.card_field
    facts = {
        "sensitive_form": sensitive_form, "external_form": reader.external_form,
        "meta_redirect": reader.meta_refresh, "gambling_offer": gambling_offer,
        "payment_incentive": bool(INCENTIVE.search(text) and DEPOSIT.search(text) and not educational),
        "payment_pressure": bool(URGENCY.search(text) and not educational), "educational_heading": educational,
        "article_markup": reader.articles > 0,
        "article_count": reader.articles,
        "form_count": reader.forms,
    }
    findings = [message for key, message in (
        ("sensitive_form", "HTML có trường yêu cầu mật khẩu, mã xác thực hoặc thông tin thẻ."),
        ("external_form", "HTML khai báo biểu mẫu gửi dữ liệu sang tên miền khác."),
        ("meta_redirect", "HTML khai báo chuyển hướng qua thẻ meta."),
        ("gambling_offer", "Nội dung có dấu hiệu mời cá cược kèm nạp tiền."),
        ("payment_incentive", "Nội dung nhắc đến khuyến mãi hoặc tiền thưởng gắn với khoản nạp."),
        ("payment_pressure", "Nội dung có lời thúc giục thanh toán."),
        ("educational_heading", "Tiêu đề có dấu hiệu là nội dung hướng dẫn nhận biết hoặc phòng tránh."),
        ("article_markup", "HTML có cấu trúc bài viết."),
    ) if facts[key]]
    # Omit promotional headers and mask personal data in read-only preview headings.
    hide_preview = bool(gambling_offer or (GAMBLING.search(heading) and not educational) or RESTRICTED_PREVIEW.search(heading))
    title = None if hide_preview else pii_mask.mask_text(heading)["masked"][:140]
    if title and reader.description and not RESTRICTED_PREVIEW.search(reader.description):
        description = TEXT_URL.sub("[URL]", " ".join(reader.description.split()))
        facts["public_description"] = pii_mask.mask_text(description)["masked"][:280]
    if title and reader.excerpts:
        facts["public_excerpts"] = reader.excerpts
    return facts, findings, title


def _destination(url):
    domain = inspect_url(url)
    parts = urlsplit(url if "://" in url else "https://" + url)
    port = 443 if parts.scheme == "https" else 80
    if not domain["lookup_allowed"] or parts.username is not None or parts.port not in (None, port):
        raise ValueError("outside public web scope")
    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    return parts.scheme, domain["host"], port, path, domain["registered_domain"]


def _public_address(value):
    ip = ipaddress.ip_address(value)
    return (ip.is_global and not ip.is_multicast and not ip.is_reserved and
            (ip.version == 4 or ip in GLOBAL_IPV6 and ip.sixtofour is None and ip.teredo is None))


async def _resolve(client, host):
    for record, number in (("A", 1), ("AAAA", 28)):
        dns = await client.get(DNS_ENDPOINT, params={"name": host, "type": record}, headers={"Accept": "application/dns-json"})
        dns.raise_for_status()
        addresses = [row["data"] for row in dns.json().get("Answer", []) if row.get("type") == number]
        if addresses:
            return addresses[0] if all(_public_address(address) for address in addresses) else None
    return None


@asynccontextmanager
async def _pinned_get(client, scheme, host, address, path, accept):
    authority = f"[{address}]" if ":" in address else address
    pinned = urlunsplit((scheme, authority, path, "", ""))
    request = httpx.Request("GET", pinned, headers={"Host": host, "Accept": accept, "Accept-Encoding": "gzip, identity"},
                            extensions={"sni_hostname": host})
    response = await client.send(request, stream=True, follow_redirects=False)
    try:
        yield response
    finally:
        await response.aclose()


async def _read_body(response, limit):
    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in {"identity", "gzip"}:
        return "unsupported", None
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
    body = bytearray()
    wire_size = 0
    async for chunk in response.aiter_raw(16_384):
        wire_size += len(chunk)
        if wire_size > limit:
            return "too_large", None
        if decoder:
            chunk = decoder.decompress(chunk, max_length=limit - len(body) + 1)
        body.extend(chunk)
        if len(body) > limit:
            return "too_large", None
    if decoder and (not decoder.eof or decoder.unused_data):
        return "unsupported", None
    return "read", body


def _media_type(response):
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


async def _fetch(url):
    original_scheme, _, _, _, original_root = _destination(url)
    async with asyncio.timeout(7), httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=3.0,
                                                   limits=httpx.Limits(max_keepalive_connections=0)) as client:
        for _ in range(3):
            scheme, host, port, path, root = _destination(url)
            if root != original_root or original_scheme == "https" and scheme != "https":
                return "redirect", None, None
            address = await _resolve(client, host)
            if not address:
                return "restricted", None, None
            async with _pinned_get(client, scheme, host, address, path, "text/html, application/xhtml+xml") as response:
                if response.status_code in REDIRECTS and response.headers.get("location"):
                    url = urljoin(f"{scheme}://{host}{path}", response.headers["location"])
                    continue
                if response.status_code != 200:
                    return "unavailable", None, None
                if _media_type(response) not in {"text/html", "application/xhtml+xml"}:
                    return "unsupported", None, None
                status, body = await _read_body(response, MAX_HTML_BYTES)
                return status, body.decode(response.encoding or "utf-8", errors="replace") if body is not None else None, f"{scheme}://{host}{path}"
        return "redirect", None, None


class PreviewAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stylesheets = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "link" and "stylesheet" in (fields.get("rel") or "").lower().split():
            self.stylesheets.append(fields.get("href"))
        if tag in {"img", "source"}:
            self.images.extend((fields.get("src"), fields.get("data-src")))
            candidates = (fields.get("srcset") or "").split(",")
            self.images.extend(entry.strip().split()[0] for entry in candidates[:3] if entry.strip())
        if tag == "meta" and fields.get("property") == "og:image":
            self.images.append(fields.get("content"))


def _css_resources(css, base):
    fonts = []
    images = []
    for match in CSS_URL.finditer(css.decode("utf-8", errors="replace")):
        source = match[1]
        if source.startswith(("#", "data:")):
            continue
        try:
            location = urljoin(base, source)
            path = urlsplit(location).path.lower()
        except ValueError:
            continue
        if path.endswith(".woff2"):
            fonts.append(location)
        elif path.endswith((".webp", ".png", ".jpg", ".jpeg", ".gif", ".avif")):
            images.append(location)
    return fonts, images


async def _read_assets(html, url):
    parser = PreviewAssets()
    parser.feed(html)
    _, _, _, _, root = _destination(url)
    assets = {}
    approved = SHARED_STATIC_HOSTS | PUBLISHER_STATIC_HOSTS.get(root, set())
    addresses = {}
    requests = asyncio.Semaphore(8)
    used_bytes = 0
    async with httpx.AsyncClient(trust_env=False, timeout=2.0, limits=httpx.Limits(max_keepalive_connections=0)) as client:
        async def read(source, kind):
            nonlocal used_bytes
            if not source:
                return
            try:
                location = str(httpx.URL(urljoin(url, source)).copy_with(fragment=None))
                if location in assets:
                    return
                scheme, host, _, path, registered = _destination(location)
                if scheme != "https" or (registered != root and host not in approved):
                    return
                async with requests:
                    if host not in addresses:
                        addresses[host] = asyncio.create_task(_resolve(client, host))
                    address = await addresses[host]
                    if not address:
                        return
                    allowed, maximum = ASSET_LIMITS[kind]
                    async with _pinned_get(client, scheme, host, address, path, ", ".join(sorted(allowed))) as response:
                        media = _media_type(response)
                        if response.status_code != 200 or media not in allowed:
                            return
                        _, body = await _read_body(response, maximum)
                    if not body or used_bytes + len(body) > 4_000_000:
                        return
                    if kind == "image":
                        with Image.open(io.BytesIO(body), formats=("JPEG", "PNG", "WEBP", "GIF", "AVIF")) as image:
                            if image.width * image.height > 6_000_000:
                                return
                            image.thumbnail((1280, 950))
                            raster = io.BytesIO()
                            mode = "RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB"
                            image.convert(mode).save(raster, format="WEBP", quality=76)
                            body, media = raster.getvalue(), "image/webp"
                    elif kind == "font":
                        if body[:4] != b"wOF2":
                            return
                        media = "font/woff2"
                    used_bytes += len(body)
                    assets[location] = (kind, media, bytes(body))
            except (httpx.HTTPError, OSError, ValueError, LookupError, zlib.error, Image.DecompressionBombError):
                return

        try:
            async with asyncio.timeout(5):
                styles = tuple(dict.fromkeys(parser.stylesheets))[:12]
                images = tuple(dict.fromkeys(parser.images))[:16]
                await asyncio.gather(*(read(src, "stylesheet") for src in styles),
                                     *(read(src, "image") for src in images))
                fonts, backgrounds = [], []
                for location, (kind, _, body) in assets.items():
                    if kind == "stylesheet":
                        css_fonts, css_images = _css_resources(body, location)
                        fonts.extend(css_fonts)
                        backgrounds.extend(css_images)
                await asyncio.gather(*(read(src, "font") for src in list(dict.fromkeys(fonts))[:14]),
                                     *(read(src, "image") for src in list(dict.fromkeys(backgrounds))[:8]))
        except TimeoutError:
            pass
    return assets


def read_public_page(url, *, capture=False):
    if not FETCH_SLOTS.acquire(blocking=False):
        return {"status": "busy"}, None
    try:
        return _read_public_page(url, capture=capture)
    finally:
        FETCH_SLOTS.release()


def _read_public_page(url, *, capture):
    try:
        status, html, origin = asyncio.run(_fetch(url))
        if status != "read":
            return {"status": status}, None
        parsed = parse_public_page(html, origin)
        if parsed is None:
            return {"status": "unavailable"}, None
        facts, findings, title = parsed
        result = {"status": "read", "findings": findings, "title": title}
        if title:
            facts["public_title"] = TEXT_URL.sub("[URL]", title)
        if capture and title is not None:
            try:
                assets = asyncio.run(_read_assets(html, origin))
            except (AssertionError, UnicodeError, ValueError, AttributeError, TypeError):
                assets = {}
            result.update(capture_article(html, str(httpx.URL(origin)), assets, offline=True))
        return result, facts
    except (AssertionError, httpx.HTTPError, LookupError, OSError, ValueError, AttributeError, TypeError, zlib.error):
        return {"status": "unavailable"}, None
