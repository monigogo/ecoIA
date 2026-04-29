from __future__ import annotations

from app.core.messages import MessageKey, get_message
from app.services.conversation_response_builder import resolve_response_payload


def _structured_response(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "summary": "Resumen",
        "key_points": [],
        "assumptions_used": [],
        "sources": [],
        "warnings": [],
        "natural_trace": [],
        "next_steps": [],
    }
    payload.update(overrides)
    return payload


def test_response_builder_adds_subsidy_disclaimer_from_structured_result() -> None:
    _, _, warnings = resolve_response_payload(
        {"structured_response": _structured_response(subsidy_candidates=[{"program": "ayuda"}])},
        include_trace=False,
        locale="es-ES",
    )

    assert warnings == [get_message(MessageKey.SUBSIDY_LEGAL_DISCLAIMER, "es-ES")]


def test_response_builder_adds_economic_compensation_disclaimer_from_structured_result() -> None:
    _, _, warnings = resolve_response_payload(
        {"structured_response": _structured_response(export_compensation={"amount_eur": 42.0})},
        include_trace=False,
        locale="es-ES",
    )

    assert warnings == [get_message(MessageKey.ECONOMIC_COMPENSATION_DISCLAIMER, "es-ES")]


def test_response_builder_adds_real_sale_disclaimer_from_structured_result() -> None:
    _, _, warnings = resolve_response_payload(
        {"structured_response": _structured_response(export_sale_revenue={"gross_eur": 65.0})},
        include_trace=False,
        locale="es-ES",
    )

    assert warnings == [get_message(MessageKey.REAL_SALE_REVENUE_DISCLAIMER, "es-ES")]


def test_response_builder_adds_rdtools_disclaimer_from_structured_result() -> None:
    _, _, warnings = resolve_response_payload(
        {"structured_response": _structured_response(rdtools_analysis={"dataset_path": "data.csv"})},
        include_trace=False,
        locale="es-ES",
    )

    assert warnings == [get_message(MessageKey.RDTOOLS_DATA_QUALITY_DISCLAIMER, "es-ES")]


def test_response_builder_deduplicates_warnings() -> None:
    disclaimer = get_message(MessageKey.SUBSIDY_LEGAL_DISCLAIMER, "es-ES")
    _, _, warnings = resolve_response_payload(
        {
            "structured_response": _structured_response(
                warnings=["base", disclaimer, "base"],
                subsidy_candidates=[{"program": "ayuda"}],
            )
        },
        include_trace=False,
        locale="es-ES",
    )

    assert warnings == ["base", disclaimer]


def test_response_builder_defaults_to_spanish_messages() -> None:
    _, _, warnings = resolve_response_payload(
        {"structured_response": _structured_response(subsidy_candidates=[{"program": "ayuda"}])},
        include_trace=False,
        locale=None,
    )

    assert warnings == [get_message(MessageKey.SUBSIDY_LEGAL_DISCLAIMER, "es")]
