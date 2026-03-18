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
from app.ui.presets import (
    DESK_LAYOUT_PRESETS,
    MONITOR_PRESETS,
    ROOM_PRESETS,
    WINDOW_PRESETS,
    apply_presets,
    default_sidebar_state,
)
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


def _compass_label(value: int) -> str:
    return {
        0: "Norte",
        90: "Este",
        180: "Sur",
        270: "Oeste",
    }[value]


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


def _resolve_location() -> LocationInput:
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
                "No he podido resolver esa ciudad. Prueba otro nombre o usa latitud/longitud."
            )
        return location
    return LocationInput(
        mode="manual",
        label=f"{st.session_state['manual_latitude']:.4f}, {st.session_state['manual_longitude']:.4f}",
        latitude=float(st.session_state["manual_latitude"]),
        longitude=float(st.session_state["manual_longitude"]),
        timezone=str(st.session_state["manual_timezone"]).strip(),
    )


def build_request_from_session() -> AnalysisRequest:
    location = _resolve_location()
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


def _render_presets() -> bool:
    with st.expander("Presets utiles", expanded=True):
        room_preset = st.selectbox("Habitacion", list(ROOM_PRESETS), key="room_preset")
        window_preset = st.selectbox("Ventana", list(WINDOW_PRESETS), key="window_preset")
        monitor_preset = st.selectbox("Monitor", list(MONITOR_PRESETS), key="monitor_preset")
        desk_layout_preset = st.selectbox("Escritorio", list(DESK_LAYOUT_PRESETS), key="desk_layout_preset")
        apply_clicked = st.button("Aplicar presets", width="stretch")
        if apply_clicked:
            patch = apply_presets(room_preset, window_preset, monitor_preset, desk_layout_preset)
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


def _render_location_and_weather() -> None:
    st.subheader("Ubicacion y fecha")
    st.radio("Modo", ["Ciudad", "Manual"], key="location_mode", horizontal=True)
    if st.session_state["location_mode"] == "Ciudad":
        st.text_input("Ciudad o ciudad, pais", key="city_query")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "Latitud",
                min_value=-90.0,
                max_value=90.0,
                step=0.0001,
                format="%.4f",
                key="manual_latitude",
            )
        with col2:
            st.number_input(
                "Longitud",
                min_value=-180.0,
                max_value=180.0,
                step=0.0001,
                format="%.4f",
                key="manual_longitude",
            )
        st.text_input("Zona horaria IANA", key="manual_timezone")

    st.date_input("Fecha de analisis", key="analysis_date")
    st.checkbox("Intentar clima real con Open-Meteo", key="use_live_weather")
    st.checkbox("Anadir resumen estacional", key="include_seasonal_summary")


def _render_advanced_numeric_controls() -> None:
    with st.expander("Ajuste numerico avanzado", expanded=False):
        st.caption("Esta vista sirve como fallback y para ajustes finos.")

        st.subheader("Ventana")
        st.select_slider(
            "Orientacion de la ventana",
            options=[0, 90, 180, 270],
            key="window_orientation_deg",
            format_func=_compass_label,
        )
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Ancho ventana (m)", min_value=0.6, max_value=5.0, step=0.1, key="window_width_m")
        with col2:
            st.slider("Centro ventana", min_value=0.1, max_value=0.9, step=0.01, key="window_center_ratio")

        st.subheader("Habitacion")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Ancho habitacion (m)", min_value=2.0, max_value=10.0, step=0.1, key="room_width_m")
            st.number_input("Altura techo (m)", min_value=2.1, max_value=4.0, step=0.1, key="room_ceiling_height_m")
        with col2:
            st.number_input("Fondo habitacion (m)", min_value=2.0, max_value=10.0, step=0.1, key="room_depth_m")

        st.subheader("Escritorio")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Posicion X mesa (m)", min_value=0.0, step=0.05, key="desk_x_m")
            st.number_input("Ancho mesa (m)", min_value=0.8, max_value=2.2, step=0.05, key="desk_width_m")
            st.number_input("Altura mesa (m)", min_value=0.65, max_value=0.9, step=0.01, key="desk_height_m")
        with col2:
            st.number_input("Posicion Y mesa (m)", min_value=0.0, step=0.05, key="desk_y_m")
            st.number_input("Fondo mesa (m)", min_value=0.5, max_value=1.1, step=0.05, key="desk_depth_m")
            st.slider("Orientacion mesa", min_value=0, max_value=359, step=15, key="desk_orientation_deg")

        st.subheader("Monitor")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Posicion X monitor (m)", min_value=0.0, step=0.05, key="monitor_x_m")
            st.number_input("Diagonal monitor (in)", min_value=20.0, max_value=34.0, step=1.0, key="monitor_diagonal_in")
            st.number_input(
                "Altura centro monitor (m)",
                min_value=0.8,
                max_value=1.6,
                step=0.01,
                key="monitor_center_height_m",
            )
        with col2:
            st.number_input("Posicion Y monitor (m)", min_value=0.0, step=0.05, key="monitor_y_m")
            st.slider("Orientacion monitor", min_value=0, max_value=359, step=15, key="monitor_orientation_deg")
            st.slider("Inclinacion monitor", min_value=-20, max_value=20, step=1, key="monitor_tilt_deg")

        st.subheader("Ergonomia")
        col1, col2 = st.columns(2)
        with col1:
            st.number_input("Altura de ojos (m)", min_value=1.0, max_value=1.5, step=0.01, key="eye_height_m")
        with col2:
            st.number_input(
                "Distancia ojos-monitor (m)",
                min_value=0.45,
                max_value=0.9,
                step=0.01,
                key="viewing_distance_m",
            )


def render_sidebar() -> SidebarSubmission:
    ensure_sidebar_state()
    apply_pending_session_patch()
    with st.sidebar:
        st.header("Contexto del escenario")
        st.caption("La distribucion principal se edita en el plano 2D del panel central.")

        preset_applied = _render_presets()
        _render_location_and_weather()
        _render_advanced_numeric_controls()

        run_requested = st.button("Analizar configuracion", type="primary", width="stretch")
        auto_run = "current_result" not in st.session_state
        should_build_request = run_requested or auto_run or preset_applied
        if not should_build_request:
            return SidebarSubmission(
                request=None,
                run_requested=False,
                use_live_weather=bool(st.session_state["use_live_weather"]),
            )
        try:
            request = build_request_from_session()
        except (ValidationError, Exception) as exc:
            log_event(
                logger,
                logging.WARNING,
                "sidebar_validation_failed",
                error=str(exc),
            )
            return SidebarSubmission(
                request=None,
                run_requested=True,
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
            run_requested=True,
            use_live_weather=bool(st.session_state["use_live_weather"]),
            location_label=request.location.label,
        )
