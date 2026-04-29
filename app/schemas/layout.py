"""Schemas for the physical-layout subsystem.

Reasoning rules (see ``AGENTS.md``):

- Every dimension is supplied explicitly by the agent. The schemas
  refuse zero or negative geometry. Default panel sizes, default
  spacings, and default maintenance margins are forbidden.
- The ``allow_rotation`` flag is a geometric switch the agent may set
  consciously; it is not a hidden default.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PanelOrientation(StrEnum):
    """Recognized panel orientations relative to the surface frame."""

    portrait = "portrait"
    landscape = "landscape"


# Used as input flag: tells the layout tool whether it may pick the best
# orientation matematically. Not a default.
LayoutMode = Literal["portrait", "landscape", "auto"]


# ---------------------------------------------------------------------------
# 1) calculate_panel_capacity_by_area
# ---------------------------------------------------------------------------


class PanelCapacityByAreaRequest(BaseModel):
    """Explicit input for ``calculate_panel_capacity_by_area``."""

    model_config = ConfigDict(extra="forbid")

    usable_width_m: float = Field(gt=0.0)
    usable_length_m: float = Field(gt=0.0)
    panel_width_m: float = Field(gt=0.0)
    panel_length_m: float = Field(gt=0.0)
    spacing_x_m: float = Field(ge=0.0)
    spacing_y_m: float = Field(ge=0.0)
    maintenance_margin_m: float = Field(ge=0.0)
    allow_rotation: bool


class PanelCapacityByAreaResult(BaseModel):
    """Normalized output of ``calculate_panel_capacity_by_area``."""

    model_config = ConfigDict(extra="forbid")

    max_panels: int
    layout_rows: int
    layout_columns: int
    panel_orientation_used: PanelOrientation | None
    used_width_m: float
    used_length_m: float
    used_area_m2: float
    usable_area_m2: float
    unused_area_m2: float
    method_used: str = "rectangular_grid_fit"
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2) calculate_required_area_for_panels
# ---------------------------------------------------------------------------


class RequiredAreaRequest(BaseModel):
    """Explicit input for ``calculate_required_area_for_panels``."""

    model_config = ConfigDict(extra="forbid")

    num_panels: int = Field(gt=0)
    panel_width_m: float = Field(gt=0.0)
    panel_length_m: float = Field(gt=0.0)
    spacing_x_m: float = Field(ge=0.0)
    spacing_y_m: float = Field(ge=0.0)
    maintenance_margin_m: float = Field(ge=0.0)
    preferred_columns: int | None = Field(default=None, gt=0)
    preferred_rows: int | None = Field(default=None, gt=0)
    allow_rotation: bool

    @model_validator(mode="after")
    def validate_preferred(self) -> RequiredAreaRequest:
        if (
            self.preferred_columns is not None
            and self.preferred_rows is not None
            and self.preferred_columns * self.preferred_rows < self.num_panels
        ):
            raise ValueError(
                "preferred_columns × preferred_rows must be at least num_panels."
            )
        return self


class RequiredAreaResult(BaseModel):
    """Normalized output of ``calculate_required_area_for_panels``."""

    model_config = ConfigDict(extra="forbid")

    required_width_m: float
    required_length_m: float
    required_area_m2: float
    layout_rows: int
    layout_columns: int
    panel_orientation_used: PanelOrientation
    method_used: str = "rectangular_compact_layout"
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 3) calculate_row_spacing_for_self_shading
# ---------------------------------------------------------------------------


class RowSpacingRequest(BaseModel):
    """Explicit input for ``calculate_row_spacing_for_self_shading``."""

    model_config = ConfigDict(extra="forbid")

    panel_length_m: float = Field(gt=0.0)
    tilt_deg: float = Field(gt=0.0, le=90.0)
    solar_elevation_deg: float = Field(gt=0.0, le=90.0)
    height_difference_m: float | None = Field(default=None, ge=0.0)


class RowSpacingResult(BaseModel):
    """Normalized output of ``calculate_row_spacing_for_self_shading``."""

    model_config = ConfigDict(extra="forbid")

    recommended_row_spacing_m: float
    shadow_length_m: float
    method_used: str = "geometric_shadow_projection"
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4) evaluate_layout_feasibility
# ---------------------------------------------------------------------------


class LayoutFeasibilityRequest(BaseModel):
    """Explicit input for ``evaluate_layout_feasibility``."""

    model_config = ConfigDict(extra="forbid")

    required_panels_for_energy: int = Field(gt=0)
    max_panels_by_layout: int = Field(ge=0)
    annual_energy_per_panel_kwh: float | None = Field(default=None, gt=0.0)
    target_annual_energy_kwh: float | None = Field(default=None, gt=0.0)


class LayoutFeasibilityResult(BaseModel):
    """Normalized output of ``evaluate_layout_feasibility``."""

    model_config = ConfigDict(extra="forbid")

    is_physically_feasible: bool
    panel_gap: int
    estimated_annual_energy_with_layout_kwh: float | None
    coverage_of_target_pct: float | None
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "LayoutFeasibilityRequest",
    "LayoutFeasibilityResult",
    "LayoutMode",
    "PanelCapacityByAreaRequest",
    "PanelCapacityByAreaResult",
    "PanelOrientation",
    "RequiredAreaRequest",
    "RequiredAreaResult",
    "RowSpacingRequest",
    "RowSpacingResult",
]
