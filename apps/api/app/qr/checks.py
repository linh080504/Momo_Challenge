import re
import subprocess

from ..analyzer.contract import DISCLAIMER, AnalyzerError
from ..analyzer.evidence.blacklist import lookup as community_domain_match
from ..analyzer.signals.rules import match_rules
from ..analyzer.providers.ocr import image_for
from ..evidence.url_gateway import checked_destination, inspect_url
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


def evaluate(data, store, signer, settings, safe_browsing=None):
    payload = decode_payload(data, settings)
    if payload.lower().startswith(("https://", "http://")):
        try:
            destination = inspect_url(payload)
        except (ValueError, UnicodeError) as exc:
            raise AnalyzerError(422, "Liên kết trong QR không hợp lệ.") from exc
        _, _, domains = extract(data.text, payload, signer)
        keys, _, _ = extract("", payload, signer)
        flagged = store.matches(keys)
        checked, found = safe_browsing.lookup(domains) if safe_browsing else (False, False)
        community_match = any(item["lookup_allowed"] and community_domain_match(host) for host, item in domains.items())
        risk = "high" if flagged or found or any(item["level"] == "high" for item in domains.values()) else "medium" if (
            community_match or match_rules(data.text) or any(item["level"] == "medium" for item in domains.values())
        ) else "low" if destination["official_homepage"] and not data.text.strip() else "uncertain"
        link_evidence = checked_destination(destination)
        if community_match:
            link_evidence["signals"].append("Danh sách cảnh báo cộng đồng có tên miền trong nội dung đối chiếu.")
        return None, {**link_evidence, "kind": "url", "risk": risk, "confirmed_alert": flagged,
                      "threat_intel_checked": checked, "threat_intel_match": found, "disclaimer": DISCLAIMER}
    return evaluate_payment(payload, data.text, store, signer)


def evaluate_payment(payload, message, store, signer):
    try:
        qr = vietqr.parse(payload)
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
    mentioned = set(ACCOUNT.findall(message))
    mismatch = bool(mentioned and mentioned != {qr.account})
    keys, _, domains = extract(message, None, signer)
    flagged = store.matches({*keys, signer.digest("ACCOUNT", qr.account)})
    suspicious_text = any(domain["level"] != "low" for domain in domains.values()) or bool(match_rules(message))
    risk = (
        "high" if flagged else "medium" if mismatch or not qr.valid_crc or suspicious_text
        else "low" if qr.bank_name else "uncertain"
    )
    return qr, {
        "kind": "payment", "bank": qr.bank_name, "bank_bin": qr.bank_bin, "account": "••••" + qr.account[-4:],
        "amount": amount, "valid_crc": qr.valid_crc, "mismatch": mismatch,
        "confirmed_alert": flagged, "risk": risk, "disclaimer": DISCLAIMER,
    }


def rebuild(qr):
    try:
        return vietqr.build(qr.bank_bin, qr.account, int(qr.amount) if qr.amount else None, qr.note)
    except ValueError as exc:
        raise AnalyzerError(422, "Thông tin trong QR không thể dùng để tạo mã mới.") from exc
