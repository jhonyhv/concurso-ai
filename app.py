from datetime import date

import streamlit as st

from components.header import render_header
from components.sidebar import render_sidebar
from components.theme import load_global_css
from database.database import connect, init_db, load_df
from services.dashboard import render_dashboard
from services.questions import render_questions_page

st.set_page_config(page_title="ConcursoAI", page_icon="🎓", layout="wide")
init_db()
load_global_css()
page = render_sidebar()
render_header()

if page == "Painel":
    render_dashboard()

elif page == "Plano de estudos":
    st.subheader("📅 Plano semanal sugerido")
    subjects = load_df("SELECT name, weight FROM subjects ORDER BY weight DESC")
    weekly_hours = st.slider("Horas disponíveis por semana", 5, 40, 20)
    if subjects.empty:
        st.warning("Nenhuma matéria cadastrada.")
    else:
        subjects["Horas/semana"] = (
            subjects["weight"] / subjects["weight"].sum() * weekly_hours
        ).round(1)
        subjects["Estratégia"] = subjects["Horas/semana"].apply(
            lambda hours: "Teoria + questões + revisão"
            if hours >= 2
            else "Revisão + questões"
        )
        st.dataframe(
            subjects.rename(columns={"name": "Matéria", "weight": "Peso relativo"}),
            use_container_width=True,
            hide_index=True,
        )

elif page == "Questões":
    render_questions_page()

elif page == "Registrar estudo":
    st.subheader("⏱ Registrar sessão de estudo")
    subjects_df = load_df("SELECT name FROM subjects ORDER BY name")
    subjects = subjects_df["name"].tolist() if not subjects_df.empty else []
    with st.form("study_form", clear_on_submit=True):
        subject = st.selectbox("Matéria", subjects)
        minutes = st.number_input("Minutos estudados", 5, 600, 60, 5)
        study_date = st.date_input("Data", value=date.today())
        notes = st.text_area("Anotações")
        submitted = st.form_submit_button("Salvar sessão", type="primary")
    if submitted:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO study_sessions(subject, minutes, session_date, notes)
                VALUES (?, ?, ?, ?)
                """,
                (subject, int(minutes), study_date.isoformat(), notes),
            )
            connection.commit()
        st.success("Sessão registrada com sucesso.")

else:
    st.subheader("📚 Conteúdo programático inicial")
    st.warning("Atualize esta base quando um novo edital oficial for publicado.")
    topics = {
        "Língua Portuguesa": [
            "Interpretação de textos",
            "Ortografia",
            "Concordância",
            "Regência",
            "Crase",
        ],
        "Matemática Financeira": [
            "Juros simples e compostos",
            "Taxas",
            "Descontos",
            "Amortização",
        ],
        "Conhecimentos Bancários": [
            "SFN",
            "Produtos bancários",
            "Mercado de capitais",
            "Câmbio",
            "LGPD",
        ],
        "Informática": ["Segurança", "Microsoft 365", "Internet", "Banco de dados"],
        "Vendas e Negociação": [
            "Venda consultiva",
            "Experiência do cliente",
            "Negociação",
            "Ética",
        ],
    }
    for subject, items in topics.items():
        with st.expander(subject):
            for item in items:
                st.checkbox(item, key=f"topic_{subject}_{item}")
