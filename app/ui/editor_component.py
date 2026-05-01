from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

from app.ui.editor_state import SceneState, scene_state_to_payload
from app.ui.i18n import LanguageCode


_COMPONENT_DIR = Path(__file__).resolve().parent / "components" / "floor_plan_editor"
_EDITOR_COMPONENT = components.declare_component(
    "sunsetup_floor_plan_editor",
    path=str(_COMPONENT_DIR),
)


def render_floor_plan_editor(
    scene: SceneState,
    *,
    key: str = "floor_plan_editor",
    height: int = 520,
    language: LanguageCode = "es",
    recommended_scene: SceneState | None = None,
) -> dict[str, Any] | None:
    default_value = {
        "scene": scene_state_to_payload(scene),
        "recommended_scene": (
            scene_state_to_payload(recommended_scene)
            if recommended_scene is not None
            else None
        ),
        "language": language,
        "event_seq": 0,
        "status": "idle",
    }
    return _EDITOR_COMPONENT(
        scene=scene_state_to_payload(scene),
        recommended_scene=(
            scene_state_to_payload(recommended_scene)
            if recommended_scene is not None
            else None
        ),
        language=language,
        default=default_value,
        height=height,
        key=key,
    )
