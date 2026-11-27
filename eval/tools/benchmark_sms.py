"""Train a benchmark-only SMS classifier with a held-out operating threshold."""
import argparse
import json
import time
import unicodedata
from pathlib import Path

from joblib import dump
from sklearn import __version__
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

from release_manifest import sha256


def rows(path):
    data = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if {item["label"] for item in data} != {"scam", "legit"}:
        raise ValueError("Cần đủ hai nhãn scam và legit")
    texts = [" ".join(unicodedata.normalize("NFC", item["text"]).casefold().split()) for item in data]
    if "" in texts or len(set(texts)) != len(texts):
        raise ValueError("Tập SMS có tin trống hoặc trùng")
    return texts, [int(item["label"] == "scam") for item in data]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train", type=Path)
    parser.add_argument("holdout", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    train, labels = rows(args.train)
    holdout, holdout_labels = rows(args.holdout)
    if not set(train).isdisjoint(holdout):
        parser.error("Train và holdout có nội dung trùng")
    train_x, dev_x, train_y, dev_y = train_test_split(train, labels, test_size=0.2, random_state=42, stratify=labels)
    model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
                          LogisticRegression(C=4, class_weight="balanced", max_iter=1000))
    model.fit(train_x, train_y)
    fpr, recall, thresholds = roc_curve(dev_y, model.predict_proba(dev_x)[:, 1], drop_intermediate=False)
    eligible = [index for index, value in enumerate(fpr) if value <= 0.10]
    chosen = max(eligible, key=lambda index: (recall[index], -fpr[index], thresholds[index]))
    threshold = float(thresholds[chosen])
    scores, times = [], []
    for message in holdout:
        started = time.perf_counter()
        scores.append(float(model.predict_proba([message])[0, 1]))
        times.append(1000 * (time.perf_counter() - started))
    outcomes = list(zip(scores, holdout_labels))
    positives = sum(holdout_labels)
    negatives = len(holdout) - positives
    args.output.mkdir(parents=True, exist_ok=False)
    artifact = args.output / "sms-tfidf.joblib"
    dump(model, artifact, compress=3)
    report = {
        "stage": "benchmark_only", "model": "sms-tfidf-logistic", "scikit_learn": __version__,
        "train_sha256": sha256(args.train), "holdout_sha256": sha256(args.holdout), "artifact_sha256": sha256(artifact),
        "train": len(train_x), "dev": len(dev_x), "holdout": len(holdout),
        "threshold": threshold if threshold != float("inf") else None,
        "dev": {"n": len(dev_x), "recall": float(recall[chosen]), "fpr": float(fpr[chosen])},
        "holdout_metrics": {"recall": sum(p >= threshold and label == 1 for p, label in outcomes) / positives,
                            "fpr": sum(p >= threshold and label == 0 for p, label in outcomes) / negatives,
                            "brier": float(brier_score_loss(holdout_labels, scores)),
                            "p95_ms": round(sorted(times)[(len(times) * 95 + 99) // 100 - 1], 3)},
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    (args.output / "manifest.json").write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
