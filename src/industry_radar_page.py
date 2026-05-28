"""Industry radar overview for the standalone trend search app."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover - optional chart dependency fallback
    px = None

from src.industry_catalyst_data import HEAT_DIRECTION_LABELS, get_catalyst_data, localized_label
from src.industry_market_data import (
    EXPLICIT_NO_MARKET_MAPPING,
    INDUSTRY_MARKET_TICKERS,
    get_market_confirmation_data,
)
from src.industry_radar_history import (
    load_latest_snapshot_lookup,
    load_snapshot_history,
    load_watchlist,
    save_snapshot,
    snapshot_summary,
)
from src.industry_trend_data import industryTrendData
from src.industry_trend_page import (
    _apply_industry_css,
    category_label,
    format_percent,
    format_score,
    industry_name,
    render_catalyst_event_guide,
    render_trend_stage_guide,
    render_trend_status_guide,
    translate_status,
)


DASH = "-"

RADAR_TEXT = {
    "zh": {
        "title": "行业雷达总览",
        "subtitle": "横向比较全部行业的 V1/V2 框架趋势分与 V3 市场价格确认数据。",
        "load": "刷新 / 加载市场雷达数据",
        "save_snapshot": "保存今日雷达快照",
        "snapshot_saved": "已保存今日雷达快照",
        "download": "下载当前雷达表 CSV",
        "category_filter": "分类筛选",
        "status_filter": "V3 状态筛选",
        "min_score": "最低市场价格确认分",
        "search": "搜索行业",
        "watchlist_only": "仅显示收藏行业",
        "all": "全部",
        "available": "正常",
        "not_configured": "未配置",
        "data_failed": "数据失败",
        "none": "无",
        "hint": "点击上方“单行业搜索”并输入行业名称查看详情。",
        "load_note": "雷达数据复用现有缓存；点击按钮会清理市场数据缓存并重新加载。",
        "snapshots": "历史快照",
        "snapshot_count": "快照数量",
        "latest_snapshot": "最新快照日期",
        "snapshot_files": "快照文件",
        "snapshot_dir": "保存目录",
        "no_snapshots": "暂无历史快照",
        "charts_title": "行业雷达图表",
        "charts_note": "图表基于当前雷达数据生成。",
        "price_top10": "价格确认 Top 10",
        "relative_top10": "相对强弱 Top 10",
        "ma50_top10": "MA50 广度 Top 10",
        "watchlist_history": "Watchlist 历史",
        "no_chart_data": "暂无可用图表数据。",
        "not_enough_history": "历史快照不足。请先保存至少两次不同日期的雷达快照，以查看趋势变化。",
        "chart_industry": "行业",
        "chart_price_score": "市场价格确认分",
        "chart_relative_strength": "相对强弱",
        "chart_ma50": "MA50 比例",
        "chart_date": "快照日期",
        "news_heat_top10": "新闻热度 Top 10",
        "chart_news_heat": "新闻热度分",
        "news_chart_note": "该数据为 V4.1 本地框架数据，不是实时新闻热度。",
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
            "price_score_change": "价格确认分变化",
            "ma50_change": "MA50 比例变化",
            "relative_strength_change": "相对强弱变化",
            "news_heat_score": "新闻热度分",
            "heat_direction": "热度方向",
            "sort_rank": "排序",
        },
    },
    "en": {
        "title": "Industry Radar Overview",
        "subtitle": "Compare V1/V2 framework trend scores with V3 market-price confirmation data across industries.",
        "load": "Refresh / Load Radar Data",
        "save_snapshot": "Save Today's Radar Snapshot",
        "snapshot_saved": "Saved today's radar snapshot",
        "download": "Download Current Radar CSV",
        "category_filter": "Category Filter",
        "status_filter": "V3 Status Filter",
        "min_score": "Minimum Market Price Score",
        "search": "Search Industry",
        "watchlist_only": "Show Watchlist Only",
        "all": "All",
        "available": "Available",
        "not_configured": "Not Configured",
        "data_failed": "Data Failed",
        "none": "None",
        "hint": 'Use "Single Industry Search" and enter the industry name to view details.',
        "load_note": "Radar data reuses the existing cache. The button clears market-data cache and reloads it.",
        "snapshots": "Historical Snapshots",
        "snapshot_count": "Snapshot Count",
        "latest_snapshot": "Latest Snapshot Date",
        "snapshot_files": "Snapshot Files",
        "snapshot_dir": "Snapshot Directory",
        "no_snapshots": "No historical snapshots yet",
        "charts_title": "Industry Radar Charts",
        "charts_note": "Charts are generated from the current radar dataset.",
        "price_top10": "Price Confirmation Top 10",
        "relative_top10": "Relative Strength Top 10",
        "ma50_top10": "MA50 Breadth Top 10",
        "watchlist_history": "Watchlist History",
        "no_chart_data": "No chart data available.",
        "not_enough_history": "Not enough historical snapshots. Save at least two snapshots on different dates to view trend changes.",
        "chart_industry": "Industry",
        "chart_price_score": "Market Price Confirmation Score",
        "chart_relative_strength": "Relative Strength",
        "chart_ma50": "MA50 Ratio",
        "chart_date": "Snapshot Date",
        "news_heat_top10": "News Heat Top 10",
        "chart_news_heat": "News Heat Score",
        "news_chart_note": "This is V4.1 local framework data, not live news heat.",
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
            "price_score_change": "Price Score Change",
            "ma50_change": "MA50 Ratio Change",
            "relative_strength_change": "Relative Strength Change",
            "news_heat_score": "News Heat Score",
            "heat_direction": "Heat Direction",
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

    if st.button(text["load"], width="content"):
        get_market_confirmation_data.clear()

    st.caption(text["load_note"])

    previous_snapshot = load_latest_snapshot_lookup(before=date.today())
    watchlist = set(load_watchlist())
    radar_records = build_radar_records(lang, previous_snapshot)
    filtered_records = filter_radar_records(radar_records, lang, watchlist)

    render_snapshot_controls(radar_records, filtered_records, lang)
    render_radar_charts(filtered_records, watchlist, lang)
    render_snapshot_expander(lang)
    radar_catalyst_title = "新闻热度与催化事件说明" if lang == "zh" else "News Heat & Catalyst Guide"
    render_catalyst_event_guide(lang, title_override=radar_catalyst_title)
    render_trend_status_guide(lang)
    render_trend_stage_guide(lang)
    render_radar_table(filtered_records, lang)
    st.caption(text["hint"])


def build_radar_records(
    lang: str,
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build localized display rows and stable snapshot rows."""

    previous_snapshot = previous_snapshot or {}
    return [build_radar_record(industry, lang, previous_snapshot) for industry in industryTrendData]


def build_radar_record(
    industry: dict[str, Any],
    lang: str,
    previous_snapshot: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build one radar record without letting one market-data failure break the page."""

    text = RADAR_TEXT[lang]
    industry_id = str(industry.get("id", ""))
    raw = base_snapshot_row(industry)
    display = base_display_row(industry, lang)
    apply_catalyst_fields(industry_id, raw, display, lang)

    if industry_id not in INDUSTRY_MARKET_TICKERS:
        raw["v3_status"] = "explicit_no_market_mapping" if industry_id in EXPLICIT_NO_MARKET_MAPPING else "no_market_mapping"
        display["v3_status"] = text["not_configured"]
        display["sort_rank"] = 2 if industry_id in EXPLICIT_NO_MARKET_MAPPING else 3
        apply_change_columns(display, raw, previous_snapshot.get(industry_id), lang)
        return {"raw": raw, "display": display}

    result = safe_market_result(industry_id)
    failed_tickers = result.get("failed_tickers") or []
    raw["failed_tickers"] = ",".join(failed_tickers)
    raw["valid_ticker_count"] = int(result.get("valid_ticker_count") or 0)
    display["failed_tickers"] = ", ".join(failed_tickers) if failed_tickers else text["none"]
    display["valid_samples"] = raw["valid_ticker_count"]

    if result.get("available") and result.get("valid_ticker_count", 0) > 0:
        raw["v3_status"] = "available"
        raw["market_price_confirmation_score"] = _to_float(result.get("score"))
        raw["ma50_ratio"] = _to_float(result.get("above_ma50_ratio"))
        raw["median_3m_return"] = _to_float(result.get("median_3m_return"))
        raw["relative_strength"] = _to_float(result.get("relative_strength"))
        display["v3_status"] = text["available"]
        display["price_score"] = _score_number(raw["market_price_confirmation_score"])
        display["ma50"] = _percent_or_dash(raw["ma50_ratio"])
        display["median_3m"] = _percent_or_dash(raw["median_3m_return"])
        display["relative_strength"] = _signed_percent(raw["relative_strength"])
        display["sort_rank"] = 0
        display["score_sort"] = raw["market_price_confirmation_score"] or -1.0
    else:
        raw["v3_status"] = "market_data_failed"
        display["v3_status"] = text["data_failed"]
        display["sort_rank"] = 1

    apply_change_columns(display, raw, previous_snapshot.get(industry_id), lang)
    return {"raw": raw, "display": display}


def base_snapshot_row(industry: dict[str, Any]) -> dict[str, Any]:
    """Return stable raw fields for saving radar history."""

    return {
        "snapshot_date": f"{date.today():%Y-%m-%d}",
        "industry_id": industry.get("id", ""),
        "industry_name": industry.get("name", ""),
        "chinese_name": industry.get("chineseName", ""),
        "category": industry.get("category", ""),
        "category_zh": industry.get("categoryZh", ""),
        "trend_status": industry.get("status", ""),
        "trend_score": _to_float(industry.get("trendScore")),
        "framework_market_confirmation": _to_float(industry.get("marketConfirmation")),
        "v3_status": "no_market_mapping",
        "market_price_confirmation_score": None,
        "ma50_ratio": None,
        "median_3m_return": None,
        "relative_strength": None,
        "valid_ticker_count": 0,
        "failed_tickers": "",
        "news_heat_score": None,
        "heat_direction": None,
    }


def base_display_row(industry: dict[str, Any], lang: str) -> dict[str, Any]:
    """Return localized display fields."""

    text = RADAR_TEXT[lang]
    return {
        "industry_id": industry.get("id", ""),
        "industry": industry_name(industry, lang),
        "category": category_label(industry, lang),
        "trend_status": translate_status(industry.get("status", ""), lang),
        "trend_score": _score_number(industry.get("trendScore")),
        "framework_market": _score_number(industry.get("marketConfirmation")),
        "v3_status": text["not_configured"],
        "price_score": DASH,
        "ma50": DASH,
        "median_3m": DASH,
        "relative_strength": DASH,
        "valid_samples": DASH,
        "failed_tickers": text["none"],
        "price_score_change": DASH,
        "ma50_change": DASH,
        "relative_strength_change": DASH,
        "news_heat_score": text["not_configured"],
        "heat_direction": text["not_configured"],
        "sort_rank": 2,
        "score_sort": -1.0,
    }


def apply_catalyst_fields(industry_id: str, raw: dict[str, Any], display: dict[str, Any], lang: str) -> None:
    """Attach local V4.1 catalyst fields to radar rows."""

    catalyst = get_catalyst_data(industry_id)
    if not catalyst:
        return
    raw["news_heat_score"] = _to_float(catalyst.get("heat_score"))
    raw["heat_direction"] = catalyst.get("heat_direction")
    display["news_heat_score"] = _score_number(catalyst.get("heat_score"))
    display["heat_direction"] = localized_label(HEAT_DIRECTION_LABELS, catalyst.get("heat_direction"), lang)


def apply_change_columns(
    display: dict[str, Any],
    raw: dict[str, Any],
    previous: dict[str, Any] | None,
    lang: str,
) -> None:
    """Add historical change fields to the localized display row."""

    if not previous:
        return
    display["price_score_change"] = _number_change(
        raw.get("market_price_confirmation_score"),
        previous.get("market_price_confirmation_score"),
    )
    display["ma50_change"] = _percent_change(raw.get("ma50_ratio"), previous.get("ma50_ratio"))
    display["relative_strength_change"] = _percent_change(
        raw.get("relative_strength"),
        previous.get("relative_strength"),
    )


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


def filter_radar_records(
    records: list[dict[str, Any]],
    lang: str,
    watchlist: set[str],
) -> list[dict[str, Any]]:
    """Render filters and return matching radar records."""

    text = RADAR_TEXT[lang]
    categories = sorted({str(record["display"]["category"]) for record in records})
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

    show_watchlist = st.checkbox(text["watchlist_only"], value=False)
    query_lower = query.strip().lower()
    filtered = []
    for record in records:
        row = record["display"]
        if show_watchlist and row["industry_id"] not in watchlist:
            continue
        if selected_category != text["all"] and row["category"] != selected_category:
            continue
        if selected_status != text["all"] and row["v3_status"] != selected_status:
            continue
        score = row["price_score"]
        if isinstance(score, (int, float)) and score < min_score:
            continue
        if not isinstance(score, (int, float)) and min_score > 0:
            continue
        if query_lower and query_lower not in str(row["industry"]).lower():
            continue
        filtered.append(record)
    return filtered


def render_snapshot_controls(
    all_records: list[dict[str, Any]],
    filtered_records: list[dict[str, Any]],
    lang: str,
) -> None:
    """Render save and download controls."""

    text = RADAR_TEXT[lang]
    left, right = st.columns([1, 1])
    with left:
        if st.button(text["save_snapshot"], width="stretch"):
            path = save_snapshot([record["raw"] for record in all_records])
            st.success(f"{text['snapshot_saved']}: {path.name}")
    with right:
        csv_data = display_dataframe(filtered_records, lang).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            text["download"],
            data=csv_data,
            file_name=f"industry_radar_{date.today():%Y-%m-%d}.csv",
            mime="text/csv",
            width="stretch",
        )


def render_radar_charts(records: list[dict[str, Any]], watchlist: set[str], lang: str) -> None:
    """Render chart tabs from the already-built radar records."""

    text = RADAR_TEXT[lang]
    st.markdown(f"### {text['charts_title']}")
    st.caption(text["charts_note"])
    tab_price, tab_relative, tab_ma50, tab_news, tab_history = st.tabs(
        [
            text["price_top10"],
            text["relative_top10"],
            text["ma50_top10"],
            text["news_heat_top10"],
            text["watchlist_history"],
        ]
    )
    with tab_price:
        render_top10_bar(records, "market_price_confirmation_score", text["chart_price_score"], lang, percent=False)
    with tab_relative:
        render_top10_bar(records, "relative_strength", text["chart_relative_strength"], lang, percent=True)
    with tab_ma50:
        render_top10_bar(records, "ma50_ratio", text["chart_ma50"], lang, percent=True)
    with tab_news:
        st.caption(text["news_chart_note"])
        render_top10_bar(records, "news_heat_score", text["chart_news_heat"], lang, percent=False, require_v3=False)
    with tab_history:
        render_watchlist_history_chart(watchlist, lang)


def render_top10_bar(
    records: list[dict[str, Any]],
    metric_key: str,
    metric_label: str,
    lang: str,
    *,
    percent: bool,
    require_v3: bool = True,
) -> None:
    """Render one Top 10 horizontal bar chart."""

    text = RADAR_TEXT[lang]
    rows = []
    for record in records:
        raw = record["raw"]
        if require_v3 and raw.get("v3_status") != "available":
            continue
        value = _to_float(raw.get(metric_key))
        if value is None:
            continue
        chart_value = value * 100 if percent else value
        rows.append(
            {
                text["chart_industry"]: record["display"]["industry"],
                metric_label: chart_value,
                "text_value": f"{chart_value:.1f}%" if percent else f"{chart_value:.1f}",
            }
        )
    if not rows:
        st.info(text["no_chart_data"])
        return
    frame = pd.DataFrame(rows).sort_values(metric_label, ascending=False).head(10)
    if px is None:
        st.bar_chart(frame, x=text["chart_industry"], y=metric_label)
        return
    fig = px.bar(
        frame,
        x=metric_label,
        y=text["chart_industry"],
        orientation="h",
        text="text_value",
        labels={metric_label: metric_label, text["chart_industry"]: text["chart_industry"]},
    )
    fig.update_layout(height=max(360, 34 * len(frame) + 120), margin=dict(l=10, r=20, t=20, b=20))
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")


def render_watchlist_history_chart(watchlist: set[str], lang: str) -> None:
    """Render watchlist history from local snapshot CSV files."""

    text = RADAR_TEXT[lang]
    history = load_snapshot_history()
    required = {"snapshot_date", "industry_id", "market_price_confirmation_score"}
    if history.empty or not required.issubset(history.columns):
        st.info(text["not_enough_history"])
        return
    history = history[history["industry_id"].astype(str).isin(watchlist)].copy()
    history["market_price_confirmation_score"] = pd.to_numeric(
        history["market_price_confirmation_score"],
        errors="coerce",
    )
    history = history.dropna(subset=["snapshot_date", "market_price_confirmation_score"])
    if history["snapshot_date"].nunique() < 2:
        st.info(text["not_enough_history"])
        return
    label_source = "chinese_name" if lang == "zh" and "chinese_name" in history.columns else "industry_name"
    if label_source not in history.columns:
        label_source = "industry_id"
    history[text["chart_industry"]] = history[label_source].fillna(history["industry_id"]).astype(str)
    history[text["chart_date"]] = pd.to_datetime(history["snapshot_date"], errors="coerce")
    history = history.dropna(subset=[text["chart_date"]]).sort_values(text["chart_date"])
    if history.empty:
        st.info(text["no_chart_data"])
        return
    if px is None:
        pivot = history.pivot_table(
            index=text["chart_date"],
            columns=text["chart_industry"],
            values="market_price_confirmation_score",
            aggfunc="last",
        )
        st.line_chart(pivot)
        return
    fig = px.line(
        history,
        x=text["chart_date"],
        y="market_price_confirmation_score",
        color=text["chart_industry"],
        markers=True,
        labels={
            text["chart_date"]: text["chart_date"],
            "market_price_confirmation_score": text["chart_price_score"],
            text["chart_industry"]: text["chart_industry"],
        },
    )
    fig.update_layout(height=420, margin=dict(l=10, r=20, t=20, b=20))
    st.plotly_chart(fig, width="stretch")


def render_snapshot_expander(lang: str) -> None:
    """Render local snapshot inventory."""

    text = RADAR_TEXT[lang]
    summary = snapshot_summary()
    with st.expander(text["snapshots"], expanded=False):
        st.write(f"{text['snapshot_count']}: {summary['count']}")
        st.write(f"{text['latest_snapshot']}: {summary['latest'] or text['no_snapshots']}")
        st.write(f"{text['snapshot_dir']}: {summary['directory']}")
        files = summary["files"] or [text["no_snapshots"]]
        st.write(f"{text['snapshot_files']}:")
        for file_name in files:
            st.write(f"- {file_name}")


def render_radar_table(records: list[dict[str, Any]], lang: str) -> None:
    """Render the filtered radar display table."""

    df = display_dataframe(records, lang)
    st.dataframe(df, width="stretch", hide_index=True)


def display_dataframe(records: list[dict[str, Any]], lang: str) -> pd.DataFrame:
    """Return localized display dataframe sorted by V3 status and score."""

    text = RADAR_TEXT[lang]
    columns = text["columns"]
    rows = [record["display"] for record in records]
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=list(columns.values()))
    df = df.sort_values(["sort_rank", "score_sort"], ascending=[True, False])
    df = df.drop(columns=["industry_id", "sort_rank", "score_sort"])
    rename_map = {
        "industry": columns["industry"],
        "category": columns["category"],
        "trend_status": columns["trend_status"],
        "trend_score": columns["trend_score"],
        "framework_market": columns["framework_market"],
        "v3_status": columns["v3_status"],
        "price_score": columns["price_score"],
        "ma50": columns["ma50"],
        "median_3m": columns["median_3m"],
        "relative_strength": columns["relative_strength"],
        "valid_samples": columns["valid_samples"],
        "failed_tickers": columns["failed_tickers"],
        "price_score_change": columns["price_score_change"],
        "ma50_change": columns["ma50_change"],
        "relative_strength_change": columns["relative_strength_change"],
        "news_heat_score": columns["news_heat_score"],
        "heat_direction": columns["heat_direction"],
    }
    display_df = df.rename(columns=rename_map)
    for column in display_df.columns:
        display_df[column] = display_df[column].map(_display_cell)
    return display_df


def _score_number(value: object) -> float | str:
    formatted = format_score(value)
    if formatted == "N/A":
        return DASH
    return round(float(formatted), 1)


def _percent_or_dash(value: object) -> str:
    return format_percent(value).replace("N/A", DASH)


def _signed_percent(value: object) -> str:
    if value is None:
        return DASH
    try:
        number = float(value)
    except (TypeError, ValueError):
        return DASH
    sign = "+" if number > 0 else ""
    return f"{sign}{number * 100:.1f}%"


def _number_change(current: object, previous: object) -> str:
    current_value = _to_float(current)
    previous_value = _to_float(previous)
    if current_value is None or previous_value is None:
        return DASH
    change = current_value - previous_value
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}"


def _percent_change(current: object, previous: object) -> str:
    current_value = _to_float(current)
    previous_value = _to_float(previous)
    if current_value is None or previous_value is None:
        return DASH
    change = current_value - previous_value
    sign = "+" if change > 0 else ""
    return f"{sign}{change * 100:.1f}%"


def _to_float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _display_cell(value: object) -> str:
    """Return a string-only display value to keep Arrow column types stable."""

    if value is None:
        return DASH
    try:
        if pd.isna(value):
            return DASH
    except (TypeError, ValueError):
        pass
    return str(value)
