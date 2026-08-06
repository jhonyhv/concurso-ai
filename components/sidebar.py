from __future__ import annotations

import streamlit as st

from database.database import get_settings

SECTIONS = [
    ("", [("Dashboard", "🏠")]),
    ("ESTUDOS", [("Estudar", "📖"), ("Questões", "❓"), ("Simulados", "📝"), ("Flashcards", "🗂️")]),
    ("IA", [("Professor IA", "🤖")]),
    ("ANÁLISES", [("Estatísticas", "📊"), ("Desempenho", "📈"), ("Revisões", "🗓️")]),
    ("OUTROS", [("Metas", "🎯"), ("Calendário", "📅"), ("Coletor automático", "🌐"), ("Configurações", "⚙️")]),
]


def render_sidebar() -> str:
    settings = get_settings()
    st.session_state.setdefault("current_page", "Dashboard")

    with st.sidebar:
        st.markdown(
            """
            <div class="brand-box brand-v2">
              <div class="brand-mark brand-bank">🏛️</div>
              <div><strong>Concurso<span>AI</span></strong><small>Banco do Brasil Edition</small></div>
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
                    f"{icon}  {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state.current_page = page

        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="upgrade-card premium-card">
              <div class="upgrade-icon">👑</div>
              <strong>Plano de aprovação</strong>
              <p>{settings['user_name']}, mantenha suas metas, revisões e questões em dia.</p>
              <div class="premium-pill">Versão 1.0 beta • Coleta automática</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return str(st.session_state.current_page)
