#!/usr/bin/env python3
"""Ẩn danh văn bản mẫu eval: pii_mask.py -> giá trị giả NHẤT QUÁN.

- Phát hiện SĐT, số tài khoản, email, OTP, CCCD bằng `.claude/skills/pii-guard/scripts/pii_mask.py`.
- Cùng một giá trị thật -> cùng một giá trị giả trong TOÀN BỘ tập dữ liệu (nhờ bảng ánh xạ).
- Bảng ánh xạ chứa giá trị THẬT nên PHẢI nằm ngoài repo (tham số `path` của Registry). Không commit.
- Không đụng tới tên miền, link, số tiền (pii_mask đã loại số tiền), hotline công khai 1800/1900.
- Giữ nguyên token do tác giả bộ dữ liệu công khai đặt ([MONEY] [NUMBER] [DATE] [TIME] [NAME]...).
- Tên người: truyền `names={"Tên thật": "Nguyễn Văn A"}`; script chỉ thay chuỗi đúng từng ký tự.

Giá trị giả dễ nhận ra là giả:
  SĐT       0900 000 NNN  (vd 0900000001)
  Tài khoản 9999 + số thứ tự, giữ nguyên độ dài
  OTP/mã    100000 + số thứ tự, giữ nguyên độ dài
  Email     nguoidung<N>@example.com
  CCCD      000000000000 + số thứ tự, giữ nguyên độ dài
  Biển số   00A-NNN.00
  Handle    @userNNNN

`anonymize_extended` thêm các bước pii_mask không có: mã OTP/kích hoạt đứng xa chữ "OTP", biển số xe, handle
@..., họ tên viết hoa kiểu họ Việt + 1–3 chữ (trừ tên địa danh/đường phố). Dùng cho dữ liệu công khai chưa duyệt tay.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "pii_mask", REPO / ".claude" / "skills" / "pii-guard" / "scripts" / "pii_mask.py")
pii_mask = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pii_mask)

FAKE_PHONE_PREFIX = "0900"
FAKE_ACCOUNT_PREFIX = "9999"

HOTLINE = re.compile(r"(?<!\d)1[89]00\d{4,6}(?!\d)")
PLATE = re.compile(r"(?<![\d\w])\d{2}[A-ZĐ]{1,2}\d?[-\s]?\d{3}[.\-]?\d{2}(?![\d\w])")
HANDLE = re.compile(r"(?<![\w.@])@[A-Za-z0-9_]{4,}")
HANDLE_KEEP = {"@viettelcskh", "@accounts"}  # tài khoản thương hiệu công khai
CODE_CTX = re.compile(
    r"(?i)((?:otp|ma xac (?:thuc|nhan|minh)|mã xác (?:thực|nhận|minh)|code|ma kich hoat|mã kích hoạt|activation)"
    r"[^\d\n]{0,60}?)(?<!\d)(?<!\d[.,])(\d{4,8})(?!\d)(?![.,]\d)")
_SUR = (r"(?:Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý"
        r"|Nguyen|Tran|Pham|Hoang|Huynh|Phan|Duong)")
_CAP = r"[A-ZÀ-ỸĐ][a-zà-ỹđ]+"
SURNAME_NAME = re.compile(rf"(?<![\w\[/])({_SUR})((?:\s+{_CAP}){{1,3}})(?![\w\]])")
_PLACE_BEFORE = re.compile(r"(?i)(đường|duong|phố|pho|quận|quan|phường|phuong|ql|tỉnh|tinh|tp\.?|thành phố|thanh pho)\W{0,3}$")
_PLACE_SPAN = re.compile(r"Hồ Chí Minh|Ho Chi Minh|Hoàng Sa|Hoang Sa|Trường Sa")
ZALO_ID = re.compile(r"(?i)(zalo\.me/)(\d{6,})")
LONG_ID = re.compile(r"(?<![\d.,])\d{20,}(?![\d])")
_UNIT_AFTER = re.compile(r"(?i)\s*(phut|phút|giay|giây|gio|giờ|ngay|ngày|s\b|gb|mb|d\b|đ|vnd|vnđ|k\b|tr\b|%|lan|lần)")


class Registry:
    """Bảng ánh xạ giá trị thật -> giả, lưu ra file JSON ngoài repo."""

    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        self.data: dict[str, dict[str, str]] = {}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def fake(self, kind: str, value: str) -> str:
        table = self.data.setdefault(kind, {})
        if value in table:
            return table[value]
        n = len(table) + 1
        if kind == "PHONE":
            fake = f"{FAKE_PHONE_PREFIX}{n:06d}"
        elif kind == "ACCOUNT":
            width = max(len(value), 8)
            fake = FAKE_ACCOUNT_PREFIX + str(n).zfill(width - len(FAKE_ACCOUNT_PREFIX))
        elif kind == "OTP":
            fake = str(10 ** (len(value) - 1) + n)
        elif kind == "ID":
            fake = str(n).zfill(len(value))
        elif kind == "EMAIL":
            fake = f"nguoidung{n}@example.com"
        elif kind == "PLATE":
            fake = f"00A-{n:03d}.00"
        elif kind == "HANDLE":
            fake = f"@user{n:04d}"
        else:  # CARD và loại khác
            fake = FAKE_ACCOUNT_PREFIX + str(n).zfill(max(len(value), 8) - len(FAKE_ACCOUNT_PREFIX))
        table[value] = fake
        return fake

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")


def anonymize(text: str, reg: Registry, names: dict[str, str] | None = None,
              keep_kinds: tuple[str, ...] = ()) -> str:
    """Trả văn bản đã thay SĐT/STK/OTP/email/CCCD/tên bằng giá trị giả.

    `keep_kinds`: loại giữ nguyên giá trị gốc, ví dụ ("OTP",) cho mã OTP trong tin lừa đảo mà ảnh
    vẫn hiện nguyên (mã do kẻ lừa đảo gửi, không phải dữ liệu cá nhân) để bản chép lại khớp ảnh.
    Hotline công khai 1800/1900 được giữ nguyên.
    """
    for real, fake in (names or {}).items():
        text = text.replace(real, fake)
    hot: list[str] = []

    def protect(m: re.Match) -> str:
        hot.append(m.group(0))
        return f"\x00H{len(hot) - 1}\x00"
    text = HOTLINE.sub(protect, text)
    masker = pii_mask.Masker()
    masked = masker.mask(text)
    for token, value in masker.mapping.items():
        kind = token.strip("[]").rsplit("_", 1)[0]
        replacement = value if kind in keep_kinds else reg.fake(kind, value)
        masked = masked.replace(token, replacement)
    return re.sub(r"\x00H(\d+)\x00", lambda m: hot[int(m.group(1))], masked)


def anonymize_extended(text: str, reg: Registry, counters: dict | None = None) -> str:
    """anonymize + mã OTP xa chữ OTP + biển số + handle + họ tên kiểu Việt. `counters` đếm số lần thay."""
    c = counters if counters is not None else {}

    def bump(k: str) -> None:
        c[k] = c.get(k, 0) + 1

    def code_sub(m: re.Match) -> str:
        digits = m.group(2)
        after = text[m.end(2):m.end(2) + 8]
        # không coi năm (1900–2100) hay số kèm đơn vị thời gian/dung lượng/tiền là mã
        if (len(digits) == 4 and 1900 <= int(digits) <= 2100) or _UNIT_AFTER.match(after):
            return m.group(0)
        bump("code")
        return m.group(1) + reg.fake("OTP", digits)
    text = CODE_CTX.sub(code_sub, text)

    def plate_sub(m: re.Match) -> str:
        bump("plate")
        return reg.fake("PLATE", m.group(0))
    text = PLATE.sub(plate_sub, text)

    def handle_sub(m: re.Match) -> str:
        if m.group(0).lower() in HANDLE_KEEP:
            return m.group(0)
        bump("handle")
        return reg.fake("HANDLE", m.group(0))
    text = HANDLE.sub(handle_sub, text)

    def name_sub(m: re.Match) -> str:
        span = m.group(0)
        if _PLACE_SPAN.search(span) or _PLACE_BEFORE.search(text[max(0, m.start() - 14):m.start()]):
            return span
        # tên không dấu chỉ coi là tên người nếu có >= 2 chữ sau họ dài; tránh bắt "Do/Ho/Le" ngẫu nhiên
        if not re.search(r"[À-ỹđĐ]", span) and len(m.group(2).split()) < 2:
            return span
        bump("name")
        return "[NAME]"
    text = SURNAME_NAME.sub(name_sub, text)
    # OTP đã được xử lý ở trên (kể cả ngoại lệ năm/đơn vị): không để pii_mask mask lại giá trị giả
    text = anonymize(text, reg, keep_kinds=("OTP",))

    # Sau bước chính (để không che hai lần): ID Zalo trong URL và chuỗi >= 20 chữ số mà pii_mask (tối đa 19) bỏ qua
    def zalo_sub(m: re.Match) -> str:
        if m.group(2).startswith(FAKE_ACCOUNT_PREFIX):
            return m.group(0)
        bump("zalo_id")
        return m.group(1) + reg.fake("ACCOUNT", m.group(2))
    text = ZALO_ID.sub(zalo_sub, text)

    def long_sub(m: re.Match) -> str:
        if m.group(0).startswith(FAKE_ACCOUNT_PREFIX):
            return m.group(0)
        bump("long_id")
        return reg.fake("ACCOUNT", m.group(0))
    return LONG_ID.sub(long_sub, text)


def leaked_values(text: str, reg: Registry, kept: tuple[str, ...] = ()) -> list[str]:
    """Giá trị thật còn sót trong `text` (dùng kiểm tra sau khi ẩn danh).

    Khớp NGUYÊN giá trị (không tính chuỗi con của số/từ dài hơn) để mã 4 chữ số không báo nhầm
    trong id hay URL. Chỉ truyền các trường nội dung (`text`, `transcript`), không truyền cả dòng JSON.
    `kept`: giá trị giữ nguyên có chủ ý (vd mã OTP của tin lừa đảo mà ảnh vẫn hiện).
    """
    found = []
    fakes = {fake for table in reg.data.values() for fake in table.values()}
    for table in reg.data.values():
        for real in table:
            # bỏ qua giá trị giữ có chủ ý, và số trùng với một giá trị GIẢ (mã 4 chữ số giả có thể
            # trùng mã thật khác; không phân biệt được nên không báo)
            if not real or real in kept or real in fakes:
                continue
            if re.search(rf"(?<![\w]){re.escape(real)}(?![\w])", text):
                found.append(real)
    return found


if __name__ == "__main__":
    import sys
    reg = Registry(sys.argv[2] if len(sys.argv) > 2 else "registry.tmp.json")
    print(anonymize_extended(sys.argv[1], reg))
