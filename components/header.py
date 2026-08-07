from __future__ import annotations

from datetime import datetime

import streamlit as st

from database.database import get_settings
from services.reviews import get_due_count


def _greeting() -> tuple[str, str]:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia", "☀️"
    if hour < 18:
        return "Boa tarde", "🌤️"
    return "Boa noite", "👋"


def render_header(page: str = "Dashboard") -> None:
    settings = get_settings()
    name = str(settings.get("user_name", "Jhony"))
    greeting, icon = _greeting()
    due = get_due_count()
    badge = f'<span class="notify-badge">{min(due, 99)}</span>' if due else ""

    st.markdown(
        f"""
        <section class="top-header reference-header">
          <div class="reference-header-left">
            <div class="reference-menu">☷</div>
            <div>
              <h1>{greeting}, {name}! <span>{icon}</span></h1>
              <p>Foque hoje, colha amanhã.</p>
            </div>
          </div>
          <div class="reference-profile">
            <div class="reference-notification" title="{due} revisão(ões) para hoje">♧{badge}</div>
            <div class="reference-avatar">{name[:1].upper()}</div>
            <div class="reference-profile-name">{name} Vieira <span>⌄</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
