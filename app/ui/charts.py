from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.domain.models import ScenarioResult
from app.utils.geometry import compass_to_unit, desk_rectangle, rectangle_corners, window_center_point


def timeline_dataframe(result: ScenarioResult) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hora": [slot.when_local.strftime("%H:%M") for slot in result.time_slots],
            "glare": [slot.glare_score for slot in result.time_slots],
            "heat": [slot.heat_score for slot in result.time_slots],
            "comfort": [slot.comfort_score for slot in result.time_slots],
        }
    )


def timeline_chart(result: ScenarioResult) -> go.Figure:
    data = timeline_dataframe(result)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["hora"],
            y=data["glare"],
            mode="lines",
            name="Riesgo de reflejo",
            line={"color": "#b8402a", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["hora"],
            y=data["heat"],
            mode="lines",
            name="Riesgo térmico",
            line={"color": "#d18c21", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["hora"],
            y=data["comfort"],
            mode="lines",
            name="Comfort score",
            line={"color": "#1f6b52", "width": 3},
        )
    )
    figure.update_layout(
        height=360,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        yaxis_title="Puntuación",
        legend_orientation="h",
        legend_y=1.1,
    )
    figure.update_yaxes(range=[0, 100])
    return figure


def score_comparison_chart(current: ScenarioResult, recommended: ScenarioResult) -> go.Figure:
    figure = go.Figure()
    metrics = ["Comfort", "Glare", "Heat", "Ergonomía"]
    figure.add_trace(
        go.Bar(
            name="Actual",
            x=metrics,
            y=[
                current.comfort_score,
                current.glare_score,
                current.heat_score,
                current.ergonomic_score,
            ],
            marker_color="#7e8b85",
        )
    )
    figure.add_trace(
        go.Bar(
            name="Recomendada",
            x=metrics,
            y=[
                recommended.comfort_score,
                recommended.glare_score,
                recommended.heat_score,
                recommended.ergonomic_score,
            ],
            marker_color="#1f6b52",
        )
    )
    figure.update_layout(
        barmode="group",
        height=300,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
    )
    figure.update_yaxes(range=[0, 100])
    return figure


def _window_segment(result: ScenarioResult) -> tuple[list[float], list[float]]:
    room = result.request.room
    window = result.request.window
    center_x, center_y, _ = window_center_point(room, window)
    half_width = window.width_m / 2
    if window.orientation_deg in (0, 180):
        return ([center_x - half_width, center_x + half_width], [center_y, center_y])
    return ([center_x, center_x], [center_y - half_width, center_y + half_width])


def room_plan_chart(current: ScenarioResult, recommended: ScenarioResult | None = None) -> go.Figure:
    figure = go.Figure()
    room = current.request.room

    figure.add_trace(
        go.Scatter(
            x=[0, room.width_m, room.width_m, 0, 0],
            y=[0, 0, room.depth_m, room.depth_m, 0],
            mode="lines",
            name="Habitación",
            line={"color": "#24372b", "width": 3},
        )
    )

    wx, wy = _window_segment(current)
    figure.add_trace(
        go.Scatter(
            x=wx,
            y=wy,
            mode="lines",
            name="Ventana",
            line={"color": "#4fa4c2", "width": 6},
        )
    )

    current_desk = rectangle_corners(desk_rectangle(current.request.desk))
    current_desk.append(current_desk[0])
    figure.add_trace(
        go.Scatter(
            x=[point[0] for point in current_desk],
            y=[point[1] for point in current_desk],
            mode="lines",
            fill="toself",
            name="Mesa actual",
            line={"color": "#b8402a", "width": 2},
            fillcolor="rgba(184,64,42,0.15)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[current.request.monitor.x_m],
            y=[current.request.monitor.y_m],
            mode="markers",
            name="Monitor actual",
            marker={"size": 10, "color": "#b8402a"},
        )
    )

    if recommended is not None:
        recommended_desk = rectangle_corners(desk_rectangle(recommended.request.desk))
        recommended_desk.append(recommended_desk[0])
        figure.add_trace(
            go.Scatter(
                x=[point[0] for point in recommended_desk],
                y=[point[1] for point in recommended_desk],
                mode="lines",
                fill="toself",
                name="Mesa recomendada",
                line={"color": "#1f6b52", "width": 2, "dash": "dash"},
                fillcolor="rgba(31,107,82,0.18)",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[recommended.request.monitor.x_m],
                y=[recommended.request.monitor.y_m],
                mode="markers",
                name="Monitor recomendado",
                marker={"size": 10, "color": "#1f6b52"},
            )
        )

    worst_slot = max(current.time_slots, key=lambda slot: slot.glare_score)
    ray_origin = window_center_point(room, current.request.window)
    direction = compass_to_unit((worst_slot.solar_azimuth_deg + 180) % 360)
    ray_length = min(room.width_m, room.depth_m) * 0.75
    figure.add_trace(
        go.Scatter(
            x=[ray_origin[0], ray_origin[0] + direction[0] * ray_length],
            y=[ray_origin[1], ray_origin[1] + direction[1] * ray_length],
            mode="lines",
            name="Dirección solar crítica",
            line={"color": "#d18c21", "width": 3, "dash": "dot"},
        )
    )
    figure.update_layout(
        height=380,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title="Ancho (m)",
        yaxis_title="Fondo (m)",
        xaxis={"range": [-0.1, room.width_m + 0.1]},
        yaxis={"range": [-0.1, room.depth_m + 0.1], "scaleanchor": "x", "scaleratio": 1},
        legend_orientation="h",
    )
    return figure


def seasonal_heatmap(result: ScenarioResult) -> go.Figure:
    seasons = [item.season.capitalize() for item in result.seasonal_summary]
    values = [
        [item.morning_comfort for item in result.seasonal_summary],
        [item.midday_comfort for item in result.seasonal_summary],
        [item.afternoon_comfort for item in result.seasonal_summary],
    ]
    figure = go.Figure(
        data=
        [
            go.Heatmap(
                z=values,
                x=seasons,
                y=["Mañana", "Mediodía", "Tarde"],
                colorscale=[
                    [0.0, "#b8402a"],
                    [0.5, "#f0d17b"],
                    [1.0, "#1f6b52"],
                ],
                zmin=0,
                zmax=100,
            )
        ]
    )
    figure.update_layout(height=260, margin={"l": 10, "r": 10, "t": 10, "b": 10})
    return figure
