from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from components.cards import metric_card, progress_row
from components.charts import PLOT_CONFIG, accuracy_evolution_chart, daily_goal_chart
from components.focus import render_focus_hero
from database.database import get_settings, load_df
from services.reviews import get_due_count, sync_reviews
from utils.helpers import format_duration


def _study_days() -> set[date]:
    frame = load_df("SELECT DISTINCT session_date FROM study_sessions")
    if frame.empty:
        return set()
    return {pd.to_datetime(value).date() for value in frame["session_date"].dropna()}


def _streaks() -> tuple[int, int]:
    days = _study_days()
    if not days:
        return 0, 0
    current_day = date.today()
    if current_day not in days and current_day - timedelta(days=1) in days:
        current_day -= timedelta(days=1)
    current = 0
    probe = current_day
    while probe in days:
        current += 1
        probe -= timedelta(days=1)

    ordered = sorted(days)
    best = run = 1
    for previous, next_day in zip(ordered, ordered[1:]):
        if next_day == previous + timedelta(days=1):
            run += 1
            best = max(best, run)
        else:
            run = 1
    return current, best


def _accuracy_last_days(days: int = 7) -> pd.DataFrame:
    start = date.today() - timedelta(days=days - 1)
    raw = load_df(
        """
        SELECT date(attempted_at) AS day,
               ROUND(100.0 * AVG(correct), 1) AS accuracy
          FROM attempts
         WHERE date(attempted_at) >= ?
         GROUP BY date(attempted_at)
         ORDER BY day
        """,
        (start.isoformat(),),
    )
    values = {row.day: float(row.accuracy) for row in raw.itertuples(index=False)}
    rows = []
    for offset in range(days):
        current = start + timedelta(days=offset)
        rows.append({"Dia": current.strftime("%d/%m"), "Acertos": values.get(current.isoformat(), 0.0)})
    return pd.DataFrame(rows)


def _calendar_html() -> str:
    sessions = load_df(
        """
        SELECT session_date, SUM(minutes) AS minutes
          FROM study_sessions
         GROUP BY session_date
        """
    )
    minutes = {pd.to_datetime(row.session_date).date(): int(row.minutes) for row in sessions.itertuples(index=False)}
    start = date.today() - timedelta(days=34)
    cells = []
    for offset in range(35):
        day = start + timedelta(days=offset)
        total = minutes.get(day, 0)
        level = 0 if total == 0 else 1 if total < 30 else 2 if total < 60 else 3 if total < 120 else 4
        today_class = " today" if day == date.today() else ""
        cells.append(f'<span class="heat-cell level-{level}{today_class}" title="{day.strftime("%d/%m/%Y")}: {total} min"></span>')
    return "".join(cells)


def _daily_goal_data() -> tuple[list[tuple[str, int, int]], float]:
    settings = get_settings()
    today = date.today().isoformat()
    questions = int(load_df("SELECT COUNT(*) AS total FROM attempts WHERE date(attempted_at) = ?", (today,)).iloc[0]["total"])
    minutes = int(load_df("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE session_date = ?", (today,)).iloc[0]["total"])
    reviews = int(load_df("SELECT COUNT(*) AS total FROM reviews WHERE date(last_reviewed_at) = ?", (today,)).iloc[0]["total"])
    cards = int(load_df("SELECT COUNT(*) AS total FROM flashcard_reviews WHERE date(reviewed_at) = ?", (today,)).iloc[0]["total"])
    items = [
        ("Questões", questions, int(settings["daily_questions_goal"])),
        ("Tempo de estudo", minutes, int(settings["daily_minutes_goal"])),
        ("Revisar erros", reviews, int(settings["daily_reviews_goal"])),
        ("Flashcards", cards, int(settings["daily_flashcards_goal"])),
    ]
    completed = sum(1 for _, current, target in items if current >= target)
    return items, 100 * completed / len(items)


def _empty_state(title: str, detail: str, icon: str = "↗") -> None:
    st.markdown(
        f"""
        <div class="dashboard-empty-state">
          <div class="dashboard-empty-icon">{icon}</div>
          <strong>{title}</strong>
          <span>{detail}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    sync_reviews()
    settings = get_settings()
    current_streak, best_streak = _streaks()
    last7 = (date.today() - timedelta(days=6)).isoformat()

    total_attempts = int(load_df("SELECT COUNT(*) AS total FROM attempts").iloc[0]["total"])
    week_attempts = load_df(
        "SELECT COUNT(*) AS total, COALESCE(100.0 * AVG(correct), 0) AS accuracy FROM attempts WHERE date(attempted_at) >= ?",
        (last7,),
    ).iloc[0]
    week_minutes = int(load_df("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE session_date >= ?", (last7,)).iloc[0]["total"])
    due_reviews = get_due_count()

    render_focus_hero(
        name=str(settings.get("user_name", "Aluno")),
        due_reviews=due_reviews,
    )

    columns = st.columns(4)
    with columns[0]:
        metric_card("Sequência", f"{current_streak} dias", f"Melhor: {best_streak} dias", "🔥", "orange")
    with columns[1]:
        metric_card("Questões", str(total_attempts), "Respondidas", "📖", "blue")
    with columns[2]:
        metric_card("Taxa de acertos", f"{float(week_attempts['accuracy']):.0f}%", "Últimos 7 dias", "🎯", "green")
    with columns[3]:
        metric_card("Tempo de estudo", format_duration(week_minutes), "Últimos 7 dias", "◷", "purple")

    left, right = st.columns([1.15, 1])
    with left:
        with st.container(border=True):
            st.markdown('<div class="panel-header"><div><h3>Evolução de acertos</h3><span>Últimos 7 dias</span></div></div>', unsafe_allow_html=True)
            if total_attempts == 0:
                _empty_state(
                    "Seu gráfico começa com a primeira questão",
                    "Resolva um bloco de questões para acompanhar a evolução de acertos ao longo da semana.",
                    "↗",
                )
            else:
                st.plotly_chart(accuracy_evolution_chart(_accuracy_last_days()), use_container_width=True, config=PLOT_CONFIG)
    with right:
        with st.container(border=True):
            st.markdown('<div class="panel-header"><div><h3>Calendário de estudos</h3><span>Últimos 35 dias</span></div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="heatmap heatmap-dashboard">{_calendar_html()}</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="heat-legend"><span class="level-4"></span> 2h+ <span class="level-3"></span> 1h+ <span class="level-2"></span> 30m+ <span class="level-0"></span> Sem estudo</div>',
                unsafe_allow_html=True,
            )

    performance = load_df(
        """
        SELECT q.subject AS Matéria,
               COUNT(a.id) AS Questões,
               ROUND(100.0 * AVG(a.correct), 1) AS Acertos
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
         GROUP BY q.subject
         ORDER BY Acertos DESC, Questões DESC
        """
    )
    goal_items, goal_progress = _daily_goal_data()
    reviews = load_df(
        """
        SELECT subject, topic, due_date, source
          FROM reviews
         WHERE status IN ('pendente', 'agendada')
         ORDER BY date(due_date), id
         LIMIT 3
        """
    )

    col1, col2, col3 = st.columns([1.05, 1.05, 1])
    with col1:
        with st.container(border=True):
            st.markdown('<div class="panel-header"><div><h3>Desempenho por matéria</h3><span>Pontos fortes e fracos</span></div></div>', unsafe_allow_html=True)
            if performance.empty:
                _empty_state("Ainda sem diagnóstico", "Seu desempenho por matéria aparecerá aqui após as primeiras questões.", "◎")
            else:
                tones = ["blue", "purple", "orange", "red", "green", "yellow"]
                for index, row in performance.head(5).reset_index(drop=True).iterrows():
                    progress_row(str(row["Matéria"]), float(row["Acertos"]), tones[index % len(tones)])

    with col2:
        with st.container(border=True):
            st.markdown('<div class="panel-header"><div><h3>Meta diária</h3><span>Progresso de hoje</span></div></div>', unsafe_allow_html=True)
            inner = st.columns([1, 1.1])
            with inner[0]:
                st.plotly_chart(daily_goal_chart(goal_progress), use_container_width=True, config=PLOT_CONFIG)
                completed = sum(1 for _, current, target in goal_items if current >= target)
                st.markdown(f'<div class="goal-caption">{completed} de {len(goal_items)} metas concluídas</div>', unsafe_allow_html=True)
            with inner[1]:
                for label, current, target in goal_items:
                    checked = "✓" if current >= target else "○"
                    st.markdown(f'<div class="goal-check"><span>{checked}</span><div><strong>{label}</strong><small>{current}/{target}</small></div></div>', unsafe_allow_html=True)

    with col3:
        with st.container(border=True):
            st.markdown('<div class="panel-header"><div><h3>Próxima revisão</h3><span>Agenda inteligente</span></div></div>', unsafe_allow_html=True)
            if reviews.empty:
                _empty_state("Fila em dia", "Nenhuma revisão está agendada no momento.", "✓")
            else:
                for row in reviews.itertuples(index=False):
                    due_date = pd.to_datetime(row.due_date).date()
                    if due_date <= date.today():
                        when = "Hoje"
                    elif due_date == date.today() + timedelta(days=1):
                        when = "Amanhã"
                    else:
                        when = due_date.strftime("%d/%m")
                    st.markdown(
                        f"""
                        <div class="review-mini">
                          <span class="review-dot"></span>
                          <div><strong>{row.topic or row.subject}</strong><small>{row.subject}</small></div>
                          <b>{when}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown(f'<div class="dashboard-foot">{due_reviews} revisão(ões) para hoje</div>', unsafe_allow_html=True)
