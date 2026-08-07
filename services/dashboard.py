from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from components.cards import metric_card, progress_row
from components.charts import PLOT_CONFIG, accuracy_evolution_chart, daily_goal_chart
from database.database import get_settings, load_df
from services.reviews import get_due_count, sync_reviews
from utils.helpers import format_duration

MONTHS_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _go(page: str) -> None:
    st.session_state.current_page = page
    st.rerun()


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
        cells.append(
            f'<span class="heat-cell level-{level}{today_class}" title="{day.strftime("%d/%m/%Y")}: {total} min"></span>'
        )
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


def _panel_header(title: str, right: str = "") -> None:
    right_html = f'<span class="reference-panel-filter">{right}</span>' if right else ""
    st.markdown(
        f'<div class="reference-panel-header"><h3>{title}</h3>{right_html}</div>',
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

    metrics = st.columns(4, gap="medium")
    with metrics[0]:
        metric_card("Sequência", f"{current_streak} dias", f"Melhor: {best_streak} dias", "🔥", "orange")
    with metrics[1]:
        metric_card("Questões", str(total_attempts), "Respondidas", "📖", "blue")
    with metrics[2]:
        metric_card("Taxa de acertos", f"{float(week_attempts['accuracy']):.0f}%", "Últimos 7 dias", "🎯", "green")
    with metrics[3]:
        metric_card("Tempo de estudo", format_duration(week_minutes), "Últimos 7 dias", "◷", "purple")

    upper_left, upper_right = st.columns([1.12, 1], gap="medium")
    with upper_left:
        with st.container(border=True):
            _panel_header("Evolução de acertos", "Últimos 7 dias⌄")
            st.plotly_chart(
                accuracy_evolution_chart(_accuracy_last_days()),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

    with upper_right:
        with st.container(border=True):
            month_label = f"{MONTHS_PT[date.today().month]} {date.today().year}   ‹   ›"
            _panel_header("Calendário de estudos  ⓘ", month_label)
            st.markdown('<div class="heat-weekdays"><span>D</span><span>S</span><span>T</span><span>Q</span><span>Q</span><span>S</span><span>S</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="heatmap reference-heatmap">{_calendar_html()}</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="heat-legend reference-heat-legend"><span class="level-4"></span> 2h+ <span class="level-3"></span> 1h+ <span class="level-2"></span> 30m+ <span class="level-0"></span> Sem estudo</div>',
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

    lower_left, lower_center, lower_right = st.columns([1.04, 1.08, 1.08], gap="medium")

    with lower_left:
        with st.container(border=True):
            _panel_header("Desempenho por matéria")
            if performance.empty:
                st.markdown(
                    '<div class="reference-empty"><strong>Seu desempenho aparecerá aqui.</strong><span>Responda questões para gerar o diagnóstico por matéria.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                for row in performance.head(5).itertuples(index=False):
                    score = float(row.Acertos)
                    tone = "blue" if score >= 50 else "yellow" if score >= 40 else "red"
                    progress_row(str(row.Matéria), score, tone)
            if st.button("Ver todas as matérias  ›", key="dashboard_subjects", use_container_width=True):
                _go("Estatísticas")

    with lower_center:
        with st.container(border=True):
            _panel_header("◎  Meta diária")
            inner = st.columns([.88, 1.12], gap="small")
            with inner[0]:
                st.plotly_chart(daily_goal_chart(goal_progress), use_container_width=True, config=PLOT_CONFIG)
                completed = sum(1 for _, current, target in goal_items if current >= target)
                st.markdown(
                    f'<div class="goal-caption reference-goal-caption">{completed} de {len(goal_items)} metas concluídas</div>',
                    unsafe_allow_html=True,
                )
            with inner[1]:
                for label, current, target in goal_items:
                    checked = "✓" if current >= target else "○"
                    st.markdown(
                        f'<div class="goal-check reference-goal-check"><span>{checked}</span><div><strong>{label}</strong><small>{current}/{target}</small></div></div>',
                        unsafe_allow_html=True,
                    )
            if st.button("Ver plano de estudos", key="dashboard_plan", use_container_width=True):
                _go("Estudar")

    with lower_right:
        with st.container(border=True):
            _panel_header("▣  Próxima revisão")
            if reviews.empty:
                st.markdown(
                    '<div class="reference-empty"><strong>Nenhuma revisão agendada.</strong><span>As próximas revisões aparecerão automaticamente aqui.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                dot_classes = ["blue", "yellow", "green"]
                for index, row in enumerate(reviews.itertuples(index=False)):
                    due_date = pd.to_datetime(row.due_date).date()
                    if due_date <= date.today():
                        when = "Hoje"
                    elif due_date == date.today() + timedelta(days=1):
                        when = "Amanhã"
                    else:
                        when = due_date.strftime("%d/%m")
                    st.markdown(
                        f"""
                        <div class="reference-review-row">
                          <span class="reference-review-dot {dot_classes[index % len(dot_classes)]}"></span>
                          <div class="reference-review-copy"><strong>{row.topic or row.subject}</strong><small>{row.subject}</small></div>
                          <div class="reference-review-date"><strong>{when}</strong><small>Revisar</small></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            if st.button("Ver todas as revisões  ›", key="dashboard_reviews", use_container_width=True):
                _go("Revisões")
