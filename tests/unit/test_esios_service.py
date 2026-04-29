from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.core.errors import ConfigurationError, ExternalServiceError
from app.schemas.prices import EsiosIndicatorRequest, PriceSource, PriceUnit
from app.services.esios_service import ESIOSService


def _request(**overrides: Any) -> EsiosIndicatorRequest:
    base: dict[str, Any] = {
        "indicator_id": 1739,
        "start_datetime": datetime(2026, 4, 1, tzinfo=UTC),
        "end_datetime": datetime(2026, 4, 30, tzinfo=UTC),
        "aggregation": "daily",
        "timezone": "Europe/Madrid",
    }
    base.update(overrides)
    return EsiosIndicatorRequest(**base)


def _payload(values: list[tuple[str, float]]) -> dict[str, Any]:
    return {
        "indicator": {
            "id": 1739,
            "name": "Precio excedentes autoconsumo",
            "magnitud": [{"name": "EUR/MWh"}],
            "values": [{"datetime": ts, "value": value} for ts, value in values],
        }
    }


def test_request_window_must_be_strictly_positive() -> None:
    with pytest.raises(ValueError):
        EsiosIndicatorRequest(
            indicator_id=1739,
            start_datetime=datetime(2026, 4, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 4, 1, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_fetch_indicator_requires_token() -> None:
    service = ESIOSService(api_token="", max_retries=1)
    with pytest.raises(ConfigurationError, match="ESIOS_API_TOKEN"):
        await service.fetch_indicator(_request())


@pytest.mark.asyncio
async def test_fetch_indicator_normalizes_eur_per_mwh_to_eur_per_kwh() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_payload(
                [
                    ("2026-04-01T00:00:00+02:00", 80.0),
                    ("2026-04-02T00:00:00+02:00", 120.0),
                ]
            ),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ESIOSService(
            base_url="https://api.esios.ree.es",
            api_token="dummy-token",
            http_client=client,
            max_retries=1,
        )
        result = await service.fetch_indicator(_request())

    assert len(captured) == 1
    assert "/indicators/1739" in str(captured[0].url)
    assert captured[0].headers["x-api-key"] == "dummy-token"
    assert result.source_name == PriceSource.esios
    assert result.indicator_id == 1739
    assert result.unit_original == PriceUnit.eur_per_mwh
    assert result.unit_normalized == PriceUnit.eur_per_kwh
    assert result.average_price_eur_kwh == pytest.approx(0.1)
    assert len(result.price_series) == 2
    assert result.price_series[0].value_eur_kwh == pytest.approx(0.08)


@pytest.mark.asyncio
async def test_fetch_indicator_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ESIOSService(api_token="dummy", http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="ESIOS returned an error"):
            await service.fetch_indicator(_request())


@pytest.mark.asyncio
async def test_fetch_indicator_raises_on_empty_series() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload([]), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ESIOSService(api_token="dummy", http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="empty series"):
            await service.fetch_indicator(_request())


@pytest.mark.asyncio
async def test_fetch_indicator_retries_transient_network_failures() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(
            200,
            json=_payload([("2026-04-01T00:00:00+02:00", 100.0)]),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = ESIOSService(api_token="dummy", http_client=client, max_retries=2)
        result = await service.fetch_indicator(_request())

    assert attempts == 2
    assert result.average_price_eur_kwh == pytest.approx(0.1)
