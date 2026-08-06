from pathlib import Path

import streamlit as st

from components.header import render_header
from components.sidebar import render_sidebar
from components.theme import load_global_css
from database.database import init_db
from database.remote_sync import sync_remote_questions
from services.analytics import render_performance_page, render_statistics_page
from services.collector_admin import render_collector_page
from services.dashboard import render_dashboard
from services.flashcards import render_flashcards_page
from services.goals import render_calendar_page, render_goals_page
from services.professor import render_professor_page
from services.questions import render_questions_page
from services.reviews import render_reviews_page
from services.settings import render_settings_page
from services.simulations import render_simulations_page
from services.study import render_study_page

VERSION_FILE = Path(__file__).resolve().parent / "VERSION"
VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else "0.9.0"

st.set_page_config(
    page_title=f"ConcursoAI v{VERSION}",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
try:
    sync_remote_questions()
except Exception:
    pass
load_global_css()
page = render_sidebar()
render_header(page)

PAGES = {
    "Dashboard": render_dashboard,
    "Estudar": render_study_page,
    "Questões": render_questions_page,
    "Simulados": render_simulations_page,
    "Flashcards": render_flashcards_page,
    "Professor IA": render_professor_page,
    "Estatísticas": render_statistics_page,
    "Desempenho": render_performance_page,
    "Revisões": render_reviews_page,
    "Metas": render_goals_page,
    "Calendário": render_calendar_page,
    "Coletor automático": render_collector_page,
    "Configurações": render_settings_page,
}

PAGES.get(page, render_dashboard)()
