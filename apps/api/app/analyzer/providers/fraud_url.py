import hashlib
import json
import math
from pathlib import Path

FEATURES = (
    "host_length", "label_count", "digit_count", "hyphen_count", "uses_http",
    "ip_address", "punycode", "brand_similarity", "shortener", "risky_suffix",
    "nonstandard_port", "restricted_host",
)


def features(destination):
    host = destination["host"]
    signals = {item["signal"] for item in destination["signals"]}
    return [len(host), host.count(".") + 1, sum(char.isdigit() for char in host), host.count("-"),
            int("http_only" in signals), int("ip_url" in signals), int("punycode" in signals),
            int(bool(signals & {"brand_homoglyph", "brand_in_unofficial", "lookalike", "official_as_subdomain"})),
            int("shortener" in signals), int("risky_tld" in signals), int("nonstandard_port" in signals),
            int("restricted_host" in signals)]


class FraudURL:
    def __init__(self, artifact):
        from lightgbm import Booster

        model_path = Path(artifact)
        manifest = json.loads(model_path.with_name("manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != 1 or manifest.get("features") != list(FEATURES)
                or manifest.get("artifact_sha256") != hashlib.sha256(model_path.read_bytes()).hexdigest()):
            raise ValueError("FraudURL artifact does not match its registry manifest.")
        self.model = Booster(model_file=model_path)
        self.version = manifest["model"]
        if self.model.feature_name() != list(FEATURES) or self.model.num_model_per_iteration() != 1:
            raise ValueError("FraudURL artifact does not match the feature schema.")

    def score(self, domains):
        if not domains:
            return None
        from numpy import asarray

        scores = self.model.predict(asarray([features(domain) for domain in domains.values()]), num_threads=1)
        valid = [float(score) for score in scores if math.isfinite(score) and 0 <= score <= 1]
        return max(valid) if valid else None
