"""Audit V4.15 catalyst override event semantics without network access."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_catalyst_framework_store import build_framework_override_from_snapshot  # noqa: E402
from src.industry_export import build_industry_markdown  # noqa: E402


def main() -> int:
    issues: list[str] = []
    issues.extend(audit_gold_semantics())
    issues.extend(audit_memory_stopwords())
    issues.extend(audit_liquor_semantics())
    issues.extend(audit_ai_compute_reinforced_high())
    issues.extend(audit_ai_compute_divergence())
    issues.extend(audit_markdown_raw_dict_cleanup())

    print_report("CATALYST EVENT SEMANTICS ISSUES", issues)
    return 1 if issues else 0


def audit_gold_semantics() -> list[str]:
    snapshot = {
        "review_status": "reinforced",
        "evidence_level": "high",
        "active_catalyst_themes": [
            theme("Dollar and real-yield pressure", "美元与实际利率压力"),
            theme("Central-bank gold demand support", "央行购金需求"),
            theme("Inflation and geopolitical risk", "通胀与地缘风险"),
        ],
        "emerging_catalyst_themes": [],
        "coverage_note": "Gold macro catalysts are visible, but price confirmation is still mixed.",
        "coverage_note_zh": "黄金宏观线索较明显，但价格确认仍需观察。",
    }
    override = build_framework_override_from_snapshot(
        "gold",
        {},
        snapshot,
        {"evidence_level": "high"},
        {"live_news_count_7d": 1, "items": [{"relevance": "high"}]},
    )
    events = override.get("events") or []
    issues = []
    if not events:
        issues.append("gold should generate at least one semantic event")
        return issues
    event_types = {event.get("event_type") for event in events}
    if "technology" in event_types:
        issues.append("gold should not classify macro/rates themes as technology")
    if not event_types.intersection({"macro", "rates", "central_bank_demand", "safe_haven"}):
        issues.append(f"gold event_type should identify macro/rates/central-bank/safe-haven semantics, got {sorted(event_types)}")
    if any(event.get("impact") == "positive" and event.get("confidence") == "high" for event in events):
        issues.append("gold with weak news threshold should not unconditionally become positive/high")
    return issues


def audit_memory_stopwords() -> list[str]:
    snapshot = {
        "review_status": "reinforced",
        "evidence_level": "high",
        "active_catalyst_themes": [
            theme("news", "news"),
            theme("technology", "technology"),
            theme("HBM / DRAM memory-chain reinforcement", "HBM / DRAM 存储链强化"),
            theme("AI server memory demand", "AI 服务器存储需求"),
        ],
        "emerging_catalyst_themes": [],
    }
    override = build_framework_override_from_snapshot(
        "memory",
        {},
        snapshot,
        {"evidence_level": "high"},
        {"live_news_count_7d": 4, "items": [{"relevance": "high"} for _ in range(4)]},
    )
    titles = " ".join(str(event.get("title") or "") for event in override.get("events") or [])
    titles_zh = " ".join(str(event.get("titleZh") or "") for event in override.get("events") or [])
    issues = []
    if "news validated" in titles.lower() or "news获得" in titles_zh:
        issues.append("memory stopword 'news' should not become a validated catalyst title")
    if "technology validated" in titles.lower() or "technology获得" in titles_zh:
        issues.append("memory stopword 'technology' should not become a validated catalyst title")
    if "HBM" not in titles and "HBM" not in titles_zh:
        issues.append("memory should retain HBM / DRAM after stopword filtering")
    return issues


def audit_liquor_semantics() -> list[str]:
    snapshot = {
        "review_status": "stable",
        "evidence_level": "medium",
        "active_catalyst_themes": [
            theme("news", "news"),
            theme("Baijiu consumption recovery", "白酒消费复苏"),
        ],
        "emerging_catalyst_themes": [
            theme("Channel inventory pressure", "渠道库存压力"),
            theme("Wholesale price decline", "批价下行"),
        ],
    }
    override = build_framework_override_from_snapshot(
        "liquor",
        {},
        snapshot,
        {"evidence_level": "medium"},
        {"live_news_count_7d": 2, "items": [{"relevance": "medium"} for _ in range(2)]},
    )
    events = override.get("events") or []
    issues = []
    titles = " ".join(str(event.get("title") or "") for event in events)
    titles_zh = " ".join(str(event.get("titleZh") or "") for event in events)
    event_types = {event.get("event_type") for event in events}
    impacts = {event.get("impact") for event in events}
    if "news receives" in titles.lower() or "news remains" in titles.lower() or "news获得" in titles_zh.lower():
        issues.append("liquor stopword 'news' should not become an event title")
    if "technology" in event_types:
        issues.append("liquor should not classify consumer/channel/inventory/pricing themes as technology")
    if not event_types.intersection({"consumption", "demand", "channel", "inventory", "pricing", "risk"}):
        issues.append(f"liquor should identify consumption/channel/inventory/pricing/risk semantics, got {sorted(event_types)}")
    if impacts == {"positive"}:
        issues.append("liquor mixed pressure themes should not produce all-positive events")
    return issues


def audit_ai_compute_reinforced_high() -> list[str]:
    snapshot = {
        "review_status": "reinforced",
        "evidence_level": "high",
        "active_catalyst_themes": [
            theme("AI data-center capex", "AI 数据中心资本开支"),
        ],
        "emerging_catalyst_themes": [
            theme("GPU / accelerator demand", "GPU / 加速器需求"),
            theme("AI server supply chain", "AI 服务器供应链"),
            theme("Cloud compute expansion", "云厂商算力扩张"),
        ],
        "coverage_note": "The review is based on 8 high-relevance news items.",
        "coverage_note_zh": "当前基于 8 条高相关新闻进行复核。",
    }
    override = build_framework_override_from_snapshot(
        "ai_compute",
        {},
        snapshot,
        {"evidence_level": "high"},
        {"live_news_count_7d": 8, "items": [{"relevance": "high"} for _ in range(8)]},
    )
    events = override.get("events") or []
    issues = []
    text = " ".join(
        str(event.get(key) or "")
        for event in events
        for key in ("title", "titleZh", "description", "descriptionZh")
    ).lower()
    if not events:
        issues.append("ai_compute reinforced/high should generate active support event")
        return issues
    if any(event.get("confidence") == "low" for event in events):
        issues.append("ai_compute reinforced/high should not generate low confidence event")
    if "diverge" in text or "diverging" in text or "分化" in text or "待验证" in text:
        issues.append("ai_compute reinforced/high should not generate divergence or validation-pending main event")
    if not any(event.get("event_type") == "capex" for event in events):
        issues.append("ai_compute reinforced/high should classify AI data-center capex as capex")
    if not any(event.get("confidence") in {"medium", "high"} for event in events):
        issues.append("ai_compute reinforced/high should produce at least medium confidence")
    return issues


def audit_ai_compute_divergence() -> list[str]:
    snapshot = {
        "review_status": "diverging",
        "evidence_level": "low",
        "active_catalyst_themes": [],
        "emerging_catalyst_themes": [
            theme("AI data-center capex", "AI 数据中心资本开支"),
            theme("GPU / accelerator demand", "GPU / 加速器需求"),
        ],
        "emerging_catalysts": ["AI data-center capex", "GPU / accelerator demand"],
        "emerging_catalysts_zh": ["AI 数据中心资本开支", "GPU / 加速器需求"],
    }
    override = build_framework_override_from_snapshot(
        "ai_compute",
        {},
        snapshot,
        {"evidence_level": "low"},
        {"live_news_count_7d": 1, "items": [{"relevance": "medium"}]},
    )
    events = override.get("events") or []
    issues = []
    text = " ".join(str(event.get("title") or "") for event in events)
    if "strongly validates" in text:
        issues.append("diverging / low evidence should not generate strong validation")
    if any(event.get("impact") == "positive" and event.get("confidence") == "high" for event in events):
        issues.append("diverging / low evidence should not generate positive/high")
    if not any(event.get("impact") == "mixed" and event.get("confidence") == "low" for event in events):
        issues.append("diverging / low evidence should generate mixed/low watch-style event")
    return issues


def audit_markdown_raw_dict_cleanup() -> list[str]:
    context = minimal_export_context()
    markdown = build_industry_markdown(context, "en")
    issues = []
    if "effective framework events:" in markdown.lower():
        issues.append("markdown should not contain effective framework events raw field")
    if "{'date'" in markdown or "'event_type'" in markdown:
        issues.append("markdown should not contain Python dict-style event output")
    return issues


def theme(en: str, zh: str) -> dict[str, str]:
    return {"theme": en, "theme_zh": zh, "matched_terms": [en], "reason": "audit", "reason_zh": "audit"}


def minimal_export_context() -> dict[str, Any]:
    event = {
        "date": "2026-06-10",
        "title": "Audit event",
        "titleZh": "审计事件",
        "event_type": "macro",
        "event_typeZh": "宏观",
        "impact": "mixed",
        "impactZh": "混合",
        "confidence": "medium",
        "confidenceZh": "中",
        "description": "Audit description",
        "descriptionZh": "审计说明",
    }
    return {
        "industry_id": "audit",
        "industry_name": "Audit",
        "chinese_name": "审计",
        "display_category": "Audit",
        "trend_summary": "Audit summary",
        "overall_view": {
            "overall_status": "Diverging",
            "trend_stage": "Diverging",
            "price_confirmation": "N/A",
            "news_heat": "N/A",
            "priced_in_risk": "N/A",
            "key_tags": [],
            "one_line_view": "Audit",
        },
        "framework_scores": {},
        "market_confirmation": {},
        "catalysts": {
            "heat_score": 1,
            "heat_level": "Low",
            "heat_direction": "Mixed",
            "summary": "Audit catalyst",
            "summaryZh": "审计催化",
            "events": [event],
        },
        "catalyst_framework": {
            "is_override": True,
            "updated_at": "2026-06-10T00:00:00",
            "base_framework_dates": ["2026-05-27"],
            "events": [event],
        },
        "catalyst_review": {},
        "dynamic_catalyst_snapshot": {},
        "live_news": {
            "source_names": [],
            "source_types": [],
            "low_relevance_count": 0,
            "live_news_count_7d": 0,
            "live_news_status": "no_recent_news",
            "latest_news_time": "",
            "items": [],
        },
        "industry_chain": {"drivers": [], "subsectors": [], "risk_signals": [], "chain": {}},
    }


def print_report(title: str, payload: object) -> None:
    print(f"\n## {title}")
    if not payload:
        print("None")
        return
    if isinstance(payload, list):
        for item in payload:
            print(f"- {item}")
        return
    print(payload)


if __name__ == "__main__":
    raise SystemExit(main())
