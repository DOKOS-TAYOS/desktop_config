from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from functools import lru_cache
from typing import cast
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
    result = cast(
        pd.DataFrame,
        pvlib.solarposition.get_solarposition(index, latitude, longitude),
    )
    first_row = result.to_dict(orient="records")[0]
    return float(first_row["azimuth"]), float(first_row["apparent_elevation"])


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
    azimuth_deg, elevation_deg = _solar_position_tuple(
        latitude, longitude, timezone, when_local
    )
    return SolarPosition(
        when_local=when_local,
        azimuth_deg=azimuth_deg,
        elevation_deg=elevation_deg,
    )


def generate_day_times(
    analysis_date: date,
    timezone: str,
    time_step_minutes: int,
) -> list[datetime]:
    tz = ZoneInfo(timezone)
    local_start = datetime.combine(analysis_date, time.min, tzinfo=tz)
    local_end = datetime.combine(analysis_date + timedelta(days=1), time.min, tzinfo=tz)
    current_utc = local_start.astimezone(dt_timezone.utc)
    end_utc = local_end.astimezone(dt_timezone.utc)
    results: list[datetime] = []
    while current_utc < end_utc:
        results.append(current_utc.astimezone(tz))
        current_utc += timedelta(minutes=time_step_minutes)
    return results
