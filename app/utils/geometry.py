from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.models import DeskConfig, MonitorConfig, RoomConfig, WindowConfig


EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Rectangle2D:
    center: tuple[float, float]
    width_m: float
    depth_m: float
    orientation_deg: float


@dataclass(frozen=True, slots=True)
class MonitorGeometry:
    center: tuple[float, float, float]
    width_m: float
    height_m: float
    normal: tuple[float, float, float]
    right: tuple[float, float, float]
    up: tuple[float, float, float]


def normalize_angle_deg(angle_deg: float) -> float:
    return angle_deg % 360


def smallest_angle_deg(a: float, b: float) -> float:
    delta = abs(normalize_angle_deg(a) - normalize_angle_deg(b)) % 360
    return min(delta, 360 - delta)


def compass_to_unit(angle_deg: float) -> tuple[float, float]:
    radians = math.radians(normalize_angle_deg(angle_deg))
    return (math.sin(radians), math.cos(radians))


def dot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross3(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm3(vector: tuple[float, float, float]) -> float:
    return math.sqrt(dot3(vector, vector))


def normalize3(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = norm3(vector)
    if length <= EPSILON:
        return (0.0, 0.0, 0.0)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def subtract3(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add3(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale3(
    vector: tuple[float, float, float], scalar: float
) -> tuple[float, float, float]:
    return (vector[0] * scalar, vector[1] * scalar, vector[2] * scalar)


def angle_between3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    denominator = max(norm3(a) * norm3(b), EPSILON)
    cosine = max(-1.0, min(1.0, dot3(a, b) / denominator))
    return math.degrees(math.acos(cosine))


def rectangle_axes(orientation_deg: float) -> tuple[tuple[float, float], tuple[float, float]]:
    forward = compass_to_unit(orientation_deg)
    right = compass_to_unit(orientation_deg + 90)
    return right, forward


def rotate_point(point: tuple[float, float], center: tuple[float, float], angle_deg: float) -> tuple[float, float]:
    radians = math.radians(angle_deg)
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return (
        center[0] + dx * math.cos(radians) - dy * math.sin(radians),
        center[1] + dx * math.sin(radians) + dy * math.cos(radians),
    )


def world_to_local(
    point: tuple[float, float], center: tuple[float, float], orientation_deg: float
) -> tuple[float, float]:
    right, forward = rectangle_axes(orientation_deg)
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return dx * right[0] + dy * right[1], dx * forward[0] + dy * forward[1]


def local_to_world(
    local_point: tuple[float, float], center: tuple[float, float], orientation_deg: float
) -> tuple[float, float]:
    right, forward = rectangle_axes(orientation_deg)
    return (
        center[0] + local_point[0] * right[0] + local_point[1] * forward[0],
        center[1] + local_point[0] * right[1] + local_point[1] * forward[1],
    )


def rectangle_half_extents(width_m: float, depth_m: float, orientation_deg: float) -> tuple[float, float]:
    right, forward = rectangle_axes(orientation_deg)
    half_width = width_m / 2
    half_depth = depth_m / 2
    half_extent_x = abs(right[0]) * half_width + abs(forward[0]) * half_depth
    half_extent_y = abs(right[1]) * half_width + abs(forward[1]) * half_depth
    return half_extent_x, half_extent_y


def point_in_rotated_rectangle(point: tuple[float, float], rectangle: Rectangle2D) -> bool:
    right, forward = rectangle_axes(rectangle.orientation_deg)
    dx = point[0] - rectangle.center[0]
    dy = point[1] - rectangle.center[1]
    local_x = dx * right[0] + dy * right[1]
    local_y = dx * forward[0] + dy * forward[1]
    return (
        abs(local_x) <= rectangle.width_m / 2 + EPSILON
        and abs(local_y) <= rectangle.depth_m / 2 + EPSILON
    )


def rectangle_corners(rectangle: Rectangle2D) -> list[tuple[float, float]]:
    right, forward = rectangle_axes(rectangle.orientation_deg)
    half_width = rectangle.width_m / 2
    half_depth = rectangle.depth_m / 2
    corners = []
    for width_sign, depth_sign in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = (
            rectangle.center[0]
            + width_sign * half_width * right[0]
            + depth_sign * half_depth * forward[0]
        )
        y = (
            rectangle.center[1]
            + width_sign * half_width * right[1]
            + depth_sign * half_depth * forward[1]
        )
        corners.append((x, y))
    return corners


def distance_point_to_ray(
    point: tuple[float, float, float],
    ray_origin: tuple[float, float, float],
    ray_direction: tuple[float, float, float],
) -> float:
    ray_direction = normalize3(ray_direction)
    origin_to_point = subtract3(point, ray_origin)
    projection = max(dot3(origin_to_point, ray_direction), 0.0)
    closest_point = add3(ray_origin, scale3(ray_direction, projection))
    delta = subtract3(point, closest_point)
    return norm3(delta)


def window_center_point(room: RoomConfig, window: WindowConfig) -> tuple[float, float, float]:
    orientation = normalize_angle_deg(window.orientation_deg)
    center_height = window.sill_height_m + window.height_m / 2
    if orientation == 0:
        return (room.width_m * window.center_ratio, room.depth_m, center_height)
    if orientation == 90:
        return (room.width_m, room.depth_m * window.center_ratio, center_height)
    if orientation == 180:
        return (room.width_m * window.center_ratio, 0.0, center_height)
    if orientation == 270:
        return (0.0, room.depth_m * window.center_ratio, center_height)
    outward = compass_to_unit(orientation)
    inward = compass_to_unit(orientation + 180)
    if abs(outward[0]) > abs(outward[1]):
        x = room.width_m if outward[0] > 0 else 0.0
        y = room.depth_m / 2
    else:
        x = room.width_m / 2
        y = room.depth_m if outward[1] > 0 else 0.0
    return (x + inward[0] * EPSILON, y + inward[1] * EPSILON, center_height)


def desk_rectangle(desk: DeskConfig) -> Rectangle2D:
    return Rectangle2D(
        center=(desk.x_m, desk.y_m),
        width_m=desk.width_m,
        depth_m=desk.depth_m,
        orientation_deg=desk.orientation_deg,
    )


def screen_size_m(
    diagonal_in: float, aspect_ratio_width: int = 16, aspect_ratio_height: int = 9
) -> tuple[float, float]:
    diagonal_m = diagonal_in * 0.0254
    ratio_diagonal = math.sqrt(aspect_ratio_width**2 + aspect_ratio_height**2)
    width = diagonal_m * aspect_ratio_width / ratio_diagonal
    height = diagonal_m * aspect_ratio_height / ratio_diagonal
    return width, height


def build_monitor_geometry(monitor: MonitorConfig) -> MonitorGeometry:
    width_m, height_m = screen_size_m(
        monitor.diagonal_in, monitor.aspect_ratio_width, monitor.aspect_ratio_height
    )
    horizontal = compass_to_unit(monitor.orientation_deg)
    pitch_rad = math.radians(-monitor.tilt_deg)
    normal = normalize3(
        (
            horizontal[0] * math.cos(pitch_rad),
            horizontal[1] * math.cos(pitch_rad),
            math.sin(pitch_rad),
        )
    )
    world_up = (0.0, 0.0, 1.0)
    right = normalize3(cross3(world_up, normal))
    up = normalize3(cross3(normal, right))
    return MonitorGeometry(
        center=(monitor.x_m, monitor.y_m, monitor.center_height_m),
        width_m=width_m,
        height_m=height_m,
        normal=normal,
        right=right,
        up=up,
    )


def ray_intersects_horizontal_rectangle(
    ray_origin: tuple[float, float, float],
    ray_direction: tuple[float, float, float],
    plane_z: float,
    rectangle: Rectangle2D,
) -> tuple[bool, tuple[float, float, float] | None]:
    if abs(ray_direction[2]) <= EPSILON:
        return False, None
    t = (plane_z - ray_origin[2]) / ray_direction[2]
    if t < 0:
        return False, None
    hit = add3(ray_origin, scale3(ray_direction, t))
    if point_in_rotated_rectangle((hit[0], hit[1]), rectangle):
        return True, hit
    return False, hit


def intersect_ray_with_monitor(
    ray_origin: tuple[float, float, float],
    ray_direction: tuple[float, float, float],
    monitor_geometry: MonitorGeometry,
) -> tuple[bool, tuple[float, float, float] | None, tuple[float, float] | None]:
    denominator = dot3(ray_direction, monitor_geometry.normal)
    if abs(denominator) <= EPSILON or denominator >= 0:
        return False, None, None
    origin_to_center = subtract3(monitor_geometry.center, ray_origin)
    t = dot3(origin_to_center, monitor_geometry.normal) / denominator
    if t < 0:
        return False, None, None
    hit_point = add3(ray_origin, scale3(ray_direction, t))
    local_x = dot3(subtract3(hit_point, monitor_geometry.center), monitor_geometry.right)
    local_y = dot3(subtract3(hit_point, monitor_geometry.center), monitor_geometry.up)
    within_bounds = (
        abs(local_x) <= monitor_geometry.width_m / 2 + EPSILON
        and abs(local_y) <= monitor_geometry.height_m / 2 + EPSILON
    )
    return within_bounds, hit_point, (local_x, local_y)


def classify_screen_zone(
    local_coordinates: tuple[float, float], monitor_geometry: MonitorGeometry
) -> str:
    local_x, local_y = local_coordinates
    width_band = monitor_geometry.width_m / 6
    height_band = monitor_geometry.height_m / 6
    if local_x < -width_band:
        horizontal = "izquierda"
    elif local_x > width_band:
        horizontal = "derecha"
    else:
        horizontal = "centro"
    if local_y > height_band:
        vertical = "superior"
    elif local_y < -height_band:
        vertical = "inferior"
    else:
        vertical = "media"
    return f"{horizontal}-{vertical}"
