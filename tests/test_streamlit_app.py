from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from app.domain.models import (
    Recommendation,
    ScenarioDiagnosis,
    ScenarioResult,
    SeasonalSummary,
    TimeWindowSummary,
)
from app.domain.validation import ValidationError
import streamlit as st

from app.services.weather import build_theoretical_weather_context
from app.ui.charts import room_plan_chart, timeline_chart
from app.ui.i18n import translate
from streamlit_app import (
    _cached_results_for_request,
    _best_and_worst_season,
    _current_language,
    _diagnosis_panel_data,
    _has_pending_analysis,
    _load_request,
    _request_cache_key,
    _recommended_scene_for_editor,
    _static_plotly_config,
    _trigger_manual_analysis,
)


def test_best_and_worst_season_returns_expected_labels(base_request) -> None:
    result = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=20.0,
        heat_score=10.0,
        ergonomic_score=10.0,
        comfort_score=80.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[
            SeasonalSummary(
                season="invierno",
                morning_comfort=70.0,
                midday_comfort=72.0,
                afternoon_comfort=74.0,
            ),
            SeasonalSummary(
                season="verano",
                morning_comfort=55.0,
                midday_comfort=50.0,
                afternoon_comfort=45.0,
            ),
        ],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="balanced",
            primary_message="No hay un riesgo dominante claro.",
            confidence_message="Confianza moderada.",
            best_window=None,
            worst_window=None,
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )

    best, worst = _best_and_worst_season(result)

    assert best == ("invierno", 72.0)
    assert worst == ("verano", 50.0)


def test_diagnosis_panel_data_exposes_practical_messages(base_request) -> None:
    diagnosis = ScenarioDiagnosis(
        dominant_risk="glare",
        primary_message="El principal problema es el reflejo durante la tarde.",
        confidence_message="Confianza moderada: el clima se ha estimado con cielo despejado teórico.",
        best_window=TimeWindowSummary(
            label="Mañana",
            start_time_label="08:00",
            end_time_label="12:00",
            mean_comfort=82.0,
            peak_glare=18.0,
            peak_heat=10.0,
        ),
        worst_window=TimeWindowSummary(
            label="Tarde",
            start_time_label="16:00",
            end_time_label="20:00",
            mean_comfort=42.0,
            peak_glare=76.0,
            peak_heat=28.0,
        ),
        high_glare_windows=[
            TimeWindowSummary(
                label="16:00-18:00",
                start_time_label="16:00",
                end_time_label="18:00",
                mean_comfort=40.0,
                peak_glare=76.0,
                peak_heat=24.0,
            )
        ],
        high_heat_windows=[],
    )
    current = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=76.0,
        heat_score=28.0,
        ergonomic_score=12.0,
        comfort_score=43.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=diagnosis,
    )
    recommended = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=50.0,
        heat_score=20.0,
        ergonomic_score=12.0,
        comfort_score=57.0,
        alerts=[],
        recommendations=[
            Recommendation(
                title="Configuración recomendada",
                message="Gira la mesa 15° a la izquierda.",
                delta_score=14.0,
                reason="Reduce el reflejo en la franja más conflictiva.",
            )
        ],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=diagnosis,
    )

    panel = _diagnosis_panel_data(current, recommended)

    assert "reflejo" in panel["what_is_happening"].lower()
    assert "08:00-12:00" in panel["good_hours"]
    assert "16:00-20:00" in panel["conflict_hours"]
    assert "reduce el reflejo" in panel["first_adjustment"].lower()
    assert "confianza moderada" in panel["confidence"].lower()


def test_timeline_chart_uses_dark_background(base_request) -> None:
    result = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=76.0,
        heat_score=28.0,
        ergonomic_score=12.0,
        comfort_score=43.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="glare",
            primary_message="El principal problema es el reflejo durante la tarde.",
            confidence_message="Confianza moderada.",
            best_window=None,
            worst_window=None,
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )

    chart = timeline_chart(result)
    layout = chart.to_plotly_json().get("layout", {})
    paper_bgcolor = layout.get("paper_bgcolor")

    assert isinstance(layout, dict)
    assert isinstance(paper_bgcolor, str)
    assert paper_bgcolor.startswith("#")


def test_static_plotly_config_disables_interaction() -> None:
    config = _static_plotly_config()

    assert config == {
        "displayModeBar": False,
        "scrollZoom": False,
        "staticPlot": True,
    }


def test_translate_returns_spanish_and_english_values() -> None:
    assert translate("app.title", "es") == "SunSetup Planner"
    assert translate("header.subtitle", "en").startswith(
        "Decide whether your desk works better"
    )
    assert translate("sidebar.run_analysis", "en") == "Update analysis"
    assert translate("summary.whats_happening", "en") == "What is happening"


def test_current_language_defaults_to_spanish() -> None:
    st.session_state.clear()

    assert _current_language() == "es"


def test_cached_results_for_request_reuses_previous_computation(
    base_request, monkeypatch
) -> None:
    st.session_state.clear()
    calls = {"analysis": 0, "recommendation": 0}
    current = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=10.0,
        heat_score=10.0,
        ergonomic_score=10.0,
        comfort_score=80.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="balanced",
            primary_message="Equilibrado.",
            confidence_message="Confianza moderada.",
            best_window=None,
            worst_window=None,
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )
    recommended = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=8.0,
        heat_score=9.0,
        ergonomic_score=10.0,
        comfort_score=83.0,
        alerts=[],
        recommendations=[
            Recommendation(
                title="Configuración recomendada",
                message="Mueve la mesa 10 cm.",
                delta_score=3.0,
                reason="Mejora ligera.",
            )
        ],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=current.diagnosis,
    )

    def fake_analyze_scenario(request, *, include_live_weather=False):
        calls["analysis"] += 1
        return current

    def fake_recommend_variant(request, baseline):
        calls["recommendation"] += 1
        return recommended

    monkeypatch.setattr("streamlit_app.analyze_scenario", fake_analyze_scenario)
    monkeypatch.setattr("streamlit_app.recommend_variant", fake_recommend_variant)

    first_current, first_recommended = _cached_results_for_request(base_request, False)
    second_current, second_recommended = _cached_results_for_request(
        base_request, False
    )

    assert calls == {"analysis": 1, "recommendation": 1}
    assert first_current.comfort_score == second_current.comfort_score
    assert first_recommended.comfort_score == second_recommended.comfort_score
    assert first_current is not second_current
    assert first_recommended is not second_recommended


def test_has_pending_analysis_compares_request_with_last_analyzed_state(
    base_request,
) -> None:
    st.session_state.clear()

    assert _has_pending_analysis(base_request, use_live_weather=False) is False

    st.session_state["last_analyzed_request_key"] = _request_cache_key(
        base_request, False
    )
    assert _has_pending_analysis(base_request, use_live_weather=False) is False
    assert _has_pending_analysis(base_request, use_live_weather=True) is True


def test_room_plan_chart_places_legend_above_the_plot_area(base_request) -> None:
    current = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=20.0,
        heat_score=10.0,
        ergonomic_score=10.0,
        comfort_score=80.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="balanced",
            primary_message="Equilibrado.",
            confidence_message="Confianza moderada.",
            best_window=None,
            worst_window=None,
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )

    chart = room_plan_chart(current, current)
    layout = chart.to_plotly_json()["layout"]
    legend = layout["legend"]
    margin = layout["margin"]

    assert legend["y"] >= 1.16
    assert margin["t"] >= 56


def test_recommended_scene_for_editor_uses_last_recommended_request(
    base_request,
) -> None:
    st.session_state.clear()
    recommended = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=20.0,
        heat_score=10.0,
        ergonomic_score=10.0,
        comfort_score=80.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="balanced",
            primary_message="Equilibrado.",
            confidence_message="Confianza moderada.",
            best_window=None,
            worst_window=None,
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )
    st.session_state["recommended_result"] = recommended

    scene = _recommended_scene_for_editor()

    assert scene is not None
    assert scene.elements["desk"].x_m == base_request.desk.x_m


def test_trigger_manual_analysis_stores_results_and_requests_rerun(
    base_request, monkeypatch
) -> None:
    calls = {"stored": 0, "rerun": 0}

    def fake_store_results(request, use_live_weather):
        assert request == base_request
        assert use_live_weather is True
        calls["stored"] += 1

    def fake_rerun():
        calls["rerun"] += 1

    monkeypatch.setattr("streamlit_app._store_results", fake_store_results)
    monkeypatch.setattr("streamlit_app.st.rerun", fake_rerun)

    returned_request = _trigger_manual_analysis(base_request, use_live_weather=True)

    assert returned_request == base_request
    assert calls == {"stored": 1, "rerun": 1}


def test_load_request_prefers_last_draft_over_last_analysis_on_validation_failure(
    base_request, monkeypatch
) -> None:
    st.session_state.clear()
    analyzed_request = SimpleNamespace(request=base_request)
    moved_draft = SimpleNamespace(
        request=replace(
            base_request,
            desk=replace(base_request.desk, x_m=base_request.desk.x_m + 0.35),
        )
    )
    st.session_state["draft_request"] = moved_draft.request
    st.session_state["current_result"] = analyzed_request

    def fail_build_request(_language):
        raise ValidationError("transient geometry")

    monkeypatch.setattr("streamlit_app.build_request_from_session", fail_build_request)

    loaded = _load_request(SimpleNamespace(request=None), "es")

    assert loaded == moved_draft.request
