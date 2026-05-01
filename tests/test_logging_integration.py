from __future__ import annotations

import logging
from datetime import date
from types import SimpleNamespace
from urllib.error import URLError

from app.services.analysis import analyze_scenario
from app.services.recommendations import recommend_variant


def test_weather_fallback_logs_warning(monkeypatch, caplog):
    from app.services import weather

    weather.get_weather_context.cache_clear()

    def fail_request(*args, **kwargs):
        raise URLError("network down")

    monkeypatch.setattr(weather, "urlopen", fail_request)
    caplog.set_level(logging.WARNING, logger="app.services.weather")

    context = weather.get_weather_context(
        40.4168, -3.7038, "Europe/Madrid", date(2026, 7, 15)
    )

    assert context.mode == "theoretical_clear_sky"
    assert any("event=weather_fallback" in record.message for record in caplog.records)


def test_analysis_logs_start_and_end(base_request, caplog):
    caplog.set_level(logging.INFO, logger="app.services.analysis")

    analyze_scenario(base_request)

    messages = [
        record.message
        for record in caplog.records
        if record.name == "app.services.analysis"
    ]
    assert any("event=analysis_started" in message for message in messages)
    assert any("event=analysis_completed" in message for message in messages)


def test_recommendation_logs_summary(base_request, caplog):
    baseline = analyze_scenario(base_request)
    caplog.set_level(logging.INFO, logger="app.services.recommendations")

    recommend_variant(base_request, baseline)

    messages = [
        record.message
        for record in caplog.records
        if record.name == "app.services.recommendations"
    ]
    assert any("event=recommendation_started" in message for message in messages)
    assert any("event=recommendation_completed" in message for message in messages)


def test_apply_pending_session_patch_logs_info(monkeypatch, caplog):
    from app.ui import forms

    fake_streamlit = SimpleNamespace(
        session_state={forms.PENDING_SESSION_PATCH_KEY: {"desk_x_m": 1.85}}
    )
    monkeypatch.setattr(forms, "st", fake_streamlit)
    caplog.set_level(logging.INFO, logger="app.ui.forms")

    forms.apply_pending_session_patch()

    assert fake_streamlit.session_state["desk_x_m"] == 1.85
    assert any(
        "event=session_patch_applied" in record.message for record in caplog.records
    )
