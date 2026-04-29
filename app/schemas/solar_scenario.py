"""Schemas for compound solar-base scenario candidates.

These schemas describe candidate bundles for broad orientative solar
estimates when several base PV parameters are missing at once.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assumptions import AssumptionConfidence, AssumptionSourceType


class SolarScenarioFieldSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    source_type: AssumptionSourceType
    source_name: str
    source_url: str | None = None
    confidence: AssumptionConfidence
    rationale: str


class SolarBaseScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    known_user_data: dict[str, Any] = Field(default_factory=dict)
    location_context: str = Field(
        description="Explicit location context already resolved by the agent.",
    )
    user_goal: str = Field(
        description="What the user wants to estimate in this turn.",
    )
    missing_fields: list[str] = Field(
        min_length=1,
        description="Base PV fields still missing for the estimate.",
    )
    allow_orientative_scenario: bool = Field(
        description="Whether the user accepted an orientative declared scenario.",
    )
    max_candidates: int = Field(default=3, ge=1, le=3)


class SolarBaseScenarioCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    panel_power_w: float | None = None
    panel_width_m: float | None = None
    panel_length_m: float | None = None
    system_loss_pct: float | None = None
    solar_degradation_pct: float | None = None
    tilt_deg: float | None = None
    azimuth_deg: float | None = None
    spacing_x_m: float | None = None
    spacing_y_m: float | None = None
    maintenance_margin_m: float | None = None
    field_sources: list[SolarScenarioFieldSource] = Field(
        min_length=1,
        description="One traceability entry per non-null field in this candidate.",
    )
    confidence: AssumptionConfidence
    limitations: list[str] = Field(
        min_length=1,
        description="Explicit limitations or caveats of this candidate.",
    )
    requires_user_disclosure: bool = True


class SolarBaseScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[SolarBaseScenarioCandidate] = Field(
        min_length=1,
        description="One or more complete scenario candidates.",
    )
    notes: str | None = None


__all__ = [
    "SolarBaseScenarioCandidate",
    "SolarBaseScenarioRequest",
    "SolarBaseScenarioResponse",
    "SolarScenarioFieldSource",
]
