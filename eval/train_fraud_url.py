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


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def dataset(file, *, uci_benchmark=False):
    rows = []
    for number, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        reviewed = row.get("verified") is True
        published = uci_benchmark and row.get("label_source") == "phiusiil_uci_967"
        if not (reviewed or published) or row.get("label") not in ("phishing", "benign"):
            raise ValueError(f"{file.name}:{number}: expected a reviewed phishing/benign label")
        item = inspect_url(row["url"])
        if not item["lookup_allowed"]:
            raise ValueError(f"{file.name}:{number}: expected an eligible public hostname")
        rows.append((item["registry_domain"], features(item), int(row["label"] == "phishing")))
    groups = {label: {domain for domain, _, actual in rows if label == actual} for label in (0, 1)}
    if min(map(len, groups.values())) < 10 or groups[0] & groups[1]:
        raise ValueError(f"{file.name}: need at least 10 distinct, consistently labeled domains per class")
    return rows


def evaluate(scores, labels, threshold):
    predicted = scores >= threshold
    return {"threshold": float(threshold),
            "recall": float(predicted[labels == 1].mean()),
            "false_positive_rate": float(predicted[labels == 0].mean()),
            "brier_score": float(np.mean((scores - labels) ** 2))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("holdout", type=Path)
    parser.add_argument("output", type=Path, help="New directory for a candidate artifact")
    parser.add_argument("--dev", type=Path, help="Independent domain split used to choose an experimental threshold")
    parser.add_argument("--compare-xgboost", action="store_true", help="Evaluate an XGBoost challenger on the same splits")
    parser.add_argument("--uci-benchmark", action="store_true", help="Allow published labels for benchmark-only artifacts")
    args = parser.parse_args()
    train = dataset(args.train, uci_benchmark=args.uci_benchmark)
    holdout = dataset(args.holdout, uci_benchmark=args.uci_benchmark)
    dev = dataset(args.dev, uci_benchmark=args.uci_benchmark) if args.dev else []
    domains = [{row[0] for row in split} for split in (train, dev, holdout)]
    if sum(map(len, domains)) != len(set.union(*domains)):
        parser.error("Training, dev and holdout domains must be disjoint.")
    samples = lgb.Dataset(np.asarray([row[1] for row in train]), label=[row[2] for row in train],
                          feature_name=list(FEATURES))
    model = lgb.train({"objective": "binary", "verbosity": -1, "num_threads": 1,
                       "deterministic": True, "force_col_wise": True, "min_data_in_leaf": 5},
                      samples, num_boost_round=60)
    def measurements(predict):
        features_test, labels = np.asarray([row[1] for row in holdout]), np.asarray([row[2] for row in holdout])
        scores = predict(features_test)
        output = {"holdout": evaluate(scores, labels, .85)}
        if dev:
            dev_labels = np.asarray([row[2] for row in dev])
            dev_scores = predict(np.asarray([row[1] for row in dev]))
            thresholds = np.append(np.unique(dev_scores), np.nextafter(1.0, 2.0))
            eligible = [result for threshold in thresholds if (result := evaluate(dev_scores, dev_labels, threshold))[
                "false_positive_rate"] <= .10]
            best = max(eligible, key=lambda result: (result["recall"], -result["false_positive_rate"]))
            output["dev_selected"] = best
            output["holdout_at_dev_threshold"] = evaluate(scores, labels, best["threshold"])
        return output

    comparison = {"lightgbm": measurements(lambda values: model.predict(values, num_threads=1))}
    if args.compare_xgboost:
        from xgboost import DMatrix, train as xgb_train

        challenger = xgb_train({"objective": "binary:logistic", "nthread": 1, "seed": 0},
                               DMatrix(np.asarray([row[1] for row in train]), label=[row[2] for row in train]),
                               num_boost_round=60)
        comparison["xgboost"] = measurements(lambda values: challenger.predict(DMatrix(values)))
    args.output.mkdir(parents=True, exist_ok=False)
    artifact = args.output / "fraud-url-v1.txt"
    model.save_model(artifact)
    manifest = {"schema_version": 1, "model": "fraud-url-v1",
                "stage": "benchmark_only" if args.uci_benchmark else "candidate", "features": FEATURES,
                "artifact_sha256": sha256(artifact),
                "input_sha256": {name: sha256(path) for name, path in (
                    ("train", args.train), ("dev", args.dev), ("holdout", args.holdout)) if path is not None},
                "train_samples": len(train), "dev_samples": len(dev), "holdout_samples": len(holdout),
                "metrics": comparison["lightgbm"]["holdout"], "comparison": comparison}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison))


if __name__ == "__main__":
    main()
