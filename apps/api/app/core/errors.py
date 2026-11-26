"""Lỗi thống nhất: mọi lỗi trả JSON `{"error": <thông báo tiếng Việt>, "code": <mã máy đọc>}`.

Không bao giờ đưa nội dung người dùng gửi vào thông báo lỗi hay log (có thể chứa PII chưa mask).
"""
import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("tkc.errors")


class ApiError(HTTPException):
    """Kế thừa HTTPException để FastAPI không nuốt nó thành 400 khi ném từ lúc đọc body."""

    def __init__(self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str,
                   headers: dict[str, str] | None = None, **extra) -> JSONResponse:
    return JSONResponse(status_code=status_code, headers=headers,
                        content={"error": message, "code": code, **extra})


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.headers)


_HTTP_MESSAGES = {
    404: ("not_found", "Không tìm thấy đường dẫn này."),
    405: ("method_not_allowed", "Đường dẫn này không hỗ trợ phương thức đã dùng."),
}


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_MESSAGES.get(exc.status_code, ("http_error", "Yêu cầu không hợp lệ."))
    return error_response(exc.status_code, code, message, getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Chỉ trả TÊN trường lỗi, không trả lại giá trị đã gửi.
    fields = sorted({".".join(str(p) for p in err["loc"][1:] if isinstance(p, str))
                     for err in exc.errors() if len(err["loc"]) > 1} - {""})
    return error_response(422, "validation_error",
                          "Dữ liệu gửi lên không hợp lệ. Hãy kiểm tra lại các trường được nêu.",
                          fields=fields)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return error_response(500, "internal_error", "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.")


def register_error_handlers(app) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
