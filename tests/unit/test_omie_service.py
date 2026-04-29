from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.schemas.prices import OmieMarketPriceRequest, PriceSource, PriceUnit
from app.services.omie_service import OMIEService


def _request(**overrides: Any) -> OmieMarketPriceRequest:
    base: dict[str, Any] = {
        "start_date": datetime(2026, 4, 1),
        "end_date": datetime(2026, 4, 1),
        "market_area": "ES",
        "aggregation": "hourly",
    }
    base.update(overrides)
    return OmieMarketPriceRequest(**base)


def _omie_file_text() -> str:
    rows = ["MARGINALPDBC;"]
    for hour in range(1, 25):
        rows.append(f"2026;04;01;{hour:02d};50.0;60.0;")
    rows.append("*")
    return "\n".join(rows)


def test_request_window_validation() -> None:
    with pytest.raises(ValueError):
        OmieMarketPriceRequest(
            start_date=datetime(2026, 4, 2),
            end_date=datetime(2026, 4, 1),
        )


@pytest.mark.asyncio
async def test_fetch_marginal_prices_parses_es_column() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text=_omie_file_text(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OMIEService(
            base_url="https://www.omie.es",
            http_client=client,
            max_retries=1,
        )
        result = await service.fetch_marginal_prices(_request())

    assert len(captured) == 1
    assert "marginalpdbc_20260401.1" in captured[0].url.params["filename"]
    assert result.source_name == PriceSource.omie
    assert result.market_area == "ES"
    assert result.unit_original == PriceUnit.eur_per_mwh
    assert result.unit_normalized == PriceUnit.eur_per_kwh
    assert len(result.price_series) == 24
    assert all(point.value_eur_kwh == pytest.approx(0.06) for point in result.price_series)
    assert result.average_price_eur_kwh == pytest.approx(0.06)
    assert any(w.code == "omie_wholesale_reference_only" for w in result.warnings)


@pytest.mark.asyncio
async def test_fetch_marginal_prices_skips_missing_days_with_warning() -> None:
    counter = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["calls"] += 1
        if counter["calls"] == 1:
            return httpx.Response(404, text="not found", request=request)
        return httpx.Response(200, text=_omie_file_text(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OMIEService(http_client=client, max_retries=1)
        result = await service.fetch_marginal_prices(
            _request(end_date=datetime(2026, 4, 2))
        )

    assert any(w.code == "omie_file_missing" for w in result.warnings)
    assert len(result.price_series) == 24


@pytest.mark.asyncio
async def test_fetch_marginal_prices_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OMIEService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="OMIE returned an error"):
            await service.fetch_marginal_prices(_request())


@pytest.mark.asyncio
async def test_fetch_marginal_prices_raises_on_no_usable_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OMIEService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="no usable data"):
            await service.fetch_marginal_prices(_request())


@pytest.mark.asyncio
async def test_fetch_marginal_prices_picks_pt_column_for_pt_area() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_omie_file_text(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = OMIEService(http_client=client, max_retries=1)
        result = await service.fetch_marginal_prices(_request(market_area="PT"))

    assert all(point.value_eur_kwh == pytest.approx(0.05) for point in result.price_series)
