"""GeocodingService - async client for explicit location geocoding.

Reasoning-first contract:

- The service geocodes only an explicit location string received from the
  caller. It does not infer intent, repair phrasing, or inject hidden
  geographic defaults.
- Provider hints such as country or language are passed through only when
  supplied explicitly.
- Queries are cached by a hashed request key so raw location text is not
  used as a cache key or emitted in logs.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Protocol

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.errors import ExternalServiceError, ValidationAppError
from app.core.logging import get_logger
from app.schemas.solar_project import (
    GeocodingCandidate,
    GeocodingRequest,
    GeocodingResult,
)

logger = get_logger(__name__)

_SEARCH_PATH = "/search"
_DEFAULT_LIMIT = 5
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


class CacheBackend(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any, expire: float | None = None) -> Any: ...


class _InMemoryTTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, Any]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return default

        expires_at, value = entry
        if expires_at is not None and expires_at <= time.monotonic():
            self._store.pop(key, None)
            return default
        return value

    def set(self, key: str, value: Any, expire: float | None = None) -> Any:
        expires_at = None if expire is None or expire <= 0 else time.monotonic() + expire
        self._store[key] = (expires_at, value)
        return True


class GeocodingService:
    """Async client for Nominatim search."""

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        min_interval_seconds: float | None = None,
        cache_ttl_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.geocoding_base_url).rstrip("/")
        self._user_agent = user_agent or settings.geocoding_user_agent
        self._timeout = float(timeout_seconds or settings.http_timeout_seconds)
        self._max_retries = int(max_retries or settings.http_max_retries)
        self._min_interval_seconds = float(
            min_interval_seconds
            if min_interval_seconds is not None
            else settings.geocoding_min_interval_seconds
        )
        self._cache_ttl_seconds = float(
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else settings.geocoding_cache_ttl_seconds
        )
        self._injected_client = http_client
        self._cache = cache_backend or _InMemoryTTLCache()
        self._rate_limit_lock = asyncio.Lock()
        self._last_request_started = 0.0

    @staticmethod
    def _to_params(request: GeocodingRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "q": request.location_text,
            "format": "geojson",
            "addressdetails": 1,
            "limit": _DEFAULT_LIMIT,
        }
        if request.country_hint is not None:
            params["countrycodes"] = request.country_hint.lower()
        if request.language is not None:
            params["accept-language"] = request.language
        return params

    @staticmethod
    def _cache_key(request: GeocodingRequest) -> str:
        canonical = json.dumps(
            request.model_dump(exclude_none=True),
            sort_keys=True,
            ensure_ascii=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def _normalize_candidate(cls, feature: dict[str, Any]) -> GeocodingCandidate:
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "feature is missing properties or geometry"},
            )

        display_name = properties.get("display_name")
        importance = properties.get("importance")
        address = properties.get("address") or {}
        coordinates = geometry.get("coordinates")

        if not isinstance(display_name, str) or not display_name.strip():
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "display_name is missing"},
            )
        if not isinstance(address, dict):
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "address is not a dictionary"},
            )
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "coordinates are missing"},
            )
        if importance is None:
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "importance is missing"},
            )

        longitude = float(coordinates[0])
        latitude = float(coordinates[1])

        return GeocodingCandidate(
            normalized_name=display_name,
            latitude=latitude,
            longitude=longitude,
            municipality=address.get("city") if isinstance(address.get("city"), str) else None,
            province=address.get("county") if isinstance(address.get("county"), str) else None,
            autonomous_community=(
                address.get("state") if isinstance(address.get("state"), str) else None
            ),
            country=address.get("country") if isinstance(address.get("country"), str) else None,
            confidence=float(importance),
        )

    @classmethod
    def _normalize(cls, payload: dict[str, Any], source_url: str) -> GeocodingResult:
        features = payload.get("features")
        if not isinstance(features, list):
            raise ExternalServiceError(
                "Geocoding response shape is invalid",
                details={"reason": "features is not a list"},
            )
        if not features:
            raise ValidationAppError(
                "Location could not be geocoded",
                details={"source": "Nominatim"},
            )

        candidates = [cls._normalize_candidate(feature) for feature in features]
        primary = candidates[0]
        warnings: list[str] = []
        ranked_candidates: list[GeocodingCandidate] | None = None
        if len(candidates) > 1:
            warnings.append(
                "Geocoding returned multiple ranked candidates; review alternatives before using coordinates."
            )
            ranked_candidates = candidates

        return GeocodingResult(
            normalized_name=primary.normalized_name,
            latitude=primary.latitude,
            longitude=primary.longitude,
            municipality=primary.municipality,
            province=primary.province,
            autonomous_community=primary.autonomous_community,
            country=primary.country,
            confidence=primary.confidence,
            source_url=source_url,
            warnings=warnings,
            candidates=ranked_candidates,
        )

    async def _respect_rate_limit(self) -> None:
        if self._min_interval_seconds <= 0:
            return

        async with self._rate_limit_lock:
            elapsed = time.monotonic() - self._last_request_started
            delay = self._min_interval_seconds - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request_started = time.monotonic()

    async def _fetch(self, params: dict[str, Any]) -> httpx.Response:
        url = f"{self._base_url}{_SEARCH_PATH}"
        headers = {"User-Agent": self._user_agent}
        retry = AsyncRetrying(
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            stop=stop_after_attempt(max(1, self._max_retries)),
            wait=wait_exponential(multiplier=0.2, max=2.0),
            reraise=True,
        )

        async def _do() -> httpx.Response:
            await self._respect_rate_limit()
            if self._injected_client is not None:
                return await self._injected_client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout,
                )
            async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
                return await client.get(url, params=params)

        async for attempt in retry:
            with attempt:
                return await _do()

        raise ExternalServiceError("Geocoding request did not produce a response")

    async def geocode(self, request: GeocodingRequest) -> GeocodingResult:
        cache_key = self._cache_key(request)
        cached = self._cache.get(cache_key)
        if isinstance(cached, dict):
            return GeocodingResult.model_validate(cached)

        params = self._to_params(request)
        source_url = f"{self._base_url}{_SEARCH_PATH}"
        logger.info("geocoding_request", source=source_url, country_hint=request.country_hint)

        try:
            response = await self._fetch(params)
        except _RETRYABLE_EXCEPTIONS as exc:
            raise ExternalServiceError(
                "Geocoding network failure",
                details={"error": str(exc)},
            ) from exc

        if response.status_code == 429:
            retry_after_raw = response.headers.get("Retry-After")
            try:
                retry_after = int(retry_after_raw) if retry_after_raw else None
            except ValueError:
                retry_after = None
            raise ExternalServiceError(
                "Geocoding provider rate limit exceeded",
                details={
                    "status": 429,
                    "retry_after_seconds": retry_after,
                    "code": "geocoding_rate_limited",
                    "policy_hint": (
                        "Public Nominatim allows at most 1 req/s; respect "
                        "GEOCODING_MIN_INTERVAL_SECONDS and consider a self-hosted instance."
                    ),
                },
            )

        if response.status_code == 403:
            raise ExternalServiceError(
                "Geocoding provider refused the request",
                details={
                    "status": 403,
                    "code": "geocoding_forbidden",
                    "policy_hint": (
                        "Verify GEOCODING_USER_AGENT identifies the application; "
                        "the public Nominatim policy forbids generic User-Agent values."
                    ),
                },
            )

        if response.status_code >= 400:
            raise ExternalServiceError(
                "Geocoding provider returned an error response",
                details={"status": response.status_code, "body": response.text[:500]},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "Geocoding response is not valid JSON",
                details={"error": str(exc), "body": response.text[:200]},
            ) from exc

        result = self._normalize(payload, source_url=source_url)
        if self._cache_ttl_seconds > 0:
            self._cache.set(cache_key, result.model_dump(), expire=self._cache_ttl_seconds)

        logger.info(
            "geocoding_result",
            country=result.country,
            candidate_count=len(result.candidates) if result.candidates is not None else 1,
        )
        return result
