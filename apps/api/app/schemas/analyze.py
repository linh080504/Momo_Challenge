from pydantic import BaseModel, ConfigDict


class AnalyzeRequest(BaseModel):
    """Hợp đồng `POST /v1/analyze` (docs/TASKS.md, DECISIONS 2026-11-24). Trường lạ bị bỏ qua, không gây lỗi.

    `image_mime` để kiểu `str` (không `Literal`) để mime sai ra 415 chứ không phải 422.
    """

    model_config = ConfigDict(extra="ignore")

    text: str | None = None
    image_base64: str | None = None
    image_mime: str | None = None
    locale: str | None = "vi"  # tùy chọn; thiếu hoặc null đều không lỗi
    url: str | None = None  # nhận nhưng chưa dùng đến ngày 3
