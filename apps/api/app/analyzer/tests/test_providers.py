import asyncio

import pytest

from app.analyzer.providers import (LLMProvider, LLMRequest, ProviderError, chain_from_env,
                                    load_provider)
from app.analyzer.providers.mock import MockProvider


def test_default_env_is_rules_only():
    assert chain_from_env({}) == []
    assert chain_from_env({"LLM_PROVIDER": "none"}) == []


def test_mock_loaded_by_convention_with_fallback():
    chain = chain_from_env({"LLM_PROVIDER": "mock", "LLM_MODEL": "m1", "LLM_FALLBACK_MODEL": "m2"})
    assert [type(p).__name__ for p in chain] == ["Provider", "Provider"]
    assert [p.model for p in chain] == ["m1", "m2"]
    assert all(isinstance(p, LLMProvider) for p in chain)


def test_invalid_provider_name_is_rejected():
    for bad in ("../x", "os.path", "Mock", ""):
        with pytest.raises(ValueError):
            load_provider(bad)


def test_unknown_provider_module_fails_loudly():
    with pytest.raises(ModuleNotFoundError):
        load_provider("doesnotexist")


def test_mock_scripted_responses_and_errors():
    p = MockProvider(responses=["a", ProviderError("quota")])
    req = LLMRequest(system="s", user="u")
    assert asyncio.run(p.generate(req, timeout_s=1)).text == "a"
    with pytest.raises(ProviderError):
        asyncio.run(p.generate(req, timeout_s=1))
    with pytest.raises(ProviderError):  # exhausted
        asyncio.run(p.generate(req, timeout_s=1))
    assert len(p.calls) == 3
