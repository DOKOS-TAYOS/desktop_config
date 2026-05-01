from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from time import perf_counter

from app.domain.models import AnalysisRequest, Recommendation, ScenarioResult
from app.domain.validation import ValidationError, validate_request
from app.services.analysis import analyze_scenario
from app.utils.logging_utils import env_flag, get_logger, log_event


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class VariantCandidate:
    request: AnalysisRequest
    result: ScenarioResult
    merit: float


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


def _coarse_desk_orientations() -> list[float]:
    return [float(angle_deg) for angle_deg in range(0, 360, 15)]


def _coarse_monitor_relative_adjustments() -> list[float]:
    return [float(angle_deg) for angle_deg in range(-30, 31, 15)]


def _refined_desk_orientations(center_deg: float) -> list[float]:
    return [float((center_deg + delta_deg) % 360) for delta_deg in range(-15, 16, 5)]


def _refined_monitor_relative_adjustments() -> list[float]:
    return [float(angle_deg) for angle_deg in range(-10, 11, 5)]


def _refined_offsets(center_x_m: float, center_y_m: float) -> list[tuple[float, float]]:
    offsets: list[tuple[float, float]] = []
    for delta_x_m in (-0.1, 0.0, 0.1):
        for delta_y_m in (-0.1, 0.0, 0.1):
            offsets.append(
                (round(center_x_m + delta_x_m, 2), round(center_y_m + delta_y_m, 2))
            )
    return offsets


def _signed_rotation_delta(target_deg: float, origin_deg: float) -> float:
    return ((target_deg - origin_deg + 540.0) % 360.0) - 180.0


def _base_monitor_relative_deg(request: AnalysisRequest) -> float:
    return _signed_rotation_delta(
        request.monitor.orientation_deg, request.desk.orientation_deg
    )


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


def _monitor_rotation_message(delta_deg: float) -> str | None:
    if abs(delta_deg) < 1:
        return None
    direction = "a la derecha" if delta_deg > 0 else "a la izquierda"
    return f"ajusta el monitor {abs(delta_deg):.0f}° {direction}"


def _risk_value(result: ScenarioResult, risk_name: str) -> float:
    if risk_name == "glare":
        return result.glare_score
    if risk_name == "heat":
        return result.heat_score
    if risk_name == "ergonomics":
        return result.ergonomic_score
    return max(result.glare_score, result.heat_score, result.ergonomic_score)


def _dominant_risk_improvement(
    candidate: ScenarioResult, baseline: ScenarioResult
) -> float:
    dominant_risk = baseline.diagnosis.dominant_risk
    if dominant_risk == "balanced":
        return 0.0
    return _risk_value(baseline, dominant_risk) - _risk_value(candidate, dominant_risk)


def _worst_window_improvement(
    candidate: ScenarioResult, baseline: ScenarioResult
) -> float:
    baseline_window = baseline.diagnosis.worst_window
    candidate_window = candidate.diagnosis.worst_window
    if baseline_window is None or candidate_window is None:
        return 0.0
    return candidate_window.mean_comfort - baseline_window.mean_comfort


def _high_risk_window_penalty(result: ScenarioResult) -> float:
    return float(
        len(result.diagnosis.high_glare_windows) * 2
        + len(result.diagnosis.high_heat_windows) * 2
    )


def _recommendation_merit(candidate: ScenarioResult, baseline: ScenarioResult) -> float:
    comfort_gain = candidate.comfort_score - baseline.comfort_score
    return round(
        candidate.comfort_score
        + comfort_gain * 1.8
        + _dominant_risk_improvement(candidate, baseline) * 1.5
        + _worst_window_improvement(candidate, baseline) * 0.35
        - _high_risk_window_penalty(candidate),
        3,
    )


def _is_material_improvement(
    candidate: ScenarioResult, baseline: ScenarioResult
) -> bool:
    comfort_gain = candidate.comfort_score - baseline.comfort_score
    dominant_risk = baseline.diagnosis.dominant_risk
    dominant_risk_improvement = _dominant_risk_improvement(candidate, baseline)
    return comfort_gain > 0.2 and (
        dominant_risk == "balanced" or dominant_risk_improvement >= 2.0
    )


def _build_candidate_request(
    request: AnalysisRequest,
    *,
    desk_x_m: float,
    desk_y_m: float,
    desk_orientation_deg: float,
    monitor_relative_deg: float,
) -> AnalysisRequest:
    monitor_orientation_deg = (desk_orientation_deg + monitor_relative_deg) % 360.0
    delta_x_m = desk_x_m - request.desk.x_m
    delta_y_m = desk_y_m - request.desk.y_m
    return replace(
        request,
        desk=replace(
            request.desk,
            x_m=round(desk_x_m, 2),
            y_m=round(desk_y_m, 2),
            orientation_deg=round(desk_orientation_deg % 360.0, 1),
        ),
        monitor=replace(
            request.monitor,
            x_m=round(request.monitor.x_m + delta_x_m, 2),
            y_m=round(request.monitor.y_m + delta_y_m, 2),
            orientation_deg=round(monitor_orientation_deg, 1),
        ),
    )


def _evaluation_time_step_minutes(request: AnalysisRequest) -> int:
    return max(request.time_step_minutes, 30)


def _evaluate_candidate(
    candidate_request: AnalysisRequest,
    baseline: ScenarioResult,
) -> VariantCandidate | None:
    try:
        validate_request(candidate_request)
    except ValidationError:
        return None

    candidate_result = analyze_scenario(
        replace(
            candidate_request,
            include_seasonal_summary=False,
            time_step_minutes=_evaluation_time_step_minutes(candidate_request),
        ),
        weather_context=baseline.weather_context,
    )
    return VariantCandidate(
        request=candidate_request,
        result=candidate_result,
        merit=_recommendation_merit(candidate_result, baseline),
    )


def _better_candidate(
    current_best: VariantCandidate | None,
    challenger: VariantCandidate | None,
) -> VariantCandidate | None:
    if challenger is None:
        return current_best
    if current_best is None:
        return challenger
    if challenger.merit > current_best.merit + 0.001:
        return challenger
    if abs(challenger.merit - current_best.merit) <= 0.001 and (
        challenger.result.comfort_score > current_best.result.comfort_score
    ):
        return challenger
    return current_best


def _search_best_candidate(
    request: AnalysisRequest, baseline: ScenarioResult
) -> VariantCandidate | None:
    base_monitor_relative_deg = _base_monitor_relative_deg(request)
    best_candidate: VariantCandidate | None = None

    for delta_x_m, delta_y_m in _candidate_offsets():
        desk_x_m = request.desk.x_m + delta_x_m
        desk_y_m = request.desk.y_m + delta_y_m
        for desk_orientation_deg in _coarse_desk_orientations():
            for monitor_adjustment_deg in _coarse_monitor_relative_adjustments():
                candidate_request = _build_candidate_request(
                    request,
                    desk_x_m=desk_x_m,
                    desk_y_m=desk_y_m,
                    desk_orientation_deg=desk_orientation_deg,
                    monitor_relative_deg=(
                        base_monitor_relative_deg + monitor_adjustment_deg
                    ),
                )
                best_candidate = _better_candidate(
                    best_candidate,
                    _evaluate_candidate(candidate_request, baseline),
                )

    if best_candidate is None:
        return None

    refined_seed = best_candidate
    refined_monitor_relative_deg = _signed_rotation_delta(
        refined_seed.request.monitor.orientation_deg,
        refined_seed.request.desk.orientation_deg,
    )
    for desk_x_m, desk_y_m in _refined_offsets(
        refined_seed.request.desk.x_m, refined_seed.request.desk.y_m
    ):
        for desk_orientation_deg in _refined_desk_orientations(
            refined_seed.request.desk.orientation_deg
        ):
            for monitor_adjustment_deg in _refined_monitor_relative_adjustments():
                candidate_request = _build_candidate_request(
                    request,
                    desk_x_m=desk_x_m,
                    desk_y_m=desk_y_m,
                    desk_orientation_deg=desk_orientation_deg,
                    monitor_relative_deg=(
                        refined_monitor_relative_deg + monitor_adjustment_deg
                    ),
                )
                best_candidate = _better_candidate(
                    best_candidate,
                    _evaluate_candidate(candidate_request, baseline),
                )

    return best_candidate


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
    best_candidate = _search_best_candidate(request, baseline)
    if best_candidate is None or best_candidate.request == baseline.request:
        best_result = baseline
    else:
        best_result = analyze_scenario(
            replace(
                best_candidate.request,
                include_seasonal_summary=request.include_seasonal_summary,
                time_step_minutes=request.time_step_minutes,
            ),
            weather_context=baseline.weather_context,
        )

    if (
        best_candidate is not None
        and env_flag("SUNSETUP_DEBUG_CANDIDATES")
        and logger.isEnabledFor(logging.DEBUG)
    ):
        log_event(
            logger,
            logging.DEBUG,
            "recommendation_candidate_improved",
            candidate_comfort=best_candidate.result.comfort_score,
            desk_orientation=best_candidate.request.desk.orientation_deg,
            desk_x_m=best_candidate.request.desk.x_m,
            desk_y_m=best_candidate.request.desk.y_m,
            monitor_orientation=best_candidate.request.monitor.orientation_deg,
        )

    delta_score = round(best_result.comfort_score - baseline.comfort_score, 1)
    materially_better = (
        best_result.request != baseline.request
        and _is_material_improvement(best_result, baseline)
    )
    movement_message = _movement_message(
        best_result.request.desk.x_m - request.desk.x_m,
        best_result.request.desk.y_m - request.desk.y_m,
    )
    desk_delta = _signed_rotation_delta(
        best_result.request.desk.orientation_deg, request.desk.orientation_deg
    )
    rotation_message = _rotation_message(desk_delta)
    monitor_delta = _signed_rotation_delta(
        best_result.request.monitor.orientation_deg, request.monitor.orientation_deg
    )
    monitor_message = _monitor_rotation_message(monitor_delta)
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
