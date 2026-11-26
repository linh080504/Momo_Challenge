import re
import subprocess

from ..analyzer.contract import DISCLAIMER, AnalyzerError
from ..analyzer.pipeline.rules import match_rules
from ..analyzer.providers.ocr import image_for
from ..kit import vietqr
from ..media import media_slot, read_media
from ..privacy.entities import ACCOUNT, extract


def decode_payload(data, settings):
    if data.payload:
        return data.payload
    try:
        with media_slot():
            image = image_for(data)
            if image is None:
                raise AnalyzerError(422, "Hãy tải ảnh QR hoặc nhập chuỗi VietQR.")
            image.thumbnail((1800, 1800))
            payload = read_media("qr", image.convert("RGBA").tobytes(), settings,
                                 str(image.width), str(image.height), timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AnalyzerError(503, "Bộ đọc mã QR đang gián đoạn.") from exc
    if not payload or len(payload) > 1024:
        raise AnalyzerError(422, "Không đọc được mã QR trong ảnh.")
    return payload


def evaluate(data, store, signer, settings):
    try:
        qr = vietqr.parse(decode_payload(data, settings))
    except (ValueError, OverflowError) as exc:
        raise AnalyzerError(422, "Chuỗi VietQR không hợp lệ.") from exc
    if not (
        qr.is_napas and qr.bank_bin and re.fullmatch(r"[0-9]{6}", qr.bank_bin)
        and qr.account and re.fullmatch(r"[a-zA-Z0-9]{1,32}", qr.account)
        and qr.currency == "704" and qr.country == "VN" and qr.service == vietqr.SERVICE_TO_ACCOUNT
    ):
        raise AnalyzerError(422, "Chỉ hỗ trợ VietQR chuyển khoản vào tài khoản VND.")
    amount = qr.amount
    if amount is not None and (not re.fullmatch(r"[0-9]{1,12}", amount) or int(amount) <= 0):
        raise AnalyzerError(422, "Số tiền trong QR không hợp lệ.")
    mentioned = set(ACCOUNT.findall(data.text))
    mismatch = bool(mentioned and mentioned != {qr.account})
    keys, _, domains = extract(data.text, None, signer)
    flagged = store.matches({*keys, signer.digest("ACCOUNT", qr.account)})
    suspicious_text = any(domain["level"] != "low" for domain in domains.values()) or bool(match_rules(data.text))
    risk = (
        "high" if flagged else "medium" if mismatch or not qr.valid_crc or suspicious_text
        else "low" if qr.bank_name else "uncertain"
    )
    return qr, {
        "bank": qr.bank_name, "bank_bin": qr.bank_bin, "account": "••••" + qr.account[-4:],
        "amount": amount, "valid_crc": qr.valid_crc, "mismatch": mismatch,
        "confirmed_alert": flagged, "risk": risk, "disclaimer": DISCLAIMER,
    }


def rebuild(qr):
    try:
        return vietqr.build(qr.bank_bin, qr.account, int(qr.amount) if qr.amount else None, qr.note)
    except ValueError as exc:
        raise AnalyzerError(422, "Thông tin trong QR không thể dùng để tạo mã mới.") from exc
