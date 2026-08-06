from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


def _base_layout(height: int = 290) -> dict:
    return dict(
        height=height,
        margin=dict(l=12, r=12, t=18, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#52627a", family="Arial"),
        hoverlabel=dict(bgcolor="white"),
    )


def weekly_evolution_chart(data: pd.DataFrame) -> go.Figure:
    if data.empty:
        data = pd.DataFrame({"Dia": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"], "Minutos": [0] * 7})
    figure = px.area(data, x="Dia", y="Minutos", markers=True)
    figure.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,.10)", line_width=3)
    figure.update_layout(**_base_layout())
    figure.update_xaxes(title=None, showgrid=False)
    figure.update_yaxes(title=None, gridcolor="#eaf0f8", rangemode="tozero")
    return figure


def accuracy_evolution_chart(data: pd.DataFrame) -> go.Figure:
    if data.empty:
        data = pd.DataFrame({"Dia": ["-"], "Acertos": [0]})
    figure = px.area(data, x="Dia", y="Acertos", markers=True)
    figure.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,.10)", line_width=3, marker_size=8)
    figure.update_layout(**_base_layout(300))
    figure.update_xaxes(title=None, showgrid=False)
    figure.update_yaxes(title=None, range=[0, 100], ticksuffix="%", gridcolor="#eaf0f8")
    return figure


def daily_goal_chart(progress: float) -> go.Figure:
    progress = max(0.0, min(float(progress), 100.0))
    figure = go.Figure(
        go.Pie(
            values=[progress, 100 - progress],
            hole=0.72,
            sort=False,
            direction="clockwise",
            marker=dict(colors=["#2563eb", "#edf2f7"], line=dict(width=0)),
            textinfo="none",
            hoverinfo="skip",
        )
    )
    figure.add_annotation(
        text=f"<b>{progress:.0f}%</b>",
        x=0.5,
        y=0.52,
        showarrow=False,
        font=dict(size=30, color="#10213e"),
    )
    figure.update_layout(**_base_layout(225), showlegend=False)
    return figure


def subject_bar_chart(data: pd.DataFrame) -> go.Figure:
    if data.empty:
        data = pd.DataFrame({"Matéria": ["Sem dados"], "Aproveitamento": [0]})
    figure = px.bar(data, x="Aproveitamento", y="Matéria", orientation="h", text="Aproveitamento")
    figure.update_traces(marker_color="#2563eb", texttemplate="%{text:.0f}%", textposition="outside")
    figure.update_layout(**_base_layout(max(260, 50 * len(data))), showlegend=False)
    figure.update_xaxes(title=None, range=[0, 110], ticksuffix="%", gridcolor="#edf2f7")
    figure.update_yaxes(title=None, autorange="reversed")
    return figure
