from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.core.errors import ExternalServiceError
from app.schemas.solar_project import PVCalcRequest
from app.services.pvgis_service import PVGISService


def _request(**overrides: Any) -> PVCalcRequest:
    base = {
        "lat": 37.3891,
        "lon": -5.9845,
        "peakpower_kwp": 5.2,
        "system_loss_pct": 14.0,
        "tilt_deg": 30.0,
        "azimuth_deg": 0.0,
    }
    base.update(overrides)
    return PVCalcRequest(**base)


def _payload(months: int = 12) -> dict[str, Any]:
    monthly = [
        {
            "month": month,
            "E_m": float(100 + month),
            "H(i)_m": float(150 + month),
        }
        for month in range(1, months + 1)
    ]
    return {
        "outputs": {
            "monthly": {"fixed": monthly},
            "totals": {
                "fixed": {
                    "E_y": sum(item["E_m"] for item in monthly),
                    "H(i)_y": sum(item["H(i)_m"] for item in monthly),
                }
            },
        },
        "meta": {"source": "mock-pvgis"},
    }


def test_to_pvgis_params_serializes_explicit_inputs() -> None:
    params = PVGISService._to_pvgis_params(
        _request(
            pv_technology="crystSi2025",
            mounting="building",
            use_horizon=True,
        )
    )
    assert params == {
        "lat": 37.3891,
        "lon": -5.9845,
        "peakpower": 5.2,
        "loss": 14.0,
        "angle": 30.0,
        "aspect": 0.0,
        "outputformat": "json",
        "pvtechchoice": "crystSi2025",
        "mountingplace": "building",
        "usehorizon": 1,
    }


def test_request_schema_requires_explicit_core_fields() -> None:
    with pytest.raises(ValidationError):
        PVCalcRequest(
            lat=37.3891,
            lon=-5.9845,
            peakpower_kwp=5.2,
            tilt_deg=30.0,
            azimuth_deg=0.0,
        )


@pytest.mark.asyncio
async def test_estimate_production_calls_pvcalc_and_normalizes_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PVGISService(
            base_url="https://re.jrc.ec.europa.eu/api/v5_3",
            http_client=client,
            max_retries=1,
        )
        result = await service.estimate_production(_request())

    assert len(requests) == 1
    assert str(requests[0].url).startswith("https://re.jrc.ec.europa.eu/api/v5_3/PVcalc")
    assert requests[0].url.params["outputformat"] == "json"
    assert requests[0].url.params["peakpower"] == "5.2"
    assert requests[0].url.params["loss"] == "14.0"
    assert result.annual_energy_kwh == pytest.approx(1278.0)
    assert len(result.monthly) == 12
    assert result.monthly[0].month == 1
    assert result.monthly[-1].month == 12
    assert result.annual_in_plane_irradiation_kwh_per_m2 == pytest.approx(1878.0)
    assert result.raw_metadata == {"source": "mock-pvgis"}
    assert result.warnings == []


@pytest.mark.asyncio
async def test_estimate_production_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PVGISService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="PVGIS returned an error response"):
            await service.estimate_production(_request())


@pytest.mark.asyncio
async def test_estimate_production_raises_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PVGISService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="PVGIS network failure"):
            await service.estimate_production(_request())


@pytest.mark.asyncio
async def test_estimate_production_retries_transient_network_errors() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200, json=_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = PVGISService(http_client=client, max_retries=2)
        result = await service.estimate_production(_request())

    assert attempts == 2
    assert result.annual_energy_kwh == pytest.approx(1278.0)
