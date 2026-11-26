"""Evidence step (pipeline step 4): code collects facts, the LLM only interprets them.

Tools run in parallel, each with its own timeout; a failing tool is skipped (never treated as "safe").
Today: domain_check (heuristics) + community blocklist. Later: Safe Browsing, internal approved
blacklist by hash, RDAP — each is one more coroutine in `gather_evidence`.

Only hosts/domains are passed to tools — never the user's text or other PII.
NOTE: lives under app/analyzer/evidence for now (scope of this branch); can move to app/evidence as is.
"""
from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from dataclasses import dataclass, field

from . import blacklist, domain_check

log = logging.getLogger("app.analyzer.evidence")

TOOL_TIMEOUT_S = 2.0
APP_STORE_HOSTS = {"play.google.com", "apps.apple.com", "itunes.apple.com"}
_TLDS = ("com|net|org|vn|info|biz|io|co|me|app|xyz|top|cc|club|icu|online|site|live|vip|buzz|shop|click|link|work|"
         "rest|cfd|sbs|lol|monster|tk|ml|ga|cf|gq|asia|store|tech|pro|fun|cyou|bond|win|vin|bet|ly|gl|at|id|to|gd|"
         "us|uk|au|cn|ru|in|cloud|today|life|world|xin|ink|pw|ws|su|mobi|tv|one|help|support|services|finance|"
         "money|bank|page|dev|edu|gov|ai|so|sh|es|fr|de|jp|kr|tw|hk|sg|th|ph|my|la|kh|cam|men|loan|trade|"
         "best|top|cyou|quest|hair|beauty|skin|makeup|autos|homes|yachts|mom|boats|bar|baby")
URL_RE = re.compile(
    r"(?<![@\w.-])((?:https?://|www\.)[^\s<>\"'(){}\[\]]+"
    r"|(?:[^\W_](?:[\w-]{0,61}[^\W_])?\.)+(?:" + _TLDS + r")(?![\w-])(?::\d{2,5})?(?:/[^\s<>\"'(){}\[\]]*)?)",
    re.IGNORECASE)
_TRAILING = ".,;:!?)]}>…\"'"


@dataclass
class UrlInfo:
    raw: str
    host: str
    registered: str
    official: bool
    app_store: bool


@dataclass
class EvidenceItem:
    source: str          # analysis.schema.json evidence.source enum
    signal: str          # internal id used by scoring.py
    finding: str         # Vietnamese, user-facing, no PII
    host: str | None = None
    level: str | None = None
    detail: dict = field(default_factory=dict)

    def for_prompt(self) -> dict:
        return {"source": self.source, "signal": self.signal, "host": self.host, "level": self.level,
                "finding": self.finding}


def _host_of(raw: str) -> str:
    target = raw if "://" in raw else "http://" + raw
    try:
        host = (urllib.parse.urlsplit(target).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    if host and not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            pass
    return host


def extract_urls(text: str, limit: int = 10) -> list[UrlInfo]:
    out: list[UrlInfo] = []
    seen: set[str] = set()
    for m in URL_RE.finditer(text or ""):
        raw = m.group(1).rstrip(_TRAILING)
        host = _host_of(raw)
        if not host or "." not in host or host in seen:
            continue
        seen.add(host)
        reg = domain_check.registered_domain(host)
        official = reg in domain_check.OFFICIAL or host.endswith(".gov.vn")
        out.append(UrlInfo(raw=raw, host=host, registered=reg, official=official, app_store=host in APP_STORE_HOSTS))
        if len(out) >= limit:
            break
    return out


async def _run(name: str, fn, *args, timeout_s: float):
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout=timeout_s)
    except Exception as exc:  # timeout or tool error -> skip, never "safe"
        log.warning("evidence tool failed", extra={"tool": name, "error": type(exc).__name__})
        return None


def _domain_items(u: UrlInfo, res: dict | None) -> list[EvidenceItem]:
    if not res:
        return []
    sigs = [s for s in res.get("signals", []) if s["signal"] != "http_only"]
    if any(s["signal"] == "official" for s in sigs):
        return [EvidenceItem("domain_check", "official_domain", f"{u.host}: {sigs[0]['detail']}.", u.host, "low", res)]
    level = res.get("level", "low")
    if level == "low":
        return [EvidenceItem("domain_check", "domain_low", f"{u.host}: chưa thấy dấu hiệu tên miền nhái "
                             "(không có nghĩa là an toàn).", u.host, "low", res)]
    details = "; ".join(s["detail"] for s in sigs[:3])
    return [EvidenceItem("domain_check", f"domain_{level}", f"{u.host}: {details}.", u.host, level, res)]


def _blacklist_item(u: UrlInfo, hit: str | None) -> list[EvidenceItem]:
    if not hit:
        return []
    info = blacklist.snapshot_info()
    return [EvidenceItem("external_blacklist", "community_blacklist",
                         f"{u.host}: có trong danh sách trang lừa đảo, độc hại của cộng đồng ({blacklist.SOURCE_NAME}, "
                         f"cập nhật {str(info.get('upstream_updated', '?'))[:10]}).",
                         u.host, "high", {"listed": hit})]


async def gather_evidence(urls: list[UrlInfo], timeout_s: float = TOOL_TIMEOUT_S) -> list[EvidenceItem]:
    if not urls:
        return []
    jobs = []
    for u in urls:
        jobs.append(_run("domain_check", domain_check.check, u.raw, False, timeout_s=timeout_s))
        jobs.append(_run("blacklist", blacklist.lookup, u.host, timeout_s=timeout_s))
    results = await asyncio.gather(*jobs)
    items: list[EvidenceItem] = []
    for i, u in enumerate(urls):
        items += _domain_items(u, results[2 * i])
        items += _blacklist_item(u, results[2 * i + 1])
    return items


__all__ = ["EvidenceItem", "UrlInfo", "extract_urls", "gather_evidence"]
