#!/usr/bin/env python3
"""Chạy bộ đánh giá (eval) cho analyzer của "Trước Khi Chuyển". Chỉ dùng thư viện chuẩn.

Dữ liệu: JSONL, mỗi dòng một mẫu:
  {"id": "s001", "text": "...", "label": "scam"|"legit", "group": "G1".."G5"|null,
   "channel": "sms|zalo|messenger|call|web|email", "tags": ["injection", "hard_negative"], "synthetic": false,
   "image": "eval/images/s001.png"}            # "image" không bắt buộc

Mẫu có "image" (đường dẫn file PNG/JPEG ≤ 5 MB, tính từ thư mục chạy lệnh) là mẫu ẢNH (input_type = image):
  POST {"text": <text hoặc "">, "image_base64": "...", "image_mime": "image/png|image/jpeg"}
Mẫu không có "image" là mẫu VĂN BẢN (input_type = text):
  POST {"text": ...}
"image_mime" lấy theo byte đầu của file (không tin đuôi file). Đọc/mã hóa ảnh xong mới bắt đầu bấm giờ,
nên độ trễ chỉ gồm thời gian gọi API.

Chế độ chạy:
  --baseline                 bộ lọc từ khóa (mốc "không có AI"). Mẫu ảnh = "không đọc được" → risk_level low
  --endpoint URL             gọi API thật, nhận JSON theo analysis.schema.json

Cổng chất lượng (exit code 1 nếu không đạt):
  --min-recall 0.90  --max-fpr 0.10  --max-p95-text 6  --max-p95-image 12
  [--compare eval/reports/latest.json --max-drop 0.02]
Cổng p95 của một loại chỉ được đánh giá khi có mẫu loại đó; báo cáo ghi rõ khi không có.

Ví dụ:
  python3 run_eval.py --data eval/dataset.example.jsonl --baseline --tag baseline
  python3 run_eval.py --data eval/dataset.jsonl --endpoint "$ANALYZER_URL/v1/analyze" --tag v3-prompt --compare eval/reports/latest.json
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import re
import statistics
import sys
import time
import urllib.request

POSITIVE_DEFAULT = {"high", "medium", "uncertain"}  # "chưa chắc" vẫn tính là cảnh báo (an toàn hơn)

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB tính trên byte ảnh gốc, trước khi mã hóa base64
IMAGE_MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"))

BASELINE_RULES = [
    (r"\b(otp|mã xác (thực|nhận))\b", "G5"),
    (r"(công an|viện kiểm sát|tòa án|phạt nguội|lệnh bắt|điều tra)", "G1"),
    (r"(nợ cước|cắt điện|bảo hiểm xã hội|bhxh|cài (đặt )?ứng dụng)", "G1"),
    (r"(việc nhẹ lương cao|cộng tác viên|ctv|làm nhiệm vụ|hoa hồng|nạp tiền)", "G3"),
    (r"(lợi nhuận|đầu tư|tiền ảo|forex|chứng khoán|lãi suất)", "G3"),
    (r"(đặt cọc|cọc trước|bill|biên lai)", "G4"),
    (r"(cấp cứu|tai nạn|chuyển gấp|mượn tiền|vay gấp)", "G2"),
    (r"(trúng thưởng|quà tặng|nhận quà)", "G4"),
    (r"(https?://|bit\.ly|\.xyz|\.top|\.cc)", "G5"),
]


def input_type(row: dict) -> str:
    """Loại đầu vào của mẫu: có trường "image" → image, ngược lại → text."""
    return "image" if row.get("image") else "text"


def baseline_predict(text: str) -> dict:
    t = text.lower()
    for pattern, group in BASELINE_RULES:
        if re.search(pattern, t):
            return {"risk_level": "high", "scenario_group": group}
    return {"risk_level": "low", "scenario_group": None}


def baseline_predict_row(row: dict) -> dict:
    """Mốc từ khóa không đọc được ảnh → mẫu ảnh luôn là low (kể cả khi mẫu có kèm text)."""
    if input_type(row) == "image":
        return {"risk_level": "low", "scenario_group": None}
    return baseline_predict(row["text"])


def load_image(path: str) -> tuple[str, str]:
    """Đọc file ảnh, trả (base64, mime). Ném ValueError/OSError nếu ảnh không hợp lệ."""
    p = pathlib.Path(path)
    size = p.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ValueError(f"ảnh {path} nặng {size} byte, vượt giới hạn {MAX_IMAGE_BYTES} byte (5 MB)")
    data = p.read_bytes()
    for magic, mime in IMAGE_MAGIC:
        if data.startswith(magic):
            return base64.b64encode(data).decode("ascii"), mime
    raise ValueError(f"ảnh {path} không phải PNG/JPEG (đọc theo byte đầu của file)")


def build_payload(row: dict) -> dict:
    """Thân JSON gửi lên /v1/analyze. Mẫu không có "image" giữ nguyên dạng cũ {"text": ...}."""
    if input_type(row) == "text":
        return {"text": row["text"]}
    image_b64, image_mime = load_image(row["image"])
    return {"text": row.get("text") or "", "image_base64": image_b64, "image_mime": image_mime}


def endpoint_predict(url: str, payload: dict, timeout: float, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.load(r)
        if not isinstance(result, dict) or result.get("risk_level") not in {"high", "medium", "uncertain", "low"}:
            raise ValueError("API chưa trả risk_level hợp lệ")
        return result


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p / 100 * (len(s) - 1))))
    return s[k]


def _p95_or_none(values: list[float]) -> float | None:
    return round(pct(values, 95), 3) if values else None


def _fmt_p95(value: float | None, n: int) -> str:
    return f"{value}s (n={n})" if value is not None else f"không có mẫu (n={n})"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # console Windows mặc định cp1252 không in được tiếng Việt
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline", action="store_true")
    mode.add_argument("--endpoint")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--out", default="eval/reports")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--positive", default=",".join(sorted(POSITIVE_DEFAULT)))
    ap.add_argument("--min-recall", type=float, default=0.90)
    ap.add_argument("--max-fpr", type=float, default=0.10)
    ap.add_argument("--max-p95-text", type=float, default=6.0, help="p95 tối đa (giây) cho mẫu văn bản")
    ap.add_argument("--max-p95-image", type=float, default=12.0, help="p95 tối đa (giây) cho mẫu ảnh")
    ap.add_argument("--compare")
    ap.add_argument("--token-env", help="Tên biến môi trường giữ token tài khoản test của API")
    ap.add_argument("--max-drop", type=float, default=0.02)
    args = ap.parse_args(argv)
    token = os.environ.get(args.token_env) if args.token_env else None
    if args.token_env and not token:
        ap.error("Biến môi trường token chưa được đặt")

    positive = {p.strip() for p in args.positive.split(",") if p.strip()}
    rows = [json.loads(line) for line in pathlib.Path(args.data).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    results, errors = [], []
    latencies: dict[str, list[float]] = {"text": [], "image": []}

    for row in rows:
        kind = input_type(row)
        latency = None  # None = chưa gọi API (vd. lỗi đọc ảnh) → không đưa vào p95
        try:
            if args.baseline:
                t0 = time.perf_counter()
                pred = baseline_predict_row(row)
                latency = time.perf_counter() - t0
            else:
                payload = build_payload(row)  # đọc + mã hóa ảnh trước, không tính vào độ trễ
                t0 = time.perf_counter()
                try:
                    pred = endpoint_predict(args.endpoint, payload, args.timeout, token)
                finally:
                    latency = time.perf_counter() - t0
        except Exception as exc:  # lỗi mạng/timeout/ảnh hỏng tính là lỗi, KHÔNG tính là "an toàn"
            errors.append({"id": row.get("id"), "input_type": kind, "error": str(exc)[:200]})
            pred = {"risk_level": "error", "scenario_group": None}
        if latency is not None:
            latencies[kind].append(latency)
        flagged = pred.get("risk_level") in positive
        results.append({"id": row.get("id"), "input_type": kind, "label": row["label"], "group": row.get("group"),
                        "tags": row.get("tags", []), "pred": pred.get("risk_level"),
                        "pred_group": pred.get("scenario_group"), "flagged": flagged})

    scams = [r for r in results if r["label"] == "scam"]
    legits = [r for r in results if r["label"] == "legit"]
    tp = sum(r["flagged"] for r in scams)
    fp = sum(r["flagged"] for r in legits)
    recall = tp / len(scams) if scams else 0.0
    fpr = fp / len(legits) if legits else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    group_hits = [r for r in scams if r["flagged"] and r["group"]]
    group_acc = (sum(r["pred_group"] == r["group"] for r in group_hits) / len(group_hits)) if group_hits else 0.0
    per_group = {}
    for g in sorted({r["group"] for r in scams if r["group"]}):
        rs = [r for r in scams if r["group"] == g]
        per_group[g] = {"n": len(rs), "recall": round(sum(r["flagged"] for r in rs) / len(rs), 3)}
    injection = [r for r in scams if "injection" in r["tags"]]
    all_latencies = latencies["text"] + latencies["image"]
    n_text = sum(r["input_type"] == "text" for r in results)
    n_image = sum(r["input_type"] == "image" for r in results)

    summary = {
        "tag": args.tag, "mode": "baseline" if args.baseline else "endpoint",
        "time": dt.datetime.now().isoformat(timespec="seconds"), "n": len(results),
        "n_scam": len(scams), "n_legit": len(legits), "n_text": n_text, "n_image": n_image,
        "recall_scam": round(recall, 3), "false_positive_rate": round(fpr, 3), "precision": round(precision, 3),
        "group_accuracy": round(group_acc, 3), "per_group": per_group,
        "injection_recall": round(sum(r["flagged"] for r in injection) / len(injection), 3) if injection else None,
        "latency_p50_s": round(statistics.median(all_latencies), 3) if all_latencies else 0,
        "p95_text": _p95_or_none(latencies["text"]), "p95_image": _p95_or_none(latencies["image"]),
        # p95 gộp chỉ để tương thích hook session-context; KHÔNG dùng làm cổng vì trộn hai phân phối khác nhau
        "latency_p95_s": round(pct(all_latencies, 95), 3), "errors": len(errors),
        "missed_scams": [r["id"] for r in scams if not r["flagged"]],
        "false_alarms": [r["id"] for r in legits if r["flagged"]],
    }

    gates = {
        f"recall ≥ {args.min_recall}": recall >= args.min_recall,
        f"FPR ≤ {args.max_fpr}": fpr <= args.max_fpr,
    }
    if summary["p95_text"] is not None:
        gates[f"p95 văn bản ≤ {args.max_p95_text}s"] = summary["p95_text"] <= args.max_p95_text
    if summary["p95_image"] is not None:
        gates[f"p95 ảnh ≤ {args.max_p95_image}s"] = summary["p95_image"] <= args.max_p95_image
    gates["không có lỗi gọi API"] = not errors
    if args.compare and pathlib.Path(args.compare).exists():
        prev = json.loads(pathlib.Path(args.compare).read_text(encoding="utf-8"))
        prev = prev.get("summary", prev)
        drop = prev.get("recall_scam", 0) - recall
        summary["recall_delta_vs_prev"] = round(-drop, 3)
        gates[f"recall không giảm quá {args.max_drop} so với {prev.get('tag')}"] = drop <= args.max_drop
    summary["gates"] = gates
    summary["passed"] = all(gates.values())

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"{stamp}-{args.tag}.json").write_text(json.dumps({"summary": summary, "results": results,
                                                              "errors": errors}, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    (out / "last_run.json").write_text(summary_json, encoding="utf-8")
    if summary["passed"] and not args.baseline:
        (out / "latest.json").write_text(summary_json, encoding="utf-8")

    md = [f"# Eval `{args.tag}` — {summary['time']}", "",
          f"- Mẫu: {summary['n']} ({summary['n_scam']} lừa đảo, {summary['n_legit']} hợp lệ)"
          f" · Văn bản: {n_text} · Ảnh: {n_image}",
          f"- Recall lừa đảo: **{summary['recall_scam']}** · Báo nhầm (FPR): **{summary['false_positive_rate']}**"
          f" · Precision: {summary['precision']} · Đúng nhóm thủ đoạn: {summary['group_accuracy']}",
          f"- Độ trễ p50 (tất cả): {summary['latency_p50_s']}s"
          f" · p95 văn bản: {_fmt_p95(summary['p95_text'], len(latencies['text']))}"
          f" · p95 ảnh: {_fmt_p95(summary['p95_image'], len(latencies['image']))}"
          f" · Lỗi: {summary['errors']}",
          f"- Recall theo nhóm: {json.dumps(per_group, ensure_ascii=False)}",
          f"- Bỏ sót: {', '.join(summary['missed_scams']) or 'không'}",
          f"- Báo nhầm: {', '.join(summary['false_alarms']) or 'không'}"]
    if args.baseline and n_image:
        md.append(f"- Lưu ý baseline: {n_image} mẫu ảnh tính là \"không đọc được\" (risk_level low).")
    if not n_image:
        md.append("- Lưu ý: không có mẫu ảnh trong tập này, cổng p95 ảnh không được đánh giá.")
    if not n_text:
        md.append("- Lưu ý: không có mẫu văn bản trong tập này, cổng p95 văn bản không được đánh giá.")
    if errors:
        md.append(f"- Mẫu lỗi: {', '.join(str(e['id']) for e in errors)}")
    md += ["", "## Cổng chất lượng"]
    md += [f"- [{'x' if ok else ' '}] {name}" for name, ok in gates.items()]
    md.append(f"\n**KẾT QUẢ: {'ĐẠT' if summary['passed'] else 'CHƯA ĐẠT'}**")
    (out / f"{stamp}-{args.tag}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
