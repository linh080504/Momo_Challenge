"""Kiểm tra ảnh người dùng gửi: cỡ (413), định dạng/hỏng (415). Không bao giờ "bỏ qua" ảnh lỗi."""
import base64
import binascii

from app.core.errors import ApiError

ALLOWED_MIMES = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}

MSG_TOO_LARGE = "Ảnh quá lớn (tối đa 5 MB). Hãy chụp lại hoặc nén ảnh nhỏ hơn rồi thử lại."
MSG_BAD_TYPE = "Chỉ hỗ trợ ảnh PNG hoặc JPEG. Hãy chụp lại màn hình hoặc đổi ảnh sang JPEG."
MSG_CORRUPT = ("Không đọc được ảnh (ảnh bị hỏng hoặc sai định dạng). Hãy tải ảnh lên lại. "
               "Đừng chuyển tiền khi chưa kiểm tra xong.")


def _base64_length(n_bytes: int) -> int:
    return 4 * ((n_bytes + 2) // 3)


def decode_image(image_base64: str, image_mime: str | None, max_bytes: int) -> tuple[bytes, str]:
    """Trả (byte ảnh gốc, mime chuẩn hóa) hoặc ném ApiError 413/415/422."""
    if not image_mime or not image_mime.strip():
        raise ApiError(422, "missing_image_mime",
                       "Thiếu image_mime. Hãy gửi kèm loại ảnh (image/png hoặc image/jpeg).")

    encoded = image_base64.strip()
    # Chặn sớm theo độ dài chuỗi, trước khi tốn bộ nhớ để giải mã.
    if len(encoded) > _base64_length(max_bytes) + 8:
        raise ApiError(413, "image_too_large", MSG_TOO_LARGE)

    mime = image_mime.strip().lower()
    if mime not in ALLOWED_MIMES:
        raise ApiError(415, "unsupported_image_type", MSG_BAD_TYPE)

    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(415, "invalid_image", MSG_CORRUPT) from None
    if not data:
        raise ApiError(415, "invalid_image", MSG_CORRUPT)
    if len(data) > max_bytes:
        raise ApiError(413, "image_too_large", MSG_TOO_LARGE)

    if not data.startswith(ALLOWED_MIMES[mime]):
        raise ApiError(415, "invalid_image", MSG_CORRUPT)
    if mime == "image/png" and (len(data) < 33 or data[12:16] != b"IHDR"):
        raise ApiError(415, "invalid_image", MSG_CORRUPT)
    return data, mime
