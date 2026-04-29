from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from app.services.pvgis_service import PVGISService
from app.tools.pvgis_tools import build_pvgis_tool


def _payload() -> dict[str, Any]:
    monthly = [
        {
            "month": month,
            "E_m": float(100 + month),
            "H(i)_m": float(150 + month),
        }
        for month in range(1, 13)
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


@pytest.mark.asyncio
@respx.mock
async def test_pvgis_tool_normalizes_mocked_response() -> None:
    route = respx.get("https://re.jrc.ec.europa.eu/api/v5_3/PVcalc").mock(
        return_value=httpx.Response(200, json=_payload())
    )

    async with httpx.AsyncClient() as client:
        service = PVGISService(http_client=client, max_retries=1)
        tool = build_pvgis_tool(service=service)

        result = await tool.ainvoke(
            {
                "lat": 37.3891,
                "lon": -5.9845,
                "peakpower_kwp": 5.2,
                "system_loss_pct": 14.0,
                "tilt_deg": 30.0,
                "azimuth_deg": 0.0,
            }
        )

    assert route.called
    assert route.calls.last.request.url.params["outputformat"] == "json"
    assert result["annual_energy_kwh"] == pytest.approx(1278.0)
    assert len(result["monthly_energy_kwh"]) == 12
    assert result["monthly_in_plane_irradiation"][0] == pytest.approx(151.0)
