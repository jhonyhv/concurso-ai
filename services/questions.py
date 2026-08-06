from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from database.database import connect, load_df

ALL = "Todos"


def get_filter_options() -> dict[str, list[str]]:
    """Carrega as opções disponíveis diretamente do banco."""
    columns = {
        "concursos": "concurso",
        "bancas": "banca",
        "materias": "subject",
        "assuntos": "assunto",
        "dificuldades": "dificuldade",
    }
    result: dict[str, list[str]] = {}
    for key, column in columns.items():
        frame = load_df(
            f"""
            SELECT DISTINCT {column} AS value
              FROM questions
             WHERE {column} IS NOT NULL AND TRIM({column}) <> ''
             ORDER BY {column}
            """
        )
        result[key] = frame["value"].astype(str).tolist() if not frame.empty else []
    return result


def get_questions(
    *,
    search: str = "",
    concurso: str = ALL,
    banca: str = ALL,
    subject: str = ALL,
    assunto: str = ALL,
    dificuldade: str = ALL,
    favorites_only: bool = False,
    errors_only: bool = False,
) -> pd.DataFrame:
    conditions: list[str] = []
    params: list[Any] = []

    filters = {
        "concurso": concurso,
        "banca": banca,
        "subject": subject,
        "assunto": assunto,
        "dificuldade": dificuldade,
    }
    for column, value in filters.items():
        if value and value != ALL:
            conditions.append(f"q.{column} = ?")
            params.append(value)

    if search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            """
            (q.statement LIKE ? OR q.explanation LIKE ? OR q.assunto LIKE ?
             OR q.subassunto LIKE ? OR q.tags LIKE ?)
            """
        )
        params.extend([term] * 5)

    if favorites_only:
        conditions.append("q.favorite = 1")

    if errors_only:
        conditions.append("EXISTS (SELECT 1 FROM error_notebook e WHERE e.question_id = q.id)")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return load_df(
        f"""
        SELECT q.*,
               COALESCE((SELECT COUNT(*) FROM attempts a WHERE a.question_id = q.id), 0) AS attempts_count,
               COALESCE((SELECT SUM(a.correct) FROM attempts a WHERE a.question_id = q.id), 0) AS correct_count
          FROM questions q
          {where}
         ORDER BY q.favorite DESC, q.subject, q.id
        """,
        tuple(params),
    )


def toggle_favorite(question_id: int) -> bool:
    with connect() as connection:
        connection.execute(
            "UPDATE questions SET favorite = CASE favorite WHEN 1 THEN 0 ELSE 1 END WHERE id = ?",
            (question_id,),
        )
        favorite = connection.execute(
            "SELECT favorite FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        connection.commit()
    return bool(favorite["favorite"]) if favorite else False


def save_attempt(
    question_id: int,
    selected: str,
    elapsed_seconds: int = 0,
) -> dict[str, Any]:
    selected = selected.upper().strip()
    if selected not in {"A", "B", "C", "D", "E"}:
        raise ValueError("Alternativa inválida.")

    attempted_at = datetime.now().isoformat(timespec="seconds")
    with connect() as connection:
        question = connection.execute(
            "SELECT answer, explanation FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        if question is None:
            raise ValueError("Questão não encontrada.")

        correct = int(selected == str(question["answer"]).upper())
        connection.execute(
            """
            INSERT INTO attempts(
                question_id, selected, correct, attempted_at, elapsed_seconds
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (question_id, selected, correct, attempted_at, max(0, int(elapsed_seconds))),
        )

        if not correct:
            connection.execute(
                """
                INSERT INTO error_notebook(
                    question_id, error_count, last_error_at, reviewed
                ) VALUES (?, 1, ?, 0)
                ON CONFLICT(question_id) DO UPDATE SET
                    error_count = error_count + 1,
                    last_error_at = excluded.last_error_at,
                    reviewed = 0
                """,
                (question_id, attempted_at),
            )
        connection.commit()

    return {
        "correct": bool(correct),
        "answer": str(question["answer"]).upper(),
        "explanation": question["explanation"] or "",
    }


def get_error_notebook(reviewed: bool | None = None) -> pd.DataFrame:
    where = ""
    params: tuple[Any, ...] = ()
    if reviewed is not None:
        where = "WHERE e.reviewed = ?"
        params = (int(reviewed),)

    return load_df(
        f"""
        SELECT e.question_id, e.error_count, e.last_error_at, e.reviewed, e.notes,
               q.subject, q.assunto, q.dificuldade, q.statement, q.answer,
               q.explanation, q.favorite
          FROM error_notebook e
          JOIN questions q ON q.id = e.question_id
          {where}
         ORDER BY e.reviewed ASC, e.last_error_at DESC
        """,
        params,
    )


def mark_error_reviewed(question_id: int, reviewed: bool = True) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE error_notebook SET reviewed = ? WHERE question_id = ?",
            (int(reviewed), question_id),
        )
        connection.commit()


def get_overall_statistics() -> dict[str, float | int]:
    frame = load_df(
        """
        SELECT COUNT(*) AS attempts,
               COALESCE(SUM(correct), 0) AS correct,
               COALESCE(ROUND(100.0 * AVG(correct), 1), 0) AS accuracy
          FROM attempts
        """
    )
    errors = load_df(
        "SELECT COUNT(*) AS total FROM error_notebook WHERE reviewed = 0"
    )
    favorites = load_df("SELECT COUNT(*) AS total FROM questions WHERE favorite = 1")
    row = frame.iloc[0]
    return {
        "attempts": int(row["attempts"]),
        "correct": int(row["correct"]),
        "accuracy": float(row["accuracy"]),
        "pending_errors": int(errors.iloc[0]["total"]),
        "favorites": int(favorites.iloc[0]["total"]),
    }


def get_subject_statistics() -> pd.DataFrame:
    return load_df(
        """
        SELECT q.subject AS Materia,
               COUNT(a.id) AS Respondidas,
               SUM(a.correct) AS Acertos,
               COUNT(a.id) - SUM(a.correct) AS Erros,
               ROUND(100.0 * AVG(a.correct), 1) AS Aproveitamento
          FROM attempts a
          JOIN questions q ON q.id = a.question_id
         GROUP BY q.subject
         ORDER BY Aproveitamento DESC, Respondidas DESC
        """
    )


def _text(value: Any, fallback: str = "Não informado") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    content = str(value).strip()
    return content if content else fallback


def _render_resolver() -> None:
    options = get_filter_options()

    search = st.text_input(
        "Pesquisar questão",
        placeholder="Digite uma palavra, assunto ou trecho do enunciado",
        key="question_search",
    )

    with st.expander("🔎 Filtros avançados", expanded=True):
        row1 = st.columns(3)
        concurso = row1[0].selectbox(
            "Concurso", [ALL] + options["concursos"], key="filter_concurso"
        )
        banca = row1[1].selectbox(
            "Banca", [ALL] + options["bancas"], key="filter_banca"
        )
        subject = row1[2].selectbox(
            "Matéria", [ALL] + options["materias"], key="filter_subject"
        )

        row2 = st.columns(4)
        assunto = row2[0].selectbox(
            "Assunto", [ALL] + options["assuntos"], key="filter_assunto"
        )
        dificuldade = row2[1].selectbox(
            "Dificuldade",
            [ALL] + options["dificuldades"],
            key="filter_difficulty",
        )
        favorites_only = row2[2].checkbox("Somente favoritas", key="filter_favorites")
        errors_only = row2[3].checkbox("Somente com erros", key="filter_errors")

    signature = (
        search,
        concurso,
        banca,
        subject,
        assunto,
        dificuldade,
        favorites_only,
        errors_only,
    )
    if st.session_state.get("question_filter_signature") != signature:
        st.session_state.question_filter_signature = signature
        st.session_state.question_offset = 0

    questions = get_questions(
        search=search,
        concurso=concurso,
        banca=banca,
        subject=subject,
        assunto=assunto,
        dificuldade=dificuldade,
        favorites_only=favorites_only,
        errors_only=errors_only,
    )

    if questions.empty:
        st.warning("Nenhuma questão encontrada com esses filtros.")
        return

    st.session_state.setdefault("question_offset", 0)
    index = st.session_state.question_offset % len(questions)
    question = questions.iloc[index]
    question_id = int(question["id"])

    top_left, top_right = st.columns([5, 1])
    top_left.caption(
        f"{_text(question['concurso'])} • {_text(question['banca'])} • "
        f"{_text(question['subject'])} • {_text(question['assunto'])} • "
        f"{_text(question['dificuldade'])}"
    )
    favorite_label = "★ Favorita" if int(question["favorite"]) else "☆ Favoritar"
    if top_right.button(
        favorite_label,
        key=f"favorite_{question_id}",
        use_container_width=True,
    ):
        toggle_favorite(question_id)
        st.rerun()

    st.markdown(
        f'<div class="question-counter">Questão {index + 1} de {len(questions)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {question['statement']}")

    letters = ["A", "B", "C", "D"]
    if _text(question.get("option_e"), ""):
        letters.append("E")
    question_options = {
        letter: _text(question[f"option_{letter.lower()}"])
        for letter in letters
    }

    selected = st.radio(
        "Escolha uma alternativa",
        letters,
        index=None,
        format_func=lambda letter: f"{letter}) {question_options[letter]}",
        key=f"question_choice_{question_id}",
    )

    answer_col, previous_col, next_col = st.columns([2, 1, 1])
    if answer_col.button(
        "Responder",
        type="primary",
        use_container_width=True,
        key=f"answer_{question_id}",
    ):
        if selected is None:
            st.warning("Selecione uma alternativa antes de responder.")
        else:
            st.session_state[f"question_feedback_{question_id}"] = save_attempt(
                question_id, selected
            )

    if previous_col.button("← Anterior", use_container_width=True):
        st.session_state.question_offset = (index - 1) % len(questions)
        st.rerun()

    if next_col.button("Próxima →", use_container_width=True):
        st.session_state.question_offset = (index + 1) % len(questions)
        st.rerun()

    feedback = st.session_state.get(f"question_feedback_{question_id}")
    if feedback:
        if feedback["correct"]:
            st.success("Resposta correta!")
        else:
            st.error(f"Resposta incorreta. Gabarito: {feedback['answer']}.")
        if feedback["explanation"]:
            st.info(f"**Comentário:** {feedback['explanation']}")

    attempts_count = int(question["attempts_count"])
    correct_count = int(question["correct_count"])
    if attempts_count:
        accuracy = 100 * correct_count / attempts_count
        st.caption(
            f"Seu histórico nesta questão: {correct_count}/{attempts_count} acertos "
            f"({accuracy:.0f}%)."
        )


def _render_error_notebook() -> None:
    status = st.radio(
        "Exibir",
        ["Pendentes", "Revisadas", "Todas"],
        horizontal=True,
        key="error_status",
    )
    reviewed_filter = {"Pendentes": False, "Revisadas": True, "Todas": None}[status]
    errors = get_error_notebook(reviewed_filter)

    if errors.empty:
        st.info("Nenhuma questão encontrada no caderno de erros.")
        return

    st.caption(f"{len(errors)} questão(ões) no caderno.")
    for row in errors.itertuples(index=False):
        status_text = "Revisada" if row.reviewed else "Pendente"
        title = f"{row.subject} • {row.error_count} erro(s) • {status_text}"
        with st.expander(title):
            st.markdown(f"**{row.statement}**")
            st.caption(
                f"Assunto: {_text(row.assunto)} • Dificuldade: {_text(row.dificuldade)} • "
                f"Último erro: {_text(row.last_error_at)}"
            )
            st.markdown(f"**Gabarito:** {row.answer}")
            if row.explanation:
                st.info(row.explanation)

            label = "Marcar como pendente" if row.reviewed else "Marcar como revisada"
            if st.button(label, key=f"review_error_{row.question_id}"):
                mark_error_reviewed(int(row.question_id), not bool(row.reviewed))
                st.rerun()


def _render_statistics() -> None:
    stats = get_overall_statistics()
    columns = st.columns(4)
    columns[0].metric("Questões respondidas", stats["attempts"])
    columns[1].metric("Aproveitamento", f"{stats['accuracy']:.1f}%")
    columns[2].metric("Erros pendentes", stats["pending_errors"])
    columns[3].metric("Favoritas", stats["favorites"])

    subjects = get_subject_statistics()
    st.markdown("### Desempenho por matéria")
    if subjects.empty:
        st.info("Responda questões para gerar as estatísticas.")
        return

    display = subjects.rename(
        columns={
            "Materia": "Matéria",
            "Respondidas": "Respondidas",
            "Acertos": "Acertos",
            "Erros": "Erros",
            "Aproveitamento": "Aproveitamento (%)",
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.bar_chart(
        subjects.set_index("Materia")["Aproveitamento"],
        use_container_width=True,
    )


def render_questions_page() -> None:
    st.subheader("📝 Banco de questões")
    st.caption("Filtre, responda, favorite e revise os assuntos em que teve dificuldade.")
    resolver, errors, statistics = st.tabs(
        ["Resolver questões", "Caderno de erros", "Estatísticas"]
    )
    with resolver:
        _render_resolver()
    with errors:
        _render_error_notebook()
    with statistics:
        _render_statistics()
