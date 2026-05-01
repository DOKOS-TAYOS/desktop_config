from __future__ import annotations

import pytest

from app.ui.forms import (
    _clamp_window_center_ratio_for_slider,
    _window_center_ratio_bounds,
)


def test_window_center_ratio_bounds_expand_for_edge_valid_positions() -> None:
    min_ratio, max_ratio = _window_center_ratio_bounds(
        room_width_m=4.0,
        room_depth_m=3.5,
        window_orientation_deg=270.0,
        window_width_m=0.6,
    )

    assert min_ratio == pytest.approx(0.0857142857)
    assert max_ratio == pytest.approx(0.9142857143)


def test_clamp_window_center_ratio_for_slider_absorbs_float_rounding_overflow() -> None:
    clamped_ratio = _clamp_window_center_ratio_for_slider(
        current_ratio=0.7811655405405405,
        min_ratio=0.2188344594594594,
        max_ratio=0.7811655405405404,
    )

    assert clamped_ratio == pytest.approx(0.7811655405405404)
