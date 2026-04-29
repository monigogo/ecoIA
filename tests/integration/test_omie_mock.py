from __future__ import annotations

from datetime import datetime

import httpx
import pytest
import respx

from app.services.omie_service import OMIEService
from app.tools.price_tools import build_get_market_sale_reference_price_tool


def _omie_text() -> str:
    rows = ["MARGINALPDBC;"]
    for hour in range(1, 25):
        rows.append(f"2026;04;01;{hour:02d};50.0;60.0;")
    rows.append("*")
    return "\n".join(rows)


@pytest.mark.asyncio
@respx.mock
async def test_market_sale_reference_tool_returns_normalized_omie_series() -> None:
    route = respx.get("https://www.omie.es/es/file-download").mock(
        return_value=httpx.Response(200, text=_omie_text())
    )

    async with httpx.AsyncClient() as client:
        service = OMIEService(http_client=client, max_retries=1)
        tool = build_get_market_sale_reference_price_tool(service=service)

        payload = await tool.ainvoke(
            {
                "start_date": datetime(2026, 4, 1).isoformat(),
                "end_date": datetime(2026, 4, 1).isoformat(),
                "market_area": "ES",
                "aggregation": "hourly",
            }
        )

    assert route.called
    assert payload["source_name"] == "omie"
    assert payload["market_area"] == "ES"
    assert payload["unit_normalized"] == "EUR_PER_KWH"
    assert payload["average_price_eur_kwh"] == pytest.approx(0.06)
    assert any(
        warning["code"] == "omie_wholesale_reference_only"
        for warning in payload["warnings"]
    )
