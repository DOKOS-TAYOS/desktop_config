from __future__ import annotations

import logging
import math
from datetime import datetime
from time import perf_counter

from app.domain.models import (
    AnalysisRequest,
    Recommendation,
    ScenarioResult,
    SeasonalSummary,
    TimeSlotResult,
    WeatherContext,
)
from app.domain.validation import validate_request
from app.services.solar import generate_day_times, get_solar_position
from app.services.weather import (
    build_theoretical_weather_context,
    get_weather_context,
    weather_sample_for_time,
)
from app.utils.config import DEFAULT_WEIGHTS, representative_date_for_season
from app.utils.geometry import (
    angle_between3,
    build_monitor_geometry,
    classify_screen_zone,
    compass_to_unit,
    desk_rectangle,
    distance_point_to_ray,
    dot3,
    intersect_ray_with_monitor,
    normalize3,
    ray_intersects_horizontal_rectangle,
    scale3,
    smallest_angle_deg,
    subtract3,
    window_center_point,
)
from app.utils.logging_utils import get_logger, log_event


logger = get_logger(__name__)


def _sun_vector_from_ground(azimuth_deg: float, elevation_deg: float) -> tuple[float, float, float]:
    elevation_rad = math.radians(elevation_deg)
    azimuth_vector = compass_to_unit(azimuth_deg)
    horizontal_scale = math.cos(elevation_rad)
    return (
        azimuth_vector[0] * horizontal_scale,
        azimuth_vector[1] * horizontal_scale,
        math.sin(elevation_rad),
    )


def _sun_enters_window(request: AnalysisRequest, azimuth_deg: float, elevation_deg: float) -> bool:
    if elevation_deg <= 0:
        return False
    return smallest_angle_deg(azimuth_deg, request.window.orientation_deg) <= 90


def _ergonomic_risk(request: AnalysisRequest) -> float:
    inward_light_direction = (request.window.orientation_deg + 180) % 360
    side_lighting_delta = smallest_angle_deg(request.monitor.orientation_deg, inward_light_direction)
    side_lighting_risk = abs(side_lighting_delta - 90) / 90 * 45
    monitor_alignment_risk = (
        smallest_angle_deg(request.monitor.orientation_deg, request.desk.orientation_deg) / 90 * 25
    )
    monitor_geometry = build_monitor_geometry(request.monitor)
    monitor_top_height = request.monitor.center_height_m + monitor_geometry.height_m / 2
    preferred_eye_height = monitor_top_height - 0.05
    eye_height_risk = min(abs(request.ergonomic.eye_height_m - preferred_eye_height) / 0.25, 1.0) * 20
    lateral_offset = abs(request.monitor.x_m - request.desk.x_m) + abs(request.monitor.y_m - request.desk.y_m)
    offset_risk = min(lateral_offset / 0.35, 1.0) * 10
    return round(
        min(100.0, side_lighting_risk + monitor_alignment_risk + eye_height_risk + offset_risk),
        1,
    )


def _reflection_alignment_deg(
    incident: tuple[float, float, float],
    hit_point: tuple[float, float, float],
    request: AnalysisRequest,
    monitor_geometry,
) -> float:
    eye_position = _eye_position(request, monitor_geometry)
    reflected = subtract3(
        incident,
        scale3(monitor_geometry.normal, 2 * dot3(incident, monitor_geometry.normal)),
    )
    eye_vector = subtract3(eye_position, hit_point)
    return angle_between3(normalize3(reflected), normalize3(eye_vector))


def _eye_position(request: AnalysisRequest, monitor_geometry) -> tuple[float, float, float]:
    return (
        monitor_geometry.center[0] + monitor_geometry.normal[0] * request.ergonomic.viewing_distance_m,
        monitor_geometry.center[1] + monitor_geometry.normal[1] * request.ergonomic.viewing_distance_m,
        request.ergonomic.eye_height_m,
    )


def _build_explanation(
    solar_enters_window: bool,
    direct_sun_on_desk: bool,
    direct_sun_on_monitor: bool,
    screen_zone_label: str | None,
) -> str:
    if not solar_enters_window:
        return "El sol no entra por la ventana en esta franja."
    if direct_sun_on_monitor and screen_zone_label:
        return f"Hay incidencia directa en la pantalla, con riesgo visible en la zona {screen_zone_label}."
    if direct_sun_on_desk:
        return "Hay sol directo sobre la mesa o la zona de trabajo."
    return "La luz entra en la habitación, pero sin impacto directo crítico sobre la pantalla."


def analyze_scenario_at_time(
    request: AnalysisRequest,
    when_local: datetime,
    weather_context: WeatherContext | None = None,
) -> TimeSlotResult:
    validate_request(request)
    solar = get_solar_position(
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        timezone=request.location.timezone,
        when_local=when_local,
    )
    ergonomic_score = _ergonomic_risk(request)
    weather_context = weather_context or build_theoretical_weather_context(request.location.timezone)
    if solar.elevation_deg <= 0:
        comfort = round(max(0.0, 100 - DEFAULT_WEIGHTS.ergonomics * ergonomic_score), 1)
        return TimeSlotResult(
            when_local=solar.when_local,
            solar_azimuth_deg=solar.azimuth_deg,
            solar_elevation_deg=solar.elevation_deg,
            glare_score=0.0,
            heat_score=0.0,
            ergonomic_score=ergonomic_score,
            comfort_score=comfort,
            solar_enters_window=False,
            direct_sun_on_desk=False,
            direct_sun_on_monitor=False,
            screen_zone_label=None,
            explanation="Es de noche o el sol está por debajo del horizonte.",
        )

    solar_enters = _sun_enters_window(request, solar.azimuth_deg, solar.elevation_deg)
    if not solar_enters:
        comfort = round(max(0.0, 100 - DEFAULT_WEIGHTS.ergonomics * ergonomic_score), 1)
        return TimeSlotResult(
            when_local=solar.when_local,
            solar_azimuth_deg=solar.azimuth_deg,
            solar_elevation_deg=solar.elevation_deg,
            glare_score=0.0,
            heat_score=0.0,
            ergonomic_score=ergonomic_score,
            comfort_score=comfort,
            solar_enters_window=False,
            direct_sun_on_desk=False,
            direct_sun_on_monitor=False,
            screen_zone_label=None,
            explanation="El sol está fuera del cono de entrada de la ventana.",
        )

    sun_vector = _sun_vector_from_ground(solar.azimuth_deg, solar.elevation_deg)
    incoming_ray = normalize3((-sun_vector[0], -sun_vector[1], -sun_vector[2]))
    weather_sample = weather_sample_for_time(weather_context, solar.when_local)
    window_origin = window_center_point(request.room, request.window)
    desk_hit, _desk_hit_point = ray_intersects_horizontal_rectangle(
        window_origin,
        incoming_ray,
        request.desk.height_m,
        desk_rectangle(request.desk),
    )
    monitor_geometry = build_monitor_geometry(request.monitor)
    monitor_hit, monitor_hit_point, local_coords = intersect_ray_with_monitor(
        window_origin,
        incoming_ray,
        monitor_geometry,
    )
    screen_zone_label = (
        classify_screen_zone(local_coords, monitor_geometry)
        if monitor_hit and local_coords is not None
        else None
    )

    reflection_alignment = 90.0
    front_alignment = 180.0
    if monitor_hit and monitor_hit_point is not None:
        front_alignment = angle_between3(incoming_ray, scale3(monitor_geometry.normal, -1))
        reflection_alignment = _reflection_alignment_deg(
            incoming_ray, monitor_hit_point, request, monitor_geometry
        )

    distance_to_monitor = distance_point_to_ray(
        monitor_geometry.center,
        window_origin,
        incoming_ray,
    )
    monitor_near_miss = distance_to_monitor <= 0.25
    eye_position = _eye_position(request, monitor_geometry)
    eye_distance = distance_point_to_ray(eye_position, window_origin, incoming_ray)
    backlighting_alignment = angle_between3(incoming_ray, scale3(monitor_geometry.normal, -1))

    if monitor_hit:
        reflection_factor = max(0.0, 1 - reflection_alignment / 25)
        front_factor = max(0.0, 1 - front_alignment / 75)
        glare_score = min(100.0, 65 + 25 * reflection_factor + 10 * front_factor)
    elif backlighting_alignment <= 40 and eye_distance <= 0.55:
        alignment_factor = max(0.0, 1 - backlighting_alignment / 40)
        eye_factor = max(0.0, 1 - eye_distance / 0.55)
        glare_score = min(100.0, 70 + 15 * alignment_factor + 15 * eye_factor)
    elif monitor_near_miss:
        glare_score = 35.0 + max(0.0, 20 * (1 - distance_to_monitor / 0.25))
    elif desk_hit:
        glare_score = 20.0
    else:
        glare_score = 8.0

    cloud_factor = 1 - min(max(weather_sample.cloud_cover_pct, 0.0), 100.0) / 100 * 0.6
    temperature_factor = min(max((weather_sample.temperature_c - 18) / 14, 0.0), 1.0)
    direct_radiation_factor = min(max((weather_sample.direct_radiation_wm2 or 0.0) / 850, 0.35), 1.0)
    solar_strength = max(math.sin(math.radians(solar.elevation_deg)), 0.0)
    if desk_hit:
        heat_score = min(
            100.0,
            (40 + 30 * solar_strength + 15 * temperature_factor) * cloud_factor * direct_radiation_factor,
        )
    elif monitor_hit:
        heat_score = min(
            100.0,
            (25 + 20 * solar_strength + 10 * temperature_factor) * cloud_factor * direct_radiation_factor,
        )
    else:
        heat_score = 10.0 * cloud_factor * solar_strength

    comfort_score = round(
        max(
            0.0,
            100
            - (
                DEFAULT_WEIGHTS.glare * glare_score
                + DEFAULT_WEIGHTS.heat * heat_score
                + DEFAULT_WEIGHTS.ergonomics * ergonomic_score
            ),
        ),
        1,
    )
    return TimeSlotResult(
        when_local=solar.when_local,
        solar_azimuth_deg=solar.azimuth_deg,
        solar_elevation_deg=solar.elevation_deg,
        glare_score=round(glare_score, 1),
        heat_score=round(heat_score, 1),
        ergonomic_score=ergonomic_score,
        comfort_score=comfort_score,
        solar_enters_window=True,
        direct_sun_on_desk=desk_hit,
        direct_sun_on_monitor=monitor_hit,
        screen_zone_label=screen_zone_label,
        explanation=_build_explanation(solar_enters, desk_hit, monitor_hit, screen_zone_label),
    )


def _aggregate_risk(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(0.6 * max(values) + 0.4 * (sum(values) / len(values)), 1)


def _periods_above_threshold(
    slots: list[TimeSlotResult], attribute: str, threshold: float
) -> list[tuple[str, str]]:
    periods: list[tuple[str, str]] = []
    start = None
    for slot in slots:
        value = getattr(slot, attribute)
        if value >= threshold and start is None:
            start = slot.when_local
        elif value < threshold and start is not None:
            periods.append((start.strftime("%H:%M"), slot.when_local.strftime("%H:%M")))
            start = None
    if start is not None and slots:
        periods.append((start.strftime("%H:%M"), slots[-1].when_local.strftime("%H:%M")))
    return periods


def _build_alerts(slots: list[TimeSlotResult], weather_context: WeatherContext) -> list[str]:
    alerts: list[str] = []
    glare_periods = _periods_above_threshold(slots, "glare_score", 60)
    heat_periods = _periods_above_threshold(slots, "heat_score", 55)
    if glare_periods:
        start, end = glare_periods[0]
        alerts.append(f"Riesgo alto de reflejo entre {start} y {end}.")
    if heat_periods:
        start, end = heat_periods[0]
        alerts.append(f"Sol directo o calor fuerte entre {start} y {end}.")
    if weather_context.mode == "theoretical_clear_sky" and weather_context.reason:
        alerts.append(f"Clima en modo teórico: {weather_context.reason}")
    return alerts


def _seasonal_bucket_mean(slots: list[TimeSlotResult], start_hour: int, end_hour: int) -> float:
    bucket = [slot.comfort_score for slot in slots if start_hour <= slot.when_local.hour < end_hour]
    if not bucket:
        return 0.0
    return round(sum(bucket) / len(bucket), 1)


def build_seasonal_summary(request: AnalysisRequest) -> list[SeasonalSummary]:
    summary: list[SeasonalSummary] = []
    for season in ("invierno", "primavera", "verano", "otono"):
        seasonal_request = AnalysisRequest(
            location=request.location,
            analysis_date=representative_date_for_season(request.analysis_date.year, season),
            room=request.room,
            window=request.window,
            desk=request.desk,
            monitor=request.monitor,
            ergonomic=request.ergonomic,
            time_step_minutes=request.time_step_minutes,
            include_seasonal_summary=False,
        )
        slots = [
            analyze_scenario_at_time(
                seasonal_request,
                when_local=slot_time,
                weather_context=build_theoretical_weather_context(request.location.timezone),
            )
            for slot_time in generate_day_times(
                seasonal_request.analysis_date,
                seasonal_request.location.timezone,
                seasonal_request.time_step_minutes,
            )
        ]
        summary.append(
            SeasonalSummary(
                season=season,
                morning_comfort=_seasonal_bucket_mean(slots, 7, 11),
                midday_comfort=_seasonal_bucket_mean(slots, 11, 15),
                afternoon_comfort=_seasonal_bucket_mean(slots, 15, 20),
            )
        )
    return summary


def analyze_scenario(
    request: AnalysisRequest,
    weather_context: WeatherContext | None = None,
    *,
    include_live_weather: bool = False,
) -> ScenarioResult:
    started_at = perf_counter()
    log_event(
        logger,
        logging.INFO,
        "analysis_started",
        analysis_date=request.analysis_date.isoformat(),
        include_live_weather=include_live_weather,
        location_label=request.location.label,
        time_step_minutes=request.time_step_minutes,
    )
    validate_request(request)
    if weather_context is None:
        weather_context = (
            get_weather_context(
                request.location.latitude,
                request.location.longitude,
                request.location.timezone,
                request.analysis_date,
            )
            if include_live_weather
            else build_theoretical_weather_context(request.location.timezone)
        )
    if include_live_weather and weather_context.mode != "forecast":
        log_event(
            logger,
            logging.WARNING,
            "analysis_weather_degraded",
            analysis_date=request.analysis_date.isoformat(),
            location_label=request.location.label,
            reason=weather_context.reason,
        )

    slots = [
        analyze_scenario_at_time(request, slot_time, weather_context)
        for slot_time in generate_day_times(
            request.analysis_date, request.location.timezone, request.time_step_minutes
        )
    ]
    glare_score = _aggregate_risk([slot.glare_score for slot in slots])
    heat_score = _aggregate_risk([slot.heat_score for slot in slots])
    ergonomic_score = slots[0].ergonomic_score if slots else _ergonomic_risk(request)
    comfort_score = round(
        max(
            0.0,
            100
            - (
                DEFAULT_WEIGHTS.glare * glare_score
                + DEFAULT_WEIGHTS.heat * heat_score
                + DEFAULT_WEIGHTS.ergonomics * ergonomic_score
            ),
        ),
        1,
    )
    result = ScenarioResult(
        request=request,
        time_slots=slots,
        glare_score=glare_score,
        heat_score=heat_score,
        ergonomic_score=ergonomic_score,
        comfort_score=comfort_score,
        alerts=_build_alerts(slots, weather_context),
        recommendations=[
            Recommendation(
                title="Base actual",
                message="Esta es la evaluación de tu configuración actual.",
                delta_score=0.0,
            )
        ],
        weather_context=weather_context,
        seasonal_summary=build_seasonal_summary(request) if request.include_seasonal_summary else [],
    )
    log_event(
        logger,
        logging.INFO,
        "analysis_completed",
        comfort_score=result.comfort_score,
        duration_ms=round((perf_counter() - started_at) * 1000, 1),
        glare_score=result.glare_score,
        heat_score=result.heat_score,
        location_label=request.location.label,
        weather_mode=result.weather_context.mode,
    )
    return result
