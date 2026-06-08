"""V4.10 catalyst review layer.

This module reviews local V4.1 catalyst framework data against cached V4.2
high-relevance live-news observations. It does not fetch news, call external
AI services, or rewrite the local catalyst framework.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.industry_catalyst_themes import normalize_catalyst_themes


REVIEW_STATUSES = {"reinforced", "stable", "diverging", "weakening", "insufficient_evidence"}
EVIDENCE_LEVELS = {"high", "medium", "low", "insufficient"}

STATUS_LABELS_ZH = {
    "reinforced": "强化",
    "stable": "稳定",
    "diverging": "分化",
    "weakening": "减弱",
    "insufficient_evidence": "证据不足",
}

EVIDENCE_LABELS_ZH = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "insufficient": "不足",
}

FALLBACK_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "framework",
    "local",
    "data",
    "event",
    "events",
    "are",
    "expectations",
    "remains",
    "related",
    "cycle",
    "demand",
    "focus",
    "focuses",
    "主要",
    "关注",
    "框架",
    "线索",
    "观察",
}

INDUSTRY_REVIEW_KEYWORDS = {
    "semiconductor": [
        "AI data center",
        "capex",
        "HBM",
        "advanced packaging",
        "Nvidia",
        "Micron",
        "TSMC",
        "GPU",
        "chip",
        "semiconductor",
    ],
    "cpo_optical_module": [
        "800G",
        "1.6T",
        "optical module",
        "CPO",
        "co-packaged optics",
        "silicon photonics",
        "Nvidia CPO",
        "data center switch",
        "data center",
        "bandwidth",
        "光模块",
        "硅光",
    ],
    "gold": [
        "real yield",
        "central bank",
        "dollar",
        "inflation",
        "treasury",
        "geopolitical",
        "gold",
        "黄金",
        "央行购金",
        "实际利率",
        "美元",
    ],
    "liquor": [
        "baijiu",
        "liquor",
        "consumption",
        "channel inventory",
        "wholesale price",
        "premium",
        "白酒",
        "批价",
        "渠道库存",
        "高端酒",
        "宴席",
        "商务消费",
    ],
    "real_estate": [
        "real estate",
        "REIT",
        "REITs",
        "property",
        "commercial property",
        "rent",
        "vacancy",
        "mortgage",
        "interest rate",
        "房地产",
        "地产",
        "租金",
        "空置率",
    ],
}


def build_catalyst_review(
    industry_id: str,
    catalyst_data: dict[str, Any] | None,
    live_news_data: dict[str, Any] | None,
    language: str = "zh",
) -> dict[str, Any]:
    """Build a deterministic review of V4.1 catalysts using cached V4.2 news."""

    catalyst_data = catalyst_data or {}
    live_news_data = live_news_data or {}
    keywords = build_review_keywords(industry_id, catalyst_data)
    news_items = [
        item
        for item in live_news_data.get("items", []) or []
        if item.get("relevance", "high") in {"high", "medium"}
    ]
    live_count = int(live_news_data.get("live_news_count_7d") or len(news_items) or 0)
    matched_keywords = collect_news_matches(news_items, keywords)
    supported = supported_catalysts_for(industry_id, matched_keywords, language)
    emerging = collect_emerging_keywords(news_items, keywords)
    active_themes = normalize_catalyst_themes(industry_id, matched_keywords, language)
    emerging_themes = normalize_catalyst_themes(industry_id, emerging, language)
    heat_score = to_float(catalyst_data.get("heat_score"))
    heat_direction = str(catalyst_data.get("heat_direction") or "")
    negative_count = sum(1 for item in news_items if str(item.get("impact", "")).lower() == "negative")

    if heat_direction.lower() == "falling" and (live_count <= 1 or negative_count > 0):
        status = "weakening"
    elif live_count >= 5 and supported:
        status = "reinforced"
    elif 1 <= live_count <= 4 and supported:
        status = "stable"
    elif heat_score is not None and heat_score >= 7.0 and live_count == 0:
        status = "insufficient_evidence"
    elif live_count > 0 and not supported:
        status = "diverging"
    elif live_count == 0:
        status = "insufficient_evidence"
    else:
        status = "stable"

    evidence = evidence_level(live_count, bool(supported))
    weak_or_missing = build_weak_or_missing(status, keywords, supported, language)
    coverage_note = coverage_note_for(status, live_count, language="en")
    coverage_note_zh = coverage_note_for(status, live_count, language="zh")
    one_line = one_line_for(status, live_count, supported, language="en", industry_id=industry_id)
    one_line_zh = one_line_for(status, live_count, supported, language="zh", industry_id=industry_id)

    return {
        "review_status": status,
        "review_status_zh": STATUS_LABELS_ZH[status],
        "evidence_level": evidence,
        "evidence_level_zh": EVIDENCE_LABELS_ZH[evidence],
        "supported_catalysts": supported,
        "emerging_catalysts": emerging,
        "raw_matched_keywords": sorted(matched_keywords),
        "active_catalyst_themes": active_themes,
        "emerging_catalyst_themes": emerging_themes,
        "weak_or_missing_evidence": weak_or_missing,
        "coverage_note": coverage_note,
        "coverage_note_zh": coverage_note_zh,
        "one_line_review": one_line,
        "one_line_review_zh": one_line_zh,
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
    }


def build_review_keywords(industry_id: str, catalyst_data: dict[str, Any]) -> list[str]:
    """Return dedicated review keywords, falling back to catalyst framework text."""

    dedicated = INDUSTRY_REVIEW_KEYWORDS.get(industry_id, [])
    fallback_parts = [
        str(catalyst_data.get("summary", "")),
        str(catalyst_data.get("summaryZh", "")),
    ]
    for event in catalyst_data.get("events", []) or []:
        fallback_parts.extend(
            [
                str(event.get("title", "")),
                str(event.get("titleZh", "")),
                str(event.get("event_type", "")),
                str(event.get("event_typeZh", "")),
            ]
        )
    fallback = split_keyword_text(" ".join(fallback_parts))
    return unique_keep_order([*dedicated, *fallback])


def collect_news_matches(news_items: list[dict[str, Any]], keywords: list[str]) -> set[str]:
    """Collect review keywords found in news titles or matched keyword fields."""

    output: set[str] = set()
    lower_keywords = [(keyword, keyword.lower()) for keyword in keywords if keyword]
    for item in news_items:
        title = str(item.get("title", "")).lower()
        matched = {str(value).lower() for value in item.get("matched_keywords", []) or []}
        for original, lower_keyword in lower_keywords:
            if lower_keyword in title or lower_keyword in matched:
                output.add(original)
    return output


def supported_catalysts_for(industry_id: str, matched_keywords: set[str], language: str) -> list[str]:
    """Map matched keywords to local catalyst clues when a theme needs explicit grouping."""

    if not matched_keywords:
        return []
    matched_lower = {keyword.lower() for keyword in matched_keywords}
    if industry_id == "cpo_optical_module":
        core_terms = {
            "cpo",
            "co-packaged optics",
            "optical module",
            "silicon photonics",
            "nvidia cpo",
            "data center switch",
            "800g",
            "1.6t",
            "bandwidth",
        }
        if matched_lower & core_terms:
            label = (
                "CPO / 光模块：技术路线验证仍是重要线索"
                if language == "zh"
                else "CPO / Optical Module: Technology route validation remains important"
            )
            return [label]
    return sorted(matched_keywords)


def collect_emerging_keywords(news_items: list[dict[str, Any]], review_keywords: list[str]) -> list[str]:
    """Return matched news keywords that are not part of the current catalyst keyword set."""

    review_lower = {keyword.lower() for keyword in review_keywords}
    emerging = []
    for item in news_items:
        for keyword in item.get("matched_keywords", []) or []:
            text = str(keyword)
            if text and text.lower() not in review_lower:
                emerging.append(text)
    return sorted(unique_keep_order(emerging))[:8]


def evidence_level(live_count: int, has_supported: bool) -> str:
    if live_count >= 5 and has_supported:
        return "high"
    if live_count >= 1 and has_supported:
        return "medium"
    if live_count > 0:
        return "low"
    return "insufficient"


def build_weak_or_missing(status: str, keywords: list[str], supported: list[str], language: str) -> list[str]:
    if status not in {"diverging", "insufficient_evidence", "weakening"}:
        return []
    missing = [keyword for keyword in keywords if keyword not in set(supported)]
    if missing:
        return missing[:8]
    if language == "zh":
        return ["当前新闻证据不足以覆盖主要催化线索"]
    return ["Current news evidence does not sufficiently cover the main catalyst clues"]


def coverage_note_for(status: str, live_count: int, language: str) -> str:
    if language == "zh":
        if status == "insufficient_evidence":
            return "当前新闻源未提供足够高相关实时证据，不代表本地催化框架失效。"
        if status == "diverging":
            return "当前新闻存在高相关内容，但与本地催化框架关键词匹配较弱。"
        if status == "weakening":
            return "当前新闻证据偏少或方向降温，需要继续观察后续覆盖情况。"
        return f"当前基于 {live_count} 条高相关新闻进行复核。"
    if status == "insufficient_evidence":
        return "The current news source does not provide enough high-relevance live evidence. This does not mean the local catalyst framework is invalid."
    if status == "diverging":
        return "High-relevance news exists, but keyword alignment with the local catalyst framework is weak."
    if status == "weakening":
        return "News evidence is limited or cooling, so later coverage should be monitored."
    return f"The review is based on {live_count} high-relevance news items."


def one_line_for(status: str, live_count: int, supported: list[str], language: str, industry_id: str = "") -> str:
    if language == "zh":
        if status == "stable" and industry_id == "cpo_optical_module":
            return "当前实时新闻对 CPO 技术路线验证形成一定支持，但新闻数量仍有限。"
        if status == "reinforced":
            return f"实时新闻与本地催化框架形成较强呼应，已匹配 {len(supported)} 条催化关键词。"
        if status == "stable":
            return "实时新闻对部分本地催化线索形成支持，框架暂时保持稳定。"
        if status == "diverging":
            return "实时新闻有覆盖，但主题与本地催化框架的匹配度偏弱。"
        if status == "weakening":
            return "新闻证据偏少或方向降温，催化线索需要后续复核。"
        return "当前高相关新闻证据不足，无法对本地催化框架形成有效复核。"
    if status == "stable" and industry_id == "cpo_optical_module":
        return "Live news provides some support for CPO technology-route validation, while the number of news items remains limited."
    if status == "reinforced":
        return f"Live news aligns strongly with the local catalyst framework, matching {len(supported)} catalyst keywords."
    if status == "stable":
        return "Live news supports part of the local catalyst clues, keeping the framework stable for now."
    if status == "diverging":
        return "Live news is available, but topic alignment with the local catalyst framework is weak."
    if status == "weakening":
        return "News evidence is limited or cooling, so catalyst clues need later review."
    return "High-relevance live-news evidence is insufficient for an effective catalyst review."


def split_keyword_text(text: str) -> list[str]:
    tokens = []
    for raw in text.replace("/", " ").replace(",", " ").replace("，", " ").split():
        cleaned = raw.strip(" .:;()[]{}")
        if len(cleaned) >= 3 and cleaned.lower() not in FALLBACK_STOPWORDS:
            tokens.append(cleaned)
    return tokens[:40]


def unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
