from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.schemas.solar_project import GeocodingCandidate, GeocodingRequest, GeocodingResult
from app.tools.geocoding_tools import build_geocoding_tool


class StubGeocodingService:
    def __init__(self, result: GeocodingResult) -> None:
        self._result = result
        self.requests: list[GeocodingRequest] = []

    async def geocode(self, request: GeocodingRequest) -> GeocodingResult:
        self.requests.append(request)
        return self._result


def _result(ambiguous: bool = False) -> GeocodingResult:
    candidates = None
    warnings: list[str] = []
    if ambiguous:
        candidates = [
            GeocodingCandidate(
                normalized_name="Valencia, Valencia, Comunitat Valenciana, España",
                latitude=39.4699,
                longitude=-0.3763,
                municipality="Valencia",
                province="Valencia",
                autonomous_community="Comunitat Valenciana",
                country="España",
                confidence=0.79,
            ),
            GeocodingCandidate(
                normalized_name="Valencia de Alcántara, Cáceres, Extremadura, España",
                latitude=39.4115,
                longitude=-7.2463,
                municipality="Valencia de Alcántara",
                province="Cáceres",
                autonomous_community="Extremadura",
                country="España",
                confidence=0.52,
            ),
        ]
        warnings = [
            "Geocoding returned multiple ranked candidates; review alternatives before using coordinates."
        ]

    return GeocodingResult(
        normalized_name="Sevilla, Provincia de Sevilla, Andalucía, España",
        latitude=37.38863,
        longitude=-5.99534,
        municipality="Sevilla",
        province="Sevilla",
        autonomous_community="Andalucía",
        country="España",
        confidence=0.82,
        source_url="https://nominatim.openstreetmap.org/search",
        warnings=warnings,
        candidates=candidates,
    )


def test_tool_has_expected_name_and_schema() -> None:
    tool = build_geocoding_tool(service=StubGeocodingService(_result()))
    assert tool.name == "geocode_location"
    assert tool.description

    schema = tool.args_schema.model_json_schema()
    assert "location_text" in schema["properties"]
    assert "country_hint" in schema["properties"]
    assert "language" in schema["properties"]
    assert schema["required"] == ["location_text"]


@pytest.mark.asyncio
async def test_tool_returns_serializable_output() -> None:
    service = StubGeocodingService(_result())
    tool = build_geocoding_tool(service=service)

    payload = await tool.ainvoke(
        {
            "location_text": "Sevilla, España",
            "country_hint": "ES",
            "language": "es",
        }
    )

    assert isinstance(payload, dict)
    assert payload["normalized_name"] == "Sevilla, Provincia de Sevilla, Andalucía, España"
    assert payload["latitude"] == pytest.approx(37.38863)
    assert payload["longitude"] == pytest.approx(-5.99534)
    assert payload["municipality"] == "Sevilla"
    assert payload["province"] == "Sevilla"
    assert payload["autonomous_community"] == "Andalucía"
    assert payload["country"] == "España"
    assert payload["confidence"] == pytest.approx(0.82)
    assert service.requests[0].location_text == "Sevilla, España"
    assert service.requests[0].country_hint == "ES"
    json.dumps(payload)


@pytest.mark.asyncio
async def test_tool_returns_ambiguous_candidates_without_deciding_them() -> None:
    tool = build_geocoding_tool(service=StubGeocodingService(_result(ambiguous=True)))
    payload = await tool.ainvoke({"location_text": "Valencia, España"})

    assert len(payload["warnings"]) == 1
    assert len(payload["candidates"]) == 2
    assert payload["candidates"][1]["municipality"] == "Valencia de Alcántara"


def test_tool_request_schema_rejects_blank_location() -> None:
    with pytest.raises(ValidationError):
        GeocodingRequest(location_text="   ")
