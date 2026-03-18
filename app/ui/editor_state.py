from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Literal

from app.domain.models import AnalysisRequest, DeskConfig, MonitorConfig, RoomConfig, WindowConfig
from app.utils.geometry import (
    EPSILON,
    desk_rectangle,
    local_to_world,
    normalize_angle_deg,
    point_in_rotated_rectangle,
    rectangle_half_extents,
    rotate_point,
    screen_size_m,
    smallest_angle_deg,
    world_to_local,
)


SceneElementKind = Literal["window", "desk", "monitor"]
EditorAction = Literal["translate", "rotate", "resize", "select"]

WINDOW_MIN_WIDTH_M = 0.6
MONITOR_EDGE_MARGIN_M = 0.03


@dataclass(slots=True)
class SceneElement:
    kind: SceneElementKind
    x_m: float
    y_m: float
    width_m: float
    depth_m: float
    orientation_deg: float
    metadata: dict[str, float | str | bool] | None = None


@dataclass(slots=True)
class SceneState:
    room_width_m: float
    room_depth_m: float
    elements: dict[SceneElementKind, SceneElement]
    selected_element: SceneElementKind = "desk"
    is_dirty: bool = False
    pending_preview: bool = False
    commit_version: int = 0
    last_action: EditorAction | None = None


@dataclass(frozen=True, slots=True)
class EditorDelta:
    target: SceneElementKind
    action: EditorAction
    dx_m: float = 0.0
    dy_m: float = 0.0
    rotation_deg: float = 0.0
    size_delta_m: float = 0.0
    preview: bool = False
    selected_element: SceneElementKind | None = None


def _snap_angle(angle_deg: float) -> float:
    return normalize_angle_deg(round(angle_deg / 15) * 15)


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _wall_axis_span(room: RoomConfig, orientation_deg: float) -> float:
    return room.width_m if normalize_angle_deg(orientation_deg) in (0, 180) else room.depth_m


def _window_center_from_ratio(room: RoomConfig, window: WindowConfig) -> tuple[float, float]:
    orientation = normalize_angle_deg(window.orientation_deg)
    if orientation == 0:
        return (room.width_m * window.center_ratio, room.depth_m)
    if orientation == 90:
        return (room.width_m, room.depth_m * window.center_ratio)
    if orientation == 180:
        return (room.width_m * window.center_ratio, 0.0)
    return (0.0, room.depth_m * window.center_ratio)


def _window_metadata(room: RoomConfig, window: WindowConfig) -> dict[str, float | str | bool]:
    wall = {0: "north", 90: "east", 180: "south", 270: "west"}[int(normalize_angle_deg(window.orientation_deg))]
    return {
        "wall": wall,
        "center_ratio": window.center_ratio,
        "wall_span_m": _wall_axis_span(room, window.orientation_deg),
    }


def build_scene_state(request: AnalysisRequest) -> SceneState:
    window_x, window_y = _window_center_from_ratio(request.room, request.window)
    monitor_width_m, _monitor_height_m = screen_size_m(request.monitor.diagonal_in)
    elements: dict[SceneElementKind, SceneElement] = {
        "window": SceneElement(
            kind="window",
            x_m=window_x,
            y_m=window_y,
            width_m=request.window.width_m,
            depth_m=0.0,
            orientation_deg=request.window.orientation_deg,
            metadata=_window_metadata(request.room, request.window),
        ),
        "desk": SceneElement(
            kind="desk",
            x_m=request.desk.x_m,
            y_m=request.desk.y_m,
            width_m=request.desk.width_m,
            depth_m=request.desk.depth_m,
            orientation_deg=request.desk.orientation_deg,
            metadata={"height_m": request.desk.height_m},
        ),
        "monitor": SceneElement(
            kind="monitor",
            x_m=request.monitor.x_m,
            y_m=request.monitor.y_m,
            width_m=monitor_width_m,
            depth_m=0.08,
            orientation_deg=request.monitor.orientation_deg,
            metadata={
                "diagonal_in": request.monitor.diagonal_in,
                "center_height_m": request.monitor.center_height_m,
                "tilt_deg": request.monitor.tilt_deg,
            },
        ),
    }
    return SceneState(
        room_width_m=request.room.width_m,
        room_depth_m=request.room.depth_m,
        elements=elements,
        selected_element="desk",
    )


def _clamp_desk_center(
    room_width_m: float,
    room_depth_m: float,
    desk: SceneElement,
    proposed_center: tuple[float, float],
) -> tuple[float, float]:
    half_extent_x, half_extent_y = rectangle_half_extents(
        desk.width_m,
        desk.depth_m,
        desk.orientation_deg,
    )
    return (
        _clamp(proposed_center[0], half_extent_x, room_width_m - half_extent_x),
        _clamp(proposed_center[1], half_extent_y, room_depth_m - half_extent_y),
    )


def _move_monitor_within_desk(monitor: SceneElement, desk: SceneElement) -> SceneElement:
    local_x, local_y = world_to_local((monitor.x_m, monitor.y_m), (desk.x_m, desk.y_m), desk.orientation_deg)
    max_x = max(desk.width_m / 2 - MONITOR_EDGE_MARGIN_M, 0.0)
    max_y = max(desk.depth_m / 2 - MONITOR_EDGE_MARGIN_M, 0.0)
    clamped_local = (
        _clamp(local_x, -max_x, max_x),
        _clamp(local_y, -max_y, max_y),
    )
    world_x, world_y = local_to_world(clamped_local, (desk.x_m, desk.y_m), desk.orientation_deg)
    return replace(monitor, x_m=world_x, y_m=world_y)


def _translate_window(
    scene: SceneState,
    window: SceneElement,
    delta: EditorDelta,
) -> SceneElement:
    wall_span = float((window.metadata or {}).get("wall_span_m", scene.room_depth_m))
    wall = str((window.metadata or {}).get("wall", "west"))
    current_axis_value = window.x_m if wall in ("north", "south") else window.y_m
    raw_axis_value = current_axis_value + (delta.dx_m if wall in ("north", "south") else delta.dy_m)
    clamped_axis_value = _clamp(raw_axis_value, window.width_m / 2, wall_span - window.width_m / 2)
    center_ratio = clamped_axis_value / max(wall_span, EPSILON)

    if wall == "north":
        x_m, y_m = clamped_axis_value, scene.room_depth_m
    elif wall == "south":
        x_m, y_m = clamped_axis_value, 0.0
    elif wall == "east":
        x_m, y_m = scene.room_width_m, clamped_axis_value
    else:
        x_m, y_m = 0.0, clamped_axis_value
    return replace(window, x_m=x_m, y_m=y_m, metadata={**(window.metadata or {}), "center_ratio": center_ratio})


def _resize_window(scene: SceneState, window: SceneElement, delta: EditorDelta) -> SceneElement:
    wall_span = float((window.metadata or {}).get("wall_span_m", scene.room_depth_m))
    wall = str((window.metadata or {}).get("wall", "west"))
    new_width = _clamp(window.width_m + delta.size_delta_m, WINDOW_MIN_WIDTH_M, wall_span)
    axis_value = window.x_m if wall in ("north", "south") else window.y_m
    clamped_axis_value = _clamp(axis_value, new_width / 2, wall_span - new_width / 2)
    center_ratio = clamped_axis_value / max(wall_span, EPSILON)
    if wall in ("north", "south"):
        x_m, y_m = clamped_axis_value, window.y_m
    else:
        x_m, y_m = window.x_m, clamped_axis_value
    return replace(
        window,
        x_m=x_m,
        y_m=y_m,
        width_m=new_width,
        metadata={**(window.metadata or {}), "center_ratio": center_ratio},
    )


def _translate_desk_and_monitor(scene: SceneState, delta: EditorDelta) -> tuple[SceneElement, SceneElement]:
    desk = scene.elements["desk"]
    monitor = scene.elements["monitor"]
    target_center = (desk.x_m + delta.dx_m, desk.y_m + delta.dy_m)
    clamped_center = _clamp_desk_center(scene.room_width_m, scene.room_depth_m, desk, target_center)
    actual_dx = clamped_center[0] - desk.x_m
    actual_dy = clamped_center[1] - desk.y_m
    moved_desk = replace(desk, x_m=clamped_center[0], y_m=clamped_center[1])
    moved_monitor = replace(monitor, x_m=monitor.x_m + actual_dx, y_m=monitor.y_m + actual_dy)
    return moved_desk, _move_monitor_within_desk(moved_monitor, moved_desk)


def _rotate_desk_and_monitor(scene: SceneState, delta: EditorDelta) -> tuple[SceneElement, SceneElement]:
    desk = scene.elements["desk"]
    monitor = scene.elements["monitor"]
    previous_orientation = desk.orientation_deg
    new_orientation = _snap_angle(previous_orientation + delta.rotation_deg)
    rotation_delta = new_orientation - previous_orientation
    rotated_desk = replace(desk, orientation_deg=new_orientation)
    rotated_monitor_position = rotate_point(
        (monitor.x_m, monitor.y_m),
        (desk.x_m, desk.y_m),
        rotation_delta,
    )
    rotated_monitor = replace(
        monitor,
        x_m=rotated_monitor_position[0],
        y_m=rotated_monitor_position[1],
        orientation_deg=_snap_angle(monitor.orientation_deg + rotation_delta),
    )
    rotated_desk = replace(
        rotated_desk,
        x_m=_clamp_desk_center(scene.room_width_m, scene.room_depth_m, rotated_desk, (desk.x_m, desk.y_m))[0],
        y_m=_clamp_desk_center(scene.room_width_m, scene.room_depth_m, rotated_desk, (desk.x_m, desk.y_m))[1],
    )
    return rotated_desk, _move_monitor_within_desk(rotated_monitor, rotated_desk)


def _translate_monitor(scene: SceneState, delta: EditorDelta) -> SceneElement:
    desk = scene.elements["desk"]
    monitor = scene.elements["monitor"]
    moved_monitor = replace(monitor, x_m=monitor.x_m + delta.dx_m, y_m=monitor.y_m + delta.dy_m)
    return _move_monitor_within_desk(moved_monitor, desk)


def _rotate_monitor(scene: SceneState, delta: EditorDelta) -> SceneElement:
    monitor = scene.elements["monitor"]
    return replace(monitor, orientation_deg=_snap_angle(monitor.orientation_deg + delta.rotation_deg))


def apply_editor_delta(scene: SceneState, delta: EditorDelta) -> SceneState:
    elements = {key: replace(value) for key, value in scene.elements.items()}
    selected_element = delta.selected_element or delta.target

    if delta.action == "translate":
        if delta.target == "window":
            elements["window"] = _translate_window(scene, elements["window"], delta)
        elif delta.target == "desk":
            elements["desk"], elements["monitor"] = _translate_desk_and_monitor(scene, delta)
        elif delta.target == "monitor":
            elements["monitor"] = _translate_monitor(scene, delta)
    elif delta.action == "rotate":
        if delta.target == "desk":
            elements["desk"], elements["monitor"] = _rotate_desk_and_monitor(scene, delta)
        elif delta.target == "monitor":
            elements["monitor"] = _rotate_monitor(scene, delta)
    elif delta.action == "resize" and delta.target == "window":
        elements["window"] = _resize_window(scene, elements["window"], delta)

    return SceneState(
        room_width_m=scene.room_width_m,
        room_depth_m=scene.room_depth_m,
        elements=elements,
        selected_element=selected_element,
        is_dirty=True,
        pending_preview=delta.preview,
        commit_version=scene.commit_version if delta.preview else scene.commit_version + 1,
        last_action=delta.action,
    )


def scene_to_request(scene: SceneState, base_request: AnalysisRequest) -> AnalysisRequest:
    window = scene.elements["window"]
    desk = scene.elements["desk"]
    monitor = scene.elements["monitor"]
    wall_span = scene.room_width_m if int(normalize_angle_deg(window.orientation_deg)) in (0, 180) else scene.room_depth_m
    center_ratio = float((window.metadata or {}).get("center_ratio", 0.5))
    if wall_span > 0:
        center_ratio = _clamp(center_ratio, 0.0, 1.0)

    room = replace(
        base_request.room,
        width_m=scene.room_width_m,
        depth_m=scene.room_depth_m,
    )
    window_config = replace(
        base_request.window,
        orientation_deg=window.orientation_deg,
        width_m=window.width_m,
        center_ratio=center_ratio,
    )
    desk_config = replace(
        base_request.desk,
        x_m=desk.x_m,
        y_m=desk.y_m,
        width_m=desk.width_m,
        depth_m=desk.depth_m,
        orientation_deg=desk.orientation_deg,
    )
    monitor_config = replace(
        base_request.monitor,
        x_m=monitor.x_m,
        y_m=monitor.y_m,
        orientation_deg=monitor.orientation_deg,
    )
    return replace(
        base_request,
        room=room,
        window=window_config,
        desk=desk_config,
        monitor=monitor_config,
    )


def scene_state_to_payload(scene: SceneState) -> dict[str, object]:
    return {
        "room_width_m": scene.room_width_m,
        "room_depth_m": scene.room_depth_m,
        "selected_element": scene.selected_element,
        "is_dirty": scene.is_dirty,
        "pending_preview": scene.pending_preview,
        "commit_version": scene.commit_version,
        "last_action": scene.last_action,
        "elements": {key: asdict(value) for key, value in scene.elements.items()},
    }


def scene_state_from_payload(payload: dict[str, object]) -> SceneState:
    elements_payload = payload.get("elements") or {}
    elements: dict[SceneElementKind, SceneElement] = {}
    for key in ("window", "desk", "monitor"):
        raw = dict((elements_payload or {}).get(key) or {})
        elements[key] = SceneElement(
            kind=key,
            x_m=float(raw.get("x_m", 0.0)),
            y_m=float(raw.get("y_m", 0.0)),
            width_m=float(raw.get("width_m", 0.0)),
            depth_m=float(raw.get("depth_m", 0.0)),
            orientation_deg=float(raw.get("orientation_deg", 0.0)),
            metadata=raw.get("metadata"),
        )
    return SceneState(
        room_width_m=float(payload.get("room_width_m", 0.0)),
        room_depth_m=float(payload.get("room_depth_m", 0.0)),
        elements=elements,
        selected_element=str(payload.get("selected_element", "desk")),  # type: ignore[arg-type]
        is_dirty=bool(payload.get("is_dirty", False)),
        pending_preview=bool(payload.get("pending_preview", False)),
        commit_version=int(payload.get("commit_version", 0)),
        last_action=payload.get("last_action"),  # type: ignore[arg-type]
    )
