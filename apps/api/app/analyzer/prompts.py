"""Load versioned prompts from prompts/<name>_<version>.md (System / User fenced blocks).

Prompt dir: env PROMPTS_DIR, else the nearest parent folder containing prompts/analyzer_v0.md
(repo root in dev). BE: the API image must ship prompts/ or set PROMPTS_DIR.
"""
from __future__ import annotations

import functools
import os
import pathlib
import re
from dataclasses import dataclass

ANALYZER_PROMPT = "analyzer_v0"
OCR_PROMPT = "ocr_v0"

_BLOCK = re.compile(r"^## (System|User)\s*\n+```text\n(.*?)\n```", re.MULTILINE | re.DOTALL)
_VERSION = re.compile(r"^prompt_version:\s*(\S+)", re.MULTILINE)
_VAR = re.compile(r"\{\{(\w+)\}\}")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    user: str

    def render(self, **values: str) -> tuple[str, str]:
        def fill(t: str) -> str:
            return _VAR.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), t)
        system, user = fill(self.system), fill(self.user)
        left = _VAR.findall(system + user)
        if left:
            raise KeyError(f"unfilled prompt variables: {sorted(set(left))}")
        return system, user


def prompts_dir() -> pathlib.Path:
    env = os.environ.get("PROMPTS_DIR")
    if env:
        return pathlib.Path(env)
    for parent in pathlib.Path(__file__).resolve().parents:
        if (parent / "prompts" / f"{ANALYZER_PROMPT}.md").exists():
            return parent / "prompts"
    raise FileNotFoundError("prompts/ not found; set PROMPTS_DIR")


@functools.lru_cache(maxsize=8)
def load(name: str) -> Prompt:
    text = (prompts_dir() / f"{name}.md").read_text(encoding="utf-8")
    blocks = {k: v for k, v in _BLOCK.findall(text)}
    if set(blocks) != {"System", "User"}:
        raise ValueError(f"{name}.md must have '## System' and '## User' ```text blocks")
    m = _VERSION.search(text)
    return Prompt(name=name, version=m.group(1) if m else name.rsplit("_", 1)[-1],
                  system=blocks["System"], user=blocks["User"])


def neutralize(content: str) -> str:
    """Stop user content from closing our XML-ish wrappers (prompt injection)."""
    return re.sub(r"</?\s*(user_content|evidence|channel|image_text)\s*>", "[thẻ bị loại]", content, flags=re.IGNORECASE)
