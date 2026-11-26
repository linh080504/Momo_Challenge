from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeIn(BaseModel):
    text: str = Field(default="", max_length=12000)
    image_base64: str | None = None
    image_mime: str | None = None
    url: str | None = Field(default=None, max_length=2000)
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


class QrIn(AnalyzeIn):
    payload: str | None = Field(default=None, max_length=1024)
    confirmed: bool = False
