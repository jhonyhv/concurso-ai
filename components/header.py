from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from database.database import get_settings
from services.reviews import get_due_count
from utils.helpers import format_date_pt
from utils.version import get_version_badge


def _greeting() -> tuple[str, str]:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia", "☀️"
    if hour < 18:
        return "Boa tarde", "🌤️"
    return "Boa noite", "🌙"


def render_header(page: str = "Dashboard") -> None:
    settings = get_settings()
    name = str(settings.get("user_name", "Jhony"))
    greeting, icon = _greeting()
    due = get_due_count()
    version_badge = get_version_badge()
    badge = f'<span class="notify-badge">{min(due, 99)}</span>' if due else ""

    st.markdown(
        f"""
        <section class="top-header top-header-v2">
          <div class="header-main">
            <span class="header-brand-dot"></span>
            <div>
              <div class="page-kicker">CONCURSOAI / {page.upper()} • {format_date_pt(date.today())}</div>
              <h1>{greeting}, {name}! <span>{icon}</span></h1>
              <p>Seu plano de preparação para o Banco do Brasil, em um só lugar.</p>
            </div>
          </div>
          <div class="profile-area profile-v2">
            <div class="status-chip"><span></span> {version_badge}</div>
            <div class="notification" title="{due} revisão(ões) para hoje">🔔{badge}</div>
            <div class="avatar avatar-photo">{name[:1].upper()}</div>
            <div class="profile-name">{name}</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
