from pathlib import Path

import streamlit as st

from database.database import get_settings


def _read_css(filename: str) -> str:
    path = Path(__file__).resolve().parent.parent / "assets" / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_global_css() -> None:
    css = _read_css("style.css")
    try:
        theme = str(get_settings().get("theme", "claro"))
    except Exception:
        theme = "claro"
    if theme == "escuro":
        css += "\n" + _read_css("dark.css")
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
