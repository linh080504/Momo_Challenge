"""Measure URL, message and QR checks using a local dataset with source citations."""

import argparse
import json
import time
from pathlib import Path

import httpx

CHANNELS = ("url", "message", "qr")


def requests_for(url):
    return (
        ("/v1/analyze", {"url": url}, "risk_level"),
        ("/v1/analyze", {"text": "Xem nội dung tại " + url}, "risk_level"),
        ("/v1/qr/parse", {"payload": url}, "risk"),
    )


def summary(rows, channel):
    found = [row for row in rows if row["channel"] == channel]
    scams = [row for row in found if row["label"] == "phishing"]
    benign = [row for row in found if row["label"] == "benign"]
    warned = {"high", "medium", "uncertain"}
    times = sorted(row["latency_ms"] for row in found)
    return {"samples": len(found), "recall": sum(row["risk"] in warned for row in scams) / len(scams),
            "fpr": sum(row["risk"] in warned for row in benign) / len(benign),
            "uncertain": sum(row["risk"] == "uncertain" for row in found),
            "errors": sum(row["risk"] == "error" for row in found),
            "p95_ms": times[round(.95 * (len(times) - 1))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--api", default="http://127.0.0.1:8020")
    args = parser.parse_args()
    inputs = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if {row.get("label") for row in inputs} != {"phishing", "benign"}:
        parser.error("Supply both phishing and benign labels.")
    ids = {row["id"] for row in inputs}
    if len(ids) != len(inputs) or any(not row.get("source") or not row.get("candidate") for row in inputs):
        parser.error("Each row needs a unique id, candidate and source citation.")
    results = []
    with httpx.Client(base_url=args.api, timeout=15, trust_env=False) as client:
        for row in inputs:
            url = row["candidate"].replace("[.]", ".")
            for channel, (endpoint, body, field) in zip(CHANNELS, requests_for(url)):
                started = time.perf_counter()
                risk, status = "error", None
                try:
                    response = client.post(endpoint, json=body)
                    status = response.status_code
                    if status == 200:
                        risk = response.json()[field]
                except (httpx.HTTPError, KeyError, TypeError, ValueError):
                    pass
                results.append({"id": row["id"], "label": row["label"], "channel": channel,
                                "risk": risk, "status": status,
                                "latency_ms": round((time.perf_counter() - started) * 1000)})
    report = {"by_channel": {channel: summary(results, channel) for channel in CHANNELS}, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["by_channel"]))


if __name__ == "__main__":
    main()
