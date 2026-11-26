"""Vietnamese text helpers: diacritic folding with index mapping, pattern compilation, verbatim quotes.

Rules are written ONCE in lowercase accented Vietnamese and compiled twice:
  - accented version, matched against the lowercased NFC text (precise: "gấp" != "gặp");
  - folded version (no diacritics, đ->d), matched against the folded text — used when the input
    itself is written without diacritics ("chuyen tien gap"), which is common in scam SMS.
Index maps let every match be cut back out of the ORIGINAL (NFC) text, so quotes are verbatim.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Old-style tone placement -> new style (2 chars -> 2 chars, index-preserving).
_TONE_FIX = {"oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
             "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
             "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy"}
_TONE_RE = re.compile("|".join(_TONE_FIX))


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def lower_1to1(text: str) -> str:
    """Lowercase char-by-char keeping length (chars whose lowercase is longer are kept as is)."""
    out = []
    for ch in text:
        lc = ch.lower()
        out.append(lc if len(lc) == 1 else ch)
    return _TONE_RE.sub(lambda m: _TONE_FIX[m.group(0)], "".join(out))


def fold(text: str) -> tuple[str, list[int]]:
    """Remove diacritics + lowercase. Returns (folded, idx) with idx[i] = index in `text` of folded char i."""
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        if ch in "đĐ":
            out.append("d")
            idx.append(i)
            continue
        for c in unicodedata.normalize("NFD", ch):
            if unicodedata.combining(c):
                continue
            lc = c.lower()
            out.append(lc if len(lc) == 1 else c)
            idx.append(i)
    return "".join(out), idx


def fold_str(s: str) -> str:
    return fold(s)[0]


def diacritic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    marked = sum(1 for c in letters if c in "đĐ" or unicodedata.normalize("NFD", c) != c)
    return marked / len(letters)


_FORBIDDEN_ESCAPES = re.compile(r"\\[SWDB]")


@dataclass(frozen=True)
class Pattern:
    accented: re.Pattern
    folded: re.Pattern
    source: str


def compile_pattern(src: str) -> Pattern:
    """Compile a lowercase accented pattern. " ?" = optional whitespace, other " " = one or more."""
    if _FORBIDDEN_ESCAPES.search(src):
        raise ValueError(f"uppercase escapes break folding: {src}")
    body = src.replace(" ?", r"\s*").replace(" ", r"\s+")
    flags = re.DOTALL
    return Pattern(re.compile(lower_1to1(body), flags), re.compile(fold_str(body), flags), src)


class Doc:
    """One analysed text: original NFC text + accented-lower + folded views."""

    def __init__(self, text: str) -> None:
        self.text = nfc(text)
        self.lower = lower_1to1(self.text)
        self.folded, self._idx = fold(self.text)
        self.accented_mode = diacritic_ratio(self.text) >= 0.08

    def finditer(self, p: Pattern):
        """Yield (start, end) spans in self.text."""
        if self.accented_mode:
            for m in p.accented.finditer(self.lower):
                if m.end() > m.start():
                    yield m.start(), m.end(), m
        else:
            for m in p.folded.finditer(self.folded):
                if m.end() > m.start():
                    yield self._to_orig(m.start(), m.end()) + (m,)

    def _to_orig(self, s: int, e: int) -> tuple[int, int]:
        start = self._idx[s]
        end = self._idx[e - 1] + 1
        while end < len(self.text) and unicodedata.combining(self.text[end]):
            end += 1
        return start, end


_BOUNDARY = re.compile(r"[.!?;](?=\s|$)|\n")
_WORD = re.compile(r"\S+")


def quote_for(text: str, start: int, end: int, max_words: int = 14) -> str:
    """Short verbatim quote (substring of `text`) around [start, end), cut at clause boundaries."""
    left = 0
    for m in _BOUNDARY.finditer(text, 0, start):
        left = m.end()
    right = len(text)
    m = _BOUNDARY.search(text, end)
    if m:
        right = m.start()
    words = [(w.start(), w.end()) for w in _WORD.finditer(text, left, right)]
    if not words:
        return text[start:end].strip()
    if len(words) <= max_words:
        return text[words[0][0]:words[-1][1]]
    first = next((i for i, (_, we) in enumerate(words) if we > start), 0)
    last = next((i for i, (ws, _) in reversed(list(enumerate(words))) if ws < end), first)
    if last - first + 1 >= max_words:
        last = first + max_words - 1
    else:
        while last - first + 1 < max_words:
            grew = False
            if first > 0:
                first -= 1
                grew = True
            if last - first + 1 < max_words and last < len(words) - 1:
                last += 1
                grew = True
            if not grew:
                break
    return text[words[first][0]:words[last][1]]


def word_count(s: str) -> int:
    return len(s.split())
