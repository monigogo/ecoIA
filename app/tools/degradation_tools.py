"""Deterministic LangChain tools for degradation analysis."""

from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool

from app.schemas.degradation import (
    CompareDegradationScenariosRequest,
    CompareDegradationScenariosResult,
    DegradationProjectionRequest,
    DegradationProjectionResult,
    DegradationScenarioCandidate,
    DegradationScenarioComparison,
    LifetimeThresholdRequest,
    LifetimeThresholdResult,
    YearlyDegradationEntry,
)


def _project_yearly_output(
    annual_energy_year1_kwh: float,
    degradation_rate_pct: float,
    years: int,
) -> list[YearlyDegradationEntry]:
    multiplier = 1.0 - degradation_rate_pct / 100.0
    cumulative = 0.0
    projection: list[YearlyDegradationEntry] = []
    for year in range(1, years + 1):
        annual_energy = annual_energy_year1_kwh * (multiplier ** (year - 1))
        cumulative += annual_energy
        projection.append(
            YearlyDegradationEntry(
                year=year,
                annual_energy_kwh=annual_energy,
                relative_output_pct=100.0 * (multiplier ** (year - 1)),
                cumulative_energy_kwh=cumulative,
            )
        )
    return projection


def build_calculate_degradation_projection_tool():
    """Return a deterministic LangChain tool for year-by-year degradation projection."""

    @tool("calculate_degradation_projection", args_schema=DegradationProjectionRequest)
    def calculate_degradation_projection(
        annual_energy_year1_kwh: float,
        degradation_rate_pct: float,
        years: int,
    ) -> dict[str, Any]:
        """Project annual PV production over time from explicit year-1 energy and degradation."""

        response = DegradationProjectionResult(
            yearly_projection=_project_yearly_output(
                annual_energy_year1_kwh=annual_energy_year1_kwh,
                degradation_rate_pct=degradation_rate_pct,
                years=years,
            )
        )

        return response.model_dump()

    return calculate_degradation_projection


def build_calculate_lifetime_threshold_tool():
    """Return a deterministic LangChain tool for threshold-year estimation."""

    @tool("calculate_lifetime_threshold", args_schema=LifetimeThresholdRequest)
    def calculate_lifetime_threshold(
        degradation_rate_pct: float,
        threshold_pct: float,
    ) -> dict[str, Any]:
        """Estimate when relative output falls to or below an explicit threshold."""

        warnings: list[str] = []
        estimated_year: int | None

        if threshold_pct >= 100.0:
            estimated_year = 1
        elif degradation_rate_pct == 0.0:
            estimated_year = None
            warnings.append(
                "The threshold is not reached under zero annual degradation."
            )
        else:
            remaining_output_fraction = threshold_pct / 100.0
            degradation_multiplier = 1.0 - degradation_rate_pct / 100.0
            estimated_year = 1 + math.ceil(
                math.log(remaining_output_fraction) / math.log(degradation_multiplier)
            )

        response = LifetimeThresholdResult(
            estimated_year_reaching_threshold=estimated_year,
            threshold_pct=threshold_pct,
            warnings=warnings,
        )

        return response.model_dump()

    return calculate_lifetime_threshold


def _compare_scenario(
    annual_energy_year1_kwh: float,
    candidate: DegradationScenarioCandidate,
    years: int,
) -> DegradationScenarioComparison:
    projection = _project_yearly_output(
        annual_energy_year1_kwh=annual_energy_year1_kwh,
        degradation_rate_pct=candidate.degradation_rate_pct,
        years=years,
    )
    final_year = projection[-1]
    return DegradationScenarioComparison(
        scenario_id=candidate.scenario_id,
        scenario_label=candidate.scenario_label,
        degradation_rate_pct=candidate.degradation_rate_pct,
        final_year_energy_kwh=final_year.annual_energy_kwh,
        cumulative_energy_kwh=final_year.cumulative_energy_kwh,
        yearly_projection=projection,
        calculation_metadata={"years": years},
    )


def build_compare_degradation_scenarios_tool():
    """Return a deterministic LangChain tool for multi-scenario degradation comparison."""

    @tool("compare_degradation_scenarios", args_schema=CompareDegradationScenariosRequest)
    def compare_degradation_scenarios(
        annual_energy_year1_kwh: float,
        scenario_candidates: list[dict[str, Any]],
        years: int,
    ) -> dict[str, Any]:
        """Compare multiple explicit degradation scenarios without choosing a winner."""

        candidates = [
            DegradationScenarioCandidate.model_validate(candidate)
            for candidate in scenario_candidates
        ]

        response = CompareDegradationScenariosResult(
            comparison=[
                _compare_scenario(
                    annual_energy_year1_kwh=annual_energy_year1_kwh,
                    candidate=candidate,
                    years=years,
                )
                for candidate in candidates
            ]
        )

        return response.model_dump()

    return compare_degradation_scenarios


calculate_degradation_projection = build_calculate_degradation_projection_tool()
calculate_lifetime_threshold = build_calculate_lifetime_threshold_tool()
compare_degradation_scenarios = build_compare_degradation_scenarios_tool()


__all__ = [
    "build_calculate_degradation_projection_tool",
    "build_calculate_lifetime_threshold_tool",
    "build_compare_degradation_scenarios_tool",
    "calculate_degradation_projection",
    "calculate_lifetime_threshold",
    "compare_degradation_scenarios",
]
