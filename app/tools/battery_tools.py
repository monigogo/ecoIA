"""Deterministic LangChain tools for battery sizing calculations."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.schemas.battery import (
    BatteryScenarioCandidate,
    BatteryScenarioComparison,
    BatterySizeRequest,
    BatterySizeResult,
    CompareBatteryScenariosRequest,
    CompareBatteryScenariosResult,
)


def _resolve_daily_consumption(
    *,
    daily_consumption_kwh: float | None,
    monthly_consumption_kwh: float | None,
) -> tuple[float, str, list[str]]:
    warnings: list[str] = []
    if daily_consumption_kwh is not None:
        return daily_consumption_kwh, "daily_consumption_kwh", warnings

    resolved_daily = (monthly_consumption_kwh * 12.0) / 365.0
    warnings.append(
        "Daily consumption was derived from explicit monthly consumption using a 365-day year."
    )
    return resolved_daily, "monthly_consumption_kwh", warnings


def _size_battery(
    *,
    daily_consumption_kwh: float,
    night_consumption_pct: float,
    depth_of_discharge_pct: float,
    autonomy_days: float,
) -> tuple[float, float]:
    useful_battery_kwh = daily_consumption_kwh * (night_consumption_pct / 100.0) * autonomy_days
    nominal_battery_kwh = useful_battery_kwh / (depth_of_discharge_pct / 100.0)
    return useful_battery_kwh, nominal_battery_kwh


def build_estimate_battery_size_tool():
    """Return a deterministic LangChain tool for approximate battery sizing."""

    @tool("estimate_battery_size", args_schema=BatterySizeRequest)
    def estimate_battery_size(
        night_consumption_pct: float,
        depth_of_discharge_pct: float,
        autonomy_days: float,
        daily_consumption_kwh: float | None = None,
        monthly_consumption_kwh: float | None = None,
    ) -> dict[str, Any]:
        """Estimate usable and nominal battery capacity from explicit consumption inputs."""

        resolved_daily, source_field_used, warnings = _resolve_daily_consumption(
            daily_consumption_kwh=daily_consumption_kwh,
            monthly_consumption_kwh=monthly_consumption_kwh,
        )
        useful_battery_kwh, nominal_battery_kwh = _size_battery(
            daily_consumption_kwh=resolved_daily,
            night_consumption_pct=night_consumption_pct,
            depth_of_discharge_pct=depth_of_discharge_pct,
            autonomy_days=autonomy_days,
        )

        response = BatterySizeResult(
            useful_battery_kwh=useful_battery_kwh,
            nominal_battery_kwh=nominal_battery_kwh,
            calculation_metadata={
                "daily_consumption_kwh_used": resolved_daily,
                "source_field_used": source_field_used,
                "night_consumption_pct": night_consumption_pct,
                "depth_of_discharge_pct": depth_of_discharge_pct,
                "autonomy_days": autonomy_days,
            },
            warnings=warnings,
        )
        return response.model_dump()

    return estimate_battery_size


def _compare_battery_scenario(
    *,
    daily_consumption_kwh: float,
    source_field_used: str,
    warnings: list[str],
    candidate: BatteryScenarioCandidate,
) -> BatteryScenarioComparison:
    useful_battery_kwh, nominal_battery_kwh = _size_battery(
        daily_consumption_kwh=daily_consumption_kwh,
        night_consumption_pct=candidate.night_consumption_pct,
        depth_of_discharge_pct=candidate.depth_of_discharge_pct,
        autonomy_days=candidate.autonomy_days,
    )
    return BatteryScenarioComparison(
        scenario_label=candidate.scenario_label,
        useful_battery_kwh=useful_battery_kwh,
        nominal_battery_kwh=nominal_battery_kwh,
        assumptions_used={
            "daily_consumption_kwh_used": daily_consumption_kwh,
            "source_field_used": source_field_used,
            "night_consumption_pct": candidate.night_consumption_pct,
            "depth_of_discharge_pct": candidate.depth_of_discharge_pct,
            "autonomy_days": candidate.autonomy_days,
        },
        warnings=list(warnings),
    )


def build_compare_battery_scenarios_tool():
    """Return a deterministic LangChain tool for comparing battery sizing scenarios."""

    @tool("compare_battery_scenarios", args_schema=CompareBatteryScenariosRequest)
    def compare_battery_scenarios(
        candidate_profiles: list[dict[str, Any]],
        daily_consumption_kwh: float | None = None,
        monthly_consumption_kwh: float | None = None,
    ) -> dict[str, Any]:
        """Compare several explicit battery sizing scenarios without selecting one."""

        resolved_daily, source_field_used, warnings = _resolve_daily_consumption(
            daily_consumption_kwh=daily_consumption_kwh,
            monthly_consumption_kwh=monthly_consumption_kwh,
        )
        profiles = [
            BatteryScenarioCandidate.model_validate(candidate)
            for candidate in candidate_profiles
        ]

        response = CompareBatteryScenariosResult(
            battery_scenario_comparison=[
                _compare_battery_scenario(
                    daily_consumption_kwh=resolved_daily,
                    source_field_used=source_field_used,
                    warnings=warnings,
                    candidate=profile,
                )
                for profile in profiles
            ]
        )
        return response.model_dump()

    return compare_battery_scenarios


estimate_battery_size = build_estimate_battery_size_tool()
compare_battery_scenarios = build_compare_battery_scenarios_tool()


__all__ = [
    "build_compare_battery_scenarios_tool",
    "build_estimate_battery_size_tool",
    "compare_battery_scenarios",
    "estimate_battery_size",
]
