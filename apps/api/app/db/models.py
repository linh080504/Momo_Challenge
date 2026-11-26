"""Bảng `entities`, `reports` và bảng nối `report_entities`.

Quy tắc dữ liệu (skill pii-guard, CLAUDE.md):
- `entities`: SĐT/STK/thẻ/email chỉ giữ HMAC-SHA256 + dạng đã che, không có cột giá trị gốc. Riêng tên miền
  (`type=URL`) `display` là tên miền đầy đủ — quyết định PM. Không bao giờ lưu đường dẫn/tham số của URL.
- `reports.content_masked` / `red_flags_masked` chỉ có khi người dùng đồng ý đóng góp, đã mask, hết hạn sau 30 ngày.
- `entities.status` mặc định `pending`. Chỉ quyết định của người vận hành (API ops, ngày 6) mới được đổi sang
  `approved`/`rejected`. Không có đường code nào của AI hay của POST /v1/reports được phép đổi trạng thái này.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ENTITY_STATUSES = ("pending", "approved", "rejected")
REPORT_STATUSES = ("new", "clustered", "closed")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReportEntity(Base):
    __tablename__ = "report_entities"

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("type", "value_hash", name="uq_entities_type_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(16))  # ACCOUNT | PHONE | URL | EMAIL | CARD ...
    value_hash: Mapped[str] = mapped_column(String(64))
    display: Mapped[str] = mapped_column(String(255))  # SĐT/STK đã che (0912****78); URL: tên miền đầy đủ
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    report_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reports: Mapped[list["Report"]] = relationship(secondary="report_entities", back_populates="entities")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="new", server_default="new")

    # Lấy từ kết quả phân tích người dùng đã thấy (đã validate theo analysis.schema.json)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scenario_group: Mapped[str | None] = mapped_column(String(4), nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # đã mask

    consent_contribute: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    content_masked: Mapped[str | None] = mapped_column(Text, nullable=True)  # chỉ khi consent
    red_flags_masked: Mapped[list | None] = mapped_column(JSON, nullable=True)  # chỉ khi consent
    content_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entities: Mapped[list[Entity]] = relationship(secondary="report_entities", back_populates="reports")
