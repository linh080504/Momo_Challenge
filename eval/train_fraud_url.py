"""Train a local FraudURL candidate from separate, reviewed JSONL datasets."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from app.analyzer.providers.fraud_url import FEATURES, features  # noqa: E402
from app.evidence.url_gateway import inspect_url  # noqa: E402


def dataset(file):
    rows = []
    for number, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("verified") is not True or row.get("label") not in ("phishing", "benign"):
            raise ValueError(f"{file.name}:{number}: expected a reviewed phishing/benign label")
        item = inspect_url(row["url"])
        if not item["lookup_allowed"]:
            raise ValueError(f"{file.name}:{number}: expected an eligible public hostname")
        rows.append((item["registered_domain"], features(item), int(row["label"] == "phishing")))
    groups = {label: {domain for domain, _, actual in rows if label == actual} for label in (0, 1)}
    if min(map(len, groups.values())) < 10 or groups[0] & groups[1]:
        raise ValueError(f"{file.name}: need at least 10 distinct, consistently labeled domains per class")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("holdout", type=Path)
    parser.add_argument("output", type=Path, help="New directory for a candidate artifact")
    args = parser.parse_args()
    train, holdout = dataset(args.train), dataset(args.holdout)
    if {row[0] for row in train} & {row[0] for row in holdout}:
        parser.error("Training and holdout domains must be disjoint.")
    samples = lgb.Dataset(np.asarray([row[1] for row in train]), label=[row[2] for row in train],
                          feature_name=list(FEATURES))
    model = lgb.train({"objective": "binary", "verbosity": -1, "num_threads": 1,
                       "deterministic": True, "force_col_wise": True, "min_data_in_leaf": 5},
                      samples, num_boost_round=60)
    scores = model.predict(np.asarray([row[1] for row in holdout]), num_threads=1)
    labels = [row[2] for row in holdout]
    threshold = .85
    metrics = {
        "threshold": threshold,
        "recall": sum(score >= threshold and label == 1 for score, label in zip(scores, labels)) / sum(labels),
        "false_positive_rate": sum(score >= threshold and label == 0 for score, label in zip(scores, labels)) / labels.count(0),
        "brier_score": float(sum((score - label) ** 2 for score, label in zip(scores, labels)) / len(labels)),
    }
    args.output.mkdir(parents=True, exist_ok=False)
    artifact = args.output / "fraud-url-v1.txt"
    model.save_model(artifact)
    manifest = {"schema_version": 1, "model": "fraud-url-v1", "stage": "candidate", "features": FEATURES,
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "train_samples": len(train), "holdout_samples": len(holdout), "metrics": metrics}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
