from __future__ import annotations

import logging
from typing import NoReturn
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.models import AnalysisRequest
from app.utils.geometry import (
    desk_rectangle,
    normalize_angle_deg,
    point_in_rotated_rectangle,
    rectangle_corners,
)
from app.utils.logging_utils import get_logger, log_event


logger = get_logger(__name__)


class ValidationError(ValueError):
    """Raised when the scenario contains invalid geometry or values."""


def _fail(message: str, **fields: object) -> NoReturn:
    log_event(logger, logging.WARNING, "validation_failed", error=message, **fields)
    raise ValidationError(message)


def _ensure_positive(name: str, value: float) -> None:
    if value <= 0:
        _fail(f"{name} must be positive.", field=name, value=value)


def validate_request(request: AnalysisRequest) -> None:
    location = request.location
    room = request.room
    window = request.window
    desk = request.desk
    monitor = request.monitor
    ergonomic = request.ergonomic

    if not -90 <= location.latitude <= 90:
        _fail(
            "latitude must be between -90 and 90.",
            field="location.latitude",
            value=location.latitude,
        )
    if not -180 <= location.longitude <= 180:
        _fail(
            "longitude must be between -180 and 180.",
            field="location.longitude",
            value=location.longitude,
        )
    try:
        ZoneInfo(location.timezone)
    except ZoneInfoNotFoundError:
        _fail(
            "timezone must be a valid IANA timezone.",
            field="location.timezone",
            value=location.timezone,
        )

    for name, value in (
        ("width_m", room.width_m),
        ("depth_m", room.depth_m),
        ("ceiling_height_m", room.ceiling_height_m),
        ("window.width_m", window.width_m),
        ("window.height_m", window.height_m),
        ("desk.width_m", desk.width_m),
        ("desk.depth_m", desk.depth_m),
        ("desk.height_m", desk.height_m),
        ("monitor.center_height_m", monitor.center_height_m),
        ("monitor.diagonal_in", monitor.diagonal_in),
        ("ergonomic.eye_height_m", ergonomic.eye_height_m),
        ("ergonomic.viewing_distance_m", ergonomic.viewing_distance_m),
    ):
        _ensure_positive(name, value)

    if (
        window.sill_height_m < 0
        or window.sill_height_m + window.height_m > room.ceiling_height_m
    ):
        _fail(
            "window sill/height must fit inside the room height.", field="window.height"
        )
    if not 0.0 <= window.center_ratio <= 1.0:
        _fail(
            "window center ratio must be between 0 and 1.",
            field="window.center_ratio",
            value=window.center_ratio,
        )

    wall_span = (
        room.width_m
        if normalize_angle_deg(window.orientation_deg) in (0, 180)
        else room.depth_m
    )
    if window.width_m > wall_span:
        _fail(
            "window width cannot exceed its wall span.",
            field="window.width_m",
            value=window.width_m,
        )
    center_along_wall = window.center_ratio * wall_span
    if (
        center_along_wall - window.width_m / 2 < 0
        or center_along_wall + window.width_m / 2 > wall_span
    ):
        _fail(
            "window must stay fully inside its wall span.",
            field="window.center_ratio",
            value=window.center_ratio,
        )

    desk_rect = desk_rectangle(desk)
    if not (0 <= desk.x_m <= room.width_m and 0 <= desk.y_m <= room.depth_m):
        _fail("desk must remain inside the room bounds.", field="desk.position")
    for corner_x, corner_y in rectangle_corners(desk_rect):
        if not (0 <= corner_x <= room.width_m and 0 <= corner_y <= room.depth_m):
            _fail("desk must remain inside the room bounds.", field="desk.corners")

    if not (0 <= monitor.x_m <= room.width_m and 0 <= monitor.y_m <= room.depth_m):
        _fail("monitor must remain inside the room bounds.", field="monitor.position")
    if not point_in_rotated_rectangle((monitor.x_m, monitor.y_m), desk_rect):
        _fail(
            "monitor must sit on top of the desk footprint.", field="monitor.position"
        )

    if monitor.center_height_m > room.ceiling_height_m:
        _fail(
            "monitor center height must fit inside the room.",
            field="monitor.center_height_m",
        )
    if not -45 <= monitor.tilt_deg <= 45:
        _fail(
            "monitor tilt must stay within a realistic range.",
            field="monitor.tilt_deg",
            value=monitor.tilt_deg,
        )
