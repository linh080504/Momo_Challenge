"""Tạo báo cáo của người dùng. Văn bản gốc chỉ nằm trong bộ nhớ; DB chỉ nhận hash + nội dung đã mask (khi có đồng ý)."""
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Entity, Report, utcnow
from app.privacy.entities import EntityHasher
from app.privacy.mask import Masker


def _build_report(session: Session, settings: Settings, hasher: EntityHasher, text: str,
                  analysis: dict | None, consent: bool) -> Report:
    masker = Masker()
    masked_text = masker.mask(text)
    now = utcnow()
    report = Report(created_at=now, status="new", consent_contribute=consent)
    session.add(report)  # thêm sớm để autoflush khi truy vấn thực thể không cảnh báo "Report not in session"

    if analysis:
        report.risk_level = analysis.get("risk_level")
        report.risk_score = analysis.get("risk_score")
        report.scenario_group = analysis.get("scenario_group")
        report.scenario_id = analysis.get("scenario_id")
        if analysis.get("summary"):
            report.summary = masker.mask(analysis["summary"])
        if consent:
            # `quote` trích nguyên văn từ nội dung người dùng → chỉ lưu khi có đồng ý, và luôn qua mask.
            report.red_flags_masked = [
                {"quote": masker.mask(flag["quote"]), "reason": masker.mask(flag["reason"]), "tactic": flag.get("tactic")}
                for flag in analysis.get("red_flags", [])
            ]
    if consent:
        report.content_masked = masked_text
        report.content_expires_at = now + timedelta(days=settings.content_retention_days)

    # Trích thực thể SAU khi đã mask mọi chuỗi, để mapping đủ giá trị.
    for found in hasher.extract(text, masker):
        entity = session.scalar(select(Entity).where(Entity.type == found.type, Entity.value_hash == found.value_hash))
        if entity is None:
            entity = Entity(type=found.type, value_hash=found.value_hash, display=found.display,
                            status="pending", report_count=1, first_seen_at=now, last_seen_at=now)
            session.add(entity)
        else:
            entity.report_count = Entity.report_count + 1  # tăng ở phía DB, tránh mất cập nhật khi báo cáo đồng thời
            entity.last_seen_at = now
        report.entities.append(entity)

    session.commit()
    return report


def create_report(session: Session, settings: Settings, hasher: EntityHasher, *, text: str,
                  analysis: dict | None, consent: bool) -> Report:
    """Hai lần thử: nếu hai báo cáo cùng tạo một thực thể mới cùng lúc, lần thua sẽ gặp IntegrityError và thử lại."""
    for attempt in (1, 2):
        try:
            return _build_report(session, settings, hasher, text, analysis, consent)
        except IntegrityError:
            session.rollback()
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def purge_expired_content(session: Session, now: datetime | None = None) -> int:
    """Xóa nội dung đóng góp quá hạn (giữ hash thực thể + mức rủi ro). Trả số báo cáo vừa được xóa nội dung.

    Chưa có bộ lập lịch gọi hàm này — cần cron/job trước khi mở cho người dùng thật.
    """
    result = session.execute(
        update(Report)
        .where(Report.content_expires_at.is_not(None), Report.content_expires_at <= (now or utcnow()))
        .values(content_masked=None, red_flags_masked=None, content_expires_at=None)
    )
    session.commit()
    return result.rowcount
