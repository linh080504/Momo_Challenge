"""Prepare the published Vietnamese SMS train/test split for local evaluation."""

import argparse
import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


SOURCE = "https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_dataset"
REVISION = "a90e2bd7e8df2376939658075ba8094dcee488ad"
SOURCE_SHA256 = {
    "train": "bf5c34567685fcb9d73e5087289fbc64a196d39fd63d43d027bb68737786da32",
    "test": "166c27e44e90c6648df07c1bf03b7106a909d62d2b5122a727405a3ba8c68391",
}
LABELS = {"0": "legit", "1": "scam"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_split(path, name):
    records = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or set(reader.fieldnames) != {"message", "label"}:
            raise ValueError(f"{name}.csv phải có hai cột message và label")
        for index, row in enumerate(reader, 1):
            message = (row["message"] or "").strip()
            if not message or len(message) > 12_000 or row["label"] not in LABELS or None in row:
                raise ValueError(f"Dữ liệu {name} không hợp lệ tại mẫu {index}")
            key = " ".join(unicodedata.normalize("NFKC", message).casefold().split())
            records.append((key, {"id": f"vsms-{name}-{index:04}", "text": message,
                                  "label": LABELS[row["label"]], "group": None,
                                  "channel": "sms", "synthetic": False, "source": SOURCE}))
    return records


def prepare(source, output):
    splits = {}
    for name, expected in SOURCE_SHA256.items():
        path = source / f"{name}.csv"
        if digest(path) != expected:
            raise ValueError(f"Checksum {path.name} không khớp bản nguồn {REVISION}")
        splits[name] = read_split(path, name)

    labels_by_message = defaultdict(set)
    for rows in splits.values():
        for key, row in rows:
            labels_by_message[key].add(row["label"])
    conflicts = {key for key, labels in labels_by_message.items() if len(labels) > 1}
    train_keys = {key for key, _ in splits["train"]}
    test_overlap = {key for key, _ in splits["test"]} & train_keys
    manifest = {
        "source": SOURCE, "revision": REVISION, "license": "CC-BY-4.0",
        "authors": ["Tran Nguyen Thai Tuan", "Le Hoang Khang", "Nguyen Minh Tai",
                    "Nguyen Van Thang", "Mai Hoang Dinh"],
        "source_positive_label": "Spam/Scam", "source_sha256": SOURCE_SHA256,
        "duplicate_key": "Unicode NFKC, casefold and collapsed whitespace",
        "conflicting_keys": len(conflicts), "overlapping_keys": len(test_overlap), "splits": {},
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        seen = set()
        kept = []
        excluded = Counter()
        for key, row in rows:
            if key in conflicts:
                excluded["conflicting_label"] += 1
            elif name == "test" and key in test_overlap:
                excluded["in_train"] += 1
            elif key in seen:
                excluded["within_split_duplicate"] += 1
            else:
                seen.add(key)
                kept.append(row)
        path = output / f"vsms_{name}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as destination:
            for row in kept:
                destination.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["splits"][name] = {"source_rows": len(rows), "kept": len(kept),
                                    "labels": dict(Counter(row["label"] for row in kept)),
                                    "excluded": dict(excluded), "sha256": digest(path)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Thư mục chứa train.csv và test.csv của bản nguồn")
    parser.add_argument("output", type=Path, help="Thư mục cục bộ để lưu JSONL và manifest")
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
