from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from components.charts import PLOT_CONFIG, accuracy_evolution_chart, subject_bar_chart
from database.database import load_df


def _subject_stats() -> pd.DataFrame:
    return load_df(
        """
        SELECT q.subject AS Matéria,
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


def _daily_accuracy(days: int = 14) -> pd.DataFrame:
    start = date.today() - timedelta(days=days - 1)
    raw = load_df(
        """
        SELECT date(attempted_at) AS day,
               ROUND(100.0 * AVG(correct), 1) AS accuracy
          FROM attempts
         WHERE date(attempted_at) >= ?
         GROUP BY date(attempted_at)
         ORDER BY day
        """,
        (start.isoformat(),),
    )
    accuracy_map = {row.day: float(row.accuracy) for row in raw.itertuples(index=False)}
    rows = []
    for offset in range(days):
        current = start + timedelta(days=offset)
        rows.append({"Dia": current.strftime("%d/%m"), "Acertos": accuracy_map.get(current.isoformat(), 0.0)})
    return pd.DataFrame(rows)


def render_statistics_page() -> None:
    st.markdown("## 📊 Estatísticas")
    st.caption("Visão consolidada das questões, estudo, revisões e flashcards.")
    attempts = load_df("SELECT COUNT(*) AS total, COALESCE(SUM(correct), 0) AS correct FROM attempts")
    study = load_df("SELECT COALESCE(SUM(minutes), 0) AS minutes FROM study_sessions")
    simulations = load_df("SELECT COUNT(*) AS total FROM simulations")
    reviews = load_df("SELECT COUNT(*) AS total FROM reviews WHERE last_reviewed_at IS NOT NULL")
    row = attempts.iloc[0]
    total = int(row["total"])
    correct = int(row["correct"])
    accuracy = 100 * correct / total if total else 0
    cols = st.columns(4)
    cols[0].metric("Questões", total)
    cols[1].metric("Aproveitamento", f"{accuracy:.1f}%")
    cols[2].metric("Tempo estudado", f"{int(study.iloc[0]['minutes']) / 60:.1f}h")
    cols[3].metric("Revisões", int(reviews.iloc[0]["total"]))

    subjects = _subject_stats()
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### Desempenho por matéria")
        if subjects.empty:
            st.info("Responda questões para gerar estatísticas.")
        else:
            st.dataframe(subjects, use_container_width=True, hide_index=True)
    with right:
        st.markdown("### Comparativo")
        if not subjects.empty:
            st.plotly_chart(
                subject_bar_chart(subjects.rename(columns={"Aproveitamento": "Aproveitamento"})[["Matéria", "Aproveitamento"]]),
                use_container_width=True,
                config=PLOT_CONFIG,
            )

    st.markdown("### Evolução dos últimos 14 dias")
    st.plotly_chart(accuracy_evolution_chart(_daily_accuracy(14)), use_container_width=True, config=PLOT_CONFIG)

    extra = st.columns(3)
    extra[0].metric("Simulados concluídos", int(simulations.iloc[0]["total"]))
    flashcards = load_df("SELECT COUNT(*) AS total FROM flashcards")
    extra[1].metric("Flashcards", int(flashcards.iloc[0]["total"]))
    errors = load_df("SELECT COUNT(*) AS total FROM error_notebook WHERE reviewed = 0")
    extra[2].metric("Erros pendentes", int(errors.iloc[0]["total"]))


def render_performance_page() -> None:
    st.markdown("## 📈 Desempenho")
    st.caption("Identifique matérias fortes, pontos de atenção e prioridades para a próxima sessão.")
    subjects = _subject_stats()
    if subjects.empty:
        st.info("Ainda não há dados suficientes.")
        return

    strongest = subjects.sort_values(["Aproveitamento", "Respondidas"], ascending=[False, False]).iloc[0]
    weakest = subjects.sort_values(["Aproveitamento", "Respondidas"], ascending=[True, False]).iloc[0]
    most_practiced = subjects.sort_values("Respondidas", ascending=False).iloc[0]
    cols = st.columns(3)
    cols[0].metric("Melhor matéria", strongest["Matéria"], f"{strongest['Aproveitamento']:.0f}%")
    cols[1].metric("Prioridade", weakest["Matéria"], f"{weakest['Aproveitamento']:.0f}%")
    cols[2].metric("Mais praticada", most_practiced["Matéria"], f"{int(most_practiced['Respondidas'])} questões")

    st.plotly_chart(subject_bar_chart(subjects[["Matéria", "Aproveitamento"]]), use_container_width=True, config=PLOT_CONFIG)
    st.markdown("### Recomendações")
    for row in subjects.sort_values("Aproveitamento").head(3).itertuples(index=False):
        if float(row.Aproveitamento) < 60:
            strategy = "retomar teoria, revisar erros e resolver blocos de 5 questões"
        elif float(row.Aproveitamento) < 80:
            strategy = "consolidar com questões médias e revisão espaçada"
        else:
            strategy = "manter com questões difíceis e simulados"
        st.markdown(
            f"""
            <div class="review-item">
              <div class="review-icon">📌</div>
              <div class="review-text"><strong>{row.Matéria}</strong><span>{row.Aproveitamento:.0f}% de acerto — {strategy}</span></div>
              <div class="review-date">{int(row.Respondidas)} questões</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
