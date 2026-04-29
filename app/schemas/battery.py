"""Schemas for deterministic battery sizing calculations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BatterySizeRequest(BaseModel):
    """Explicit inputs for approximate stationary battery sizing."""

    model_config = ConfigDict(extra="forbid")

    daily_consumption_kwh: float | None = Field(
        default=None,
        gt=0.0,
        description="Explicit daily electricity consumption in kWh.",
    )
    monthly_consumption_kwh: float | None = Field(
        default=None,
        gt=0.0,
        description="Explicit representative monthly electricity consumption in kWh.",
    )
    night_consumption_pct: float = Field(
        gt=0.0,
        le=100.0,
        description="Share of consumption that must be supplied overnight.",
    )
    depth_of_discharge_pct: float = Field(
        gt=0.0,
        le=100.0,
        description="Usable depth of discharge in percent.",
    )
    autonomy_days: float = Field(
        gt=0.0,
        description="Explicit autonomy target in days.",
    )

    @model_validator(mode="after")
    def validate_one_consumption_source(self) -> BatterySizeRequest:
        provided = [
            self.daily_consumption_kwh is not None,
            self.monthly_consumption_kwh is not None,
        ]
        if sum(provided) != 1:
            raise ValueError(
                "Provide exactly one explicit consumption source: "
                "daily_consumption_kwh or monthly_consumption_kwh."
            )
        return self


class BatterySizeResult(BaseModel):
    """Normalized battery sizing output."""

    model_config = ConfigDict(extra="forbid")

    useful_battery_kwh: float
    nominal_battery_kwh: float
    calculation_metadata: dict[str, float | str]
    warnings: list[str] = Field(default_factory=list)


class BatteryScenarioCandidate(BaseModel):
    """One explicit battery sizing scenario to compare."""

    model_config = ConfigDict(extra="forbid")

    scenario_label: str = Field(min_length=1)
    night_consumption_pct: float = Field(gt=0.0, le=100.0)
    depth_of_discharge_pct: float = Field(gt=0.0, le=100.0)
    autonomy_days: float = Field(gt=0.0)


class CompareBatteryScenariosRequest(BaseModel):
    """Explicit inputs for multi-scenario battery comparison."""

    model_config = ConfigDict(extra="forbid")

    daily_consumption_kwh: float | None = Field(default=None, gt=0.0)
    monthly_consumption_kwh: float | None = Field(default=None, gt=0.0)
    candidate_profiles: list[BatteryScenarioCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_one_consumption_source(self) -> CompareBatteryScenariosRequest:
        provided = [
            self.daily_consumption_kwh is not None,
            self.monthly_consumption_kwh is not None,
        ]
        if sum(provided) != 1:
            raise ValueError(
                "Provide exactly one explicit consumption source: "
                "daily_consumption_kwh or monthly_consumption_kwh."
            )
        return self


class BatteryScenarioComparison(BaseModel):
    """Calculated output for one battery scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_label: str
    useful_battery_kwh: float
    nominal_battery_kwh: float
    assumptions_used: dict[str, float | str]
    warnings: list[str] = Field(default_factory=list)


class CompareBatteryScenariosResult(BaseModel):
    """Normalized response for multi-scenario battery comparison."""

    model_config = ConfigDict(extra="forbid")

    battery_scenario_comparison: list[BatteryScenarioComparison]
