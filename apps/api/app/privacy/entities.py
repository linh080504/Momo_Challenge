import re
from ..evidence.url_gateway import inspect_url
from ..kit import pii_mask

URL = re.compile(
    r"https?://[^\s<>\"']+|(?<![\w@.])(?:[^\W_](?:[^\W_]|-){0,62}[.。．｡])+"
    r"(?:[a-z]{2,}|xn--[a-z0-9-]+)(?=[/?:\s,.)!?;]|$)(?:[/:?][^\s<>\"']*)?", re.I
)
ACCOUNT = re.compile(
    r"\b(?:stk|số tài khoản|tài khoản (?:nhận|tạm giữ|cá nhân))\s*[:#-]?\s*([0-9]{6,19})(?!\d)",
    re.I,
)


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
            result = inspect_url(candidate)
        except (ValueError, UnicodeError):
            continue
        signals = {signal["signal"] for signal in result["signals"]}
        host = result["host"]
        if host not in domains or result["score"] > domains[host]["score"]:
            domains[host] = result
        # Avoid approving an entire official service or a shared shortener.
        if result["lookup_allowed"] and not signals.intersection({"official", "shortener"}):
            add("URL", host, "Đã trích tên miền")
    return keys, entities, domains
