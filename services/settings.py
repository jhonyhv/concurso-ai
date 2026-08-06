from __future__ import annotations

import streamlit as st

from database.database import connect, get_settings


def render_settings_page() -> None:
    st.markdown("## ⚙️ Configurações")
    st.caption("Personalize o nome exibido e as metas do ConcursoAI.")
    settings = get_settings()
    with st.form("settings_form"):
        name = st.text_input("Nome", value=str(settings["user_name"]))
        theme = st.selectbox("Tema", ["claro"], index=0, help="O tema escuro será incluído em uma versão futura.")
        cols = st.columns(2)
        minutes = cols[0].number_input("Meta diária de minutos", 10, 600, int(settings["daily_minutes_goal"]), 10)
        questions = cols[1].number_input("Meta diária de questões", 1, 300, int(settings["daily_questions_goal"]), 1)
        reviews = cols[0].number_input("Meta diária de revisões", 1, 100, int(settings["daily_reviews_goal"]), 1)
        flashcards = cols[1].number_input("Meta diária de flashcards", 1, 200, int(settings["daily_flashcards_goal"]), 1)
        submitted = st.form_submit_button("Salvar configurações", type="primary")
    if submitted:
        if not name.strip():
            st.warning("Informe um nome.")
            return
        with connect() as connection:
            connection.execute(
                """
                UPDATE settings
                   SET user_name = ?, daily_minutes_goal = ?, daily_questions_goal = ?,
                       daily_reviews_goal = ?, daily_flashcards_goal = ?, theme = ?,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = 1
                """,
                (name.strip(), int(minutes), int(questions), int(reviews), int(flashcards), theme),
            )
            connection.commit()
        st.success("Configurações salvas.")
        st.rerun()

    st.markdown("### Sobre esta versão")
    st.info(
        "ConcursoAI v0.8 reúne o dashboard v0.6, metas e revisão espaçada v0.7, flashcards, simulados e Professor IA local v0.8."
    )
