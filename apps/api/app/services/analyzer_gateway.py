"""Cầu nối tới `app.analyzer.analyze()` (do ai-engineer sở hữu — BE chỉ gọi).

Nạp trễ (lúc có request) để API vẫn chạy được khi analyzer chưa có trên nhánh; khi đó trả 502, KHÔNG trả kết quả giả.
Mọi lỗi trả 502 kèm thông báo tiếng Việt cố định: không chuyển nguyên message của analyzer ra ngoài
(có thể chứa chi tiết nội bộ), và chỉ log tên kiểu lỗi + mã, không log đầu vào.
"""
import asyncio
import importlib
import inspect
import logging
import re

from app.core.errors import ApiError
from app.services.images import MSG_BAD_TYPE, MSG_TOO_LARGE

logger = logging.getLogger("tkc.analyzer")

MSG_FAILED = ("Hệ thống phân tích đang gặp sự cố nên chưa thể kết luận. Đừng chuyển tiền khi chưa xác minh "
              "qua số tổng đài chính thức, rồi thử lại sau.")
MSG_EMPTY = "Hãy dán nội dung tin nhắn hoặc tải ảnh lên để kiểm tra."
_SAFE_CODE = re.compile(r"^[a-z0-9_.-]{1,64}$")

# Lỗi do ĐẦU VÀO mà analyzer tự phát hiện (hợp đồng với ai-engineer) → 4xx, không phải 502. Thông báo là của BE
# (tiếng Việt cố định), không chuyển message của analyzer ra ngoài. Mã khác → 502.
ANALYZER_CLIENT_ERRORS: dict[str, tuple[int, str]] = {
    "empty_input": (422, MSG_EMPTY),
    "unsupported_mime": (415, MSG_BAD_TYPE),
    "image_too_large": (413, MSG_TOO_LARGE),
}


def _failure(code: str) -> ApiError:
    return ApiError(502, code, MSG_FAILED)


async def run_analyzer(text: str | None, image: bytes | None, mime: str | None, timeout_s: float) -> dict:
    try:
        module = importlib.import_module("app.analyzer")
        analyze = module.analyze
    except (ImportError, AttributeError):
        logger.error("analyzer module/function not available")
        raise _failure("analyzer_unavailable") from None
    analyzer_error = getattr(module, "AnalyzerError", None)

    try:
        if inspect.iscoroutinefunction(analyze):
            result = await asyncio.wait_for(analyze(text, image, mime), timeout=timeout_s)
        else:
            result = await asyncio.wait_for(asyncio.to_thread(analyze, text, image, mime), timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.error("analyzer timed out after %.1fs", timeout_s)
        raise _failure("analyzer_timeout") from None
    except Exception as exc:  # noqa: BLE001 — mọi lỗi analyzer đều quy về 502
        code = "analyzer_error"
        if analyzer_error is not None and isinstance(exc, analyzer_error):
            raw = str(getattr(exc, "code", "") or "")
            if raw in ANALYZER_CLIENT_ERRORS:
                status, message = ANALYZER_CLIENT_ERRORS[raw]
                logger.info("analyzer rejected input: code=%s", raw)
                raise ApiError(status, raw, message) from None
            code = raw if _SAFE_CODE.match(raw) else code
        logger.error("analyzer failed: %s code=%s", type(exc).__name__, code)
        raise _failure(code) from None

    if not isinstance(result, dict):
        logger.error("analyzer returned %s instead of dict", type(result).__name__)
        raise _failure("invalid_analyzer_output")
    return result
