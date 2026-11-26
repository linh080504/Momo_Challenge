from fastapi import APIRouter, Request

from app.core.errors import ApiError
from app.qr import parse_vietqr
from app.schemas.qr import QrParseRequest, QrParseResponse

router = APIRouter()


@router.post("/v1/qr/parse", response_model=QrParseResponse)
def qr_parse(body: QrParseRequest, request: Request) -> dict:
    """Giải mã chuỗi VietQR bằng skill `vietqr` (CRC sai → `valid_crc=false` + cảnh báo, vẫn trả 200)."""
    try:
        return parse_vietqr(body.payload, request.app.state.settings.vietqr_path)
    except ValueError as exc:  # TLV hỏng/cắt cụt — thông báo gốc của skill là tiếng Việt
        raise ApiError(422, "invalid_qr", f"Không đọc được mã QR: {exc}") from None
