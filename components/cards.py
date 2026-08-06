import html

import streamlit as st


CARD_STYLES = {
    "blue": ("#eaf3ff", "#2563eb"),
    "orange": ("#fff3e8", "#f97316"),
    "green": ("#eafaf1", "#16a34a"),
    "purple": ("#f3ecff", "#7c3aed"),
    "yellow": ("#fff8d8", "#ca8a04"),
}


def metric_card(
    label: str,
    value: str,
    detail: str = "",
    icon: str = "📊",
    tone: str = "blue",
) -> None:
    background, accent = CARD_STYLES.get(tone, CARD_STYLES["blue"])
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-icon" style="background:{background}; color:{accent};">{html.escape(icon)}</div>
          <div class="metric-content">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-detail">{html.escape(detail)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def progress_row(label: str, value: float, tone: str = "blue") -> None:
    _, accent = CARD_STYLES.get(tone, CARD_STYLES["blue"])
    safe_value = max(0.0, min(float(value), 100.0))
    st.markdown(
        f"""
        <div class="progress-row">
          <div class="progress-head"><span>{html.escape(label)}</span><strong>{safe_value:.0f}%</strong></div>
          <div class="progress-track"><div class="progress-fill" style="width:{safe_value:.1f}%; background:{accent};"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
