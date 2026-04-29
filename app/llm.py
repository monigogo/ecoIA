"""Shared chat-model factory for SolarLife LLM-backed components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.core.errors import ConfigurationError

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel


def _missing_credentials_error(settings: Settings, consumer: str) -> ConfigurationError:
    return ConfigurationError(
        f"{settings.llm_credential_hint} is not set; {consumer} cannot run without a model.",
        details={"provider": settings.resolved_llm_provider},
    )


def build_default_chat_model(
    *,
    settings: Settings | None = None,
    temperature: float = 0,
) -> BaseChatModel:
    """Build the default LangChain chat model for the configured provider."""

    resolved_settings = settings or get_settings()
    provider = resolved_settings.resolved_llm_provider

    if provider == "nvidia":
        api_key = resolved_settings.resolved_nvidia_api_key
        if not api_key:
            raise _missing_credentials_error(resolved_settings, "the configured NVIDIA runtime")

        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        base_url = resolved_settings.resolved_nvidia_base_url
        if base_url:
            return ChatNVIDIA(
                model=resolved_settings.llm_model,
                api_key=api_key,
                temperature=temperature,
                disable_streaming="tool_calling",
                base_url=base_url,
            )
        return ChatNVIDIA(
            model=resolved_settings.llm_model,
            api_key=api_key,
            temperature=temperature,
            disable_streaming="tool_calling",
        )

    if not resolved_settings.openai_api_key:
        raise _missing_credentials_error(resolved_settings, "the configured OpenAI runtime")

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=resolved_settings.llm_model,
        api_key=SecretStr(resolved_settings.openai_api_key),
        base_url=resolved_settings.openai_base_url,
        temperature=temperature,
        disable_streaming="tool_calling",
        model_kwargs={"parallel_tool_calls": False},
    )


__all__ = ["build_default_chat_model"]
