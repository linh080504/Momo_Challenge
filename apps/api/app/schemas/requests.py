from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AnalyzeIn(BaseModel):
    text: str = Field(default="", max_length=12000, description="Tin nhắn hoặc nội dung đi kèm.")
    image_base64: str | None = Field(default=None, description="Ảnh PNG/JPEG dạng Base64, tối đa 5 MiB trước mã hóa.")
    image_mime: str | None = Field(default=None, description="image/png hoặc image/jpeg, đi cùng image_base64.")
    image_kind: Literal["image", "receipt"] = Field(default="image", description="Ảnh chụp hoặc ảnh gốc biên lai.")
    qwen_vision: bool = Field(default=False, description="Cho phép gửi ảnh chụp đến QwenCloud để đọc chữ.")
    audio_base64: str | None = Field(
        default=None, description="WAV PCM mono 16 bit, 16 kHz dạng Base64. Tối đa 45 giây, dùng thay ảnh đính kèm.",
    )
    qr_payload: str | None = Field(default=None, max_length=2000, description="Nội dung QR đã giải mã, dạng HTTP(S) hoặc VietQR.")
    transfer_intent: Literal["receive", "pay"] | None = Field(
        default=None, description="Mục đích người dùng chọn khi kiểm tra luồng tiền của mã QR.",
    )
    url: str | None = Field(default=None, max_length=2000, description="Địa chỉ web cần đối chiếu tên miền.")
    website_html: str | None = Field(default=None, max_length=35000, description="Đoạn HTML do người dùng cung cấp để đọc tĩnh.")
    website_preview: bool = Field(default=False, description="Thử đọc bài công khai từ nguồn có trong danh mục.")
    locale: Literal["vi"] = "vi"


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class ProofIn(BaseModel):
    analysis_id: str = Field(max_length=18000)


class ReportIn(ProofIn):
    consent: Literal[True]


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    revision: int = Field(gt=0)


class ReviewIn(BaseModel):
    group: Literal["G1", "G2", "G3", "G4", "G5"]
    revision: int = Field(gt=0)


class SampleReviewIn(BaseModel):
    label: Literal["scam", "legit", "uncertain", "withdrawn"]
    revision: int = Field(ge=0)


class SplitReportIn(BaseModel):
    revision: int = Field(gt=0)


class BrandIntakeIn(BaseModel):
    source: Literal["CT_LOGS", "CSKH_REPORT", "QR_GATEWAY", "THREAT_INTEL", "QUICK_CHECK"]
    addresses: list[Annotated[str, Field(min_length=1, max_length=600)]] = Field(min_length=1, max_length=100)


class BrandEvidenceIn(BaseModel):
    html: str = Field(min_length=1, max_length=35000)
    revision: int = Field(gt=0)


class BrandDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "revoke"]
    revision: int = Field(gt=0)


class QrIn(BaseModel):
    text: str = Field(default="", max_length=12000, description="Tin nhắn đi kèm để đối chiếu người nhận hoặc đường link.")
    image_base64: str | None = Field(default=None, description="Ảnh QR PNG/JPEG dạng Base64, tối đa 5 MiB trước mã hóa.")
    image_mime: str | None = Field(default=None, description="image/png hoặc image/jpeg, đi cùng image_base64.")
    payload: str | None = Field(default=None, max_length=1024)
    confirmed: bool = False


class BrandAlert(BaseModel):
    host: str
    finding: str


class QrLinkResult(BaseModel):
    kind: Literal["url"]
    host: str
    level: Literal["low", "medium", "high"]
    signals: list[str]
    domain_age_days: int | None
    threat_intel_checked: bool
    threat_intel_match: bool
    confirmed_alert: bool
    brand_alert: BrandAlert | None = None
    risk: Literal["high", "medium", "low", "uncertain"]
    disclaimer: str


class QrPaymentResult(BaseModel):
    kind: Literal["payment"]
    bank: str | None
    bank_bin: str
    account: str
    amount: str | None
    valid_crc: bool
    mismatch: bool
    confirmed_alert: bool
    risk: Literal["low", "medium", "high", "uncertain"]
    disclaimer: str


QrResult = Annotated[QrLinkResult | QrPaymentResult, Field(discriminator="kind")]
