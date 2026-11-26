import base64
import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict


class Signer:
    def __init__(self, secret):
        self.key = secret.encode()

    def digest(self, purpose, value):
        return hmac.new(self.key, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()

    def issue(self, purpose, claims, seconds):
        body = base64.urlsafe_b64encode(
            json.dumps([int(time.time()) + seconds, claims], separators=(",", ":")).encode()
        ).decode().rstrip("=")
        return f"{body}.{self.digest(purpose, body)}"

    def read(self, purpose, token):
        try:
            body, signature = token.split(".", 1)
            if not hmac.compare_digest(self.digest(purpose, body), signature):
                return None
            expires, claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            return claims if expires > time.time() else None
        except (ValueError, TypeError):
            return None


class Limits:
    """Bounded rate counters for the MVP's single API instance."""

    def __init__(self):
        self.lock = threading.Lock()
        self.buckets = OrderedDict()

    def take(self, key, maximum, period=60):
        window = int(time.time()) // period
        with self.lock:
            previous, count = self.buckets.get(key, (window, 0))
            if previous != window:
                count = 0
            if count >= maximum:
                return False
            self.buckets[key] = (window, count + 1)
            self.buckets.move_to_end(key)
            if len(self.buckets) > 4096:
                first = next(iter(self.buckets))
                if first == "llm-daily":
                    self.buckets.move_to_end(first)
                self.buckets.popitem(last=False)
            return True
