import re
import threading
import time
from collections import OrderedDict

import httpx

from ..privacy.entities import HOST

ENDPOINT = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


class SafeBrowsing:
    def __init__(self, key):
        self.key = key
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def lookup(self, domains):
        # Query only a domain root. User paths, query strings and private hosts
        # never leave this process, so coverage is limited to domain matches.
        roots = {
            result["registered_domain"].encode("idna").decode().rstrip(".")
            for result in domains.values()
            if not any(signal["signal"] == "ip_url" for signal in result["signals"])
        }
        candidates = [
            f"https://{root}/" for root in sorted(roots)
            if HOST.fullmatch(root) and not re.search(r"\d{6,}", root)
            and not root.endswith((".local", ".internal", ".test", ".localhost", ".invalid"))
        ]
        if not candidates or not self.key:
            return False, False
        now = time.monotonic()
        with self.lock:
            cached = {url: value for url in candidates
                      if (value := self.cache.get(url)) and value[0] > now}
        pending = [url for url in candidates if url not in cached]
        found = any(value[1] for value in cached.values())
        if not pending:
            return True, found
        try:
            response = httpx.post(
                ENDPOINT, params={"key": self.key},
                json={"client": {"clientId": "truoc-khi-chuyen", "clientVersion": "0.1"},
                      "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                                     "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
                                     "threatEntries": [{"url": url} for url in pending]}},
                timeout=1.35,
            )
            response.raise_for_status()
            matches = {
                row["threat"]["url"]: float(row["cacheDuration"].removesuffix("s"))
                for row in response.json().get("matches", [])
            }
        except (httpx.HTTPError, ValueError, AttributeError, KeyError, TypeError):
            return False, found
        with self.lock:
            for url in pending:
                positive = url in matches
                ttl = min(matches[url], 3600) if positive else 60
                self.cache[url] = (now + ttl, positive)
                self.cache.move_to_end(url)
            while len(self.cache) > 2048:
                self.cache.popitem(last=False)
        return True, found or any(url in matches for url in pending)
