"""Standalone Streamlit entrypoint for the Industry Trend Search Engine."""

from __future__ import annotations

import streamlit as st

from src.industry_radar_page import render_industry_radar_page
from src.industry_trend_page import render_industry_trend_search_page, render_language_picker


st.set_page_config(
    page_title="Industry Trend Search Engine",
    layout="wide",
)


def main() -> None:
    """Render only the standalone industry trend search page."""

    lang = render_language_picker()
    labels = {
        "zh": ("单行业搜索", "行业雷达总览"),
        "en": ("Single Industry Search", "Industry Radar Overview"),
    }
    search_label, radar_label = labels[lang]
    selected_view = st.radio(
        "View",
        [search_label, radar_label],
        horizontal=True,
        label_visibility="collapsed",
    )
    if selected_view == radar_label:
        render_industry_radar_page(lang)
    else:
        render_industry_trend_search_page(lang=lang, show_language_picker=False)


if __name__ == "__main__":
    main()
