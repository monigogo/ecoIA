"""RdTools service for explicit historical-installation analysis."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import rdtools

from app.core.errors import ExternalServiceError, ValidationAppError
from app.core.logging import get_logger
from app.schemas.rdtools import (
    AnalyzeExistingInstallationWithRdtoolsRequest,
    RdtoolsAnalysisResult,
    RdtoolsDegradationResult,
    RdtoolsNormalizationMethod,
    RdtoolsSystemMetadata,
)

logger = get_logger(__name__)


class RdtoolsService:
    """Run explicit, reproducible RdTools analyses on local datasets."""

    @staticmethod
    def _convert_energy_to_wh(series: pd.Series, metadata: RdtoolsSystemMetadata) -> pd.Series:
        if metadata.energy_unit == "Wh":
            return series.astype(float)
        if metadata.energy_unit == "kWh":
            return series.astype(float) * 1000.0
        raise ValidationAppError("energy_unit is required to convert energy data.")

    @staticmethod
    def _convert_power_to_w(series: pd.Series, unit: str | None) -> pd.Series:
        if unit == "W":
            return series.astype(float)
        if unit == "kW":
            return series.astype(float) * 1000.0
        raise ValidationAppError("A power unit is required to convert power data.")

    @staticmethod
    def _convert_irradiance_to_w_per_m2(series: pd.Series, metadata: RdtoolsSystemMetadata) -> pd.Series:
        if metadata.irradiance_unit == "W/m2":
            return series.astype(float)
        if metadata.irradiance_unit == "kW/m2":
            return series.astype(float) * 1000.0
        raise ValidationAppError("irradiance_unit is required to convert irradiance data.")

    @staticmethod
    def _prepare_frame(request: AnalyzeExistingInstallationWithRdtoolsRequest) -> tuple[pd.DataFrame, list[str]]:
        csv_path = Path(request.dataset_path)
        if not csv_path.exists():
            raise ValidationAppError(
                "CSV dataset not found.",
                details={"dataset_path": request.dataset_path},
            )

        frame = pd.read_csv(csv_path)
        warnings_list: list[str] = []

        missing_columns = [
            column
            for column in {
                request.column_mapping.timestamp_column,
                request.column_mapping.energy_column,
                request.column_mapping.power_column,
                request.column_mapping.expected_power_column,
                request.column_mapping.irradiance_column,
                request.column_mapping.temperature_column,
            }
            if column is not None and column not in frame.columns
        ]
        if missing_columns:
            raise ValidationAppError(
                "Dataset is missing one or more explicitly mapped columns.",
                details={"missing_columns": sorted(missing_columns)},
            )

        timestamps = pd.to_datetime(
            frame[request.column_mapping.timestamp_column],
            utc=True,
            errors="coerce",
        )
        invalid_timestamps = int(timestamps.isna().sum())
        if invalid_timestamps > 0:
            warnings_list.append(
                f"Dropped {invalid_timestamps} rows with invalid timestamps in the mapped timestamp column."
            )

        prepared = frame.loc[~timestamps.isna()].copy()
        prepared.index = timestamps.loc[~timestamps.isna()]
        prepared = prepared.sort_index()

        required_columns = [
            request.column_mapping.irradiance_column,
        ]
        if request.normalization_method == "expected_power":
            required_columns.append(request.column_mapping.expected_power_column)
            if request.column_mapping.energy_column is not None:
                required_columns.append(request.column_mapping.energy_column)
            if request.column_mapping.power_column is not None:
                required_columns.append(request.column_mapping.power_column)
        elif request.normalization_method == "pvwatts":
            required_columns.append(request.column_mapping.energy_column)
            if request.column_mapping.temperature_column is not None:
                required_columns.append(request.column_mapping.temperature_column)

        missing_required_values = prepared[required_columns].isna().any(axis=1)
        missing_value_rows = int(missing_required_values.sum())
        if missing_value_rows > 0:
            warnings_list.append(
                f"Dropped {missing_value_rows} rows with missing values in required analysis columns."
            )
            prepared = prepared.loc[~missing_required_values].copy()

        if prepared.empty:
            raise ValidationAppError("No valid data rows remain after explicit CSV preparation.")

        span_days = (prepared.index.max() - prepared.index.min()).total_seconds() / 86400.0
        if span_days < 365.0:
            raise ValidationAppError(
                "RdTools year-on-year degradation needs more than one year of valid data.",
                details={"time_span_days": span_days},
            )

        if prepared.index.duplicated().any():
            warnings_list.append("The timestamp index contains duplicates; RdTools results may be noisier.")
        if not prepared.index.is_monotonic_increasing:
            warnings_list.append("The timestamp index is not strictly increasing after preparation.")

        return prepared, warnings_list

    def _normalize_expected_power(
        self,
        frame: pd.DataFrame,
        request: AnalyzeExistingInstallationWithRdtoolsRequest,
    ) -> tuple[pd.Series, pd.Series]:
        metadata = request.system_metadata
        mapping = request.column_mapping
        poa_global = self._convert_irradiance_to_w_per_m2(frame[mapping.irradiance_column], metadata)
        expected_power = self._convert_power_to_w(frame[mapping.expected_power_column], metadata.expected_power_unit)

        if mapping.energy_column is not None:
            pv_series = self._convert_energy_to_wh(frame[mapping.energy_column], metadata)
            pv_input = "energy"
        else:
            pv_series = self._convert_power_to_w(frame[mapping.power_column], metadata.power_unit)
            pv_input = "power"

        return rdtools.normalize_with_expected_power(
            pv=pv_series,
            power_expected=expected_power,
            poa_global=poa_global,
            pv_input=pv_input,
        )

    def _normalize_pvwatts(
        self,
        frame: pd.DataFrame,
        request: AnalyzeExistingInstallationWithRdtoolsRequest,
    ) -> tuple[pd.Series, pd.Series]:
        metadata = request.system_metadata
        mapping = request.column_mapping
        config = request.pvwatts_config

        energy = self._convert_energy_to_wh(frame[mapping.energy_column], metadata)
        pvwatts_kws: dict[str, Any] = {
            "poa_global": self._convert_irradiance_to_w_per_m2(frame[mapping.irradiance_column], metadata),
            "power_dc_rated": config.power_dc_rated_w,
            "poa_global_ref": config.poa_global_ref_w_per_m2,
        }
        if mapping.temperature_column is not None:
            pvwatts_kws["temperature_cell"] = frame[mapping.temperature_column].astype(float)
            pvwatts_kws["temperature_cell_ref"] = config.temperature_cell_ref_c
            pvwatts_kws["gamma_pdc"] = config.gamma_pdc_per_c

        return rdtools.normalize_with_pvwatts(energy=energy, pvwatts_kws=pvwatts_kws)

    def _normalize(
        self,
        frame: pd.DataFrame,
        request: AnalyzeExistingInstallationWithRdtoolsRequest,
    ) -> tuple[pd.Series, pd.Series]:
        if request.normalization_method == "expected_power":
            return self._normalize_expected_power(frame, request)
        if request.normalization_method == "pvwatts":
            return self._normalize_pvwatts(frame, request)
        raise ValidationAppError(
            "Unsupported RdTools normalization method.",
            details={"normalization_method": request.normalization_method},
        )

    @staticmethod
    def _method_name(normalization_method: RdtoolsNormalizationMethod) -> str:
        return f"rdtools_{normalization_method}_year_on_year"

    def analyze_existing_installation(
        self,
        request: AnalyzeExistingInstallationWithRdtoolsRequest,
    ) -> RdtoolsAnalysisResult:
        frame, data_quality_warnings = self._prepare_frame(request)

        try:
            with warnings.catch_warnings(record=True) as captured_warnings:
                warnings.simplefilter("always")
                energy_normalized, insolation = self._normalize(frame, request)
                clean_normalized = energy_normalized.dropna()
                if clean_normalized.empty:
                    raise ValidationAppError(
                        "RdTools normalization produced no valid normalized points."
                    )

                rd_pct, confidence_interval, calc_info = rdtools.degradation_year_on_year(
                    clean_normalized
                )
        except ValidationAppError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("rdtools_analysis_failure", dataset_path=request.dataset_path)
            raise ExternalServiceError(
                "RdTools analysis failed",
                details={"dataset_path": request.dataset_path, "error": str(exc)},
            ) from exc

        for captured in captured_warnings:
            message = str(captured.message).strip()
            if message:
                data_quality_warnings.append(f"RdTools warning: {message}")

        confidence_values: list[float] | None = None
        if confidence_interval is not None:
            confidence_values = [float(confidence_interval[0]), float(confidence_interval[1])]

        exceedance_level = calc_info.get("exceedance_level")
        analysis_window = {
            "start": clean_normalized.index.min().isoformat(),
            "end": clean_normalized.index.max().isoformat(),
        }

        return RdtoolsAnalysisResult(
            degradation_result=RdtoolsDegradationResult(
                estimated_degradation_rate_pct_per_year=float(rd_pct),
                confidence_interval_pct_per_year=confidence_values,
                exceedance_level_pct_per_year=(
                    float(exceedance_level) if exceedance_level is not None else None
                ),
            ),
            data_quality_warnings=data_quality_warnings,
            method_used=self._method_name(request.normalization_method),
            source_dataset=request.dataset_path,
            analysis_window=analysis_window,
            normalized_point_count=int(clean_normalized.shape[0]),
            source_version=getattr(rdtools, "__version__", "unknown"),
            raw_metadata={
                "analysis_mode": request.analysis_mode,
                "normalization_method": request.normalization_method,
                "insolation_point_count": int(insolation.dropna().shape[0]),
                "rdtools_version": getattr(rdtools, "__version__", "unknown"),
                "renormalizing_factor": calc_info.get("renormalizing_factor"),
                "usage_of_points_count": int(calc_info.get("usage_of_points", pd.Series(dtype=float)).shape[0]),
            },
        )
