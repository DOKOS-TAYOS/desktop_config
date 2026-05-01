from __future__ import annotations

import json
import logging
from datetime import date, datetime
from functools import lru_cache
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.domain.models import LocationInput, WeatherContext, WeatherSample
from app.utils.config import (
    FORECAST_TEMPERATURE_C,
    THEORETICAL_DIRECT_RADIATION_WM2,
    WEATHER_TIMEOUT_SECONDS,
)
from app.utils.logging_utils import get_logger, log_event


logger = get_logger(__name__)


def _float_or_default(value, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_theoretical_weather_context(
    timezone: str, reason: str | None = None
) -> WeatherContext:
    return WeatherContext(
        mode="theoretical_clear_sky",
        timezone=timezone,
        reason=reason or "Usando cielo despejado teórico.",
    )


def _fetch_json(url: str, params: dict[str, str | int | float]) -> dict[str, Any]:
    query_string = urlencode(params)
    request_url = f"{url}?{query_string}"
    with urlopen(request_url, timeout=WEATHER_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


@lru_cache(maxsize=64)
def geocode_city(query: str) -> LocationInput | None:
    try:
        payload = _fetch_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": query, "count": 1, "language": "es", "format": "json"},
        )
    except URLError:
        log_event(logger, logging.WARNING, "geocode_failed", city_query=query)
        raise

    results = payload.get("results") or []
    if not results:
        log_event(logger, logging.WARNING, "geocode_no_results", city_query=query)
        return None

    best = results[0]
    label_parts = [best.get("name"), best.get("country_code")]
    label = ", ".join(part for part in label_parts if part)
    log_event(
        logger,
        logging.INFO,
        "geocode_resolved",
        city_query=query,
        label=label,
        timezone=best.get("timezone", "UTC"),
    )
    return LocationInput(
        mode="city",
        label=label,
        latitude=float(best["latitude"]),
        longitude=float(best["longitude"]),
        timezone=best.get("timezone", "UTC"),
        city_query=query,
    )


@lru_cache(maxsize=64)
def get_weather_context(
    latitude: float,
    longitude: float,
    timezone: str,
    analysis_date: date,
) -> WeatherContext:
    try:
        payload = _fetch_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,cloud_cover,direct_radiation",
                "timezone": timezone,
                "forecast_days": 16,
            },
        )
    except URLError as exc:
        reason = f"Open-Meteo no disponible: {exc}."
        log_event(
            logger,
            logging.WARNING,
            "weather_fallback",
            reason=reason,
            timezone=timezone,
        )
        return build_theoretical_weather_context(timezone, reason=reason)

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        reason = "Open-Meteo no devolvió datos horarios."
        log_event(
            logger,
            logging.WARNING,
            "weather_fallback",
            reason=reason,
            timezone=timezone,
        )
        return build_theoretical_weather_context(
            timezone, reason="Open-Meteo no devolvió datos horarios."
        )

    samples: dict[datetime, WeatherSample] = {}
    cloud_cover = hourly.get("cloud_cover") or []
    temperatures = hourly.get("temperature_2m") or []
    radiations = hourly.get("direct_radiation") or []

    for index, timestamp in enumerate(times):
        sample_time = datetime.fromisoformat(timestamp)
        samples[sample_time] = WeatherSample(
            cloud_cover_pct=_float_or_default(
                cloud_cover[index] if index < len(cloud_cover) else 0.0,
                0.0,
            ),
            temperature_c=_float_or_default(
                temperatures[index]
                if index < len(temperatures)
                else FORECAST_TEMPERATURE_C,
                FORECAST_TEMPERATURE_C,
            ),
            direct_radiation_wm2=_float_or_default(
                radiations[index]
                if index < len(radiations)
                else THEORETICAL_DIRECT_RADIATION_WM2,
                THEORETICAL_DIRECT_RADIATION_WM2,
            ),
        )

    if not any(sample_time.date() == analysis_date for sample_time in samples):
        reason = "La fecha queda fuera del pronóstico disponible."
        log_event(
            logger,
            logging.WARNING,
            "weather_fallback",
            reason=reason,
            analysis_date=analysis_date.isoformat(),
            timezone=timezone,
        )
        return build_theoretical_weather_context(
            timezone,
            reason="La fecha queda fuera del pronóstico disponible.",
        )

    log_event(
        logger,
        logging.INFO,
        "weather_forecast_loaded",
        analysis_date=analysis_date.isoformat(),
        sample_count=len(samples),
        timezone=timezone,
    )
    return WeatherContext(mode="forecast", timezone=timezone, hourly_samples=samples)


def weather_sample_for_time(
    context: WeatherContext, when_local: datetime
) -> WeatherSample:
    if context.mode != "forecast" or not context.hourly_samples:
        return WeatherSample(
            cloud_cover_pct=0.0,
            temperature_c=FORECAST_TEMPERATURE_C,
            direct_radiation_wm2=THEORETICAL_DIRECT_RADIATION_WM2,
        )
    reference = when_local.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    if reference in context.hourly_samples:
        return context.hourly_samples[reference]
    nearest_time = min(
        context.hourly_samples,
        key=lambda sample_time: abs((sample_time - reference).total_seconds()),
    )
    return context.hourly_samples[nearest_time]
