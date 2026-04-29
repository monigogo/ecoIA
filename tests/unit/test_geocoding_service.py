from __future__ import annotations

from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.core.errors import ExternalServiceError, ValidationAppError
from app.schemas.solar_project import GeocodingRequest
from app.services.geocoding_service import GeocodingService


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.keys: list[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        return self.store.get(key, default)

    def set(self, key: str, value: Any, expire: float | None = None) -> Any:
        self.keys.append(key)
        self.store[key] = value
        return expire


def _request(**overrides: Any) -> GeocodingRequest:
    base = {
        "location_text": "Sevilla, España",
        "country_hint": "ES",
        "language": "es",
    }
    base.update(overrides)
    return GeocodingRequest(**base)


def _feature(
    display_name: str,
    latitude: float,
    longitude: float,
    city: str,
    county: str,
    state: str,
    country: str,
    importance: float,
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude],
        },
        "properties": {
            "display_name": display_name,
            "importance": importance,
            "address": {
                "city": city,
                "county": county,
                "state": state,
                "country": country,
            },
        },
    }


def _payload(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def test_to_params_serializes_explicit_inputs() -> None:
    params = GeocodingService._to_params(_request())
    assert params == {
        "q": "Sevilla, España",
        "format": "geojson",
        "addressdetails": 1,
        "limit": 5,
        "countrycodes": "es",
        "accept-language": "es",
    }


def test_request_schema_requires_explicit_location_text() -> None:
    with pytest.raises(ValidationError):
        GeocodingRequest(location_text="   ")


@pytest.mark.asyncio
async def test_geocode_calls_search_and_normalizes_response() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=_payload(
                _feature(
                    display_name="Sevilla, Provincia de Sevilla, Andalucía, España",
                    latitude=37.38863,
                    longitude=-5.99534,
                    city="Sevilla",
                    county="Sevilla",
                    state="Andalucía",
                    country="España",
                    importance=0.82,
                )
            ),
            request=request,
        )

    cache = FakeCache()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            cache_backend=cache,
            max_retries=1,
            min_interval_seconds=0,
        )
        result = await service.geocode(_request())

    assert len(requests) == 1
    assert str(requests[0].url).startswith("https://nominatim.openstreetmap.org/search")
    assert requests[0].url.params["q"] == "Sevilla, España"
    assert requests[0].url.params["countrycodes"] == "es"
    assert requests[0].url.params["accept-language"] == "es"
    assert requests[0].headers["User-Agent"] == "solarlife-backend"
    assert result.normalized_name == "Sevilla, Provincia de Sevilla, Andalucía, España"
    assert result.latitude == pytest.approx(37.38863)
    assert result.longitude == pytest.approx(-5.99534)
    assert result.municipality == "Sevilla"
    assert result.province == "Sevilla"
    assert result.autonomous_community == "Andalucía"
    assert result.country == "España"
    assert result.confidence == pytest.approx(0.82)
    assert result.source_name == "Nominatim / OpenStreetMap"
    assert result.source_url == "https://nominatim.openstreetmap.org/search"
    assert result.warnings == []
    assert cache.keys
    assert "Sevilla, España" not in cache.keys[0]


@pytest.mark.asyncio
async def test_geocode_returns_candidates_and_warning_when_ambiguous() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload(
                _feature(
                    display_name="Valencia, Valencia, Comunitat Valenciana, España",
                    latitude=39.4699,
                    longitude=-0.3763,
                    city="Valencia",
                    county="Valencia",
                    state="Comunitat Valenciana",
                    country="España",
                    importance=0.79,
                ),
                _feature(
                    display_name="Valencia de Alcántara, Cáceres, Extremadura, España",
                    latitude=39.4115,
                    longitude=-7.2463,
                    city="Valencia de Alcántara",
                    county="Cáceres",
                    state="Extremadura",
                    country="España",
                    importance=0.52,
                ),
            ),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        result = await service.geocode(_request(location_text="Valencia, España"))

    assert result.municipality == "Valencia"
    assert len(result.warnings) == 1
    assert result.candidates is not None
    assert len(result.candidates) == 2
    assert result.candidates[1].municipality == "Valencia de Alcántara"


@pytest.mark.asyncio
async def test_geocode_raises_controlled_error_when_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        with pytest.raises(ValidationAppError, match="Location could not be geocoded"):
            await service.geocode(_request(location_text="Lugar inexistente"))


@pytest.mark.asyncio
async def test_geocode_raises_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        with pytest.raises(ExternalServiceError, match="Geocoding network failure"):
            await service.geocode(_request())


@pytest.mark.asyncio
async def test_geocode_raises_distinct_error_on_429_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "12"},
            text="Too Many Requests",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        with pytest.raises(ExternalServiceError, match="rate limit") as excinfo:
            await service.geocode(_request())

    assert excinfo.value.details is not None
    assert excinfo.value.details["status"] == 429
    assert excinfo.value.details["retry_after_seconds"] == 12
    assert excinfo.value.details["code"] == "geocoding_rate_limited"


@pytest.mark.asyncio
async def test_geocode_raises_distinct_error_on_403_user_agent_policy() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            max_retries=1,
            min_interval_seconds=0,
            cache_ttl_seconds=0,
        )
        with pytest.raises(ExternalServiceError, match="refused the request") as excinfo:
            await service.geocode(_request())

    assert excinfo.value.details is not None
    assert excinfo.value.details["status"] == 403
    assert excinfo.value.details["code"] == "geocoding_forbidden"
    assert "User-Agent" in excinfo.value.details["policy_hint"]


@pytest.mark.asyncio
async def test_geocode_uses_cache_after_first_network_call() -> None:
    call_count = 0
    cache = FakeCache()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json=_payload(
                _feature(
                    display_name="Sevilla, Provincia de Sevilla, Andalucía, España",
                    latitude=37.38863,
                    longitude=-5.99534,
                    city="Sevilla",
                    county="Sevilla",
                    state="Andalucía",
                    country="España",
                    importance=0.82,
                )
            ),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = GeocodingService(
            http_client=client,
            cache_backend=cache,
            max_retries=1,
            min_interval_seconds=0,
        )
        first = await service.geocode(_request())
        second = await service.geocode(_request())

    assert call_count == 1
    assert first.model_dump() == second.model_dump()
