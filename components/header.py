from __future__ import annotations

from datetime import date, datetime
import html

import streamlit as st

from database.database import get_settings
from services.reviews import get_due_count
from utils.helpers import format_date_pt


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


def render_header(page: str = "Dashboard") -> None:
    settings = get_settings()
    name = str(settings.get("user_name", "Aluno"))
    safe_name = html.escape(name)
    safe_page = html.escape(page)
    due = get_due_count()
    badge = f'<span class="command-notify-badge">{min(due, 99)}</span>' if due else ""

    st.markdown(
        f"""
        <section class="command-header">
          <div class="command-header-copy">
            <div class="command-breadcrumb"><span>CONCURSOAI</span><b>/</b>{safe_page}</div>
            <h1>{_greeting()}, {safe_name}.</h1>
            <p>Seu centro de comando para transformar estudo em aprovação.</p>
          </div>
          <div class="command-header-actions">
            <div class="command-date"><small>HOJE</small><strong>{format_date_pt(date.today())}</strong></div>
            <div class="command-notification" title="{due} revisão(ões) para hoje">◷{badge}</div>
            <div class="command-user">
              <div class="command-avatar">{safe_name[:1].upper()}</div>
              <div><strong>{safe_name}</strong><small>Banco do Brasil</small></div>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
