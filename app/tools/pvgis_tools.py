"""LangChain tools wrapping the PVGIS PVcalc service."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from app.schemas.responses import SolarProductionEstimateResponse
from app.schemas.solar_project import (
    MountingPlace,
    PVCalcRequest,
    PVCalcResult,
    PvTechnology,
)
from app.services.pvgis_service import PVGISService


@lru_cache(maxsize=1)
def _default_service() -> PVGISService:
    return PVGISService()


def _to_response(result: PVCalcResult) -> SolarProductionEstimateResponse:
    monthly = sorted(result.monthly, key=lambda item: item.month)
    return SolarProductionEstimateResponse(
        annual_energy_kwh=result.annual_energy_kwh,
        monthly_energy_kwh=[item.energy_kwh for item in monthly],
        monthly_in_plane_irradiation=[
            item.in_plane_irradiation_kwh_per_m2 for item in monthly
        ],
        source_name=result.source_name,
        source_version=result.source_version,
        raw_metadata=result.raw_metadata,
        warnings=result.warnings,
    )


def build_pvgis_tool(service: PVGISService | None = None):
    """Return an async LangChain tool bound to a specific PVGIS service."""

    bound_service = service or _default_service()

    @tool("estimate_solar_production_with_pvgis", args_schema=PVCalcRequest)
    async def estimate_solar_production_with_pvgis(
        lat: float,
        lon: float,
        peakpower_kwp: float,
        system_loss_pct: float,
        tilt_deg: float,
        azimuth_deg: float,
        pv_technology: PvTechnology | None = None,
        mounting: MountingPlace | None = None,
        use_horizon: bool | None = None,
    ) -> dict[str, object]:
        """Query PVGIS PVcalc to estimate monthly and annual PV production.

        Every required parameter must already be explicit. The tool never
        invents tilt, azimuth, losses, or peak power on its own.
        """

        request = PVCalcRequest(
            lat=lat,
            lon=lon,
            peakpower_kwp=peakpower_kwp,
            system_loss_pct=system_loss_pct,
            tilt_deg=tilt_deg,
            azimuth_deg=azimuth_deg,
            pv_technology=pv_technology,
            mounting=mounting,
            use_horizon=use_horizon,
        )
        result = await bound_service.estimate_production(request)
        return _to_response(result).model_dump()

    return estimate_solar_production_with_pvgis


estimate_solar_production_with_pvgis = build_pvgis_tool()
