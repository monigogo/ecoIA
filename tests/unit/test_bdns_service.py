from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.schemas.subsidy import (
    Administration,
    SubsidySearchRequest,
    SubsidyStatus,
)
from app.services.bdns_service import BDNSService


def _request(**overrides: Any) -> SubsidySearchRequest:
    base: dict[str, Any] = {
        "project_context": "Residencial unifamiliar",
        "location_context": "Sevilla, Andalucía",
        "reasoned_query": "ayudas autoconsumo solar fotovoltaico residencial",
        "autonomous_community": "Andalucía",
    }
    base.update(overrides)
    return SubsidySearchRequest(**base)


def _payload(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"convocatorias": entries}


@pytest.mark.asyncio
async def test_search_normalizes_bdns_payload() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_payload(
                [
                    {
                        "idConvocatoria": "BDNS-12345",
                        "descripcion": "Ayudas autoconsumo solar Andalucía",
                        "nivelAdministrativo": "Comunidad Autónoma",
                        "comunidadAutonoma": "Andalucía",
                        "estado": "Abierta",
                        "fechaFinSolicitud": "2026-12-31",
                        "urlConvocatoria": "https://example.org/conv/12345",
                        "beneficiarios": "Personas físicas",
                        "finalidad": "Autoconsumo fotovoltaico residencial",
                    }
                ]
            ),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = BDNSService(
            base_url="https://www.infosubvenciones.es/bdnstrans/api",
            http_client=client,
            max_retries=1,
        )
        result = await service.search(_request())

    assert len(captured) == 1
    assert captured[0].url.params["descripcion"]
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.id == "BDNS-12345"
    assert candidate.administration == Administration.autonomous_community
    assert candidate.status == SubsidyStatus.open
    assert candidate.deadline is not None
    assert candidate.requires_verification is True


@pytest.mark.asyncio
async def test_search_warns_when_no_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload([]), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = BDNSService(http_client=client, max_retries=1)
        result = await service.search(_request())

    assert result.candidates == []
    assert any("no normalized candidates" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_search_skips_entries_without_id_or_title() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_payload(
                [
                    {"idConvocatoria": "X", "descripcion": "Valid"},
                    {"descripcion": "missing id"},
                    {"idConvocatoria": "Y"},
                ]
            ),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = BDNSService(http_client=client, max_retries=1)
        result = await service.search(_request())

    assert len(result.candidates) == 1
    assert any("were skipped" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_search_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="boom", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = BDNSService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="BDNS returned an error"):
            await service.search(_request())


@pytest.mark.asyncio
async def test_search_raises_on_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = BDNSService(http_client=client, max_retries=1)
        with pytest.raises(ExternalServiceError, match="not valid JSON"):
            await service.search(_request())
