from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import connect, load_df


def _subject_stats(subject: str) -> tuple[int, float, int]:
    params: tuple[object, ...] = () if subject == "Todas" else (subject,)
    where = "" if subject == "Todas" else "WHERE q.subject = ?"
    frame = load_df(
        f"""
        SELECT COUNT(a.id) AS attempts,
               COALESCE(100.0 * AVG(a.correct), 0) AS accuracy,
               COALESCE(SUM(CASE WHEN a.correct = 0 THEN 1 ELSE 0 END), 0) AS errors
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
          {where}
        """,
        params,
    )
    row = frame.iloc[0]
    return int(row["attempts"]), float(row["accuracy"]), int(row["errors"])


def _matching_content(prompt: str, subject: str) -> pd.DataFrame:
    words = [word.strip(".,!?;:").lower() for word in prompt.split() if len(word.strip(".,!?;:")) >= 4]
    conditions: list[str] = []
    params: list[object] = []
    if subject != "Todas":
        conditions.append("subject = ?")
        params.append(subject)
    word_conditions: list[str] = []
    for word in words[:5]:
        word_conditions.append("(LOWER(statement) LIKE ? OR LOWER(explanation) LIKE ? OR LOWER(assunto) LIKE ? OR LOWER(tags) LIKE ?)")
        term = f"%{word}%"
        params.extend([term] * 4)
    if word_conditions:
        conditions.append(f"({' OR '.join(word_conditions)})")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return load_df(
        f"""
        SELECT subject, assunto, statement, answer, explanation
          FROM questions
          {where}
         ORDER BY subject, id
         LIMIT 3
        """,
        tuple(params),
    )


def build_local_response(prompt: str, subject: str) -> str:
    attempts, accuracy, errors = _subject_stats(subject)
    content = _matching_content(prompt, subject)
    scope = "seu desempenho geral" if subject == "Todas" else f"seu desempenho em **{subject}**"

    if attempts == 0:
        diagnosis = f"Ainda não há respostas suficientes para avaliar {scope}. Comece com 10 questões e volte ao diagnóstico."
    elif accuracy >= 80:
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). O desempenho é forte; priorize manutenção e questões difíceis."
    elif accuracy >= 60:
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). A base está evoluindo, mas os {errors} erro(s) ainda precisam de revisão ativa."
    else:
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). Recomendo voltar à teoria, revisar os erros e resolver blocos menores de questões."

    parts = [diagnosis]
    if not content.empty:
        parts.append("\n\n**Pontos do seu banco de conteúdo relacionados à pergunta:**")
        for row in content.itertuples(index=False):
            explanation = row.explanation or f"Gabarito: {row.answer}."
            parts.append(f"\n- **{row.assunto or row.subject}:** {explanation}")
    else:
        parts.append("\n\nNão encontrei uma questão diretamente relacionada no banco local. Use palavras do edital, da matéria ou do assunto para uma resposta mais específica.")

    parts.append(
        "\n\n**Plano recomendado agora:**\n"
        "1. Revise as questões erradas pendentes.\n"
        "2. Faça 10 questões do assunto.\n"
        "3. Transforme os pontos difíceis em flashcards.\n"
        "4. Refaça a revisão na data programada."
    )
    return "".join(parts)


def save_note(subject: str, prompt: str, response: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO professor_notes(subject, prompt, response, created_at) VALUES (?, ?, ?, ?)",
            (subject, prompt, response, datetime.now().isoformat(timespec="seconds")),
        )
        connection.commit()


def render_professor_page() -> None:
    st.markdown("## 🤖 Professor IA")
    st.caption("Tutor inteligente local, conectado ao seu desempenho, questões, erros e flashcards.")

    subjects = load_df("SELECT name FROM subjects ORDER BY name")
    subject = st.selectbox("Foco da conversa", ["Todas"] + subjects["name"].tolist(), key="prof_subject")

    attempts, accuracy, errors = _subject_stats(subject)
    cols = st.columns(3)
    cols[0].metric("Questões analisadas", attempts)
    cols[1].metric("Aproveitamento", f"{accuracy:.0f}%")
    cols[2].metric("Erros registrados", errors)

    st.info(
        "O Professor IA desta versão funciona em modo local: analisa seu banco e gera orientação sem enviar seus dados para serviços externos."
    )

    st.session_state.setdefault("professor_messages", [])
    for message in st.session_state.professor_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Pergunte sobre uma matéria, erro, assunto ou estratégia de estudo")
    if prompt:
        st.session_state.professor_messages.append({"role": "user", "content": prompt})
        response = build_local_response(prompt, subject)
        st.session_state.professor_messages.append({"role": "assistant", "content": response})
        save_note(subject, prompt, response)
        st.rerun()

    with st.expander("Sugestões de perguntas"):
        st.markdown(
            "- Onde estou errando mais?\n"
            "- Como estudar conhecimentos bancários esta semana?\n"
            "- Explique juros simples com base nas minhas questões.\n"
            "- Qual matéria devo priorizar hoje?"
        )
