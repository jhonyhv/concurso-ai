from __future__ import annotations

import streamlit as st

from database.database import get_settings
from utils.version import get_version_label

SECTIONS = [
    ("", [("Dashboard", "⌂")]),
    ("ESTUDOS", [("Estudar", "▣"), ("Questões", "?"), ("Simulados", "✎"), ("Flashcards", "▤")]),
    ("INTELIGÊNCIA", [("Professor IA", "✦")]),
    ("ANÁLISES", [("Estatísticas", "▥"), ("Desempenho", "↗"), ("Revisões", "◷")]),
    ("GESTÃO", [("Metas", "◎"), ("Calendário", "□"), ("Coletor automático", "⇄"), ("Configurações", "⚙")]),
]


def render_sidebar() -> str:
    settings = get_settings()
    version_label = get_version_label()
    st.session_state.setdefault("current_page", "Dashboard")

    with st.sidebar:
        st.markdown(
            """
            <div class="brand-box brand-v2">
              <div class="brand-mark brand-bank">CA</div>
              <div><strong>Concurso<span>AI</span></strong><small>Preparação Banco do Brasil</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for heading, items in SECTIONS:
            if heading:
                st.markdown(f'<div class="nav-section">{heading}</div>', unsafe_allow_html=True)
            for page, icon in items:
                active = st.session_state.current_page == page
                if st.button(
                    f"{icon}   {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state.current_page = page

        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="upgrade-card premium-card">
              <div class="upgrade-icon">⚡</div>
              <strong>Rota de aprovação</strong>
              <p>{settings['user_name']}, acompanhe estudo, revisões, questões e evolução em um único painel.</p>
              <div class="premium-pill">v{version_label} • Catálogo revisado</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return str(st.session_state.current_page)
