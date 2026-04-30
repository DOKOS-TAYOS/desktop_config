from __future__ import annotations

from datetime import datetime

from app.domain.models import WeatherContext, WeatherSample
from app.services.analysis import analyze_scenario
from app.services.analysis import analyze_scenario_at_time
from app.domain.models import MonitorConfig
from app.utils.geometry import (
    build_monitor_geometry,
    classify_screen_zone,
    intersect_ray_with_monitor,
)


def test_night_slot_has_zero_glare_and_heat(base_request):
    result = analyze_scenario_at_time(base_request, datetime(2026, 7, 15, 1, 0))

    assert result.glare_score == 0
    assert result.heat_score == 0
    assert result.direct_sun_on_desk is False
    assert result.direct_sun_on_monitor is False


def test_west_window_afternoon_creates_high_glare(base_request):
    result = analyze_scenario_at_time(base_request, datetime(2026, 7, 15, 18, 0))

    assert result.glare_score >= 70
    assert result.solar_enters_window is True
    assert "pantalla" in result.explanation or "habitación" in result.explanation


def test_north_window_stays_low_risk_without_direct_sun(base_request):
    base_request.window.orientation_deg = 0

    result = analyze_scenario_at_time(base_request, datetime(2026, 7, 15, 13, 0))

    assert result.glare_score <= 15
    assert result.heat_score <= 15
    assert result.direct_sun_on_desk is False


def test_screen_zone_detection_returns_center_media_for_a_clean_hit():
    geometry = build_monitor_geometry(
        MonitorConfig(
            x_m=1.0,
            y_m=1.0,
            center_height_m=1.2,
            diagonal_in=27,
            orientation_deg=270,
            tilt_deg=0.0,
        )
    )

    hit, _point, local_coords = intersect_ray_with_monitor(
        ray_origin=(0.0, 1.0, 1.2),
        ray_direction=(1.0, 0.0, 0.0),
        monitor_geometry=geometry,
    )

    assert hit is True
    assert local_coords is not None
    assert classify_screen_zone(local_coords, geometry) == "centro-media"


def test_analysis_builds_a_practical_diagnosis_for_afternoon_glare(base_request):
    result = analyze_scenario(base_request)

    assert result.diagnosis.dominant_risk == "glare"
    assert result.diagnosis.worst_window is not None
    assert "tarde" in result.diagnosis.worst_window.label.lower()
    assert "reflejo" in result.diagnosis.primary_message.lower()
    assert result.diagnosis.high_glare_windows


def test_zero_direct_radiation_reduces_heat_risk_for_same_solar_geometry(base_request):
    when_local = datetime(2026, 7, 15, 19, 0)
    clear_context = WeatherContext(mode="forecast", timezone="Europe/Madrid")
    clear_context.hourly_samples = {
        datetime(2026, 7, 15, 19, 0): WeatherSample(
            cloud_cover_pct=0.0,
            temperature_c=30.0,
            direct_radiation_wm2=800.0,
        )
    }
    no_radiation_context = WeatherContext(mode="forecast", timezone="Europe/Madrid")
    no_radiation_context.hourly_samples = {
        datetime(2026, 7, 15, 19, 0): WeatherSample(
            cloud_cover_pct=0.0,
            temperature_c=30.0,
            direct_radiation_wm2=0.0,
        )
    }

    clear_result = analyze_scenario_at_time(base_request, when_local, clear_context)
    no_radiation_result = analyze_scenario_at_time(
        base_request, when_local, no_radiation_context
    )

    assert clear_result.direct_sun_on_desk is True
    assert no_radiation_result.direct_sun_on_desk is True
    assert no_radiation_result.heat_score < clear_result.heat_score / 2
