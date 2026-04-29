"""LangChain tools wrapping explicit location geocoding."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from app.schemas.solar_project import GeocodingRequest
from app.services.geocoding_service import GeocodingService


@lru_cache(maxsize=1)
def _default_service() -> GeocodingService:
    return GeocodingService()


def build_geocoding_tool(service: GeocodingService | None = None):
    """Return an async LangChain tool bound to a specific geocoding service."""

    bound_service = service or _default_service()

    @tool("geocode_location", args_schema=GeocodingRequest)
    async def geocode_location(
        location_text: str,
        country_hint: str | None = None,
        language: str | None = None,
    ) -> dict[str, object]:
        """Geocode an explicit textual location into coordinates and admin data.

        The tool does not interpret intent, expand keywords, or repair the
        location semantically. It only geocodes the explicit input supplied.
        """

        request = GeocodingRequest(
            location_text=location_text,
            country_hint=country_hint,
            language=language,
        )
        result = await bound_service.geocode(request)
        return result.model_dump()

    return geocode_location


geocode_location = build_geocoding_tool()
