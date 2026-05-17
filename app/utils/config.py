from __future__ import annotations

from dataclasses import dataclass
from datetime import date


APP_TITLE = "SunSetup Planner"
TIME_STEP_MINUTES = 15
WEATHER_TIMEOUT_SECONDS = 10
MAX_WEATHER_RESPONSE_BYTES = 1_000_000
MAX_GEOCODE_QUERY_LENGTH = 80
FORECAST_TEMPERATURE_C = 22.0
THEORETICAL_DIRECT_RADIATION_WM2 = 800.0
SEASON_REPRESENTATIVE_DATES = {
    "invierno": (12, 21),
    "primavera": (3, 20),
    "verano": (6, 21),
    "otono": (9, 22),
}


@dataclass(frozen=True, slots=True)
class WeightConfig:
    glare: float = 0.45
    heat: float = 0.35
    ergonomics: float = 0.20


DEFAULT_WEIGHTS = WeightConfig()


def representative_date_for_season(year: int, season: str) -> date:
    month, day = SEASON_REPRESENTATIVE_DATES[season]
    return date(year, month, day)
