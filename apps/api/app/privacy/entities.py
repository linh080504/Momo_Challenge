import re
from urllib.parse import urlsplit

from ..kit import domain_check, pii_mask

URL = re.compile(
    r"https?://[^\s<>\"']+|(?<![\w@.])(?:[a-z\d](?:[a-z\d-]*[a-z\d])?\.)+"
    r"(?:[a-z]{2,})(?=[/?:\s,.)!?;]|$)(?:/[^\s<>\"']*)?", re.I
)
ACCOUNT = re.compile(
    r"\b(?:stk|số tài khoản|tài khoản (?:nhận|tạm giữ|cá nhân))\s*[:#-]?\s*([0-9]{6,19})(?!\d)",
    re.I,
)
HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")


def extract(text, supplied_url, signer):
    keys, entities, domains = {}, [], {}

    def add(kind, value, display):
        digest = signer.digest(kind, value)
        if digest not in keys and len(keys) < 30:
            keys[digest] = kind
            entities.append({"type": kind, "display": display})

    explicit_accounts = set(ACCOUNT.findall(text))
    for account in sorted(explicit_accounts):
        add("ACCOUNT", account, "••••" + account[-4:])
    for token, value in pii_mask.mask_text(text)["mapping"].items():
        kind = token[1:].split("_")[0]
        # Long unidentified numbers are review context only, never match keys.
        if kind == "PHONE" and value not in explicit_accounts:
            add(kind, value, "••••" + value[-4:])

    candidates = ([supplied_url] if supplied_url else []) + URL.findall(text)[:20]
    for raw in candidates:
        if len(domains) >= 6:
            break
        candidate = raw.strip().rstrip(".,)!?;")
        try:
            parsed = urlsplit(candidate if "://" in candidate else "http://" + candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                continue
            result = domain_check.check(candidate)
            host = result["host"].rstrip(".").encode("idna").decode()
        except (ValueError, UnicodeError):
            continue
        signals = {signal["signal"] for signal in result["signals"]}
        if not HOST.fullmatch(host) and "ip_url" not in signals:
            continue
        domains[host] = result
        # Avoid approving an entire official service or a shared shortener.
        if not signals.intersection({"official", "shortener", "ip_url"}):
            add("URL", host, "Đã trích tên miền")
    return keys, entities, domains
