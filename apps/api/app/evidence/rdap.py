from datetime import datetime, timezone

import httpx

from .url_gateway import is_public_domain

REGISTRIES = {suffix: f"https://rdap.verisign.com/{suffix}/v1/domain/" for suffix in ("com", "net")}


def lookup_age(domains, limits, quota, *, explicit_website=False):
    if not quota:
        return None
    for domain in sorted(domains.values(), key=lambda item: item["score"], reverse=True):
        root = domain["registry_domain"]
        if not root or root != domain["registered_domain"]:
            continue
        endpoint = REGISTRIES.get(root.rsplit(".", 1)[-1])
        if not (domain["lookup_allowed"] and (explicit_website or domain["score"] >= 20) and endpoint and is_public_domain(root)):
            continue
        if not limits.take("rdap-hourly", quota, 3600):
            break
        try:
            response = httpx.get(endpoint + root, timeout=1.2, follow_redirects=False, trust_env=False,
                                 headers={"Accept": "application/rdap+json"})
            response.raise_for_status()
            for event in response.json().get("events", []):
                if event.get("eventAction") == "registration":
                    registered = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - registered).days
                    return (domain["host"], age, registered.astimezone(timezone.utc).date().isoformat()) if age >= 0 else None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            pass
        break
    return None
