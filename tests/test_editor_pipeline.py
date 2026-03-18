from __future__ import annotations

from types import SimpleNamespace

from app.services.analysis import analyze_scenario
from app.services.recommendations import recommend_variant
from app.ui.editor_state import EditorDelta, apply_editor_delta, build_scene_state, scene_to_request
from app.ui.forms import apply_pending_session_patch, queue_request_sync, request_to_session_patch


def test_request_to_session_patch_reflects_editor_changes(base_request):
    scene = build_scene_state(base_request)
    moved = apply_editor_delta(
        scene,
        EditorDelta(target="desk", action="translate", dx_m=0.3, dy_m=0.2, preview=False),
    )
    updated_request = scene_to_request(moved, base_request)

    patch = request_to_session_patch(updated_request)

    assert patch["desk_x_m"] == updated_request.desk.x_m
    assert patch["desk_y_m"] == updated_request.desk.y_m
    assert patch["monitor_x_m"] == updated_request.monitor.x_m
    assert patch["monitor_y_m"] == updated_request.monitor.y_m


def test_queue_request_sync_defers_widget_patch_until_next_run(base_request, monkeypatch):
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr("app.ui.forms.st", fake_streamlit)

    queue_request_sync(base_request)

    assert "_pending_form_patch" in fake_streamlit.session_state
    assert "desk_x_m" not in fake_streamlit.session_state

    apply_pending_session_patch()

    assert "_pending_form_patch" not in fake_streamlit.session_state
    assert fake_streamlit.session_state["desk_x_m"] == base_request.desk.x_m
    assert fake_streamlit.session_state["analysis_date"] == base_request.analysis_date


def test_scene_edit_keeps_analysis_and_recommendation_pipeline_working(base_request):
    scene = build_scene_state(base_request)
    moved = apply_editor_delta(
        scene,
        EditorDelta(target="desk", action="rotate", rotation_deg=30.0, preview=False),
    )
    updated_request = scene_to_request(moved, base_request)

    current = analyze_scenario(updated_request)
    recommended = recommend_variant(updated_request, current)

    assert current.comfort_score >= 0
    assert recommended.comfort_score >= current.comfort_score
