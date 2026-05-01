from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

import streamlit as st

from app.domain.models import (
    AnalysisRequest,
    DeskConfig,
    ErgonomicProfile,
    LocationInput,
    MonitorConfig,
    RoomConfig,
    WindowConfig,
)
from app.domain.validation import ValidationError, validate_request
from app.services.weather import geocode_city
from app.ui.i18n import LanguageCode, translate, translate_compass, translate_preset
from app.ui.presets import (
    DESK_LAYOUT_PRESETS,
    MONITOR_PRESETS,
    ROOM_PRESETS,
    WINDOW_PRESETS,
    apply_presets,
    default_sidebar_state,
)
from app.utils.geometry import normalize_angle_deg
from app.utils.logging_utils import get_logger, log_event


PENDING_SESSION_PATCH_KEY = "_pending_form_patch"
logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SidebarSubmission:
    request: AnalysisRequest | None
    run_requested: bool
    use_live_weather: bool
    error: str | None = None
    location_label: str | None = None


def _compass_label(value: int, language: LanguageCode) -> str:
    return translate_compass(value, language)


def _window_center_ratio_bounds(
    *,
    room_width_m: float,
    room_depth_m: float,
    window_orientation_deg: float,
    window_width_m: float,
) -> tuple[float, float]:
    wall_span = (
        room_width_m
        if normalize_angle_deg(window_orientation_deg) in (0, 180)
        else room_depth_m
    )
    if wall_span <= 0:
        return 0.0, 1.0
    half_ratio = min(max(window_width_m / 2 / wall_span, 0.0), 0.5)
    return half_ratio, 1.0 - half_ratio


def _clamp_window_center_ratio_for_slider(
    *,
    current_ratio: float,
    min_ratio: float,
    max_ratio: float,
) -> float:
    return min(max(current_ratio, min_ratio), max_ratio)


def request_to_session_patch(request: AnalysisRequest) -> dict[str, object]:
    return {
        "analysis_date": request.analysis_date,
        "room_width_m": request.room.width_m,
        "room_depth_m": request.room.depth_m,
        "room_ceiling_height_m": request.room.ceiling_height_m,
        "window_orientation_deg": request.window.orientation_deg,
        "window_width_m": request.window.width_m,
        "window_center_ratio": request.window.center_ratio,
        "desk_x_m": request.desk.x_m,
        "desk_y_m": request.desk.y_m,
        "desk_width_m": request.desk.width_m,
        "desk_depth_m": request.desk.depth_m,
        "desk_height_m": request.desk.height_m,
        "desk_orientation_deg": request.desk.orientation_deg,
        "monitor_x_m": request.monitor.x_m,
        "monitor_y_m": request.monitor.y_m,
        "monitor_center_height_m": request.monitor.center_height_m,
        "monitor_diagonal_in": request.monitor.diagonal_in,
        "monitor_orientation_deg": request.monitor.orientation_deg,
        "monitor_tilt_deg": request.monitor.tilt_deg,
        "eye_height_m": request.ergonomic.eye_height_m,
        "viewing_distance_m": request.ergonomic.viewing_distance_m,
        "include_seasonal_summary": request.include_seasonal_summary,
    }


def sync_request_to_session(request: AnalysisRequest) -> None:
    for key, value in request_to_session_patch(request).items():
        st.session_state[key] = value


def queue_request_sync(request: AnalysisRequest) -> None:
    st.session_state[PENDING_SESSION_PATCH_KEY] = request_to_session_patch(request)


def apply_pending_session_patch() -> None:
    patch = st.session_state.pop(PENDING_SESSION_PATCH_KEY, None)
    if not isinstance(patch, dict):
        return
    for key, value in patch.items():
        st.session_state[key] = value
    log_event(logger, logging.INFO, "session_patch_applied", field_count=len(patch))


def ensure_sidebar_state() -> None:
    defaults = default_sidebar_state()
    defaults["window_center_ratio"] = 0.5
    defaults["editor_selected_element"] = "desk"
    defaults["editor_commit_version"] = 0
    defaults["editor_event_seq"] = 0
    defaults["editor_mode"] = "plan"
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state["analysis_date"] is None:
        st.session_state["analysis_date"] = date.today()


def _resolve_location(language: LanguageCode) -> LocationInput:
    mode = st.session_state["location_mode"]
    log_event(logger, logging.INFO, "location_mode_selected", mode=mode)
    if mode == "Ciudad":
        location = geocode_city(st.session_state["city_query"].strip())
        if location is None:
            log_event(
                logger,
                logging.WARNING,
                "city_not_resolved",
                city_query=st.session_state["city_query"].strip(),
            )
            raise ValidationError(
                "No he podido resolver esa ciudad. Prueba otro nombre o usa latitud y longitud."
                if language == "es"
                else "I could not resolve that city. Try another name or use latitude and longitude."
            )
        return location
    return LocationInput(
        mode="manual",
        label=f"{st.session_state['manual_latitude']:.4f}, {st.session_state['manual_longitude']:.4f}",
        latitude=float(st.session_state["manual_latitude"]),
        longitude=float(st.session_state["manual_longitude"]),
        timezone=str(st.session_state["manual_timezone"]).strip(),
    )


def build_request_from_session(language: LanguageCode = "es") -> AnalysisRequest:
    location = _resolve_location(language)
    request = AnalysisRequest(
        location=location,
        analysis_date=st.session_state["analysis_date"],
        room=RoomConfig(
            width_m=float(st.session_state["room_width_m"]),
            depth_m=float(st.session_state["room_depth_m"]),
            ceiling_height_m=float(st.session_state["room_ceiling_height_m"]),
        ),
        window=WindowConfig(
            orientation_deg=float(st.session_state["window_orientation_deg"]),
            width_m=float(st.session_state["window_width_m"]),
            center_ratio=float(st.session_state["window_center_ratio"]),
        ),
        desk=DeskConfig(
            x_m=float(st.session_state["desk_x_m"]),
            y_m=float(st.session_state["desk_y_m"]),
            width_m=float(st.session_state["desk_width_m"]),
            depth_m=float(st.session_state["desk_depth_m"]),
            height_m=float(st.session_state["desk_height_m"]),
            orientation_deg=float(st.session_state["desk_orientation_deg"]),
        ),
        monitor=MonitorConfig(
            x_m=float(st.session_state["monitor_x_m"]),
            y_m=float(st.session_state["monitor_y_m"]),
            center_height_m=float(st.session_state["monitor_center_height_m"]),
            diagonal_in=float(st.session_state["monitor_diagonal_in"]),
            orientation_deg=float(st.session_state["monitor_orientation_deg"]),
            tilt_deg=float(st.session_state["monitor_tilt_deg"]),
        ),
        ergonomic=ErgonomicProfile(
            eye_height_m=float(st.session_state["eye_height_m"]),
            viewing_distance_m=float(st.session_state["viewing_distance_m"]),
            preset_name="manual",
        ),
        include_seasonal_summary=bool(st.session_state["include_seasonal_summary"]),
    )
    validate_request(request)
    return request


def _render_presets(language: LanguageCode) -> bool:
    with st.expander(translate("sidebar.presets", language), expanded=True):
        room_preset = st.selectbox(
            translate("sidebar.room", language),
            list(ROOM_PRESETS),
            key="room_preset",
            format_func=lambda label: translate_preset("room", label, language),
        )
        window_preset = st.selectbox(
            translate("sidebar.window", language),
            list(WINDOW_PRESETS),
            key="window_preset",
            format_func=lambda label: translate_preset("window", label, language),
        )
        monitor_preset = st.selectbox(
            translate("sidebar.monitor", language),
            list(MONITOR_PRESETS),
            key="monitor_preset",
        )
        desk_layout_preset = st.selectbox(
            translate("sidebar.desk_layout", language),
            list(DESK_LAYOUT_PRESETS),
            key="desk_layout_preset",
            format_func=lambda label: translate_preset("desk_layout", label, language),
        )
        apply_clicked = st.button(
            translate("sidebar.apply_presets", language), width="stretch"
        )
        if apply_clicked:
            patch = apply_presets(
                room_preset, window_preset, monitor_preset, desk_layout_preset
            )
            patch["window_center_ratio"] = 0.5
            for key, value in patch.items():
                st.session_state[key] = value
            log_event(
                logger,
                logging.INFO,
                "presets_applied",
                desk_layout_preset=desk_layout_preset,
                monitor_preset=monitor_preset,
                room_preset=room_preset,
                window_preset=window_preset,
            )
    return apply_clicked


def _render_location_and_weather(language: LanguageCode) -> None:
    st.subheader(translate("sidebar.location_and_date", language))
    st.radio(
        translate("sidebar.mode", language),
        ["Ciudad", "Manual"],
        key="location_mode",
        horizontal=True,
        format_func=lambda value: translate(
            "sidebar.mode.city" if value == "Ciudad" else "sidebar.mode.manual",
            language,
        ),
    )
    if st.session_state["location_mode"] == "Ciudad":
        st.text_input(translate("sidebar.city_query", language), key="city_query")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Latitud" if language == "es" else "Latitude",
                min_value=-90.0,
                max_value=90.0,
                step=0.0001,
                format="%.4f",
                key="manual_latitude",
            )
        with col2:
            st.number_input(
                "Longitud" if language == "es" else "Longitude",
                min_value=-180.0,
                max_value=180.0,
                step=0.0001,
                format="%.4f",
                key="manual_longitude",
            )
        st.text_input(translate("sidebar.timezone", language), key="manual_timezone")

    st.date_input(translate("sidebar.analysis_date", language), key="analysis_date")
    st.checkbox(translate("sidebar.use_live_weather", language), key="use_live_weather")
    st.checkbox(
        translate("sidebar.include_seasonal_summary", language),
        key="include_seasonal_summary",
    )


def _render_advanced_numeric_controls(language: LanguageCode) -> None:
    with st.expander(translate("sidebar.advanced_controls", language), expanded=False):
        st.caption(translate("sidebar.advanced_caption", language))

        st.subheader(translate("sidebar.window", language))
        st.select_slider(
            "Orientación de la ventana" if language == "es" else "Window orientation",
            options=[0, 90, 180, 270],
            key="window_orientation_deg",
            format_func=lambda value: _compass_label(value, language),
        )
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Ancho de la ventana (m)" if language == "es" else "Window width (m)",
                min_value=0.6,
                max_value=5.0,
                step=0.1,
                key="window_width_m",
            )
        with col2:
            center_min_ratio, center_max_ratio = _window_center_ratio_bounds(
                room_width_m=float(st.session_state["room_width_m"]),
                room_depth_m=float(st.session_state["room_depth_m"]),
                window_orientation_deg=float(
                    st.session_state["window_orientation_deg"]
                ),
                window_width_m=float(st.session_state["window_width_m"]),
            )
            st.session_state["window_center_ratio"] = (
                _clamp_window_center_ratio_for_slider(
                    current_ratio=float(st.session_state["window_center_ratio"]),
                    min_ratio=float(center_min_ratio),
                    max_ratio=float(center_max_ratio),
                )
            )
            st.slider(
                "Centro de la ventana" if language == "es" else "Window center",
                min_value=float(center_min_ratio),
                max_value=float(center_max_ratio),
                step=0.01,
                key="window_center_ratio",
            )

        st.subheader(translate("sidebar.room", language))
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Ancho de la habitación (m)" if language == "es" else "Room width (m)",
                min_value=2.0,
                max_value=10.0,
                step=0.1,
                key="room_width_m",
            )
            st.number_input(
                "Altura del techo (m)" if language == "es" else "Ceiling height (m)",
                min_value=2.1,
                max_value=4.0,
                step=0.1,
                key="room_ceiling_height_m",
            )
        with col2:
            st.number_input(
                "Fondo de la habitación (m)" if language == "es" else "Room depth (m)",
                min_value=2.0,
                max_value=10.0,
                step=0.1,
                key="room_depth_m",
            )

        st.subheader("Mesa" if language == "es" else "Desk")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Posición X de la mesa (m)"
                if language == "es"
                else "Desk X position (m)",
                min_value=0.0,
                step=0.05,
                key="desk_x_m",
            )
            st.number_input(
                "Ancho de la mesa (m)" if language == "es" else "Desk width (m)",
                min_value=0.8,
                max_value=2.2,
                step=0.05,
                key="desk_width_m",
            )
            st.number_input(
                "Altura de la mesa (m)" if language == "es" else "Desk height (m)",
                min_value=0.65,
                max_value=0.9,
                step=0.01,
                key="desk_height_m",
            )
        with col2:
            st.number_input(
                "Posición Y de la mesa (m)"
                if language == "es"
                else "Desk Y position (m)",
                min_value=0.0,
                step=0.05,
                key="desk_y_m",
            )
            st.number_input(
                "Fondo de la mesa (m)" if language == "es" else "Desk depth (m)",
                min_value=0.5,
                max_value=1.1,
                step=0.05,
                key="desk_depth_m",
            )
            st.slider(
                "Orientación de la mesa" if language == "es" else "Desk orientation",
                min_value=0,
                max_value=359,
                step=15,
                key="desk_orientation_deg",
            )

        st.subheader(translate("sidebar.monitor", language))
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Posición X del monitor (m)"
                if language == "es"
                else "Monitor X position (m)",
                min_value=0.0,
                step=0.05,
                key="monitor_x_m",
            )
            st.number_input(
                "Diagonal del monitor (in)"
                if language == "es"
                else "Monitor diagonal (in)",
                min_value=20.0,
                max_value=34.0,
                step=1.0,
                key="monitor_diagonal_in",
            )
            st.number_input(
                "Altura del centro del monitor (m)"
                if language == "es"
                else "Monitor center height (m)",
                min_value=0.8,
                max_value=1.6,
                step=0.01,
                key="monitor_center_height_m",
            )
        with col2:
            st.number_input(
                "Posición Y del monitor (m)"
                if language == "es"
                else "Monitor Y position (m)",
                min_value=0.0,
                step=0.05,
                key="monitor_y_m",
            )
            st.slider(
                "Orientación del monitor"
                if language == "es"
                else "Monitor orientation",
                min_value=0,
                max_value=359,
                step=15,
                key="monitor_orientation_deg",
            )
            st.slider(
                "Inclinación del monitor" if language == "es" else "Monitor tilt",
                min_value=-20,
                max_value=20,
                step=1,
                key="monitor_tilt_deg",
            )

        st.subheader("Ergonomía" if language == "es" else "Ergonomics")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Altura de los ojos (m)" if language == "es" else "Eye height (m)",
                min_value=1.0,
                max_value=1.5,
                step=0.01,
                key="eye_height_m",
            )
        with col2:
            st.number_input(
                "Distancia ojos-monitor (m)"
                if language == "es"
                else "Eye-to-monitor distance (m)",
                min_value=0.45,
                max_value=0.9,
                step=0.01,
                key="viewing_distance_m",
            )


def render_sidebar(language: LanguageCode = "es") -> SidebarSubmission:
    ensure_sidebar_state()
    apply_pending_session_patch()
    with st.sidebar:
        st.header(translate("sidebar.context", language))
        st.caption(translate("sidebar.caption", language))

        preset_applied = _render_presets(language)
        _render_location_and_weather(language)
        _render_advanced_numeric_controls(language)

        run_requested = st.button(
            translate("sidebar.run_analysis", language),
            type="primary",
            width="stretch",
        )
        should_build_request = run_requested or preset_applied
        if not should_build_request:
            return SidebarSubmission(
                request=None,
                run_requested=False,
                use_live_weather=bool(st.session_state["use_live_weather"]),
            )
        try:
            request = build_request_from_session(language)
        except (ValidationError, Exception) as exc:
            log_event(
                logger,
                logging.WARNING,
                "sidebar_validation_failed",
                error=str(exc),
            )
            return SidebarSubmission(
                request=None,
                run_requested=run_requested,
                use_live_weather=bool(st.session_state["use_live_weather"]),
                error=str(exc),
            )
        log_event(
            logger,
            logging.INFO,
            "sidebar_request_built",
            analysis_date=request.analysis_date.isoformat(),
            location_label=request.location.label,
        )
        return SidebarSubmission(
            request=request,
            run_requested=run_requested,
            use_live_weather=bool(st.session_state["use_live_weather"]),
            location_label=request.location.label,
        )
