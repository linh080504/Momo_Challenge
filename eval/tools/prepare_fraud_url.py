"""Prepare offline, domain-disjoint benchmark splits from the UCI PhiUSIIL archive."""

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZipFile

import idna

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
from app.evidence.url_gateway import REGISTRY_SUFFIX, is_public_domain  # noqa: E402

SOURCE = "UCI PhiUSIIL Phishing URL (Website), Prasad and Chandra (2024), CC BY 4.0"
LABELS = {"0": "phishing", "1": "benign"}
SPLITS = ("train", "dev", "holdout")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare(archive, limit):
    by_domain = {}
    mixed = set()
    with ZipFile(archive) as package:
        member = next(name for name in package.namelist() if name.endswith("PhiUSIIL_Phishing_URL_Dataset.csv"))
        with package.open(member) as stream:
            rows = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
            if not {"URL", "label"}.issubset(rows.fieldnames or ()):
                raise ValueError("Expected PhiUSIIL CSV fields 'URL' and 'label'.")
            for row in rows:
                label = LABELS.get(row["label"])
                try:
                    parts = urlsplit(row["URL"])
                    if parts.username is not None or parts.scheme not in {"https", "http"}:
                        continue
                    host = idna.encode((parts.hostname or "").rstrip("."), uts46=True).decode("ascii")
                    port = parts.port
                except (TypeError, ValueError, UnicodeError):
                    continue
                if not label or not is_public_domain(host):
                    continue
                clean = urlunsplit((parts.scheme, f"{host}:{port}" if port is not None else host, "", "", ""))
                domain = REGISTRY_SUFFIX(host).top_domain_under_public_suffix
                if not domain:
                    continue
                previous = by_domain.get(domain)
                if previous is not None and previous[0] != label:
                    mixed.add(domain)
                rank = digest(clean)
                if previous is None or rank < previous[1]:
                    by_domain[domain] = (label, rank, clean)
    splits = {name: [] for name in SPLITS}
    counts = Counter()
    for domain in sorted(by_domain, key=digest):
        if domain in mixed:
            continue
        bucket = int(digest("phiusiil-v1:" + domain)[:8], 16) % 100
        split = "train" if bucket < 70 else "dev" if bucket < 85 else "holdout"
        label, _, url = by_domain[domain]
        if counts[split, label] >= limit:
            continue
        counts[split, label] += 1
        splits[split].append({"url": url, "label": label, "label_source": "phiusiil_uci_967"})
    return splits, len(mixed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-per-class", type=int, default=5000)
    args = parser.parse_args()
    if args.max_per_class < 10:
        parser.error("Each split needs at least 10 samples per class.")
    splits, excluded = prepare(args.archive, args.max_per_class)
    if any(min(Counter(row["label"] for row in rows).get(label, 0) for label in LABELS.values()) < 10
           for rows in splits.values()):
        parser.error("A generated split has fewer than 10 domains for a label.")
    with args.archive.open("rb") as source:
        archive_hash = hashlib.file_digest(source, "sha256").hexdigest()
    manifest = {"version": "phiusiil-domain-split-v1", "source": SOURCE, "mixed_label_domains_excluded": excluded,
                "archive_sha256": archive_hash, "splits": {}}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, rows in splits.items():
        path = args.output / (name + ".jsonl")
        data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
        path.write_bytes(data)
        manifest["splits"][name] = {"counts": dict(Counter(row["label"] for row in rows)),
                                    "sha256": hashlib.sha256(data).hexdigest()}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: value["counts"] for name, value in manifest["splits"].items()}))


if __name__ == "__main__":
    main()
