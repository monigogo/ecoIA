from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.llm import build_default_chat_model


@pytest.mark.parametrize(
    ("provider", "api_key", "model_name"),
    [
        ("nvidia", "nvapi-test-key", "nvidia/nemotron-3-super-120b-a12b"),
        ("openai", "sk-test-key", "gpt-4o-mini"),
    ],
)
def test_build_default_chat_model_respects_explicit_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    api_key: str,
    model_name: str,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_MODEL", model_name)
    monkeypatch.setenv("NVIDIA_API_KEY", api_key if provider == "nvidia" else "")
    monkeypatch.setenv("OPENAI_API_KEY", api_key if provider == "openai" else "")
    get_settings.cache_clear()

    model = build_default_chat_model()

    expected = "ChatNVIDIA" if provider == "nvidia" else "ChatOpenAI"
    assert model.__class__.__name__ == expected
    get_settings.cache_clear()


def test_settings_infers_nvidia_from_legacy_openai_compatible_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.resolved_llm_provider == "nvidia"
    assert settings.resolved_nvidia_api_key == "legacy-key"
    assert settings.resolved_nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.has_llm_credentials is True
    get_settings.cache_clear()
