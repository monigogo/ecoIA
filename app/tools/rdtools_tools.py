"""LangChain tools for explicit RdTools dataset validation."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from langchain_core.tools import tool

from app.core.errors import ValidationAppError
from app.schemas.rdtools import (
    AnalyzeExistingInstallationWithRdtoolsRequest,
    RdtoolsAnalysisResult,
    RdtoolsColumnMapping,
    ValidateRdtoolsCsvRequest,
    ValidateRdtoolsCsvResult,
)
from app.services.rdtools_service import RdtoolsService


@lru_cache(maxsize=1)
def _default_service() -> RdtoolsService:
    return RdtoolsService()


def _mapped_columns(mapping: RdtoolsColumnMapping) -> dict[str, str]:
    columns = {
        "timestamp_column": mapping.timestamp_column,
        "irradiance_column": mapping.irradiance_column,
    }
    if mapping.energy_column is not None:
        columns["energy_column"] = mapping.energy_column
    if mapping.power_column is not None:
        columns["power_column"] = mapping.power_column
    if mapping.expected_power_column is not None:
        columns["expected_power_column"] = mapping.expected_power_column
    if mapping.temperature_column is not None:
        columns["temperature_column"] = mapping.temperature_column
    if mapping.availability_column is not None:
        columns["availability_column"] = mapping.availability_column
    return columns


def build_validate_rdtools_csv_tool():
    """Return a LangChain tool that validates an explicit RdTools CSV mapping."""

    @tool("validate_rdtools_csv", args_schema=ValidateRdtoolsCsvRequest)
    def validate_rdtools_csv(
        dataset_path: str,
        column_mapping: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate a PV time-series CSV using only explicit column mappings."""

        csv_path = Path(dataset_path)
        if not csv_path.exists():
            raise ValidationAppError(
                "CSV dataset not found.",
                details={"dataset_path": dataset_path},
            )

        frame = pd.read_csv(csv_path)
        detected_columns = [str(column) for column in frame.columns.tolist()]
        row_count = int(len(frame.index))
        warnings: list[str] = []
        missing_columns: list[str] = []
        time_range: dict[str, str] | None = None
        recommended_mapping: dict[str, str] | None = None
        is_valid = False

        if column_mapping is None:
            warnings.append(
                "Explicit column_mapping is required. The tool does not infer semantic roles from column names."
            )
        else:
            mapping = RdtoolsColumnMapping.model_validate(column_mapping)
            recommended_mapping = _mapped_columns(mapping)
            expected_columns = list(recommended_mapping.values())
            missing_columns = [
                column_name
                for column_name in expected_columns
                if column_name not in detected_columns
            ]

            if not missing_columns:
                timestamp_series = pd.to_datetime(
                    frame[mapping.timestamp_column],
                    utc=True,
                    errors="coerce",
                )
                valid_timestamps = timestamp_series.dropna()
                if valid_timestamps.empty:
                    warnings.append("No valid timestamps were found in the mapped timestamp column.")
                else:
                    time_range = {
                        "start": valid_timestamps.min().isoformat(),
                        "end": valid_timestamps.max().isoformat(),
                    }
                    if not valid_timestamps.is_monotonic_increasing:
                        warnings.append(
                            "The mapped timestamp column is not strictly sorted in ascending order."
                        )
                    duplicate_count = int(valid_timestamps.duplicated().sum())
                    if duplicate_count > 0:
                        warnings.append(
                            f"The mapped timestamp column contains {duplicate_count} duplicate timestamps."
                        )

                for mapped_name, column_name in recommended_mapping.items():
                    null_count = int(frame[column_name].isna().sum())
                    if null_count > 0:
                        warnings.append(
                            f"{mapped_name} contains {null_count} missing values."
                        )

                is_valid = not valid_timestamps.empty

        response = ValidateRdtoolsCsvResult(
            is_valid=is_valid,
            detected_columns=detected_columns,
            missing_columns=missing_columns,
            time_range=time_range,
            row_count=row_count,
            data_quality_warnings=warnings,
            recommended_mapping=recommended_mapping,
        )

        return response.model_dump()

    return validate_rdtools_csv


def build_analyze_existing_installation_with_rdtools_tool(
    service: RdtoolsService | None = None,
):
    """Return a LangChain tool that runs a real RdTools analysis over a local CSV."""

    bound_service = service or _default_service()

    @tool(
        "analyze_existing_installation_with_rdtools",
        args_schema=AnalyzeExistingInstallationWithRdtoolsRequest,
    )
    def analyze_existing_installation_with_rdtools(
        dataset_path: str,
        column_mapping: dict[str, Any],
        system_metadata: dict[str, Any],
        normalization_method: str,
        analysis_mode: str,
        pvwatts_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a historical PV dataset with RdTools using only explicit mappings and metadata."""

        request = AnalyzeExistingInstallationWithRdtoolsRequest.model_validate(
            {
                "dataset_path": dataset_path,
                "column_mapping": column_mapping,
                "system_metadata": system_metadata,
                "normalization_method": normalization_method,
                "analysis_mode": analysis_mode,
                "pvwatts_config": pvwatts_config,
            }
        )

        result: RdtoolsAnalysisResult = bound_service.analyze_existing_installation(request)

        return result.model_dump()

    return analyze_existing_installation_with_rdtools


validate_rdtools_csv = build_validate_rdtools_csv_tool()
analyze_existing_installation_with_rdtools = build_analyze_existing_installation_with_rdtools_tool()


__all__ = [
    "analyze_existing_installation_with_rdtools",
    "build_analyze_existing_installation_with_rdtools_tool",
    "build_validate_rdtools_csv_tool",
    "validate_rdtools_csv",
]
