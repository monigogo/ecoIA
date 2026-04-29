"""LangChain tool exposing compound solar-base scenario candidates."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.tools import tool

from app.schemas.solar_scenario import SolarBaseScenarioRequest
from app.services.solar_scenario_service import SolarScenarioService


@lru_cache(maxsize=1)
def _default_service() -> SolarScenarioService:
    return SolarScenarioService()


def build_solar_base_scenario_tool(service: SolarScenarioService | None = None):
    bound_service = service or _default_service()

    @tool("get_solar_base_scenario_candidates", args_schema=SolarBaseScenarioRequest)
    def get_solar_base_scenario_candidates(
        known_user_data: dict[str, Any],
        location_context: str,
        user_goal: str,
        missing_fields: list[str],
        allow_orientative_scenario: bool,
        max_candidates: int = 3,
    ) -> dict[str, Any]:
        """Return complete candidate scenarios for broad orientative solar estimates.

        Use this when several base PV parameters are missing at once, such as
        panel power, panel dimensions, tilt, azimuth, system loss, or a
        lifetime degradation rate for a broad orientative estimate. The tool
        returns coherent candidate bundles with sources and limitations. It
        does not choose a scenario and does not apply silent defaults.
        """

        request = SolarBaseScenarioRequest(
            known_user_data=known_user_data,
            location_context=location_context,
            user_goal=user_goal,
            missing_fields=missing_fields,
            allow_orientative_scenario=allow_orientative_scenario,
            max_candidates=max_candidates,
        )
        response = bound_service.generate_candidates(request)
        return response.model_dump()

    return get_solar_base_scenario_candidates


get_solar_base_scenario_candidates = build_solar_base_scenario_tool()


__all__ = ["build_solar_base_scenario_tool", "get_solar_base_scenario_candidates"]
