from __future__ import annotations

import html

import streamlit as st


def render_focus_hero(
    name: str,
    streak: int,
    accuracy: float,
    study_minutes: int,
    due_reviews: int,
) -> None:
    hours = study_minutes // 60
    minutes = study_minutes % 60
    study_label = f"{hours}h {minutes:02d}m" if hours else f"{minutes} min"
    safe_name = html.escape(name)

    if due_reviews:
        priority = f"Você tem {due_reviews} revisão(ões) aguardando hoje."
    elif accuracy < 70:
        priority = "Prioridade de hoje: consolidar os pontos fracos com questões e revisão."
    else:
        priority = "Bom ritmo. Mantenha consistência e aumente gradualmente o volume de questões."

    st.markdown(
        f"""
        <section class="focus-hero">
          <div class="focus-hero-copy">
            <div class="focus-eyebrow">PAINEL DE FOCO</div>
            <h2>{safe_name}, transforme estudo em execução.</h2>
            <p>{html.escape(priority)} O ConcursoAI organiza sua rotina para você decidir rapidamente o que estudar, revisar e praticar.</p>
          </div>
          <div class="focus-hero-side">
            <div class="focus-stat"><strong>{streak} dias</strong><span>sequência atual</span></div>
            <div class="focus-stat"><strong>{accuracy:.0f}%</strong><span>acertos em 7 dias</span></div>
            <div class="focus-stat"><strong>{study_label}</strong><span>estudo em 7 dias</span></div>
            <div class="focus-stat"><strong>{due_reviews}</strong><span>revisões hoje</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
