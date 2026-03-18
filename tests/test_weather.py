from __future__ import annotations

from datetime import date

import requests

from app.services.weather import get_weather_context


def test_weather_context_falls_back_to_theoretical_on_request_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr("app.services.weather.requests.get", raise_error)

    context = get_weather_context(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        analysis_date=date(2026, 7, 15),
    )

    assert context.mode == "theoretical_clear_sky"
    assert context.reason is not None


def test_weather_context_handles_null_values_without_crashing(monkeypatch):
    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-03-18T12:00"],
                    "cloud_cover": [None],
                    "temperature_2m": [None],
                    "direct_radiation": [None],
                }
            }

    monkeypatch.setattr("app.services.weather.requests.get", lambda *args, **kwargs: DummyResponse())
    get_weather_context.cache_clear()

    context = get_weather_context(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        analysis_date=date(2026, 3, 18),
    )

    assert context.mode == "forecast"
    only_sample = next(iter(context.hourly_samples.values()))
    assert only_sample.cloud_cover_pct == 0.0
    assert only_sample.temperature_c == 22.0
