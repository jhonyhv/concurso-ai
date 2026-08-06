from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database.database import connect, get_settings, load_df
from services.reviews import get_due_count
from utils.helpers import safe_percent


def _today_progress() -> dict[str, int | float]:
    settings = get_settings()
    today = date.today().isoformat()
    questions = load_df("SELECT COUNT(*) AS total FROM attempts WHERE date(attempted_at) = ?", (today,))
    minutes = load_df("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE session_date = ?", (today,))
    reviews = load_df("SELECT COUNT(*) AS total FROM reviews WHERE date(last_reviewed_at) = ?", (today,))
    cards = load_df("SELECT COUNT(*) AS total FROM flashcard_reviews WHERE date(reviewed_at) = ?", (today,))
    return {
        "questions": int(questions.iloc[0]["total"]),
        "minutes": int(minutes.iloc[0]["total"]),
        "reviews": int(reviews.iloc[0]["total"]),
        "flashcards": int(cards.iloc[0]["total"]),
        "questions_goal": int(settings["daily_questions_goal"]),
        "minutes_goal": int(settings["daily_minutes_goal"]),
        "reviews_goal": int(settings["daily_reviews_goal"]),
        "flashcards_goal": int(settings["daily_flashcards_goal"]),
    }


def _calendar_cells() -> str:
    sessions = load_df(
        """
        SELECT session_date, SUM(minutes) AS minutes
          FROM study_sessions
         GROUP BY session_date
        """
    )
    minute_map = {pd.to_datetime(row.session_date).date(): int(row.minutes) for row in sessions.itertuples(index=False)}
    start = date.today() - timedelta(days=34)
    cells = []
    for offset in range(35):
        day = start + timedelta(days=offset)
        minutes = minute_map.get(day, 0)
        level = 0 if minutes == 0 else 1 if minutes < 30 else 2 if minutes < 60 else 3 if minutes < 120 else 4
        today_class = " today" if day == date.today() else ""
        cells.append(
            f'<span class="heat-cell level-{level}{today_class}" title="{day.strftime("%d/%m/%Y")}: {minutes} min"></span>'
        )
    return "".join(cells)


def render_goals_page() -> None:
    st.markdown("## 🎯 Metas")
    st.caption("Defina objetivos diários e acompanhe o que já foi concluído hoje.")
    progress = _today_progress()
    items = [
        ("Questões", progress["questions"], progress["questions_goal"], "📘"),
        ("Minutos de estudo", progress["minutes"], progress["minutes_goal"], "⏱️"),
        ("Revisões", progress["reviews"], progress["reviews_goal"], "🗓️"),
        ("Flashcards", progress["flashcards"], progress["flashcards_goal"], "🗂️"),
    ]
    for label, current, target, icon in items:
        percent = safe_percent(float(current), float(target))
        st.markdown(
            f"""
            <div class="goal-row">
              <div class="goal-icon">{icon}</div>
              <div class="goal-main"><strong>{label}</strong><span>{current} de {target}</span>
                <div class="progress-track"><div class="progress-fill" style="width:{percent:.1f}%; background:#2563eb"></div></div>
              </div>
              <div class="goal-percent">{percent:.0f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Ajustar metas")
    settings = get_settings()
    with st.form("goals_form"):
        cols = st.columns(2)
        minutes = cols[0].number_input("Minutos por dia", 10, 600, int(settings["daily_minutes_goal"]), 10)
        questions = cols[1].number_input("Questões por dia", 1, 300, int(settings["daily_questions_goal"]), 1)
        reviews = cols[0].number_input("Revisões por dia", 1, 100, int(settings["daily_reviews_goal"]), 1)
        flashcards = cols[1].number_input("Flashcards por dia", 1, 200, int(settings["daily_flashcards_goal"]), 1)
        submitted = st.form_submit_button("Salvar metas", type="primary")
    if submitted:
        with connect() as connection:
            connection.execute(
                """
                UPDATE settings
                   SET daily_minutes_goal = ?, daily_questions_goal = ?,
                       daily_reviews_goal = ?, daily_flashcards_goal = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = 1
                """,
                (int(minutes), int(questions), int(reviews), int(flashcards)),
            )
            connection.commit()
        st.success("Metas atualizadas.")
        st.rerun()


def render_calendar_page() -> None:
    st.markdown("## 📅 Calendário")
    st.caption("Visualize os últimos 35 dias e o histórico de estudos.")
    st.markdown(f'<div class="heatmap heatmap-large">{_calendar_cells()}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="heat-legend"><span class="level-0"></span> Sem estudo <span class="level-1"></span> &lt;30m <span class="level-2"></span> 30m+ <span class="level-3"></span> 1h+ <span class="level-4"></span> 2h+</div>',
        unsafe_allow_html=True,
    )
    history = load_df(
        """
        SELECT session_date AS Data, subject AS Matéria, minutes AS Minutos, notes AS Anotações
          FROM study_sessions
         ORDER BY session_date DESC, id DESC
        """
    )
    if history.empty:
        st.info("Nenhuma sessão registrada.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)
