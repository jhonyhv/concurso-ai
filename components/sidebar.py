from __future__ import annotations

import streamlit as st

from utils.version import get_version_label

SECTIONS = [
    ("", [("Dashboard", "◈")]),
    ("ESTUDAR", [("Estudar", "▣"), ("Questões", "◎"), ("Simulados", "◫"), ("Flashcards", "◇")]),
    ("INTELIGÊNCIA", [("Professor IA", "✦")]),
    ("EVOLUÇÃO", [("Estatísticas", "▥"), ("Desempenho", "↗"), ("Revisões", "◷")]),
    ("PLANEJAR", [("Metas", "◉"), ("Calendário", "□"), ("Configurações", "⚙")]),
]


def render_sidebar() -> str:
    st.session_state.setdefault("current_page", "Dashboard")
    version = get_version_label()

    with st.sidebar:
        st.markdown(
            """
            <div class="command-brand">
              <div class="command-logo">CA</div>
              <div class="command-brand-copy">
                <strong>Concurso<span>AI</span></strong>
                <small>Approval Intelligence</small>
              </div>
            </div>
            <div class="command-edition"><span></span> Banco do Brasil Edition</div>
            """,
            unsafe_allow_html=True,
        )

        for heading, items in SECTIONS:
            if heading:
                st.markdown(f'<div class="command-nav-section">{heading}</div>', unsafe_allow_html=True)
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

        st.markdown('<div class="command-sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="command-status-card">
              <div class="command-status-top"><span class="command-live-dot"></span><b>SISTEMA ATIVO</b></div>
              <strong>Modo Banco do Brasil</strong>
              <p>Questões, revisões e IA trabalhando sobre a mesma trilha de preparação.</p>
              <div class="command-version">v{version} <span>•</span> beta</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return str(st.session_state.current_page)
