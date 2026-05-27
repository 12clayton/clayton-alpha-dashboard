"""Standalone Streamlit entrypoint for the Industry Trend Search Engine."""

from __future__ import annotations

import streamlit as st

from src.industry_trend_page import render_industry_trend_search_page


st.set_page_config(
    page_title="Industry Trend Search Engine",
    layout="wide",
)


def main() -> None:
    """Render only the standalone industry trend search page."""

    render_industry_trend_search_page()


if __name__ == "__main__":
    main()
