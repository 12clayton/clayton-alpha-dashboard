"""Industry radar overview for the standalone trend search app."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.industry_market_data import (
    EXPLICIT_NO_MARKET_MAPPING,
    INDUSTRY_MARKET_TICKERS,
    get_market_confirmation_data,
)
from src.industry_trend_data import industryTrendData
from src.industry_trend_page import (
    TEXT,
    _apply_industry_css,
    category_label,
    format_percent,
    format_score,
    industry_name,
    translate_status,
)


RADAR_TEXT = {
    "zh": {
        "title": "行业雷达总览",
        "subtitle": "横向比较全部行业的 V1/V2 框架趋势分与 V3 市场价格确认数据。",
        "load": "刷新 / 加载市场雷达数据",
        "category_filter": "分类筛选",
        "status_filter": "V3 状态筛选",
        "min_score": "最低市场价格确认分",
        "search": "搜索行业",
        "all": "全部",
        "available": "正常",
        "not_configured": "未配置",
        "data_failed": "数据失败",
        "none": "无",
        "hint": "点击上方“单行业搜索”并输入行业名称查看详情。",
        "load_note": "雷达数据复用现有缓存；点击按钮会清理市场数据缓存并重新加载。",
        "columns": {
            "industry": "行业",
            "category": "分类",
            "trend_status": "趋势状态",
            "trend_score": "框架趋势分",
            "framework_market": "框架市场确认",
            "v3_status": "V3 状态",
            "price_score": "市场价格确认分",
            "ma50": "MA50 比例",
            "median_3m": "3个月中位数表现",
            "relative_strength": "相对强弱",
            "valid_samples": "有效样本",
            "failed_tickers": "下载失败",
            "sort_rank": "排序",
        },
    },
    "en": {
        "title": "Industry Radar Overview",
        "subtitle": "Compare V1/V2 framework trend scores with V3 market-price confirmation data across industries.",
        "load": "Refresh / Load Radar Data",
        "category_filter": "Category Filter",
        "status_filter": "V3 Status Filter",
        "min_score": "Minimum Market Price Score",
        "search": "Search Industry",
        "all": "All",
        "available": "Available",
        "not_configured": "Not Configured",
        "data_failed": "Data Failed",
        "none": "None",
        "hint": "Use “Single Industry Search” and enter the industry name to view details.",
        "load_note": "Radar data reuses the existing cache. The button clears market-data cache and reloads it.",
        "columns": {
            "industry": "Industry",
            "category": "Category",
            "trend_status": "Trend Status",
            "trend_score": "Framework Trend Score",
            "framework_market": "Framework Market Confirmation",
            "v3_status": "V3 Status",
            "price_score": "Market Price Confirmation Score",
            "ma50": "MA50 Ratio",
            "median_3m": "Median 3M Return",
            "relative_strength": "Relative Strength",
            "valid_samples": "Valid Samples",
            "failed_tickers": "Failed Tickers",
            "sort_rank": "Sort",
        },
    },
}


def render_industry_radar_page(lang: str) -> None:
    """Render a cross-industry radar table."""

    _apply_industry_css()
    text = RADAR_TEXT[lang]

    st.markdown(f"## {text['title']}")
    st.caption(text["subtitle"])

    if st.button(text["load"], use_container_width=False):
        get_market_confirmation_data.clear()

    st.caption(text["load_note"])

    rows = build_radar_rows(lang)
    filtered = filter_radar_rows(rows, lang)

    df = pd.DataFrame(filtered)
    if not df.empty:
        sort_col = text["columns"]["sort_rank"]
        score_sort_col = "__score_sort"
        df = df.sort_values([sort_col, score_sort_col], ascending=[True, False])
        df = df.drop(columns=[sort_col, score_sort_col])

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(text["hint"])


def build_radar_rows(lang: str) -> list[dict[str, Any]]:
    """Build localized radar rows for all industry records."""

    rows = []
    for industry in industryTrendData:
        rows.append(build_radar_row(industry, lang))
    return rows


def build_radar_row(industry: dict[str, Any], lang: str) -> dict[str, Any]:
    """Build one radar table row without letting one market-data failure break the page."""

    text = RADAR_TEXT[lang]
    columns = text["columns"]
    industry_id = str(industry.get("id", ""))
    row = {
        columns["industry"]: industry_name(industry, lang),
        columns["category"]: category_label(industry, lang),
        columns["trend_status"]: translate_status(industry.get("status", ""), lang),
        columns["trend_score"]: _score_number(industry.get("trendScore")),
        columns["framework_market"]: _score_number(industry.get("marketConfirmation")),
        columns["v3_status"]: text["not_configured"],
        columns["price_score"]: "—",
        columns["ma50"]: "—",
        columns["median_3m"]: "—",
        columns["relative_strength"]: "—",
        columns["valid_samples"]: "—",
        columns["failed_tickers"]: text["none"],
        columns["sort_rank"]: 2,
        "__score_sort": -1.0,
    }

    if industry_id not in INDUSTRY_MARKET_TICKERS:
        row[columns["v3_status"]] = text["not_configured"]
        row[columns["sort_rank"]] = 2 if industry_id in EXPLICIT_NO_MARKET_MAPPING else 3
        return row

    result = safe_market_result(industry_id)
    failed_tickers = result.get("failed_tickers") or []
    row[columns["failed_tickers"]] = ", ".join(failed_tickers) if failed_tickers else text["none"]
    row[columns["valid_samples"]] = int(result.get("valid_ticker_count") or 0)

    if result.get("available") and result.get("valid_ticker_count", 0) > 0:
        row[columns["v3_status"]] = text["available"]
        row[columns["price_score"]] = _score_number(result.get("score"))
        row["__score_sort"] = float(result.get("score") or -1.0)
        row[columns["ma50"]] = format_percent(result.get("above_ma50_ratio")).replace("N/A", "—")
        row[columns["median_3m"]] = format_percent(result.get("median_3m_return")).replace("N/A", "—")
        row[columns["relative_strength"]] = _signed_percent(result.get("relative_strength"))
        row[columns["sort_rank"]] = 0
        return row

    row[columns["v3_status"]] = text["data_failed"]
    row[columns["sort_rank"]] = 1
    return row


def safe_market_result(industry_id: str) -> dict[str, Any]:
    """Return market data result with a local failure fallback."""

    try:
        return get_market_confirmation_data(industry_id)
    except Exception as exc:  # pragma: no cover - defensive UI fallback
        return {
            "available": False,
            "reason_code": "market_data_failed",
            "valid_ticker_count": 0,
            "failed_tickers": [],
            "message": str(exc),
        }


def filter_radar_rows(rows: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """Render filters and return matching radar rows."""

    text = RADAR_TEXT[lang]
    columns = text["columns"]
    categories = sorted({str(row[columns["category"]]) for row in rows})
    statuses = [text["available"], text["not_configured"], text["data_failed"]]

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1.4])
    with c1:
        selected_category = st.selectbox(text["category_filter"], [text["all"], *categories])
    with c2:
        selected_status = st.selectbox(text["status_filter"], [text["all"], *statuses])
    with c3:
        min_score = st.slider(text["min_score"], 0.0, 9.5, 0.0, 0.5)
    with c4:
        query = st.text_input(text["search"], placeholder=text["search"])

    filtered = []
    query_lower = query.strip().lower()
    for row in rows:
        if selected_category != text["all"] and row[columns["category"]] != selected_category:
            continue
        if selected_status != text["all"] and row[columns["v3_status"]] != selected_status:
            continue
        score = row[columns["price_score"]]
        if isinstance(score, (int, float)) and score < min_score:
            continue
        if not isinstance(score, (int, float)) and min_score > 0:
            continue
        if query_lower and query_lower not in str(row[columns["industry"]]).lower():
            continue
        filtered.append(row)
    return filtered


def _score_number(value: object) -> float | str:
    formatted = format_score(value)
    if formatted == "N/A":
        return "—"
    return round(float(formatted), 1)


def _signed_percent(value: object) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if number > 0 else ""
    return f"{sign}{number * 100:.1f}%"
