import html

import streamlit as st

CARD_STYLES = {
    "blue": ("#eaf1ff", "#2563eb"),
    "orange": ("#fff0e8", "#ff4b21"),
    "green": ("#eaf9ee", "#16a05d"),
    "purple": ("#f3edff", "#7036d8"),
    "yellow": ("#fff8d8", "#c89400"),
    "red": ("#fff0f0", "#ef4444"),
}


def metric_card(label: str, value: str, detail: str = "", icon: str = "📊", tone: str = "blue") -> None:
    background, accent = CARD_STYLES.get(tone, CARD_STYLES["blue"])
    st.markdown(
        f"""
        <div class="metric-card metric-card-v2">
          <div class="metric-icon metric-icon-v2" style="background:{background}; color:{accent};">{html.escape(icon)}</div>
          <div class="metric-content">
            <div class="metric-label metric-label-v2">{html.escape(label)}</div>
            <div class="metric-value metric-value-v2" style="color:{accent};">{html.escape(value)}</div>
            <div class="metric-detail metric-detail-v2">{html.escape(detail)}</div>
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
          <div class="progress-head"><span>{html.escape(label)}</span><strong style="color:{accent}">{safe_value:.0f}%</strong></div>
          <div class="progress-track"><div class="progress-fill" style="width:{safe_value:.1f}%; background:{accent};"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
