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
        "catalyst_review": "V4.10 催化复核",
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
        "catalyst_review": "V4.10 Catalyst Review",
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

MARKDOWN_LABELS = {
    "zh": {
        "industry_id": "行业 ID",
        "industry_name": "行业英文名",
        "chinese_name": "行业中文名",
        "category": "分类",
        "overall_status": "综合状态",
        "trend_stage": "趋势阶段",
        "price_confirmation": "价格确认",
        "news_heat": "新闻热度",
        "priced_in_risk": "透支风险",
        "key_tags": "关键标签",
        "one_line_view": "一句话解释",
        "trend_summary": "趋势摘要",
        "trend_score": "趋势评分",
        "framework_market_confirmation": "框架市场确认",
        "fundamental_validation": "基本验证",
        "valuation_pressure": "估值压力",
        "macro_sensitivity": "宏观敏感度",
        "market_price_confirmation_score": "市场价格确认分",
        "above_ma20_ratio": "MA20 比例",
        "above_ma50_ratio": "MA50 比例",
        "above_ma200_ratio": "MA200 比例",
        "median_3m_return": "3个月中位数表现",
        "relative_strength": "相对强弱",
        "v3_status": "V3 状态",
        "valid_ticker_count": "有效样本数",
        "failed_tickers": "下载失败 ticker",
        "heat_score": "新闻热度分",
        "heat_level": "热度等级",
        "heat_direction": "热度方向",
        "summary": "摘要",
        "events": "催化事件",
        "live_news_count_7d": "7天新闻数",
        "live_news_status": "实时新闻状态",
        "latest_news_time": "最新新闻时间",
        "recent_news": "最近新闻",
        "drivers": "核心驱动因素",
        "subsectors": "子行业",
        "risk_signals": "风险信号",
        "chain_map": "产业链地图",
        "review_status": "复核状态",
        "evidence_level": "证据强度",
        "one_line_review": "一句话复核",
        "supported_catalysts": "已支持催化",
        "emerging_catalysts": "新出现线索",
        "weak_or_missing_evidence": "证据不足说明",
        "reviewed_at": "复核时间",
    },
    "en": {
        "industry_id": "Industry ID",
        "industry_name": "Industry",
        "chinese_name": "Chinese Name",
        "category": "Category",
        "overall_status": "Overall Status",
        "trend_stage": "Trend Stage",
        "price_confirmation": "Price Confirmation",
        "news_heat": "News Heat",
        "priced_in_risk": "Priced-in Risk",
        "key_tags": "Key Tags",
        "one_line_view": "One-line View",
        "trend_summary": "Trend Summary",
        "trend_score": "trend_score",
        "framework_market_confirmation": "framework_market_confirmation",
        "fundamental_validation": "fundamental_validation",
        "valuation_pressure": "valuation_pressure",
        "macro_sensitivity": "macro_sensitivity",
        "market_price_confirmation_score": "market_price_confirmation_score",
        "above_ma20_ratio": "above_ma20_ratio",
        "above_ma50_ratio": "above_ma50_ratio",
        "above_ma200_ratio": "above_ma200_ratio",
        "median_3m_return": "median_3m_return",
        "relative_strength": "relative_strength",
        "v3_status": "v3_status",
        "valid_ticker_count": "valid_ticker_count",
        "failed_tickers": "failed_tickers",
        "heat_score": "heat_score",
        "heat_level": "heat_level",
        "heat_direction": "heat_direction",
        "summary": "summary",
        "events": "events",
        "live_news_count_7d": "live_news_count_7d",
        "live_news_status": "live_news_status",
        "latest_news_time": "latest_news_time",
        "recent_news": "recent_news",
        "drivers": "Drivers",
        "subsectors": "Sub-sectors",
        "risk_signals": "Risk Signals",
        "chain_map": "Chain Map",
        "review_status": "review_status",
        "evidence_level": "evidence_level",
        "one_line_review": "one_line_review",
        "supported_catalysts": "supported_catalysts",
        "emerging_catalysts": "emerging_catalysts",
        "weak_or_missing_evidence": "weak_or_missing_evidence",
        "reviewed_at": "reviewed_at",
    },
}

EXPORT_TEXT["zh"].update({"dynamic_snapshot": "V4.12 动态催化快照"})
EXPORT_TEXT["en"].update({"dynamic_snapshot": "V4.12 Dynamic Catalyst Snapshot"})

MARKDOWN_LABELS["zh"].update(
    {
        "news_source": "新闻来源",
        "source_type": "来源类型",
        "low_relevance_count": "低相关新闻数",
        "snapshot_generated_at": "快照更新时间",
        "framework_record_dates": "本地框架记录日期",
        "dynamic_status": "动态状态",
        "active_catalysts": "当前活跃催化",
        "active_catalyst_themes": "当前活跃催化主题",
        "emerging_catalyst_themes": "新出现催化主题",
        "cooling_catalysts": "降温催化线索",
        "one_line_snapshot": "一句话快照",
        "coverage_note": "覆盖说明",
    }
)
MARKDOWN_LABELS["en"].update(
    {
        "news_source": "News Source",
        "source_type": "Source Type",
        "low_relevance_count": "low_relevance_count",
        "snapshot_generated_at": "snapshot_generated_at",
        "framework_record_dates": "framework_record_dates",
        "dynamic_status": "dynamic_status",
        "active_catalysts": "active_catalysts",
        "active_catalyst_themes": "active_catalyst_themes",
        "emerging_catalyst_themes": "emerging_catalyst_themes",
        "cooling_catalysts": "cooling_catalysts",
        "one_line_snapshot": "one_line_snapshot",
        "coverage_note": "coverage_note",
    }
)

MARKDOWN_LABELS["zh"].update(
    {
        "framework_is_override": "是否为更新后的框架",
        "framework_updated_at": "最新框架更新时间",
        "base_framework_dates": "基础框架记录日期",
        "effective_framework_events": "当前 effective framework events",
    }
)
MARKDOWN_LABELS["en"].update(
    {
        "framework_is_override": "framework_is_override",
        "framework_updated_at": "framework_updated_at",
        "base_framework_dates": "base_framework_dates",
        "effective_framework_events": "effective_framework_events",
    }
)

HEAT_LEVEL_LABELS_ZH = {
    "Low": "低",
    "Medium": "中",
    "High": "高",
    "Very High": "很高",
}

HEAT_DIRECTION_LABELS_ZH = {
    "Rising": "升温",
    "Stable": "稳定",
    "Falling": "降温",
    "Mixed": "分化",
}

LIVE_NEWS_STATUS_LABELS_ZH = {
    "available": "可用",
    "no_recent_news": "暂无高相关新闻",
    "fetch_failed": "抓取失败",
    "not_configured": "未配置",
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
    catalyst_review: dict[str, Any] | None = None,
    dynamic_catalyst_snapshot: dict[str, Any] | None = None,
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
        "catalyst_framework": normalize_catalyst_framework(catalyst),
        "catalyst_review": normalize_catalyst_review(catalyst_review),
        "dynamic_catalyst_snapshot": normalize_dynamic_catalyst_snapshot(dynamic_catalyst_snapshot),
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
    framework = context.get("catalyst_framework") or {}
    catalyst_review = context.get("catalyst_review") or {}
    dynamic_snapshot = context.get("dynamic_catalyst_snapshot") or {}
    live_news = context["live_news"]
    chain = context["industry_chain"]
    labels = MARKDOWN_LABELS[lang]
    lines = [
        text["prompt"],
        "",
        f"# {text['title']}",
        "",
        f"## {text['basic']}",
        f"- {labels['industry_id']}: {context.get('industry_id') or na}",
        f"- {labels['industry_name']}: {context.get('industry_name') or na}",
        f"- {labels['chinese_name']}: {context.get('chinese_name') or na}",
        f"- {labels['category']}: {context.get('display_category') or na}",
        "",
        f"## {text['overall']}",
        f"- {labels['overall_status']}: {overall.get('overall_status') or na}",
        f"- {labels['trend_stage']}: {overall.get('trend_stage') or na}",
        f"- {labels['price_confirmation']}: {overall.get('price_confirmation') or na}",
        f"- {labels['news_heat']}: {overall.get('news_heat') or na}",
        f"- {labels['priced_in_risk']}: {overall.get('priced_in_risk') or na}",
        f"- {labels['key_tags']}: {', '.join(overall.get('key_tags') or []) or na}",
        f"- {labels['one_line_view']}: {overall.get('one_line_view') or na}",
        f"- {labels['trend_summary']}: {context.get('trend_summary') or na}",
        "",
        f"## {text['scores']}",
    ]
    for key, value in scores.items():
        lines.append(f"- {labels.get(key, key)}: {value if value is not None else na}")
    lines.extend(["", f"## {text['market']}"])
    for key, value in market.items():
        lines.append(f"- {labels.get(key, key)}: {format_export_value(value, na)}")
    lines.extend(["", f"## {text['catalysts']}"])
    lines.append(f"- {labels['framework_is_override']}: {format_export_value(framework.get('is_override'), na)}")
    lines.append(f"- {labels['framework_updated_at']}: {format_export_value(framework.get('updated_at'), na)}")
    lines.append(f"- {labels['base_framework_dates']}: {format_export_value(framework.get('base_framework_dates'), na)}")
    lines.append(f"- {labels['heat_score']}: {format_export_value(catalysts.get('heat_score'), na)}")
    lines.append(f"- {labels['heat_level']}: {localized_heat_level(catalysts.get('heat_level'), lang) or na}")
    lines.append(f"- {labels['heat_direction']}: {localized_heat_direction(catalysts.get('heat_direction'), lang) or na}")
    lines.append(f"- {labels['summary']}: {localized_value(catalysts, 'summary', lang) or na}")
    lines.append(f"- {labels['events']}:")
    for event in catalysts.get("events", []):
        title = localized_value(event, "title", lang)
        event_type = localized_value(event, "event_type", lang)
        impact = localized_value(event, "impact", lang)
        confidence = localized_value(event, "confidence", lang)
        description = localized_value(event, "description", lang)
        lines.append(
            f"  - {event.get('date', '')}: {title or na} "
            f"({event_type or na}, {impact or na}, {confidence or na})"
        )
        if description:
            lines.append(f"    - {description}")
    lines.extend(["", f"## {text['catalyst_review']}"])
    review_status = localized_review_value(catalyst_review, "review_status", lang)
    evidence_level = localized_review_value(catalyst_review, "evidence_level", lang)
    one_line_review = localized_review_value(catalyst_review, "one_line_review", lang)
    weak_note = catalyst_review.get("weak_or_missing_evidence") or []
    lines.append(f"- {labels['review_status']}: {review_status or na}")
    lines.append(f"- {labels['evidence_level']}: {evidence_level or na}")
    lines.append(f"- {labels['one_line_review']}: {one_line_review or na}")
    lines.append(f"- {labels['active_catalyst_themes']}: {format_export_value(format_theme_names(catalyst_review.get('active_catalyst_themes'), lang), na)}")
    lines.append(f"- {labels['emerging_catalyst_themes']}: {format_export_value(format_theme_names(catalyst_review.get('emerging_catalyst_themes'), lang), na)}")
    lines.append(f"- {labels['supported_catalysts']}: {format_export_value(catalyst_review.get('supported_catalysts'), na)}")
    lines.append(f"- {labels['emerging_catalysts']}: {format_export_value(catalyst_review.get('emerging_catalysts'), na)}")
    lines.append(f"- {labels['weak_or_missing_evidence']}: {format_export_value(weak_note, na)}")
    lines.append(f"- {labels['reviewed_at']}: {format_export_value(catalyst_review.get('reviewed_at'), na)}")
    lines.extend(["", f"## {text['dynamic_snapshot']}"])
    snapshot_status = localized_snapshot_value(dynamic_snapshot, "review_status", lang)
    snapshot_evidence = localized_snapshot_value(dynamic_snapshot, "evidence_level", lang)
    snapshot_one_line = localized_snapshot_value(dynamic_snapshot, "one_line_snapshot", lang)
    snapshot_coverage = localized_snapshot_value(dynamic_snapshot, "coverage_note", lang)
    active_key = "active_catalysts_zh" if lang == "zh" else "active_catalysts"
    emerging_key = "emerging_catalysts_zh" if lang == "zh" else "emerging_catalysts"
    cooling_key = "cooling_catalysts_zh" if lang == "zh" else "cooling_catalysts"
    lines.append(f"- {labels['snapshot_generated_at']}: {format_export_value(dynamic_snapshot.get('snapshot_generated_at'), na)}")
    lines.append(f"- {labels['framework_record_dates']}: {format_export_value(dynamic_snapshot.get('framework_record_dates'), na)}")
    lines.append(f"- {labels['dynamic_status']}: {snapshot_status or na}")
    lines.append(f"- {labels['evidence_level']}: {snapshot_evidence or na}")
    lines.append(f"- {labels['one_line_snapshot']}: {snapshot_one_line or na}")
    lines.append(f"- {labels['active_catalyst_themes']}: {format_export_value(format_theme_names(dynamic_snapshot.get('active_catalyst_themes'), lang), na)}")
    lines.append(f"- {labels['emerging_catalyst_themes']}: {format_export_value(format_theme_names(dynamic_snapshot.get('emerging_catalyst_themes'), lang), na)}")
    lines.append(f"- {labels['active_catalysts']}: {format_export_value(dynamic_snapshot.get(active_key), na)}")
    lines.append(f"- {labels['emerging_catalysts']}: {format_export_value(dynamic_snapshot.get(emerging_key), na)}")
    lines.append(f"- {labels['cooling_catalysts']}: {format_export_value(dynamic_snapshot.get(cooling_key), na)}")
    lines.append(f"- {labels['coverage_note']}: {snapshot_coverage or na}")
    lines.extend(["", f"## {text['live_news']}"])
    lines.append(f"- {labels['news_source']}: {format_export_value(live_news.get('source_names'), na)}")
    lines.append(f"- {labels['source_type']}: {format_export_value(live_news.get('source_types'), na)}")
    lines.append(f"- {labels['low_relevance_count']}: {format_export_value(live_news.get('low_relevance_count'), na)}")
    for key in ["live_news_count_7d", "live_news_status", "latest_news_time"]:
        value = localized_live_news_status(live_news.get(key), lang) if key == "live_news_status" else live_news.get(key)
        lines.append(f"- {labels[key]}: {format_export_value(value, na)}")
    lines.append(f"- {labels['recent_news']}:")
    for item in live_news.get("items", [])[:5]:
        lines.append(f"  - {item.get('published_at', '')}: {item.get('title', '')} - {item.get('publisher', '')}")
    lines.extend(["", f"## {text['chain']}"])
    lines.append(f"- {labels['drivers']}: {format_export_value(format_drivers(chain.get('drivers', []), lang), na)}")
    lines.append(f"- {labels['subsectors']}: {format_export_value(localized_named_items(chain.get('subsectors', []), lang), na)}")
    lines.append(f"- {labels['risk_signals']}: {format_export_value(chain.get('risk_signals'), na)}")
    lines.append(f"- {labels['chain_map']}: {format_export_value(chain.get('chain'), na)}")
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


def normalize_catalyst_framework(catalyst: dict[str, Any] | None) -> dict[str, Any]:
    if not catalyst:
        return {"is_override": False, "events": [], "base_framework_dates": []}
    return {
        "is_override": bool(catalyst.get("is_override")),
        "updated_at": catalyst.get("updated_at"),
        "source": catalyst.get("source"),
        "base_framework_dates": catalyst.get("base_framework_dates") or [],
        "events": catalyst.get("events", []),
    }


def normalize_catalyst_review(review: dict[str, Any] | None) -> dict[str, Any] | None:
    if not review:
        return None
    return {
        "review_status": review.get("review_status"),
        "review_status_zh": review.get("review_status_zh"),
        "evidence_level": review.get("evidence_level"),
        "evidence_level_zh": review.get("evidence_level_zh"),
        "supported_catalysts": review.get("supported_catalysts") or [],
        "emerging_catalysts": review.get("emerging_catalysts") or [],
        "raw_matched_keywords": review.get("raw_matched_keywords") or [],
        "active_catalyst_themes": review.get("active_catalyst_themes") or [],
        "emerging_catalyst_themes": review.get("emerging_catalyst_themes") or [],
        "weak_or_missing_evidence": review.get("weak_or_missing_evidence") or [],
        "coverage_note": review.get("coverage_note"),
        "coverage_note_zh": review.get("coverage_note_zh"),
        "one_line_review": review.get("one_line_review"),
        "one_line_review_zh": review.get("one_line_review_zh"),
        "reviewed_at": review.get("reviewed_at"),
    }


def normalize_dynamic_catalyst_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    return {
        "industry_id": snapshot.get("industry_id"),
        "framework_record_dates": snapshot.get("framework_record_dates") or [],
        "snapshot_generated_at": snapshot.get("snapshot_generated_at"),
        "review_status": snapshot.get("review_status"),
        "review_status_zh": snapshot.get("review_status_zh"),
        "evidence_level": snapshot.get("evidence_level"),
        "evidence_level_zh": snapshot.get("evidence_level_zh"),
        "active_catalysts": snapshot.get("active_catalysts") or [],
        "active_catalysts_zh": snapshot.get("active_catalysts_zh") or [],
        "active_catalyst_themes": snapshot.get("active_catalyst_themes") or [],
        "active_catalyst_themes_zh": snapshot.get("active_catalyst_themes_zh") or [],
        "emerging_catalysts": snapshot.get("emerging_catalysts") or [],
        "emerging_catalysts_zh": snapshot.get("emerging_catalysts_zh") or [],
        "emerging_catalyst_themes": snapshot.get("emerging_catalyst_themes") or [],
        "emerging_catalyst_themes_zh": snapshot.get("emerging_catalyst_themes_zh") or [],
        "cooling_catalysts": snapshot.get("cooling_catalysts") or [],
        "cooling_catalysts_zh": snapshot.get("cooling_catalysts_zh") or [],
        "coverage_note": snapshot.get("coverage_note"),
        "coverage_note_zh": snapshot.get("coverage_note_zh"),
        "one_line_snapshot": snapshot.get("one_line_snapshot"),
        "one_line_snapshot_zh": snapshot.get("one_line_snapshot_zh"),
    }


def normalize_live_news(live_news: dict[str, Any]) -> dict[str, Any]:
    items = [
        item
        for item in (live_news.get("items") or [])
        if item.get("relevance", "high") in {"high", "medium"}
    ]
    return {
        "source": live_news.get("source"),
        "source_names": live_news.get("source_names") or [],
        "source_types": live_news.get("source_types") or [],
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


def localized_value(data: dict[str, Any], key: str, lang: str) -> Any:
    """Return language-preferred value while keeping JSON context unchanged."""

    if lang == "zh":
        return data.get(f"{key}Zh") or data.get(key)
    return data.get(key) or data.get(f"{key}Zh")


def localized_review_value(data: dict[str, Any], key: str, lang: str) -> Any:
    if lang == "zh":
        return data.get(f"{key}_zh") or data.get(key)
    return data.get(key) or data.get(f"{key}_zh")


def localized_snapshot_value(data: dict[str, Any], key: str, lang: str) -> Any:
    if lang == "zh":
        if key == "review_status":
            return data.get("review_status_zh") or data.get("review_status")
        if key == "evidence_level":
            return data.get("evidence_level_zh") or data.get("evidence_level")
        return data.get(f"{key}_zh") or data.get(key)
    if key == "review_status":
        return data.get("review_status") or data.get("review_status_zh")
    if key == "evidence_level":
        return data.get("evidence_level") or data.get("evidence_level_zh")
    return data.get(key) or data.get(f"{key}_zh")


def localized_heat_level(value: Any, lang: str) -> str:
    raw = str(value or "")
    if lang == "zh":
        return HEAT_LEVEL_LABELS_ZH.get(raw, raw)
    return raw


def localized_heat_direction(value: Any, lang: str) -> str:
    raw = str(value or "")
    if lang == "zh":
        return HEAT_DIRECTION_LABELS_ZH.get(raw, raw)
    return raw


def localized_live_news_status(value: Any, lang: str) -> str:
    raw = str(value or "")
    if lang == "zh":
        return LIVE_NEWS_STATUS_LABELS_ZH.get(raw, raw)
    return raw


def localized_named_items(items: list[dict[str, Any]], lang: str) -> list[str]:
    output = []
    for item in items:
        name = localized_value(item, "name", lang)
        if name:
            output.append(str(name))
    return output


def format_drivers(drivers: list[dict[str, Any]], lang: str) -> list[str]:
    output = []
    for driver in drivers:
        name = localized_value(driver, "name", lang)
        explanation = localized_value(driver, "explanation", lang)
        if name and explanation:
            output.append(f"{name}：{explanation}" if lang == "zh" else f"{name}: {explanation}")
        elif name:
            output.append(str(name))
    return output


def format_theme_names(themes: list[dict[str, Any]] | None, lang: str) -> list[str]:
    output = []
    for theme in themes or []:
        if lang == "zh":
            name = theme.get("theme_zh") or theme.get("theme")
        else:
            name = theme.get("theme") or theme.get("theme_zh")
        if name:
            output.append(str(name))
    return output


def format_export_value(value: Any, missing: str) -> str:
    if value is None or value == "":
        return missing
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else missing
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
