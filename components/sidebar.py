from __future__ import annotations

import streamlit as st

SECTIONS = [
    ("", [("Dashboard", "⌂")]),
    ("ESTUDOS", [("Estudar", "▣"), ("Questões", "?"), ("Simulados", "▤"), ("Flashcards", "▥")]),
    ("IA", [("Professor IA", "♙")]),
    ("ANÁLISES", [("Estatísticas", "▥"), ("Desempenho", "⌁"), ("Revisões", "▣")]),
    ("OUTROS", [("Metas", "◎"), ("Calendário", "□"), ("Configurações", "⚙")]),
]


def render_sidebar() -> str:
    st.session_state.setdefault("current_page", "Dashboard")

    with st.sidebar:
        st.markdown(
            """
            <div class="reference-brand">
              <div class="reference-brand-icon">🏛️</div>
              <div class="reference-brand-copy">
                <strong>Concurso<span>AI</span></strong>
                <small>Banco do Brasil Edition</small>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for heading, items in SECTIONS:
            if heading:
                st.markdown(f'<div class="nav-section reference-nav-section">{heading}</div>', unsafe_allow_html=True)
            for page, icon in items:
                active = st.session_state.current_page == page
                if st.button(
                    f"{icon}   {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state.current_page = page
                    st.rerun()

        st.markdown('<div class="reference-sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="reference-premium-card">
              <div class="reference-premium-title"><span>♛</span><strong>Plano Premium</strong></div>
              <p>Desbloqueie todos<br>os recursos</p>
              <div class="reference-premium-button">Assinar agora</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return str(st.session_state.current_page)
