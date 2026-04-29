"""LLM-backed provider of compound solar-base scenario candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from app.core.errors import AppError, ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.llm import build_default_chat_model
from app.schemas.assumptions import ReferenceSource
from app.schemas.solar_scenario import (
    SolarBaseScenarioRequest,
    SolarBaseScenarioResponse,
)

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "reference_sources.json"

SYSTEM_PROMPT = (
    "You are a solar base-scenario provider for a solar planning backend. "
    "Your job is to return complete candidate scenarios for missing base PV parameters "
    "when the user accepted an orientative estimate and filling fields one by one would be too slow.\n\n"
    "Hard rules:\n"
    "- Never choose a winner for the agent.\n"
    "- Return coherent candidate bundles, not disconnected single-field suggestions.\n"
    "- Do not silently apply defaults. Every field must carry an explicit source or rationale.\n"
    "- Only return orientative scenarios when `allow_orientative_scenario` is true.\n"
    "- If `allow_orientative_scenario` is true, return at least one candidate. "
    "Do not return an empty candidate list unless the user explicitly rejected an orientative scenario.\n"
    "- When the user goal includes lifetime or 25-year production, include a "
    "degradation field when you can justify one.\n"
    "- If uncertainty is high, keep the candidate but state the limitation explicitly.\n"
    "- Each candidate must contain at least one entry in `field_sources` explaining where each non-null field came from. "
    "Never return an empty `field_sources` list.\n"
    "- Each candidate must contain at least one entry in `limitations` describing caveats of the scenario "
    "(uncertainty, assumed values, missing measurements, etc.). Never return an empty `limitations` list.\n"
    "- Keep the number of candidates at or below `max_candidates`.\n"
)


class SolarScenarioService:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        registry_path: Path | None = None,
    ) -> None:
        self._model = model
        self._registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._registry: list[ReferenceSource] | None = None

    def load_registry(self) -> list[ReferenceSource]:
        if self._registry is not None:
            return self._registry
        try:
            raw = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(
                "reference_sources.json not found",
                details={"path": str(self._registry_path)},
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                "reference_sources.json is not valid JSON",
                details={"path": str(self._registry_path), "error": str(exc)},
            ) from exc

        self._registry = [ReferenceSource.model_validate(item) for item in raw.get("sources", [])]
        return self._registry

    def _resolve_model(self) -> BaseChatModel:
        if self._model is not None:
            return self._model

        from app.core.config import get_settings

        settings = get_settings()
        if not settings.has_llm_credentials:
            raise ConfigurationError(
                f"{settings.llm_credential_hint} is not set; SolarScenarioService cannot reason without a model.",
            )

        self._model = build_default_chat_model(settings=settings, temperature=0)
        return self._model

    @staticmethod
    def _format_registry(sources: list[ReferenceSource]) -> str:
        if not sources:
            return "(registry is empty)"

        lines: list[str] = []
        for src in sources:
            url = f" - {src.url}" if src.url else ""
            lines.append(
                f"- {src.source_id} | {src.title} | {src.organization} "
                f"| type={src.source_type}{url}"
                + (f" | notes: {src.notes}" if src.notes else "")
            )
        return "\n".join(lines)

    def _build_user_prompt(
        self,
        request: SolarBaseScenarioRequest,
        sources: list[ReferenceSource],
    ) -> str:
        return (
            "Known user data:\n"
            f"{json.dumps(request.known_user_data, ensure_ascii=False, sort_keys=True)}\n\n"
            f"Location context: {request.location_context}\n"
            f"User goal: {request.user_goal}\n"
            f"Missing fields: {', '.join(request.missing_fields)}\n"
            f"Allow orientative scenario: {request.allow_orientative_scenario}\n"
            f"Maximum candidates: {request.max_candidates}\n\n"
            "Available citable sources (registry):\n"
            f"{self._format_registry(sources)}\n\n"
            "Return complete candidate bundles for the missing base PV parameters."
        )

    def generate_candidates(
        self,
        request: SolarBaseScenarioRequest,
    ) -> SolarBaseScenarioResponse:
        sources = self.load_registry()
        model = self._resolve_model()
        user_prompt = self._build_user_prompt(request, sources)
        base_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        retry_message = {
            "role": "user",
            "content": (
                "Your previous response did not contain valid scenario candidates. "
                "Return at least one complete candidate bundle. Do not leave "
                "`candidates`, `field_sources`, or `limitations` empty."
            ),
        }

        structured = model.with_structured_output(SolarBaseScenarioResponse)
        last_error: Exception | None = None
        response: SolarBaseScenarioResponse | None = None

        for attempt in range(2):
            messages = base_messages if attempt == 0 else [*base_messages, retry_message]
            try:
                response = cast(
                    SolarBaseScenarioResponse,
                    structured.invoke(messages),
                )
            except AppError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
            if response.candidates:
                break

        if response is None or not response.candidates:
            logger.warning(
                "solar_base_scenario_model_error",
                error=str(last_error) if last_error else "empty_candidates",
            )
            raise ExternalServiceError(
                "Solar base scenario provider returned no candidates",
                details={
                    "missing_fields": request.missing_fields,
                    "user_goal": request.user_goal,
                    "error": str(last_error) if last_error else "empty_candidates",
                },
            )

        if len(response.candidates) > request.max_candidates:
            response = response.model_copy(update={"candidates": response.candidates[: request.max_candidates]})

        logger.info(
            "solar_base_scenario_candidates_generated",
            count=len(response.candidates),
            missing_fields=len(request.missing_fields),
        )
        return response


__all__ = ["SolarScenarioService"]
