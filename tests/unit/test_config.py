import pytest

from app.core.config import Settings


def test_settings_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("APP_NAME", "APP_ENV", "LOG_LEVEL", "TRACE_ENABLED", "MEMORY_STORAGE_BACKEND"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_name == "ecoIA"
    assert settings.app_env == "development"
    assert settings.api_port > 0
    assert settings.memory_storage_backend in {"memory", "sqlite", "store"}
    assert settings.pvgis_base_url.startswith("https://")
    assert settings.http_timeout_seconds > 0
    assert settings.trace_enabled is True
    assert settings.agent_pii_guardrails_enabled is True
    assert settings.agent_prompt_guardrails_enabled is True
    assert settings.agent_output_guardrails_enabled is True
    assert settings.agent_human_in_the_loop_enabled is False
    assert settings.agent_human_in_the_loop_tools == []


def test_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"


def test_settings_from_kwargs_override(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("APP_ENV", "LOG_LEVEL"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None, app_env="staging", log_level="WARNING")  # type: ignore[call-arg]
    assert settings.app_env == "staging"
    assert settings.log_level == "WARNING"
