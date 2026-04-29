"""OMIEService — async client for OMIE day-ahead marginal price files.

Reasoning-first contract:

- The agent must declare the date window explicitly. The service does
  not pick a default window or guess "this month".
- OMIE publishes daily marginal price files in a fixed text format:
  ``marginalpdbc_YYYYMMDD.1``. Each row contains a year/month/day/hour
  index and two prices in EUR/MWh — the first column is the Portuguese
  zone, the second is the Spanish zone (per OMIE documentation).
- Output is normalized into :class:`PriceSeriesResult` so downstream
  tools never deal with the raw OMIE file format.
- HTTP errors raise :class:`ExternalServiceError`. Tests mock all HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger
from app.schemas.prices import (
    MarketArea,
    OmieMarketPriceRequest,
    PricePoint,
    PriceProviderWarning,
    PriceSeriesResult,
    PriceSource,
    PriceUnit,
)

logger = get_logger(__name__)

_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)

_FILE_DOWNLOAD_PATH = "/es/file-download"
_PARENTS = "marginalpdbc"


class OMIEService:
    """Async client for OMIE marginal price files."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.omie_base_url).rstrip("/")
        self._timeout = float(timeout_seconds or settings.price_provider_timeout_seconds)
        self._max_retries = int(max_retries or settings.http_max_retries)
        self._injected_client = http_client

    # --- URL building -----------------------------------------------------

    def _file_url(self, date: datetime) -> tuple[str, dict[str, Any]]:
        filename = f"marginalpdbc_{date.strftime('%Y%m%d')}.1"
        url = f"{self._base_url}{_FILE_DOWNLOAD_PATH}"
        params: dict[str, Any] = {"parents": _PARENTS, "filename": filename}
        return url, params

    # --- HTTP -------------------------------------------------------------

    async def _fetch(self, url: str, params: dict[str, Any]) -> httpx.Response:
        retry = AsyncRetrying(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(max(1, self._max_retries)),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            reraise=True,
        )

        async def _do() -> httpx.Response:
            if self._injected_client is not None:
                return await self._injected_client.get(
                    url, params=params, timeout=self._timeout
                )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.get(url, params=params)

        async for attempt in retry:
            with attempt:
                return await _do()

        raise ExternalServiceError("OMIE request did not produce a response")

    # --- Parsing ----------------------------------------------------------

    @staticmethod
    def _parse_file(text: str, market_area: MarketArea) -> list[PricePoint]:
        """Parse an OMIE marginalpdbc file into hourly PricePoint entries.

        File format (semicolon separated, one header line + hourly rows):
            MARGINALPDBC;
            2026;04;28;01;<PT EUR/MWh>;<ES EUR/MWh>;
            ...
            *
        """

        points: list[PricePoint] = []
        column_index = 5 if market_area in ("ES", "MIBEL") else 4
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("MARGINALPDBC") or line.startswith("*"):
                continue
            parts = [p for p in line.split(";") if p != ""]
            if len(parts) < 6:
                continue
            try:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                hour = int(parts[3])
                value_eur_mwh = float(parts[column_index].replace(",", "."))
            except (ValueError, IndexError):
                continue
            ts = datetime(year, month, day, hour - 1, tzinfo=UTC)
            points.append(
                PricePoint(
                    timestamp=ts,
                    value=value_eur_mwh,
                    unit=PriceUnit.eur_per_mwh,
                    value_eur_kwh=value_eur_mwh / 1000.0,
                )
            )
        return points

    # --- Public API -------------------------------------------------------

    async def fetch_marginal_prices(
        self, request: OmieMarketPriceRequest
    ) -> PriceSeriesResult:
        all_points: list[PricePoint] = []
        warnings: list[PriceProviderWarning] = []
        last_url: str | None = None

        cursor = datetime(
            request.start_date.year,
            request.start_date.month,
            request.start_date.day,
        )
        end_inclusive = datetime(
            request.end_date.year,
            request.end_date.month,
            request.end_date.day,
        )

        while cursor <= end_inclusive:
            url, params = self._file_url(cursor)
            logger.info("omie_request", url=url, filename=params["filename"])
            try:
                response = await self._fetch(url, params)
            except _RETRYABLE_EXCEPTIONS as exc:
                raise ExternalServiceError(
                    "OMIE network failure",
                    details={"error": str(exc), "filename": params["filename"]},
                ) from exc

            if response.status_code == 404:
                warnings.append(
                    PriceProviderWarning(
                        code="omie_file_missing",
                        message=(
                            f"OMIE marginal price file not available for "
                            f"{cursor.date().isoformat()}; skipped."
                        ),
                    )
                )
                cursor += timedelta(days=1)
                continue

            if response.status_code >= 400:
                raise ExternalServiceError(
                    "OMIE returned an error response",
                    details={
                        "status": response.status_code,
                        "filename": params["filename"],
                        "body": response.text[:500],
                    },
                )

            last_url = str(response.url)
            day_points = self._parse_file(response.text, request.market_area)
            if not day_points:
                warnings.append(
                    PriceProviderWarning(
                        code="omie_file_unparsed",
                        message=(
                            f"OMIE file for {cursor.date().isoformat()} produced "
                            "no parseable rows."
                        ),
                    )
                )
            all_points.extend(day_points)
            cursor += timedelta(days=1)

        if not all_points:
            raise ExternalServiceError(
                "OMIE returned no usable data for the requested window",
                details={
                    "start": request.start_date.isoformat(),
                    "end": request.end_date.isoformat(),
                },
            )

        warnings.append(
            PriceProviderWarning(
                code="omie_wholesale_reference_only",
                message=(
                    "OMIE marginal price is a wholesale market reference, not the "
                    "net revenue a residential prosumer receives. Net revenue "
                    "depends on contract, representation fees, taxes, and access charges."
                ),
            )
        )

        average_eur_kwh = sum(p.value_eur_kwh for p in all_points) / len(all_points)
        return PriceSeriesResult(
            source_name=PriceSource.omie,
            source_url=last_url,
            indicator_id=None,
            market_area=request.market_area,
            date_range_start=request.start_date,
            date_range_end=request.end_date,
            aggregation=request.aggregation,
            unit_original=PriceUnit.eur_per_mwh,
            unit_normalized=PriceUnit.eur_per_kwh,
            average_price_eur_kwh=average_eur_kwh,
            price_series=all_points,
            retrieved_at=datetime.now(tz=UTC),
            warnings=warnings,
        )
