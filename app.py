import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "bb_master.db"

SUBJECTS = [
    ("Língua Portuguesa", 15),
    ("Língua Inglesa", 5),
    ("Matemática", 5),
    ("Atualidades do Mercado Financeiro", 5),
    ("Matemática Financeira", 5),
    ("Conhecimentos Bancários", 10),
    ("Conhecimentos de Informática", 15),
    ("Vendas e Negociação", 15),
]

QUESTIONS = [
    ("Conhecimentos Bancários", "Qual instituição define a taxa Selic?", "Banco Central do Brasil", "CVM", "Banco do Brasil", "BNDES", "A", "A taxa Selic é definida pelo Copom, órgão do Banco Central."),
    ("Matemática Financeira", "Em juros simples, qual é a fórmula dos juros?", "J = C × i × t", "J = C × (1+i)^t", "M = C ÷ i", "J = C + i + t", "A", "Em juros simples, os juros são calculados sobre o capital inicial."),
    ("Conhecimentos de Informática", "Qual prática aumenta a segurança de uma conta?", "Reutilizar a mesma senha", "Ativar autenticação em dois fatores", "Compartilhar a senha", "Desativar atualizações", "B", "A autenticação em dois fatores adiciona uma segunda camada de proteção."),
    ("Vendas e Negociação", "Na venda consultiva, a primeira etapa essencial é:", "Oferecer o produto mais caro", "Compreender as necessidades do cliente", "Encerrar rapidamente", "Evitar perguntas", "B", "A venda consultiva começa pelo diagnóstico das necessidades."),
    ("Língua Portuguesa", "Assinale a alternativa com concordância adequada:", "Fazem dois anos que estudo", "Houveram muitos candidatos", "Faz dois anos que estudo", "Existe muitas vagas", "C", "O verbo fazer indicando tempo decorrido é impessoal e fica no singular."),
    ("Atualidades do Mercado Financeiro", "O Pix é um sistema de pagamentos instantâneos criado por:", "Banco Central do Brasil", "Banco do Brasil", "Tesouro Nacional", "CVM", "A", "O Pix foi criado e é gerido pelo Banco Central do Brasil."),
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                weight INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                statement TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                answer TEXT NOT NULL,
                explanation TEXT
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                selected TEXT NOT NULL,
                correct INTEGER NOT NULL,
                attempted_at TEXT NOT NULL
            );
            """
        )
        for name, weight in SUBJECTS:
            conn.execute("INSERT OR IGNORE INTO subjects(name, weight) VALUES (?, ?)", (name, weight))
        count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        if count == 0:
            conn.executemany(
                """INSERT INTO questions(subject, statement, option_a, option_b, option_c, option_d, answer, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                QUESTIONS,
            )
        conn.commit()


def load_df(query, params=()):
    with connect() as conn:
        return pd.read_sql_query(query, conn, params=params)


st.set_page_config(page_title="BB Master AI", page_icon="🏦", layout="wide")
init_db()

st.title("🏦 BB Master AI")
st.caption("Plataforma pessoal de preparação para o concurso do Banco do Brasil")

page = st.sidebar.radio("Navegação", ["Painel", "Plano de estudos", "Questões", "Registrar estudo", "Conteúdo programático"])

if page == "Painel":
    sessions = load_df("SELECT * FROM study_sessions")
    attempts = load_df("SELECT * FROM attempts")
    total_minutes = int(sessions["minutes"].sum()) if not sessions.empty else 0
    total_attempts = len(attempts)
    accuracy = (attempts["correct"].mean() * 100) if total_attempts else 0
    studied_days = sessions["session_date"].nunique() if not sessions.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Horas estudadas", f"{total_minutes / 60:.1f}")
    c2.metric("Questões respondidas", total_attempts)
    c3.metric("Taxa de acertos", f"{accuracy:.1f}%")
    c4.metric("Dias com estudo", studied_days)

    st.subheader("Desempenho por matéria")
    performance = load_df(
        """
        SELECT q.subject AS Matéria, COUNT(a.id) AS Questões,
               ROUND(100.0 * AVG(a.correct), 1) AS Acertos
        FROM attempts a JOIN questions q ON q.id = a.question_id
        GROUP BY q.subject ORDER BY Acertos ASC
        """
    )
    if performance.empty:
        st.info("Responda algumas questões para começar a gerar seu diagnóstico.")
    else:
        st.dataframe(performance, use_container_width=True, hide_index=True)
        st.bar_chart(performance.set_index("Matéria")["Acertos"])

    st.subheader("Tempo estudado por matéria")
    by_subject = load_df("SELECT subject AS Matéria, SUM(minutes) AS Minutos FROM study_sessions GROUP BY subject ORDER BY Minutos DESC")
    if by_subject.empty:
        st.info("Registre sua primeira sessão de estudo.")
    else:
        st.bar_chart(by_subject.set_index("Matéria")["Minutos"])

elif page == "Plano de estudos":
    st.subheader("Plano semanal sugerido")
    subjects = load_df("SELECT name, weight FROM subjects ORDER BY weight DESC")
    weekly_hours = st.slider("Horas disponíveis por semana", 5, 40, 20)
    subjects["Horas/semana"] = (subjects["weight"] / subjects["weight"].sum() * weekly_hours).round(1)
    subjects["Estratégia"] = subjects["Horas/semana"].apply(lambda h: "Teoria + questões + revisão" if h >= 2 else "Revisão + questões")
    st.dataframe(subjects.rename(columns={"name": "Matéria", "weight": "Peso relativo"}), use_container_width=True, hide_index=True)
    st.info("Priorize matérias de maior peso e aquelas em que sua taxa de acertos estiver abaixo de 70%.")

elif page == "Questões":
    st.subheader("Banco de questões")
    subjects = load_df("SELECT DISTINCT subject FROM questions ORDER BY subject")["subject"].tolist()
    chosen_subject = st.selectbox("Matéria", ["Todas"] + subjects)
    if "question_offset" not in st.session_state:
        st.session_state.question_offset = 0
    params = () if chosen_subject == "Todas" else (chosen_subject,)
    where = "" if chosen_subject == "Todas" else "WHERE subject = ?"
    questions = load_df(f"SELECT * FROM questions {where} ORDER BY id", params)
    if questions.empty:
        st.warning("Nenhuma questão cadastrada.")
    else:
        index = st.session_state.question_offset % len(questions)
        q = questions.iloc[index]
        st.caption(f"{q['subject']} • questão {index + 1} de {len(questions)}")
        st.markdown(f"### {q['statement']}")
        options = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}
        selected = st.radio("Escolha uma alternativa", list(options), format_func=lambda x: f"{x}) {options[x]}", key=f"q_{q['id']}_{index}")
        col1, col2 = st.columns(2)
        if col1.button("Responder", type="primary", use_container_width=True):
            correct = int(selected == q["answer"])
            with connect() as conn:
                conn.execute("INSERT INTO attempts(question_id, selected, correct, attempted_at) VALUES (?, ?, ?, ?)",
                             (int(q["id"]), selected, correct, datetime.now().isoformat(timespec="seconds")))
                conn.commit()
            if correct:
                st.success("Resposta correta!")
            else:
                st.error(f"Resposta incorreta. Gabarito: {q['answer']}.")
            st.write(q["explanation"])
        if col2.button("Próxima questão", use_container_width=True):
            st.session_state.question_offset += 1
            st.rerun()

elif page == "Registrar estudo":
    st.subheader("Registrar sessão de estudo")
    subjects = load_df("SELECT name FROM subjects ORDER BY name")["name"].tolist()
    with st.form("study_form", clear_on_submit=True):
        subject = st.selectbox("Matéria", subjects)
        minutes = st.number_input("Minutos estudados", min_value=5, max_value=600, value=60, step=5)
        study_date = st.date_input("Data", value=date.today())
        notes = st.text_area("Anotações", placeholder="Ex.: juros compostos, 30 questões, revisar erros amanhã")
        submitted = st.form_submit_button("Salvar sessão", type="primary")
    if submitted:
        with connect() as conn:
            conn.execute("INSERT INTO study_sessions(subject, minutes, session_date, notes) VALUES (?, ?, ?, ?)",
                         (subject, int(minutes), study_date.isoformat(), notes))
            conn.commit()
        st.success("Sessão registrada.")

elif page == "Conteúdo programático":
    st.subheader("Conteúdo programático inicial")
    st.warning("Base inicial inspirada na última seleção pública. Atualize este conteúdo quando um novo edital oficial for publicado.")
    topics = {
        "Língua Portuguesa": ["Interpretação de textos", "Ortografia", "Classes de palavras", "Concordância", "Regência", "Crase", "Pontuação"],
        "Matemática Financeira": ["Juros simples e compostos", "Taxas", "Descontos", "Séries uniformes", "Sistemas de amortização"],
        "Conhecimentos Bancários": ["Sistema Financeiro Nacional", "Produtos bancários", "Mercado de capitais", "Câmbio", "Garantias", "Lavagem de dinheiro", "LGPD"],
        "Informática": ["Segurança da informação", "Microsoft 365", "Internet", "Sistemas operacionais", "Banco de dados", "Ferramentas colaborativas"],
        "Vendas e Negociação": ["Venda consultiva", "Experiência do cliente", "Técnicas de negociação", "Marketing digital", "Ética", "Atendimento"],
    }
    for subject, items in topics.items():
        with st.expander(subject):
            for item in items:
                st.checkbox(item, key=f"topic_{subject}_{item}")
