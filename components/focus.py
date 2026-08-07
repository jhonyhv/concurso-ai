from __future__ import annotations

import html

import streamlit as st


def render_focus_hero(name: str, due_reviews: int) -> None:
    safe_name = html.escape(name)

    if due_reviews:
        priority = f"Você tem {due_reviews} revisão(ões) aguardando hoje."
        next_title = f"Revisar {due_reviews} item(ns) pendente(s)"
        next_detail = "Comece pelas revisões e depois avance para um bloco curto de questões."
    else:
        priority = "Sua fila de revisão está em dia."
        next_title = "Resolver um bloco de 10 questões"
        next_detail = "Use o desempenho do bloco para escolher o próximo assunto de estudo."

    st.markdown(
        f"""
        <section class="focus-hero">
          <div class="focus-hero-copy">
            <div class="focus-eyebrow">FOCO DE HOJE</div>
            <h2>{safe_name}, transforme estudo em execução.</h2>
            <p>{html.escape(priority)} O painel abaixo mostra seu ritmo, desempenho e o que merece atenção agora.</p>
          </div>
          <div class="focus-next-card">
            <span>PRÓXIMO PASSO</span>
            <strong>{html.escape(next_title)}</strong>
            <small>{html.escape(next_detail)}</small>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
