from datetime import date, timedelta

import pandas as pd
import streamlit as st

from components.cards import metric_card, progress_row
from components.charts import PLOT_CONFIG, daily_goal_chart, weekly_evolution_chart
from database.database import load_df


def _streak_days(sessions: pd.DataFrame) -> int:
    if sessions.empty:
        return 0
    days = {pd.to_datetime(value).date() for value in sessions["session_date"].dropna()}
    current = date.today()
    if current not in days and current - timedelta(days=1) in days:
        current -= timedelta(days=1)
    streak = 0
    while current in days:
        streak += 1
        current -= timedelta(days=1)
    return streak


def _weekly_data(sessions: pd.DataFrame) -> pd.DataFrame:
    labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    start = date.today() - timedelta(days=date.today().weekday())
    result = []
    for offset, label in enumerate(labels):
        day = start + timedelta(days=offset)
        if sessions.empty:
            minutes = 0
        else:
            dates = pd.to_datetime(sessions["session_date"]).dt.date
            minutes = int(sessions.loc[dates == day, "minutes"].sum())
        result.append({"Dia": label, "Minutos": minutes})
    return pd.DataFrame(result)


def _calendar_html(sessions: pd.DataFrame) -> str:
    studied = set()
    if not sessions.empty:
        studied = {pd.to_datetime(value).date() for value in sessions["session_date"].dropna()}
    cells = []
    start = date.today() - timedelta(days=34)
    for offset in range(35):
        day = start + timedelta(days=offset)
        active = " active" if day in studied else ""
        today = " today" if day == date.today() else ""
        cells.append(f'<span class="heat-cell{active}{today}" title="{day.strftime("%d/%m/%Y")}"></span>')
    return "".join(cells)


def render_dashboard() -> None:
    sessions = load_df("SELECT * FROM study_sessions")
    attempts = load_df("SELECT * FROM attempts")

    total_minutes = int(sessions["minutes"].sum()) if not sessions.empty else 0
    total_attempts = len(attempts)
    accuracy = float(attempts["correct"].mean() * 100) if total_attempts else 0.0
    streak = _streak_days(sessions)

    today_text = date.today().strftime("%d de %B de %Y")
    st.markdown(f'<div class="date-line">📅 {today_text}</div>', unsafe_allow_html=True)

    columns = st.columns(4)
    with columns[0]:
        metric_card("Sequência atual", f"{streak} dias", "Mantenha o ritmo", "🔥", "orange")
    with columns[1]:
        metric_card("Questões respondidas", str(total_attempts), "Histórico acumulado", "📚", "blue")
    with columns[2]:
        metric_card("Taxa de acertos", f"{accuracy:.0f}%", "Desempenho geral", "🎯", "green")
    with columns[3]:
        metric_card("Tempo de estudo", f"{total_minutes / 60:.1f}h", "Tempo acumulado", "⏱", "purple")

    weekly = _weekly_data(sessions)
    today_minutes = 0
    if not sessions.empty:
        session_dates = pd.to_datetime(sessions["session_date"]).dt.date
        today_minutes = int(sessions.loc[session_dates == date.today(), "minutes"].sum())
    daily_target = 120
    daily_progress = min(today_minutes / daily_target * 100, 100)

    left, right = st.columns([1.65, 1])
    with left:
        st.markdown('<div class="panel-title">Evolução semanal</div><div class="panel-subtitle">Minutos estudados nesta semana</div>', unsafe_allow_html=True)
        st.plotly_chart(weekly_evolution_chart(weekly), use_container_width=True, config=PLOT_CONFIG)
    with right:
        st.markdown('<div class="panel-title">Meta diária</div><div class="panel-subtitle">Objetivo: 2 horas por dia</div>', unsafe_allow_html=True)
        st.plotly_chart(daily_goal_chart(daily_progress), use_container_width=True, config=PLOT_CONFIG)
        st.markdown(f'<div class="goal-caption">{today_minutes} de {daily_target} minutos concluídos</div>', unsafe_allow_html=True)

    performance = load_df(
        """
        SELECT q.subject AS Matéria, COUNT(a.id) AS Questões,
               ROUND(100.0 * AVG(a.correct), 1) AS Acertos
        FROM attempts a
        JOIN questions q ON q.id = a.question_id
        GROUP BY q.subject
        ORDER BY Acertos DESC
        """
    )

    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('<div class="panel-title">Desempenho por matéria</div><div class="panel-subtitle">Acompanhe os seus pontos fortes e fracos</div>', unsafe_allow_html=True)
        if performance.empty:
            st.info("Responda questões para gerar seu diagnóstico.")
        else:
            tones = ["blue", "green", "purple", "orange", "yellow"]
            for index, row in performance.head(6).reset_index(drop=True).iterrows():
                progress_row(str(row["Matéria"]), float(row["Acertos"]), tones[index % len(tones)])
    with right:
        st.markdown('<div class="panel-title">Calendário de estudos</div><div class="panel-subtitle">Últimos 35 dias</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="heatmap">{_calendar_html(sessions)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="heat-legend"><span></span> Sem estudo <span class="active"></span> Com estudo</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel-title review-title">Próximas revisões</div>', unsafe_allow_html=True)
    if performance.empty:
        reviews = [
            ("Conhecimentos Bancários", "Revisar Sistema Financeiro Nacional", "Hoje"),
            ("Matemática Financeira", "Revisar juros simples e compostos", "Amanhã"),
            ("Língua Portuguesa", "Revisar concordância verbal", "Em 3 dias"),
        ]
    else:
        weakest = performance.sort_values("Acertos").head(3)
        reviews = [(str(row["Matéria"]), f"Revisar questões com {row['Acertos']:.0f}% de acerto", when) for (_, row), when in zip(weakest.iterrows(), ["Hoje", "Amanhã", "Em 3 dias"])]
    for subject, description, when in reviews:
        st.markdown(
            f"""
            <div class="review-item">
              <div class="review-icon">📖</div>
              <div class="review-text"><strong>{subject}</strong><span>{description}</span></div>
              <div class="review-date">{when}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
