from __future__ import annotations

import json

import pytest

from app.core.errors import ValidationAppError
from app.tools.solar_calculation_tools import (
    build_calculate_annual_consumption_tool,
    build_calculate_coverage_tool,
    build_calculate_system_kwp_tool,
    build_estimate_panels_for_future_target_tool,
)


def test_calculate_system_kwp_tool_has_expected_name() -> None:
    tool = build_calculate_system_kwp_tool()
    assert tool.name == "calculate_system_kwp"
    assert tool.description


def test_calculate_annual_consumption_tool_has_expected_schema() -> None:
    tool = build_calculate_annual_consumption_tool()
    schema = tool.args_schema.model_json_schema()
    assert "monthly_consumption_kwh" in schema["properties"]
    assert "annual_consumption_kwh" in schema["properties"]


def test_calculate_coverage_tool_has_expected_name() -> None:
    tool = build_calculate_coverage_tool()
    assert tool.name == "calculate_coverage"


def test_estimate_panels_for_future_target_tool_has_expected_name() -> None:
    tool = build_estimate_panels_for_future_target_tool()
    assert tool.name == "estimate_panels_for_future_target"


def test_calculate_system_kwp_returns_serializable_output() -> None:
    tool = build_calculate_system_kwp_tool()
    payload = tool.invoke({"num_panels": 12, "panel_power_w": 455.0})

    assert payload["system_kwp"] == pytest.approx(5.46)
    json.dumps(payload)


def test_calculate_annual_consumption_sums_explicit_months() -> None:
    tool = build_calculate_annual_consumption_tool()
    payload = tool.invoke({"monthly_consumption_kwh": [100.0] * 12})

    assert payload["annual_consumption_kwh"] == pytest.approx(1200.0)
    assert payload["source_field_used"] == "monthly_consumption_kwh"


def test_calculate_annual_consumption_rejects_inconsistent_inputs() -> None:
    tool = build_calculate_annual_consumption_tool()
    with pytest.raises(ValidationAppError):
        tool.invoke(
            {
                "monthly_consumption_kwh": [100.0] * 12,
                "annual_consumption_kwh": 900.0,
            }
        )


def test_calculate_coverage_returns_serializable_metrics() -> None:
    tool = build_calculate_coverage_tool()
    payload = tool.invoke(
        {
            "annual_energy_kwh": 6500.0,
            "annual_consumption_kwh": 5400.0,
        }
    )

    assert payload["coverage_pct"] == pytest.approx((6500.0 / 5400.0) * 100.0)
    assert payload["surplus_or_deficit_kwh"] == pytest.approx(1100.0)
    assert payload["interpretation_metrics"]["production_to_consumption_ratio"] == pytest.approx(
        6500.0 / 5400.0
    )
    json.dumps(payload)


def test_estimate_panels_for_future_target_returns_serializable_output() -> None:
    tool = build_estimate_panels_for_future_target_tool()
    payload = tool.invoke(
        {
            "target_energy_year_n_kwh": 6000.0,
            "energy_per_panel_year1_kwh": 450.0,
            "degradation_rate_pct": 0.5,
            "target_year": 25,
            "safety_margin_pct": 10.0,
        }
    )

    assert payload["recommended_panels"] >= 1
    assert payload["required_year1_energy_kwh"] > 6000.0
    assert payload["calculation_metadata"]["safety_margin_pct"] == pytest.approx(10.0)
    json.dumps(payload)
