from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from app.tools.layout_tools import (
    build_calculate_panel_capacity_by_area_tool,
    build_calculate_required_area_for_panels_tool,
    build_calculate_row_spacing_for_self_shading_tool,
    build_evaluate_layout_feasibility_tool,
)

# ---------------------------------------------------------------------------
# calculate_panel_capacity_by_area
# ---------------------------------------------------------------------------


def test_capacity_tool_has_expected_name() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    assert tool.name == "calculate_panel_capacity_by_area"
    assert tool.description


def test_capacity_simple_grid_no_spacing_no_margin() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    payload = tool.invoke(
        {
            "usable_width_m": 10.0,
            "usable_length_m": 5.0,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 0.0,
            "allow_rotation": False,
        }
    )
    assert payload["max_panels"] == 20
    assert payload["layout_columns"] == 10
    assert payload["layout_rows"] == 2  # length 5 / panel_length 2 → 2 rows portrait
    assert payload["panel_orientation_used"] == "portrait"
    json.dumps(payload)


def test_capacity_with_spacing_and_margin() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    payload = tool.invoke(
        {
            "usable_width_m": 10.0,
            "usable_length_m": 5.0,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.1,
            "spacing_y_m": 0.1,
            "maintenance_margin_m": 0.5,
            "allow_rotation": False,
        }
    )
    # inner area = 9.0 x 4.0
    # cols = floor((9.0 + 0.1) / (1.0 + 0.1)) = 8
    # rows = floor((4.0 + 0.1) / (2.0 + 0.1)) = 1
    assert payload["layout_columns"] == 8
    assert payload["layout_rows"] == 1
    assert payload["max_panels"] == 8


def test_capacity_allow_rotation_picks_more_panels() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    payload = tool.invoke(
        {
            "usable_width_m": 4.0,
            "usable_length_m": 4.0,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 0.0,
            "allow_rotation": True,
        }
    )
    # Both orientations yield 4×2=8 panels in a 4x4 area; rotation does not hurt.
    assert payload["max_panels"] == 8


def test_capacity_allow_rotation_false_keeps_portrait() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    payload = tool.invoke(
        {
            "usable_width_m": 5.0,
            "usable_length_m": 2.0,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 0.0,
            "allow_rotation": False,
        }
    )
    assert payload["panel_orientation_used"] == "portrait"
    assert payload["max_panels"] == 5


def test_capacity_zero_dimensions_rejected_by_schema() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "usable_width_m": 0.0,
                "usable_length_m": 5.0,
                "panel_width_m": 1.0,
                "panel_length_m": 2.0,
                "spacing_x_m": 0.0,
                "spacing_y_m": 0.0,
                "maintenance_margin_m": 0.0,
                "allow_rotation": False,
            }
        )


def test_capacity_margin_consumes_area_returns_zero_with_warning() -> None:
    tool = build_calculate_panel_capacity_by_area_tool()
    payload = tool.invoke(
        {
            "usable_width_m": 1.0,
            "usable_length_m": 1.0,
            "panel_width_m": 1.0,
            "panel_length_m": 1.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 1.0,
            "allow_rotation": False,
        }
    )
    assert payload["max_panels"] == 0
    assert payload["panel_orientation_used"] is None
    assert any("margin" in w.lower() for w in payload["warnings"])


# ---------------------------------------------------------------------------
# calculate_required_area_for_panels
# ---------------------------------------------------------------------------


def test_required_area_tool_has_expected_name() -> None:
    tool = build_calculate_required_area_for_panels_tool()
    assert tool.name == "calculate_required_area_for_panels"


def test_required_area_compact_layout_for_12_panels() -> None:
    tool = build_calculate_required_area_for_panels_tool()
    payload = tool.invoke(
        {
            "num_panels": 12,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 0.0,
            "allow_rotation": False,
        }
    )
    # cols = ceil(sqrt(12)) = 4; rows = ceil(12/4) = 3
    assert payload["layout_columns"] == 4
    assert payload["layout_rows"] == 3
    assert payload["required_width_m"] == pytest.approx(4.0)
    assert payload["required_length_m"] == pytest.approx(6.0)
    assert payload["required_area_m2"] == pytest.approx(24.0)


def test_required_area_respects_preferred_columns() -> None:
    tool = build_calculate_required_area_for_panels_tool()
    payload = tool.invoke(
        {
            "num_panels": 12,
            "panel_width_m": 1.0,
            "panel_length_m": 2.0,
            "spacing_x_m": 0.0,
            "spacing_y_m": 0.0,
            "maintenance_margin_m": 0.0,
            "preferred_columns": 6,
            "allow_rotation": False,
        }
    )
    assert payload["layout_columns"] == 6
    assert payload["layout_rows"] == 2


def test_required_area_preferred_grid_too_small_raises() -> None:
    tool = build_calculate_required_area_for_panels_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "num_panels": 12,
                "panel_width_m": 1.0,
                "panel_length_m": 2.0,
                "spacing_x_m": 0.0,
                "spacing_y_m": 0.0,
                "maintenance_margin_m": 0.0,
                "preferred_columns": 2,
                "preferred_rows": 2,
                "allow_rotation": False,
            }
        )


def test_required_area_zero_panels_rejected() -> None:
    tool = build_calculate_required_area_for_panels_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "num_panels": 0,
                "panel_width_m": 1.0,
                "panel_length_m": 2.0,
                "spacing_x_m": 0.0,
                "spacing_y_m": 0.0,
                "maintenance_margin_m": 0.0,
                "allow_rotation": False,
            }
        )


# ---------------------------------------------------------------------------
# calculate_row_spacing_for_self_shading
# ---------------------------------------------------------------------------


def test_row_spacing_tool_has_expected_name() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    assert tool.name == "calculate_row_spacing_for_self_shading"


def test_row_spacing_uses_explicit_height_difference() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    payload = tool.invoke(
        {
            "panel_length_m": 2.0,
            "tilt_deg": 30.0,
            "solar_elevation_deg": 45.0,
            "height_difference_m": 1.0,
        }
    )
    expected = 1.0 / math.tan(math.radians(45.0))
    assert payload["recommended_row_spacing_m"] == pytest.approx(expected)
    assert payload["method_used"] == "explicit_height_difference"


def test_row_spacing_geometric_projection() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    payload = tool.invoke(
        {
            "panel_length_m": 2.0,
            "tilt_deg": 30.0,
            "solar_elevation_deg": 30.0,
        }
    )
    expected_height = 2.0 * math.sin(math.radians(30.0))
    expected_shadow = expected_height / math.tan(math.radians(30.0))
    assert payload["recommended_row_spacing_m"] == pytest.approx(expected_shadow)
    assert payload["method_used"] == "geometric_shadow_projection"
    assert any("approximation" in w.lower() for w in payload["warnings"])


def test_row_spacing_warns_for_low_elevation() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    payload = tool.invoke(
        {
            "panel_length_m": 2.0,
            "tilt_deg": 30.0,
            "solar_elevation_deg": 10.0,
        }
    )
    assert any("below 15" in w for w in payload["warnings"])


def test_row_spacing_invalid_tilt_rejected() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "panel_length_m": 2.0,
                "tilt_deg": 0.0,
                "solar_elevation_deg": 30.0,
            }
        )


def test_row_spacing_invalid_elevation_rejected() -> None:
    tool = build_calculate_row_spacing_for_self_shading_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "panel_length_m": 2.0,
                "tilt_deg": 30.0,
                "solar_elevation_deg": 0.0,
            }
        )


# ---------------------------------------------------------------------------
# evaluate_layout_feasibility
# ---------------------------------------------------------------------------


def test_feasibility_tool_has_expected_name() -> None:
    tool = build_evaluate_layout_feasibility_tool()
    assert tool.name == "evaluate_layout_feasibility"


def test_feasibility_when_layout_supports_demand() -> None:
    tool = build_evaluate_layout_feasibility_tool()
    payload = tool.invoke(
        {
            "required_panels_for_energy": 10,
            "max_panels_by_layout": 12,
        }
    )
    assert payload["is_physically_feasible"] is True
    assert payload["panel_gap"] == -2
    assert payload["estimated_annual_energy_with_layout_kwh"] is None
    assert payload["coverage_of_target_pct"] is None
    assert any("supports" in r for r in payload["recommendations"])


def test_feasibility_when_layout_short_of_demand() -> None:
    tool = build_evaluate_layout_feasibility_tool()
    payload = tool.invoke(
        {
            "required_panels_for_energy": 12,
            "max_panels_by_layout": 9,
            "annual_energy_per_panel_kwh": 450.0,
            "target_annual_energy_kwh": 5400.0,
        }
    )
    assert payload["is_physically_feasible"] is False
    assert payload["panel_gap"] == 3
    assert payload["estimated_annual_energy_with_layout_kwh"] == pytest.approx(4050.0)
    assert payload["coverage_of_target_pct"] == pytest.approx(75.0)
    assert any("short by 3" in r for r in payload["recommendations"])


def test_feasibility_warns_when_target_without_per_panel() -> None:
    tool = build_evaluate_layout_feasibility_tool()
    payload = tool.invoke(
        {
            "required_panels_for_energy": 12,
            "max_panels_by_layout": 9,
            "target_annual_energy_kwh": 5400.0,
        }
    )
    assert payload["coverage_of_target_pct"] is None
    assert any("annual_energy_per_panel_kwh" in w for w in payload["warnings"])


def test_feasibility_zero_required_panels_rejected() -> None:
    tool = build_evaluate_layout_feasibility_tool()
    with pytest.raises(ValidationError):
        tool.invoke(
            {
                "required_panels_for_energy": 0,
                "max_panels_by_layout": 5,
            }
        )
