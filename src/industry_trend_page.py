"""Streamlit page for the Industry Trend Search Engine."""

from __future__ import annotations

import html

import streamlit as st

from src.industry_trend_data import INDUSTRY_CATEGORIES
from src.industry_trend_search import find_industry_trend


STATUS_COLORS = {
    "Strong Trend": "#22C55E",
    "Trend Intact": "#38BDF8",
    "Diverging": "#FBBF24",
    "Weakening": "#F97316",
    "Broken Trend": "#EF4444",
    "Overheated": "#F59E0B",
    "Strong": "#22C55E",
    "Moderate-Strong": "#38BDF8",
    "Moderate": "#CBD5E1",
    "Recovering": "#A78BFA",
    "Stable": "#94A3B8",
    "Framework": "#CBD5E1",
    "Emerging": "#2DD4BF",
}


def render_industry_trend_search_page() -> None:
    """Render the mock V1 and V2 industry trend search page."""

    _apply_industry_css()
    _render_html(
        """
        <div class="industry-hero">
            <div>
                <h1>Industry Trend Search Engine</h1>
                <p>Neutral industry research workspace using V1 + V2 mock data only.</p>
            </div>
            <div class="industry-version">V1 + V2 Skeleton</div>
        </div>
        """
    )

    query = st.text_input(
        "Search industry or theme...",
        value="Semiconductor",
        placeholder="Search industry or theme...",
        label_visibility="collapsed",
    )
    industry, matched = find_industry_trend(query)

    if not matched:
        st.warning("No exact match found")
        st.info("Showing a general trend analysis framework")

    render_industry_overview(industry)
    render_score_grid(industry)

    left, right = st.columns([1.35, 1])
    with left:
        render_key_drivers(industry)
        render_industry_chain(industry)
    with right:
        render_subsectors(industry)
        render_catalysts(industry)
        render_risk_signals(industry)

    render_available_universe()


def render_industry_overview(industry: dict) -> None:
    """Render headline industry context."""

    status = html.escape(industry["status"])
    color = STATUS_COLORS.get(industry["status"], "#CBD5E1")
    _render_html(
        f"""
        <section class="industry-panel">
            <div class="industry-kicker">{html.escape(industry["category"])} / {html.escape(industry["chineseName"])}</div>
            <div class="industry-title-row">
                <h2>{html.escape(industry["name"])}</h2>
                <span class="industry-badge" style="border-color:{color}; color:{color};">{status}</span>
            </div>
            <p>{html.escape(industry["overview"])}</p>
            <div class="stage-box">
                <div class="stage-label">Trend Stage</div>
                <div class="stage-value">{html.escape(industry["trendStage"])}</div>
                <div class="stage-note">{html.escape(industry["trendStageExplanation"])}</div>
            </div>
        </section>
        """
    )


def render_score_grid(industry: dict) -> None:
    """Render score cards with native Streamlit progress bars."""

    metrics = [
        ("Trend Score", industry["trendScore"], "Composite trend quality from mock market, heat, and validation inputs."),
        ("Market Confirmation", industry["marketConfirmation"], industry["marketConfirmationExplanation"]),
        ("Fundamental Validation", industry["fundamentalValidation"], industry["fundamentalValidationExplanation"]),
        ("Valuation Pressure", industry["valuationPressure"], industry["valuationPressureExplanation"]),
        ("Macro Sensitivity", industry["macroSensitivity"], industry["macroSensitivityExplanation"]),
    ]
    score_items = metrics + [
        ("Heat Level", industry["heatLevel"], industry["heatLevelExplanation"]),
    ]
    for row_start in range(0, len(score_items), 3):
        cols = st.columns(3)
        for col, item in zip(cols, score_items[row_start : row_start + 3]):
            label, value, explanation = item
            with col:
                if label == "Heat Level":
                    render_heat_card_native(str(value), str(explanation))
                else:
                    render_score_card_native(label, float(value), str(explanation))


def render_score_card_native(label: str, value: float, explanation: str) -> None:
    """Render one score card without raw HTML."""

    pct = max(0.0, min(value / 10, 1.0))
    with st.container(border=True):
        st.markdown(f"**{label}**")
        st.metric(label="Score", value=f"{value:.1f}", label_visibility="collapsed")
        st.progress(pct)
        st.markdown(explanation)


def render_heat_card_native(heat_level: str, explanation: str) -> None:
    """Render heat-level card without raw HTML."""

    heat_progress = {
        "Low": 0.25,
        "Moderate": 0.5,
        "High": 0.75,
        "Very High": 1.0,
    }.get(heat_level, 0.5)
    with st.container(border=True):
        st.markdown("**Heat Level**")
        st.metric(label="Heat Level", value=heat_level, label_visibility="collapsed")
        st.progress(heat_progress)
        st.markdown(explanation)


def render_key_drivers(industry: dict) -> None:
    """Render key trend drivers."""

    rows = "".join(
        render_labeled_row(driver["name"], driver["status"], driver["explanation"])
        for driver in industry["keyDrivers"]
    )
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>Key Trend Drivers</h3>
            <p>Core drivers explain what is supporting or challenging the industry trend in this mock framework.</p>
            {rows}
        </section>
        """
    )


def render_subsectors(industry: dict) -> None:
    """Render sub-sector chips."""

    chips = "".join(
        f'<span class="theme-chip">{html.escape(item["name"])} | {html.escape(item["status"])}</span>'
        for item in industry["subSectors"]
    )
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>Sub-Sectors & Related Themes</h3>
            <p>Related areas can confirm, lag, or diverge from the headline industry trend.</p>
            <div class="chip-wrap">{chips}</div>
        </section>
        """
    )


def render_industry_chain(industry: dict) -> None:
    """Render upstream, midstream, and downstream chain map."""

    chain = industry["industryChain"]
    columns = [
        ("Upstream", chain.get("upstream", [])),
        ("Midstream", chain.get("midstream", [])),
        ("Downstream", chain.get("downstream", [])),
    ]
    body = ""
    for title, values in columns:
        items = "".join(f"<li>{html.escape(value)}</li>" for value in values)
        body += f'<div class="chain-column"><h4>{title}</h4><ul>{items}</ul></div>'
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>Industry Chain Map</h3>
            <p>The chain map separates input layers, production or platform layers, and demand-facing applications.</p>
            <div class="chain-grid">{body}</div>
        </section>
        """
    )


def render_catalysts(industry: dict) -> None:
    """Render catalysts."""

    items = "".join(f"<li>{html.escape(item)}</li>" for item in industry["catalysts"])
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>Key Catalysts</h3>
            <p>Catalysts are events or data points that may change trend confirmation or heat level.</p>
            <ul class="clean-list">{items}</ul>
        </section>
        """
    )


def render_risk_signals(industry: dict) -> None:
    """Render trend risk signals."""

    items = "".join(f"<li>{html.escape(item)}</li>" for item in industry["riskSignals"])
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>Trend Risk Signals</h3>
            <p>Risk signals highlight areas where trend quality may weaken or become less internally consistent.</p>
            <ul class="clean-list">{items}</ul>
        </section>
        """
    )


def render_labeled_row(name: str, status: str, explanation: str) -> str:
    """Return a compact driver row."""

    color = STATUS_COLORS.get(status, "#CBD5E1")
    return f"""
        <div class="driver-row">
            <div>
                <strong>{html.escape(name)}</strong>
                <p>{html.escape(explanation)}</p>
            </div>
            <span style="border-color:{color}; color:{color};">{html.escape(status)}</span>
        </div>
        """


def render_available_universe() -> None:
    """Render the built-in mock universe."""

    with st.expander("Built-in mock industry universe", expanded=False):
        for category, items in INDUSTRY_CATEGORIES.items():
            labels = ", ".join(item[1] for item in items)
            st.markdown(f"**{category}**: {labels}")


def _render_html(markup: str) -> None:
    """Render trusted local HTML for this Streamlit page."""

    st.markdown(markup, unsafe_allow_html=True)


def _apply_industry_css() -> None:
    """Apply page-scoped dashboard styling."""

    _render_html(
        """
        <style>
        .industry-hero {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 16px;
            padding: 18px 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(15, 23, 42, 0.72);
            border-radius: 8px;
        }
        .industry-hero h1 {
            margin: 0;
            font-size: 30px;
            line-height: 1.15;
        }
        .industry-hero p {
            margin: 6px 0 0;
            color: #CBD5E1;
        }
        .industry-version {
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.42);
            border-radius: 999px;
            padding: 6px 10px;
            white-space: nowrap;
            font-size: 13px;
        }
        .industry-panel {
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.58);
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
        }
        .industry-panel h2, .industry-panel h3, .industry-panel h4 {
            margin-top: 0;
        }
        .industry-panel p, .trend-card p, .driver-row p {
            color: #CBD5E1;
            line-height: 1.5;
        }
        .industry-kicker {
            color: #94A3B8;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .industry-title-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
        }
        .industry-badge, .driver-row span {
            border: 1px solid;
            border-radius: 999px;
            padding: 5px 9px;
            font-size: 12px;
            white-space: nowrap;
            background: rgba(15, 23, 42, 0.72);
        }
        .stage-box {
            margin-top: 14px;
            padding: 12px;
            background: rgba(30, 41, 59, 0.72);
            border-left: 3px solid #38BDF8;
            border-radius: 6px;
        }
        .stage-label {
            color: #94A3B8;
            font-size: 12px;
        }
        .stage-value {
            color: #F8FAFC;
            font-size: 18px;
            font-weight: 700;
            margin: 3px 0;
        }
        .stage-note {
            color: #CBD5E1;
            font-size: 13px;
        }
        .score-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0;
        }
        .trend-card {
            border: 1px solid rgba(148, 163, 184, 0.2);
            background: rgba(30, 41, 59, 0.66);
            border-radius: 8px;
            padding: 14px;
            min-height: 156px;
        }
        .trend-card-top {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            color: #E5E7EB;
            margin-bottom: 10px;
        }
        .trend-card-top strong {
            color: #F8FAFC;
            font-size: 20px;
        }
        .bar-track {
            height: 8px;
            background: rgba(148, 163, 184, 0.2);
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #38BDF8, #22C55E);
        }
        .heat-strip {
            height: 8px;
            border-radius: 999px;
            margin: 0 0 10px;
            background: #CBD5E1;
        }
        .heat-low { background: #94A3B8; }
        .heat-moderate { background: #38BDF8; }
        .heat-high { background: #FBBF24; }
        .heat-very-high { background: #F97316; }
        .driver-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 0;
            border-top: 1px solid rgba(148, 163, 184, 0.16);
        }
        .driver-row:first-of-type {
            border-top: 0;
        }
        .driver-row p {
            margin: 4px 0 0;
        }
        .chip-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .theme-chip {
            display: inline-flex;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(30, 41, 59, 0.78);
            color: #E5E7EB;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 13px;
        }
        .chain-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }
        .chain-column {
            background: rgba(30, 41, 59, 0.62);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            padding: 12px;
        }
        .chain-column ul, .clean-list {
            margin-bottom: 0;
            padding-left: 18px;
        }
        @media (max-width: 900px) {
            .score-grid, .chain-grid {
                grid-template-columns: 1fr;
            }
            .industry-hero, .industry-title-row, .driver-row {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        </style>
        """
    )
