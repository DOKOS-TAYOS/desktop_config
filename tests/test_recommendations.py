from __future__ import annotations

from dataclasses import replace

from app.domain.models import (
    Recommendation,
    ScenarioDiagnosis,
    ScenarioResult,
    TimeWindowSummary,
)
from app.domain.validation import validate_request
from app.services.analysis import analyze_scenario
from app.services.recommendations import recommend_variant
from app.services.weather import build_theoretical_weather_context


def test_recommend_variant_improves_bad_configuration(base_request):
    validate_request(base_request)
    baseline = analyze_scenario(base_request)
    recommended = recommend_variant(base_request, baseline)

    assert recommended.comfort_score > baseline.comfort_score
    assert 0 <= recommended.request.desk.x_m <= recommended.request.room.width_m
    assert 0 <= recommended.request.desk.y_m <= recommended.request.room.depth_m
    assert recommended.request.desk.orientation_deg % 15 == 0


def test_recommend_variant_does_not_claim_improvement_if_dominant_risk_gets_worse(
    base_request,
    monkeypatch,
):
    baseline = ScenarioResult(
        request=base_request,
        time_slots=[],
        glare_score=70.0,
        heat_score=15.0,
        ergonomic_score=10.0,
        comfort_score=62.0,
        alerts=[],
        recommendations=[],
        weather_context=build_theoretical_weather_context(
            base_request.location.timezone
        ),
        seasonal_summary=[],
        diagnosis=ScenarioDiagnosis(
            dominant_risk="glare",
            primary_message="El principal problema es el reflejo.",
            confidence_message="Confianza moderada.",
            best_window=TimeWindowSummary(
                label="Mañana",
                start_time_label="08:00",
                end_time_label="12:00",
                mean_comfort=75.0,
                peak_glare=25.0,
                peak_heat=10.0,
            ),
            worst_window=TimeWindowSummary(
                label="Tarde",
                start_time_label="16:00",
                end_time_label="20:00",
                mean_comfort=40.0,
                peak_glare=70.0,
                peak_heat=15.0,
            ),
            high_glare_windows=[],
            high_heat_windows=[],
        ),
    )

    def fake_analyze_scenario(
        request, weather_context=None, *, include_live_weather=False
    ):
        return replace(
            baseline,
            request=request,
            glare_score=78.0,
            comfort_score=63.5,
            diagnosis=replace(
                baseline.diagnosis,
                primary_message="El reflejo sigue siendo el problema principal.",
            ),
        )

    monkeypatch.setattr(
        "app.services.recommendations.analyze_scenario", fake_analyze_scenario
    )
    monkeypatch.setattr(
        "app.services.recommendations._candidate_offsets", lambda: [(0.25, 0.0)]
    )
    monkeypatch.setattr(
        "app.services.recommendations._candidate_rotations", lambda: [0]
    )
    monkeypatch.setattr(
        "app.services.recommendations._candidate_monitor_rotations", lambda: [0]
    )

    recommended = recommend_variant(base_request, baseline)

    assert recommended.request == baseline.request
    assert recommended.recommendations == [
        Recommendation(
            title="Configuración recomendada",
            message="La configuración actual ya está bastante equilibrada para este modelo.",
            delta_score=0.0,
            reason="La mejor variante encontrada no reduce el riesgo dominante de forma material.",
        )
    ]
