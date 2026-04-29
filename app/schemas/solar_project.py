"""Schemas for the solar project, geocoding, and PVGIS subsystems.

Reasoning-first contract: every input below MUST be supplied explicitly.
The service does NOT fall back to PVGIS server-side defaults silently.
If the agent does not have a value for ``tilt_deg`` / ``azimuth_deg`` /
``system_loss_pct``, it must pick one via ``get_assumption_candidates``
(or ask the user) and pass it here. Defaults baked in this layer are
forbidden.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PvTechnology = Literal["crystSi", "crystSi2025", "CIS", "CdTe", "Unknown"]
MountingPlace = Literal["free", "building"]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]


class GeocodingRequest(BaseModel):
    """Explicit geocoding input.

    The geocoding layer does not interpret intent or repair the query
    semantically. It only forwards an explicit location string plus
    optional provider hints.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    location_text: str = Field(
        min_length=1,
        description="Explicit textual location to geocode, as provided by the user or agent.",
    )
    country_hint: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Optional ISO 3166-1 alpha-2 country hint, for example ES.",
    )
    language: str | None = Field(
        default=None,
        min_length=2,
        description="Optional response language hint forwarded to the geocoding provider.",
    )


class GeocodingCandidate(BaseModel):
    """One ranked geocoding result returned by the provider."""

    model_config = ConfigDict(extra="forbid")

    normalized_name: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    municipality: str | None = None
    province: str | None = None
    autonomous_community: str | None = None
    country: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class GeocodingResult(GeocodingCandidate):
    """Normalized geocoding output used by tools and subagents."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = "Nominatim / OpenStreetMap"
    source_url: str
    warnings: list[str] = Field(default_factory=list)
    candidates: list[GeocodingCandidate] | None = None


class PVCalcRequest(BaseModel):
    """Inputs for PVGIS PVcalc.

    All angles in degrees. Azimuth follows PVGIS convention:
    0 = south, 90 = west, -90 = east.
    """

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90.0, le=90.0, description="Latitude in decimal degrees.")
    lon: float = Field(ge=-180.0, le=180.0, description="Longitude in decimal degrees.")
    peakpower_kwp: float = Field(gt=0.0, description="Nominal PV system power in kWp.")
    system_loss_pct: float = Field(
        ge=0.0,
        le=100.0,
        description=(
            "Aggregate system loss percentage. Must be supplied explicitly by the agent — "
            "either from user input or from a chosen assumption candidate."
        ),
    )
    tilt_deg: float = Field(
        ge=0.0,
        le=90.0,
        description="Tilt angle from horizontal. Must be explicit.",
    )
    azimuth_deg: float = Field(
        ge=-180.0,
        le=180.0,
        description="Azimuth (PVGIS aspect): 0=south, 90=west, -90=east. Must be explicit.",
    )
    pv_technology: PvTechnology | None = Field(
        default=None,
        description="Optional override of PV technology. None lets PVGIS pick its standard cell type.",
    )
    mounting: MountingPlace | None = Field(
        default=None,
        description="Optional mounting place. None lets PVGIS pick its standard mounting.",
    )
    use_horizon: bool | None = Field(
        default=None,
        description="If set, instructs PVGIS whether to apply the local horizon shading model.",
    )


class PVMonthlyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: int = Field(ge=1, le=12)
    energy_kwh: float
    in_plane_irradiation_kwh_per_m2: float


class PVCalcResult(BaseModel):
    """Normalized PVGIS PVcalc response.

    Keeps the source-of-truth identifiers so downstream subagents can cite
    PVGIS in the natural trace.
    """

    model_config = ConfigDict(extra="forbid")

    annual_energy_kwh: float
    monthly: list[PVMonthlyEntry]
    annual_in_plane_irradiation_kwh_per_m2: float | None = None
    source_name: str = "PVGIS"
    source_version: str = "v5_3"
    source_url: str | None = None
    raw_metadata: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class SystemKwpRequest(BaseModel):
    """Explicit inputs for installed peak power calculation."""

    model_config = ConfigDict(extra="forbid")

    num_panels: int = Field(gt=0, description="Number of PV modules in the array.")
    panel_power_w: float = Field(
        gt=0.0,
        description="Nominal panel power in watts. Must be explicit.",
    )


class SystemKwpResult(BaseModel):
    """Deterministic installed peak power result."""

    model_config = ConfigDict(extra="forbid")

    system_kwp: float


class AnnualConsumptionRequest(BaseModel):
    """Explicit inputs for annual electricity consumption."""

    model_config = ConfigDict(extra="forbid")

    monthly_consumption_kwh: list[NonNegativeFloat] | None = Field(
        default=None,
        min_length=12,
        max_length=12,
        description="Monthly electricity consumption in kWh for the full year.",
    )
    annual_consumption_kwh: float | None = Field(
        default=None,
        ge=0.0,
        description="Explicit annual electricity consumption in kWh.",
    )

    @model_validator(mode="after")
    def validate_at_least_one_consumption_source(self) -> AnnualConsumptionRequest:
        if self.monthly_consumption_kwh is None and self.annual_consumption_kwh is None:
            raise ValueError(
                "At least one explicit consumption source is required: "
                "monthly_consumption_kwh or annual_consumption_kwh."
            )
        return self


class AnnualConsumptionResult(BaseModel):
    """Normalized annual consumption output."""

    model_config = ConfigDict(extra="forbid")

    annual_consumption_kwh: float
    source_field_used: str
    warnings: list[str] = Field(default_factory=list)


class CoverageRequest(BaseModel):
    """Explicit inputs for annual production vs consumption coverage."""

    model_config = ConfigDict(extra="forbid")

    annual_energy_kwh: float = Field(ge=0.0)
    annual_consumption_kwh: float = Field(gt=0.0)


class CoverageResult(BaseModel):
    """Deterministic annual coverage metrics."""

    model_config = ConfigDict(extra="forbid")

    coverage_pct: float
    surplus_or_deficit_kwh: float
    interpretation_metrics: dict[str, float]


class PanelsForFutureTargetRequest(BaseModel):
    """Explicit inputs for future-year panel requirement calculation."""

    model_config = ConfigDict(extra="forbid")

    target_energy_year_n_kwh: float = Field(
        gt=0.0,
        description="Target annual energy that must still be produced in the target year.",
    )
    energy_per_panel_year1_kwh: float = Field(
        gt=0.0,
        description="Year-1 annual energy output per panel in kWh.",
    )
    degradation_rate_pct: float = Field(
        ge=0.0,
        lt=100.0,
        description="Annual degradation rate in percent, for example 0.5 for 0.5%/year.",
    )
    target_year: int = Field(
        ge=1,
        description="Target operating year for the energy objective.",
    )
    safety_margin_pct: float = Field(
        ge=0.0,
        description="Explicit safety margin in percent. Use 0 when no margin is desired.",
    )


class PanelsForFutureTargetResult(BaseModel):
    """Normalized panel-count recommendation for a future-year target."""

    model_config = ConfigDict(extra="forbid")

    required_year1_energy_kwh: float
    recommended_panels: int
    calculation_metadata: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
