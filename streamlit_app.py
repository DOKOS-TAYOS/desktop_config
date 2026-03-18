from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from app.services.analysis import analyze_scenario
from app.services.recommendations import recommend_variant
from app.ui.charts import room_plan_chart, score_comparison_chart, seasonal_heatmap, timeline_chart
from app.ui.editor_component import render_floor_plan_editor
from app.ui.editor_state import (
    EditorDelta,
    apply_editor_delta,
    build_scene_state,
    scene_state_from_payload,
    scene_to_request,
)
from app.ui.forms import (
    build_request_from_session,
    queue_request_sync,
    render_sidebar,
)
from app.utils.config import APP_TITLE
from app.utils.logging_utils import bind_context, get_logger, setup_logging

import streamlit as st


setup_logging()
logger = get_logger(__name__)


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)


def _session_logger():
    session_id = st.session_state.setdefault("_session_id", uuid4().hex[:12])
    if "_session_started_logged" not in st.session_state:
        bind_context(logger, session_id=session_id).info("app_session_started")
        st.session_state["_session_started_logged"] = True
    return bind_context(logger, session_id=session_id)


def _next_request_logger(request) -> object:
    session_logger = _session_logger()
    counter = int(st.session_state.get("_request_counter", 0)) + 1
    st.session_state["_request_counter"] = counter
    request_id = f"{st.session_state.get('_session_id')}-{counter}"
    return session_logger.bind(
        analysis_date=request.analysis_date.isoformat(),
        location_label=request.location.label,
        request_id=request_id,
    )


def _best_and_worst_season(result):
    if not result.seasonal_summary:
        return None, None
    scored = [
        (
            item.season,
            round((item.morning_comfort + item.midday_comfort + item.afternoon_comfort) / 3, 1),
        )
        for item in result.seasonal_summary
    ]
    best = max(scored, key=lambda item: item[1])
    worst = min(scored, key=lambda item: item[1])
    return best, worst


def _render_header() -> None:
    st.title("SunSetup Planner")
    st.markdown(
        """
        Decide si tu escritorio funciona mejor por la manana o por la tarde sin promesas magicas.
        La app estima reflejos, calor directo y confort ergonomico con un modelo geometrico simple,
        explicable y pensado para decisiones reales de teletrabajo.
        """
    )


def _store_results(request, use_live_weather: bool) -> None:
    request_logger = _next_request_logger(request)
    request_logger.info("analysis_triggered", include_live_weather=use_live_weather)
    with st.spinner("Calculando posicion solar, riesgos y propuesta recomendada..."):
        current = analyze_scenario(
            request,
            include_live_weather=use_live_weather,
        )
        recommended = recommend_variant(request, current)
    st.session_state["current_result"] = current
    st.session_state["recommended_result"] = recommended
    st.session_state["location_label"] = request.location.label
    request_logger.info(
        "analysis_results_stored",
        comfort_score=current.comfort_score,
        recommended_comfort=recommended.comfort_score,
    )


def _load_request(submission):
    if submission.request is not None:
        return submission.request
    try:
        return build_request_from_session()
    except Exception:
        current = st.session_state.get("current_result")
        if current:
            return current.request
        raise


def _scene_from_request(request):
    scene = build_scene_state(request)
    scene.selected_element = st.session_state.get("editor_selected_element", "desk")
    scene.commit_version = int(st.session_state.get("editor_commit_version", 0))
    return scene


def _apply_scene_commit(scene, base_request, use_live_weather: bool):
    updated_request = scene_to_request(scene, base_request)
    queue_request_sync(updated_request)
    st.session_state["editor_selected_element"] = scene.selected_element
    st.session_state["editor_commit_version"] = scene.commit_version
    _store_results(updated_request, use_live_weather)
    st.rerun()
    return updated_request


def _handle_editor_event(base_request, use_live_weather: bool):
    scene = _scene_from_request(base_request)
    active_request = base_request
    fallback_mode = False
    session_logger = _session_logger().bind(editor_commit_version=scene.commit_version)

    try:
        payload = render_floor_plan_editor(scene, key="floor_plan_editor", height=520)
    except Exception as exc:
        fallback_mode = True
        st.warning("No he podido montar el editor interactivo. Usa el ajuste numerico avanzado de la sidebar.")
        st.caption(f"Detalle tecnico: {exc}")
        session_logger.warning("editor_fallback_enabled", reason=str(exc))
        payload = None

    if not payload:
        return active_request, fallback_mode

    event_seq = int(payload.get("event_seq", 0))
    known_event_seq = int(st.session_state.get("editor_event_seq", 0))
    if event_seq <= known_event_seq:
        return active_request, fallback_mode

    st.session_state["editor_event_seq"] = event_seq
    scene_payload = payload.get("scene")
    if not isinstance(scene_payload, dict):
        session_logger.warning("editor_payload_invalid")
        return active_request, fallback_mode

    returned_scene = scene_state_from_payload(scene_payload)
    st.session_state["editor_selected_element"] = returned_scene.selected_element
    if returned_scene.pending_preview:
        return active_request, fallback_mode
    if returned_scene.commit_version > int(st.session_state.get("editor_commit_version", 0)):
        _session_logger().info(
            "editor_commit_received",
            editor_commit_version=returned_scene.commit_version,
            selected_element=returned_scene.selected_element,
        )
        active_request = _apply_scene_commit(returned_scene, base_request, use_live_weather)
    return active_request, fallback_mode


def _apply_quick_adjustment(base_request, use_live_weather: bool, delta: EditorDelta):
    scene = _scene_from_request(base_request)
    updated_scene = apply_editor_delta(scene, delta)
    return _apply_scene_commit(updated_scene, base_request, use_live_weather)


def _apply_request_update(request, use_live_weather: bool):
    queue_request_sync(request)
    _store_results(request, use_live_weather)
    st.rerun()
    return request


def _selected_element_summary(request):
    selected = st.session_state.get("editor_selected_element", "desk")
    if selected == "window":
        return {
            "title": "Ventana principal",
            "line_1": f"Pared: {int(request.window.orientation_deg):.0f} deg",
            "line_2": f"Ancho: {request.window.width_m:.2f} m",
            "line_3": f"Centro: {request.window.center_ratio:.2f} del tramo",
        }
    if selected == "monitor":
        return {
            "title": "Monitor",
            "line_1": f"Posicion: ({request.monitor.x_m:.2f}, {request.monitor.y_m:.2f}) m",
            "line_2": f"Orientacion: {request.monitor.orientation_deg:.0f} deg",
            "line_3": f"Diagonal: {request.monitor.diagonal_in:.0f} in",
        }
    return {
        "title": "Escritorio",
        "line_1": f"Posicion: ({request.desk.x_m:.2f}, {request.desk.y_m:.2f}) m",
        "line_2": f"Orientacion: {request.desk.orientation_deg:.0f} deg",
        "line_3": f"Tamano: {request.desk.width_m:.2f} x {request.desk.depth_m:.2f} m",
    }


def _render_inspector(base_request, use_live_weather: bool):
    summary = _selected_element_summary(base_request)
    st.subheader("Inspector")
    st.caption("Selecciona un elemento en el plano para ver su ficha y hacer microajustes.")
    st.markdown(f"**{summary['title']}**")
    st.write(summary["line_1"])
    st.write(summary["line_2"])
    st.write(summary["line_3"])

    selected = st.session_state.get("editor_selected_element", "desk")
    if selected in {"desk", "monitor"}:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Girar -15 deg", key=f"rotate_left_{selected}", width="stretch"):
                return _apply_quick_adjustment(
                    base_request,
                    use_live_weather,
                    EditorDelta(target=selected, action="rotate", rotation_deg=-15.0, preview=False),
                )
        with col2:
            if st.button("Girar +15 deg", key=f"rotate_right_{selected}", width="stretch"):
                return _apply_quick_adjustment(
                    base_request,
                    use_live_weather,
                    EditorDelta(target=selected, action="rotate", rotation_deg=15.0, preview=False),
                )

    if selected == "window":
        if st.button("Centrar ventana", key="center_window", width="stretch"):
            centered_request = replace(
                base_request,
                window=replace(base_request.window, center_ratio=0.5),
            )
            return _apply_request_update(centered_request, use_live_weather)

    if selected == "monitor":
        if st.button("Centrar monitor en la mesa", key="center_monitor", width="stretch"):
            centered_request = replace(
                base_request,
                monitor=replace(
                    base_request.monitor,
                    x_m=base_request.desk.x_m,
                    y_m=base_request.desk.y_m,
                    orientation_deg=base_request.desk.orientation_deg,
                ),
            )
            return _apply_request_update(centered_request, use_live_weather)

    return base_request


def _render_summary(current, recommended) -> None:
    delta = round(recommended.comfort_score - current.comfort_score, 1)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Comfort score", f"{current.comfort_score:.1f}/100", delta=f"+{delta:.1f}")
    metric_cols[1].metric(
        "Riesgo de reflejo",
        f"{current.glare_score:.1f}",
        delta=f"{current.glare_score - recommended.glare_score:.1f}",
    )
    metric_cols[2].metric(
        "Riesgo termico",
        f"{current.heat_score:.1f}",
        delta=f"{current.heat_score - recommended.heat_score:.1f}",
    )
    metric_cols[3].metric(
        "Riesgo ergonomico",
        f"{current.ergonomic_score:.1f}",
        delta=f"{current.ergonomic_score - recommended.ergonomic_score:.1f}",
    )

    for alert in current.alerts[:3]:
        st.warning(alert)

    if recommended.recommendations:
        st.success(recommended.recommendations[0].message)

    weather_text = (
        "Clima real con Open-Meteo"
        if current.weather_context.mode == "forecast"
        else "Cielo despejado teorico"
    )
    st.caption(
        f"Ubicacion resuelta: {st.session_state.get('location_label', current.request.location.label)}. "
        f"Modo de clima: {weather_text}."
    )


def _render_main_panels(current, recommended) -> None:
    top_left, top_right = st.columns((1.6, 1.0))
    with top_left:
        st.subheader("Timeline del dia")
        st.plotly_chart(timeline_chart(current), width="stretch")
    with top_right:
        st.subheader("Antes vs recomendacion")
        st.plotly_chart(score_comparison_chart(current, recommended), width="stretch")
        st.markdown("**Cambios accionables**")
        for recommendation in recommended.recommendations:
            st.write(f"- {recommendation.message}")

    bottom_left, bottom_right = st.columns((1.3, 1.3))
    with bottom_left:
        st.subheader("Plano 2D y direccion solar")
        st.plotly_chart(room_plan_chart(current, recommended), width="stretch")
    with bottom_right:
        if current.seasonal_summary:
            st.subheader("Resumen estacional")
            st.plotly_chart(seasonal_heatmap(current), width="stretch")
            best, worst = _best_and_worst_season(current)
            if best and worst:
                st.caption(
                    f"Mejor estacion media: {best[0]} ({best[1]:.1f}/100). "
                    f"Peor estacion media: {worst[0]} ({worst[1]:.1f}/100)."
                )


def _render_comparison(current, recommended) -> None:
    st.subheader("Comparador actual vs recomendado")
    comparison_cols = st.columns(2)
    with comparison_cols[0]:
        st.markdown("**Configuracion actual**")
        st.write(f"- Mesa en ({current.request.desk.x_m:.2f}, {current.request.desk.y_m:.2f}) m")
        st.write(f"- Orientacion mesa: {current.request.desk.orientation_deg:.0f} deg")
        st.write(f"- Orientacion monitor: {current.request.monitor.orientation_deg:.0f} deg")
    with comparison_cols[1]:
        st.markdown("**Configuracion recomendada**")
        st.write(f"- Mesa en ({recommended.request.desk.x_m:.2f}, {recommended.request.desk.y_m:.2f}) m")
        st.write(f"- Orientacion mesa: {recommended.request.desk.orientation_deg:.0f} deg")
        st.write(f"- Orientacion monitor: {recommended.request.monitor.orientation_deg:.0f} deg")


def _render_model_notes() -> None:
    with st.expander("Como interpreta el modelo", expanded=False):
        st.markdown(
            """
            - La planta se modela en 2D con una habitacion rectangular y una ventana principal.
            - La parte vertical es una simplificacion: se usan alturas de mesa, monitor y ojos para estimar incidencia solar.
            - El riesgo de reflejo se clasifica con heuristicas geometricas; no es una simulacion optica cientifica.
            - El clima real solo se usa cuando Open-Meteo tiene datos disponibles para esa fecha. Si no, se calcula con cielo despejado teorico.
            """
        )


_render_header()
submission = render_sidebar()
use_live_weather = bool(st.session_state.get("use_live_weather", False))

if submission.error:
    st.error(submission.error)

request = _load_request(submission)

if submission.run_requested and submission.request is not None:
    _store_results(request, submission.use_live_weather)

editor_cols = st.columns((1.8, 1.0))
with editor_cols[0]:
    st.subheader("Plano editable")
    request, editor_fallback = _handle_editor_event(request, use_live_weather)
with editor_cols[1]:
    request = _render_inspector(request, use_live_weather)

current_result = st.session_state.get("current_result")
recommended_result = st.session_state.get("recommended_result")

if current_result and recommended_result:
    st.divider()
    _render_summary(current_result, recommended_result)
    st.divider()
    _render_main_panels(current_result, recommended_result)
    st.divider()
    _render_comparison(current_result, recommended_result)
    if editor_fallback:
        st.info("El editor no esta disponible en esta sesion. Puedes seguir ajustando el escenario desde la sidebar.")
    _render_model_notes()
else:
    st.info("Ajusta el escenario en la sidebar o en el plano y ejecuta el analisis.")
