#!/usr/bin/env python3
"""Kiểm tra pool NHÃN THÔ (eval/pool/vsms_train.jsonl, vsms_test.jsonl): tin chưa chấm điểm, giữ nhãn gốc của tác giả.

  python3 eval/tools/validate_raw_pool.py eval/pool/vsms_train.jsonl eval/pool/vsms_test.jsonl --main eval/dataset.jsonl

Kiểm tra (mỗi lỗi in 1 dòng `FAIL <id>: ...`, exit code 1 nếu có lỗi):
  1. JSON hợp lệ, đủ trường: id, text, raw_label (0 | 1 | null), split (khớp tên file), channel=sms, synthetic=false, source,
     source_url http(s), source_date YYYY-MM-DD không ở tương lai, provenance=public_dataset, flags (danh sách cờ hợp lệ),
     duplicates_merged (số nguyên >= 0).
  2. `id` không trùng; văn bản không trùng trong pool; KHÔNG giao với tập chính `--main` (pool là phần còn lại).
  3. `raw_label` null khi và chỉ khi có cờ label_conflict.
  4. Không còn PII: cùng bộ kiểm tra của validate_dataset.py (SĐT/STK/email/thẻ/CCCD, biển số, handle, mã OTP >= 5 chữ số).
Nhãn ở đây là NHÃN THÔ của tác giả (1 = rác/lừa đảo gộp quảng cáo, cờ bạc; 0 = hợp lệ), KHÔNG dùng để chấm điểm.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.util
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("validate_dataset", HERE / "validate_dataset.py")
vd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vd)

FLAGS = {"label_conflict", "also_in_train", "template_like", "date_from_repo_commit", "label_suspect"}
REQUIRED = {"id": str, "text": str, "split": str, "channel": str, "synthetic": bool, "source": str,
            "source_url": str, "source_date": str, "provenance": str, "flags": list, "duplicates_merged": int}


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--main", default=None, help="tập chính để kiểm tra pool không giao với nó")
    ap.add_argument("--expect-total", type=int, default=None, help="tổng số tin duy nhất mong đợi (pool + phần đã vào tập chính)")
    args = ap.parse_args()

    errors: list[str] = []
    rows: list[dict] = []
    ids: dict[str, str] = {}
    texts: dict[str, str] = {}
    today = datetime.date.today()
    main_texts: dict[str, str] = {}
    n_main_vsms = 0
    if args.main:
        for line in pathlib.Path(args.main).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("text"):
                    main_texts[norm(r["text"])] = r["id"]
                if r.get("source") == "vietnamese_sms_dataset":
                    n_main_vsms += 1

    def fail(rid: str, msg: str) -> None:
        errors.append(f"FAIL {rid}: {msg}")

    for fname in args.files:
        path = pathlib.Path(fname)
        want_split = "train" if "train" in path.name else "test"
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"{path.name}:{lineno}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                fail(where, f"JSON lỗi ({e})")
                continue
            rid = str(row.get("id", where))
            for key, typ in REQUIRED.items():
                if key not in row:
                    fail(rid, f"thiếu trường `{key}`")
                elif not isinstance(row[key], typ) or (typ is int and isinstance(row[key], bool)):
                    fail(rid, f"`{key}` phải là {typ.__name__}")
            if "raw_label" not in row:
                fail(rid, "thiếu trường `raw_label`")
            if rid in ids:
                fail(rid, f"id trùng ({ids[rid]} và {where})")
            ids[rid] = where
            if row.get("raw_label") not in (0, 1, None):
                fail(rid, f"raw_label `{row.get('raw_label')}` không thuộc {{0, 1, null}}")
            flags = row.get("flags") if isinstance(row.get("flags"), list) else []
            bad = [f for f in flags if f not in FLAGS]
            if bad:
                fail(rid, f"cờ lạ {bad}")
            if (row.get("raw_label") is None) != ("label_conflict" in flags):
                fail(rid, "raw_label null khi và chỉ khi có cờ label_conflict")
            if row.get("split") != want_split:
                fail(rid, f"split `{row.get('split')}` không khớp tên file ({want_split})")
            if "also_in_train" in flags and row.get("split") != "test":
                fail(rid, "cờ also_in_train chỉ dành cho split test")
            if row.get("channel") != "sms":
                fail(rid, f"channel phải là sms, đang là `{row.get('channel')}`")
            if row.get("synthetic") is not False:
                fail(rid, "synthetic phải là false")
            if row.get("provenance") != "public_dataset":
                fail(rid, f"provenance phải là public_dataset, đang là `{row.get('provenance')}`")
            if not re.match(r"^https?://\S+$", str(row.get("source_url", ""))):
                fail(rid, "source_url phải là http(s) URL")
            try:
                if datetime.date.fromisoformat(str(row.get("source_date", ""))) > today:
                    fail(rid, "source_date ở tương lai")
            except ValueError:
                fail(rid, f"source_date `{row.get('source_date')}` không phải YYYY-MM-DD")
            text = row.get("text", "")
            if not str(text).strip():
                fail(rid, "text rỗng")
            else:
                key = norm(text)
                if key in texts:
                    fail(rid, f"văn bản trùng với {texts[key]}")
                texts[key] = rid
                if key in main_texts:
                    fail(rid, f"văn bản trùng với mẫu trong tập chính ({main_texts[key]}): pool phải là phần còn lại")
            for p in vd.pii_problems(str(text)) + vd.extra_pii_problems(str(text), strict_codes=True):
                fail(rid, f"text: {p}")
            rows.append(row)

    by = collections.Counter((r.get("split"), r.get("raw_label")) for r in rows)
    flag_c = collections.Counter(f for r in rows for f in r.get("flags", []))
    total = len(rows)
    print(f"Pool nhãn thô: {total} tin | train: {sum(v for (s, _), v in by.items() if s == 'train')} "
          f"| test: {sum(v for (s, _), v in by.items() if s == 'test')}")
    print("Theo (split, raw_label): " + ", ".join(f"{k}={v}" for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))))
    print("Cờ: " + ", ".join(f"{k}={v}" for k, v in sorted(flag_c.items())))
    if args.main:
        print(f"Tin vietnamese_sms_dataset đã vào tập chính: {n_main_vsms}")
    if args.expect_total is not None:
        print(f"Tổng pool + tập chính (nguồn vietnamese_sms_dataset) = {total + n_main_vsms} (mong đợi {args.expect_total})")
        if total + n_main_vsms != args.expect_total:
            errors.append(f"FAIL tổng: {total + n_main_vsms} != {args.expect_total}")
    for e in errors[:60]:
        print(e)
    if len(errors) > 60:
        print(f"... và {len(errors) - 60} lỗi nữa")
    print("KẾT QUẢ: " + ("FAIL" if errors else "PASS") + f" ({len(errors)} lỗi)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
