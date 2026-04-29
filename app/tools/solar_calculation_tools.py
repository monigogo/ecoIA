"""Deterministic LangChain tools for solar sizing calculations."""

from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool

from app.core.errors import ValidationAppError
from app.schemas.solar_project import (
    AnnualConsumptionRequest,
    AnnualConsumptionResult,
    CoverageRequest,
    CoverageResult,
    PanelsForFutureTargetRequest,
    PanelsForFutureTargetResult,
    SystemKwpRequest,
    SystemKwpResult,
)


def build_calculate_system_kwp_tool():
    """Return a deterministic LangChain tool for installed system peak power."""

    @tool("calculate_system_kwp", args_schema=SystemKwpRequest)
    def calculate_system_kwp(num_panels: int, panel_power_w: float) -> dict[str, Any]:
        """Calculate installed system peak power from explicit panel count and panel wattage."""

        response = SystemKwpResult(system_kwp=(num_panels * panel_power_w) / 1000.0)
        return response.model_dump()

    return calculate_system_kwp


def build_calculate_annual_consumption_tool():
    """Return a deterministic LangChain tool for annualized electricity consumption."""

    @tool("calculate_annual_consumption", args_schema=AnnualConsumptionRequest)
    def calculate_annual_consumption(
        monthly_consumption_kwh: list[float] | None = None,
        annual_consumption_kwh: float | None = None,
    ) -> dict[str, Any]:
        """Calculate or validate annual electricity consumption from explicit inputs only."""

        warnings: list[str] = []
        source_field_used = "annual_consumption_kwh"
        resolved_annual = annual_consumption_kwh

        if monthly_consumption_kwh is not None:
            monthly_total = float(sum(monthly_consumption_kwh))
            if annual_consumption_kwh is None:
                resolved_annual = monthly_total
                source_field_used = "monthly_consumption_kwh"
            else:
                difference = abs(monthly_total - annual_consumption_kwh)
                if difference > 1.0:
                    raise ValidationAppError(
                        "Monthly and annual consumption inputs are inconsistent.",
                        details={
                            "monthly_total_kwh": monthly_total,
                            "annual_consumption_kwh": annual_consumption_kwh,
                            "difference_kwh": difference,
                        },
                    )
                resolved_annual = annual_consumption_kwh
                source_field_used = "validated_monthly_and_annual"
                warnings.append(
                    "Both monthly and annual consumption were provided and found consistent."
                )

        if resolved_annual is None:
            raise ValidationAppError(
                "No explicit consumption value was supplied.",
            )

        response = AnnualConsumptionResult(
            annual_consumption_kwh=resolved_annual,
            source_field_used=source_field_used,
            warnings=warnings,
        )
        return response.model_dump()

    return calculate_annual_consumption


def build_calculate_coverage_tool():
    """Return a deterministic LangChain tool for annual coverage metrics."""

    @tool("calculate_coverage", args_schema=CoverageRequest)
    def calculate_coverage(
        annual_energy_kwh: float,
        annual_consumption_kwh: float,
    ) -> dict[str, Any]:
        """Compare annual PV production against annual electricity consumption."""

        coverage_ratio = annual_energy_kwh / annual_consumption_kwh
        response = CoverageResult(
            coverage_pct=coverage_ratio * 100.0,
            surplus_or_deficit_kwh=annual_energy_kwh - annual_consumption_kwh,
            interpretation_metrics={"production_to_consumption_ratio": coverage_ratio},
        )
        return response.model_dump()

    return calculate_coverage


def build_estimate_panels_for_future_target_tool():
    """Return a deterministic LangChain tool for future-year panel requirements."""

    @tool("estimate_panels_for_future_target", args_schema=PanelsForFutureTargetRequest)
    def estimate_panels_for_future_target(
        target_energy_year_n_kwh: float,
        energy_per_panel_year1_kwh: float,
        degradation_rate_pct: float,
        target_year: int,
        safety_margin_pct: float,
    ) -> dict[str, Any]:
        """Estimate how many panels are required to hit a future-year energy target."""

        degradation_multiplier = (1.0 - degradation_rate_pct / 100.0) ** (target_year - 1)
        if degradation_multiplier <= 0.0:
            raise ValidationAppError(
                "The explicit degradation inputs yield a non-positive target-year output multiplier.",
                details={
                    "degradation_rate_pct": degradation_rate_pct,
                    "target_year": target_year,
                },
            )

        required_year1_energy_kwh = (
            target_energy_year_n_kwh / degradation_multiplier
        ) * (1.0 + safety_margin_pct / 100.0)
        recommended_panels = math.ceil(required_year1_energy_kwh / energy_per_panel_year1_kwh)

        response = PanelsForFutureTargetResult(
            required_year1_energy_kwh=required_year1_energy_kwh,
            recommended_panels=recommended_panels,
            calculation_metadata={
                "target_energy_year_n_kwh": target_energy_year_n_kwh,
                "energy_per_panel_year1_kwh": energy_per_panel_year1_kwh,
                "degradation_rate_pct": degradation_rate_pct,
                "target_year": target_year,
                "safety_margin_pct": safety_margin_pct,
                "target_year_output_multiplier": degradation_multiplier,
            },
        )
        return response.model_dump()

    return estimate_panels_for_future_target


calculate_system_kwp = build_calculate_system_kwp_tool()
calculate_annual_consumption = build_calculate_annual_consumption_tool()
calculate_coverage = build_calculate_coverage_tool()
estimate_panels_for_future_target = build_estimate_panels_for_future_target_tool()


__all__ = [
    "build_calculate_annual_consumption_tool",
    "build_calculate_coverage_tool",
    "build_calculate_system_kwp_tool",
    "build_estimate_panels_for_future_target_tool",
    "calculate_annual_consumption",
    "calculate_coverage",
    "calculate_system_kwp",
    "estimate_panels_for_future_target",
]
