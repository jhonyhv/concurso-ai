from __future__ import annotations

from datetime import date

import streamlit as st

from database.database import connect, get_settings, load_df

TOPICS = {
    "Língua Portuguesa": ["Interpretação de textos", "Ortografia", "Concordância", "Regência", "Crase"],
    "Matemática Financeira": ["Juros simples e compostos", "Taxas", "Descontos", "Amortização"],
    "Conhecimentos Bancários": ["SFN", "Produtos bancários", "Mercado de capitais", "Câmbio", "LGPD"],
    "Conhecimentos de Informática": ["Segurança", "Microsoft 365", "Internet", "Banco de dados"],
    "Vendas e Negociação": ["Venda consultiva", "Experiência do cliente", "Negociação", "Ética"],
}


def render_study_page() -> None:
    st.markdown("## 📖 Estudar")
    st.caption("Organize o plano semanal, registre sessões e acompanhe o conteúdo programático.")
    plan_tab, register_tab, content_tab = st.tabs(["Plano de estudos", "Registrar estudo", "Conteúdo programático"])

    with plan_tab:
        settings = get_settings()
        subjects = load_df("SELECT name, weight FROM subjects ORDER BY weight DESC")
        weekly_hours = st.slider("Horas disponíveis por semana", 5, 40, 20)
        if not subjects.empty:
            subjects["Horas/semana"] = (subjects["weight"] / subjects["weight"].sum() * weekly_hours).round(1)
            subjects["Questões sugeridas"] = (subjects["weight"] / subjects["weight"].sum() * int(settings["daily_questions_goal"]) * 7).round().astype(int)
            subjects["Estratégia"] = subjects["Horas/semana"].apply(
                lambda hours: "Teoria + questões + revisão" if hours >= 2 else "Revisão + questões"
            )
            st.dataframe(
                subjects.rename(columns={"name": "Matéria", "weight": "Peso relativo"}),
                use_container_width=True,
                hide_index=True,
            )

    with register_tab:
        subjects_df = load_df("SELECT name FROM subjects ORDER BY name")
        with st.form("study_form", clear_on_submit=True):
            subject = st.selectbox("Matéria", subjects_df["name"].tolist())
            minutes = st.number_input("Minutos estudados", 5, 600, 60, 5)
            study_date = st.date_input("Data", value=date.today())
            notes = st.text_area("Anotações")
            submitted = st.form_submit_button("Salvar sessão", type="primary")
        if submitted:
            with connect() as connection:
                connection.execute(
                    "INSERT INTO study_sessions(subject, minutes, session_date, notes) VALUES (?, ?, ?, ?)",
                    (subject, int(minutes), study_date.isoformat(), notes),
                )
                connection.commit()
            st.success("Sessão registrada com sucesso.")

        recent = load_df(
            """
            SELECT session_date AS Data, subject AS Matéria, minutes AS Minutos, notes AS Anotações
              FROM study_sessions
             ORDER BY session_date DESC, id DESC
             LIMIT 20
            """
        )
        if not recent.empty:
            st.markdown("### Sessões recentes")
            st.dataframe(recent, use_container_width=True, hide_index=True)

    with content_tab:
        st.warning("Use o edital oficial vigente como fonte principal.")
        for subject, items in TOPICS.items():
            with st.expander(subject):
                for item in items:
                    st.checkbox(item, key=f"topic_{subject}_{item}")
