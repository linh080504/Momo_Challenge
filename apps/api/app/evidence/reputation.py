"""Read existing reputation records without submitting a URL for analysis."""
import csv
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
import idna


VIRUSTOTAL = "https://www.virustotal.com/api/v3/domains/"
NAMES = {"virustotal": "VirusTotal", "urlhaus": "URLhaus", "phishtank": "PhishTank"}


def _url_key(url):
    try:
        parts = urlsplit(url if "://" in url else "https://" + url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None:
            return None
        authority = idna.encode(parts.hostname.rstrip("."), uts46=True).decode("ascii")
        if parts.port and parts.port != {"https": 443, "http": 80}[parts.scheme]:
            authority += f":{parts.port}"
        return urlunsplit((parts.scheme, authority, parts.path or "/", parts.query, ""))
    except (ValueError, UnicodeError):
        return None


@lru_cache(maxsize=6)
def _load(path, kind, _mtime, _size):
    with path.open(encoding="utf-8-sig", newline="") as source:
        if kind == "phishtank":
            reader = csv.DictReader(source)
            if not {"url", "verified", "online"} <= set(reader.fieldnames or []):
                raise ValueError("Unexpected PhishTank CSV")
            urls = (row["url"] for row in reader if row["verified"] == "yes" and row["online"] == "yes" and row["url"])
        else:
            urls = (line.strip() for line in source if line.strip() and not line.lstrip().startswith("#"))
        return frozenset(key for url in urls if (key := _url_key(url)))


def _feed_lookup(filename, kind, url):
    scope = "URL trong bản dữ liệu cục bộ"
    if not filename or not url:
        return {"status": "unavailable", "scope": scope}
    path = Path(filename)
    try:
        info = path.stat()
        if not path.is_file() or not 0 < info.st_size <= 24_000_000:
            raise ValueError("Invalid feed size")
        entries = _load(path, kind, info.st_mtime_ns, info.st_size)
    except (OSError, ValueError, csv.Error, UnicodeError):
        return {"status": "unavailable", "scope": scope}
    status = "match" if url in entries else "clear" if entries else "unavailable"
    return {"status": status, "scope": scope}


def check_reputation(url, domain, settings, limits):
    key = _url_key(url) if domain.get("lookup_allowed") else None
    result = {kind: _feed_lookup(filename, kind, key) for kind, filename in (
        ("urlhaus", settings.urlhaus_feed_path), ("phishtank", settings.phishtank_feed_path),
    )}
    vt = {"status": "unavailable", "scope": "Tên miền đăng ký"}
    result["virustotal"] = vt
    token = settings.virustotal_api_key.get_secret_value().strip()
    root = domain.get("registered_domain")
    if not (key and token and root and root == domain.get("registry_domain")
            and limits.take("virustotal-minute", 4)):
        return result
    try:
        response = httpx.get(VIRUSTOTAL + root, headers={"x-apikey": token}, timeout=1.5,
                             follow_redirects=False, trust_env=False)
        response.raise_for_status()
        engines = response.json()["data"]["attributes"]["last_analysis_stats"]
        if type(engines.get("malicious")) is int and engines["malicious"] >= 0:
            vt["status"] = "match" if engines["malicious"] >= 2 else "checked"
    except (httpx.HTTPError, KeyError, ValueError, AttributeError, TypeError):
        pass
    return result
