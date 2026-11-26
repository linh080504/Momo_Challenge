#!/usr/bin/env python3
"""Ẩn danh văn bản mẫu eval: pii_mask.py -> giá trị giả NHẤT QUÁN.

- Phát hiện SĐT, số tài khoản, email, OTP, CCCD bằng `.claude/skills/pii-guard/scripts/pii_mask.py`.
- Cùng một giá trị thật -> cùng một giá trị giả trong TOÀN BỘ tập dữ liệu (nhờ bảng ánh xạ).
- Bảng ánh xạ chứa giá trị THẬT nên PHẢI nằm ngoài repo (tham số `registry_path`). Không commit.
- Không đụng tới tên miền, link, số tiền (pii_mask đã loại số tiền).
- Tên người: truyền `names={"Tên thật": "Nguyễn Văn A"}`; script chỉ thay chuỗi đúng từng ký tự.

Giá trị giả dễ nhận ra là giả:
  SĐT      0900 000 NNN  (vd 0900000001)
  Tài khoản 9999 + số thứ tự, giữ nguyên độ dài
  OTP       100000 + số thứ tự, giữ nguyên độ dài
  Email     nguoidung<N>@example.com
  CCCD      000000000000 + số thứ tự, giữ nguyên độ dài
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "pii_mask", REPO / ".claude" / "skills" / "pii-guard" / "scripts" / "pii_mask.py")
pii_mask = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pii_mask)

FAKE_PHONE_PREFIX = "0900"
FAKE_ACCOUNT_PREFIX = "9999"


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
    """
    for real, fake in (names or {}).items():
        text = text.replace(real, fake)
    masker = pii_mask.Masker()
    masked = masker.mask(text)
    for token, value in masker.mapping.items():
        kind = token.strip("[]").rsplit("_", 1)[0]
        replacement = value if kind in keep_kinds else reg.fake(kind, value)
        masked = masked.replace(token, replacement)
    return masked


def leaked_values(text: str, reg: Registry) -> list[str]:
    """Giá trị thật còn sót trong `text` (dùng kiểm tra sau khi ẩn danh)."""
    found = []
    for table in reg.data.values():
        for real in table:
            if real and real in text:
                found.append(real)
    return found


if __name__ == "__main__":
    import sys
    reg = Registry(sys.argv[2] if len(sys.argv) > 2 else "registry.tmp.json")
    print(anonymize(sys.argv[1], reg))
