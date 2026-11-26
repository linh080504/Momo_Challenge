"""LLM provider interface. No vendor SDK is imported here.

Adding a vendor = adding ONE file `providers/<name>.py` that defines `Provider(LLMProvider)`.
It is loaded by convention from env, no registry edit needed:

    LLM_PROVIDER=bedrock LLM_MODEL=<model-id>               # primary
    LLM_FALLBACK_PROVIDER=bedrock LLM_FALLBACK_MODEL=<id>   # optional fallback (provider defaults to primary's)
    LLM_PROVIDER=none (default)                             # rules-only mode ("che do han che")

Contract for implementations:
- `generate()` receives text that is ALREADY masked by pii-guard; never log `req.user` / images.
- Raise `ProviderError` on any vendor failure. The pipeline enforces the timeout too (asyncio.wait_for).
- Low temperature (default 0.1). Honour `json_mode` via the vendor's JSON/structured mode when available;
  the server validates against the schema anyway.
"""
from __future__ import annotations

import importlib
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


class ProviderError(Exception):
    """Vendor call failed (network, quota, refusal, bad response)."""


@dataclass(frozen=True)
class ImagePart:
    data: bytes
    mime: str  # "image/png" | "image/jpeg"


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    images: tuple[ImagePart, ...] = ()
    purpose: str = "reason"  # "ocr" (step 1, vision) | "reason" (step 5)
    temperature: float = 0.1
    max_tokens: int = 1200
    json_mode: bool = True


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: ClassVar[str] = "base"
    supports_vision: ClassVar[bool] = False

    def __init__(self, model: str, **options) -> None:
        self.model = model
        self.options = options

    @abstractmethod
    async def generate(self, req: LLMRequest, *, timeout_s: float) -> LLMResponse:
        """Return the raw model text. Must raise ProviderError on failure."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model={self.model!r})"


_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def load_provider(name: str, model: str = "", **options) -> LLMProvider:
    """Load `providers/<name>.py` and instantiate its `Provider` class."""
    if not _NAME.match(name or ""):
        raise ValueError(f"invalid provider name: {name!r}")
    module = importlib.import_module(f"{__name__}.{name}")
    cls = getattr(module, "Provider", None)
    if not (isinstance(cls, type) and issubclass(cls, LLMProvider)):
        raise ValueError(f"providers/{name}.py must define Provider(LLMProvider)")
    return cls(model=model, **options)


def chain_from_env(env: dict | None = None) -> list[LLMProvider]:
    """[primary, fallback?] from env. Empty list = rules-only mode."""
    env = os.environ if env is None else env
    primary = (env.get("LLM_PROVIDER") or "none").strip().lower()
    if primary in ("", "none", "off", "rules"):
        return []
    chain = [load_provider(primary, env.get("LLM_MODEL", ""))]
    fb_model = env.get("LLM_FALLBACK_MODEL", "")
    fb_name = (env.get("LLM_FALLBACK_PROVIDER") or primary).strip().lower()
    if fb_model or fb_name != primary:
        chain.append(load_provider(fb_name, fb_model))
    return chain


__all__ = ["ImagePart", "LLMProvider", "LLMRequest", "LLMResponse", "ProviderError",
           "chain_from_env", "load_provider"]
