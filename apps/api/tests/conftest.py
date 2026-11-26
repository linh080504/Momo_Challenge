import base64
import copy
import re
import struct
import sys
import types
import zlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.day_two import create_app

DISCLAIMER = "Kết quả do AI phân tích và có thể sai. Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền."

SAMPLE_RESULT = {
    "risk_level": "high",
    "risk_score": 92,
    "scenario_group": "G1",
    "scenario_id": "G1.2",
    "summary": "Tin nhắn mạo danh công an và yêu cầu chuyển tiền gấp vào tài khoản lạ.",
    "red_flags": [
        {"quote": "chuyển tiền vào tài khoản tạm giữ", "reason": "Cơ quan nhà nước không yêu cầu chuyển tiền.",
         "tactic": "authority"},
    ],
    "verification_questions": ["Bạn đã gọi lại số tổng đài chính thức của cơ quan này chưa?"],
    "recommended_action": "stop_and_verify",
    "entities": [{"type": "ACCOUNT", "token": "[ACCOUNT_1]", "display": "0123****89"}],
    "evidence": [{"source": "rules", "finding": "Khớp mẫu mạo danh cơ quan nhà nước.", "weight": 40}],
    "ai_disclaimer": DISCLAIMER,
    "model": "fake", "prompt_version": "v0", "latency_ms": 5,
}

VIETNAMESE = re.compile(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", re.I)


TEST_HASH_KEY = "test-only-entity-hash-key-0123456789abcdef"  # khóa giả cho test, không phải secret thật


def make_settings(tmp_path, **overrides) -> Settings:
    base = dict(database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
                entity_hash_key=TEST_HASH_KEY,
                rate_limit_analyze=1000, rate_limit_reports=1000, rate_limit_default=1000)
    base.update(overrides)
    return Settings(**base)


def make_png(extra: int = 0) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b"") + b"\0" * extra)


def make_jpeg(extra: int = 0) -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\0" * extra + b"\xff\xd9"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def assert_error(response, status: int, code: str | None = None) -> dict:
    """Mọi lỗi: đúng mã HTTP, có `error` tiếng Việt, và TUYỆT ĐỐI không có kết quả phân tích (không `low`)."""
    assert response.status_code == status, response.text
    body = response.json()
    assert isinstance(body["error"], str) and VIETNAMESE.search(body["error"]), body
    assert "risk_level" not in body and "ai_disclaimer" not in body
    if code:
        assert body["code"] == code
    return body


class AnalyzerError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class FakeAnalyzer:
    """Giả lập `app.analyzer.analyze()` bằng cách thay module trong sys.modules (monkeypatch)."""

    def __init__(self):
        self.result = copy.deepcopy(SAMPLE_RESULT)
        self.error: Exception | None = None
        self.delay = 0.0
        self.calls: list[tuple] = []

    def install(self, monkeypatch, *, sync: bool = False) -> "FakeAnalyzer":
        module = types.ModuleType("app.analyzer")
        module.AnalyzerError = AnalyzerError

        def run(text, image, mime):
            self.calls.append((text, image, mime))
            if self.error:
                raise self.error
            return self.result

        if sync:
            module.analyze = run
        else:
            async def analyze(text, image, mime):
                import asyncio
                if self.delay:
                    await asyncio.sleep(self.delay)
                return run(text, image, mime)
            module.analyze = analyze
        monkeypatch.setitem(sys.modules, "app.analyzer", module)
        return self


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def fake_analyzer(monkeypatch):
    return FakeAnalyzer().install(monkeypatch)
