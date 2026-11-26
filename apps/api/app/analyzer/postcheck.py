"""Post-checks (pipeline step 6): every red_flags[].quote must appear verbatim in the input.

For image input, "input" = text read from the image (DECISIONS 2026-11-24) + the user's typed text.
The LLM sees masked text, so its quotes may contain tokens ([PHONE_1]); they are unmasked with the
server-side mapping before matching. Whitespace differences are tolerated; the returned quote is
always the exact substring of the input.
"""
from __future__ import annotations

import re

from .pii import display
from .text import nfc, word_count

MAX_QUOTE_WORDS = 20
_TOKEN = re.compile(r"\[(PHONE|ACCOUNT|EMAIL|CARD|OTP|ID)_\d+\]")


def unmask(s: str, mapping: dict[str, str]) -> str:
    return _TOKEN.sub(lambda m: mapping.get(m.group(0), m.group(0)), s)


def verify_quote(quote: str, source: str, mapping: dict[str, str]) -> str | None:
    """Return the exact input substring matching `quote`, or None if it is not in the input."""
    if not isinstance(quote, str):
        return None
    q = nfc(unmask(quote, mapping)).strip().strip("\"'“”«»")
    if not q or word_count(q) > MAX_QUOTE_WORDS or _TOKEN.search(q):
        return None
    src = nfc(source)
    if q in src:
        return q
    rx = re.compile(r"\s+".join(re.escape(w) for w in q.split()))
    m = rx.search(src)
    return m.group(0) if m else None


def humanize_tokens(s: str, mapping: dict[str, str]) -> str:
    """Replace tokens in LLM prose with partially hidden values (0123****89) — never full PII."""
    def sub(m: re.Match) -> str:
        val = mapping.get(m.group(0))
        return display(m.group(1), val) if val else m.group(0)
    return _TOKEN.sub(sub, s)


def no_absolute_safety(s: str) -> str:
    return re.sub(r"an toàn tuyệt đối", "chưa thấy dấu hiệu lừa đảo", s, flags=re.IGNORECASE)
