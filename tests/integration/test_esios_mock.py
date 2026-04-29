from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import respx

from app.services.esios_service import ESIOSService
from app.tools.price_tools import (
    build_get_pvpc_import_reference_price_tool,
    build_get_pvpc_surplus_compensation_price_tool,
)


def _payload() -> dict[str, Any]:
    return {
        "indicator": {
            "id": 1739,
            "name": "Precio excedentes autoconsumo",
            "magnitud": [{"name": "EUR/MWh"}],
            "values": [
                {"datetime": "2026-04-01T00:00:00+02:00", "value": 80.0},
                {"datetime": "2026-04-01T01:00:00+02:00", "value": 100.0},
            ],
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_pvpc_surplus_tool_normalizes_mocked_response() -> None:
    route = respx.get("https://api.esios.ree.es/indicators/1739").mock(
        return_value=httpx.Response(200, json=_payload())
    )

    async with httpx.AsyncClient() as client:
        service = ESIOSService(api_token="dummy", http_client=client, max_retries=1)
        tool = build_get_pvpc_surplus_compensation_price_tool(service=service)

        payload = await tool.ainvoke(
            {
                "indicator_id": 1739,
                "start_datetime": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
                "end_datetime": datetime(2026, 4, 30, tzinfo=UTC).isoformat(),
                "aggregation": "hourly",
                "timezone": "Europe/Madrid",
            }
        )

    assert route.called
    assert payload["source_name"] == "esios"
    assert payload["indicator_id"] == 1739
    assert payload["average_price_eur_kwh"] == pytest.approx(0.09)
    assert payload["unit_normalized"] == "EUR_PER_KWH"


@pytest.mark.asyncio
@respx.mock
async def test_pvpc_import_reference_tool_uses_explicit_indicator_id() -> None:
    route = respx.get("https://api.esios.ree.es/indicators/1001").mock(
        return_value=httpx.Response(200, json=_payload())
    )

    async with httpx.AsyncClient() as client:
        service = ESIOSService(api_token="dummy", http_client=client, max_retries=1)
        tool = build_get_pvpc_import_reference_price_tool(service=service)

        payload = await tool.ainvoke(
            {
                "indicator_id": 1001,
                "start_datetime": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
                "end_datetime": datetime(2026, 4, 30, tzinfo=UTC).isoformat(),
            }
        )

    assert route.called
    assert payload["indicator_id"] == 1001
