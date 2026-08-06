from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from database.database import connect, load_df
from services.reviews import complete_review, sync_reviews


def get_flashcards(subject: str = "Todas", due_only: bool = False, favorites_only: bool = False) -> pd.DataFrame:
    conditions: list[str] = []
    params: list[object] = []
    if subject != "Todas":
        conditions.append("subject = ?")
        params.append(subject)
    if due_only:
        conditions.append("date(due_date) <= date('now')")
    if favorites_only:
        conditions.append("favorite = 1")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return load_df(
        f"SELECT * FROM flashcards {where} ORDER BY date(due_date), favorite DESC, subject, id",
        tuple(params),
    )


def create_flashcard(subject: str, topic: str, front: str, back: str) -> int:
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO flashcards(subject, topic, front, back, due_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subject.strip(), topic.strip(), front.strip(), back.strip(), date.today().isoformat()),
        )
        card_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT OR IGNORE INTO reviews(
                review_key, flashcard_id, subject, topic, source, due_date, status
            ) VALUES (?, ?, ?, ?, 'flashcard', ?, 'pendente')
            """,
            (f"flashcard:{card_id}", card_id, subject.strip(), topic.strip(), date.today().isoformat()),
        )
        connection.commit()
        return card_id


def toggle_flashcard_favorite(card_id: int) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE flashcards SET favorite = CASE favorite WHEN 1 THEN 0 ELSE 1 END WHERE id = ?",
            (card_id,),
        )
        connection.commit()


def import_errors_as_flashcards() -> int:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT q.subject, q.assunto, q.statement,
                   'Gabarito: ' || q.answer || '. ' || COALESCE(q.explanation, '') AS back
              FROM error_notebook e
              JOIN questions q ON q.id = e.question_id
             WHERE NOT EXISTS (
                   SELECT 1 FROM flashcards f
                    WHERE f.front = q.statement
             )
            """
        ).fetchall()
        count = 0
        for row in rows:
            cursor = connection.execute(
                """
                INSERT INTO flashcards(subject, topic, front, back, due_date)
                VALUES (?, ?, ?, ?, date('now'))
                """,
                (row["subject"], row["assunto"], row["statement"], row["back"]),
            )
            card_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT OR IGNORE INTO reviews(
                    review_key, flashcard_id, subject, topic, source, due_date, status
                ) VALUES (?, ?, ?, ?, 'flashcard', date('now'), 'pendente')
                """,
                (f"flashcard:{card_id}", card_id, row["subject"], row["assunto"]),
            )
            count += 1
        connection.commit()
    return count


def _study_card(card: pd.Series) -> None:
    card_id = int(card["id"])
    st.markdown(
        f"""
        <div class="flashcard-shell">
          <div class="flashcard-meta"><span>{card['subject']}</span><span>{card.get('topic') or 'Geral'}</span></div>
          <div class="flashcard-label">PERGUNTA</div>
          <div class="flashcard-question">{card['front']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    reveal_key = f"flashcard_reveal_{card_id}"
    if st.button("Virar cartão", key=f"flip_{card_id}", type="primary", use_container_width=True):
        st.session_state[reveal_key] = True
    if st.session_state.get(reveal_key):
        st.success(str(card["back"]))
        review = load_df("SELECT id FROM reviews WHERE review_key = ?", (f"flashcard:{card_id}",))
        if not review.empty:
            review_id = int(review.iloc[0]["id"])
            cols = st.columns(4)
            for col, (quality, label) in zip(cols, [(1, "Errei"), (3, "Difícil"), (4, "Bom"), (5, "Fácil")]):
                if col.button(label, key=f"fc_rate_{card_id}_{quality}", use_container_width=True):
                    complete_review(review_id, quality)
                    st.session_state.pop(reveal_key, None)
                    st.rerun()


def render_flashcards_page() -> None:
    sync_reviews()
    st.markdown("## 🗂️ Flashcards")
    st.caption("Crie cartões, revise no tempo certo e acompanhe sua retenção.")
    study_tab, library_tab, create_tab = st.tabs(["Estudar", "Biblioteca", "Criar cartão"])

    with study_tab:
        subjects = load_df("SELECT DISTINCT subject FROM flashcards ORDER BY subject")
        subject = st.selectbox("Matéria", ["Todas"] + subjects["subject"].tolist(), key="fc_subject")
        cols = st.columns(2)
        due_only = cols[0].checkbox("Somente cartões de hoje", value=True, key="fc_due")
        favorites_only = cols[1].checkbox("Somente favoritos", key="fc_fav")
        cards = get_flashcards(subject, due_only, favorites_only)
        if cards.empty:
            st.info("Nenhum cartão disponível com esses filtros.")
        else:
            st.session_state.setdefault("flashcard_offset", 0)
            index = st.session_state.flashcard_offset % len(cards)
            _study_card(cards.iloc[index])
            nav = st.columns(2)
            if nav[0].button("← Anterior", use_container_width=True):
                st.session_state.flashcard_offset = (index - 1) % len(cards)
                st.rerun()
            if nav[1].button("Próximo →", use_container_width=True):
                st.session_state.flashcard_offset = (index + 1) % len(cards)
                st.rerun()
            st.caption(f"Cartão {index + 1} de {len(cards)}")

    with library_tab:
        metrics = st.columns(4)
        total = load_df("SELECT COUNT(*) AS total FROM flashcards")
        due = load_df("SELECT COUNT(*) AS total FROM flashcards WHERE date(due_date) <= date('now')")
        favorites = load_df("SELECT COUNT(*) AS total FROM flashcards WHERE favorite = 1")
        reviewed = load_df("SELECT COUNT(*) AS total FROM flashcard_reviews")
        metrics[0].metric("Cartões", int(total.iloc[0]["total"]))
        metrics[1].metric("Para hoje", int(due.iloc[0]["total"]))
        metrics[2].metric("Favoritos", int(favorites.iloc[0]["total"]))
        metrics[3].metric("Revisões", int(reviewed.iloc[0]["total"]))
        if st.button("Criar cartões a partir do caderno de erros"):
            created = import_errors_as_flashcards()
            st.success(f"{created} cartão(ões) criado(s).")
            st.rerun()
        cards = get_flashcards()
        if not cards.empty:
            for row in cards.itertuples(index=False):
                with st.expander(f"{row.subject} • {row.topic or 'Geral'} • Próxima: {row.due_date}"):
                    st.markdown(f"**Frente:** {row.front}")
                    st.markdown(f"**Verso:** {row.back}")
                    label = "★ Remover favorito" if row.favorite else "☆ Favoritar"
                    if st.button(label, key=f"fav_fc_{row.id}"):
                        toggle_flashcard_favorite(int(row.id))
                        st.rerun()

    with create_tab:
        subjects = load_df("SELECT name FROM subjects ORDER BY name")
        with st.form("new_flashcard", clear_on_submit=True):
            subject = st.selectbox("Matéria", subjects["name"].tolist())
            topic = st.text_input("Assunto", placeholder="Ex.: Juros compostos")
            front = st.text_area("Frente do cartão", placeholder="Escreva a pergunta ou conceito")
            back = st.text_area("Verso do cartão", placeholder="Escreva a resposta ou explicação")
            submitted = st.form_submit_button("Criar flashcard", type="primary")
        if submitted:
            if not front.strip() or not back.strip():
                st.warning("Preencha a frente e o verso.")
            else:
                create_flashcard(subject, topic or "Geral", front, back)
                st.success("Flashcard criado e agendado para hoje.")
