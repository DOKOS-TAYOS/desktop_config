from __future__ import annotations

import json
from io import BytesIO
from datetime import date
from urllib.error import URLError

from app.services.weather import geocode_city, get_weather_context
from app.utils.config import MAX_WEATHER_RESPONSE_BYTES


def test_weather_context_falls_back_to_theoretical_on_request_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise URLError("boom")

    monkeypatch.setattr("app.services.weather.urlopen", raise_error)
    get_weather_context.cache_clear()

    context = get_weather_context(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        analysis_date=date(2026, 7, 15),
    )

    assert context.mode == "theoretical_clear_sky"
    assert context.reason is not None


def test_weather_context_handles_null_values_without_crashing(monkeypatch):
    payload = {
        "hourly": {
            "time": ["2026-03-18T12:00"],
            "cloud_cover": [None],
            "temperature_2m": [None],
            "direct_radiation": [None],
        }
    }

    monkeypatch.setattr(
        "app.services.weather.urlopen",
        lambda *args, **kwargs: BytesIO(json.dumps(payload).encode("utf-8")),
    )
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


def test_weather_context_falls_back_when_response_is_too_large(monkeypatch):
    payload = b"{" + (b" " * MAX_WEATHER_RESPONSE_BYTES) + b"}"

    monkeypatch.setattr(
        "app.services.weather.urlopen",
        lambda *args, **kwargs: BytesIO(payload),
    )
    get_weather_context.cache_clear()

    context = get_weather_context(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        analysis_date=date(2026, 3, 18),
    )

    assert context.mode == "theoretical_clear_sky"
    assert context.reason is not None


def test_geocode_city_skips_empty_queries(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("empty query should not call the geocoding service")

    monkeypatch.setattr("app.services.weather.urlopen", fail_if_called)
    geocode_city.cache_clear()

    assert geocode_city("   ") is None
