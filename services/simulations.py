from __future__ import annotations

import random
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import connect, load_df


def _available_questions(subject: str) -> pd.DataFrame:
    if subject == "Todas":
        return load_df("SELECT * FROM questions ORDER BY id")
    return load_df("SELECT * FROM questions WHERE subject = ? ORDER BY id", (subject,))


def _start_simulation(subject: str, quantity: int) -> None:
    questions = _available_questions(subject)
    quantity = min(quantity, len(questions))
    ids = questions["id"].astype(int).tolist()
    st.session_state.simulation_ids = random.sample(ids, quantity)
    st.session_state.simulation_index = 0
    st.session_state.simulation_answers = {}
    st.session_state.simulation_started = time.time()
    st.session_state.simulation_subject = subject
    st.session_state.simulation_finished = False


def _finish_simulation() -> None:
    ids = st.session_state.simulation_ids
    answers = st.session_state.simulation_answers
    elapsed = max(0, int(time.time() - st.session_state.simulation_started))
    placeholders = ",".join("?" for _ in ids)
    questions = load_df(f"SELECT id, answer FROM questions WHERE id IN ({placeholders})", tuple(ids))
    answer_map = {int(row.id): str(row.answer).upper() for row in questions.itertuples(index=False)}
    correct = sum(1 for question_id, selected in answers.items() if selected == answer_map.get(question_id))
    started_at = datetime.fromtimestamp(st.session_state.simulation_started).isoformat(timespec="seconds")
    finished_at = datetime.now().isoformat(timespec="seconds")

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO simulations(title, started_at, finished_at, total_questions, correct_answers, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"Simulado - {st.session_state.simulation_subject}",
                started_at,
                finished_at,
                len(ids),
                correct,
                elapsed,
            ),
        )
        simulation_id = int(cursor.lastrowid)
        for question_id in ids:
            selected = answers.get(question_id, "-")
            is_correct = int(selected == answer_map.get(question_id))
            connection.execute(
                """
                INSERT INTO simulation_answers(simulation_id, question_id, selected, correct)
                VALUES (?, ?, ?, ?)
                """,
                (simulation_id, question_id, selected, is_correct),
            )
            if selected != "-":
                connection.execute(
                    """
                    INSERT INTO attempts(question_id, selected, correct, attempted_at, elapsed_seconds)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (question_id, selected, is_correct, finished_at),
                )
                if not is_correct:
                    connection.execute(
                        """
                        INSERT INTO error_notebook(question_id, error_count, last_error_at, reviewed)
                        VALUES (?, 1, ?, 0)
                        ON CONFLICT(question_id) DO UPDATE SET
                            error_count = error_count + 1,
                            last_error_at = excluded.last_error_at,
                            reviewed = 0
                        """,
                        (question_id, finished_at),
                    )
        connection.commit()

    st.session_state.simulation_result = {
        "correct": correct,
        "total": len(ids),
        "elapsed": elapsed,
        "answers": answers,
        "answer_map": answer_map,
    }
    st.session_state.simulation_finished = True


def _render_running() -> None:
    ids: list[int] = st.session_state.simulation_ids
    index = int(st.session_state.simulation_index)
    question_id = ids[index]
    question = load_df("SELECT * FROM questions WHERE id = ?", (question_id,)).iloc[0]

    elapsed = max(0, int(time.time() - st.session_state.simulation_started))
    minutes, seconds = divmod(elapsed, 60)
    top = st.columns([3, 1])
    top[0].progress((index + 1) / len(ids), text=f"Questão {index + 1} de {len(ids)}")
    top[1].metric("Tempo", f"{minutes:02d}:{seconds:02d}")

    st.markdown(f"### {question['statement']}")
    letters = ["A", "B", "C", "D"]
    if pd.notna(question.get("option_e")) and str(question.get("option_e") or "").strip():
        letters.append("E")
    options = {letter: str(question[f"option_{letter.lower()}"]) for letter in letters}
    previous = st.session_state.simulation_answers.get(question_id)
    default_index = letters.index(previous) if previous in letters else None
    selected = st.radio(
        "Escolha uma alternativa",
        letters,
        index=default_index,
        format_func=lambda letter: f"{letter}) {options[letter]}",
        key=f"simulation_question_{question_id}",
    )
    if selected:
        st.session_state.simulation_answers[question_id] = selected

    cols = st.columns([1, 1, 2])
    if cols[0].button("← Anterior", disabled=index == 0, use_container_width=True):
        st.session_state.simulation_index = index - 1
        st.rerun()
    if cols[1].button("Próxima →", disabled=index == len(ids) - 1, use_container_width=True):
        st.session_state.simulation_index = index + 1
        st.rerun()
    if cols[2].button("Finalizar simulado", type="primary", use_container_width=True):
        _finish_simulation()
        st.rerun()


def _render_result() -> None:
    result = st.session_state.simulation_result
    accuracy = 100 * result["correct"] / max(1, result["total"])
    minutes, seconds = divmod(result["elapsed"], 60)
    st.success("Simulado concluído!")
    cols = st.columns(3)
    cols[0].metric("Acertos", f"{result['correct']}/{result['total']}")
    cols[1].metric("Aproveitamento", f"{accuracy:.0f}%")
    cols[2].metric("Tempo", f"{minutes:02d}:{seconds:02d}")
    if st.button("Iniciar novo simulado", type="primary"):
        for key in [
            "simulation_ids", "simulation_index", "simulation_answers",
            "simulation_started", "simulation_subject", "simulation_finished", "simulation_result"
        ]:
            st.session_state.pop(key, None)
        st.rerun()


def render_simulations_page() -> None:
    st.markdown("## 📝 Simulados")
    st.caption("Monte provas rápidas, responda sem feedback imediato e acompanhe o resultado final.")

    if st.session_state.get("simulation_finished"):
        _render_result()
    elif st.session_state.get("simulation_ids"):
        _render_running()
    else:
        subjects = load_df("SELECT DISTINCT subject FROM questions ORDER BY subject")
        subject = st.selectbox("Matéria", ["Todas"] + subjects["subject"].tolist())
        available = len(_available_questions(subject))
        if available == 0:
            st.warning("Não há questões disponíveis.")
        else:
            quantity = st.slider("Quantidade de questões", 1, available, min(5, available))
            st.info("O resultado e o gabarito serão mostrados somente ao finalizar.")
            if st.button("Começar simulado", type="primary", use_container_width=True):
                _start_simulation(subject, quantity)
                st.rerun()

    st.markdown("### Histórico")
    history = load_df(
        """
        SELECT title AS Simulado, started_at AS Data,
               total_questions AS Questões, correct_answers AS Acertos,
               ROUND(100.0 * correct_answers / total_questions, 1) AS Aproveitamento,
               duration_seconds AS Segundos
          FROM simulations
         ORDER BY id DESC
         LIMIT 20
        """
    )
    if history.empty:
        st.info("Nenhum simulado concluído ainda.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)
