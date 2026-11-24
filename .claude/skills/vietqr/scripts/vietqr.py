#!/usr/bin/env python3
"""VietQR (EMVCo) parser / builder / validator — chỉ dùng thư viện chuẩn.

Dùng cho 2 việc trong sản phẩm "Trước Khi Chuyển":
  1. Đọc mã QR người dùng gửi: lấy BIN ngân hàng, số tài khoản, số tiền, nội dung,
     kiểm tra CRC (QR bị sửa tay sẽ sai CRC).
  2. Tạo "QR sạch" đúng người nhận, đúng số tiền, đúng nội dung.

CLI:
  python3 vietqr.py parse "<payload>"
  python3 vietqr.py build --bin 970436 --account 0123456789 --amount 50000 --note "TKC 123"
  python3 vietqr.py image path/to/qr.png      # cần: pip install opencv-python-headless

Lưu ý: bảng BIN bên dưới chỉ là một phần. Danh sách đầy đủ, cập nhật: https://api.vietqr.io/v2/banks
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict

NAPAS_GUID = "A000000727"
SERVICE_TO_ACCOUNT = "QRIBFTTA"
SERVICE_TO_CARD = "QRIBFTTC"

# Một phần bảng BIN (kiểm tra lại với https://api.vietqr.io/v2/banks trước khi dùng thật)
BANK_BINS = {
    "970436": "Vietcombank",
    "970415": "VietinBank",
    "970418": "BIDV",
    "970405": "Agribank",
    "970407": "Techcombank",
    "970422": "MB Bank",
    "970416": "ACB",
    "970432": "VPBank",
    "970423": "TPBank",
    "970403": "Sacombank",
}


def crc16_ccitt_false(data: str) -> str:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) — chuẩn EMVCo tag 63."""
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    length = len(value)
    if length > 99:
        raise ValueError(f"Tag {tag}: giá trị dài {length} > 99 ký tự")
    return f"{tag}{length:02d}{value}"


def parse_tlv(payload: str) -> list[tuple[str, str]]:
    """Tách chuỗi TLV thành danh sách (tag, value). Raise ValueError nếu hỏng."""
    items, i = [], 0
    while i < len(payload):
        if i + 4 > len(payload):
            raise ValueError(f"TLV bị cắt cụt tại vị trí {i}")
        tag, length_s = payload[i:i + 2], payload[i + 2:i + 4]
        if not (tag.isdigit() and length_s.isdigit()):
            raise ValueError(f"TLV không hợp lệ tại vị trí {i}: {payload[i:i + 4]!r}")
        length = int(length_s)
        value = payload[i + 4:i + 4 + length]
        if len(value) != length:
            raise ValueError(f"Tag {tag} khai báo dài {length} nhưng chỉ còn {len(value)} ký tự")
        items.append((tag, value))
        i += 4 + length
    return items


@dataclass
class VietQR:
    raw: str
    valid_crc: bool
    is_napas: bool
    initiation: str | None = None          # "static" | "dynamic"
    bank_bin: str | None = None
    bank_name: str | None = None
    account: str | None = None
    service: str | None = None             # QRIBFTTA (tài khoản) | QRIBFTTC (thẻ)
    amount: str | None = None
    currency: str | None = None
    country: str | None = None
    note: str | None = None                # nội dung chuyển khoản (tag 62.08)
    merchant_name: str | None = None
    warnings: list[str] = field(default_factory=list)


def parse(payload: str) -> VietQR:
    payload = payload.strip()
    warnings: list[str] = []
    valid_crc = False
    if len(payload) > 8 and payload[-8:-4] == "6304":
        valid_crc = crc16_ccitt_false(payload[:-4]) == payload[-4:].upper()
        if not valid_crc:
            warnings.append("CRC sai: mã QR có thể đã bị chỉnh sửa hoặc ghép tay")
    else:
        warnings.append("Không có tag 63 (CRC) ở cuối chuỗi")

    top = dict(parse_tlv(payload))
    qr = VietQR(raw=payload, valid_crc=valid_crc, is_napas=False, warnings=warnings)
    qr.initiation = {"11": "static", "12": "dynamic"}.get(top.get("01", ""), None)
    qr.currency = top.get("53")
    qr.amount = top.get("54")
    qr.country = top.get("58")
    qr.merchant_name = top.get("59")

    mai = top.get("38")
    if mai:
        sub = dict(parse_tlv(mai))
        qr.is_napas = sub.get("00", "").upper() == NAPAS_GUID
        qr.service = sub.get("02")
        bene = sub.get("01")
        if bene:
            bsub = dict(parse_tlv(bene))
            qr.bank_bin = bsub.get("00")
            qr.account = bsub.get("01")
            qr.bank_name = BANK_BINS.get(qr.bank_bin or "")
    if not qr.is_napas:
        warnings.append("Không phải VietQR/NAPAS (thiếu GUID A000000727 trong tag 38)")
    if qr.currency and qr.currency != "704":
        warnings.append(f"Mã tiền tệ {qr.currency} không phải VND (704)")
    if qr.bank_bin and not qr.bank_name:
        warnings.append(f"BIN {qr.bank_bin} không có trong bảng rút gọn; tra api.vietqr.io/v2/banks")

    add = top.get("62")
    if add:
        asub = dict(parse_tlv(add))
        qr.note = asub.get("08")
    return qr


def build(bank_bin: str, account: str, amount: int | None = None, note: str | None = None,
          to_card: bool = False) -> str:
    """Tạo payload VietQR. Có amount → QR động (12), không có → QR tĩnh (11)."""
    if not (bank_bin.isdigit() and len(bank_bin) == 6):
        raise ValueError("BIN phải gồm 6 chữ số")
    if not account.isalnum():
        raise ValueError("Số tài khoản/thẻ chỉ gồm chữ và số")
    beneficiary = _tlv("00", bank_bin) + _tlv("01", account)
    mai = _tlv("00", NAPAS_GUID) + _tlv("01", beneficiary) + _tlv(
        "02", SERVICE_TO_CARD if to_card else SERVICE_TO_ACCOUNT)
    parts = [
        _tlv("00", "01"),
        _tlv("01", "12" if amount else "11"),
        _tlv("38", mai),
        _tlv("53", "704"),
    ]
    if amount:
        if amount <= 0:
            raise ValueError("Số tiền phải > 0")
        parts.append(_tlv("54", str(int(amount))))
    parts.append(_tlv("58", "VN"))
    if note:
        parts.append(_tlv("62", _tlv("08", note)))
    body = "".join(parts) + "6304"
    return body + crc16_ccitt_false(body)


def decode_image(path: str) -> str:
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Cần cài: pip install opencv-python-headless") from exc
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"Không đọc được ảnh: {path}")
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    if not data:
        raise SystemExit("Không tìm thấy mã QR trong ảnh")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse"); p.add_argument("payload")
    b = sub.add_parser("build")
    b.add_argument("--bin", required=True); b.add_argument("--account", required=True)
    b.add_argument("--amount", type=int); b.add_argument("--note"); b.add_argument("--card", action="store_true")
    im = sub.add_parser("image"); im.add_argument("path")
    args = ap.parse_args()

    if args.cmd == "parse":
        print(json.dumps(asdict(parse(args.payload)), ensure_ascii=False, indent=2))
    elif args.cmd == "build":
        print(build(args.bin, args.account, args.amount, args.note, args.card))
    else:
        print(json.dumps(asdict(parse(decode_image(args.path))), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
