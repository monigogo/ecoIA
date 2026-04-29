"""AssumptionService — pure-reasoner provider of candidate assumptions.

Design rules (strict, see ``AGENTS.md``):

- No hardcoded domain values. No if/else branching on domain keys.
- No regex, no keyword matching, no string-similarity heuristics.
- No silent defaults. Every candidate is reasoned by an LLM and must
  cite a registry source from ``reference_sources.json`` OR be tagged as
  ``technical_reference`` with ``requires_user_disclosure=True``.
- The service does NOT pick a winner. It returns options.

The service is a thin pipeline:

    request + registry  ->  prompt  ->  LLM with structured output  ->  AssumptionResponse

The chat model is dependency-injected so tests can pass a fake without an
API key, and so the same service can be reused by different agents/subagents
with different model overrides.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, cast

from app.core.errors import AppError, ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.llm import build_default_chat_model
from app.schemas.assumptions import (
    AssumptionRequest,
    AssumptionResponse,
    ReferenceSource,
)

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "reference_sources.json"

SYSTEM_PROMPT = (
    "You are an assumption provider for a solar planning backend. "
    "Your role is to propose candidate values for a technical or regulatory parameter "
    "that the planning agent could not obtain from the user or from external APIs.\n\n"
    "Hard rules:\n"
    "- Never decide for the agent. Always return at least two distinct candidates "
    "covering plausible scenarios (e.g. conservative, central, optimistic).\n"
    "- Each candidate must cite a `source_name` (and `source_url` when available). "
    "If the candidate is not anchored to a registry source, set `source_type` to "
    "`technical_reference` and explain the reasoning.\n"
    "- Set `requires_user_disclosure=True` whenever the candidate is not strictly "
    "user-provided or directly fetched from an external API.\n"
    "- Always populate `reasoning` and `limitations`. Never leave them empty.\n"
    "- Do not invent regulatory facts. If unsure, say so in `limitations` and lower "
    "the `confidence`.\n"
    "- The `domain` of every candidate must echo the request `domain` verbatim.\n"
)


class AssumptionService:
    """LLM-backed provider of candidate assumptions.

    Parameters
    ----------
    model:
        Any LangChain chat model. If ``None``, the service will lazily build
        the configured provider-native model from settings on first use.
    registry_path:
        Path to ``reference_sources.json``. Defaults to the bundled file.
    """

    def __init__(
        self,
        model: BaseChatModel | None = None,
        registry_path: Path | None = None,
    ) -> None:
        self._model = model
        self._registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self._registry: list[ReferenceSource] | None = None

    # --- Registry ---------------------------------------------------------

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

        sources = [ReferenceSource.model_validate(item) for item in raw.get("sources", [])]
        self._registry = sources
        return sources

    # --- Model resolution -------------------------------------------------

    def _resolve_model(self) -> BaseChatModel:
        if self._model is not None:
            return self._model

        from app.core.config import get_settings

        settings = get_settings()
        if not settings.has_llm_credentials:
            raise ConfigurationError(
                f"{settings.llm_credential_hint} is not set; AssumptionService cannot reason without a model.",
            )

        self._model = build_default_chat_model(settings=settings, temperature=0)
        return self._model

    # --- Prompt -----------------------------------------------------------

    @staticmethod
    def _format_registry(sources: list[ReferenceSource]) -> str:
        if not sources:
            return "(registry is empty - only generic technical_reference candidates are allowed)"
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
        self, request: AssumptionRequest, sources: list[ReferenceSource]
    ) -> str:
        return (
            f"Domain: {request.domain}\n"
            f"Context provided by the agent:\n{request.context}\n\n"
            "Available citable sources (registry):\n"
            f"{self._format_registry(sources)}\n\n"
            "Produce candidate assumptions. Echo the domain verbatim into each candidate."
        )

    # --- Public API -------------------------------------------------------

    def generate_candidates(self, request: AssumptionRequest) -> AssumptionResponse:
        sources = self.load_registry()
        model = self._resolve_model()

        try:
            structured = model.with_structured_output(AssumptionResponse)
            user_prompt = self._build_user_prompt(request, sources)
            response = cast(
                AssumptionResponse,
                structured.invoke(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ]
                ),
            )
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001 — model errors are heterogeneous
            logger.exception("assumption_model_error", domain=request.domain)
            raise ExternalServiceError(
                "Assumption model invocation failed",
                details={"domain": request.domain, "error": str(exc)},
            ) from exc

        for candidate in response.candidates:
            if candidate.domain != request.domain:
                candidate.domain = request.domain

        logger.info(
            "assumption_candidates_generated",
            domain=request.domain,
            count=len(response.candidates),
        )
        return response
