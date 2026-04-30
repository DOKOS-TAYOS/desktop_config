from __future__ import annotations


from app.domain.models import (
    Recommendation,
    ScenarioDiagnosis,
    ScenarioResult,
    SeasonalSummary,
    TimeWindowSummary,
)
from app.services.weather import build_theoretical_weather_context
from app.ui.charts import timeline_chart
from streamlit_app import _best_and_worst_season, _diagnosis_panel_data


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
