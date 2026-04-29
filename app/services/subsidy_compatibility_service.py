"""SubsidyCompatibilityService — LLM-backed compatibility evaluator.

Reasoning rules:

- No scoring tables, no keyword matching, no string similarity.
- The LLM reads the project context, the candidate's normalized text,
  and any available evidence, and produces a structured
  :class:`CompatibilityEvaluationResult`.
- The result is never a guarantee of grant. The legal warning is fixed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.core.errors import AppError, ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.llm import build_default_chat_model
from app.schemas.subsidy import (
    CompatibilityEvaluationRequest,
    CompatibilityEvaluationResult,
    CompatibilityLevel,
)

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a subsidy-compatibility evaluator for a solar planning backend.\n"
    "Your job is to read a project context, a candidate subsidy, and any "
    "evidence the user already provided, and return a STRUCTURED reasoning "
    "of compatibility. You do NOT decide eligibility. You do NOT promise "
    "concession. You ONLY indicate plausibility.\n\n"
    "Hard rules:\n"
    "- Use the four levels: high, medium, low, requires_verification.\n"
    "- Always populate `reasoning` with a concise rationale.\n"
    "- Always list `matched_requirements` and `missing_requirements` "
    "explicitly. If you don't know, list it under `missing_requirements`.\n"
    "- Always list documents the user must verify in `documents_to_verify`.\n"
    "- Never say the user is guaranteed to receive the subsidy.\n"
    "- Do not classify by keyword. Reason about the candidate's stated "
    "purpose, beneficiaries, region, and dates relative to the project.\n"
)


class SubsidyCompatibilityService:
    """LLM-backed reasoner that produces compatibility evaluations."""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        self._model = model

    def _resolve_model(self) -> BaseChatModel:
        if self._model is not None:
            return self._model

        from app.core.config import get_settings

        settings = get_settings()
        if not settings.has_llm_credentials:
            raise ConfigurationError(
                f"{settings.llm_credential_hint} is not set; SubsidyCompatibilityService "
                "cannot reason without a model.",
            )

        self._model = build_default_chat_model(settings=settings, temperature=0)
        return self._model

    @staticmethod
    def _build_user_prompt(request: CompatibilityEvaluationRequest) -> str:
        candidate = request.subsidy_candidate
        return (
            f"Project context:\n{request.project_context}\n\n"
            f"Available evidence:\n{request.available_evidence or '(none provided)'}\n\n"
            "Candidate subsidy:\n"
            f"- id: {candidate.id}\n"
            f"- title: {candidate.title}\n"
            f"- administration: {candidate.administration}\n"
            f"- region: {candidate.region or '(unspecified)'}\n"
            f"- municipality: {candidate.municipality or '(unspecified)'}\n"
            f"- beneficiary_summary: {candidate.beneficiary_summary or '(unspecified)'}\n"
            f"- purpose_summary: {candidate.purpose_summary or '(unspecified)'}\n"
            f"- status: {candidate.status}\n"
            f"- deadline: {candidate.deadline.isoformat() if candidate.deadline else '(unspecified)'}\n"
            f"- amount_summary: {candidate.amount_summary or '(unspecified)'}\n"
            f"- source_url: {candidate.source_url or '(none)'}\n\n"
            "Reason about compatibility and return the structured result."
        )

    def evaluate(
        self, request: CompatibilityEvaluationRequest
    ) -> CompatibilityEvaluationResult:
        model = self._resolve_model()
        try:
            structured = model.with_structured_output(CompatibilityEvaluationResult)
            user_prompt = self._build_user_prompt(request)
            response = cast(
                CompatibilityEvaluationResult,
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
            logger.exception(
                "subsidy_compatibility_model_error",
                candidate_id=request.subsidy_candidate.id,
            )
            raise ExternalServiceError(
                "Subsidy compatibility model invocation failed",
                details={
                    "candidate_id": request.subsidy_candidate.id,
                    "error": str(exc),
                },
            ) from exc

        # Guard: the model must produce one of the recognized levels. Pydantic
        # already enforces this, but we harden against any future schema drift.
        if response.compatibility_level not in CompatibilityLevel:
            response.compatibility_level = CompatibilityLevel.requires_verification

        logger.info(
            "subsidy_compatibility_evaluated",
            candidate_id=request.subsidy_candidate.id,
            level=response.compatibility_level,
        )
        return response
