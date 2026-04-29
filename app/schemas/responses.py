"""Response schemas emitted by tools and higher-level app surfaces."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SolarProductionEstimateResponse(BaseModel):
    """Serialized output returned by the PVGIS production tool."""

    model_config = ConfigDict(extra="forbid")

    annual_energy_kwh: float
    monthly_energy_kwh: list[float] = Field(
        description="Monthly PV energy output in kWh, ordered from January to December.",
    )
    monthly_in_plane_irradiation: list[float] = Field(
        description="Monthly plane-of-array irradiation in kWh/m2, ordered from January to December.",
    )
    source_name: str
    source_version: str
    raw_metadata: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
