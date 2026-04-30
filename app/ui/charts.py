from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.domain.models import ScenarioResult
from app.ui.i18n import LanguageCode, translate, translate_season
from app.utils.geometry import (
    compass_to_unit,
    desk_rectangle,
    rectangle_corners,
    window_center_point,
)


DARK_PAPER_BG = "#11181f"
DARK_PLOT_BG = "#182028"
DARK_GRID = "#2b3642"
DARK_FONT = "#edf4ef"


def _apply_dark_layout(figure: go.Figure, *, height: int) -> go.Figure:
    figure.update_layout(
        height=height,
        paper_bgcolor=DARK_PAPER_BG,
        plot_bgcolor=DARK_PLOT_BG,
        font={"color": DARK_FONT},
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        legend={
            "orientation": "h",
            "y": 1.08,
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": DARK_FONT},
        },
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor=DARK_GRID,
        zeroline=False,
        linecolor=DARK_GRID,
        tickfont={"color": DARK_FONT},
        title_font={"color": DARK_FONT},
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=DARK_GRID,
        zeroline=False,
        linecolor=DARK_GRID,
        tickfont={"color": DARK_FONT},
        title_font={"color": DARK_FONT},
    )
    return figure


def timeline_dataframe(result: ScenarioResult) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": [slot.when_local.strftime("%H:%M") for slot in result.time_slots],
            "glare": [slot.glare_score for slot in result.time_slots],
            "heat": [slot.heat_score for slot in result.time_slots],
            "comfort": [slot.comfort_score for slot in result.time_slots],
        }
    )


def timeline_chart(result: ScenarioResult, language: LanguageCode = "es") -> go.Figure:
    data = timeline_dataframe(result)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["glare"],
            mode="lines",
            name=translate("summary.metric.glare", language),
            line={"color": "#ff8e72", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["heat"],
            mode="lines",
            name=translate("summary.metric.heat", language),
            line={"color": "#f1bc62", "width": 3},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["comfort"],
            mode="lines",
            name=translate("summary.metric.comfort", language),
            line={"color": "#7bd6bf", "width": 3},
        )
    )
    yaxis_title = "Puntuación" if language == "es" else "Score"
    figure.update_layout(yaxis_title=yaxis_title)
    figure.update_yaxes(range=[0, 100])
    return _apply_dark_layout(figure, height=360)


def score_comparison_chart(
    current: ScenarioResult,
    recommended: ScenarioResult,
    language: LanguageCode = "es",
) -> go.Figure:
    figure = go.Figure()
    metrics = [
        translate("summary.metric.comfort", language),
        "Reflejo" if language == "es" else "Glare",
        "Calor" if language == "es" else "Heat",
        "Ergonomía" if language == "es" else "Ergonomics",
    ]
    figure.add_trace(
        go.Bar(
            name="Actual" if language == "es" else "Current",
            x=metrics,
            y=[
                current.comfort_score,
                current.glare_score,
                current.heat_score,
                current.ergonomic_score,
            ],
            marker_color="#7d8a96",
        )
    )
    figure.add_trace(
        go.Bar(
            name="Recomendada" if language == "es" else "Recommended",
            x=metrics,
            y=[
                recommended.comfort_score,
                recommended.glare_score,
                recommended.heat_score,
                recommended.ergonomic_score,
            ],
            marker_color="#7bd6bf",
        )
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(range=[0, 100])
    return _apply_dark_layout(figure, height=300)


def _window_segment(result: ScenarioResult) -> tuple[list[float], list[float]]:
    room = result.request.room
    window = result.request.window
    center_x, center_y, _ = window_center_point(room, window)
    half_width = window.width_m / 2
    if window.orientation_deg in (0, 180):
        return ([center_x - half_width, center_x + half_width], [center_y, center_y])
    return ([center_x, center_x], [center_y - half_width, center_y + half_width])


def room_plan_chart(
    current: ScenarioResult,
    recommended: ScenarioResult | None = None,
    language: LanguageCode = "es",
) -> go.Figure:
    figure = go.Figure()
    room = current.request.room

    figure.add_trace(
        go.Scatter(
            x=[0, room.width_m, room.width_m, 0, 0],
            y=[0, 0, room.depth_m, room.depth_m, 0],
            mode="lines",
            name=translate("editor.room", language),
            line={"color": "#d8e3dc", "width": 3},
        )
    )

    wx, wy = _window_segment(current)
    figure.add_trace(
        go.Scatter(
            x=wx,
            y=wy,
            mode="lines",
            name=translate("editor.window", language),
            line={"color": "#67c5e7", "width": 6},
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
            name="Mesa actual" if language == "es" else "Current desk",
            line={"color": "#ff8e72", "width": 2},
            fillcolor="rgba(255,142,114,0.18)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[current.request.monitor.x_m],
            y=[current.request.monitor.y_m],
            mode="markers",
            name="Monitor actual" if language == "es" else "Current monitor",
            marker={"size": 10, "color": "#ff8e72"},
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
                name="Mesa recomendada" if language == "es" else "Recommended desk",
                line={"color": "#7bd6bf", "width": 2, "dash": "dash"},
                fillcolor="rgba(123,214,191,0.18)",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[recommended.request.monitor.x_m],
                y=[recommended.request.monitor.y_m],
                mode="markers",
                name="Monitor recomendado"
                if language == "es"
                else "Recommended monitor",
                marker={"size": 10, "color": "#7bd6bf"},
            )
        )

    if current.time_slots:
        worst_slot = max(current.time_slots, key=lambda slot: slot.glare_score)
        ray_origin = window_center_point(room, current.request.window)
        direction = compass_to_unit((worst_slot.solar_azimuth_deg + 180) % 360)
        ray_length = min(room.width_m, room.depth_m) * 0.75
        figure.add_trace(
            go.Scatter(
                x=[ray_origin[0], ray_origin[0] + direction[0] * ray_length],
                y=[ray_origin[1], ray_origin[1] + direction[1] * ray_length],
                mode="lines",
                name="Dirección solar crítica"
                if language == "es"
                else "Critical solar direction",
                line={"color": "#f1bc62", "width": 3, "dash": "dot"},
            )
        )

    figure.update_layout(
        xaxis_title="Ancho (m)" if language == "es" else "Width (m)",
        yaxis_title="Fondo (m)" if language == "es" else "Depth (m)",
        xaxis={"range": [-0.1, room.width_m + 0.1]},
        yaxis={
            "range": [-0.1, room.depth_m + 0.1],
            "scaleanchor": "x",
            "scaleratio": 1,
        },
    )
    return _apply_dark_layout(figure, height=380)


def seasonal_heatmap(
    result: ScenarioResult, language: LanguageCode = "es"
) -> go.Figure:
    seasons = [
        translate_season(item.season, language) for item in result.seasonal_summary
    ]
    values = [
        [item.morning_comfort for item in result.seasonal_summary],
        [item.midday_comfort for item in result.seasonal_summary],
        [item.afternoon_comfort for item in result.seasonal_summary],
    ]
    figure = go.Figure(
        data=[
            go.Heatmap(
                z=values,
                x=seasons,
                y=[
                    "Mañana" if language == "es" else "Morning",
                    "Mediodía" if language == "es" else "Midday",
                    "Tarde" if language == "es" else "Afternoon",
                ],
                colorscale=[
                    [0.0, "#ff8e72"],
                    [0.5, "#f1bc62"],
                    [1.0, "#7bd6bf"],
                ],
                zmin=0,
                zmax=100,
            )
        ]
    )
    return _apply_dark_layout(figure, height=260)
