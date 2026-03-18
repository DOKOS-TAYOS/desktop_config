from __future__ import annotations

from app.domain.validation import validate_request
from app.services.analysis import analyze_scenario
from app.services.recommendations import recommend_variant


def test_recommend_variant_improves_bad_configuration(base_request):
    validate_request(base_request)
    baseline = analyze_scenario(base_request)
    recommended = recommend_variant(base_request, baseline)

    assert recommended.comfort_score > baseline.comfort_score
    assert 0 <= recommended.request.desk.x_m <= recommended.request.room.width_m
    assert 0 <= recommended.request.desk.y_m <= recommended.request.room.depth_m
    assert recommended.request.desk.orientation_deg % 15 == 0
