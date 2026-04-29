"""ESIOSService — async client for the ESIOS REE indicators API.

Reasoning-first contract:

- Inputs are explicit (indicator id, window, timezone, optional geo). The
  service does not invent indicators or windows.
- The ESIOS personal token is read from settings. If absent at request
  time, raise :class:`ConfigurationError` — never silently substitute a
  fake value, never return a fabricated price series.
- HTTP errors and bad payload shapes raise :class:`ExternalServiceError`.
- Tests must mock HTTP. The service makes no real network calls.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.errors import ConfigurationError, ExternalServiceError
from app.core.logging import get_logger
from app.schemas.prices import (
    EsiosIndicatorRequest,
    PricePoint,
    PriceSeriesResult,
    PriceSource,
    PriceUnit,
)

logger = get_logger(__name__)

_INDICATOR_PATH = "/indicators/{indicator_id}"
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


class ESIOSService:
    """Async client for the ESIOS REE indicators endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.esios_api_base_url).rstrip("/")
        self._token = api_token if api_token is not None else settings.esios_api_token
        self._timeout = float(timeout_seconds or settings.price_provider_timeout_seconds)
        self._max_retries = int(max_retries or settings.http_max_retries)
        self._injected_client = http_client

    # --- Param building ---------------------------------------------------

    @staticmethod
    def _format_iso(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()

    def _build_params(self, request: EsiosIndicatorRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "start_date": self._format_iso(request.start_datetime),
            "end_date": self._format_iso(request.end_datetime),
            "time_trunc": request.aggregation,
            "time_zone": request.timezone,
        }
        if request.geo_id is not None:
            params["geo_ids[]"] = request.geo_id
        return params

    def _build_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json; application/vnd.esios-api-v2+json",
            "Content-Type": "application/json",
            "x-api-key": self._token,
        }

    # --- HTTP -------------------------------------------------------------

    async def _fetch(self, url: str, params: dict[str, Any]) -> httpx.Response:
        retry = AsyncRetrying(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(max(1, self._max_retries)),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            reraise=True,
        )
        headers = self._build_headers()

        async def _do() -> httpx.Response:
            if self._injected_client is not None:
                return await self._injected_client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout,
                )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.get(url, params=params, headers=headers)

        async for attempt in retry:
            with attempt:
                return await _do()

        raise ExternalServiceError("ESIOS request did not produce a response")

    # --- Normalization ----------------------------------------------------

    @staticmethod
    def _normalize(
        payload: dict[str, Any],
        request: EsiosIndicatorRequest,
        source_url: str,
    ) -> PriceSeriesResult:
        indicator_block = payload.get("indicator")
        if not isinstance(indicator_block, dict):
            raise ExternalServiceError(
                "ESIOS response missing 'indicator' block",
                details={"payload_keys": list(payload.keys())},
            )

        values = indicator_block.get("values")
        if not isinstance(values, list):
            raise ExternalServiceError(
                "ESIOS response 'indicator.values' is not a list",
                details={"indicator_keys": list(indicator_block.keys())},
            )

        unit_label = (indicator_block.get("magnitud") or [{}])[0].get("name") if isinstance(
            indicator_block.get("magnitud"), list
        ) else None
        # ESIOS reports indicator unit via 'magnitud'/'tiempo'; in absence of a
        # consistent unit field we trust the documented unit per indicator. For
        # 1739 and the PVPC family the unit is EUR/MWh.
        unit_original = PriceUnit.eur_per_mwh
        if isinstance(unit_label, str) and "kwh" in unit_label.lower():
            unit_original = PriceUnit.eur_per_kwh

        points: list[PricePoint] = []
        for entry in values:
            try:
                ts_raw = entry["datetime"]
                value_raw = entry["value"]
            except (KeyError, TypeError) as exc:
                raise ExternalServiceError(
                    "ESIOS value entry missing required field",
                    details={"missing_field": str(exc)},
                ) from exc
            try:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                value = float(value_raw)
            except (TypeError, ValueError) as exc:
                raise ExternalServiceError(
                    "ESIOS value entry has invalid types",
                    details={"error": str(exc)},
                ) from exc
            value_eur_kwh = value / 1000.0 if unit_original == PriceUnit.eur_per_mwh else value
            points.append(
                PricePoint(
                    timestamp=ts,
                    value=value,
                    unit=unit_original,
                    value_eur_kwh=value_eur_kwh,
                )
            )

        if not points:
            raise ExternalServiceError(
                "ESIOS returned an empty series for the requested window",
                details={"indicator_id": request.indicator_id},
            )

        average_eur_kwh = sum(p.value_eur_kwh for p in points) / len(points)

        return PriceSeriesResult(
            source_name=PriceSource.esios,
            source_url=source_url,
            indicator_id=request.indicator_id,
            market_area=None,
            date_range_start=request.start_datetime,
            date_range_end=request.end_datetime,
            aggregation=request.aggregation,
            unit_original=unit_original,
            unit_normalized=PriceUnit.eur_per_kwh,
            average_price_eur_kwh=average_eur_kwh,
            price_series=points,
            retrieved_at=datetime.now(tz=UTC),
            warnings=[],
        )

    # --- Public API -------------------------------------------------------

    async def fetch_indicator(self, request: EsiosIndicatorRequest) -> PriceSeriesResult:
        if not self._token:
            raise ConfigurationError(
                "ESIOS_API_TOKEN is not configured; cannot query ESIOS.",
                details={"indicator_id": request.indicator_id},
            )

        url = f"{self._base_url}{_INDICATOR_PATH.format(indicator_id=request.indicator_id)}"
        params = self._build_params(request)
        logger.info(
            "esios_request",
            url=url,
            indicator_id=request.indicator_id,
            start=params["start_date"],
            end=params["end_date"],
        )

        try:
            response = await self._fetch(url, params)
        except _RETRYABLE_EXCEPTIONS as exc:
            raise ExternalServiceError(
                "ESIOS network failure",
                details={"error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                "ESIOS returned an error response",
                details={"status": response.status_code, "body": response.text[:500]},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "ESIOS response is not valid JSON",
                details={"error": str(exc), "body": response.text[:200]},
            ) from exc

        result = self._normalize(payload, request, source_url=str(response.url))
        logger.info(
            "esios_result",
            indicator_id=request.indicator_id,
            points=len(result.price_series),
            average_eur_kwh=result.average_price_eur_kwh,
        )
        return result
