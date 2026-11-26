import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.errors import ApiError
from app.schemas.analyze import AnalyzeRequest
from app.services.analyzer_gateway import MSG_FAILED, run_analyzer
from app.services.images import decode_image

router = APIRouter()
logger = logging.getLogger("tkc.analyze")


@router.post("/v1/analyze")
async def analyze(body: AnalyzeRequest, request: Request) -> JSONResponse:
    """Nhận JSON base64 → gọi analyzer → validate theo analysis.schema.json → trả.

    Lỗi đầu vào luôn là 4xx tiếng Việt; không đường nào trả `risk_level: "low"` khi không phân tích được.
    """
    settings = request.app.state.settings
    text = body.text or ""
    has_text = bool(text.strip())
    has_image = bool(body.image_base64 and body.image_base64.strip())

    if not has_text and not has_image:
        raise ApiError(422, "missing_input", "Hãy dán nội dung tin nhắn hoặc tải ảnh lên để kiểm tra.")
    if len(text) > settings.max_text_chars:
        raise ApiError(422, "text_too_long",
                       f"Nội dung quá dài (tối đa {settings.max_text_chars} ký tự). Hãy chỉ dán phần đáng ngờ.")

    image, mime = (decode_image(body.image_base64, body.image_mime, settings.max_image_bytes)
                   if has_image else (None, None))

    started = time.perf_counter()
    result = await run_analyzer(text if has_text else None, image, mime, settings.analyze_timeout_s)

    problem = request.app.state.analysis_validator.first_error(result)
    if problem is not None:
        logger.error("analyzer output rejected by schema at %s", problem)
        raise ApiError(502, "invalid_analyzer_output", MSG_FAILED)

    # Chỉ log metadata, không log nội dung đầu vào hay kết quả (có thể chứa trích dẫn chưa mask).
    logger.info("analyze ok input=%s latency_ms=%d risk=%s",
                "text+image" if has_text and has_image else "image" if has_image else "text",
                (time.perf_counter() - started) * 1000, result.get("risk_level"))
    return JSONResponse(result)
