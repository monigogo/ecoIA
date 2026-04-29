from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from app.services.geocoding_service import GeocodingService
from app.tools.geocoding_tools import build_geocoding_tool


def _payload() -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [-5.99534, 37.38863],
                },
                "properties": {
                    "display_name": "Sevilla, Provincia de Sevilla, Andalucía, España",
                    "importance": 0.82,
                    "address": {
                        "city": "Sevilla",
                        "county": "Sevilla",
                        "state": "Andalucía",
                        "country": "España",
                    },
                },
            }
        ],
    }


@pytest.mark.asyncio
@respx.mock
async def test_geocoding_tool_normalizes_mocked_response() -> None:
    route = respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(200, json=_payload())
    )

    async with httpx.AsyncClient() as client:
        service = GeocodingService(
            http_client=client,
            user_agent="solarlife-tests/1.0",
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        tool = build_geocoding_tool(service=service)

        result = await tool.ainvoke(
            {
                "location_text": "Sevilla, España",
                "country_hint": "ES",
                "language": "es",
            }
        )

    assert route.called
    assert route.calls.last.request.url.params["q"] == "Sevilla, España"
    assert route.calls.last.request.url.params["countrycodes"] == "es"
    assert route.calls.last.request.url.params["accept-language"] == "es"
    assert route.calls.last.request.headers["User-Agent"] == "solarlife-tests/1.0"
    assert result["municipality"] == "Sevilla"
    assert result["autonomous_community"] == "Andalucía"
    assert result["confidence"] == pytest.approx(0.82)
