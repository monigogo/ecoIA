"""Structured response schemas for the SolarLife agent graph."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assumptions import AssumptionConfidence
from app.tracing.trace_events import TraceEventKind


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str | None = None


class AssumptionDisclosure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter: str = Field(description="Parameter that required an explicit assumption.")
    chosen_value: str = Field(description="Value the agent selected and disclosed.")
    rationale: str = Field(description="Why the agent selected this assumption.")
    source_name: str
    source_url: str | None = None
    confidence: AssumptionConfidence | None = None
    disclosure_required: bool = True


class NaturalTraceLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str
    summary: str
    kind: TraceEventKind = Field(default=TraceEventKind.note)


class SubagentStructuredResponse(BaseModel):
    """Generic structured payload returned by specialist subagents."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    key_points: list[str] = Field(default_factory=list)
    assumptions_used: list[AssumptionDisclosure] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    natural_trace: list[NaturalTraceLine] = Field(default_factory=list)


class SolarAgentStructuredResponse(SubagentStructuredResponse):
    """Final structured response returned by the SolarLife supervisor."""

    response_status: Literal["complete", "partial", "needs_user_input", "failed_controlled"] = (
        "complete"
    )
    missing_information: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    subsidy_candidates: list[dict[str, Any]] = Field(default_factory=list)
    export_compensation: dict[str, Any] | None = None
    export_sale_revenue: dict[str, Any] | None = None
    rdtools_analysis: dict[str, Any] | None = None


__all__ = [
    "AssumptionDisclosure",
    "NaturalTraceLine",
    "SolarAgentStructuredResponse",
    "SourceCitation",
    "SubagentStructuredResponse",
]
