from __future__ import annotations

import json

import pytest

from app.tools.degradation_tools import (
    build_calculate_degradation_projection_tool,
    build_calculate_lifetime_threshold_tool,
    build_compare_degradation_scenarios_tool,
)


def test_calculate_degradation_projection_tool_has_expected_name() -> None:
    tool = build_calculate_degradation_projection_tool()
    assert tool.name == "calculate_degradation_projection"
    assert tool.description


def test_calculate_lifetime_threshold_tool_has_expected_name() -> None:
    tool = build_calculate_lifetime_threshold_tool()
    assert tool.name == "calculate_lifetime_threshold"


def test_compare_degradation_scenarios_tool_has_expected_name() -> None:
    tool = build_compare_degradation_scenarios_tool()
    assert tool.name == "compare_degradation_scenarios"


def test_calculate_degradation_projection_returns_serializable_curve() -> None:
    tool = build_calculate_degradation_projection_tool()
    payload = tool.invoke(
        {
            "annual_energy_year1_kwh": 7000.0,
            "degradation_rate_pct": 0.5,
            "years": 3,
        }
    )

    assert len(payload["yearly_projection"]) == 3
    assert payload["yearly_projection"][0]["annual_energy_kwh"] == pytest.approx(7000.0)
    assert payload["yearly_projection"][1]["annual_energy_kwh"] == pytest.approx(6965.0)
    assert payload["yearly_projection"][2]["cumulative_energy_kwh"] > 0.0
    json.dumps(payload)


def test_calculate_lifetime_threshold_handles_zero_degradation() -> None:
    tool = build_calculate_lifetime_threshold_tool()
    payload = tool.invoke({"degradation_rate_pct": 0.0, "threshold_pct": 80.0})

    assert payload["estimated_year_reaching_threshold"] is None
    assert payload["warnings"] == ["The threshold is not reached under zero annual degradation."]


def test_compare_degradation_scenarios_returns_all_candidates_without_selecting_one() -> None:
    tool = build_compare_degradation_scenarios_tool()
    payload = tool.invoke(
        {
            "annual_energy_year1_kwh": 7000.0,
            "scenario_candidates": [
                {
                    "scenario_id": "central",
                    "scenario_label": "Central",
                    "degradation_rate_pct": 0.5,
                },
                {
                    "scenario_id": "conservative",
                    "scenario_label": "Conservative",
                    "degradation_rate_pct": 0.8,
                },
            ],
            "years": 2,
        }
    )

    assert len(payload["comparison"]) == 2
    assert "selected_candidate" not in payload
    assert payload["comparison"][0]["scenario_id"] == "central"
    assert payload["comparison"][1]["final_year_energy_kwh"] < payload["comparison"][0][
        "final_year_energy_kwh"
    ]
    json.dumps(payload)
