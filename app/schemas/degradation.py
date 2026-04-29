"""Schemas for deterministic degradation calculations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DegradationProjectionRequest(BaseModel):
    """Explicit inputs for a year-by-year degradation projection."""

    model_config = ConfigDict(extra="forbid")

    annual_energy_year1_kwh: float = Field(gt=0.0)
    degradation_rate_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Annual degradation rate in percent, for example 0.5 for 0.5%/year.",
    )
    years: int = Field(ge=1)


class YearlyDegradationEntry(BaseModel):
    """One annual output point in the degradation curve."""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=1)
    annual_energy_kwh: float
    relative_output_pct: float
    cumulative_energy_kwh: float


class DegradationProjectionResult(BaseModel):
    """Normalized degradation projection response."""

    model_config = ConfigDict(extra="forbid")

    yearly_projection: list[YearlyDegradationEntry]


class LifetimeThresholdRequest(BaseModel):
    """Explicit inputs for threshold-year estimation."""

    model_config = ConfigDict(extra="forbid")

    degradation_rate_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Annual degradation rate in percent, for example 0.5 for 0.5%/year.",
    )
    threshold_pct: float = Field(
        gt=0.0,
        le=100.0,
        description="Relative output threshold expressed as a percentage of year-1 production.",
    )


class LifetimeThresholdResult(BaseModel):
    """Threshold-year estimate for a degradation curve."""

    model_config = ConfigDict(extra="forbid")

    estimated_year_reaching_threshold: int | None = None
    threshold_pct: float
    warnings: list[str] = Field(default_factory=list)


class DegradationScenarioCandidate(BaseModel):
    """One explicit degradation scenario to compare."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    scenario_label: str = Field(min_length=1)
    degradation_rate_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Annual degradation rate in percent.",
    )


class CompareDegradationScenariosRequest(BaseModel):
    """Explicit inputs for multi-scenario degradation comparison."""

    model_config = ConfigDict(extra="forbid")

    annual_energy_year1_kwh: float = Field(gt=0.0)
    scenario_candidates: list[DegradationScenarioCandidate] = Field(min_length=1)
    years: int = Field(ge=1)


class DegradationScenarioComparison(BaseModel):
    """Projected output for one degradation scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_label: str
    degradation_rate_pct: float
    final_year_energy_kwh: float
    cumulative_energy_kwh: float
    yearly_projection: list[YearlyDegradationEntry]
    calculation_metadata: dict[str, Any] | None = None


class CompareDegradationScenariosResult(BaseModel):
    """Normalized multi-scenario degradation comparison."""

    model_config = ConfigDict(extra="forbid")

    comparison: list[DegradationScenarioComparison]
