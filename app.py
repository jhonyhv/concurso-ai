import streamlit as st

from components.header import render_header
from components.sidebar import render_sidebar
from components.theme import load_global_css
from database.database import init_db
from services.analytics import render_performance_page, render_statistics_page
from services.dashboard import render_dashboard
from services.flashcards import render_flashcards_page
from services.goals import render_calendar_page, render_goals_page
from services.professor import render_professor_page
from services.questions import render_questions_page
from services.reviews import render_reviews_page
from services.settings import render_settings_page
from services.simulations import render_simulations_page
from services.study import render_study_page

st.set_page_config(
    page_title="ConcursoAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
load_global_css()
page = render_sidebar()
render_header()

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
    "Configurações": render_settings_page,
}

PAGES.get(page, render_dashboard)()
