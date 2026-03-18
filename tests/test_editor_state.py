from __future__ import annotations

import pytest

from app.domain.validation import validate_request
from app.ui.editor_state import (
    EditorDelta,
    apply_editor_delta,
    build_scene_state,
    scene_to_request,
)


def test_scene_roundtrip_preserves_request_geometry(base_request):
    scene = build_scene_state(base_request)

    roundtrip = scene_to_request(scene, base_request)

    assert roundtrip.room.width_m == pytest.approx(base_request.room.width_m)
    assert roundtrip.room.depth_m == pytest.approx(base_request.room.depth_m)
    assert roundtrip.window.orientation_deg == pytest.approx(base_request.window.orientation_deg)
    assert roundtrip.window.width_m == pytest.approx(base_request.window.width_m)
    assert roundtrip.desk.x_m == pytest.approx(base_request.desk.x_m)
    assert roundtrip.desk.y_m == pytest.approx(base_request.desk.y_m)
    assert roundtrip.monitor.x_m == pytest.approx(base_request.monitor.x_m)
    assert roundtrip.monitor.y_m == pytest.approx(base_request.monitor.y_m)


def test_window_translate_clamps_to_wall_span(base_request):
    scene = build_scene_state(base_request)

    moved = apply_editor_delta(
        scene,
        EditorDelta(target="window", action="translate", dx_m=99.0, dy_m=99.0, preview=False),
    )
    updated_request = scene_to_request(moved, base_request)

    assert 0.0 <= updated_request.window.center_ratio <= 1.0
    half_width = updated_request.window.width_m / 2
    wall_span = updated_request.room.depth_m
    center_along_wall = updated_request.window.center_ratio * wall_span
    assert half_width <= center_along_wall <= wall_span - half_width


def test_desk_translate_stays_inside_room_and_keeps_monitor_valid(base_request):
    scene = build_scene_state(base_request)

    moved = apply_editor_delta(
        scene,
        EditorDelta(target="desk", action="translate", dx_m=50.0, dy_m=50.0, preview=False),
    )
    updated_request = scene_to_request(moved, base_request)

    validate_request(updated_request)


def test_rotation_snaps_to_15_degree_increment(base_request):
    scene = build_scene_state(base_request)

    rotated = apply_editor_delta(
        scene,
        EditorDelta(target="desk", action="rotate", rotation_deg=17.0, preview=False),
    )

    assert rotated.elements["desk"].orientation_deg % 15 == 0


def test_preview_delta_marks_scene_dirty_without_commit(base_request):
    scene = build_scene_state(base_request)

    preview = apply_editor_delta(
        scene,
        EditorDelta(target="monitor", action="translate", dx_m=0.1, dy_m=0.1, preview=True),
    )

    assert preview.is_dirty is True
    assert preview.pending_preview is True
    assert preview.commit_version == scene.commit_version


def test_committed_delta_advances_commit_version(base_request):
    scene = build_scene_state(base_request)

    committed = apply_editor_delta(
        scene,
        EditorDelta(target="monitor", action="rotate", rotation_deg=15.0, preview=False),
    )

    assert committed.pending_preview is False
    assert committed.commit_version == scene.commit_version + 1
