from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.errors import ValidationAppError
from app.schemas.rdtools import RdtoolsAnalysisResult, RdtoolsDegradationResult
from app.tools.rdtools_tools import (
    build_analyze_existing_installation_with_rdtools_tool,
    build_validate_rdtools_csv_tool,
)


def _write_csv(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class StubRdtoolsService:
    def __init__(self, result: RdtoolsAnalysisResult) -> None:
        self._result = result

    def analyze_existing_installation(self, request: object) -> RdtoolsAnalysisResult:
        self.request = request
        return self._result


def test_validate_rdtools_csv_tool_has_expected_name() -> None:
    tool = build_validate_rdtools_csv_tool()
    assert tool.name == "validate_rdtools_csv"
    assert tool.description


def test_validate_rdtools_csv_requires_explicit_mapping_to_be_valid() -> None:
    csv_path = _write_csv(
        Path(".test_artifacts/rdtools/no_mapping.csv"),
        "timestamp,energy,poa\n2024-01-01T00:00:00Z,1.0,2.0\n",
    )
    tool = build_validate_rdtools_csv_tool()
    payload = tool.invoke({"dataset_path": str(csv_path)})

    assert payload["is_valid"] is False
    assert payload["detected_columns"] == ["timestamp", "energy", "poa"]
    assert payload["data_quality_warnings"] == [
        "Explicit column_mapping is required. The tool does not infer semantic roles from column names."
    ]
    json.dumps(payload)


def test_validate_rdtools_csv_returns_time_range_and_warnings() -> None:
    csv_path = _write_csv(
        Path(".test_artifacts/rdtools/valid.csv"),
        (
            "timestamp_utc,energy_kwh,poa_irradiance,temperature_c\n"
            "2024-01-01T00:00:00Z,1.0,2.0,15.0\n"
            "2024-01-01T00:00:00Z,1.1,,16.0\n"
        ),
    )
    tool = build_validate_rdtools_csv_tool()
    payload = tool.invoke(
        {
            "dataset_path": str(csv_path),
            "column_mapping": {
                "timestamp_column": "timestamp_utc",
                "energy_column": "energy_kwh",
                "irradiance_column": "poa_irradiance",
                "temperature_column": "temperature_c",
            },
        }
    )

    assert payload["is_valid"] is True
    assert payload["row_count"] == 2
    assert payload["time_range"]["start"] == "2024-01-01T00:00:00+00:00"
    assert payload["missing_columns"] == []
    assert any("duplicate timestamps" in warning for warning in payload["data_quality_warnings"])
    assert any("missing values" in warning for warning in payload["data_quality_warnings"])
    json.dumps(payload)


def test_validate_rdtools_csv_raises_for_missing_file() -> None:
    tool = build_validate_rdtools_csv_tool()
    with pytest.raises(ValidationAppError):
        tool.invoke({"dataset_path": ".test_artifacts/rdtools/missing.csv"})


def test_analyze_existing_installation_tool_has_expected_name() -> None:
    tool = build_analyze_existing_installation_with_rdtools_tool(
        service=StubRdtoolsService(
            RdtoolsAnalysisResult(
                degradation_result=RdtoolsDegradationResult(
                    estimated_degradation_rate_pct_per_year=-0.5,
                    confidence_interval_pct_per_year=[-0.6, -0.4],
                ),
                method_used="rdtools_expected_power_year_on_year",
                source_dataset="dataset.csv",
                analysis_window={"start": "2020-01-01T00:00:00+00:00", "end": "2022-12-31T00:00:00+00:00"},
                normalized_point_count=1000,
                source_version="3.1.1",
            )
        )
    )
    assert tool.name == "analyze_existing_installation_with_rdtools"
    assert tool.description


def test_analyze_existing_installation_tool_returns_serializable_output() -> None:
    service = StubRdtoolsService(
        RdtoolsAnalysisResult(
            degradation_result=RdtoolsDegradationResult(
                estimated_degradation_rate_pct_per_year=-0.5,
                confidence_interval_pct_per_year=[-0.6, -0.4],
            ),
            data_quality_warnings=["warning"],
            method_used="rdtools_expected_power_year_on_year",
            source_dataset="dataset.csv",
            analysis_window={"start": "2020-01-01T00:00:00+00:00", "end": "2022-12-31T00:00:00+00:00"},
            normalized_point_count=1000,
            source_version="3.1.1",
        )
    )
    tool = build_analyze_existing_installation_with_rdtools_tool(service=service)
    payload = tool.invoke(
        {
            "dataset_path": "dataset.csv",
            "column_mapping": {
                "timestamp_column": "timestamp_utc",
                "energy_column": "energy_wh",
                "expected_power_column": "expected_power_w",
                "irradiance_column": "poa_wm2",
            },
            "system_metadata": {
                "energy_unit": "Wh",
                "expected_power_unit": "W",
                "irradiance_unit": "W/m2",
            },
            "normalization_method": "expected_power",
            "analysis_mode": "degradation",
        }
    )

    assert payload["degradation_result"]["estimated_degradation_rate_pct_per_year"] == pytest.approx(
        -0.5
    )
    assert payload["method_used"] == "rdtools_expected_power_year_on_year"
    json.dumps(payload)
