import re

from ..analyzer.contract import AnalyzerError
from .checks import decode_qr_image, evaluate_payment


REFUND = re.compile(r"\b(?:nhận khoản hoàn tiền|nhận hoàn tiền|hoàn tiền)\b", re.IGNORECASE)
SCAN = re.compile(r"\bquét mã(?: QR)?\b", re.IGNORECASE)
CONFLICT_REASON = "Mục đích đã chọn là nhận tiền nhưng VietQR yêu cầu chuyển tiền đi."


def review_payment(intent, payload, image, text, screenshot_text, store, signer, settings):
    review = {"intent": intent, "status": "unreadable"}
    for source, message in (("message", text), ("image", screenshot_text or "")):
        match = REFUND.search(message) or SCAN.search(message)
        if match:
            review.update(quote=match[0], quote_source=source)
            break

    if not payload:
        try:
            payload = decode_qr_image(image, settings)
        except AnalyzerError as exc:
            if exc.status in (429, 503):
                review["status"] = "unavailable"
            elif exc.status != 422:
                raise
            return review, None, None, None
    if payload.lower().startswith(("http://", "https://")):
        review["status"] = "link"
        return review, None, None, payload

    try:
        qr, payment = evaluate_payment(payload, "\n".join(filter(None, (text, screenshot_text))), store, signer)
    except AnalyzerError as exc:
        if exc.status != 422:
            raise
        review["status"] = "unsupported"
        return review, None, None, None

    if not qr.valid_crc:
        review["status"] = "invalid_crc"
        return review, qr, payment, None
    review.update(status="conflict" if intent == "receive" else "payment", amount=payment["amount"],
                  account=payment["account"], bank=payment["bank"])
    return review, qr, payment, None
