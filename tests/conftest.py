from __future__ import annotations

from datetime import date

import pytest

from app.domain.models import (
    AnalysisRequest,
    DeskConfig,
    ErgonomicProfile,
    LocationInput,
    MonitorConfig,
    RoomConfig,
    WindowConfig,
)


@pytest.fixture
def base_request() -> AnalysisRequest:
    return AnalysisRequest(
        location=LocationInput(
            mode="manual",
            label="Madrid, ES",
            latitude=40.4168,
            longitude=-3.7038,
            timezone="Europe/Madrid",
        ),
        analysis_date=date(2026, 7, 15),
        room=RoomConfig(width_m=4.0, depth_m=3.5, ceiling_height_m=2.6),
        window=WindowConfig(
            orientation_deg=270,
            width_m=1.6,
            height_m=1.2,
            sill_height_m=0.9,
        ),
        desk=DeskConfig(
            x_m=1.7,
            y_m=1.75,
            width_m=1.4,
            depth_m=0.7,
            height_m=0.74,
            orientation_deg=270,
        ),
        monitor=MonitorConfig(
            x_m=1.7,
            y_m=1.75,
            center_height_m=1.16,
            diagonal_in=27,
            orientation_deg=270,
            tilt_deg=-5.0,
        ),
        ergonomic=ErgonomicProfile(
            eye_height_m=1.22,
            viewing_distance_m=0.65,
            preset_name="estandar",
        ),
        time_step_minutes=15,
        include_seasonal_summary=True,
    )
