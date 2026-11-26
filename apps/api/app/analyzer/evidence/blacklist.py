"""Community blocklist lookup: vn-badsite-filter (malware-filter), data CC0 / project MIT.

Source:  https://malware-filter.gitlab.io/vn-badsite-filter/vn-badsite-filter-domains.txt
Project: https://gitlab.com/malware-filter/vn-badsite-filter (upstream: api.chongluadao.vn)
Snapshot + provenance header: data/vn-badsite-filter-domains.txt (refresh: refresh_blacklist.py).

This is a THIRD-PARTY list, not our ops-approved internal blacklist: it gets a lower weight than
"danh sách đen ĐÃ DUYỆT" (+60) — see scoring.py. Upstream froze on 2025-04-11 (README: "Daily update
... has been stopped due to deprecation of upstream source"), so a miss means nothing; only hits count.
Official domains (domain_check.OFFICIAL, *.gov.vn) are never reported as hits.
"""
from __future__ import annotations

import functools
import pathlib

from .domain_check import OFFICIAL, registered_domain

DATA_FILE = pathlib.Path(__file__).with_name("data") / "vn-badsite-filter-domains.txt"
SOURCE_NAME = "vn-badsite-filter (malware-filter, CC0)"


@functools.lru_cache(maxsize=1)
def _domains() -> frozenset[str]:
    try:
        lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


@functools.lru_cache(maxsize=1)
def snapshot_info() -> dict:
    info = {"source": SOURCE_NAME, "size": len(_domains())}
    try:
        for line in DATA_FILE.read_text(encoding="utf-8").splitlines()[:10]:
            if line.startswith("# Upstream updated:"):
                info["upstream_updated"] = line.split(":", 1)[1].strip()
    except OSError:
        pass
    return info


def lookup(host: str) -> str | None:
    """Return the listed domain matching `host` or one of its parent domains, else None."""
    host = (host or "").lower().rstrip(".")
    if not host or registered_domain(host) in OFFICIAL or host.endswith(".gov.vn"):
        return None
    domains = _domains()
    parts = host.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in domains:
            return candidate
    return None
