from __future__ import annotations

import logging


def test_build_event_message_contains_event_and_fields():
    from app.utils.logging_utils import build_event_message

    message = build_event_message(
        "analysis_completed",
        comfort=71.2,
        location_label="Madrid home office",
    )

    assert "event=analysis_completed" in message
    assert "comfort=71.2" in message
    assert 'location_label="Madrid home office"' in message


def test_setup_logging_uses_env_level(monkeypatch):
    from app.utils.logging_utils import setup_logging

    monkeypatch.setenv("SUNSETUP_LOG_LEVEL", "DEBUG")

    setup_logging(force=True)

    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG
