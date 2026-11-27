import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit

import idna
from tldextract import TLDExtract

from ..kit import domain_check

HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")
REDIRECT_HINT = re.compile(r"(?:^|&)(?:next|redirect(?:_uri|_url)?|return(?:_to|_url)?|continue|destination)=", re.I)
REGISTRY_SUFFIX = TLDExtract(cache_dir=None, suffix_list_urls=())
TENANT_SUFFIX = TLDExtract(cache_dir=None, suffix_list_urls=(), include_psl_private_domains=True)
LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa", ".test", ".invalid", ".example")
BRAND_CONFUSABLES = str.maketrans("аеіјорсухԁԛαεικνορτυχ", "aeijopcyxdqaeikvoptux")


def is_public_domain(host):
    return (is_web_domain(host) and not re.search(r"\d{6,}", host)
            and bool(TENANT_SUFFIX(host).top_domain_under_public_suffix))


def is_web_domain(host):
    return bool(HOST.fullmatch(host) and not host.endswith(LOCAL_SUFFIXES)
                and not host.rsplit(".", 1)[-1].isdigit())


def inspect_url(value):
    """Classify a destination offline. Network clients use configured service URLs only."""
    value = value.strip()
    if not value or len(value) > 2000 or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("invalid URL")
    if "\\" in value:
        raise ValueError("ambiguous URL delimiter")
    parts = urlsplit(value if "://" in value else "https://" + value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("unsupported URL")
    port = parts.port
    address = None
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        host = idna.encode(parts.hostname.rstrip("."), uts46=True).decode("ascii")
    else:
        host = address.compressed
    authority = f"[{host}]" if address and address.version == 6 else host
    result = domain_check.check(f"{parts.scheme}://{authority}")
    if address is None:
        result["registered_domain"] = TENANT_SUFFIX(host).top_domain_under_public_suffix or None
        result["registry_domain"] = REGISTRY_SUFFIX(host).top_domain_under_public_suffix or None
    else:
        result["registered_domain"] = result["registry_domain"] = None
    signals = result["signals"]
    for item in signals:
        if item["signal"] == "shortener":
            item["detail"] = "Link rút gọn che tên miền đích. Hãy kiểm tra nguồn gửi trước khi mở."

    def add(signal, points, detail):
        signals.append({"signal": signal, "points": points, "detail": detail})

    if parts.username is not None:
        add("at_sign", 40, "Địa chỉ chứa thông tin đăng nhập trước tên miền đích.")
    if port is not None and port != {"https": 443, "http": 80}[parts.scheme]:
        add("nonstandard_port", 20, "Đường dẫn sử dụng cổng khác cổng web mặc định.")
    if address is None and "xn--" in host:
        decoded = idna.decode(host)
        folded = unicodedata.normalize("NFKC", decoded).casefold().translate(BRAND_CONFUSABLES)
        for official in domain_check.OFFICIAL:
            if folded == official or folded.endswith("." + official):
                add("brand_homoglyph", 45, "Một số ký tự trong tên miền trông giống địa chỉ thương hiệu.")
                break
    if (address is not None and not address.is_global) or (address is None and not is_web_domain(host)):
        add("restricted_host", 45, "Địa chỉ thuộc mạng nội bộ hoặc vùng tên miền hạn chế.")
    if REDIRECT_HINT.search(parts.query):
        add("redirect_hint", 0, "URL có tham số thường dùng để chuyển hướng. Đích thực tế chưa được xác minh.")
    result["score"] = max(0, min(100, sum(item["points"] for item in signals if item["points"] > 0)))
    result["level"] = "high" if result["score"] >= 45 else "medium" if result["score"] >= 20 else "low"
    result["lookup_allowed"] = address is None and is_public_domain(host)
    result["official_brand"] = domain_check.OFFICIAL.get(host.removeprefix("www."))
    # The allowlist verifies a known origin. Limit the low-risk route to its homepage.
    result["official_homepage"] = (
        result["lookup_allowed"] and parts.scheme == "https" and result["score"] == 0
        and result["official_brand"] is not None
        and parts.path in {"", "/"} and not parts.query and not parts.fragment
    )
    return result


def checked_destination(domain):
    host = re.sub(r"\d{6,}", "••••", domain["host"])
    return {"host": host, "level": domain["level"],
            "signals": [re.sub(r"\d{6,}", "••••", item["detail"]) for item in domain["signals"]],
            "domain_age_days": domain["domain_age_days"], "domain_registered_on": domain.get("domain_registered_on"),
            "official_brand": domain["official_brand"]}
