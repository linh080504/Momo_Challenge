#!/usr/bin/env python3
"""Kiểm tra tập dữ liệu eval theo `.claude/skills/eval-harness/dataset-guide.md`.

Chạy từ gốc repo:
  python3 eval/tools/validate_dataset.py eval/dataset.jsonl
  python3 eval/tools/validate_dataset.py eval/dataset.jsonl --min-total 100 --min-images 20 --min-g17 2 --min-per-group 10
  python3 eval/tools/validate_dataset.py eval/pool/legit_pham.jsonl --pool     # file pool: cho phép tag ambiguous

Kiểm tra (mỗi lỗi in 1 dòng `FAIL <id>: ...`, exit code 1 nếu có lỗi):
  1. Mỗi dòng là JSON hợp lệ, đủ trường bắt buộc, đúng kiểu, giá trị hợp lệ.
  2. `id` không trùng (trong file và giữa các file truyền vào).
  3. Mẫu ảnh: file tồn tại, là PNG/JPEG thật (đọc byte đầu), <= 5 MB, tag `image`, `text` rỗng, có `transcript`.
  4. Mẫu văn bản: `text` không rỗng, không có tag `image`.
  5. Mẫu thật: `synthetic=false`, có `source_url` http(s) và `source_date` YYYY-MM-DD. Mẫu tổng hợp: `synthetic=true`
     CHỈ khi `provenance=synthetic` và có tag `injection` (không cần source_url); trần số lượng bằng --max-synthetic.
  6. Không trùng văn bản; không trùng ảnh (băm nội dung); không có hai mẫu văn bản gần trùng (Jaccard từ >= 0.85).
  7. Không còn PII thật: chạy pii_mask lên `text`/`transcript`; SĐT phải dạng giả 0900xxxxxx, số tài khoản phải bắt đầu 9999,
     email phải @example.com (trừ email vai trò), biển số phải 00A-NNN.00, handle phải @userNNNN (trừ handle thương hiệu);
     với mẫu `public_dataset`, mã OTP/kích hoạt dài >= 5 chữ số phải là giá trị giả (bắt đầu 100). Mã 4 chữ số không kiểm được.
  8. Mẫu có tag `ambiguous` không được nằm trong tập chấm điểm chính (chỉ cho phép khi có --pool).
  9. Cổng số lượng tùy chọn: --min-total, --min-images (chỉ đếm ảnh KHÔNG phải official_mock), --min-g17,
     --min-per-group, --max-source NAME=N.
Ảnh nằm trong eval/images/ mà không mẫu nào dùng được liệt kê dưới dạng WARN (không làm fail).
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]

REQUIRED = {
    "id": str, "text": str, "label": str, "channel": str, "tags": list,
    "synthetic": bool, "source": str, "source_date": str, "provenance": str,
}  # source_url bắt buộc với mẫu thật, kiểm riêng bên dưới
LABELS = {"scam", "legit"}
GROUPS = {"G1", "G2", "G3", "G4", "G5"}
CHANNELS = {"sms", "zalo", "messenger", "call", "web", "email"}
TAGS = {"hard_positive", "hard_negative", "injection", "image", "audio", "qr", "ambiguous",
        "seller_side", "annotated", "stitched", "template_like"}
# screenshot: ảnh chụp màn hình thật · photo: ảnh chụp màn hình điện thoại bằng máy ảnh
# official_mock: đồ họa/mô phỏng do cơ quan, ngân hàng, ví dựng lại (KHÔNG tính vào chỉ tiêu ảnh thật)
# quote: đoạn trích nguyên văn trong bài · public_dataset: bộ dữ liệu công bố (Pham & Le-Hong; vietnamese_sms_dataset)
# synthetic: mẫu do đội tự viết (chỉ injection, có trần)
# Tag stitched: văn bản do ghép nhiều trích dẫn rời trong cùng bài (báo không đăng nguyên hội thoại)
# Tag template_like: tin ngày 2026-07-24 của vietnamese_sms_dataset có chữ ký khuôn trùng với tin khác (nghi sinh theo
#   khuôn; tác giả ghi là tin thật, chưa kiểm chứng được) — báo recall riêng
PROVENANCE = {"screenshot", "photo", "official_mock", "quote", "public_dataset", "synthetic"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
FAKE_PHONE = re.compile(r"^0900\d{6}$")
# Email vai trò của tổ chức (không gắn với một cá nhân) được giữ nguyên vì thường là bằng chứng lừa đảo
# (tên miền nhái). Email có phần trước @ khác danh sách này phải là @example.com.
ROLE_MAILBOXES = {"info", "hanhchinh", "lienhe", "contact", "support", "cskh", "admin", "tuyensinh", "daotao"}
FAKE_ACCOUNT_PREFIX = "9999"

_spec = importlib.util.spec_from_file_location(
    "pii_mask", REPO / ".claude" / "skills" / "pii-guard" / "scripts" / "pii_mask.py")
pii_mask = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pii_mask)


def image_kind(path: pathlib.Path) -> str | None:
    head = path.read_bytes()[:8]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    return None


PLATE = re.compile(r"(?<![\d\w])\d{2}[A-ZĐ]{1,2}\d?[-\s]?\d{3}[.\-]?\d{2}(?![\d\w])")
FAKE_PLATE = re.compile(r"^00A-\d{3}\.00$")
HANDLE = re.compile(r"(?<![\w.@])@[A-Za-z0-9_]{4,}")
FAKE_HANDLE = re.compile(r"^@user\d{4}$")
BRAND_HANDLES = {"@viettelcskh", "@accounts"}
CODE_CTX = re.compile(
    r"(?i)((?:otp|ma xac (?:thuc|nhan|minh)|mã xác (?:thực|nhận|minh)|code|ma kich hoat|mã kích hoạt|activation)"
    r"[^\d\n]{0,60}?)(?<!\d)(?<!\d[.,])(\d{4,8})(?!\d)(?![.,]\d)")
UNIT_AFTER = re.compile(r"(?i)\s*(phut|phút|giay|giây|gio|giờ|ngay|ngày|s\b|gb|mb|d\b|đ|vnd|vnđ|k\b|tr\b|%|lan|lần)")


def extra_pii_problems(text: str, strict_codes: bool) -> list[str]:
    problems = []
    for m in PLATE.finditer(text):
        if not FAKE_PLATE.match(m.group(0)):
            problems.append("biển số xe chưa ẩn danh")
    for m in HANDLE.finditer(text):
        h = m.group(0)
        if not FAKE_HANDLE.match(h) and h.lower() not in BRAND_HANDLES:
            problems.append("handle chưa ẩn danh")
    for m in re.finditer(r"(?i)zalo\.me/(\d{6,})", text):
        if not m.group(1).startswith(FAKE_ACCOUNT_PREFIX):
            problems.append("ID Zalo trong URL chưa ẩn danh")
    for m in re.finditer(r"(?<![\d.,])\d{20,}(?!\d)", text):
        if not m.group(0).startswith(FAKE_ACCOUNT_PREFIX):
            problems.append("chuỗi >= 20 chữ số chưa ẩn danh")
    if strict_codes:
        for m in CODE_CTX.finditer(text):
            d = m.group(2)
            if (len(d) == 4 and 1900 <= int(d) <= 2100) or UNIT_AFTER.match(text[m.end(2):m.end(2) + 8]):
                continue
            # giá trị giả hợp lệ: mã giả bắt đầu 100 (OTP giả) hoặc 9999 (đã bị đổi tiếp thành số tài khoản giả)
            if len(d) >= 5 and not d.startswith(("100", FAKE_ACCOUNT_PREFIX)):
                problems.append(f"mã OTP/kích hoạt chưa ẩn danh ({len(d)} chữ số)")
    return problems


def pii_problems(text: str) -> list[str]:
    masker = pii_mask.Masker()
    masker.mask(text)
    problems = []
    for token, value in masker.mapping.items():
        kind = token.strip("[]").rsplit("_", 1)[0]
        if kind == "PHONE" and not FAKE_PHONE.match(value):
            problems.append(f"SĐT chưa ẩn danh ({value[:4]}…)")
        elif kind == "ACCOUNT" and not value.startswith(FAKE_ACCOUNT_PREFIX):
            problems.append(f"số dài chưa ẩn danh ({value[:4]}…, {len(value)} chữ số)")
        elif kind == "EMAIL" and not (value.endswith("@example.com")
                                      or value.split("@")[0].lower() in ROLE_MAILBOXES):
            problems.append("email chưa ẩn danh")
        elif kind == "CARD" and not value.startswith(FAKE_ACCOUNT_PREFIX):
            # số giả 9999… dài 16–19 chữ số có thể tình cờ qua kiểm Luhn: không coi là thẻ thật
            problems.append("số thẻ chưa ẩn danh")
        elif kind == "ID" and not set(value[:-3]) <= {"0"}:
            problems.append("CCCD/CMND chưa ẩn danh")
    return problems


def main() -> int:
    # Console Windows mặc định cp1252 không in được tiếng Việt.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--pool", action="store_true", help="file pool: cho phép tag ambiguous")
    ap.add_argument("--min-total", type=int, default=0)
    ap.add_argument("--min-images", type=int, default=0)
    ap.add_argument("--min-g17", type=int, default=0)
    ap.add_argument("--min-per-group", type=int, default=0, help="số mẫu scam THẬT tối thiểu mỗi nhóm G1–G5 (không tính tổng hợp)")
    ap.add_argument("--max-source", action="append", default=[], metavar="NAME=N",
                    help="trần số mẫu của một nguồn (vd dataset-pham-lehong=25)")
    ap.add_argument("--max-synthetic", type=int, default=None, help="trần số mẫu synthetic=true (PM cho phép 5)")
    args = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []
    rows: list[dict] = []
    ids: dict[str, str] = {}
    texts: dict[str, str] = {}
    image_hashes: dict[str, str] = {}
    used_images: set[str] = set()
    today = datetime.date.today()

    def fail(rid: str, msg: str) -> None:
        errors.append(f"FAIL {rid}: {msg}")

    for fname in args.files:
        path = pathlib.Path(fname)
        if not path.exists():
            errors.append(f"FAIL {fname}: file không tồn tại")
            continue
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
            # 1. trường bắt buộc
            for key, typ in REQUIRED.items():
                if key not in row:
                    fail(rid, f"thiếu trường `{key}`")
                elif not isinstance(row[key], typ):
                    fail(rid, f"`{key}` phải là {typ.__name__}")
            if "group" not in row:
                fail(rid, "thiếu trường `group` (null nếu legit)")
            if not isinstance(row.get("id"), str) or not row.get("id"):
                continue
            # 2. id không trùng
            if rid in ids:
                fail(rid, f"id trùng ({ids[rid]} và {where})")
            ids[rid] = where
            label, group, tags = row.get("label"), row.get("group"), row.get("tags") or []
            if label not in LABELS:
                fail(rid, f"label `{label}` không thuộc {sorted(LABELS)}")
            if label == "scam" and group not in GROUPS:
                fail(rid, f"scam phải có group G1–G5, đang là `{group}`")
            if label == "legit" and group is not None:
                fail(rid, "legit phải có group null")
            if row.get("channel") not in CHANNELS:
                fail(rid, f"channel `{row.get('channel')}` không thuộc {sorted(CHANNELS)}")
            bad_tags = [t for t in tags if t not in TAGS]
            if bad_tags:
                fail(rid, f"tag lạ {bad_tags}")
            if "ambiguous" in tags and not args.pool:
                fail(rid, "tag ambiguous không được nằm trong tập chấm điểm chính (dùng eval/pool/)")
            sid = row.get("scenario_id")
            if sid is not None and (group is None or not str(sid).startswith(str(group) + ".")):
                fail(rid, f"scenario_id `{sid}` không khớp group `{group}`")
            if label == "scam" and "hard_negative" in tags:
                fail(rid, "scam không được gắn hard_negative")
            if label == "legit" and "hard_positive" in tags:
                fail(rid, "legit không được gắn hard_positive")
            # 5. nguồn: mẫu thật hay mẫu tổng hợp (chỉ injection, có trần)
            prov = row.get("provenance")
            if row.get("synthetic") is True:
                if prov != "synthetic":
                    fail(rid, "synthetic=true chỉ hợp lệ khi provenance=synthetic")
                if "injection" not in tags:
                    fail(rid, "mẫu tổng hợp chỉ được dùng cho injection (thiếu tag injection)")
            else:
                if prov == "synthetic":
                    fail(rid, "provenance=synthetic nhưng synthetic không phải true")
                if not re.match(r"^https?://\S+$", str(row.get("source_url", ""))):
                    fail(rid, "mẫu thật phải có source_url http(s)")
            try:
                d = datetime.date.fromisoformat(str(row.get("source_date", "")))
                if d > today:
                    fail(rid, f"source_date {d} ở tương lai")
            except ValueError:
                fail(rid, f"source_date `{row.get('source_date')}` không phải YYYY-MM-DD")
            if row.get("provenance") not in PROVENANCE:
                fail(rid, f"provenance `{row.get('provenance')}` không thuộc {sorted(PROVENANCE)}")
            # 3/4. ảnh hoặc văn bản
            text = row.get("text", "")
            if "image" in row:
                if "image" not in tags:
                    fail(rid, "có trường image nhưng thiếu tag `image`")
                if text != "":
                    fail(rid, "mẫu ảnh phải có text rỗng (đáp án nằm trong ảnh, không nằm trong text)")
                if not str(row.get("transcript", "")).strip():
                    fail(rid, "mẫu ảnh thiếu `transcript`")
                rel = str(row["image"])
                if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or "\\" in rel:
                    fail(rid, f"image phải là đường dẫn tương đối dùng '/', đang là `{rel}`")
                ipath = REPO / rel
                if not ipath.is_file():
                    fail(rid, f"file ảnh không tồn tại: {rel}")
                else:
                    used_images.add(ipath.resolve().as_posix())
                    kind = image_kind(ipath)
                    if kind is None:
                        fail(rid, f"{rel} không phải PNG/JPEG (đọc byte đầu)")
                    if ipath.stat().st_size > MAX_IMAGE_BYTES:
                        fail(rid, f"{rel} lớn hơn 5 MB ({ipath.stat().st_size} byte)")
                    suffix_kind = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg"}.get(ipath.suffix.lower())
                    if kind and suffix_kind != kind:
                        fail(rid, f"đuôi file {ipath.suffix} không khớp nội dung thật ({kind})")
                    h = hashlib.sha256(ipath.read_bytes()).hexdigest()
                    if h in image_hashes:
                        fail(rid, f"ảnh trùng với {image_hashes[h]}")
                    image_hashes[h] = rid
            else:
                if "image" in tags:
                    fail(rid, "có tag `image` nhưng thiếu trường `image`")
                if not text.strip():
                    fail(rid, "text rỗng")
                key = re.sub(r"\s+", " ", text).strip().lower()
                if key in texts:
                    fail(rid, f"văn bản trùng với {texts[key]}")
                texts[key] = rid
            # 7. PII
            for field in ("text", "transcript"):
                val = str(row.get(field, ""))
                for p in pii_problems(val) + extra_pii_problems(val, strict_codes=(prov == "public_dataset")):
                    fail(rid, f"{field}: {p}")
            rows.append(row)

    # 6b. văn bản gần trùng (Jaccard theo tập từ >= 0.85)
    def words(t: str) -> set:
        return set(re.findall(r"\w+", t.lower()))
    text_rows = [(r["id"], words(r["text"])) for r in rows if "image" not in r and r.get("text")]
    for i in range(len(text_rows)):
        for j in range(i + 1, len(text_rows)):
            a, b = text_rows[i][1], text_rows[j][1]
            if a and b and len(a & b) / len(a | b) >= 0.85:
                fail(text_rows[i][0], f"gần trùng với {text_rows[j][0]} (Jaccard từ >= 0.85)")

    # 9. cổng số lượng
    n_img = sum(1 for r in rows if "image" in r)
    n_img_real = sum(1 for r in rows if "image" in r and r.get("provenance") != "official_mock")
    n_g17 = sum(1 for r in rows if r.get("scenario_id") == "G1.7")
    # cổng theo nhóm chỉ tính mẫu THẬT: mẫu tổng hợp (injection) không được dùng để "lấp" nhóm thiếu
    per_group = collections.Counter(r.get("group") for r in rows if r.get("label") == "scam" and r.get("synthetic") is not True)
    per_group_syn = collections.Counter(r.get("group") for r in rows if r.get("label") == "scam" and r.get("synthetic") is True)
    by_source = collections.Counter(r.get("source") for r in rows)
    if len(rows) < args.min_total:
        errors.append(f"FAIL tổng: {len(rows)} mẫu < {args.min_total}")
    if n_img_real < args.min_images:
        errors.append(f"FAIL ảnh thật: {n_img_real} mẫu ảnh (không tính official_mock) < {args.min_images}")
    if n_g17 < args.min_g17:
        errors.append(f"FAIL G1.7: {n_g17} mẫu < {args.min_g17}")
    if args.min_per_group:
        for g in sorted(GROUPS):
            if per_group[g] < args.min_per_group:
                errors.append(f"FAIL nhóm {g}: {per_group[g]} mẫu scam < {args.min_per_group}")
    for spec in args.max_source:
        name, _, limit = spec.partition("=")
        if by_source[name] > int(limit):
            errors.append(f"FAIL nguồn {name}: {by_source[name]} mẫu > trần {limit}")
    n_syn = sum(1 for r in rows if r.get("synthetic") is True)
    if args.max_synthetic is not None and n_syn > args.max_synthetic:
        errors.append(f"FAIL mẫu tổng hợp: {n_syn} > trần {args.max_synthetic}")

    images_dir = REPO / "eval" / "images"
    if images_dir.is_dir() and not args.pool:
        for p in sorted(images_dir.iterdir()):
            if p.is_file() and p.resolve().as_posix() not in used_images:
                warns.append(f"WARN ảnh mồ côi (không mẫu nào dùng): eval/images/{p.name}")

    # báo cáo
    label_c = collections.Counter(r.get("label") for r in rows)
    tag_c = collections.Counter(t for r in rows for t in r.get("tags", []))
    prov_c = collections.Counter(r.get("provenance") for r in rows)
    print(f"Tổng mẫu: {len(rows)} | scam: {label_c['scam']} | legit: {label_c['legit']} | ảnh: {n_img} (thật: {n_img_real}, official_mock: {n_img - n_img_real}) | G1.7: {n_g17}")
    print("Scam THẬT theo nhóm: " + ", ".join(f"{g}={per_group[g]}" for g in sorted(GROUPS))
          + " | thêm mẫu tổng hợp: " + ", ".join(f"{g}={per_group_syn[g]}" for g in sorted(GROUPS)))
    print(f"Tag: hard_positive={tag_c['hard_positive']} hard_negative={tag_c['hard_negative']} "
          f"injection={tag_c['injection']} annotated={tag_c['annotated']} stitched={tag_c['stitched']} "
          f"template_like={tag_c['template_like']} ambiguous={tag_c['ambiguous']}")
    print(f"Mẫu tổng hợp (synthetic=true): {n_syn}/{len(rows)} = {n_syn / len(rows):.1%} (báo trên slide)"
          if rows else "Mẫu tổng hợp: 0")
    print(f"Ảnh annotated (báo recall riêng): {sum(1 for r in rows if 'image' in r and 'annotated' in r.get('tags', []))} "
          f"| ảnh không chú thích: {sum(1 for r in rows if 'image' in r and 'annotated' not in r.get('tags', []))}")
    print("Nguồn gốc (provenance): " + ", ".join(f"{k}={v}" for k, v in sorted(prov_c.items(), key=lambda kv: str(kv[0]))))
    print("Theo nguồn: " + ", ".join(f"{k}={v}" for k, v in sorted(by_source.items(), key=lambda kv: str(kv[0]))))
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    print("KẾT QUẢ: " + ("FAIL" if errors else "PASS") + f" ({len(errors)} lỗi, {len(warns)} cảnh báo)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
