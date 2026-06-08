"""Industry radar overview for the standalone trend search app."""

from __future__ import annotations

from datetime import date
from time import perf_counter
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
from src.industry_news_provider import (
    NEWS_CACHE_PATH,
    cached_news_is_fresh,
    load_news_cache,
    read_industry_news,
    refresh_industry_news,
)
from src.industry_overall_view import compute_overall_view
from src.industry_radar_history import (
    latest_radar_updated_at,
    load_latest_radar_frame,
    load_latest_snapshot_lookup,
    load_snapshot_history,
    load_watchlist,
    save_latest_radar,
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
        "refresh_market": "刷新市场数据",
        "market_refresh_done": "市场数据已刷新，缓存已更新。",
        "market_refresh_failed": "刷新失败，当前仍使用旧市场缓存。",
        "market_refresh_partial": "市场数据已刷新，但部分行业数据不可用，已保留失败状态。",
        "no_radar_cache": "暂无本地雷达缓存，请点击“刷新市场数据”生成。",
        "no_news_cache": "暂无新闻缓存，请展开“数据更新与维护”。",
        "load_watchlist_first": "优先加载收藏行业",
        "data_source": "数据来源",
        "local_cache": "本地缓存",
        "live_refresh": "实时刷新",
        "market_updated": "市场数据更新时间",
        "news_updated": "新闻数据更新时间",
        "industry_count": "行业数量",
        "load_time": "加载耗时",
        "advanced_metrics": "高级指标",
        "charts_expander": "图表",
        "snapshots_export": "历史快照与导出",
        "watchlist_manager": "观察列表管理",
        "news_refresh_expander": "新闻刷新",
        "data_update_maintenance": "数据更新与维护",
        "guides_expander": "说明 Guide",
        "developer_details": "开发者信息",
        "watchlist_note": "观察列表筛选使用上方“仅显示收藏行业”。观察列表内容保存在本地 watchlist.json。",
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
        "load_note": "雷达页默认读取本地缓存；只有点击刷新按钮才会联网更新市场数据。",
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
        "live_news_top10": "7天新闻热度 Top 10",
        "chart_live_news_count": "7天新闻数",
        "refresh_news": "刷新当前筛选行业新闻",
        "refresh_watchlist_news": "刷新收藏行业新闻",
        "refresh_top10_news": "刷新当前前 10 个行业新闻",
        "refresh_all_news": "刷新全部筛选行业新闻",
        "refresh_all_news_note": "刷新全部筛选行业可能较慢，因为需要逐个请求多个行业的新闻源。",
        "force_news_refresh": "强制刷新未过期缓存",
        "industries_to_refresh": "当前将刷新",
        "fresh_cache_skip": "其中 {count} 个行业缓存仍有效，将跳过。",
        "industries_available_refresh": "当前可刷新",
        "news_cache_valid": "新闻缓存当前有效，无需刷新。如需强制更新，可展开数据更新与维护。",
        "refreshing_news": "正在刷新新闻：第 {current} / {total} 个行业",
        "news_refresh_done": "新闻数据刷新完成",
        "columns": {
            "industry": "行业",
            "category": "分类",
            "overall_status": "综合状态",
            "priced_in_risk": "透支风险",
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
            "live_news_count_7d": "7天新闻数",
            "live_news_status": "实时新闻状态",
            "sort_rank": "排序",
        },
    },
    "en": {
        "title": "Industry Radar Overview",
        "subtitle": "Compare V1/V2 framework trend scores with V3 market-price confirmation data across industries.",
        "load": "Refresh / Load Radar Data",
        "refresh_market": "Refresh Market Data",
        "market_refresh_done": "Market data refreshed and cache updated.",
        "market_refresh_failed": "Refresh failed. The page is still using the old market cache.",
        "market_refresh_partial": "Market data refreshed, with unavailable industries preserved as failed status.",
        "no_radar_cache": "No local radar cache found. Click “Refresh Market Data” to generate it.",
        "no_news_cache": "No news cache found. Expand Data Update & Maintenance.",
        "load_watchlist_first": "Load Watchlist First",
        "data_source": "Data Source",
        "local_cache": "Local Cache",
        "live_refresh": "Live Refresh",
        "market_updated": "Market Data Updated",
        "news_updated": "News Data Updated",
        "industry_count": "Industry Count",
        "load_time": "Load Time",
        "advanced_metrics": "Advanced Metrics",
        "charts_expander": "Charts",
        "snapshots_export": "Snapshots & Export",
        "watchlist_manager": "Watchlist Manager",
        "news_refresh_expander": "News Refresh",
        "data_update_maintenance": "Data Update & Maintenance",
        "guides_expander": "Guides",
        "developer_details": "Developer Details",
        "watchlist_note": "Use Show Watchlist Only above to filter watchlist industries. The watchlist is stored in local watchlist.json.",
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
        "load_note": "The radar page reads local cache by default. Market data is refreshed online only when the button is clicked.",
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
        "live_news_top10": "7D News Heat Top 10",
        "chart_live_news_count": "7D News Count",
        "refresh_news": "Refresh News for Filtered Industries",
        "refresh_watchlist_news": "Refresh Watchlist News",
        "refresh_top10_news": "Refresh Top 10 Filtered Industries News",
        "refresh_all_news": "Refresh All Filtered Industries News",
        "refresh_all_news_note": "Refreshing all filtered industries may take longer because multiple industry news sources need to be requested.",
        "force_news_refresh": "Force refresh fresh cache",
        "industries_to_refresh": "Industries to refresh",
        "fresh_cache_skip": "{count} industries still have valid cache and will be skipped.",
        "industries_available_refresh": "Industries available for refresh",
        "news_cache_valid": "News cache is currently valid. Expand Data Update & Maintenance if you want to force refresh.",
        "refreshing_news": "Refreshing news: {current} / {total} industries",
        "news_refresh_done": "News data refresh completed",
        "columns": {
            "industry": "Industry",
            "category": "Category",
            "overall_status": "Overall Status",
            "priced_in_risk": "Priced-in Risk",
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
            "live_news_count_7d": "7D News Count",
            "live_news_status": "Live News Status",
            "sort_rank": "Sort",
        },
    },
}


def render_industry_radar_page(lang: str) -> None:
    """Render a cross-industry radar table."""

    started = perf_counter()
    _apply_industry_css()
    text = RADAR_TEXT[lang]

    st.markdown(f"## {text['title']}")
    st.caption(text["subtitle"])

    previous_snapshot = load_latest_snapshot_lookup(before=date.today())
    watchlist = set(load_watchlist())
    data_source = text["local_cache"]
    radar_records = build_cached_radar_records(lang, previous_snapshot)

    st.caption(text["load_note"])
    if not radar_records:
        st.info(text["no_radar_cache"])
    if not has_news_cache_entries():
        st.info(text["no_news_cache"])

    render_performance_strip(
        data_source=data_source,
        market_updated=latest_radar_updated_at(),
        news_updated=news_cache_updated_at(),
        industry_count=len(radar_records),
        load_seconds=perf_counter() - started,
        lang=lang,
    )
    filtered_records = filter_radar_records(radar_records, lang, watchlist)

    render_radar_table(filtered_records, lang, "simple")
    with st.expander(text["advanced_metrics"], expanded=False):
        render_radar_table(filtered_records, lang, "detailed")
    with st.expander(text["charts_expander"], expanded=False):
        render_radar_charts(filtered_records, watchlist, lang)
    with st.expander(text["snapshots_export"], expanded=False):
        render_snapshot_controls(radar_records, filtered_records, lang)
        render_snapshot_inventory(lang)
    with st.expander(text["watchlist_manager"], expanded=False):
        st.caption(text["watchlist_note"])
    with st.expander(text["data_update_maintenance"], expanded=False):
        if st.button(text["refresh_market"], width="content", key="radar_refresh_market_data"):
            success, message = refresh_market_radar_cache(lang, previous_snapshot)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)
        render_radar_news_refresh(filtered_records, watchlist, lang)
    with st.expander(text["guides_expander"], expanded=False):
        radar_catalyst_title = "新闻热度与催化事件说明" if lang == "zh" else "News Heat & Catalyst Guide"
        render_catalyst_event_guide(lang, title_override=radar_catalyst_title, wrap=False)
        render_trend_status_guide(lang, wrap=False)
        render_trend_stage_guide(lang, wrap=False)
    with st.expander(text["developer_details"], expanded=False):
        render_radar_table(filtered_records, lang, "developer")
        st.json(
            {
                "record_count": len(filtered_records),
                "market_cache_updated": latest_radar_updated_at(),
                "news_cache_updated": news_cache_updated_at(),
            }
        )
    st.caption(text["hint"])


def render_performance_strip(
    *,
    data_source: str,
    market_updated: str,
    news_updated: str,
    industry_count: int,
    load_seconds: float,
    lang: str,
) -> None:
    """Render lightweight cache and load metadata."""

    text = RADAR_TEXT[lang]
    missing = "—"
    message = (
        f"{text['data_source']}: {data_source} | "
        f"{text['market_updated']}: {market_updated or missing} | "
        f"{text['news_updated']}: {news_updated or missing} | "
        f"{text['industry_count']}: {industry_count} | "
        f"{text['load_time']}: {load_seconds:.2f}s"
    )
    st.caption(message)


def has_news_cache_entries() -> bool:
    """Return whether the local news cache has at least one industry entry."""

    try:
        cache = load_news_cache()
    except Exception:
        return False
    industries = cache.get("industries") if isinstance(cache, dict) else {}
    return bool(industries)


def news_cache_updated_at() -> str:
    """Return the news cache mtime if a cache file exists."""

    if not NEWS_CACHE_PATH.exists():
        return ""
    try:
        from datetime import datetime

        return datetime.fromtimestamp(NEWS_CACHE_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def refresh_market_radar_cache(
    lang: str,
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    """Rebuild full radar market rows and persist the latest local cache."""

    text = RADAR_TEXT[lang]
    try:
        get_market_confirmation_data.clear()
        refreshed_records = build_live_radar_records(lang, previous_snapshot)
        if not refreshed_records:
            return False, text["market_refresh_failed"]

        raw_rows = [record["raw"] for record in refreshed_records]
        mapped_rows = [
            row
            for row in raw_rows
            if str(row.get("industry_id", "")) in INDUSTRY_MARKET_TICKERS
        ]
        available_rows = [
            row
            for row in mapped_rows
            if str(row.get("v3_status", "")) == "available"
        ]
        if mapped_rows and not available_rows:
            return False, text["market_refresh_failed"]

        save_latest_radar(raw_rows)
        save_snapshot(raw_rows)
        clear_radar_page_caches()
        if len(available_rows) < len(mapped_rows):
            return True, text["market_refresh_partial"]
        return True, text["market_refresh_done"]
    except Exception as exc:
        return False, f"{text['market_refresh_failed']} {exc}"


def clear_radar_page_caches() -> None:
    """Clear local Streamlit caches that can keep stale radar data visible."""

    for cached_func in (load_snapshot_history,):
        try:
            cached_func.clear()
        except Exception:
            continue


def build_live_radar_records(
    lang: str,
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build localized display rows and stable snapshot rows with live market refresh."""

    previous_snapshot = previous_snapshot or {}
    return [build_radar_record(industry, lang, previous_snapshot) for industry in industryTrendData]


def build_cached_radar_records(
    lang: str,
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build radar records from local latest_radar.csv without network calls."""

    previous_snapshot = previous_snapshot or {}
    frame = load_latest_radar_frame()
    if frame.empty or "industry_id" not in frame.columns:
        return []

    industry_lookup = {str(industry.get("id", "")): industry for industry in industryTrendData}
    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw = normalize_cached_radar_row(row.to_dict())
        industry = industry_lookup.get(str(raw.get("industry_id", "")))
        if not industry:
            continue
        display = display_row_from_cached_raw(industry, raw, lang)
        apply_overall_fields(industry, raw, display, lang)
        apply_change_columns(display, raw, previous_snapshot.get(str(raw.get("industry_id", ""))), lang)
        records.append({"raw": raw, "display": display})
    return records


def normalize_cached_radar_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize latest radar CSV values into the raw row schema."""

    raw = dict(row)
    for key in (
        "trend_score",
        "framework_market_confirmation",
        "market_price_confirmation_score",
        "ma50_ratio",
        "median_3m_return",
        "relative_strength",
        "news_heat_score",
        "live_news_count_7d",
    ):
        raw[key] = _to_float(raw.get(key))
    valid_count = _to_float(raw.get("valid_ticker_count"))
    raw["valid_ticker_count"] = int(valid_count or 0)
    for key in ("failed_tickers", "heat_direction", "live_news_status", "v3_status"):
        value = raw.get(key)
        raw[key] = "" if value is None or pd.isna(value) else str(value)
    return raw


def display_row_from_cached_raw(industry: dict[str, Any], raw: dict[str, Any], lang: str) -> dict[str, Any]:
    """Return localized display values from one cached raw radar row."""

    text = RADAR_TEXT[lang]
    display = base_display_row(industry, lang)
    apply_catalyst_fields(str(industry.get("id", "")), raw, display, lang)
    apply_live_news_fields(str(industry.get("id", "")), raw, display, lang)

    failed_tickers = split_failed_tickers(raw.get("failed_tickers"))
    display["failed_tickers"] = ", ".join(failed_tickers) if failed_tickers else text["none"]
    display["valid_samples"] = int(raw.get("valid_ticker_count") or 0)

    status = str(raw.get("v3_status") or "no_market_mapping")
    if status == "available":
        display["v3_status"] = text["available"]
        display["price_score"] = _score_number(raw.get("market_price_confirmation_score"))
        display["ma50"] = _percent_or_dash(raw.get("ma50_ratio"))
        display["median_3m"] = _percent_or_dash(raw.get("median_3m_return"))
        display["relative_strength"] = _signed_percent(raw.get("relative_strength"))
        display["sort_rank"] = 0
        display["score_sort"] = raw.get("market_price_confirmation_score") or -1.0
    elif status == "market_data_failed":
        display["v3_status"] = text["data_failed"]
        display["sort_rank"] = 1
    else:
        display["v3_status"] = text["not_configured"]
        display["sort_rank"] = 2 if status == "explicit_no_market_mapping" else 3
    return display


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
    apply_live_news_fields(industry_id, raw, display, lang)

    if industry_id not in INDUSTRY_MARKET_TICKERS:
        raw["v3_status"] = "explicit_no_market_mapping" if industry_id in EXPLICIT_NO_MARKET_MAPPING else "no_market_mapping"
        display["v3_status"] = text["not_configured"]
        display["sort_rank"] = 2 if industry_id in EXPLICIT_NO_MARKET_MAPPING else 3
        apply_overall_fields(industry, raw, display, lang)
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

    apply_overall_fields(industry, raw, display, lang)
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
        "overall_status": None,
        "priced_in_risk": None,
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
        "live_news_count_7d": None,
        "live_news_status": None,
    }


def base_display_row(industry: dict[str, Any], lang: str) -> dict[str, Any]:
    """Return localized display fields."""

    text = RADAR_TEXT[lang]
    return {
        "industry_id": industry.get("id", ""),
        "industry": industry_name(industry, lang),
        "category": category_label(industry, lang),
        "trend_status": translate_status(industry.get("status", ""), lang),
        "overall_status": DASH,
        "priced_in_risk": DASH,
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
        "live_news_count_7d": "暂无" if lang == "zh" else "N/A",
        "live_news_status": "暂无" if lang == "zh" else "N/A",
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


def apply_live_news_fields(industry_id: str, raw: dict[str, Any], display: dict[str, Any], lang: str) -> None:
    """Attach V4.2 cached live-news fields to radar rows without fetching."""

    result = read_industry_news(industry_id)
    count_7d = result.get("live_news_count_7d")
    status = str(result.get("live_news_status") or "not_configured")
    raw["live_news_count_7d"] = _to_float(count_7d)
    raw["live_news_status"] = status
    display["live_news_count_7d"] = str(int(count_7d or 0)) if result.get("failed_reason") != "cache_missing" else ("暂无" if lang == "zh" else "N/A")
    display["live_news_status"] = live_news_status_label(status, lang)


def apply_overall_fields(industry: dict[str, Any], raw: dict[str, Any], display: dict[str, Any], lang: str) -> None:
    """Attach deterministic overall view fields to radar rows."""

    overall = compute_overall_view(
        framework_trend_score=raw.get("trend_score"),
        market_price_confirmation_score=raw.get("market_price_confirmation_score"),
        news_heat_score=raw.get("news_heat_score"),
        valuation_pressure=industry.get("valuationPressure"),
        fundamental_validation=industry.get("fundamentalValidation"),
        ma50_ratio=raw.get("ma50_ratio"),
        trend_stage=str(industry.get("trendStage", "")),
        lang=lang,
    )
    raw["overall_status"] = overall["status_key"]
    raw["priced_in_risk"] = overall["priced_in_risk_key"]
    display["overall_status"] = overall["status_label"]
    display["priced_in_risk"] = overall["priced_in_risk_label"]


def live_news_status_label(status: str, lang: str) -> str:
    labels = {
        "zh": {
            "available": "可用",
            "no_recent_news": "暂无近期新闻",
            "fetch_failed": "抓取失败",
            "not_configured": "未配置",
        },
        "en": {
            "available": "available",
            "no_recent_news": "no_recent_news",
            "fetch_failed": "fetch_failed",
            "not_configured": "not_configured",
        },
    }
    return labels[lang].get(status, status)


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

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.4, 1])
    with c1:
        selected_category = st.selectbox(text["category_filter"], [text["all"], *categories])
    with c2:
        selected_status = st.selectbox(text["status_filter"], [text["all"], *statuses])
    with c3:
        query = st.text_input(text["search"], placeholder=text["search"])
    with c4:
        show_watchlist = st.checkbox(text["watchlist_only"], value=False)
    load_watchlist_first = True
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
        if query_lower and query_lower not in str(row["industry"]).lower():
            continue
        filtered.append(record)
    if load_watchlist_first:
        filtered.sort(
            key=lambda item: (
                0 if item["display"]["industry_id"] in watchlist else 1,
                item["display"].get("sort_rank", 9),
                -float(item["display"].get("score_sort") or -1.0),
            )
        )
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


def render_radar_news_refresh(records: list[dict[str, Any]], watchlist: set[str], lang: str) -> None:
    """Render tiered manual news refresh controls."""

    text = RADAR_TEXT[lang]
    unique_records = unique_industry_records(records)
    watchlist_records = [record for record in unique_records if str(record["raw"].get("industry_id")) in watchlist]
    top10_records = unique_records[:10]
    force_refresh = st.checkbox(text["force_news_refresh"], value=False)

    pending_watchlist, _skipped_watchlist = split_news_refresh_scope(watchlist_records, force_refresh)
    pending_top10, _skipped_top10 = split_news_refresh_scope(top10_records, force_refresh)
    pending_all, skipped_all = split_news_refresh_scope(unique_records, force_refresh)

    if not force_refresh and not pending_all:
        st.info(text["news_cache_valid"])
    else:
        st.caption(f"{text['industries_available_refresh']}: {len(pending_all)}")
    if pending_all and skipped_all:
        st.caption(text["fresh_cache_skip"].format(count=skipped_all))

    c1, c2, c3 = st.columns([1, 1.25, 1.25])
    with c1:
        refresh_watchlist = st.button(
            text["refresh_watchlist_news"],
            width="stretch",
            disabled=not pending_watchlist,
        )
    with c2:
        refresh_top10 = st.button(
            f"{text['refresh_top10_news']} ({len(pending_top10)})",
            width="stretch",
            disabled=not pending_top10,
        )
    with c3:
        refresh_all = st.button(
            f"{text['refresh_all_news']} ({len(pending_all)})",
            width="stretch",
            disabled=not pending_all,
        )
        st.caption(text["refresh_all_news_note"])

    selected_records: list[dict[str, Any]] = []
    if refresh_watchlist:
        selected_records = pending_watchlist
    elif refresh_top10:
        selected_records = pending_top10
    elif refresh_all:
        selected_records = pending_all

    if not selected_records:
        return
    refresh_news_records(selected_records, lang, force_refresh)
    st.success(text["news_refresh_done"])
    st.rerun()


def unique_industry_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one radar record per industry while preserving order."""

    seen = set()
    output = []
    for record in records:
        industry_id = str(record["raw"].get("industry_id", ""))
        if not industry_id or industry_id in seen:
            continue
        seen.add(industry_id)
        output.append(record)
    return output


def split_news_refresh_scope(
    records: list[dict[str, Any]],
    force_refresh: bool,
) -> tuple[list[dict[str, Any]], int]:
    """Return records needing refresh and the count skipped by TTL."""

    if force_refresh:
        return records, 0
    pending = []
    skipped = 0
    for record in records:
        industry_id = str(record["raw"].get("industry_id", ""))
        if industry_id and cached_news_is_fresh(industry_id):
            skipped += 1
            continue
        pending.append(record)
    return pending, skipped


def refresh_news_records(records: list[dict[str, Any]], lang: str, force_refresh: bool) -> None:
    """Refresh selected industries with progress feedback."""

    text = RADAR_TEXT[lang]
    industry_lookup = {str(item.get("id")): item for item in industryTrendData}
    progress = st.progress(0.0)
    status = st.empty()
    total = len(records)
    for index, record in enumerate(records, start=1):
        status.info(text["refreshing_news"].format(current=index, total=total))
        industry = industry_lookup.get(str(record["raw"].get("industry_id")))
        if industry:
            refresh_industry_news(industry, force=force_refresh)
        progress.progress(index / total)


def render_radar_charts(records: list[dict[str, Any]], watchlist: set[str], lang: str) -> None:
    """Render chart tabs from the already-built radar records."""

    text = RADAR_TEXT[lang]
    st.markdown(f"### {text['charts_title']}")
    st.caption(text["charts_note"])
    tab_price, tab_relative, tab_ma50, tab_news, tab_live_news, tab_history = st.tabs(
        [
            text["price_top10"],
            text["relative_top10"],
            text["ma50_top10"],
            text["news_heat_top10"],
            text["live_news_top10"],
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
    with tab_live_news:
        render_top10_bar(records, "live_news_count_7d", text["chart_live_news_count"], lang, percent=False, require_v3=False)
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
        if metric_key == "live_news_count_7d" and value <= 0:
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

    with st.expander(RADAR_TEXT[lang]["snapshots"], expanded=False):
        render_snapshot_inventory(lang)


def render_snapshot_inventory(lang: str) -> None:
    """Render local snapshot inventory content."""

    text = RADAR_TEXT[lang]
    summary = snapshot_summary()
    st.write(f"{text['snapshot_count']}: {summary['count']}")
    st.write(f"{text['latest_snapshot']}: {summary['latest'] or text['no_snapshots']}")
    st.write(f"{text['snapshot_dir']}: {summary['directory']}")
    files = summary["files"] or [text["no_snapshots"]]
    st.write(f"{text['snapshot_files']}:")
    for file_name in files:
        st.write(f"- {file_name}")


def render_radar_table(records: list[dict[str, Any]], lang: str, mode: str = "simple") -> None:
    """Render the filtered radar display table."""

    df = display_dataframe(records, lang, mode)
    st.dataframe(df, width="stretch", hide_index=True)


def display_dataframe(records: list[dict[str, Any]], lang: str, mode: str = "simple") -> pd.DataFrame:
    """Return localized display dataframe sorted by V3 status and score."""

    text = RADAR_TEXT[lang]
    columns = text["columns"]
    rows = [record["display"] for record in records]
    df = pd.DataFrame(rows)
    if df.empty:
        empty_df = pd.DataFrame(columns=list(columns.values()))
        return select_radar_display_columns(empty_df, columns, mode)
    df = df.sort_values(["sort_rank", "score_sort"], ascending=[True, False])
    df = df.drop(columns=["industry_id", "sort_rank", "score_sort"])
    rename_map = {
        "industry": columns["industry"],
        "category": columns["category"],
        "overall_status": columns["overall_status"],
        "priced_in_risk": columns["priced_in_risk"],
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
        "live_news_count_7d": columns["live_news_count_7d"],
        "live_news_status": columns["live_news_status"],
    }
    display_df = df.rename(columns=rename_map)
    display_df = select_radar_display_columns(display_df, columns, mode)
    for column in display_df.columns:
        display_df[column] = display_df[column].map(_display_cell)
    return display_df


def select_radar_display_columns(df: pd.DataFrame, columns: dict[str, str], mode: str) -> pd.DataFrame:
    """Return mode-specific radar columns."""

    simple_columns = [
        columns["industry"],
        columns["category"],
        columns["overall_status"],
        columns["price_score"],
        columns["news_heat_score"],
        columns["priced_in_risk"],
        columns["v3_status"],
        columns["live_news_status"],
    ]
    detailed_extra = [
        columns["trend_score"],
        columns["framework_market"],
        columns["ma50"],
        columns["median_3m"],
        columns["relative_strength"],
        columns["valid_samples"],
        columns["live_news_count_7d"],
    ]
    developer_extra = [
        columns["trend_status"],
        columns["failed_tickers"],
        columns["price_score_change"],
        columns["ma50_change"],
        columns["relative_strength_change"],
        columns["heat_direction"],
    ]
    selected = simple_columns
    if mode in {"detailed", "developer"}:
        selected = [*selected, *detailed_extra]
    if mode == "developer":
        selected = [*selected, *developer_extra]
    return df[[column for column in selected if column in df.columns]]


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


def split_failed_tickers(value: object) -> list[str]:
    """Split cached failed ticker text into stable display tokens."""

    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


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
