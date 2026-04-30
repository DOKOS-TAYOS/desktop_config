from __future__ import annotations

from app.ui.presets import ROOM_PRESETS


def test_room_presets_cover_common_spanish_home_layouts() -> None:
    expected_presets = {
        "Dormitorio pequeño",
        "Dormitorio principal",
        "Despacho compacto",
        "Salón adaptado",
        "Habitación alargada",
    }

    assert expected_presets.issubset(set(ROOM_PRESETS))
