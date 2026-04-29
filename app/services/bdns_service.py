"""BDNSService — async client for BDNS / SNPSAP convocatorias.

Reasoning-first contract:

- The agent supplies an explicit ``SubsidySearchRequest``. The service
  does not invent regions, beneficiaries, or technologies.
- HTTP errors raise :class:`ExternalServiceError`. Tests mock all HTTP.
- The service does NOT classify eligibility. It returns normalized
  candidates with ``requires_verification=True``.
- Endpoint paths follow the public BDNS REST surface; the exact
  endpoint may evolve and is configurable via ``BDNS_API_BASE_URL``.
"""

from __future__ import annotations

from datetime import date, datetime
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
from app.schemas.subsidy import (
    Administration,
    SubsidyCandidate,
    SubsidySearchRequest,
    SubsidySearchResult,
    SubsidyStatus,
)

logger = get_logger(__name__)

_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)

_CONVOCATORIAS_PATH = "/convocatorias/busqueda"


class BDNSService:
    """Async client for BDNS / SNPSAP convocatorias."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.bdns_api_base_url).rstrip("/")
        self._timeout = float(
            timeout_seconds or settings.subsidy_provider_timeout_seconds
        )
        self._max_retries = int(max_retries or settings.http_max_retries)
        self._injected_client = http_client

    # --- Param building ---------------------------------------------------

    @staticmethod
    def _build_params(request: SubsidySearchRequest) -> dict[str, Any]:
        params: dict[str, Any] = {"descripcion": request.reasoned_query}
        if request.autonomous_community:
            params["comunidadAutonoma"] = request.autonomous_community
        if request.province:
            params["provincia"] = request.province
        if request.municipality:
            params["municipio"] = request.municipality
        if request.date_range_start:
            params["fechaDesde"] = request.date_range_start.isoformat()
        if request.date_range_end:
            params["fechaHasta"] = request.date_range_end.isoformat()
        return params

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
                    url,
                    params=params,
                    timeout=self._timeout,
                    headers={"Accept": "application/json"},
                )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.get(
                    url, params=params, headers={"Accept": "application/json"}
                )

        async for attempt in retry:
            with attempt:
                return await _do()

        raise ExternalServiceError("BDNS request did not produce a response")

    # --- Normalization ----------------------------------------------------

    @staticmethod
    def _parse_administration(value: Any) -> Administration:
        if not isinstance(value, str):
            return Administration.other
        normalized = value.strip().lower()
        mapping = {
            "estado": Administration.state,
            "estatal": Administration.state,
            "comunidad autónoma": Administration.autonomous_community,
            "comunidad autonoma": Administration.autonomous_community,
            "autonómica": Administration.autonomous_community,
            "autonomica": Administration.autonomous_community,
            "provincia": Administration.province,
            "diputación": Administration.province,
            "diputacion": Administration.province,
            "ayuntamiento": Administration.municipality,
            "municipal": Administration.municipality,
            "ue": Administration.eu,
            "europea": Administration.eu,
        }
        return mapping.get(normalized, Administration.other)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    @staticmethod
    def _parse_status(value: Any) -> SubsidyStatus:
        if not isinstance(value, str):
            return SubsidyStatus.unknown
        normalized = value.strip().lower()
        mapping = {
            "abierta": SubsidyStatus.open,
            "open": SubsidyStatus.open,
            "vigente": SubsidyStatus.open,
            "próxima": SubsidyStatus.upcoming,
            "proxima": SubsidyStatus.upcoming,
            "upcoming": SubsidyStatus.upcoming,
            "cerrada": SubsidyStatus.closed,
            "closed": SubsidyStatus.closed,
        }
        return mapping.get(normalized, SubsidyStatus.unknown)

    @classmethod
    def _normalize_entry(cls, entry: dict[str, Any]) -> SubsidyCandidate | None:
        identifier = entry.get("idConvocatoria") or entry.get("id")
        title = entry.get("descripcion") or entry.get("titulo") or entry.get("title")
        if not identifier or not title:
            return None
        return SubsidyCandidate(
            id=str(identifier),
            title=str(title),
            source_name="BDNS",
            source_url=entry.get("urlConvocatoria") or entry.get("url"),
            administration=cls._parse_administration(entry.get("nivelAdministrativo")),
            region=entry.get("comunidadAutonoma"),
            municipality=entry.get("municipio"),
            beneficiary_summary=entry.get("beneficiarios"),
            purpose_summary=entry.get("finalidad"),
            status=cls._parse_status(entry.get("estado")),
            deadline=cls._parse_date(entry.get("fechaFinSolicitud")),
            amount_summary=entry.get("presupuestoTotal"),
            raw_metadata={k: v for k, v in entry.items() if k not in {"raw"}},
            requires_verification=True,
        )

    @classmethod
    def _normalize(
        cls, payload: Any, source_url: str
    ) -> SubsidySearchResult:
        if isinstance(payload, dict):
            entries = payload.get("convocatorias") or payload.get("results") or []
        elif isinstance(payload, list):
            entries = payload
        else:
            entries = []

        if not isinstance(entries, list):
            raise ExternalServiceError(
                "BDNS payload has unexpected shape",
                details={"type": type(payload).__name__},
            )

        candidates: list[SubsidyCandidate] = []
        skipped = 0
        for entry in entries:
            if not isinstance(entry, dict):
                skipped += 1
                continue
            normalized = cls._normalize_entry(entry)
            if normalized is None:
                skipped += 1
                continue
            candidates.append(normalized)

        warnings: list[str] = []
        if skipped:
            warnings.append(
                f"{skipped} BDNS entry(s) were skipped because they lacked a stable id or title."
            )
        if not candidates:
            warnings.append(
                "BDNS returned no normalized candidates for this query; the agent must "
                "not infer the absence of subsidies — only this query produced no rows."
            )

        return SubsidySearchResult(
            candidates=candidates,
            source_name="BDNS",
            source_url=source_url,
            warnings=warnings,
        )

    # --- Public API -------------------------------------------------------

    async def search(self, request: SubsidySearchRequest) -> SubsidySearchResult:
        url = f"{self._base_url}{_CONVOCATORIAS_PATH}"
        params = self._build_params(request)
        logger.info("bdns_request", url=url, params=params)

        try:
            response = await self._fetch(url, params)
        except _RETRYABLE_EXCEPTIONS as exc:
            raise ExternalServiceError(
                "BDNS network failure",
                details={"error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                "BDNS returned an error response",
                details={"status": response.status_code, "body": response.text[:500]},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "BDNS response is not valid JSON",
                details={"error": str(exc), "body": response.text[:200]},
            ) from exc

        result = self._normalize(payload, source_url=str(response.url))
        logger.info("bdns_result", count=len(result.candidates))
        return result
