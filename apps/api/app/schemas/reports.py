import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str  # nội dung đáng ngờ người dùng muốn báo cáo (xử lý trong bộ nhớ, không lưu bản gốc)
    analysis: dict[str, Any] | None = None  # kết quả /v1/analyze mà người dùng đã thấy; validate theo schema
    consent_contribute: bool = False  # "đóng góp để bảo vệ người khác": chỉ khi true mới lưu nội dung (đã mask)


class ReportCreated(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime
    entities_linked: int
    content_stored: bool
    message: str
