import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import idna

from ..kit import domain_check
from .rdap import REGISTRIES
from .url_gateway import inspect_url


FIELD_LABELS = (
    (re.compile(r"\b(?:mật khẩu|password)\b", re.I), "mật khẩu"),
    (re.compile(r"\b(?:otp|mã xác thực|mã xác minh)\b", re.I), "mã xác thực"),
    (re.compile(r"\b(?:số thẻ|cvv|cvc)\b", re.I), "thẻ ngân hàng"),
)
BRAND_LABELS = tuple((re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.I), name, host)
                     for host, name in domain_check.OFFICIAL.items())


def credential_labels(recognized):
    return [label for pattern, label in FIELD_LABELS if pattern.search(recognized)]


def screenshot_brands(recognized, host):
    return [{"name": name, "domain_matches": host == official or host.endswith("." + official)}
            for pattern, name, official in BRAND_LABELS if pattern.search(recognized)][:3]


def source_status(checked, found):
    if found:
        return "match"
    return "clear" if checked else "unavailable"


class PageMarkup(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.host = inspect_url(url)["host"]
        self.password_field = False
        self.verification_field = False
        self.card_field = False
        self.external_form = False
        self.meta_refresh = False

    def handle_starttag(self, tag, attrs):
        values = {name: (value or "").strip() for name, value in attrs}
        if tag == "input":
            autocomplete = set(values.get("autocomplete", "").lower().split())
            self.password_field |= values.get("type", "").lower() == "password"
            self.verification_field |= "one-time-code" in autocomplete
            self.card_field |= bool(autocomplete & {"cc-number", "cc-csc"})
        elif tag == "meta" and values.get("http-equiv", "").lower() == "refresh":
            self.meta_refresh |= bool(re.search(r";\s*url\s*=", values.get("content", ""), re.I))
        action = values.get("action", "") if tag == "form" else values.get("formaction", "") if tag in {"button", "input"} else ""
        if action.lower().startswith(("//", "https://", "http://")) and not self.external_form:
            try:
                # Compare literal hostnames. No destination is resolved or opened.
                target = urlsplit(action).hostname
                if target:
                    host = idna.encode(target.rstrip("."), uts46=True).decode("ascii")
                    self.external_form = host != self.host
            except (ValueError, UnicodeError):
                pass


def markup_signals(html, url):
    parser = PageMarkup(url)
    try:
        parser.feed(html)
        parser.close()
    except (AssertionError, ValueError):
        return {"status": "unreadable", "findings": []}
    signals = (
        (parser.password_field, "HTML có trường nhập mật khẩu."),
        (parser.verification_field, "HTML có trường nhập mã xác thực một lần."),
        (parser.card_field, "HTML có trường nhập số thẻ hoặc mã bảo mật thẻ."),
        (parser.external_form, "HTML khai báo gửi biểu mẫu sang một tên miền khác."),
        (parser.meta_refresh, "HTML khai báo tự chuyển hướng bằng thẻ meta refresh."),
    )
    return {"status": "checked", "findings": [finding for present, finding in signals if present]}


def build_report(domains, evidence, screenshot_text, checked, found, markup, settings):
    sources = {item["source"] for item in evidence}
    eligible = any(domain["lookup_allowed"] for domain in domains.values())
    report = {
        "sources": {
            "domain": source_status(True, any(domain["score"] for domain in domains.values())),
            "community": source_status(eligible, "external_blacklist" in sources),
            "approved_cases": source_status(True, "internal_blacklist" in sources),
            "safe_browsing": source_status(checked, found),
            "rdap": "checked" if "rdap" in sources else "unavailable",
        },
        "screenshot": None,
        "markup": markup,
    }
    limits = {}
    if not checked and not found and not settings.safe_browsing_key:
        limits["safe_browsing"] = "Chưa cấu hình"
    if "rdap" not in sources:
        registry_supported = any((item["registry_domain"] or "").rsplit(".", 1)[-1] in REGISTRIES
                                 for item in domains.values())
        if not registry_supported:
            limits["rdap"] = "Ngoài phạm vi hỗ trợ"
        elif not settings.rdap_lookups_per_hour:
            limits["rdap"] = "Chưa cấu hình"
    if limits:
        report["source_limits"] = limits
    if screenshot_text is not None:
        screenshot_host = next(iter(domains))
        report["screenshot"] = {"credential_labels": credential_labels(screenshot_text),
                                "brands": screenshot_brands(screenshot_text, screenshot_host)}
    return report
