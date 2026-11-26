"""Analyzer of "Truoc Khi Chuyen" — public contract used by the backend (BE <-> AI boundary).

    async def analyze(text: str | None, image: bytes | None, mime: str | None) -> dict
        Returns a dict that validates against .claude/skills/scam-analyzer/analysis.schema.json.
        Raises AnalyzerError(code, message) only for invalid input:
            empty_input -> 422 · unsupported_mime -> 415 · image_too_large -> 413
        Internal/LLM failures do NOT raise: they degrade to rules-only ("chế độ hạn chế") and the
        result is never "low" unless an LLM actually said so.

LLM selection from env (see providers/__init__.py): LLM_PROVIDER=none (default, rules-only) | mock | <vendor>.
"""
from __future__ import annotations

import functools
import logging

from .pipeline import AI_DISCLAIMER, fallback_result, run
from .providers import LLMProvider, chain_from_env

log = logging.getLogger("app.analyzer")

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg"}


class AnalyzerError(Exception):
    """Analyzer failure. `code` is a short machine-readable id, `message` is Vietnamese for the user."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@functools.lru_cache(maxsize=1)
def _providers() -> tuple[LLMProvider, ...]:
    chain = tuple(chain_from_env())
    log.info("analyzer providers", extra={"providers": [repr(p) for p in chain] or ["rules-only"]})
    return chain


async def analyze(text: str | None, image: bytes | None, mime: str | None) -> dict:
    if not (text or "").strip() and not image:
        raise AnalyzerError("empty_input", "Hãy dán nội dung tin nhắn hoặc tải ảnh chụp màn hình.")
    if image:
        if mime not in ALLOWED_MIME:
            raise AnalyzerError("unsupported_mime", "Chỉ nhận ảnh PNG hoặc JPEG.")
        if len(image) > MAX_IMAGE_BYTES:
            raise AnalyzerError("image_too_large", "Ảnh quá 5 MB. Hãy chụp lại hoặc cắt bớt ảnh.")
    try:
        return await run(text, image, mime, providers=list(_providers()))
    except Exception as exc:  # last-resort guard: degraded answer instead of an error page
        log.error("analyzer pipeline crashed", extra={"error": type(exc).__name__})
        return fallback_result()


__all__ = ["analyze", "AnalyzerError", "AI_DISCLAIMER"]
