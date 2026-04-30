from __future__ import annotations

from datetime import date, datetime

from app.services.solar import generate_day_times, get_solar_position


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


def test_generate_day_times_skips_nonexistent_local_hour_on_dst_start():
    slots = generate_day_times(date(2026, 3, 29), "Europe/Madrid", 60)

    slot_labels = [slot.strftime("%H:%M %z") for slot in slots]

    assert len(slots) == 23
    assert "02:00 +0100" not in slot_labels
    assert len({slot.astimezone().timestamp() for slot in slots}) == len(slots)
