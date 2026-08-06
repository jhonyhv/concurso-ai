import streamlit as st


NAVIGATION = [
    "Painel",
    "Plano de estudos",
    "Questões",
    "Registrar estudo",
    "Conteúdo programático",
]


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-box">
              <div class="brand-mark">C<span>AI</span></div>
              <div><strong>ConcursoAI</strong><small>Banco do Brasil</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        page = st.radio("Menu principal", NAVIGATION, label_visibility="collapsed")
        st.markdown(
            """
            <div class="sidebar-divider"></div>
            <div class="upgrade-card">
              <div class="upgrade-icon">⭐</div>
              <strong>Continue evoluindo</strong>
              <p>Registre seus estudos e acompanhe seu desempenho.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return page
