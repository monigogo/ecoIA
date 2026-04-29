from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.tools.rdtools_tools import build_analyze_existing_installation_with_rdtools_tool


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


def test_analyze_existing_installation_with_rdtools_runs_end_to_end() -> None:
    csv_path = _write_expected_power_csv(Path(".test_artifacts/rdtools/integration_expected_power.csv"))
    tool = build_analyze_existing_installation_with_rdtools_tool()

    payload = tool.invoke(
        {
            "dataset_path": str(csv_path),
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

    assert payload["source_name"] == "RdTools"
    assert payload["method_used"] == "rdtools_expected_power_year_on_year"
    assert payload["degradation_result"]["estimated_degradation_rate_pct_per_year"] == pytest.approx(
        -0.5, abs=0.02
    )
