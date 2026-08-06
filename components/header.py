from datetime import datetime

import streamlit as st


def _greeting() -> tuple[str, str]:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia", "☀️"
    if hour < 18:
        return "Boa tarde", "🌤️"
    return "Boa noite", "🌙"


def render_header(name: str = "Jhony") -> None:
    greeting, icon = _greeting()
    st.markdown(
        f"""
        <section class="top-header">
          <div>
            <h1>{greeting}, {name}! <span>{icon}</span></h1>
            <p>Pronto para avançar mais um passo rumo à aprovação?</p>
          </div>
          <div class="profile-area">
            <div class="notification">🔔</div>
            <div class="avatar">JV</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
