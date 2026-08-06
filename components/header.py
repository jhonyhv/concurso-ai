from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from database.database import get_settings
from services.reviews import get_due_count
from utils.helpers import format_date_pt


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
        <section class="top-header top-header-v2">
          <div class="header-main">
            <div class="menu-symbol">☰</div>
            <div>
              <div class="page-kicker">{page} • {format_date_pt(date.today())}</div>
              <h1>{greeting}, {name}! <span>{icon}</span></h1>
              <p>Foque hoje, colha amanhã.</p>
            </div>
          </div>
          <div class="profile-area profile-v2">
            <div class="status-chip"><span></span> v0.9</div>
            <div class="notification" title="{due} revisão(ões) para hoje">🔔{badge}</div>
            <div class="avatar avatar-photo">{name[:1].upper()}</div>
            <div class="profile-name">{name} ▾</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
