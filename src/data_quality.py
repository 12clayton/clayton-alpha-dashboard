"""Unified data-quality classification helpers for dashboard surfaces."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd


QUALITY_META = {
    "fresh": {
        "label": "数据正常",
        "severity": "ok",
        "explanation": "最新真实数据可用，可以正常参考。",
    },
    "stale": {
        "label": "数据滞后",
        "severity": "warning",
        "explanation": "数据日期偏旧，结论需要降权参考。",
    },
    "cache": {
        "label": "使用缓存",
        "severity": "warning",
        "explanation": "在线数据暂不可用，当前使用本地缓存。",
    },
    "proxy": {
        "label": "代理估算",
        "severity": "warning",
        "explanation": "当前使用代理资产或大类代理，不代表真实标的本身。",
    },
    "partial": {
        "label": "部分可用",
        "severity": "warning",
        "explanation": "部分数据可用，部分数据缺失。",
    },
    "missing": {
        "label": "数据缺失",
        "severity": "error",
        "explanation": "当前数据不可用，相关结论需要谨慎对待。",
    },
    "title_only": {
        "label": "仅标题",
        "severity": "warning",
        "explanation": "新闻正文不可用，仅基于标题判断。",
    },
    "manual": {
        "label": "手动录入",
        "severity": "warning",
        "explanation": "该数据来自手动维护，需确认更新时间。",
    },
    "public_fallback": {
        "label": "Public 展示数据",
        "severity": "warning",
        "explanation": "公网展示 fallback 数据，仅用于观察。",
    },
}


STATUS_ALIASES = {
    "": "missing",
    "nan": "missing",
    "none": "missing",
    "missing_nav": "missing",
    "missing_code": "missing",
    "nav_pending": "stale",
    "data_unavailable": "missing",
    "manual_nav": "manual",
    "stale_cache": "stale",
    "reference_market": "proxy",
    "proxy_estimated": "proxy",
    "partial_reference_market": "partial",
    "rss_summary": "partial",
    "summary_only": "partial",
    "yfinance": "fresh",
    "yahoo_chart_api": "fresh",
    "public_market": "fresh",
    "akshare": "fresh",
    "eastmoney_f10": "fresh",
    "daily_report": "fresh",
}


def normalize_quality_status(status: Any) -> str:
    """Normalize provider-specific quality strings to the dashboard vocabulary."""

    text = str(status or "").strip().lower()
    if text in QUALITY_META:
        return text
    return STATUS_ALIASES.get(text, text if text in QUALITY_META else "missing")


def quality_result(status: str, explanation: str | None = None) -> dict[str, str]:
    """Return the standard quality result structure."""

    normalized = normalize_quality_status(status)
    meta = QUALITY_META.get(normalized, QUALITY_META["missing"])
    return {
        "status": normalized,
        "label": meta["label"],
        "severity": meta["severity"],
        "explanation": explanation or meta["explanation"],
    }


def format_data_quality_badge(value: Any) -> str:
    """Format a quality value or quality-result dict for compact display."""

    if isinstance(value, dict):
        status = value.get("status", "missing")
    else:
        status = value
    result = quality_result(str(status))
    prefix = {"ok": "OK", "warning": "注意", "error": "缺失"}.get(result["severity"], "注意")
    return f"{prefix}｜{result['label']}"


def classify_market_data_quality(
    frame: pd.DataFrame | None = None,
    latest_date: Any = None,
    data_source: str | None = None,
    used_cache: bool | None = None,
) -> dict[str, str]:
    """Classify OHLC/close-price data freshness."""

    if frame is not None and isinstance(frame, pd.DataFrame) and not frame.empty and "Close" in frame.columns:
        if latest_date is None:
            latest_date = pd.to_datetime(frame.index, errors="coerce").max()
        if data_source is None:
            data_source = str(frame.attrs.get("data_source", ""))
    else:
        return quality_result("missing", "该 ticker 暂无可用价格数据。")

    source = str(data_source or "").lower()
    if used_cache is None:
        used_cache = source == "cache"
    if used_cache:
        return quality_result("cache", "该 ticker 当前使用缓存价格数据。")

    parsed_date = pd.to_datetime(latest_date, errors="coerce")
    if pd.isna(parsed_date):
        return quality_result("partial", "价格数据存在，但无法确认最新日期。")
    if parsed_date.date() < datetime.now().date() - timedelta(days=2):
        return quality_result("stale", f"最新价格日期为 {parsed_date.date()}，可能已经滞后。")
    return quality_result("fresh", f"最新价格日期为 {parsed_date.date()}。")


def classify_fund_nav_quality(nav: dict | pd.Series | None) -> dict[str, str]:
    """Classify real mutual-fund NAV data quality."""

    if nav is None:
        return quality_result("missing", "基金净值数据缺失。")
    record = nav.to_dict() if isinstance(nav, pd.Series) else dict(nav)
    raw_quality = str(record.get("data_quality", "") or "")
    source = str(record.get("data_source", "") or "")
    if raw_quality in {"missing_code", "missing_nav"}:
        explanation = "基金代码缺失，无法获取真实净值。" if raw_quality == "missing_code" else "接口和缓存都没有可用净值。"
        return quality_result("missing", explanation)
    if raw_quality == "manual_nav" or source == "manual_nav":
        return quality_result("manual", "基金净值来自手动录入。")
    if raw_quality in {"cache", "stale_cache"}:
        status = "stale" if raw_quality == "stale_cache" else "cache"
        return quality_result(status, "基金净值来自缓存，需留意是否已更新。")

    nav_date = pd.to_datetime(record.get("nav_date", ""), errors="coerce")
    if pd.isna(nav_date):
        return quality_result("stale", "基金净值日期不可用，可能尚未公布。")
    if nav_date.date() < datetime.now().date() - timedelta(days=3):
        return quality_result("stale", f"基金净值日期为 {nav_date.date()}，可能存在 QDII 滞后。")
    return quality_result("fresh", f"基金净值日期为 {nav_date.date()}。")


def classify_news_quality(news_items: pd.DataFrame | None = None, public_fallback: bool = False) -> dict[str, str]:
    """Classify news data quality from parsed RSS/report rows."""

    if news_items is None or not isinstance(news_items, pd.DataFrame) or news_items.empty:
        return quality_result("public_fallback" if public_fallback else "missing", "当前没有可解析新闻，保留研究框架。")
    qualities = {normalize_quality_status(value) for value in news_items.get("data_quality", pd.Series(dtype=str)).astype(str)}
    if not qualities:
        raw_available = news_items.get("raw_text_available", pd.Series(dtype=bool)).astype(bool)
        return quality_result("partial" if raw_available.any() else "title_only")
    if qualities == {"title_only"}:
        return quality_result("title_only", "新闻只有标题，卡片将做保守解读。")
    if "missing" in qualities and len(qualities) == 1:
        return quality_result("missing", "新闻源暂不可用。")
    if "partial" in qualities or "title_only" in qualities:
        return quality_result("partial", "部分新闻只有摘要或标题，没有完整正文。")
    return quality_result("fresh", "RSS 新闻数据正常。")


def classify_theme_quality(
    used_symbols: list[str] | None = None,
    missing_symbols: list[str] | None = None,
    fallback_reason: str = "",
) -> dict[str, str]:
    """Classify theme proxy-basket data quality."""

    used = [symbol for symbol in (used_symbols or []) if symbol]
    missing = [symbol for symbol in (missing_symbols or []) if symbol]
    if not used:
        return quality_result("missing", "该主题 proxy basket 全部缺失。")
    if fallback_reason or (used == ["SMH"] and missing):
        return quality_result("proxy", "该主题暂用大类代理，不能代表独立主题走势。")
    if missing:
        return quality_result("partial", "该主题部分 proxy 可用，部分缺失。")
    return quality_result("fresh", "该主题 proxy basket 数据完整。")


def summarize_overall_data_quality(
    market_quality: Any = None,
    fund_quality: Any = None,
    news_quality: Any = None,
    theme_quality: Any = None,
) -> dict[str, Any]:
    """Summarize page-level data quality and conclusion confidence."""

    groups = {
        "市场数据": _summarize_group(market_quality),
        "基金净值": _summarize_group(fund_quality),
        "新闻数据": _summarize_group(news_quality),
        "行业研究": _summarize_group(theme_quality),
    }
    severities = [item["severity"] for item in groups.values()]
    if "error" in severities:
        confidence = "低"
    elif "warning" in severities:
        confidence = "中"
    else:
        confidence = "高"
    return {"groups": groups, "confidence": confidence}


def _summarize_group(value: Any) -> dict[str, str]:
    """Summarize one quality group from statuses, dicts, or lists."""

    if value is None:
        return quality_result("missing")
    values = value if isinstance(value, list) else [value]
    results = []
    for item in values:
        if isinstance(item, dict):
            results.append(quality_result(item.get("status", "missing"), item.get("explanation")))
        else:
            results.append(quality_result(str(item)))
    if any(result["severity"] == "error" for result in results):
        return quality_result("missing")
    if any(result["severity"] == "warning" for result in results):
        return quality_result("partial")
    return quality_result("fresh")
