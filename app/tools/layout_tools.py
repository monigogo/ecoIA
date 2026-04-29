"""Deterministic layout tools for physical PV-panel placement.

Reasoning rules (see ``AGENTS.md``):

- All dimensions arrive explicitly. The tools never invent panel size,
  spacing, or maintenance margin. If anything is missing the agent must
  ask the user or call ``get_assumption_candidates``.
- Rotation is a geometric switch, not a hidden default. The agent
  decides whether ``allow_rotation`` is acceptable for the user's
  installation (e.g. a tilted roof may not allow it).
- The tools compute geometry. They do NOT decide aesthetic layout, do
  NOT decide solar elevation, and do NOT replace a professional
  shading study.
"""

from __future__ import annotations

import math
from typing import Any

from langchain_core.tools import tool

from app.schemas.layout import (
    LayoutFeasibilityRequest,
    LayoutFeasibilityResult,
    PanelCapacityByAreaRequest,
    PanelCapacityByAreaResult,
    PanelOrientation,
    RequiredAreaRequest,
    RequiredAreaResult,
    RowSpacingRequest,
    RowSpacingResult,
)

# ---------------------------------------------------------------------------
# Internal geometry helpers
# ---------------------------------------------------------------------------


def _grid_fit(
    *,
    inner_width_m: float,
    inner_length_m: float,
    panel_width_m: float,
    panel_length_m: float,
    spacing_x_m: float,
    spacing_y_m: float,
) -> tuple[int, int]:
    """Number of (rows, columns) of panels that fit a rectangular inner area.

    Convention: ``columns`` are along the width axis, ``rows`` along
    the length axis. ``panel_width_m`` aligns with the width axis.
    """

    if inner_width_m < panel_width_m or inner_length_m < panel_length_m:
        return 0, 0
    columns = int((inner_width_m + spacing_x_m) // (panel_width_m + spacing_x_m))
    rows = int((inner_length_m + spacing_y_m) // (panel_length_m + spacing_y_m))
    return rows, columns


def _used_envelope(
    *,
    rows: int,
    columns: int,
    panel_width_m: float,
    panel_length_m: float,
    spacing_x_m: float,
    spacing_y_m: float,
    margin_m: float,
) -> tuple[float, float]:
    if rows <= 0 or columns <= 0:
        return 0.0, 0.0
    used_width = columns * panel_width_m + max(columns - 1, 0) * spacing_x_m + 2.0 * margin_m
    used_length = rows * panel_length_m + max(rows - 1, 0) * spacing_y_m + 2.0 * margin_m
    return used_width, used_length


# ---------------------------------------------------------------------------
# 1) calculate_panel_capacity_by_area
# ---------------------------------------------------------------------------


def build_calculate_panel_capacity_by_area_tool():
    """Return a deterministic LangChain tool for capacity-by-area."""

    @tool(
        "calculate_panel_capacity_by_area",
        args_schema=PanelCapacityByAreaRequest,
    )
    def calculate_panel_capacity_by_area(
        usable_width_m: float,
        usable_length_m: float,
        panel_width_m: float,
        panel_length_m: float,
        spacing_x_m: float,
        spacing_y_m: float,
        maintenance_margin_m: float,
        allow_rotation: bool,
    ) -> dict[str, Any]:
        """Compute the maximum number of panels that fit a rectangular area."""

        inner_width = usable_width_m - 2.0 * maintenance_margin_m
        inner_length = usable_length_m - 2.0 * maintenance_margin_m

        warnings: list[str] = []
        if inner_width <= 0 or inner_length <= 0:
            warnings.append(
                "Maintenance margin consumes the entire usable area; no panels fit."
            )
            response = PanelCapacityByAreaResult(
                max_panels=0,
                layout_rows=0,
                layout_columns=0,
                panel_orientation_used=None,
                used_width_m=0.0,
                used_length_m=0.0,
                used_area_m2=0.0,
                usable_area_m2=usable_width_m * usable_length_m,
                unused_area_m2=usable_width_m * usable_length_m,
                warnings=warnings,
            )
            return response.model_dump()

        candidates: list[
            tuple[int, int, int, PanelOrientation, float, float]
        ] = []

        rows_p, cols_p = _grid_fit(
            inner_width_m=inner_width,
            inner_length_m=inner_length,
            panel_width_m=panel_width_m,
            panel_length_m=panel_length_m,
            spacing_x_m=spacing_x_m,
            spacing_y_m=spacing_y_m,
        )
        if rows_p > 0 and cols_p > 0:
            used_w, used_l = _used_envelope(
                rows=rows_p,
                columns=cols_p,
                panel_width_m=panel_width_m,
                panel_length_m=panel_length_m,
                spacing_x_m=spacing_x_m,
                spacing_y_m=spacing_y_m,
                margin_m=maintenance_margin_m,
            )
            candidates.append(
                (rows_p * cols_p, rows_p, cols_p, PanelOrientation.portrait, used_w, used_l)
            )

        if allow_rotation:
            rows_l, cols_l = _grid_fit(
                inner_width_m=inner_width,
                inner_length_m=inner_length,
                panel_width_m=panel_length_m,
                panel_length_m=panel_width_m,
                spacing_x_m=spacing_x_m,
                spacing_y_m=spacing_y_m,
            )
            if rows_l > 0 and cols_l > 0:
                used_w, used_l = _used_envelope(
                    rows=rows_l,
                    columns=cols_l,
                    panel_width_m=panel_length_m,
                    panel_length_m=panel_width_m,
                    spacing_x_m=spacing_x_m,
                    spacing_y_m=spacing_y_m,
                    margin_m=maintenance_margin_m,
                )
                candidates.append(
                    (
                        rows_l * cols_l,
                        rows_l,
                        cols_l,
                        PanelOrientation.landscape,
                        used_w,
                        used_l,
                    )
                )

        if not candidates:
            warnings.append(
                "Panel does not fit the usable area for any allowed orientation."
            )
            response = PanelCapacityByAreaResult(
                max_panels=0,
                layout_rows=0,
                layout_columns=0,
                panel_orientation_used=None,
                used_width_m=0.0,
                used_length_m=0.0,
                used_area_m2=0.0,
                usable_area_m2=usable_width_m * usable_length_m,
                unused_area_m2=usable_width_m * usable_length_m,
                warnings=warnings,
            )
            return response.model_dump()

        best = max(candidates, key=lambda item: item[0])
        max_panels, rows, cols, orientation, used_w, used_l = best
        usable_area = usable_width_m * usable_length_m
        used_area = used_w * used_l

        response = PanelCapacityByAreaResult(
            max_panels=max_panels,
            layout_rows=rows,
            layout_columns=cols,
            panel_orientation_used=orientation,
            used_width_m=used_w,
            used_length_m=used_l,
            used_area_m2=used_area,
            usable_area_m2=usable_area,
            unused_area_m2=max(usable_area - used_area, 0.0),
            warnings=warnings,
        )

        return response.model_dump()

    return calculate_panel_capacity_by_area


# ---------------------------------------------------------------------------
# 2) calculate_required_area_for_panels
# ---------------------------------------------------------------------------


def _layout_dimensions(
    *,
    rows: int,
    columns: int,
    panel_width_m: float,
    panel_length_m: float,
    spacing_x_m: float,
    spacing_y_m: float,
    margin_m: float,
) -> tuple[float, float, float]:
    width = columns * panel_width_m + max(columns - 1, 0) * spacing_x_m + 2.0 * margin_m
    length = rows * panel_length_m + max(rows - 1, 0) * spacing_y_m + 2.0 * margin_m
    return width, length, width * length


def build_calculate_required_area_for_panels_tool():
    """Return a deterministic LangChain tool for required-area-for-panels."""

    @tool(
        "calculate_required_area_for_panels",
        args_schema=RequiredAreaRequest,
    )
    def calculate_required_area_for_panels(
        num_panels: int,
        panel_width_m: float,
        panel_length_m: float,
        spacing_x_m: float,
        spacing_y_m: float,
        maintenance_margin_m: float,
        allow_rotation: bool,
        preferred_columns: int | None = None,
        preferred_rows: int | None = None,
    ) -> dict[str, Any]:
        """Compute the area required to lay out a given number of panels."""

        if preferred_columns is not None and preferred_rows is not None:
            cols = preferred_columns
            rows = preferred_rows
        elif preferred_columns is not None:
            cols = preferred_columns
            rows = math.ceil(num_panels / cols)
        elif preferred_rows is not None:
            rows = preferred_rows
            cols = math.ceil(num_panels / rows)
        else:
            cols = math.ceil(math.sqrt(num_panels))
            rows = math.ceil(num_panels / cols)

        candidates: list[tuple[float, float, float, PanelOrientation]] = []

        width_p, length_p, area_p = _layout_dimensions(
            rows=rows,
            columns=cols,
            panel_width_m=panel_width_m,
            panel_length_m=panel_length_m,
            spacing_x_m=spacing_x_m,
            spacing_y_m=spacing_y_m,
            margin_m=maintenance_margin_m,
        )
        candidates.append((width_p, length_p, area_p, PanelOrientation.portrait))

        if allow_rotation:
            width_l, length_l, area_l = _layout_dimensions(
                rows=rows,
                columns=cols,
                panel_width_m=panel_length_m,
                panel_length_m=panel_width_m,
                spacing_x_m=spacing_x_m,
                spacing_y_m=spacing_y_m,
                margin_m=maintenance_margin_m,
            )
            candidates.append((width_l, length_l, area_l, PanelOrientation.landscape))

        best = min(candidates, key=lambda item: item[2])
        width, length, area, orientation = best

        warnings: list[str] = []
        if rows * cols > num_panels:
            warnings.append(
                f"Layout reserves space for {rows * cols} panels but only {num_panels} are needed; "
                "the trailing positions are spare."
            )

        response = RequiredAreaResult(
            required_width_m=width,
            required_length_m=length,
            required_area_m2=area,
            layout_rows=rows,
            layout_columns=cols,
            panel_orientation_used=orientation,
            warnings=warnings,
        )

        return response.model_dump()

    return calculate_required_area_for_panels


# ---------------------------------------------------------------------------
# 3) calculate_row_spacing_for_self_shading
# ---------------------------------------------------------------------------


def build_calculate_row_spacing_for_self_shading_tool():
    """Return a deterministic LangChain tool for row spacing."""

    @tool(
        "calculate_row_spacing_for_self_shading",
        args_schema=RowSpacingRequest,
    )
    def calculate_row_spacing_for_self_shading(
        panel_length_m: float,
        tilt_deg: float,
        solar_elevation_deg: float,
        height_difference_m: float | None = None,
    ) -> dict[str, Any]:
        """Estimate row spacing required to limit self-shading at a given solar elevation."""

        tilt_rad = math.radians(tilt_deg)
        elevation_rad = math.radians(solar_elevation_deg)

        if height_difference_m is not None:
            effective_height = height_difference_m
            method_used = "explicit_height_difference"
        else:
            effective_height = panel_length_m * math.sin(tilt_rad)
            method_used = "geometric_shadow_projection"

        shadow_length = effective_height / math.tan(elevation_rad)
        recommended = max(shadow_length, 0.0)

        warnings = [
            "Geometric approximation; ignores diffuse irradiance, partial shading, and "
            "site-specific obstacles. It does not replace a professional shading study.",
        ]
        if solar_elevation_deg < 15.0:
            warnings.append(
                "Solar elevation below 15° produces very long shadows; verify whether the "
                "chosen elevation is the right design criterion (often the winter solstice noon)."
            )

        response = RowSpacingResult(
            recommended_row_spacing_m=recommended,
            shadow_length_m=shadow_length,
            method_used=method_used,
            warnings=warnings,
        )

        return response.model_dump()

    return calculate_row_spacing_for_self_shading


# ---------------------------------------------------------------------------
# 4) evaluate_layout_feasibility
# ---------------------------------------------------------------------------


def build_evaluate_layout_feasibility_tool():
    """Return a deterministic LangChain tool for layout feasibility comparison."""

    @tool(
        "evaluate_layout_feasibility",
        args_schema=LayoutFeasibilityRequest,
    )
    def evaluate_layout_feasibility(
        required_panels_for_energy: int,
        max_panels_by_layout: int,
        annual_energy_per_panel_kwh: float | None = None,
        target_annual_energy_kwh: float | None = None,
    ) -> dict[str, Any]:
        """Compare energy-required panels against physically feasible panels."""

        is_feasible = max_panels_by_layout >= required_panels_for_energy
        panel_gap = required_panels_for_energy - max_panels_by_layout

        estimated_energy: float | None = None
        coverage_pct: float | None = None
        warnings: list[str] = []
        recommendations: list[str] = []

        if annual_energy_per_panel_kwh is not None:
            estimated_energy = max_panels_by_layout * annual_energy_per_panel_kwh
            if target_annual_energy_kwh is not None:
                coverage_pct = (estimated_energy / target_annual_energy_kwh) * 100.0
        elif target_annual_energy_kwh is not None:
            warnings.append(
                "target_annual_energy_kwh was supplied but annual_energy_per_panel_kwh "
                "was not; coverage cannot be computed without both."
            )

        if is_feasible:
            recommendations.append(
                "Physical layout supports the energy-required panel count; "
                "the user can install the full set."
            )
        else:
            recommendations.append(
                f"Physical layout is short by {panel_gap} panel(s); consider one of: "
                "reduce target consumption, accept partial coverage, increase usable area, "
                "or revisit spacing/margin assumptions."
            )

        if estimated_energy is None:
            warnings.append(
                "Estimated annual energy with the layout was not computed because "
                "annual_energy_per_panel_kwh was not supplied."
            )

        response = LayoutFeasibilityResult(
            is_physically_feasible=is_feasible,
            panel_gap=panel_gap,
            estimated_annual_energy_with_layout_kwh=estimated_energy,
            coverage_of_target_pct=coverage_pct,
            recommendations=recommendations,
            warnings=warnings,
        )

        return response.model_dump()

    return evaluate_layout_feasibility


# Default exports for agent construction.
calculate_panel_capacity_by_area = build_calculate_panel_capacity_by_area_tool()
calculate_required_area_for_panels = build_calculate_required_area_for_panels_tool()
calculate_row_spacing_for_self_shading = (
    build_calculate_row_spacing_for_self_shading_tool()
)
evaluate_layout_feasibility = build_evaluate_layout_feasibility_tool()


__all__ = [
    "build_calculate_panel_capacity_by_area_tool",
    "build_calculate_required_area_for_panels_tool",
    "build_calculate_row_spacing_for_self_shading_tool",
    "build_evaluate_layout_feasibility_tool",
    "calculate_panel_capacity_by_area",
    "calculate_required_area_for_panels",
    "calculate_row_spacing_for_self_shading",
    "evaluate_layout_feasibility",
]
