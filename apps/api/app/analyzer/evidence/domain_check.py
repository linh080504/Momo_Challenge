"""Domain heuristics — port of .claude/skills/evidence-tools/scripts/domain_check.py (logic identical).

*.gov.vn counts as official (VNNIC only issues .gov.vn to state bodies; DECISIONS 2026-11-26).

Keep in sync with the kit script; test_evidence.py checks parity on sample URLs.
RDAP (network) is off by default; .vn domains usually have no RDAP -> None, never "safe".
"""
from __future__ import annotations

import ipaddress
import json
import urllib.parse
import urllib.request

from rapidfuzz.distance import Levenshtein

# Danh sách trắng rút gọn — đội bổ sung và kiểm chứng từng mục (sau này chuyển sang DB, chuyên viên sửa được).
OFFICIAL = {
    "vietcombank.com.vn": "Vietcombank", "vietinbank.vn": "VietinBank", "bidv.com.vn": "BIDV",
    "agribank.com.vn": "Agribank", "techcombank.com": "Techcombank", "mbbank.com.vn": "MB Bank",
    "acb.com.vn": "ACB", "vpbank.com.vn": "VPBank", "tpb.vn": "TPBank", "sacombank.com.vn": "Sacombank",
    "momo.vn": "MoMo", "zalopay.vn": "ZaloPay", "vnpay.vn": "VNPAY", "napas.com.vn": "NAPAS",
    "dichvucong.gov.vn": "Cổng DVC quốc gia", "bocongan.gov.vn": "Bộ Công an", "vss.gov.vn": "BHXH VN",
    "evn.com.vn": "EVN", "shopee.vn": "Shopee", "tiki.vn": "Tiki", "lazada.vn": "Lazada",
    "tinnhiemmang.vn": "NCSC", "chongluadao.vn": "Chống Lừa Đảo",
    "kaspersky.com.vn": "Kaspersky",
}
BRAND_TOKENS = {
    "vietcombank": "vietcombank.com.vn", "vcb": "vietcombank.com.vn", "vietinbank": "vietinbank.vn",
    "bidv": "bidv.com.vn", "agribank": "agribank.com.vn", "techcombank": "techcombank.com",
    "mbbank": "mbbank.com.vn", "vpbank": "vpbank.com.vn", "tpbank": "tpb.vn", "sacombank": "sacombank.com.vn",
    "momo": "momo.vn", "zalopay": "zalopay.vn", "vnpay": "vnpay.vn", "napas": "napas.com.vn",
    "dichvucong": "dichvucong.gov.vn", "congan": "bocongan.gov.vn", "bocongan": "bocongan.gov.vn",
    "baohiemxahoi": "vss.gov.vn", "bhxh": "vss.gov.vn", "evn": "evn.com.vn", "shopee": "shopee.vn",
    "vneid": "vneid.gov.vn", "kaspersky": "kaspersky.com.vn",
}
RISKY_TLDS = {"xyz", "top", "cc", "club", "icu", "online", "site", "live", "vip", "buzz", "shop", "click",
              "link", "info", "work", "rest", "cfd", "sbs", "lol", "monster", "tk", "ml", "ga", "cf", "gq"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "s.id", "shorturl.at",
              "tiny.cc", "ow.ly", "rebrand.ly"}
MULTI_SUFFIX = {"com.vn", "gov.vn", "net.vn", "org.vn", "edu.vn", "co.uk", "com.au"}
HOMOGLYPHS = [("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s")]


def registered_domain(host: str) -> str:
    parts = host.lower().rstrip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_SUFFIX:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def levenshtein(a: str, b: str) -> int:
    return Levenshtein.distance(a, b)


def deglyph(s: str) -> str:
    for a, b in HOMOGLYPHS:
        s = s.replace(a, b)
    return s


def rdap_age_days(domain: str, timeout: float = 6.0) -> int | None:
    """Tuổi tên miền (ngày) qua rdap.org. Trả None nếu không tra được (thường gặp với .vn)."""
    import datetime as dt
    try:
        with urllib.request.urlopen(f"https://rdap.org/domain/{domain}", timeout=timeout) as r:
            data = json.load(r)
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                created = dt.datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
                return (dt.datetime.now(dt.timezone.utc) - created).days
    except Exception:
        return None
    return None


def check(url: str, use_rdap: bool = False) -> dict:
    raw = url.strip()
    if "://" not in raw:
        raw = "http://" + raw
    u = urllib.parse.urlsplit(raw)
    host = (u.hostname or "").lower()
    signals: list[dict] = []

    def add(name: str, points: int, detail: str) -> None:
        signals.append({"signal": name, "points": points, "detail": detail})

    try:
        ipaddress.ip_address(host)
        add("ip_url", 40, "Link dùng địa chỉ IP thay vì tên miền")
    except ValueError:
        pass

    try:
        unicode_host = host.encode("ascii").decode("idna") if "xn--" in host else host
    except UnicodeError:
        unicode_host = host
    if "xn--" in host:
        add("punycode", 35, f"Tên miền mã hóa punycode, hiển thị thành: {unicode_host}")

    reg = registered_domain(host)
    label = reg.split(".")[0]
    tld = host.rsplit(".", 1)[-1] if "." in host else ""

    if reg in OFFICIAL or host.endswith(".gov.vn"):
        add("official", -40, f"Khớp tên miền chính thức của {OFFICIAL.get(reg, 'cơ quan nhà nước (.gov.vn)')}")
    else:
        if "@" in u.netloc:
            add("at_sign", 30, "Có ký tự @ trong phần tên miền (kỹ thuật che giấu địa chỉ thật)")
        if host in SHORTENERS or reg in SHORTENERS:
            add("shortener", 20, "Link rút gọn: không biết đích thật, cần mở rộng phía server")
        if tld in RISKY_TLDS:
            add("risky_tld", 20, f"Đuôi .{tld} hay bị dùng cho trang lừa đảo")
        if host.count(".") >= 4:
            add("many_subdomains", 10, "Quá nhiều tên miền con")
        if host.endswith(".gov.vn") is False and any(t in host for t in ("gov", "congan", "chinhphu")):
            add("gov_claim", 25, "Tự xưng cơ quan nhà nước nhưng không dùng đuôi .gov.vn")
        flat = deglyph(host.replace("-", "").replace(".", ""))
        for token, official in BRAND_TOKENS.items():
            if len(token) >= 4 and token in flat:
                add("brand_in_unofficial", 45, f"Chứa '{token}' nhưng không phải {official}")
                break
        else:
            for off in OFFICIAL:
                off_label = off.split(".")[0]
                if len(off_label) >= 5 and 0 < levenshtein(deglyph(label), off_label) <= 2:
                    add("lookalike", 45, f"Gần giống {off} (khác ≤ 2 ký tự)")
                    break
        if any(off in host and not host.endswith(off) for off in OFFICIAL):
            add("official_as_subdomain", 45, "Tên miền chính thức bị đặt làm tên miền con của trang khác")
    if u.scheme == "http":
        add("http_only", 5, "Không dùng HTTPS")

    age = rdap_age_days(reg) if use_rdap else None
    if age is not None and age < 30:
        add("new_domain", 30, f"Tên miền mới đăng ký {age} ngày")

    score = max(0, min(100, sum(s["points"] for s in signals)))
    level = "high" if score >= 45 else "medium" if score >= 20 else "low"
    return {"input": url, "host": host, "registered_domain": reg, "domain_age_days": age,
            "score": score, "level": level, "signals": signals}
