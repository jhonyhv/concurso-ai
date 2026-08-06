import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


def weekly_evolution_chart(data: pd.DataFrame) -> go.Figure:
    if data.empty:
        data = pd.DataFrame({"Dia": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"], "Minutos": [0] * 7})
    figure = px.area(data, x="Dia", y="Minutos", markers=True)
    figure.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,.12)")
    figure.update_layout(
        height=290,
        margin=dict(l=10, r=10, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title=None, gridcolor="#eef2f7", rangemode="tozero"),
        hoverlabel=dict(bgcolor="white"),
    )
    return figure


def daily_goal_chart(progress: float) -> go.Figure:
    progress = max(0.0, min(float(progress), 100.0))
    figure = go.Figure(
        go.Pie(
            values=[progress, 100 - progress],
            hole=0.76,
            sort=False,
            direction="clockwise",
            marker=dict(colors=["#2563eb", "#edf2f7"], line=dict(width=0)),
            textinfo="none",
            hoverinfo="skip",
        )
    )
    figure.add_annotation(
        text=f"<b>{progress:.0f}%</b><br><span style='font-size:12px;color:#64748b'>concluído</span>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=23, color="#0f172a"),
    )
    figure.update_layout(
        height=230,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return figure
