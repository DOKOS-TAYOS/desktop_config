from __future__ import annotations

import logging
from dataclasses import replace
from time import perf_counter

from app.domain.models import AnalysisRequest, Recommendation, ScenarioResult
from app.domain.validation import ValidationError, validate_request
from app.services.analysis import analyze_scenario
from app.utils.logging_utils import env_flag, get_logger, log_event


logger = get_logger(__name__)


def _candidate_offsets() -> list[tuple[float, float]]:
    return [
        (0.0, 0.0),
        (0.25, 0.0),
        (-0.25, 0.0),
        (0.0, 0.25),
        (0.0, -0.25),
        (0.4, 0.0),
        (-0.4, 0.0),
    ]


def _candidate_rotations() -> list[int]:
    return [-30, -15, 0, 15, 30]


def _candidate_monitor_rotations() -> list[int]:
    return [-15, 0, 15]


def _movement_message(delta_x: float, delta_y: float) -> str | None:
    moves: list[str] = []
    if abs(delta_x) >= 0.05:
        horizontal = "este" if delta_x > 0 else "oeste"
        moves.append(
            f"desplaza el escritorio {abs(delta_x) * 100:.0f} cm hacia el {horizontal}"
        )
    if abs(delta_y) >= 0.05:
        vertical = "norte" if delta_y > 0 else "sur"
        moves.append(f"muevelo {abs(delta_y) * 100:.0f} cm hacia el {vertical}")
    return " y ".join(moves) if moves else None


def _rotation_message(delta_deg: float) -> str | None:
    if abs(delta_deg) < 1:
        return None
    direction = "a la derecha" if delta_deg > 0 else "a la izquierda"
    return f"gira la mesa {abs(delta_deg):.0f}° {direction}"


def _risk_value(result: ScenarioResult, risk_name: str) -> float:
    if risk_name == "glare":
        return result.glare_score
    if risk_name == "heat":
        return result.heat_score
    if risk_name == "ergonomics":
        return result.ergonomic_score
    return max(result.glare_score, result.heat_score, result.ergonomic_score)


def _is_material_improvement(
    candidate: ScenarioResult, baseline: ScenarioResult
) -> bool:
    comfort_gain = candidate.comfort_score - baseline.comfort_score
    dominant_risk = (
        baseline.diagnosis.dominant_risk
        if baseline.diagnosis is not None
        else "balanced"
    )
    dominant_risk_improvement = _risk_value(baseline, dominant_risk) - _risk_value(
        candidate, dominant_risk
    )
    return comfort_gain > 0.2 and (
        dominant_risk == "balanced" or dominant_risk_improvement >= 2.0
    )


def recommend_variant(
    request: AnalysisRequest,
    baseline: ScenarioResult | None = None,
) -> ScenarioResult:
    started_at = perf_counter()
    validate_request(request)
    baseline = baseline or analyze_scenario(request)
    log_event(
        logger,
        logging.INFO,
        "recommendation_started",
        baseline_comfort=baseline.comfort_score,
        location_label=request.location.label,
    )
    best_result = baseline

    for delta_x, delta_y in _candidate_offsets():
        for desk_rotation in _candidate_rotations():
            for monitor_rotation in _candidate_monitor_rotations():
                candidate_request = replace(
                    request,
                    desk=replace(
                        request.desk,
                        x_m=round(request.desk.x_m + delta_x, 2),
                        y_m=round(request.desk.y_m + delta_y, 2),
                        orientation_deg=(request.desk.orientation_deg + desk_rotation)
                        % 360,
                    ),
                    monitor=replace(
                        request.monitor,
                        x_m=round(request.monitor.x_m + delta_x, 2),
                        y_m=round(request.monitor.y_m + delta_y, 2),
                        orientation_deg=(
                            request.monitor.orientation_deg
                            + desk_rotation
                            + monitor_rotation
                        )
                        % 360,
                    ),
                )
                try:
                    validate_request(candidate_request)
                except ValidationError:
                    continue

                candidate_result = analyze_scenario(
                    replace(candidate_request, include_seasonal_summary=False),
                    weather_context=baseline.weather_context,
                )
                if _is_material_improvement(candidate_result, baseline) and (
                    candidate_result.comfort_score > best_result.comfort_score + 0.2
                ):
                    if env_flag("SUNSETUP_DEBUG_CANDIDATES") and logger.isEnabledFor(
                        logging.DEBUG
                    ):
                        log_event(
                            logger,
                            logging.DEBUG,
                            "recommendation_candidate_improved",
                            candidate_comfort=candidate_result.comfort_score,
                            desk_orientation=candidate_request.desk.orientation_deg,
                            desk_x_m=candidate_request.desk.x_m,
                            desk_y_m=candidate_request.desk.y_m,
                            monitor_orientation=candidate_request.monitor.orientation_deg,
                        )
                    best_result = candidate_result

    delta_score = round(best_result.comfort_score - baseline.comfort_score, 1)
    materially_better = (
        best_result.request != baseline.request
        and _is_material_improvement(best_result, baseline)
    )
    movement_message = _movement_message(
        best_result.request.desk.x_m - request.desk.x_m,
        best_result.request.desk.y_m - request.desk.y_m,
    )
    desk_delta = (
        (best_result.request.desk.orientation_deg - request.desk.orientation_deg + 540)
        % 360
    ) - 180
    rotation_message = _rotation_message(desk_delta)
    monitor_delta = (
        (
            best_result.request.monitor.orientation_deg
            - request.monitor.orientation_deg
            + 540
        )
        % 360
    ) - 180
    monitor_message = (
        f"ajusta el monitor {abs(monitor_delta):.0f}° {'a la derecha' if monitor_delta > 0 else 'a la izquierda'}"
        if abs(monitor_delta) >= 1
        else None
    )
    recommendation_messages = [
        message
        for message in (movement_message, rotation_message, monitor_message)
        if message
    ]
    recommendation_reason = (
        "Reduce el riesgo dominante y mejora el confort total."
        if materially_better
        else "La mejor variante encontrada no reduce el riesgo dominante de forma material."
    )
    if not materially_better or not recommendation_messages:
        recommendation_messages = [
            "La configuración actual ya está bastante equilibrada para este modelo"
        ]
        delta_score = 0.0
        best_result = baseline

    if (
        best_result.request.include_seasonal_summary is False
        and request.include_seasonal_summary
    ):
        best_result = analyze_scenario(
            replace(best_result.request, include_seasonal_summary=True),
            weather_context=baseline.weather_context,
        )
        delta_score = round(best_result.comfort_score - baseline.comfort_score, 1)

    best_result.recommendations = [
        Recommendation(
            title="Configuración recomendada",
            message=f"{message}.",
            delta_score=delta_score,
            reason=recommendation_reason,
        )
        for message in recommendation_messages
    ]
    best_result.alerts = [
        *best_result.alerts,
        f"Mejora estimada del confort: +{delta_score:.1f} puntos.",
    ]
    log_event(
        logger,
        logging.INFO,
        "recommendation_completed",
        delta_score=delta_score,
        duration_ms=round((perf_counter() - started_at) * 1000, 1),
        recommended_comfort=best_result.comfort_score,
        recommended_desk_orientation=best_result.request.desk.orientation_deg,
        recommended_monitor_orientation=best_result.request.monitor.orientation_deg,
    )
    return best_result
