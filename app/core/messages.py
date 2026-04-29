"""Central registry for critical user-facing messages.

This registry stays intentionally small. It is not a full i18n system.
"""

from __future__ import annotations

from enum import StrEnum


class MessageKey(StrEnum):
    TECHNICAL_ESTIMATE_DISCLAIMER = "technical_estimate_disclaimer"
    SUBSIDY_LEGAL_DISCLAIMER = "subsidy_legal_disclaimer"
    ECONOMIC_COMPENSATION_DISCLAIMER = "economic_compensation_disclaimer"
    REAL_SALE_REVENUE_DISCLAIMER = "real_sale_revenue_disclaimer"
    RDTOOLS_DATA_QUALITY_DISCLAIMER = "rdtools_data_quality_disclaimer"
    PRIVACY_WARNING = "privacy_warning"
    MISSING_INFORMATION_RECOVERY = "missing_information_recovery"
    AGENT_FAILURE_MESSAGE = "agent_failure_message"


CRITICAL_MESSAGES: dict[str, dict[MessageKey, str]] = {
    "es": {
        MessageKey.TECHNICAL_ESTIMATE_DISCLAIMER: (
            "Esta estimación es orientativa y no sustituye un estudio técnico profesional."
        ),
        MessageKey.SUBSIDY_LEGAL_DISCLAIMER: (
            "La detección de ayudas es una preevaluación. La elegibilidad real depende de la "
            "convocatoria vigente, del presupuesto disponible, de la documentación y de la "
            "normativa aplicable."
        ),
        MessageKey.ECONOMIC_COMPENSATION_DISCLAIMER: (
            "La compensación de excedentes en factura no es lo mismo que vender energía "
            "como productor."
        ),
        MessageKey.REAL_SALE_REVENUE_DISCLAIMER: (
            "La venta real de energía puede requerir trámites, representación, costes e impuestos."
        ),
        MessageKey.RDTOOLS_DATA_QUALITY_DISCLAIMER: (
            "El análisis con RdTools depende de la calidad, la frecuencia y la cobertura de "
            "los datos históricos."
        ),
        MessageKey.PRIVACY_WARNING: (
            "No compartas datos personales sensibles, claves API ni información fiscal privada."
        ),
        MessageKey.MISSING_INFORMATION_RECOVERY: (
            "Puedo continuar con datos parciales, pero declararé qué falta y no inventaré valores."
        ),
        MessageKey.AGENT_FAILURE_MESSAGE: (
            "No he podido completar la solicitud, pero la traza conserva el punto donde falló."
        ),
    },
    "en": {
        MessageKey.TECHNICAL_ESTIMATE_DISCLAIMER: (
            "This estimate is indicative and does not replace a professional technical assessment."
        ),
        MessageKey.SUBSIDY_LEGAL_DISCLAIMER: (
            "Subsidy detection is a pre-assessment. Real eligibility depends on the active call, "
            "available budget, required documentation, and applicable regulation."
        ),
        MessageKey.ECONOMIC_COMPENSATION_DISCLAIMER: (
            "Bill compensation for surplus energy is not the same as selling electricity as a producer."
        ),
        MessageKey.REAL_SALE_REVENUE_DISCLAIMER: (
            "Actual electricity sale may require procedures, representation, costs, and taxes."
        ),
        MessageKey.RDTOOLS_DATA_QUALITY_DISCLAIMER: (
            "RdTools analysis depends on the quality, frequency, and coverage of historical data."
        ),
        MessageKey.PRIVACY_WARNING: (
            "Do not share sensitive personal data, API keys, or private tax information."
        ),
        MessageKey.MISSING_INFORMATION_RECOVERY: (
            "I can continue with partial data, but I will declare what is missing and will not invent values."
        ),
        MessageKey.AGENT_FAILURE_MESSAGE: (
            "I could not complete the request, but the trace preserves where it failed."
        ),
    },
}


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return "es"
    lowered = locale.lower()
    if lowered.startswith("en"):
        return "en"
    return "es"


def get_message(key: MessageKey, locale: str | None = "es") -> str:
    return CRITICAL_MESSAGES[normalize_locale(locale)][key]


__all__ = ["CRITICAL_MESSAGES", "MessageKey", "get_message", "normalize_locale"]
