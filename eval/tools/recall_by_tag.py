#!/usr/bin/env python3
"""Recall / báo nhầm theo từng nhóm mẫu, đọc báo cáo `run_eval.py` (file `eval/reports/<stamp>-<tag>.json`).

Mục đích (quyết định PM 2026-11-26): ảnh có chú thích (tag `annotated`) phải báo recall RIÊNG, vì analyzer có thể
đọc nhãn từ dấu X đỏ/"GIẢ MẠO" thay vì từ nội dung; ảnh `official_mock` không tính vào ảnh thật.

  python3 eval/tools/recall_by_tag.py eval/reports/20261127-101500-v1.json --data eval/dataset.jsonl

Nhóm in ra: tất cả · văn bản · ảnh thật (không official_mock) · ảnh annotated · ảnh KHÔNG chú thích ·
official_mock · hard_positive · hard_negative · từng `provenance` · từng `scenario_id` có ≥ 1 mẫu scam.
Cột n nhỏ (< 5) kèm cảnh báo: con số chưa có ý nghĩa thống kê.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--data", default="eval/dataset.jsonl")
    args = ap.parse_args()

    rep = json.loads(pathlib.Path(args.report).read_text(encoding="utf-8"))
    if "results" not in rep:
        print("Báo cáo không có `results` (dùng file timestamp `<stamp>-<tag>.json`, không dùng latest.json)")
        return 2
    data = {}
    for line in pathlib.Path(args.data).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            data[row["id"]] = row

    rows = []
    for r in rep["results"]:
        meta = data.get(r["id"])
        if meta is None:
            continue  # mẫu không còn trong dataset
        rows.append({**r, "provenance": meta.get("provenance"), "scenario_id": meta.get("scenario_id"),
                     "is_image": "image" in meta})

    def seg(name, pred):
        rs = [r for r in rows if pred(r)]
        sc = [r for r in rs if r["label"] == "scam"]
        lg = [r for r in rs if r["label"] == "legit"]
        rec = f"{sum(r['flagged'] for r in sc) / len(sc):.3f}" if sc else "  -  "
        fpr = f"{sum(r['flagged'] for r in lg) / len(lg):.3f}" if lg else "  -  "
        warn = "  (n nhỏ)" if (sc and len(sc) < 5) or (lg and len(lg) < 5) else ""
        missed = ",".join(r["id"] for r in sc if not r["flagged"])
        print(f"{name:<32} scam={len(sc):<3} recall={rec}   legit={len(lg):<3} báo nhầm={fpr}{warn}"
              + (f"   bỏ sót: {missed}" if missed else ""))

    print(f"Báo cáo: {args.report} · {len(rows)}/{len(rep['results'])} mẫu khớp dataset")
    seg("tất cả", lambda r: True)
    seg("văn bản", lambda r: not r["is_image"])
    seg("ảnh thật (không official_mock)", lambda r: r["is_image"] and r["provenance"] != "official_mock")
    seg("ảnh annotated", lambda r: r["is_image"] and "annotated" in r["tags"])
    seg("ảnh KHÔNG chú thích", lambda r: r["is_image"] and "annotated" not in r["tags"]
        and r["provenance"] != "official_mock")
    seg("ảnh official_mock", lambda r: r["provenance"] == "official_mock")
    seg("hard_positive", lambda r: "hard_positive" in r["tags"])
    seg("hard_negative", lambda r: "hard_negative" in r["tags"])
    for prov in sorted({r["provenance"] for r in rows if r["provenance"]}):
        seg(f"provenance={prov}", lambda r, p=prov: r["provenance"] == p)
    for sid in sorted({r["scenario_id"] for r in rows if r["scenario_id"] and r["label"] == "scam"}):
        seg(f"scenario {sid}", lambda r, s=sid: r["scenario_id"] == s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
