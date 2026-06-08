"""Rule-based catalyst theme normalization.

This module maps raw news keywords into readable catalyst themes. It is fully
local and deterministic; it does not call AI services or external APIs.
"""

from __future__ import annotations

from typing import Any

from src.industry_news_config import get_industry_news_config


BROAD_FALLBACK_TERMS = {
    "chip",
    "chips",
    "technology",
    "infrastructure",
    "market",
    "stock",
    "company",
    "sector",
    "semiconductor",
}

THEME_MAPPINGS: dict[str, list[dict[str, Any]]] = {
    "semiconductor": [
        {
            "theme": "AI chip-chain diffusion",
            "theme_zh": "AI 芯片链条扩散",
            "terms": ["AI chip", "Nvidia", "Broadcom", "Marvell", "GPU", "ASIC", "chip", "chips"],
            "reason": "News terms point to AI accelerator and chip supplier-chain diffusion.",
            "reason_zh": "新闻线索指向 AI 加速器与芯片供应链扩散。",
        },
        {
            "theme": "HBM / DRAM memory-chain reinforcement",
            "theme_zh": "HBM / DRAM 存储链强化",
            "terms": ["HBM", "DRAM", "Micron", "SK Hynix", "memory", "AI memory"],
            "reason": "News terms point to memory supply-chain validation around HBM, DRAM, and AI memory.",
            "reason_zh": "新闻线索指向 HBM、DRAM 与 AI memory 相关的存储供应链验证。",
        },
        {
            "theme": "Advanced packaging and high-end compute supply constraints",
            "theme_zh": "先进封装与高端算力供给约束",
            "terms": ["advanced packaging", "packaging", "TSMC", "CoWoS", "foundry"],
            "reason": "News terms point to advanced packaging, foundry, and high-end compute capacity constraints.",
            "reason_zh": "新闻线索指向先进封装、晶圆代工与高端算力产能约束。",
        },
        {
            "theme": "AI data-center infrastructure demand",
            "theme_zh": "AI 数据中心基础设施需求",
            "terms": ["AI infrastructure", "data center", "AI data center", "infrastructure"],
            "reason": "News terms point to AI data-center buildout and related infrastructure demand.",
            "reason_zh": "新闻线索指向 AI 数据中心建设和相关基础设施需求。",
        },
    ],
    "cpo_optical_module": [
        {
            "theme": "CPO technology-route validation",
            "theme_zh": "CPO 技术路线验证",
            "terms": ["CPO", "co-packaged optics", "Nvidia CPO", "data center switch"],
            "reason": "News terms point to validation of the co-packaged optics technology path.",
            "reason_zh": "新闻线索指向 CPO 共封装光学技术路线验证。",
        },
        {
            "theme": "Silicon photonics route progress",
            "theme_zh": "硅光路线推进",
            "terms": ["silicon photonics", "硅光"],
            "reason": "News terms point to silicon photonics progress in the optical interconnect chain.",
            "reason_zh": "新闻线索指向光互联链条中的硅光路线推进。",
        },
        {
            "theme": "High-speed optical-module upgrade cycle",
            "theme_zh": "高速光模块升级周期",
            "terms": ["optical module", "800G", "1.6T", "bandwidth"],
            "reason": "News terms point to high-speed optical-module upgrades and bandwidth demand.",
            "reason_zh": "新闻线索指向高速光模块升级和带宽需求。",
        },
    ],
    "gold": [
        {
            "theme": "Dollar and real-yield pressure",
            "theme_zh": "美元与实际利率压力",
            "terms": ["dollar", "treasury yields", "real yields", "real yield", "U.S. yields"],
            "reason": "News terms point to the impact of the dollar and real yields on gold pricing.",
            "reason_zh": "新闻线索指向美元和实际利率对黄金定价的影响。",
        },
        {
            "theme": "Central-bank gold demand support",
            "theme_zh": "央行购金支撑",
            "terms": ["central bank buying", "central banks", "央行购金"],
            "reason": "News terms point to central-bank gold demand as a support factor.",
            "reason_zh": "新闻线索指向央行购金需求对黄金形成支撑。",
        },
        {
            "theme": "Inflation and geopolitical risk",
            "theme_zh": "通胀与地缘风险",
            "terms": ["inflation", "geopolitical", "war", "oil"],
            "reason": "News terms point to inflation or geopolitical risk as gold-related catalysts.",
            "reason_zh": "新闻线索指向通胀或地缘风险相关催化。",
        },
    ],
}


def normalize_catalyst_themes(
    industry_id: str,
    keywords: list[Any] | set[Any] | tuple[Any, ...],
    language: str = "zh",
) -> list[dict[str, Any]]:
    """Map raw keywords to readable catalyst themes."""

    raw_terms = unique_keep_order([str(item).strip() for item in keywords if str(item).strip()])
    if not raw_terms:
        return []
    output = []
    for mapping in configured_theme_mappings(industry_id):
        matched = matched_theme_terms(raw_terms, mapping.get("terms", []))
        if matched:
            output.append(
                {
                    "theme": mapping["theme"],
                    "theme_zh": mapping["theme_zh"],
                    "matched_terms": matched,
                    "reason": mapping["reason"],
                    "reason_zh": mapping["reason_zh"],
                }
            )
    if output:
        return output
    for mapping in THEME_MAPPINGS.get(industry_id, []):
        matched = matched_theme_terms(raw_terms, mapping.get("terms", []))
        if matched:
            output.append(
                {
                    "theme": mapping["theme"],
                    "theme_zh": mapping["theme_zh"],
                    "matched_terms": matched,
                    "reason": mapping["reason"],
                    "reason_zh": mapping["reason_zh"],
                }
            )
    if output:
        return output
    fallback = [
        term
        for term in raw_terms
        if term.lower() not in BROAD_FALLBACK_TERMS and len(term) >= 3
    ][:6]
    return [
        {
            "theme": term,
            "theme_zh": term,
            "matched_terms": [term],
            "reason": "Specific unmatched catalyst term retained for review.",
            "reason_zh": "保留较具体但尚未归并的催化线索，供后续复核。",
        }
        for term in fallback
    ]


def configured_theme_mappings(industry_id: str) -> list[dict[str, Any]]:
    """Build theme mappings from the optional V4.14 news config layer."""

    theme_keywords = get_industry_news_config(industry_id).get("theme_keywords", {})
    if not isinstance(theme_keywords, dict):
        return []
    mappings = []
    for theme_name, terms in theme_keywords.items():
        if not isinstance(terms, list):
            continue
        clean_terms = unique_keep_order([str(term).strip() for term in terms if str(term).strip()])
        if not clean_terms:
            continue
        mappings.append(
            {
                "theme": str(theme_name),
                "theme_zh": str(theme_name),
                "terms": clean_terms,
                "reason": "Configured news terms match this catalyst theme.",
                "reason_zh": "配置层新闻关键词命中该催化主题。",
            }
        )
    return mappings


def theme_display_name(theme: dict[str, Any], language: str = "zh") -> str:
    if language == "zh":
        return str(theme.get("theme_zh") or theme.get("theme") or "")
    return str(theme.get("theme") or theme.get("theme_zh") or "")


def theme_reason(theme: dict[str, Any], language: str = "zh") -> str:
    if language == "zh":
        return str(theme.get("reason_zh") or theme.get("reason") or "")
    return str(theme.get("reason") or theme.get("reason_zh") or "")


def matched_theme_terms(raw_terms: list[str], mapping_terms: list[str]) -> list[str]:
    matched = []
    lowered_raw = [(term, term.lower()) for term in raw_terms]
    for mapping_term in mapping_terms:
        lower_mapping = str(mapping_term).lower()
        for original, lower_original in lowered_raw:
            if lower_mapping in lower_original or lower_original in lower_mapping:
                matched.append(original)
    return unique_keep_order(matched)


def unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
