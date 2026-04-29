"""PVGISService — async client for the PVcalc endpoint.

Reasoning-first contract:

- Every input is explicit. The service does NOT fall back to PVGIS
  server-side defaults silently. Missing inputs are caller errors.
- No regex, no keyword matching, no domain heuristics.
- Network failures are retried via tenacity. HTTP errors (4xx/5xx) are
  surfaced as :class:`ExternalServiceError` and never retried as if they
  were transient.

The service speaks normalized Pydantic models in / out so callers do not
deal with PVGIS's raw JSON quirks.
"""

from __future__ import annotations

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
from app.schemas.solar_project import PVCalcRequest, PVCalcResult, PVMonthlyEntry

logger = get_logger(__name__)

_PVCALC_PATH = "/PVcalc"
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


class PVGISService:
    """Async client for PVGIS PVcalc."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.pvgis_base_url).rstrip("/")
        self._timeout = float(timeout_seconds or settings.http_timeout_seconds)
        self._max_retries = int(max_retries or settings.http_max_retries)
        self._injected_client = http_client

    # --- Param building ---------------------------------------------------

    @staticmethod
    def _to_pvgis_params(request: PVCalcRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "lat": request.lat,
            "lon": request.lon,
            "peakpower": request.peakpower_kwp,
            "loss": request.system_loss_pct,
            "angle": request.tilt_deg,
            "aspect": request.azimuth_deg,
            "outputformat": "json",
        }
        if request.pv_technology is not None:
            params["pvtechchoice"] = request.pv_technology
        if request.mounting is not None:
            params["mountingplace"] = request.mounting
        if request.use_horizon is not None:
            params["usehorizon"] = 1 if request.use_horizon else 0
        return params

    # --- HTTP -------------------------------------------------------------

    async def _fetch(self, params: dict[str, Any]) -> httpx.Response:
        url = f"{self._base_url}{_PVCALC_PATH}"
        retry = AsyncRetrying(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(max(1, self._max_retries)),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            reraise=True,
        )

        async def _do() -> httpx.Response:
            if self._injected_client is not None:
                return await self._injected_client.get(url, params=params, timeout=self._timeout)
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.get(url, params=params)

        async for attempt in retry:
            with attempt:
                return await _do()

        raise ExternalServiceError("PVGIS request did not produce a response")

    # --- Normalization ----------------------------------------------------

    @staticmethod
    def _normalize(payload: dict[str, Any], source_url: str | None) -> PVCalcResult:
        outputs = payload.get("outputs") or {}
        monthly_block = (outputs.get("monthly") or {}).get("fixed") or []
        totals_block = (outputs.get("totals") or {}).get("fixed") or {}

        if not isinstance(monthly_block, list) or not isinstance(totals_block, dict):
            raise ExternalServiceError(
                "PVGIS response shape is invalid",
                details={
                    "monthly_type": type(monthly_block).__name__,
                    "totals_type": type(totals_block).__name__,
                },
            )

        monthly: list[PVMonthlyEntry] = []
        try:
            for entry in monthly_block:
                monthly.append(
                    PVMonthlyEntry(
                        month=int(entry["month"]),
                        energy_kwh=float(entry["E_m"]),
                        in_plane_irradiation_kwh_per_m2=float(entry["H(i)_m"]),
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError(
                "PVGIS response shape is invalid",
                details={"missing_or_invalid_field": str(exc)},
            ) from exc

        monthly.sort(key=lambda item: item.month)

        annual_energy = totals_block.get("E_y")
        if annual_energy is None and monthly:
            annual_energy = sum(m.energy_kwh for m in monthly)
        if annual_energy is None:
            raise ExternalServiceError(
                "PVGIS response missing annual energy and monthly data",
                details={"payload_keys": list(payload.keys())},
            )

        warnings: list[str] = []
        if len(monthly) != 12:
            warnings.append(
                f"PVGIS returned {len(monthly)} monthly entries instead of 12; result may be partial."
            )

        meta = payload.get("meta")
        raw_metadata = meta if isinstance(meta, dict) else None

        return PVCalcResult(
            annual_energy_kwh=float(annual_energy),
            monthly=monthly,
            annual_in_plane_irradiation_kwh_per_m2=(
                float(totals_block["H(i)_y"]) if "H(i)_y" in totals_block else None
            ),
            source_url=source_url,
            raw_metadata=raw_metadata,
            warnings=warnings,
        )

    # --- Public API -------------------------------------------------------

    async def estimate_production(self, request: PVCalcRequest) -> PVCalcResult:
        params = self._to_pvgis_params(request)
        url = f"{self._base_url}{_PVCALC_PATH}"
        logger.info("pvgis_request", url=url, lat=request.lat, lon=request.lon)

        try:
            response = await self._fetch(params)
        except _RETRYABLE_EXCEPTIONS as exc:
            raise ExternalServiceError(
                "PVGIS network failure",
                details={"error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                "PVGIS returned an error response",
                details={"status": response.status_code, "body": response.text[:500]},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "PVGIS response is not valid JSON",
                details={"error": str(exc), "body": response.text[:200]},
            ) from exc

        result = self._normalize(payload, source_url=str(response.url))
        logger.info(
            "pvgis_result",
            annual_energy_kwh=result.annual_energy_kwh,
            months=len(result.monthly),
        )
        return result
