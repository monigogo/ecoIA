from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from app.services.bdns_service import BDNSService
from app.tools.subsidy_tools import build_search_subsidies_tool


def _payload() -> dict[str, Any]:
    return {
        "convocatorias": [
            {
                "idConvocatoria": "BDNS-99999",
                "descripcion": "Programa autoconsumo Andalucía 2026",
                "nivelAdministrativo": "Comunidad Autónoma",
                "comunidadAutonoma": "Andalucía",
                "estado": "Abierta",
                "fechaFinSolicitud": "2026-12-31",
                "urlConvocatoria": "https://example.org/conv/99999",
                "beneficiarios": "Personas físicas",
                "finalidad": "Autoconsumo residencial",
            }
        ]
    }


@pytest.mark.asyncio
@respx.mock
async def test_search_subsidies_tool_normalizes_mocked_bdns() -> None:
    route = respx.get(
        "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda"
    ).mock(return_value=httpx.Response(200, json=_payload()))

    async with httpx.AsyncClient() as client:
        service = BDNSService(http_client=client, max_retries=1)
        tool = build_search_subsidies_tool(service=service)

        payload = await tool.ainvoke(
            {
                "project_context": "Vivienda unifamiliar 5kWp",
                "location_context": "Sevilla, Andalucía",
                "reasoned_query": "ayudas autoconsumo solar fotovoltaico residencial",
                "autonomous_community": "Andalucía",
            }
        )

    assert route.called
    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["id"] == "BDNS-99999"
    assert candidate["administration"] == "autonomous_community"
    assert candidate["status"] == "open"
    assert candidate["requires_verification"] is True
