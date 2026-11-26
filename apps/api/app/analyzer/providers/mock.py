"""MockProvider — deterministic, offline. Used by tests and by `LLM_PROVIDER=mock` for BE/FE integration.

Scripted mode (tests):
    MockProvider(responses=['{"risk_level": ...}', ProviderError("quota"), "not json"])
    -> each generate() call consumes the next item (str = model text, Exception = raised).
Handler mode:
    MockProvider(handler=lambda req: "...")
Default (env mode): OCR returns "" (cannot read), reasoning returns a schema-valid "uncertain" answer.

`calls` records every LLMRequest so tests can assert that only masked text was sent.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

from . import LLMProvider, LLMRequest, LLMResponse, ProviderError

_DEFAULT_REASON = {
    "risk_level": "uncertain",
    "risk_score": 30,
    "scenario_group": None,
    "scenario_id": None,
    "summary": "Mock LLM: chưa đủ thông tin để kết luận. Hãy gọi lại số tổng đài chính thức.",
    "red_flags": [],
    "verification_questions": [],
    "recommended_action": "stop_and_verify",
    "evidence": [],
    "ai_disclaimer": ("Kết quả do AI phân tích và có thể sai. "
                      "Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền."),
    "prompt_version": "v0",
}


class Provider(LLMProvider):
    name = "mock"
    supports_vision = True

    def __init__(self, model: str = "", responses: list | None = None,
                 handler: Callable[[LLMRequest], str] | None = None, delay_s: float = 0.0, **options) -> None:
        super().__init__(model=model or "mock-1", **options)
        self._responses = list(responses) if responses is not None else None
        self._handler = handler
        self._delay_s = delay_s
        self.calls: list[LLMRequest] = []

    async def generate(self, req: LLMRequest, *, timeout_s: float) -> LLMResponse:
        self.calls.append(req)
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        if self._responses is not None:
            if not self._responses:
                raise ProviderError("mock: no scripted response left")
            item = self._responses.pop(0)
            if isinstance(item, BaseException):
                raise item
            text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        elif self._handler is not None:
            text = self._handler(req)
        else:
            text = "" if req.purpose == "ocr" else json.dumps(_DEFAULT_REASON, ensure_ascii=False)
        return LLMResponse(text=text, model=self.model, latency_ms=int(self._delay_s * 1000))


MockProvider = Provider
