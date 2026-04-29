from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.schemas.solar_project import PVCalcRequest, PVCalcResult, PVMonthlyEntry
from app.tools.pvgis_tools import build_pvgis_tool


class StubPVGISService:
    def __init__(self, result: PVCalcResult) -> None:
        self._result = result
        self.requests: list[PVCalcRequest] = []

    async def estimate_production(self, request: PVCalcRequest) -> PVCalcResult:
        self.requests.append(request)
        return self._result


def _result() -> PVCalcResult:
    monthly = [
        PVMonthlyEntry(
            month=month,
            energy_kwh=float(100 + month),
            in_plane_irradiation_kwh_per_m2=float(150 + month),
        )
        for month in range(12, 0, -1)
    ]
    return PVCalcResult(
        annual_energy_kwh=1278.0,
        monthly=monthly,
        annual_in_plane_irradiation_kwh_per_m2=1878.0,
        raw_metadata={"source": "stub"},
    )


def test_tool_has_expected_name_and_required_schema() -> None:
    tool = build_pvgis_tool(service=StubPVGISService(_result()))
    assert tool.name == "estimate_solar_production_with_pvgis"
    assert tool.description

    schema = tool.args_schema.model_json_schema()
    required = set(schema["required"])
    assert {
        "lat",
        "lon",
        "peakpower_kwp",
        "system_loss_pct",
        "tilt_deg",
        "azimuth_deg",
    }.issubset(required)


@pytest.mark.asyncio
async def test_tool_returns_serializable_normalized_output() -> None:
    service = StubPVGISService(_result())
    tool = build_pvgis_tool(service=service)

    payload = await tool.ainvoke(
        {
            "lat": 37.3891,
            "lon": -5.9845,
            "peakpower_kwp": 5.2,
            "system_loss_pct": 14.0,
            "tilt_deg": 30.0,
            "azimuth_deg": 0.0,
        }
    )

    assert isinstance(payload, dict)
    assert payload["annual_energy_kwh"] == pytest.approx(1278.0)
    assert len(payload["monthly_energy_kwh"]) == 12
    assert len(payload["monthly_in_plane_irradiation"]) == 12
    assert payload["monthly_energy_kwh"][0] == pytest.approx(101.0)
    assert payload["monthly_energy_kwh"][-1] == pytest.approx(112.0)
    assert payload["source_name"] == "PVGIS"
    assert payload["source_version"] == "v5_3"
    assert payload["raw_metadata"] == {"source": "stub"}
    assert service.requests[0].system_loss_pct == pytest.approx(14.0)
    json.dumps(payload)


def test_tool_request_schema_does_not_allow_missing_core_inputs() -> None:
    with pytest.raises(ValidationError):
        PVCalcRequest(
            lat=37.3891,
            lon=-5.9845,
            peakpower_kwp=5.2,
            tilt_deg=30.0,
            azimuth_deg=0.0,
        )
