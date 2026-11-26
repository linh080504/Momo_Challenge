#!/usr/bin/env python3
"""So nhãn thứ hai (eval/blind20.csv đã điền) với nhãn trong dataset.jsonl.

  python3 eval/tools/compare_blind20.py                      # dùng eval/blind20.csv, eval/blind20.key.csv
  python3 eval/tools/compare_blind20.py --csv path/to/filled.csv

Cột người gán điền: `label (scam|legit)`, `group`, `scenario_id`, `chac_chan (y|n)`, `ghi_chu`.
In: tỷ lệ đồng thuận nhãn, Cohen's kappa (scam/legit), đồng thuận nhóm G1–G5 trên các mẫu cùng scam, danh sách mẫu lệch.
KHÔNG sửa nhãn: mẫu lệch → ghi `docs/DECISIONS.md` và hỏi PM (quy tắc eval-qa).
Không in nhãn gốc của các mẫu đồng thuận, chỉ in mẫu lệch.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="eval/blind20.csv")
    ap.add_argument("--key", default="eval/blind20.key.csv")
    ap.add_argument("--data", default="eval/dataset.jsonl")
    args = ap.parse_args()

    data = {}
    for line in pathlib.Path(args.data).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            data[r["id"]] = r
    key = {r["blind_id"]: r["dataset_id"] for r in csv.DictReader(open(args.key, encoding="utf-8", newline=""))}
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8-sig", newline="")))
    label_col = next(c for c in rows[0] if c.startswith("label"))
    group_col = next(c for c in rows[0] if c.startswith("group"))
    sure_col = next(c for c in rows[0] if c.startswith("chac_chan"))

    pairs, blank, bad = [], [], []
    for r in rows:
        mine = (r[label_col] or "").strip().lower()
        if not mine:
            blank.append(r["blind_id"])
            continue
        if mine not in ("scam", "legit"):
            bad.append(f"{r['blind_id']}:{mine}")
            continue
        did = key[r["blind_id"]]
        pairs.append((r["blind_id"], did, mine, data[did]["label"], (r[group_col] or "").strip().upper(),
                      data[did].get("group") or "", (r[sure_col] or "").strip().lower()))
    if blank or bad:
        print(f"Chưa điền: {blank} · giá trị lạ: {bad}")
        if not pairs:
            return 2

    n = len(pairs)
    agree = sum(1 for p in pairs if p[2] == p[3])
    po = agree / n
    pm_scam = sum(1 for p in pairs if p[2] == "scam") / n
    pd_scam = sum(1 for p in pairs if p[3] == "scam") / n
    pe = pm_scam * pd_scam + (1 - pm_scam) * (1 - pd_scam)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"Mẫu so sánh: {n} · đồng thuận nhãn: {agree}/{n} = {po:.2f} · Cohen's kappa = {kappa:.2f}")
    both_scam = [p for p in pairs if p[2] == "scam" and p[3] == "scam"]
    if both_scam:
        g_ok = sum(1 for p in both_scam if p[4] == p[5])
        print(f"Đồng thuận nhóm G1–G5 trên {len(both_scam)} mẫu cả hai cùng gán scam: {g_ok}/{len(both_scam)}")
    diff = [p for p in pairs if p[2] != p[3]]
    print(f"Lệch nhãn ({len(diff)}):")
    for p in diff:
        print(f"  {p[1]} (blind {p[0]}): người gán thứ hai = {p[2]}, dataset = {p[3]}, chắc chắn = {p[6] or '?'}")
    gd = [p for p in both_scam if p[4] != p[5]]
    if gd:
        print(f"Lệch nhóm ({len(gd)}):")
        for p in gd:
            print(f"  {p[1]} (blind {p[0]}): người gán thứ hai = {p[4] or '(trống)'}, dataset = {p[5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
