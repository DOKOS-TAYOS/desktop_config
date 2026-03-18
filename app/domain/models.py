from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


LocationMode = Literal["city", "manual"]
WeatherMode = Literal["forecast", "theoretical_clear_sky"]


@dataclass(slots=True)
class LocationInput:
    mode: LocationMode
    label: str
    latitude: float
    longitude: float
    timezone: str
    city_query: str | None = None


@dataclass(slots=True)
class RoomConfig:
    width_m: float
    depth_m: float
    ceiling_height_m: float = 2.6


@dataclass(slots=True)
class WindowConfig:
    orientation_deg: float
    width_m: float
    height_m: float = 1.2
    sill_height_m: float = 0.9
    center_ratio: float = 0.5


@dataclass(slots=True)
class DeskConfig:
    x_m: float
    y_m: float
    width_m: float = 1.4
    depth_m: float = 0.7
    height_m: float = 0.74
    orientation_deg: float = 180.0


@dataclass(slots=True)
class MonitorConfig:
    x_m: float
    y_m: float
    center_height_m: float
    diagonal_in: float
    orientation_deg: float
    tilt_deg: float = -5.0
    aspect_ratio_width: int = 16
    aspect_ratio_height: int = 9


@dataclass(slots=True)
class ErgonomicProfile:
    eye_height_m: float
    viewing_distance_m: float = 0.65
    preset_name: str = "estandar"


@dataclass(slots=True)
class AnalysisRequest:
    location: LocationInput
    analysis_date: date
    room: RoomConfig
    window: WindowConfig
    desk: DeskConfig
    monitor: MonitorConfig
    ergonomic: ErgonomicProfile
    time_step_minutes: int = 15
    include_seasonal_summary: bool = True


@dataclass(frozen=True, slots=True)
class WeatherSample:
    cloud_cover_pct: float
    temperature_c: float
    direct_radiation_wm2: float | None = None


@dataclass(slots=True)
class WeatherContext:
    mode: WeatherMode
    timezone: str
    hourly_samples: dict[datetime, WeatherSample] = field(default_factory=dict)
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SolarPosition:
    when_local: datetime
    azimuth_deg: float
    elevation_deg: float


@dataclass(frozen=True, slots=True)
class Recommendation:
    title: str
    message: str
    delta_score: float


@dataclass(frozen=True, slots=True)
class TimeSlotResult:
    when_local: datetime
    solar_azimuth_deg: float
    solar_elevation_deg: float
    glare_score: float
    heat_score: float
    ergonomic_score: float
    comfort_score: float
    solar_enters_window: bool
    direct_sun_on_desk: bool
    direct_sun_on_monitor: bool
    screen_zone_label: str | None
    explanation: str


@dataclass(frozen=True, slots=True)
class SeasonalSummary:
    season: str
    morning_comfort: float
    midday_comfort: float
    afternoon_comfort: float


@dataclass(slots=True)
class ScenarioResult:
    request: AnalysisRequest
    time_slots: list[TimeSlotResult]
    glare_score: float
    heat_score: float
    ergonomic_score: float
    comfort_score: float
    alerts: list[str]
    recommendations: list[Recommendation]
    weather_context: WeatherContext
    seasonal_summary: list[SeasonalSummary] = field(default_factory=list)
