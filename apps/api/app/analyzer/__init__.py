"""Analyzer of "Truoc Khi Chuyen" — public contract used by the backend (BE <-> AI boundary).

    async def analyze(text: str | None, image: bytes | None, mime: str | None) -> dict
        Returns a dict that validates against .claude/skills/scam-analyzer/analysis.schema.json.
        Raises AnalyzerError(code, message) on failure; BE maps it to HTTP 502 with an 'error' body.

STUB (D2-AI-00): returns a fixed, schema-valid sample so BE/FE can integrate before the real
pipeline lands. The quote is taken verbatim from the input so the "quote must appear in input"
invariant also holds for the stub.
"""
from __future__ import annotations

AI_DISCLAIMER = ("Kết quả do AI phân tích và có thể sai. "
                 "Hãy xác minh qua số tổng đài chính thức trước khi chuyển tiền.")


class AnalyzerError(Exception):
    """Analyzer failure. `code` is a short machine-readable id, `message` is Vietnamese for the user."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _stub_quote(text: str | None) -> str | None:
    words = (text or "").split()
    return " ".join(words[:8]) if words else None


async def analyze(text: str | None, image: bytes | None, mime: str | None) -> dict:
    quote = _stub_quote(text)
    red_flags = []
    if quote:
        red_flags.append({"quote": quote, "reason": "Mẫu thử (stub): chưa phân tích thật.", "tactic": "other"})
    return {
        "risk_level": "uncertain",
        "risk_score": 30,
        "scenario_group": None,
        "scenario_id": None,
        "summary": "Đây là kết quả mẫu, chưa phân tích thật. Hãy gọi lại số tổng đài chính thức trước khi chuyển tiền.",
        "red_flags": red_flags,
        "verification_questions": ["Bạn đã gọi lại số tổng đài in trên website chính thức chưa?"],
        "recommended_action": "stop_and_verify",
        "entities": [],
        "evidence": [{"source": "rules", "finding": "Stub: chưa chạy luật.", "weight": 0}],
        "ai_disclaimer": AI_DISCLAIMER,
        "model": "stub",
        "prompt_version": "stub",
        "latency_ms": 0,
    }


__all__ = ["analyze", "AnalyzerError", "AI_DISCLAIMER"]
