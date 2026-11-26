from pydantic import BaseModel, Field


class QrParseRequest(BaseModel):
    payload: str = Field(min_length=1, max_length=4096, description="Chuỗi giải mã từ mã QR (EMVCo/VietQR)")


class QrParseResponse(BaseModel):
    """Các trường của `vietqr.VietQR` (skill vietqr)."""

    raw: str
    valid_crc: bool
    is_napas: bool
    initiation: str | None = None
    bank_bin: str | None = None
    bank_name: str | None = None
    account: str | None = None
    service: str | None = None
    amount: str | None = None
    currency: str | None = None
    country: str | None = None
    note: str | None = None
    merchant_name: str | None = None
    warnings: list[str] = []
