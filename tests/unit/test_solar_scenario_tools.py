from __future__ import annotations

from typing import Any

import pytest

from app.core.errors import ExternalServiceError
from app.schemas.assumptions import AssumptionConfidence, AssumptionSourceType
from app.schemas.solar_scenario import (
    SolarBaseScenarioCandidate,
    SolarBaseScenarioRequest,
    SolarBaseScenarioResponse,
    SolarScenarioFieldSource,
)
from app.services.solar_scenario_service import SolarScenarioService
from app.tools.solar_scenario_tools import build_solar_base_scenario_tool
from tests.fixtures.fake_chat_model import FakeChatModel


def _factory(_messages: Any) -> SolarBaseScenarioResponse:
    return SolarBaseScenarioResponse(
        candidates=[
            SolarBaseScenarioCandidate(
                id="scenario-1",
                label="orientative residential",
                panel_power_w=450,
                panel_width_m=1.13,
                panel_length_m=1.76,
                system_loss_pct=14,
                solar_degradation_pct=0.5,
                tilt_deg=20,
                azimuth_deg=0,
                field_sources=[
                    SolarScenarioFieldSource(
                        field="panel_power_w",
                        source_type=AssumptionSourceType.technical_reference,
                        source_name="Residential module reference",
                        confidence=AssumptionConfidence.medium,
                        rationale="Representative modern rooftop module.",
                    )
                ],
                confidence=AssumptionConfidence.medium,
                limitations=["Orientative scenario only."],
                requires_user_disclosure=True,
            )
        ]
    )


def _build() -> Any:
    service = SolarScenarioService(model=FakeChatModel(_factory))
    return build_solar_base_scenario_tool(service=service)


def test_tool_has_expected_name_and_schema() -> None:
    tool = _build()
    assert tool.name == "get_solar_base_scenario_candidates"
    schema = tool.args_schema.model_json_schema()
    assert "known_user_data" in schema["properties"]
    assert "missing_fields" in schema["properties"]
    assert "allow_orientative_scenario" in schema["properties"]


def test_tool_invokes_and_returns_serializable_dict() -> None:
    tool = _build()
    result = tool.invoke(
        {
            "known_user_data": {"monthly_consumption_kwh": 500, "roof_width_m": 8, "roof_length_m": 5},
            "location_context": "Sevilla, España",
            "user_goal": "Broad orientative solar estimate",
            "missing_fields": [
                "panel_power_w",
                "panel_width_m",
                "panel_length_m",
                "system_loss_pct",
            ],
            "allow_orientative_scenario": True,
            "max_candidates": 2,
        }
    )
    assert isinstance(result, dict)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["requires_user_disclosure"] is True

    import json

    json.dumps(result)


def test_tool_raises_when_orientative_scenario_returns_no_candidates() -> None:
    service = SolarScenarioService(
        model=FakeChatModel(
            lambda _messages: SolarBaseScenarioResponse.model_construct(candidates=[])
        )
    )
    tool = build_solar_base_scenario_tool(service=service)

    with pytest.raises(ExternalServiceError):
        tool.invoke(
            {
                "known_user_data": {"monthly_consumption_kwh": 500},
                "location_context": "Sevilla, España",
                "user_goal": "Broad orientative solar estimate",
                "missing_fields": ["panel_power_w", "system_loss_pct", "tilt_deg"],
                "allow_orientative_scenario": True,
            }
        )


def test_service_retries_once_when_first_structured_response_is_empty() -> None:
    calls = {"count": 0}

    def _factory(_messages: Any) -> SolarBaseScenarioResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            return SolarBaseScenarioResponse.model_construct(candidates=[])
        return SolarBaseScenarioResponse(
            candidates=[
                SolarBaseScenarioCandidate(
                    id="scenario-1",
                    label="retry-success",
                    panel_power_w=450,
                    panel_width_m=1.13,
                    panel_length_m=1.76,
                    system_loss_pct=14,
                    solar_degradation_pct=0.5,
                    tilt_deg=20,
                    azimuth_deg=0,
                    field_sources=[
                        SolarScenarioFieldSource(
                            field="panel_power_w",
                            source_type=AssumptionSourceType.technical_reference,
                            source_name="Residential module reference",
                            confidence=AssumptionConfidence.medium,
                            rationale="Representative modern rooftop module.",
                        )
                    ],
                    confidence=AssumptionConfidence.medium,
                    limitations=["Orientative scenario only."],
                    requires_user_disclosure=True,
                )
            ]
        )

    service = SolarScenarioService(model=FakeChatModel(_factory))
    response = service.generate_candidates(
        SolarBaseScenarioRequest(
            known_user_data={"monthly_consumption_kwh": 500},
            location_context="Sevilla, España",
            user_goal="Broad orientative solar estimate",
            missing_fields=["panel_power_w", "system_loss_pct", "tilt_deg"],
            allow_orientative_scenario=True,
        )
    )

    assert calls["count"] == 2
    assert response.candidates[0].label == "retry-success"
