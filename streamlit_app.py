from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import streamlit as st

from app.domain.models import AnalysisRequest, ScenarioResult, TimeWindowSummary
from app.ui.editor_component import render_floor_plan_editor
from app.ui.editor_state import (
    EditorDelta,
    SceneElementKind,
    SceneState,
    apply_editor_delta,
    build_scene_state,
    scene_state_from_payload,
    scene_to_request,
)
from app.ui.forms import build_request_from_session, queue_request_sync, render_sidebar
from app.ui.i18n import (
    LanguageCode,
    translate,
    translate_season,
    translate_window_label,
)
from app.utils.config import APP_TITLE
from app.utils.logging_utils import bind_context, get_logger, setup_logging


logger = get_logger(__name__)


def analyze_scenario(
    request: AnalysisRequest,
    *,
    include_live_weather: bool = False,
) -> ScenarioResult:
    from app.services.analysis import analyze_scenario as _analyze_scenario

    return _analyze_scenario(request, include_live_weather=include_live_weather)


def recommend_variant(
    request: AnalysisRequest,
    baseline: ScenarioResult | None = None,
) -> ScenarioResult:
    from app.services.recommendations import recommend_variant as _recommend_variant

    return _recommend_variant(request, baseline)


def timeline_chart(result: ScenarioResult, language: LanguageCode = "es") -> Any:
    from app.ui.charts import timeline_chart as _timeline_chart

    return _timeline_chart(result, language)


def score_comparison_chart(
    current: ScenarioResult,
    recommended: ScenarioResult,
    language: LanguageCode = "es",
) -> Any:
    from app.ui.charts import score_comparison_chart as _score_comparison_chart

    return _score_comparison_chart(current, recommended, language)


def room_plan_chart(
    current: ScenarioResult,
    recommended: ScenarioResult | None = None,
    language: LanguageCode = "es",
) -> Any:
    from app.ui.charts import room_plan_chart as _room_plan_chart

    return _room_plan_chart(current, recommended, language)


def seasonal_heatmap(result: ScenarioResult, language: LanguageCode = "es") -> Any:
    from app.ui.charts import seasonal_heatmap as _seasonal_heatmap

    return _seasonal_heatmap(result, language)


def _session_logger() -> Any:
    session_id = st.session_state.setdefault("_session_id", uuid4().hex[:12])
    if "_session_started_logged" not in st.session_state:
        bind_context(logger, session_id=session_id).info("app_session_started")
        st.session_state["_session_started_logged"] = True
    return bind_context(logger, session_id=session_id)


def _static_plotly_config() -> dict[str, bool]:
    return {
        "displayModeBar": False,
        "scrollZoom": False,
        "staticPlot": True,
    }


def _current_language() -> LanguageCode:
    return cast(LanguageCode, st.session_state.setdefault("language", "es"))


def _request_cache_key(request: AnalysisRequest, use_live_weather: bool) -> str:
    return f"{use_live_weather}:{request!r}"


def _cached_results_for_request(
    request: AnalysisRequest,
    use_live_weather: bool,
) -> tuple[ScenarioResult, ScenarioResult]:
    cache = cast(
        dict[str, tuple[ScenarioResult, ScenarioResult]],
        st.session_state.setdefault("_analysis_cache", {}),
    )
    cache_key = _request_cache_key(request, use_live_weather)
    if cache_key not in cache:
        current = analyze_scenario(
            request,
            include_live_weather=use_live_weather,
        )
        recommended = recommend_variant(request, current)
        cache[cache_key] = (deepcopy(current), deepcopy(recommended))
    cached_current, cached_recommended = cache[cache_key]
    return deepcopy(cached_current), deepcopy(cached_recommended)


def _has_pending_analysis(
    request: AnalysisRequest,
    *,
    use_live_weather: bool,
) -> bool:
    last_key = cast(str | None, st.session_state.get("last_analyzed_request_key"))
    if last_key is None:
        return False
    return last_key != _request_cache_key(request, use_live_weather)


def _remember_draft_request(request: AnalysisRequest) -> None:
    st.session_state["draft_request"] = deepcopy(request)


def _draft_request_from_state() -> AnalysisRequest | None:
    draft_request = cast(AnalysisRequest | None, st.session_state.get("draft_request"))
    return deepcopy(draft_request) if draft_request is not None else None


def _render_language_switch() -> LanguageCode:
    current = _current_language()
    selected = st.segmented_control(
        translate("language.label", current),
        options=["es", "en"],
        selection_mode="single",
        default=current,
        key="language_switch",
        format_func=lambda value: value.upper(),
    )
    if selected in {"es", "en"}:
        st.session_state["language"] = selected
        return cast(LanguageCode, selected)
    st.session_state["language"] = current
    return current


def _next_request_logger(request: AnalysisRequest) -> Any:
    session_logger = _session_logger()
    counter = int(st.session_state.get("_request_counter", 0)) + 1
    st.session_state["_request_counter"] = counter
    request_id = f"{st.session_state.get('_session_id')}-{counter}"
    return session_logger.bind(
        analysis_date=request.analysis_date.isoformat(),
        location_label=request.location.label,
        request_id=request_id,
    )


def _best_and_worst_season(
    result: ScenarioResult,
) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    if not result.seasonal_summary:
        return None, None
    scored: list[tuple[str, float]] = [
        (
            item.season,
            round(
                (item.morning_comfort + item.midday_comfort + item.afternoon_comfort)
                / 3,
                1,
            ),
        )
        for item in result.seasonal_summary
    ]
    best = max(scored, key=lambda item: item[1])
    worst = min(scored, key=lambda item: item[1])
    return best, worst


def _format_window_summary(
    window_summary: TimeWindowSummary | None, language: LanguageCode
) -> str:
    if window_summary is None:
        return translate("summary.no_data", language)
    return (
        f"{window_summary.start_time_label}-{window_summary.end_time_label} "
        f"({translate_window_label(window_summary.label, language)})"
    )


def _localized_primary_message(current: ScenarioResult, language: LanguageCode) -> str:
    dominant_risk = current.diagnosis.dominant_risk
    worst_window = current.diagnosis.worst_window
    worst_label = (
        translate_window_label(worst_window.label, language)
        if worst_window is not None
        else ("las horas más delicadas" if language == "es" else "the trickiest hours")
    )
    if dominant_risk == "glare":
        return (
            f"El principal problema es el reflejo, sobre todo en la {worst_label}."
            if language == "es"
            else f"The main problem is glare, especially in the {worst_label}."
        )
    if dominant_risk == "heat":
        return (
            f"El principal problema es el calor o el sol directo, sobre todo en la {worst_label}."
            if language == "es"
            else f"The main problem is heat or direct sun, especially in the {worst_label}."
        )
    if dominant_risk == "ergonomics":
        return (
            "El principal límite es ergonómico: la orientación y el encaje entre mesa y monitor pesan más que el sol."
            if language == "es"
            else "The main limitation is ergonomic: desk and monitor alignment matters more than the sun here."
        )
    return (
        "No hay un riesgo dominante claro: la configuración está razonablemente equilibrada para este modelo."
        if language == "es"
        else "There is no clearly dominant risk: the layout is reasonably balanced for this model."
    )


def _localized_confidence_message(
    current: ScenarioResult, language: LanguageCode
) -> str:
    if current.weather_context.mode == "forecast":
        return (
            "Confianza media-alta: el análisis usa pronóstico real disponible para esa fecha."
            if language == "es"
            else "Medium-high confidence: the analysis uses real forecast data available for that date."
        )
    return (
        "Confianza moderada: la geometría es útil, pero el clima se ha estimado con cielo despejado teórico."
        if language == "es"
        else "Moderate confidence: the geometry is useful, but the weather has been estimated with a theoretical clear sky."
    )


def _rotation_delta(current_deg: float, target_deg: float) -> float:
    return ((target_deg - current_deg + 540) % 360) - 180


def _localized_recommendation_lines(
    current: ScenarioResult, recommended: ScenarioResult, language: LanguageCode
) -> tuple[list[str], str]:
    current_request = current.request
    recommended_request = recommended.request
    lines: list[str] = []

    delta_x = recommended_request.desk.x_m - current_request.desk.x_m
    delta_y = recommended_request.desk.y_m - current_request.desk.y_m
    if abs(delta_x) >= 0.05:
        direction_key = (
            "summary.direction.east" if delta_x > 0 else "summary.direction.west"
        )
        lines.append(
            translate(
                "summary.recommendation.move",
                language,
                distance_cm=round(abs(delta_x) * 100),
                direction=translate(direction_key, language),
            )
        )
    if abs(delta_y) >= 0.05:
        direction_key = (
            "summary.direction.north" if delta_y > 0 else "summary.direction.south"
        )
        lines.append(
            translate(
                "summary.recommendation.move",
                language,
                distance_cm=round(abs(delta_y) * 100),
                direction=translate(direction_key, language),
            )
        )

    desk_delta = _rotation_delta(
        current_request.desk.orientation_deg, recommended_request.desk.orientation_deg
    )
    if abs(desk_delta) >= 1:
        direction_key = (
            "summary.direction.right" if desk_delta > 0 else "summary.direction.left"
        )
        lines.append(
            translate(
                "summary.recommendation.rotate_desk",
                language,
                degrees=round(abs(desk_delta)),
                direction=translate(direction_key, language),
            )
        )

    monitor_delta = _rotation_delta(
        current_request.monitor.orientation_deg,
        recommended_request.monitor.orientation_deg,
    )
    if abs(monitor_delta) >= 1:
        direction_key = (
            "summary.direction.right" if monitor_delta > 0 else "summary.direction.left"
        )
        lines.append(
            translate(
                "summary.recommendation.rotate_monitor",
                language,
                degrees=round(abs(monitor_delta)),
                direction=translate(direction_key, language),
            )
        )

    materially_better = (
        recommended_request != current_request
        and recommended.comfort_score > current.comfort_score + 0.2
    )
    reason = translate(
        "summary.recommendation.reason.material"
        if materially_better
        else "summary.recommendation.reason.marginal",
        language,
    )

    if not lines and language == "es" and recommended.recommendations:
        lines = [recommended.recommendations[0].message.rstrip(".") + "."]
        reason = recommended.recommendations[0].reason
    elif not lines:
        lines = [translate("summary.recommendation.no_change", language)]

    return lines, reason


def _diagnosis_panel_data(
    current: ScenarioResult,
    recommended: ScenarioResult,
    language: LanguageCode = "es",
) -> dict[str, str]:
    recommendation_lines, recommendation_reason = _localized_recommendation_lines(
        current, recommended, language
    )
    first_recommendation = (
        f"{recommendation_lines[0]} {recommendation_reason}"
        if recommendation_lines
        else translate("summary.recommendation.none", language)
    )
    return {
        "what_is_happening": _localized_primary_message(current, language),
        "good_hours": _format_window_summary(current.diagnosis.best_window, language),
        "conflict_hours": _format_window_summary(
            current.diagnosis.worst_window, language
        ),
        "first_adjustment": first_recommendation,
        "confidence": _localized_confidence_message(current, language),
    }


def _render_header(language: LanguageCode) -> None:
    st.title(translate("app.title", language))
    st.markdown(
        f"""
        {translate("header.subtitle", language)}
        {translate("header.description", language)}
        """
    )


def _store_results(request: AnalysisRequest, use_live_weather: bool) -> None:
    request_logger = _next_request_logger(request)
    request_logger.info("analysis_triggered", include_live_weather=use_live_weather)
    spinner_text = (
        "Calculando posición solar, riesgos y propuesta recomendada..."
        if _current_language() == "es"
        else "Calculating solar position, risks, and the recommended layout..."
    )
    with st.spinner(spinner_text):
        current, recommended = _cached_results_for_request(request, use_live_weather)
    st.session_state["current_result"] = current
    st.session_state["recommended_result"] = recommended
    st.session_state["location_label"] = request.location.label
    st.session_state["last_analyzed_request_key"] = _request_cache_key(
        request, use_live_weather
    )
    _remember_draft_request(request)
    request_logger.info(
        "analysis_results_stored",
        comfort_score=current.comfort_score,
        recommended_comfort=recommended.comfort_score,
    )


def _load_request(submission: Any, language: LanguageCode) -> AnalysisRequest:
    if submission.request is not None:
        _remember_draft_request(submission.request)
        return submission.request
    try:
        request = build_request_from_session(language)
        _remember_draft_request(request)
        return request
    except Exception:
        draft_request = _draft_request_from_state()
        if draft_request is not None:
            return draft_request
        current = cast(ScenarioResult | None, st.session_state.get("current_result"))
        if current is not None:
            return current.request
        raise


def _scene_from_request(request: AnalysisRequest):
    scene = build_scene_state(request)
    scene.selected_element = st.session_state.get("editor_selected_element", "desk")
    scene.commit_version = int(st.session_state.get("editor_commit_version", 0))
    return scene


def _recommended_scene_for_editor() -> SceneState | None:
    recommended_result = cast(
        ScenarioResult | None, st.session_state.get("recommended_result")
    )
    if recommended_result is None:
        return None
    return build_scene_state(recommended_result.request)


def _apply_scene_commit(
    scene, base_request: AnalysisRequest, use_live_weather: bool
) -> AnalysisRequest:
    updated_request = scene_to_request(scene, base_request)
    _remember_draft_request(updated_request)
    queue_request_sync(updated_request)
    st.session_state["editor_selected_element"] = scene.selected_element
    st.session_state["editor_commit_version"] = scene.commit_version
    st.rerun()
    return updated_request


def _handle_editor_event(
    base_request: AnalysisRequest,
    use_live_weather: bool,
    language: LanguageCode,
) -> tuple[AnalysisRequest, bool]:
    scene = _scene_from_request(base_request)
    active_request = base_request
    fallback_mode = False
    session_logger = _session_logger().bind(editor_commit_version=scene.commit_version)

    try:
        payload = render_floor_plan_editor(
            scene,
            key="floor_plan_editor",
            height=520,
            language=language,
            recommended_scene=_recommended_scene_for_editor(),
        )
    except Exception as exc:
        fallback_mode = True
        st.warning(
            "No he podido montar el editor interactivo. Usa el ajuste numérico avanzado de la barra lateral."
            if language == "es"
            else "I could not load the interactive editor. Use the advanced numeric controls in the sidebar."
        )
        st.caption(
            f"Detalle técnico: {exc}"
            if language == "es"
            else f"Technical detail: {exc}"
        )
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
    if returned_scene.commit_version > int(
        st.session_state.get("editor_commit_version", 0)
    ):
        _session_logger().info(
            "editor_commit_received",
            editor_commit_version=returned_scene.commit_version,
            selected_element=returned_scene.selected_element,
        )
        active_request = _apply_scene_commit(
            returned_scene, base_request, use_live_weather
        )
    return active_request, fallback_mode


def _apply_quick_adjustment(
    base_request: AnalysisRequest, use_live_weather: bool, delta: EditorDelta
) -> AnalysisRequest:
    scene = _scene_from_request(base_request)
    updated_scene = apply_editor_delta(scene, delta)
    return _apply_scene_commit(updated_scene, base_request, use_live_weather)


def _apply_request_update(
    request: AnalysisRequest, use_live_weather: bool
) -> AnalysisRequest:
    _remember_draft_request(request)
    queue_request_sync(request)
    st.rerun()
    return request


def _trigger_manual_analysis(
    request: AnalysisRequest, use_live_weather: bool
) -> AnalysisRequest:
    _store_results(request, use_live_weather)
    st.rerun()
    return request


def _selected_element_summary(
    request: AnalysisRequest, language: LanguageCode
) -> dict[str, str]:
    selected = st.session_state.get("editor_selected_element", "desk")
    if selected == "room":
        return {
            "title": "Habitación" if language == "es" else "Room",
            "line_1": (
                f"Ancho: {request.room.width_m:.2f} m"
                if language == "es"
                else f"Width: {request.room.width_m:.2f} m"
            ),
            "line_2": (
                f"Fondo: {request.room.depth_m:.2f} m"
                if language == "es"
                else f"Depth: {request.room.depth_m:.2f} m"
            ),
            "line_3": (
                f"Altura libre: {request.room.ceiling_height_m:.2f} m"
                if language == "es"
                else f"Clear height: {request.room.ceiling_height_m:.2f} m"
            ),
        }
    if selected == "window":
        return {
            "title": "Ventana principal" if language == "es" else "Main window",
            "line_1": (
                f"Pared: {int(request.window.orientation_deg):.0f}°"
                if language == "es"
                else f"Wall: {int(request.window.orientation_deg):.0f}°"
            ),
            "line_2": (
                f"Ancho: {request.window.width_m:.2f} m"
                if language == "es"
                else f"Width: {request.window.width_m:.2f} m"
            ),
            "line_3": (
                f"Centro: {request.window.center_ratio:.2f} del tramo"
                if language == "es"
                else f"Center: {request.window.center_ratio:.2f} of the span"
            ),
        }
    if selected == "monitor":
        return {
            "title": "Monitor",
            "line_1": (
                f"Posición: ({request.monitor.x_m:.2f}, {request.monitor.y_m:.2f}) m"
                if language == "es"
                else f"Position: ({request.monitor.x_m:.2f}, {request.monitor.y_m:.2f}) m"
            ),
            "line_2": (
                f"Orientación: {request.monitor.orientation_deg:.0f}°"
                if language == "es"
                else f"Orientation: {request.monitor.orientation_deg:.0f}°"
            ),
            "line_3": (
                f"Diagonal: {request.monitor.diagonal_in:.0f} in"
                if language == "es"
                else f"Diagonal: {request.monitor.diagonal_in:.0f} in"
            ),
        }
    return {
        "title": "Mesa" if language == "es" else "Desk",
        "line_1": (
            f"Posición: ({request.desk.x_m:.2f}, {request.desk.y_m:.2f}) m"
            if language == "es"
            else f"Position: ({request.desk.x_m:.2f}, {request.desk.y_m:.2f}) m"
        ),
        "line_2": (
            f"Orientación: {request.desk.orientation_deg:.0f}°"
            if language == "es"
            else f"Orientation: {request.desk.orientation_deg:.0f}°"
        ),
        "line_3": (
            f"Tamaño: {request.desk.width_m:.2f} x {request.desk.depth_m:.2f} m"
            if language == "es"
            else f"Size: {request.desk.width_m:.2f} x {request.desk.depth_m:.2f} m"
        ),
    }


def _render_inspector(
    base_request: AnalysisRequest, use_live_weather: bool, language: LanguageCode
) -> AnalysisRequest:
    summary = _selected_element_summary(base_request, language)
    st.subheader("Inspector")
    st.caption(
        "Selecciona un elemento en el plano para ver su ficha y hacer microajustes."
        if language == "es"
        else "Select an element on the plan to inspect it and make small adjustments."
    )
    st.markdown(f"**{summary['title']}**")
    st.write(summary["line_1"])
    st.write(summary["line_2"])
    st.write(summary["line_3"])

    selected: SceneElementKind = st.session_state.get("editor_selected_element", "desk")
    if selected in {"desk", "monitor"}:
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Girar -15°" if language == "es" else "Rotate -15°",
                key=f"rotate_left_{selected}",
                width="stretch",
            ):
                return _apply_quick_adjustment(
                    base_request,
                    use_live_weather,
                    EditorDelta(
                        target=selected,
                        action="rotate",
                        rotation_deg=-15.0,
                        preview=False,
                    ),
                )
        with col2:
            if st.button(
                "Girar +15°" if language == "es" else "Rotate +15°",
                key=f"rotate_right_{selected}",
                width="stretch",
            ):
                return _apply_quick_adjustment(
                    base_request,
                    use_live_weather,
                    EditorDelta(
                        target=selected,
                        action="rotate",
                        rotation_deg=15.0,
                        preview=False,
                    ),
                )

    if selected == "window":
        if st.button(
            "Centrar ventana" if language == "es" else "Center window",
            key="center_window",
            width="stretch",
        ):
            centered_request = replace(
                base_request,
                window=replace(base_request.window, center_ratio=0.5),
            )
            return _apply_request_update(centered_request, use_live_weather)

    if selected == "monitor":
        if st.button(
            "Centrar monitor en la mesa"
            if language == "es"
            else "Center monitor on the desk",
            key="center_monitor",
            width="stretch",
        ):
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

    if st.button(
        translate("sidebar.run_analysis", language),
        key="inspector_run_analysis",
        width="stretch",
    ):
        return _trigger_manual_analysis(base_request, use_live_weather)

    return base_request


def _localized_alerts(current: ScenarioResult, language: LanguageCode) -> list[str]:
    alerts: list[str] = []
    if current.diagnosis.high_glare_windows:
        alerts.append(
            translate(
                "summary.glare_window",
                language,
                window_list=", ".join(
                    f"{window.start_time_label}-{window.end_time_label}"
                    for window in current.diagnosis.high_glare_windows
                ),
            )
        )
    if current.diagnosis.high_heat_windows:
        alerts.append(
            translate(
                "summary.heat_window",
                language,
                window_list=", ".join(
                    f"{window.start_time_label}-{window.end_time_label}"
                    for window in current.diagnosis.high_heat_windows
                ),
            )
        )
    return alerts


def _render_summary(
    current: ScenarioResult, recommended: ScenarioResult, language: LanguageCode
) -> None:
    delta = round(recommended.comfort_score - current.comfort_score, 1)
    recommendation_lines, _recommendation_reason = _localized_recommendation_lines(
        current, recommended, language
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric(
        translate("summary.metric.comfort", language),
        f"{current.comfort_score:.1f}/100",
        delta=f"+{delta:.1f}",
    )
    metric_cols[1].metric(
        translate("summary.metric.glare", language),
        f"{current.glare_score:.1f}",
        delta=f"{current.glare_score - recommended.glare_score:.1f}",
    )
    metric_cols[2].metric(
        translate("summary.metric.heat", language),
        f"{current.heat_score:.1f}",
        delta=f"{current.heat_score - recommended.heat_score:.1f}",
    )
    metric_cols[3].metric(
        translate("summary.metric.ergonomics", language),
        f"{current.ergonomic_score:.1f}",
        delta=f"{current.ergonomic_score - recommended.ergonomic_score:.1f}",
    )

    for alert in _localized_alerts(current, language):
        st.warning(alert)

    if recommendation_lines:
        st.success(recommendation_lines[0])

    weather_text = translate(
        "summary.weather.forecast"
        if current.weather_context.mode == "forecast"
        else "summary.weather.theoretical",
        language,
    )
    st.caption(
        translate(
            "summary.weather.caption",
            language,
            location=st.session_state.get(
                "location_label", current.request.location.label
            ),
            weather_mode=weather_text,
        )
    )


def _render_pending_notice(
    request: AnalysisRequest,
    *,
    use_live_weather: bool,
    language: LanguageCode,
) -> None:
    if not _has_pending_analysis(request, use_live_weather=use_live_weather):
        return
    st.warning(translate("summary.pending_changes", language))


def _render_diagnosis_panel(
    current: ScenarioResult, recommended: ScenarioResult, language: LanguageCode
) -> None:
    panel = _diagnosis_panel_data(current, recommended, language)
    st.subheader(translate("summary.whats_happening", language))
    st.info(panel["what_is_happening"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{translate('summary.good_hours', language)}**")
        st.write(panel["good_hours"])
        st.markdown(f"**{translate('summary.first_adjustment', language)}**")
        st.write(panel["first_adjustment"])
    with col2:
        st.markdown(f"**{translate('summary.conflict_hours', language)}**")
        st.write(panel["conflict_hours"])
        st.markdown(f"**{translate('summary.confidence', language)}**")
        st.write(panel["confidence"])


def _render_main_panels(
    current: ScenarioResult, recommended: ScenarioResult, language: LanguageCode
) -> None:
    plotly_config = _static_plotly_config()
    recommendation_lines, _recommendation_reason = _localized_recommendation_lines(
        current, recommended, language
    )
    top_left, top_right = st.columns((1.6, 1.0))
    with top_left:
        st.subheader(translate("summary.section.timeline", language))
        st.plotly_chart(
            timeline_chart(current, language),
            width="stretch",
            config=plotly_config,
        )
    with top_right:
        st.subheader(translate("summary.section.recommendation", language))
        st.plotly_chart(
            score_comparison_chart(current, recommended, language),
            width="stretch",
            config=plotly_config,
        )
        st.markdown(f"**{translate('summary.section.actions', language)}**")
        for recommendation in recommendation_lines:
            st.write(f"- {recommendation}")

    bottom_left, bottom_right = st.columns((1.3, 1.3))
    with bottom_left:
        st.subheader(translate("summary.section.plan", language))
        st.plotly_chart(
            room_plan_chart(current, recommended, language),
            width="stretch",
            config=plotly_config,
        )
    with bottom_right:
        if current.seasonal_summary:
            st.subheader(translate("summary.section.seasonal", language))
            st.plotly_chart(
                seasonal_heatmap(current, language),
                width="stretch",
                config=plotly_config,
            )
            best, worst = _best_and_worst_season(current)
            if best and worst:
                st.caption(
                    translate(
                        "summary.season.best_worst",
                        language,
                        best_label=translate_season(best[0], language),
                        best_score=best[1],
                        worst_label=translate_season(worst[0], language),
                        worst_score=worst[1],
                    )
                )


def _render_comparison(
    current: ScenarioResult, recommended: ScenarioResult, language: LanguageCode
) -> None:
    st.subheader(translate("summary.section.compare", language))
    comparison_cols = st.columns(2)
    with comparison_cols[0]:
        st.markdown(f"**{translate('summary.config.current', language)}**")
        st.write(
            "- "
            + translate(
                "summary.config.desk_position",
                language,
                x=current.request.desk.x_m,
                y=current.request.desk.y_m,
            )
        )
        st.write(
            "- "
            + translate(
                "summary.config.desk_orientation",
                language,
                degrees=current.request.desk.orientation_deg,
            )
        )
        st.write(
            "- "
            + translate(
                "summary.config.monitor_orientation",
                language,
                degrees=current.request.monitor.orientation_deg,
            )
        )
    with comparison_cols[1]:
        st.markdown(f"**{translate('summary.config.recommended', language)}**")
        st.write(
            "- "
            + translate(
                "summary.config.desk_position",
                language,
                x=recommended.request.desk.x_m,
                y=recommended.request.desk.y_m,
            )
        )
        st.write(
            "- "
            + translate(
                "summary.config.desk_orientation",
                language,
                degrees=recommended.request.desk.orientation_deg,
            )
        )
        st.write(
            "- "
            + translate(
                "summary.config.monitor_orientation",
                language,
                degrees=recommended.request.monitor.orientation_deg,
            )
        )


def _render_model_notes(language: LanguageCode) -> None:
    with st.expander(translate("summary.model_notes", language), expanded=False):
        st.markdown(
            "\n".join(
                [
                    f"- {translate('summary.model_note.1', language)}",
                    f"- {translate('summary.model_note.2', language)}",
                    f"- {translate('summary.model_note.3', language)}",
                    f"- {translate('summary.model_note.4', language)}",
                ]
            )
        )


def main() -> None:
    setup_logging()
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    language = _render_language_switch()
    _render_header(language)
    submission = render_sidebar(language)
    use_live_weather = bool(st.session_state.get("use_live_weather", False))

    if submission.error:
        st.error(submission.error)

    request = _load_request(submission, language)

    if submission.run_requested and submission.request is not None:
        _store_results(request, submission.use_live_weather)

    editor_cols = st.columns((1.8, 1.0))
    with editor_cols[0]:
        st.subheader("Plano editable" if language == "es" else "Editable floor plan")
        request, editor_fallback = _handle_editor_event(
            request, use_live_weather, language
        )
    with editor_cols[1]:
        request = _render_inspector(request, use_live_weather, language)

    current_result = st.session_state.get("current_result")
    recommended_result = st.session_state.get("recommended_result")

    _render_pending_notice(
        request, use_live_weather=use_live_weather, language=language
    )

    if current_result and recommended_result:
        st.divider()
        _render_summary(current_result, recommended_result, language)
        st.divider()
        _render_diagnosis_panel(current_result, recommended_result, language)
        st.divider()
        _render_main_panels(current_result, recommended_result, language)
        st.divider()
        _render_comparison(current_result, recommended_result, language)
        if editor_fallback:
            st.info(translate("summary.fallback_editor", language))
        _render_model_notes(language)
    else:
        st.info(translate("summary.empty_state", language))


if __name__ == "__main__":
    main()
