from __future__ import annotations


ROOM_PRESETS = {
    "Despacho estándar": {"width_m": 4.0, "depth_m": 3.5, "ceiling_height_m": 2.6},
    "Habitación pequeña": {"width_m": 3.0, "depth_m": 2.6, "ceiling_height_m": 2.5},
}

WINDOW_PRESETS = {
    "Norte": 0,
    "Este": 90,
    "Sur": 180,
    "Oeste": 270,
}

MONITOR_PRESETS = {
    '24"': {"diagonal_in": 24.0, "center_height_m": 1.12, "tilt_deg": -5.0},
    '27"': {"diagonal_in": 27.0, "center_height_m": 1.16, "tilt_deg": -5.0},
}

DESK_LAYOUT_PRESETS = {
    "Centrado": {"x_ratio": 0.5, "y_ratio": 0.5, "orientation_deg": 180},
    "Pegado a pared": {"x_ratio": 0.5, "y_ratio": 0.22, "orientation_deg": 180},
}


def default_sidebar_state() -> dict[str, object]:
    return {
        "room_preset": "Despacho estándar",
        "window_preset": "Oeste",
        "monitor_preset": '27"',
        "desk_layout_preset": "Centrado",
        "location_mode": "Manual",
        "city_query": "Madrid",
        "manual_latitude": 40.4168,
        "manual_longitude": -3.7038,
        "manual_timezone": "Europe/Madrid",
        "analysis_date": None,
        "use_live_weather": True,
        "include_seasonal_summary": True,
        "room_width_m": 4.0,
        "room_depth_m": 3.5,
        "room_ceiling_height_m": 2.6,
        "window_orientation_deg": 270,
        "window_width_m": 1.6,
        "desk_x_m": 2.0,
        "desk_y_m": 1.75,
        "desk_width_m": 1.4,
        "desk_depth_m": 0.7,
        "desk_height_m": 0.74,
        "desk_orientation_deg": 180,
        "monitor_x_m": 2.0,
        "monitor_y_m": 1.75,
        "monitor_center_height_m": 1.16,
        "monitor_diagonal_in": 27.0,
        "monitor_orientation_deg": 180,
        "monitor_tilt_deg": -5.0,
        "eye_height_m": 1.22,
        "viewing_distance_m": 0.65,
    }


def apply_presets(
    room_name: str,
    window_name: str,
    monitor_name: str,
    desk_layout_name: str,
) -> dict[str, float]:
    room = ROOM_PRESETS[room_name]
    window_orientation = WINDOW_PRESETS[window_name]
    monitor = MONITOR_PRESETS[monitor_name]
    layout = DESK_LAYOUT_PRESETS[desk_layout_name]
    desk_x = round(room["width_m"] * layout["x_ratio"], 2)
    desk_y = round(room["depth_m"] * layout["y_ratio"], 2)
    desk_orientation = float(layout["orientation_deg"])

    return {
        "room_width_m": room["width_m"],
        "room_depth_m": room["depth_m"],
        "room_ceiling_height_m": room["ceiling_height_m"],
        "window_orientation_deg": float(window_orientation),
        "window_width_m": min(1.6, room["width_m"] if window_orientation in (0, 180) else room["depth_m"]),
        "desk_x_m": desk_x,
        "desk_y_m": desk_y,
        "desk_width_m": 1.4,
        "desk_depth_m": 0.7,
        "desk_height_m": 0.74,
        "desk_orientation_deg": desk_orientation,
        "monitor_x_m": desk_x,
        "monitor_y_m": desk_y,
        "monitor_center_height_m": monitor["center_height_m"],
        "monitor_diagonal_in": monitor["diagonal_in"],
        "monitor_orientation_deg": desk_orientation,
        "monitor_tilt_deg": monitor["tilt_deg"],
        "eye_height_m": 1.22,
        "viewing_distance_m": 0.65,
    }
