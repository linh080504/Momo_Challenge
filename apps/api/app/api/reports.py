from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.schemas.reports import ReportCreate, ReportCreated
from app.services.reports import create_report

router = APIRouter()


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@router.post("/v1/reports", status_code=201, response_model=ReportCreated)
def post_report(body: ReportCreate, request: Request, session: Session = Depends(get_session)) -> ReportCreated:
    """Người dùng báo cáo nội dung đáng ngờ. Không tự đưa thực thể vào danh sách đen — mọi thực thể vào ở `pending`."""
    settings = request.app.state.settings
    if not body.text.strip():
        raise ApiError(422, "missing_input", "Hãy gửi kèm nội dung cần báo cáo.")
    if len(body.text) > settings.max_text_chars:
        raise ApiError(422, "text_too_long", f"Nội dung quá dài (tối đa {settings.max_text_chars} ký tự).")
    if body.analysis is not None and request.app.state.analysis_validator.first_error(body.analysis) is not None:
        raise ApiError(422, "invalid_analysis", "Kết quả phân tích đính kèm không đúng định dạng.")

    report = create_report(session, settings, request.app.state.entity_hasher, text=body.text,
                           analysis=body.analysis, consent=body.consent_contribute)
    return ReportCreated(
        id=report.id, status=report.status, created_at=report.created_at,
        entities_linked=len(report.entities), content_stored=report.content_masked is not None,
        message="Cảm ơn bạn. Báo cáo đã được ghi nhận và sẽ do người vận hành xem xét trước khi cảnh báo cho người khác.",
    )
