from __future__ import annotations

import streamlit as st

from database.database import connect, get_settings, load_df
from services.ai_client import ai_available, get_ai_config, test_connection
from services.backup import backup_bytes, backup_filename, restore_database

MODELS = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
]


def _render_general_settings() -> None:
    settings = get_settings()
    with st.form("settings_form"):
        name = st.text_input("Nome", value=str(settings["user_name"]))
        theme_options = ["claro", "escuro"]
        current_theme = str(settings.get("theme", "claro"))
        theme = st.selectbox(
            "Tema",
            theme_options,
            index=theme_options.index(current_theme) if current_theme in theme_options else 0,
        )
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


def _render_ai_settings() -> None:
    settings = get_settings()
    configured_model = str(settings.get("ai_model") or MODELS[0])
    model_options = MODELS if configured_model in MODELS else [configured_model] + MODELS

    if ai_available():
        config = get_ai_config()
        st.success(f"Chave encontrada. Provedor: {config.provider}")
    else:
        st.warning("A variável `GROQ_API_KEY` ainda não foi configurada.")

    model = st.selectbox(
        "Modelo da IA",
        model_options,
        index=model_options.index(configured_model),
        help="O modelo pode ser alterado sem salvar a chave no banco.",
    )
    if st.button("Salvar modelo", key="save_ai_model"):
        with connect() as connection:
            connection.execute(
                "UPDATE settings SET ai_model = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                (model,),
            )
            connection.commit()
        st.success("Modelo salvo.")
        st.rerun()

    st.code(
        'GROQ_API_KEY = "sua-chave-aqui"\nGROQ_MODEL = "openai/gpt-oss-20b"',
        language="toml",
    )
    st.caption(
        "No computador, coloque essas linhas em `.streamlit/secrets.toml`. "
        "No Streamlit Community Cloud, use a área Secrets nas configurações do aplicativo."
    )

    if st.button("Testar conexão com a IA", disabled=not ai_available(), key="test_ai_connection"):
        with st.spinner("Testando conexão..."):
            try:
                result = test_connection()
                st.success(f"Conexão confirmada em {result.latency_ms / 1000:.1f}s — {result.model}")
            except RuntimeError as exc:
                st.error(str(exc))

    usage = load_df(
        """
        SELECT COUNT(*) AS requests,
               COALESCE(SUM(success), 0) AS successes,
               COALESCE(ROUND(AVG(latency_ms)), 0) AS avg_latency
          FROM ai_usage
        """
    ).iloc[0]
    cols = st.columns(3)
    cols[0].metric("Consultas", int(usage["requests"]))
    cols[1].metric("Sucesso", int(usage["successes"]))
    cols[2].metric("Latência média", f"{int(usage['avg_latency'])} ms")


def _render_backup_settings() -> None:
    st.markdown("O backup contém questões, histórico, metas, simulados, flashcards e revisões.")
    data = backup_bytes()
    st.download_button(
        "Baixar backup do banco",
        data=data,
        file_name=backup_filename(),
        mime="application/x-sqlite3",
        use_container_width=True,
        disabled=not bool(data),
    )

    uploaded = st.file_uploader("Restaurar backup", type=["db", "sqlite", "sqlite3"])
    confirm = st.checkbox("Entendo que a restauração substituirá os dados atuais.")
    if st.button(
        "Restaurar banco enviado",
        type="primary",
        disabled=uploaded is None or not confirm,
        use_container_width=True,
    ):
        try:
            restore_database(uploaded.getvalue())
            st.success("Backup restaurado. O aplicativo será recarregado.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def _render_admin_settings() -> None:
    st.markdown("### Administração do catálogo")
    st.caption("Área reservada para coleta, revisão e publicação das questões automáticas.")
    if st.button("Abrir Coletor e revisão", type="primary", use_container_width=True, key="open_collector_admin"):
        st.session_state.current_page = "Coletor automático"
        st.rerun()


def render_settings_page() -> None:
    st.markdown("## ⚙️ Configurações")
    st.caption("Personalização, IA online, backup e administração da plataforma.")

    general_tab, ai_tab, backup_tab, admin_tab, about_tab = st.tabs(
        ["Geral", "Professor IA", "Backup", "Administração", "Sobre"]
    )
    with general_tab:
        _render_general_settings()
    with ai_tab:
        _render_ai_settings()
    with backup_tab:
        _render_backup_settings()
    with admin_tab:
        _render_admin_settings()
    with about_tab:
        st.info("ConcursoAI — plataforma de preparação para concursos com revisão, simulados e IA.")
        st.markdown(
            "- Os dados de estudo ficam no SQLite local.\n"
            "- A chave da IA não é salva no banco nem no GitHub.\n"
            "- O catálogo remoto passa por revisão administrativa antes da publicação."
        )
