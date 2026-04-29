from __future__ import annotations

from app.core.messages import CRITICAL_MESSAGES, MessageKey, get_message, normalize_locale


def test_all_message_keys_exist_in_spanish_and_english() -> None:
    expected = set(MessageKey)
    assert set(CRITICAL_MESSAGES["es"]) == expected
    assert set(CRITICAL_MESSAGES["en"]) == expected


def test_all_messages_are_non_empty() -> None:
    for locale_messages in CRITICAL_MESSAGES.values():
        for message in locale_messages.values():
            assert message.strip()


def test_get_message_falls_back_to_spanish_for_unknown_locale() -> None:
    assert get_message(MessageKey.AGENT_FAILURE_MESSAGE, "fr-FR") == CRITICAL_MESSAGES["es"][
        MessageKey.AGENT_FAILURE_MESSAGE
    ]


def test_normalize_locale_maps_english_and_defaults_to_spanish() -> None:
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("es-ES") == "es"
    assert normalize_locale(None) == "es"
