"""Local Markdown / JSON export helpers for one industry analysis page."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.industry_overall_view import compute_overall_view, format_overall_score


EXPORT_TEXT = {
    "zh": {
        "prompt": (
            "请基于以下行业趋势系统导出的上下文，帮我做一份结构化分析。重点判断：\n"
            "1. 当前行业趋势是否健康；\n"
            "2. 是否存在热度与价格背离；\n"
            "3. 是否存在提前透支未来收益的风险；\n"
            "4. 哪些指标最关键；\n"
            "5. 后续应该观察哪些信号。\n"
            "不要给出直接交易指令。"
        ),
        "na": "暂无",
        "title": "行业趋势分析上下文",
        "basic": "基础信息",
        "overall": "综合判断",
        "scores": "核心评分",
        "market": "V3 市场价格确认摘要",
        "catalysts": "V4.1 新闻热度与催化事件",
        "live_news": "V4.2 实时新闻观察",
        "chain": "产业链与风险信号",
        "notes": "数据说明",
        "notes_items": [
            "V3 使用市场价格代理数据。",
            "V4.1 是本地催化事件框架。",
            "V4.2 是轻量真实新闻观察。",
            "该导出不代表完整研究结论。",
        ],
    },
    "en": {
        "prompt": (
            "Please analyze the following exported industry trend context. Focus on:\n"
            "1. whether the industry trend is healthy;\n"
            "2. whether there is heat-price divergence;\n"
            "3. whether there is priced-in risk;\n"
            "4. which indicators matter most;\n"
            "5. what signals should be monitored next.\n"
            "Do not provide direct trading instructions."
        ),
        "na": "N/A",
        "title": "Industry Trend Analysis Context",
        "basic": "Basic Information",
        "overall": "Overall View",
        "scores": "Framework Scores",
        "market": "V3 Market Price Confirmation Summary",
        "catalysts": "V4.1 News Heat & Catalysts",
        "live_news": "V4.2 Live News Watch",
        "chain": "Industry Chain & Risk Signals",
        "notes": "Data Notes",
        "notes_items": [
            "V3 uses market-price proxy data.",
            "V4.1 is a local catalyst-event framework.",
            "V4.2 is a lightweight live-news watch layer.",
            "This export does not represent a full research conclusion.",
        ],
    },
}


def build_industry_export_context(
    *,
    industry: dict[str, Any],
    market_result: dict[str, Any],
    catalyst: dict[str, Any] | None,
    live_news: dict[str, Any],
    lang: str,
    trend_stage: str,
    category: str,
    trend_summary: str,
) -> dict[str, Any]:
    """Build a stable export context without fetching additional data."""

    price_score = market_result.get("score") if market_result.get("available") else None
    heat_score = catalyst.get("heat_score") if catalyst else None
    ma50_ratio = market_result.get("above_ma50_ratio") if market_result.get("available") else None
    overall = compute_overall_view(
        framework_trend_score=industry.get("trendScore"),
        market_price_confirmation_score=price_score,
        news_heat_score=heat_score,
        valuation_pressure=industry.get("valuationPressure"),
        fundamental_validation=industry.get("fundamentalValidation"),
        ma50_ratio=ma50_ratio,
        trend_stage=trend_stage,
        lang=lang,
    )
    return {
        "industry_id": industry.get("id"),
        "industry_name": industry.get("name"),
        "chinese_name": industry.get("chineseName"),
        "category": industry.get("category"),
        "category_zh": industry.get("categoryZh"),
        "display_category": category,
        "trend_summary": trend_summary,
        "overall_view": {
            "overall_status": overall["status_label"],
            "trend_stage": trend_stage,
            "price_confirmation": format_overall_score(price_score, lang),
            "news_heat": format_overall_score(heat_score, lang),
            "priced_in_risk": overall["priced_in_risk_label"],
            "key_tags": overall["tags"],
            "one_line_view": overall["one_line"],
        },
        "framework_scores": {
            "trend_score": industry.get("trendScore"),
            "framework_market_confirmation": industry.get("marketConfirmation"),
            "fundamental_validation": industry.get("fundamentalValidation"),
            "valuation_pressure": industry.get("valuationPressure"),
            "macro_sensitivity": industry.get("macroSensitivity"),
        },
        "market_confirmation": {
            "market_price_confirmation_score": price_score,
            "above_ma20_ratio": market_result.get("above_ma20_ratio"),
            "above_ma50_ratio": market_result.get("above_ma50_ratio"),
            "above_ma200_ratio": market_result.get("above_ma200_ratio"),
            "median_3m_return": market_result.get("median_3m_return"),
            "relative_strength": market_result.get("relative_strength"),
            "v3_status": "available" if market_result.get("available") else market_result.get("reason_code"),
            "valid_ticker_count": market_result.get("valid_ticker_count"),
            "failed_tickers": market_result.get("failed_tickers") or [],
        },
        "catalysts": normalize_catalyst(catalyst),
        "live_news": normalize_live_news(live_news),
        "industry_chain": {
            "drivers": industry.get("keyDrivers", []),
            "subsectors": industry.get("subSectors", []),
            "risk_signals": localized_list(industry, "riskSignals", lang),
            "chain": industry.get("industryChainZh" if lang == "zh" else "industryChain") or industry.get("industryChain", {}),
        },
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_industry_markdown(context: dict[str, Any], lang: str) -> str:
    """Build copy-ready Markdown export."""

    text = EXPORT_TEXT[lang]
    na = text["na"]
    overall = context["overall_view"]
    scores = context["framework_scores"]
    market = context["market_confirmation"]
    catalysts = context["catalysts"]
    live_news = context["live_news"]
    chain = context["industry_chain"]
    lines = [
        text["prompt"],
        "",
        f"# {text['title']}",
        "",
        f"## {text['basic']}",
        f"- Industry ID: {context.get('industry_id') or na}",
        f"- Industry: {context.get('industry_name') or na}",
        f"- Chinese Name: {context.get('chinese_name') or na}",
        f"- Category: {context.get('display_category') or na}",
        "",
        f"## {text['overall']}",
        f"- Overall Status: {overall.get('overall_status') or na}",
        f"- Trend Stage: {overall.get('trend_stage') or na}",
        f"- Price Confirmation: {overall.get('price_confirmation') or na}",
        f"- News Heat: {overall.get('news_heat') or na}",
        f"- Priced-in Risk: {overall.get('priced_in_risk') or na}",
        f"- Key Tags: {', '.join(overall.get('key_tags') or []) or na}",
        f"- One-line View: {overall.get('one_line_view') or na}",
        f"- Trend Summary: {context.get('trend_summary') or na}",
        "",
        f"## {text['scores']}",
    ]
    for key, value in scores.items():
        lines.append(f"- {key}: {value if value is not None else na}")
    lines.extend(["", f"## {text['market']}"])
    for key, value in market.items():
        lines.append(f"- {key}: {format_export_value(value, na)}")
    lines.extend(["", f"## {text['catalysts']}"])
    lines.append(f"- heat_score: {format_export_value(catalysts.get('heat_score'), na)}")
    lines.append(f"- heat_level: {format_export_value(catalysts.get('heat_level'), na)}")
    lines.append(f"- heat_direction: {format_export_value(catalysts.get('heat_direction'), na)}")
    lines.append(f"- summary: {catalysts.get('summary') or na}")
    for event in catalysts.get("events", []):
        lines.append(f"- {event.get('date', '')}: {event.get('title', '')} ({event.get('type', '')}, {event.get('impact', '')})")
    lines.extend(["", f"## {text['live_news']}"])
    for key in ["live_news_count_7d", "live_news_status", "latest_news_time"]:
        lines.append(f"- {key}: {format_export_value(live_news.get(key), na)}")
    for item in live_news.get("items", [])[:5]:
        lines.append(f"- {item.get('published_at', '')}: {item.get('title', '')} - {item.get('publisher', '')}")
    lines.extend(["", f"## {text['chain']}"])
    lines.append(f"- Drivers: {format_export_value([driver.get('nameZh') or driver.get('name') for driver in chain.get('drivers', [])], na)}")
    lines.append(f"- Sub-sectors: {format_export_value([item.get('nameZh') or item.get('name') for item in chain.get('subsectors', [])], na)}")
    lines.append(f"- Risk Signals: {format_export_value(chain.get('risk_signals'), na)}")
    lines.append(f"- Chain Map: {format_export_value(chain.get('chain'), na)}")
    lines.extend(["", f"## {text['notes']}"])
    lines.extend([f"- {item}" for item in text["notes_items"]])
    return "\n".join(lines)


def build_industry_json(context: dict[str, Any]) -> str:
    """Build JSON export text."""

    return json.dumps(context, ensure_ascii=False, indent=2)


def normalize_catalyst(catalyst: dict[str, Any] | None) -> dict[str, Any]:
    if not catalyst:
        return {"events": []}
    return {
        "heat_score": catalyst.get("heat_score"),
        "heat_level": catalyst.get("heat_level"),
        "heat_direction": catalyst.get("heat_direction"),
        "summary": catalyst.get("summary"),
        "summaryZh": catalyst.get("summaryZh"),
        "events": catalyst.get("events", []),
    }


def normalize_live_news(live_news: dict[str, Any]) -> dict[str, Any]:
    items = [
        item
        for item in (live_news.get("items") or [])
        if item.get("relevance", "high") in {"high", "medium"}
    ]
    return {
        "live_news_count_7d": live_news.get("live_news_count_7d"),
        "live_news_status": live_news.get("live_news_status"),
        "latest_news_time": live_news.get("latest_news_time"),
        "items": items,
        "low_relevance_count": live_news.get("low_relevance_count", 0),
    }


def localized_list(industry: dict[str, Any], key: str, lang: str) -> list[Any]:
    if lang == "zh":
        return industry.get(f"{key}Zh") or industry.get(key) or []
    return industry.get(key) or industry.get(f"{key}Zh") or []


def format_export_value(value: Any, missing: str) -> str:
    if value is None or value == "":
        return missing
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else missing
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
