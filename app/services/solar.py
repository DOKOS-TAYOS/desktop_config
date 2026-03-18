from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
import pvlib

from app.domain.models import SolarPosition


@lru_cache(maxsize=4096)
def _solar_position_tuple(
    latitude: float,
    longitude: float,
    timezone: str,
    when_local: datetime,
) -> tuple[float, float]:
    tz = ZoneInfo(timezone)
    if when_local.tzinfo is None:
        when_local = when_local.replace(tzinfo=tz)
    else:
        when_local = when_local.astimezone(tz)
    index = pd.DatetimeIndex([pd.Timestamp(when_local)])
    result = pvlib.solarposition.get_solarposition(index, latitude, longitude)
    row = result.iloc[0]
    return float(row["azimuth"]), float(row["apparent_elevation"])


def get_solar_position(
    latitude: float,
    longitude: float,
    timezone: str,
    when_local: datetime,
) -> SolarPosition:
    tz = ZoneInfo(timezone)
    if when_local.tzinfo is None:
        when_local = when_local.replace(tzinfo=tz)
    else:
        when_local = when_local.astimezone(tz)
    azimuth_deg, elevation_deg = _solar_position_tuple(latitude, longitude, timezone, when_local)
    return SolarPosition(
        when_local=when_local,
        azimuth_deg=azimuth_deg,
        elevation_deg=elevation_deg,
    )


def generate_day_times(
    analysis_date: date, timezone: str, time_step_minutes: int
) -> list[datetime]:
    tz = ZoneInfo(timezone)
    current = datetime.combine(analysis_date, time.min, tzinfo=tz)
    end = current + timedelta(days=1)
    results: list[datetime] = []
    while current < end:
        results.append(current)
        current += timedelta(minutes=time_step_minutes)
    return results
