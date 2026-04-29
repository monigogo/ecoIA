from __future__ import annotations

import json

import pytest

from app.tools.battery_tools import (
    build_compare_battery_scenarios_tool,
    build_estimate_battery_size_tool,
)


def test_estimate_battery_size_tool_has_expected_name() -> None:
    tool = build_estimate_battery_size_tool()
    assert tool.name == "estimate_battery_size"
    assert tool.description


def test_compare_battery_scenarios_tool_has_expected_name() -> None:
    tool = build_compare_battery_scenarios_tool()
    assert tool.name == "compare_battery_scenarios"


def test_estimate_battery_size_returns_serializable_output() -> None:
    tool = build_estimate_battery_size_tool()
    payload = tool.invoke(
        {
            "daily_consumption_kwh": 12.0,
            "night_consumption_pct": 40.0,
            "depth_of_discharge_pct": 90.0,
            "autonomy_days": 1.0,
        }
    )

    assert payload["useful_battery_kwh"] == pytest.approx(4.8)
    assert payload["nominal_battery_kwh"] == pytest.approx(4.8 / 0.9)
    assert payload["calculation_metadata"]["source_field_used"] == "daily_consumption_kwh"
    json.dumps(payload)


def test_estimate_battery_size_derives_daily_value_from_explicit_monthly_consumption() -> None:
    tool = build_estimate_battery_size_tool()
    payload = tool.invoke(
        {
            "monthly_consumption_kwh": 360.0,
            "night_consumption_pct": 50.0,
            "depth_of_discharge_pct": 80.0,
            "autonomy_days": 1.0,
        }
    )

    assert payload["calculation_metadata"]["source_field_used"] == "monthly_consumption_kwh"
    assert payload["warnings"] == [
        "Daily consumption was derived from explicit monthly consumption using a 365-day year."
    ]


def test_compare_battery_scenarios_returns_all_profiles_without_selecting_one() -> None:
    tool = build_compare_battery_scenarios_tool()
    payload = tool.invoke(
        {
            "daily_consumption_kwh": 10.0,
            "candidate_profiles": [
                {
                    "scenario_label": "Base",
                    "night_consumption_pct": 40.0,
                    "depth_of_discharge_pct": 90.0,
                    "autonomy_days": 1.0,
                },
                {
                    "scenario_label": "High autonomy",
                    "night_consumption_pct": 40.0,
                    "depth_of_discharge_pct": 90.0,
                    "autonomy_days": 2.0,
                },
            ],
        }
    )

    assert len(payload["battery_scenario_comparison"]) == 2
    assert payload["battery_scenario_comparison"][0]["scenario_label"] == "Base"
    assert payload["battery_scenario_comparison"][1]["nominal_battery_kwh"] > payload[
        "battery_scenario_comparison"
    ][0]["nominal_battery_kwh"]
    assert "selected_scenario" not in payload
    json.dumps(payload)
