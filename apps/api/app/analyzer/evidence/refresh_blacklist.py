"""Refresh data/vn-badsite-filter-domains.txt from upstream (stdlib only, run by a human or cron).

    python -m app.analyzer.evidence.refresh_blacklist            # from apps/api
    python -m app.analyzer.evidence.refresh_blacklist --check    # print upstream "Updated:" only

Every line is validated as a plain domain; anything else is dropped. Refuses to overwrite the
snapshot with a list that shrank by more than half (likely a broken download).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
import urllib.request

from .blacklist import DATA_FILE

URLS = ("https://malware-filter.gitlab.io/vn-badsite-filter/vn-badsite-filter-domains.txt",
        "https://vn-badsite-filter.pages.dev/vn-badsite-filter-domains.txt")
DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
MAX_BYTES = 20 * 1024 * 1024


def download() -> tuple[str, bytes]:
    last = None
    for url in URLS:
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                if "text/plain" not in r.headers.get("Content-Type", ""):
                    raise ValueError(f"unexpected content-type {r.headers.get('Content-Type')}")
                return url, r.read(MAX_BYTES)
        except Exception as exc:  # try next mirror
            last = exc
    raise RuntimeError(f"all mirrors failed: {last}")


def build(url: str, raw: bytes) -> tuple[str, int, str | None]:
    updated, domains, rejected = None, set(), 0
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("# Updated:"):
            updated = line.split(":", 1)[1].strip()
        if not line or line.startswith("#"):
            continue
        if len(line) <= 253 and DOMAIN.match(line):
            domains.add(line)
        else:
            rejected += 1
    header = [
        "# vn-badsite-filter (domains) - snapshot for Truoc Khi Chuyen analyzer",
        f"# Source: {url}",
        "# Project: https://gitlab.com/malware-filter/vn-badsite-filter (MIT; data CC0, upstream api.chongluadao.vn)",
        f"# Upstream updated: {updated}",
        f"# Downloaded: {dt.date.today().isoformat()}  sha256(raw)={hashlib.sha256(raw).hexdigest()}",
        f"# Domains: {len(domains)}  rejected_lines: {rejected}",
    ]
    return "\n".join(header + sorted(domains)) + "\n", len(domains), updated


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    url, raw = download()
    content, n, updated = build(url, raw)
    print(f"upstream updated={updated} domains={n} from {url}")
    if args.check:
        return 0
    old = sum(1 for line in DATA_FILE.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")) \
        if DATA_FILE.exists() else 0
    if old and n < old // 2:
        print(f"refusing: new list has {n} domains, snapshot has {old}", file=sys.stderr)
        return 1
    DATA_FILE.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {DATA_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
