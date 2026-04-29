"""Schemas for explicit RdTools-compatible validation and analysis."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EnergyUnit = Literal["Wh", "kWh"]
PowerUnit = Literal["W", "kW"]
IrradianceUnit = Literal["W/m2", "kW/m2"]
TemperatureUnit = Literal["C"]
RdtoolsNormalizationMethod = Literal["expected_power", "pvwatts"]
RdtoolsAnalysisMode = Literal["degradation"]


class RdtoolsColumnMapping(BaseModel):
    """Explicit semantic mapping for a PV time-series CSV."""

    model_config = ConfigDict(extra="forbid")

    timestamp_column: str = Field(min_length=1)
    energy_column: str | None = None
    power_column: str | None = None
    expected_power_column: str | None = None
    irradiance_column: str = Field(min_length=1)
    temperature_column: str | None = None
    availability_column: str | None = None

    @model_validator(mode="after")
    def validate_energy_or_power(self) -> RdtoolsColumnMapping:
        provided = [self.energy_column is not None, self.power_column is not None]
        if sum(provided) != 1:
            raise ValueError(
                "Provide exactly one production signal mapping: energy_column or power_column."
            )
        return self


class ValidateRdtoolsCsvRequest(BaseModel):
    """Explicit inputs for RdTools CSV validation."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str = Field(min_length=1)
    column_mapping: RdtoolsColumnMapping | None = None


class ValidateRdtoolsCsvResult(BaseModel):
    """Normalized RdTools CSV validation result."""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    detected_columns: list[str]
    missing_columns: list[str]
    time_range: dict[str, str] | None = None
    row_count: int
    data_quality_warnings: list[str] = Field(default_factory=list)
    recommended_mapping: dict[str, str] | None = None


class RdtoolsSystemMetadata(BaseModel):
    """Explicit units required to normalize a PV dataset for RdTools."""

    model_config = ConfigDict(extra="forbid")

    energy_unit: EnergyUnit | None = None
    power_unit: PowerUnit | None = None
    expected_power_unit: PowerUnit | None = None
    irradiance_unit: IrradianceUnit
    temperature_unit: TemperatureUnit | None = None


class RdtoolsPvwattsConfig(BaseModel):
    """Explicit PVWatts normalization inputs used by RdTools."""

    model_config = ConfigDict(extra="forbid")

    power_dc_rated_w: float = Field(gt=0.0)
    poa_global_ref_w_per_m2: float = Field(gt=0.0)
    temperature_cell_ref_c: float | None = None
    gamma_pdc_per_c: float | None = None

    @model_validator(mode="after")
    def validate_temperature_pair(self) -> RdtoolsPvwattsConfig:
        provided = [
            self.temperature_cell_ref_c is not None,
            self.gamma_pdc_per_c is not None,
        ]
        if sum(provided) not in {0, 2}:
            raise ValueError(
                "temperature_cell_ref_c and gamma_pdc_per_c must be supplied together."
            )
        return self


class AnalyzeExistingInstallationWithRdtoolsRequest(BaseModel):
    """Explicit inputs for a real RdTools installation analysis."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str = Field(min_length=1)
    column_mapping: RdtoolsColumnMapping
    system_metadata: RdtoolsSystemMetadata
    normalization_method: RdtoolsNormalizationMethod
    analysis_mode: RdtoolsAnalysisMode
    pvwatts_config: RdtoolsPvwattsConfig | None = None

    @model_validator(mode="after")
    def validate_analysis_requirements(self) -> AnalyzeExistingInstallationWithRdtoolsRequest:
        if self.column_mapping.energy_column is not None and self.system_metadata.energy_unit is None:
            raise ValueError("energy_unit is required when energy_column is supplied.")
        if self.column_mapping.power_column is not None and self.system_metadata.power_unit is None:
            raise ValueError("power_unit is required when power_column is supplied.")
        if (
            self.column_mapping.expected_power_column is not None
            and self.system_metadata.expected_power_unit is None
        ):
            raise ValueError(
                "expected_power_unit is required when expected_power_column is supplied."
            )
        if self.column_mapping.temperature_column is not None and self.system_metadata.temperature_unit is None:
            raise ValueError("temperature_unit is required when temperature_column is supplied.")

        if (
            self.normalization_method == "expected_power"
            and self.column_mapping.expected_power_column is None
        ):
            raise ValueError(
                "expected_power_column is required when normalization_method is 'expected_power'."
            )
        if self.normalization_method == "pvwatts":
            if self.column_mapping.energy_column is None:
                raise ValueError(
                    "energy_column is required when normalization_method is 'pvwatts'."
                )
            if self.pvwatts_config is None:
                raise ValueError("pvwatts_config is required when normalization_method is 'pvwatts'.")

            temperature_inputs_provided = [
                self.column_mapping.temperature_column is not None,
                self.pvwatts_config.temperature_cell_ref_c is not None,
                self.pvwatts_config.gamma_pdc_per_c is not None,
            ]
            if sum(temperature_inputs_provided) not in {0, 3}:
                raise ValueError(
                    "temperature_column, temperature_cell_ref_c, and gamma_pdc_per_c must be provided together."
                )
        return self


class RdtoolsDegradationResult(BaseModel):
    """Normalized degradation output from RdTools."""

    model_config = ConfigDict(extra="forbid")

    estimated_degradation_rate_pct_per_year: float
    confidence_interval_pct_per_year: list[float] | None = None
    exceedance_level_pct_per_year: float | None = None


class RdtoolsAnalysisResult(BaseModel):
    """Normalized output for a real RdTools installation analysis."""

    model_config = ConfigDict(extra="forbid")

    degradation_result: RdtoolsDegradationResult
    soiling_result: dict[str, Any] | None = None
    availability_result: dict[str, Any] | None = None
    data_quality_warnings: list[str] = Field(default_factory=list)
    method_used: str
    source_dataset: str
    analysis_window: dict[str, str]
    normalized_point_count: int
    source_name: str = "RdTools"
    source_version: str
    raw_metadata: dict[str, Any] | None = None
