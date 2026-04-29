import os
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvName = Literal["development", "test", "staging", "production"]
MemoryBackend = Literal["memory", "sqlite", "store"]
LLMProvider = Literal["openai", "nvidia"]

_NVIDIA_HOST_MARKERS = (
    "integrate.api.nvidia.com",
    "api.nvcf.nvidia.com",
)


def _looks_like_nvidia_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    lowered = base_url.lower()
    return any(marker in lowered for marker in _NVIDIA_HOST_MARKERS)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- App identity ---
    app_name: str = Field(default="ecoIA")
    app_env: EnvName = Field(default="development")
    log_level: str = Field(default="INFO")

    # --- API ---
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # --- LLM (optional at boot) ---
    llm_provider: LLMProvider | None = Field(default=None)
    llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL"),
    )
    openai_api_key: str = Field(default="")
    openai_base_url: str | None = Field(default=None)
    nvidia_api_key: str = Field(default="")
    nvidia_base_url: str | None = Field(default=None)

    # --- Storage / persistence ---
    database_url: str = Field(default="sqlite:///./solarlife.db")
    memory_storage_backend: MemoryBackend = Field(default="sqlite")
    agent_checkpoint_sqlite_path: str = Field(default="./.data/langgraph_checkpoints.sqlite")
    diskcache_dir: str = Field(default="./.cache")

    # --- External APIs ---
    pvgis_base_url: str = Field(default="https://re.jrc.ec.europa.eu/api/v5_3")
    bdns_base_url: str = Field(default="https://www.infosubvenciones.es/bdnstrans/api")
    geocoding_base_url: str = Field(default="https://nominatim.openstreetmap.org")
    geocoding_user_agent: str = Field(default="solarlife-backend")
    geocoding_cache_ttl_seconds: int = Field(default=86400)
    geocoding_min_interval_seconds: float = Field(default=1.0)

    # --- Energy price providers ---
    # ESIOS (REE) — requires personal token. Endpoint:
    # https://api.esios.ree.es/indicators/{indicator_id}
    esios_api_base_url: str = Field(default="https://api.esios.ree.es")
    esios_api_token: str = Field(default="")
    # Indicator 1739: surplus compensation price for simplified self-consumption (PVPC).
    esios_indicator_pvpc_surplus_compensation: int = Field(default=1739)
    # PVPC import reference indicator id is configurable. The agent must
    # set this explicitly when used; no opaque hardcoded default.
    esios_indicator_pvpc_import_reference: int | None = Field(default=None)
    # OMIE — public day-ahead market data. Daily marginal price file lives at
    # https://www.omie.es/es/file-download?parents=marginalpdbc&filename=marginalpdbc_YYYYMMDD.1
    omie_base_url: str = Field(default="https://www.omie.es")
    price_provider_timeout_seconds: int = Field(default=30)

    # --- Subsidy / tax-benefit providers ---
    bdns_api_base_url: str = Field(default="https://www.infosubvenciones.es/bdnstrans/api")
    bdns_swagger_url: str = Field(
        default="https://www.infosubvenciones.es/bdnstrans/doc/swagger"
    )
    idae_base_url: str = Field(default="https://www.idae.es")
    aeat_base_url: str = Field(default="https://sede.agenciatributaria.gob.es")
    subsidy_provider_timeout_seconds: int = Field(default=30)

    # --- HTTP ---
    http_timeout_seconds: int = Field(default=30)
    http_max_retries: int = Field(default=3)

    # --- Agent runtime ---
    agent_model_call_limit: int = Field(default=24)
    agent_tool_call_limit: int = Field(default=32)
    agent_task_call_limit: int = Field(default=8)
    agent_assumption_call_limit: int = Field(default=2)
    agent_solar_base_scenario_call_limit: int = Field(default=1)
    agent_runtime_timeout_seconds: int = Field(default=1000)
    agent_assumption_tool_timeout_seconds: int = Field(default=60)
    agent_solar_base_scenario_tool_timeout_seconds: int = Field(default=90)
    agent_pvgis_tool_timeout_seconds: int = Field(default=45)
    agent_subsidy_tool_timeout_seconds: int = Field(default=60)
    agent_pii_guardrails_enabled: bool = Field(default=True)
    agent_prompt_guardrails_enabled: bool = Field(default=True)
    agent_output_guardrails_enabled: bool = Field(default=True)
    agent_human_in_the_loop_enabled: bool = Field(default=False)
    agent_human_in_the_loop_tools: list[str] = Field(default_factory=list)

    # --- Tracing ---
    trace_enabled: bool = Field(default=True)

    @property
    def resolved_llm_provider(self) -> LLMProvider:
        if self.llm_provider is not None:
            return self.llm_provider
        if (
            self.nvidia_api_key
            or self.nvidia_base_url
            or _looks_like_nvidia_base_url(self.openai_base_url)
            or self.llm_model.startswith("nvidia/")
        ):
            return "nvidia"
        return "openai"

    @property
    def resolved_nvidia_api_key(self) -> str:
        if self.nvidia_api_key:
            return self.nvidia_api_key
        if _looks_like_nvidia_base_url(self.openai_base_url):
            return self.openai_api_key
        return ""

    @property
    def resolved_nvidia_base_url(self) -> str | None:
        if self.nvidia_base_url:
            return self.nvidia_base_url
        if _looks_like_nvidia_base_url(self.openai_base_url):
            return self.openai_base_url
        return None

    @property
    def has_llm_credentials(self) -> bool:
        if self.resolved_llm_provider == "nvidia":
            return bool(self.resolved_nvidia_api_key)
        return bool(self.openai_api_key)

    @property
    def llm_credential_hint(self) -> str:
        if self.resolved_llm_provider == "nvidia":
            if _looks_like_nvidia_base_url(self.openai_base_url):
                return "NVIDIA_API_KEY (or legacy OPENAI_API_KEY with an NVIDIA base URL)"
            return "NVIDIA_API_KEY"
        return "OPENAI_API_KEY"


@lru_cache
def get_settings() -> Settings:
    env_file = None if os.getenv("APP_ENV") == "test" else ".env"
    return Settings(_env_file=env_file)  # type: ignore[call-arg]
