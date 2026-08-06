from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import connect, load_df
from services.ai_client import ai_available, chat_completion, get_ai_config


STYLE_MAP = {
    "Explicação didática": "explicação didática com conceito, exemplo curto e armadilha de prova",
    "Plano de estudo": "plano de estudo prático, dividido em etapas, com tempo e quantidade de questões",
    "Resposta objetiva": "resposta direta e objetiva, sem introduções longas",
    "Revisão para prova": "resumo de revisão com pontos-chave, erros comuns e cinco perguntas de checagem",
}


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
        word_conditions.append(
            "(LOWER(statement) LIKE ? OR LOWER(explanation) LIKE ? OR LOWER(assunto) LIKE ? OR LOWER(tags) LIKE ?)"
        )
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
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). Priorize manutenção e questões difíceis."
    elif accuracy >= 60:
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). A base está evoluindo, mas os {errors} erro(s) precisam de revisão ativa."
    else:
        diagnosis = f"Você está com **{accuracy:.0f}% de aproveitamento** em {attempts} resposta(s). Retome a teoria, revise os erros e faça blocos menores de questões."

    parts = [diagnosis]
    if not content.empty:
        parts.append("\n\n**Pontos relacionados encontrados no banco local:**")
        for row in content.itertuples(index=False):
            explanation = row.explanation or f"Gabarito: {row.answer}."
            parts.append(f"\n- **{row.assunto or row.subject}:** {explanation}")
    else:
        parts.append("\n\nNão encontrei conteúdo diretamente relacionado no banco local.")

    parts.append(
        "\n\n**Próxima ação recomendada:**\n"
        "1. Revise os erros pendentes.\n"
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


def _generate_response(prompt: str, subject: str, mode: str, style: str) -> tuple[str, str]:
    history = list(st.session_state.get("professor_messages", []))
    use_online = mode == "IA online" or (mode == "Automático" and ai_available())
    if use_online:
        try:
            result = chat_completion(
                prompt=prompt,
                subject=subject,
                response_style=STYLE_MAP[style],
                history=history,
            )
            source = f"{result.provider} • {result.model} • {result.latency_ms / 1000:.1f}s"
            return result.content, source
        except RuntimeError as exc:
            if mode == "IA online":
                raise
            local = build_local_response(prompt, subject)
            return local, f"Modo local após falha da IA: {exc}"
    return build_local_response(prompt, subject), "Modo local"


def _submit_prompt(prompt: str, subject: str, mode: str, style: str) -> None:
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return
    st.session_state.professor_messages.append({"role": "user", "content": clean_prompt})
    try:
        response, source = _generate_response(clean_prompt, subject, mode, style)
    except RuntimeError as exc:
        response = f"Não foi possível consultar a IA online. **{exc}**"
        source = "Erro de conexão"
    st.session_state.professor_messages.append(
        {"role": "assistant", "content": response, "source": source}
    )
    save_note(subject, clean_prompt, response)


def render_professor_page() -> None:
    st.markdown("## 🤖 Professor IA")
    st.caption("Tutor conectado ao seu desempenho, caderno de erros, questões e revisões.")

    subjects = load_df("SELECT name FROM subjects ORDER BY name")
    controls = st.columns([1.2, 1, 1])
    subject = controls[0].selectbox("Foco da conversa", ["Todas"] + subjects["name"].tolist(), key="prof_subject")
    mode = controls[1].selectbox("Modo", ["Automático", "IA online", "Local"], key="prof_mode")
    style = controls[2].selectbox("Formato", list(STYLE_MAP), key="prof_style")

    attempts, accuracy, errors = _subject_stats(subject)
    cols = st.columns(3)
    cols[0].metric("Questões analisadas", attempts)
    cols[1].metric("Aproveitamento", f"{accuracy:.0f}%")
    cols[2].metric("Erros registrados", errors)

    if ai_available():
        config = get_ai_config()
        st.success(f"IA online configurada — {config.provider} / {config.model}")
        st.caption("Ao usar IA online, sua pergunta e um resumo do desempenho são enviados ao provedor configurado.")
    else:
        st.info("Modo local ativo. Configure `GROQ_API_KEY` nos segredos para habilitar a IA online.")

    st.session_state.setdefault("professor_messages", [])

    quick = st.columns(4)
    quick_prompts = [
        "Onde estou errando mais e o que devo estudar hoje?",
        "Monte um plano de estudo de 7 dias com base no meu desempenho.",
        "Explique meu assunto mais fraco com um exemplo de prova.",
        "Crie uma revisão rápida dos meus erros recentes.",
    ]
    for index, (column, text) in enumerate(zip(quick, quick_prompts)):
        if column.button(text, key=f"prof_quick_{index}", use_container_width=True):
            _submit_prompt(text, subject, mode, style)
            st.rerun()

    for message in st.session_state.professor_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("source"):
                st.caption(message["source"])

    prompt = st.chat_input("Pergunte sobre uma matéria, erro, questão ou estratégia de estudo")
    if prompt:
        _submit_prompt(prompt, subject, mode, style)
        st.rerun()

    if st.session_state.professor_messages:
        if st.button("Limpar conversa", key="clear_professor_chat"):
            st.session_state.professor_messages = []
            st.rerun()
