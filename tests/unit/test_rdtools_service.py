from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.core.errors import ValidationAppError
from app.schemas.rdtools import AnalyzeExistingInstallationWithRdtoolsRequest
from app.services.rdtools_service import RdtoolsService


def _write_expected_power_csv(path: Path) -> Path:
    index = pd.date_range("2020-01-01", periods=365 * 3, freq="D", tz="UTC")
    poa = pd.Series(500 + 100 * np.sin(np.arange(len(index)) / 30), index=index)
    expected_power_w = poa * 10.0
    energy_wh = expected_power_w * 24.0 * (1 - 0.005 * np.arange(len(index)) / 365.0)
    frame = pd.DataFrame(
        {
            "timestamp_utc": index.astype(str),
            "energy_wh": energy_wh.to_numpy(),
            "expected_power_w": expected_power_w.to_numpy(),
            "poa_wm2": poa.to_numpy(),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _write_pvwatts_csv(path: Path) -> Path:
    index = pd.date_range("2020-01-01", periods=365 * 3, freq="D", tz="UTC")
    poa = pd.Series(500 + 100 * np.sin(np.arange(len(index)) / 30), index=index)
    energy_wh = (poa * 10000.0 / 1000.0 * 24.0) * (1 - 0.005 * np.arange(len(index)) / 365.0)
    temperature_c = pd.Series(25.0, index=index)
    frame = pd.DataFrame(
        {
            "timestamp_utc": index.astype(str),
            "energy_wh": energy_wh.to_numpy(),
            "poa_wm2": poa.to_numpy(),
            "temperature_c": temperature_c.to_numpy(),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def test_analyze_existing_installation_runs_expected_power_degradation() -> None:
    csv_path = _write_expected_power_csv(Path(".test_artifacts/rdtools/expected_power_analysis.csv"))
    service = RdtoolsService()

    result = service.analyze_existing_installation(
        AnalyzeExistingInstallationWithRdtoolsRequest(
            dataset_path=str(csv_path),
            column_mapping={
                "timestamp_column": "timestamp_utc",
                "energy_column": "energy_wh",
                "expected_power_column": "expected_power_w",
                "irradiance_column": "poa_wm2",
            },
            system_metadata={
                "energy_unit": "Wh",
                "expected_power_unit": "W",
                "irradiance_unit": "W/m2",
            },
            normalization_method="expected_power",
            analysis_mode="degradation",
        )
    )

    assert result.method_used == "rdtools_expected_power_year_on_year"
    assert result.degradation_result.estimated_degradation_rate_pct_per_year == pytest.approx(
        -0.5, abs=0.02
    )
    assert result.degradation_result.confidence_interval_pct_per_year is not None


def test_analyze_existing_installation_runs_pvwatts_degradation() -> None:
    csv_path = _write_pvwatts_csv(Path(".test_artifacts/rdtools/pvwatts_analysis.csv"))
    service = RdtoolsService()

    result = service.analyze_existing_installation(
        AnalyzeExistingInstallationWithRdtoolsRequest(
            dataset_path=str(csv_path),
            column_mapping={
                "timestamp_column": "timestamp_utc",
                "energy_column": "energy_wh",
                "irradiance_column": "poa_wm2",
                "temperature_column": "temperature_c",
            },
            system_metadata={
                "energy_unit": "Wh",
                "irradiance_unit": "W/m2",
                "temperature_unit": "C",
            },
            normalization_method="pvwatts",
            analysis_mode="degradation",
            pvwatts_config={
                "power_dc_rated_w": 10000.0,
                "poa_global_ref_w_per_m2": 1000.0,
                "temperature_cell_ref_c": 25.0,
                "gamma_pdc_per_c": -0.004,
            },
        )
    )

    assert result.method_used == "rdtools_pvwatts_year_on_year"
    assert result.degradation_result.estimated_degradation_rate_pct_per_year == pytest.approx(
        -0.5, abs=0.02
    )
    assert result.normalized_point_count > 1000


def test_analyze_existing_installation_raises_when_mapped_columns_are_missing() -> None:
    csv_path = _write_expected_power_csv(Path(".test_artifacts/rdtools/missing_column_analysis.csv"))
    service = RdtoolsService()

    with pytest.raises(ValidationAppError, match="explicitly mapped columns"):
        service.analyze_existing_installation(
            AnalyzeExistingInstallationWithRdtoolsRequest(
                dataset_path=str(csv_path),
                column_mapping={
                    "timestamp_column": "timestamp_utc",
                    "energy_column": "energy_wh",
                    "expected_power_column": "expected_power_missing",
                    "irradiance_column": "poa_wm2",
                },
                system_metadata={
                    "energy_unit": "Wh",
                    "expected_power_unit": "W",
                    "irradiance_unit": "W/m2",
                },
                normalization_method="expected_power",
                analysis_mode="degradation",
            )
        )
