from __future__ import annotations

from datetime import datetime

from app.services.solar import get_solar_position


def test_solar_position_night_has_negative_elevation():
    solar = get_solar_position(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        when_local=datetime(2026, 6, 21, 0, 30),
    )

    assert solar.elevation_deg < 0


def test_midday_elevation_is_higher_than_morning():
    morning = get_solar_position(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        when_local=datetime(2026, 6, 21, 9, 0),
    )
    noon = get_solar_position(
        latitude=40.4168,
        longitude=-3.7038,
        timezone="Europe/Madrid",
        when_local=datetime(2026, 6, 21, 13, 0),
    )

    assert noon.elevation_deg > morning.elevation_deg
