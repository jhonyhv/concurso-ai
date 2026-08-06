from __future__ import annotations

from datetime import datetime

import streamlit as st

from database.database import get_settings


def _greeting() -> tuple[str, str]:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia", "☀️"
    if hour < 18:
        return "Boa tarde", "🌤️"
    return "Boa noite", "👋"


def render_header() -> None:
    settings = get_settings()
    name = str(settings.get("user_name", "Jhony"))
    greeting, icon = _greeting()
    st.markdown(
        f"""
        <section class="top-header top-header-v2">
          <div class="header-main">
            <div class="menu-symbol">☰</div>
            <div>
              <h1>{greeting}, {name}! <span>{icon}</span></h1>
              <p>Foque hoje, colha amanhã.</p>
            </div>
          </div>
          <div class="profile-area profile-v2">
            <div class="notification">🔔<span class="notify-badge">3</span></div>
            <div class="avatar avatar-photo">{name[:1].upper()}</div>
            <div class="profile-name">{name} ▾</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
