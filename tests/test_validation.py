from __future__ import annotations

import pytest

from app.domain.validation import ValidationError, validate_request
from app.ui.editor_state import build_scene_state, scene_to_request


def test_validate_request_rejects_negative_room_dimension(base_request):
    base_request.room.width_m = -4.0

    with pytest.raises(ValidationError, match="width_m"):
        validate_request(base_request)


def test_validate_request_rejects_monitor_outside_desk(base_request):
    base_request.monitor.x_m = 3.2

    with pytest.raises(ValidationError, match="monitor"):
        validate_request(base_request)


def test_validate_request_allows_rotated_desk_touching_room_corner(base_request):
    scene = build_scene_state(base_request)
    scene.elements["desk"].orientation_deg = 30.0
    scene.elements["desk"].x_m = 0.0
    scene.elements["desk"].y_m = 0.0

    updated_request = scene_to_request(scene, base_request)

    validate_request(updated_request)
