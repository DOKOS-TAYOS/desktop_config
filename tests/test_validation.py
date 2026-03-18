from __future__ import annotations

import pytest

from app.domain.validation import ValidationError, validate_request


def test_validate_request_rejects_negative_room_dimension(base_request):
    base_request.room.width_m = -4.0

    with pytest.raises(ValidationError, match="width_m"):
        validate_request(base_request)


def test_validate_request_rejects_monitor_outside_desk(base_request):
    base_request.monitor.x_m = 3.2

    with pytest.raises(ValidationError, match="monitor"):
        validate_request(base_request)
