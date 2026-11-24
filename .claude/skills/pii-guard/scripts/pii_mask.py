#!/usr/bin/env python3
"""Ẩn danh dữ liệu cá nhân (PII) tiếng Việt trước khi gửi nội dung lên LLM.

- Thay SĐT, email, số thẻ, CCCD, số tài khoản, mã OTP bằng token: [PHONE_1], [ACCOUNT_1]...
- Cùng một giá trị → cùng một token (để LLM vẫn hiểu "số này xuất hiện 2 lần").
- Trả về mapping để backend tra cứu bằng chứng bằng giá trị thật (KHÔNG gửi mapping lên LLM).
- Không đụng tới số tiền ("50.000.000đ", "5 triệu", "200k").

CLI:
  python3 pii_mask.py "Chuyển 5.000.000đ vào STK 0123456789 Vietcombank, gọi 0912 345 678"
  echo "..." | python3 pii_mask.py --json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\d)(?:\+84|84|0)[ .-]?(?:3|5|7|8|9)(?:[ .-]?\d){8}(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d{4}[ -]?){3}\d{4}(?:[ -]?\d{1,3})?(?!\d)")
LONG_NUM = re.compile(r"(?<!\d)(?<!\d[.,])\d{6,19}(?!\d|[.,]\d)")
OTP_CTX = re.compile(r"(OTP|mã xác (?:thực|nhận)|ma xac (?:thuc|nhan))\D{0,15}(\d{4,8})", re.IGNORECASE)
ID_CTX = re.compile(r"(CCCD|CMND|căn cước|can cuoc|định danh)\D{0,15}(\d{9,12})", re.IGNORECASE)
AMOUNT_SUFFIX = re.compile(r"^\s*(đ|d\b|vnd|vnđ|đồng|dong|k\b|tr\b|triệu|trieu|nghìn|ngàn)", re.IGNORECASE)


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


class Masker:
    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self._rev: dict[tuple[str, str], str] = {}
        self._count: dict[str, int] = {}

    def token(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self._rev:
            self._count[kind] = self._count.get(kind, 0) + 1
            tok = f"[{kind}_{self._count[kind]}]"
            self._rev[key] = tok
            self.mapping[tok] = value
        return self._rev[key]

    def mask(self, text: str) -> str:
        # Thứ tự quan trọng: ngữ cảnh rõ (OTP, CCCD) → email → thẻ → SĐT → số dài còn lại.
        text = OTP_CTX.sub(lambda m: m.group(0).replace(m.group(2), self.token("OTP", m.group(2))), text)
        text = ID_CTX.sub(lambda m: m.group(0).replace(m.group(2), self.token("ID", m.group(2))), text)
        text = EMAIL.sub(lambda m: self.token("EMAIL", m.group(0)), text)

        def card_sub(m: re.Match) -> str:
            d = _digits(m.group(0))
            return self.token("CARD", d) if 16 <= len(d) <= 19 and _luhn_ok(d) else m.group(0)
        text = CARD.sub(card_sub, text)
        text = PHONE.sub(lambda m: self.token("PHONE", "0" + _digits(m.group(0))[-9:]), text)

        def num_sub(m: re.Match) -> str:
            after = text_ref[m.end():m.end() + 8]
            if AMOUNT_SUFFIX.match(after):
                return m.group(0)  # là số tiền, giữ nguyên
            return self.token("ACCOUNT", m.group(0)) if len(m.group(0)) >= 8 else m.group(0)
        text_ref = text
        text = LONG_NUM.sub(num_sub, text)
        return text

    def entities(self) -> list[dict]:
        """Danh sách thực thể để lưu/tra cứu: chỉ lưu hash, không lưu giá trị gốc."""
        out = []
        for tok, val in self.mapping.items():
            kind = tok.strip("[]").rsplit("_", 1)[0]
            out.append({"token": tok, "type": kind,
                        "sha256_12": hashlib.sha256(val.encode()).hexdigest()[:12]})
        return out


def mask_text(text: str) -> dict:
    m = Masker()
    masked = m.mask(text)
    return {"masked": masked, "mapping": m.mapping, "entities": m.entities()}


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--json"]
    text = " ".join(args) if args else sys.stdin.read()
    result = mask_text(text)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["masked"])


if __name__ == "__main__":
    main()
