from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from database.database import connect, load_df


def sync_reviews() -> None:
    """Mantém revisões de erros e flashcards sincronizadas com o banco."""
    with connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO reviews(
                review_key, question_id, subject, topic, source, due_date, status
            )
            SELECT 'error:' || e.question_id, e.question_id, q.subject, q.assunto,
                   'caderno de erros', date('now'),
                   CASE WHEN e.reviewed = 1 THEN 'concluida' ELSE 'pendente' END
              FROM error_notebook e
              JOIN questions q ON q.id = e.question_id
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO reviews(
                review_key, flashcard_id, subject, topic, source, due_date, status
            )
            SELECT 'flashcard:' || f.id, f.id, f.subject, f.topic,
                   'flashcard', f.due_date, 'pendente'
              FROM flashcards f
            """
        )
        connection.execute(
            """
            UPDATE reviews
               SET due_date = (SELECT f.due_date FROM flashcards f WHERE f.id = reviews.flashcard_id),
                   status = CASE
                       WHEN date((SELECT f.due_date FROM flashcards f WHERE f.id = reviews.flashcard_id)) <= date('now')
                       THEN 'pendente' ELSE 'agendada' END
             WHERE flashcard_id IS NOT NULL
            """
        )
        connection.commit()


def get_reviews(status: str = "Todas") -> pd.DataFrame:
    sync_reviews()
    conditions: list[str] = []
    params: list[object] = []
    if status == "Pendentes":
        conditions.append("r.status IN ('pendente', 'agendada') AND date(r.due_date) <= date('now')")
    elif status == "Próximas":
        conditions.append("date(r.due_date) > date('now')")
    elif status == "Concluídas":
        conditions.append("r.status = 'concluida'")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return load_df(
        f"""
        SELECT r.*,
               q.statement, q.answer, q.explanation,
               f.front, f.back
          FROM reviews r
          LEFT JOIN questions q ON q.id = r.question_id
          LEFT JOIN flashcards f ON f.id = r.flashcard_id
          {where}
         ORDER BY date(r.due_date), r.subject, r.id
        """,
        tuple(params),
    )


def _sm2(current_interval: int, repetitions: int, ease: float, quality: int) -> tuple[int, int, float]:
    quality = max(0, min(5, int(quality)))
    if quality < 3:
        return 1, 0, max(1.3, ease - 0.2)
    if repetitions == 0:
        interval = 1
    elif repetitions == 1:
        interval = 6
    else:
        interval = max(1, round(current_interval * ease))
    new_ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return interval, repetitions + 1, new_ease


def complete_review(review_id: int, quality: int) -> None:
    with connect() as connection:
        review = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if not review:
            return
        interval, repetitions, ease = _sm2(
            int(review["interval_days"]), int(review["repetitions"]), float(review["ease_factor"]), quality
        )
        next_due = date.today() + timedelta(days=interval)
        status = "pendente" if quality < 3 else "agendada"
        connection.execute(
            """
            UPDATE reviews
               SET interval_days = ?, repetitions = ?, ease_factor = ?, due_date = ?,
                   status = ?, last_reviewed_at = ?
             WHERE id = ?
            """,
            (interval, repetitions, ease, next_due.isoformat(), status, datetime.now().isoformat(timespec="seconds"), review_id),
        )
        if review["question_id"] is not None:
            connection.execute(
                "UPDATE error_notebook SET reviewed = ? WHERE question_id = ?",
                (int(quality >= 3), int(review["question_id"])),
            )
        if review["flashcard_id"] is not None:
            flashcard_id = int(review["flashcard_id"])
            connection.execute(
                """
                UPDATE flashcards
                   SET interval_days = ?, repetitions = ?, ease_factor = ?, due_date = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
                """,
                (interval, repetitions, ease, next_due.isoformat(), flashcard_id),
            )
            connection.execute(
                """
                INSERT INTO flashcard_reviews(flashcard_id, quality, reviewed_at, next_due_date)
                VALUES (?, ?, ?, ?)
                """,
                (flashcard_id, quality, datetime.now().isoformat(timespec="seconds"), next_due.isoformat()),
            )
        connection.commit()


def get_due_count() -> int:
    sync_reviews()
    frame = load_df(
        """
        SELECT COUNT(*) AS total
          FROM reviews
         WHERE status IN ('pendente', 'agendada') AND date(due_date) <= date('now')
        """
    )
    return int(frame.iloc[0]["total"]) if not frame.empty else 0


def _review_card(row: pd.Series) -> None:
    is_question = pd.notna(row.get("question_id"))
    title = str(row.get("statement") if is_question else row.get("front"))
    answer = str(row.get("explanation") or f"Gabarito: {row.get('answer')}") if is_question else str(row.get("back"))

    st.markdown(
        f"""
        <div class="study-card">
          <div class="study-card-top"><span>{row['subject']}</span><span>{row.get('topic') or 'Geral'}</span></div>
          <h3>{title}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    reveal_key = f"review_reveal_{int(row['id'])}"
    if st.button("Mostrar resposta", key=f"show_{row['id']}", use_container_width=True):
        st.session_state[reveal_key] = True
    if st.session_state.get(reveal_key):
        st.info(answer)
        cols = st.columns(4)
        ratings = [(1, "Errei"), (3, "Difícil"), (4, "Bom"), (5, "Fácil")]
        for col, (quality, label) in zip(cols, ratings):
            if col.button(label, key=f"rate_{row['id']}_{quality}", use_container_width=True):
                complete_review(int(row["id"]), quality)
                st.session_state.pop(reveal_key, None)
                st.success("Revisão registrada e próxima data calculada.")
                st.rerun()


def render_reviews_page() -> None:
    st.markdown("## 🗓️ Revisões")
    st.caption("Revisão espaçada baseada no seu caderno de erros e nos flashcards.")
    due = get_due_count()
    cols = st.columns(3)
    cols[0].metric("Revisões para hoje", due)
    upcoming = load_df("SELECT COUNT(*) AS total FROM reviews WHERE date(due_date) > date('now')")
    cols[1].metric("Próximas", int(upcoming.iloc[0]["total"]))
    completed = load_df("SELECT COUNT(*) AS total FROM reviews WHERE last_reviewed_at IS NOT NULL")
    cols[2].metric("Revisões realizadas", int(completed.iloc[0]["total"]))

    status = st.radio("Exibir", ["Pendentes", "Próximas", "Concluídas", "Todas"], horizontal=True)
    reviews = get_reviews(status)
    if reviews.empty:
        st.info("Nenhuma revisão encontrada para este filtro.")
        return

    if status == "Pendentes":
        _review_card(reviews.iloc[0])
        if len(reviews) > 1:
            st.caption(f"Mais {len(reviews) - 1} revisão(ões) aguardando.")
        return

    display = reviews[["subject", "topic", "source", "due_date", "status"]].rename(
        columns={"subject": "Matéria", "topic": "Assunto", "source": "Origem", "due_date": "Data", "status": "Status"}
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
