"""Read-only audit for all-industry V4.15 catalyst event semantics."""

from __future__ import annotations

import json
import sys
import types
from collections import Counter
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_catalyst_framework_store import clean_catalyst_names, get_effective_catalyst_framework  # noqa: E402
from src.industry_export import build_industry_markdown  # noqa: E402
from src.industry_trend_data import industryTrendData  # noqa: E402


FRAMEWORK_OVERRIDES_PATH = ROOT / "data" / "industry_catalyst" / "framework_overrides.json"
LATEST_SNAPSHOT_PATH = ROOT / "data" / "industry_catalyst" / "latest_catalyst_snapshot.json"

TECH_OK_INDUSTRIES = {
    "semiconductor",
    "memory",
    "cpo_optical_module",
    "ai_compute",
    "cpu",
    "cloud_computing",
    "data_center",
    "cybersecurity",
    "consumer_electronics",
    "robotics",
    "sic",
    "power_equipment",
    "industrial_automation",
    "medical_devices",
    "biotechnology",
    "ai_healthcare",
}

NON_TECH_INDUSTRIES = {
    "gold",
    "copper",
    "aluminum",
    "lithium",
    "rare_earth",
    "oil",
    "natural_gas",
    "coal",
    "liquor",
    "food_beverage",
    "tourism",
    "hotel",
    "aviation",
    "gaming",
    "e_commerce",
    "banking",
    "insurance",
    "brokerage",
    "real_estate",
    "reits",
    "chemicals",
    "cement",
    "shipping",
    "ports",
    "logistics",
}

STOPWORD_TERMS = {
    "news",
    "technology",
    "market",
    "stock",
    "stocks",
    "shares",
    "company",
    "companies",
    "industry",
    "sector",
    "report",
    "analysis",
    "analyst",
    "data",
    "provides",
    "include",
    "active",
    "catalyst",
    "themes",
    "emerging",
    "latest",
    "update",
    "business",
    "finance",
    "新闻",
    "技术",
    "市场",
    "股票",
    "公司",
    "行业",
    "板块",
    "报告",
    "分析",
    "主题",
    "催化",
    "线索",
    "更新",
}

STRONG_VALIDATION_TERMS = {
    "strongly validates",
    "较强验证",
    "å½¢æˆè¾ƒå¼ºéªŒè¯",
}

DIVERGENCE_TERMS = {
    "diverge",
    "diverging",
    "validation",
    "待验证",
    "分化",
    "å¾…éªŒè¯",
    "åˆ†åŒ–",
}


def main() -> int:
    overrides = load_json(FRAMEWORK_OVERRIDES_PATH)
    snapshots = load_json(LATEST_SNAPSHOT_PATH).get("industries", {})
    rows = [audit_industry(industry, overrides, snapshots) for industry in industryTrendData]
    summary = Counter(row["issue_level"] for row in rows)
    fail_rows = [row for row in rows if row["issue_level"] == "fail"]
    warning_rows = [row for row in rows if row["issue_level"] == "warning"]
    old_template_rows = [row for row in rows if row["old_override_issue"]]

    print_report(
        "ALL INDUSTRY CATALYST SEMANTICS SUMMARY",
        {
            "total_industries": len(rows),
            "pass": summary.get("pass", 0),
            "warning": summary.get("warning", 0),
            "fail": summary.get("fail", 0),
            "old_template_override_count": len(old_template_rows),
        },
    )
    print_report("FAIL INDUSTRIES", compact_rows(fail_rows))
    print_report("WARNING INDUSTRIES", compact_rows(warning_rows))
    print_report("OLD TEMPLATE OVERRIDE INDUSTRIES", compact_rows(old_template_rows))
    print_report("ALL INDUSTRY CATALYST SEMANTICS ROWS", rows)
    return 1 if fail_rows else 0


def audit_industry(industry: dict[str, Any], overrides: dict[str, Any], snapshots: dict[str, Any]) -> dict[str, Any]:
    industry_id = str(industry.get("id") or "")
    snapshot = snapshots.get(industry_id) if isinstance(snapshots, dict) else {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    framework = get_effective_catalyst_framework(industry_id) or {}
    override = overrides.get(industry_id) if isinstance(overrides, dict) else None
    events = [event for event in framework.get("events", []) or [] if isinstance(event, dict)]
    themes = collect_theme_names(snapshot)
    if industry_id == "liquor":
        themes = clean_catalyst_names(themes)
    notes: list[str] = []

    event_type_issue = detect_event_type_issue(industry_id, events, notes)
    impact_issue = detect_impact_issue(events, notes)
    confidence_issue = detect_confidence_issue(events, notes)
    stopword_theme_issue = detect_stopword_theme_issue(themes, notes)
    status_consistency_issue = detect_status_consistency_issue(snapshot, events, notes)
    old_override_issue = detect_old_override_issue(override, events, notes)
    markdown_export_issue = detect_markdown_export_issue(industry, framework, snapshot, notes)

    hard_fail = status_consistency_issue or markdown_export_issue
    warning = (
        event_type_issue
        or impact_issue
        or confidence_issue
        or stopword_theme_issue
        or old_override_issue
    )
    issue_level = "fail" if hard_fail else "warning" if warning else "pass"

    return {
        "industry_id": industry_id,
        "industry_name_zh": industry.get("chineseName") or "",
        "issue_level": issue_level,
        "event_type_issue": event_type_issue,
        "impact_issue": impact_issue,
        "confidence_issue": confidence_issue,
        "stopword_theme_issue": stopword_theme_issue,
        "status_consistency_issue": status_consistency_issue,
        "old_override_issue": old_override_issue,
        "markdown_export_issue": markdown_export_issue,
        "notes": notes,
    }


def detect_event_type_issue(industry_id: str, events: list[dict[str, Any]], notes: list[str]) -> bool:
    if not events:
        return False
    types = [str(event.get("event_type") or "") for event in events]
    all_technology = bool(types) and all(item == "technology" for item in types)
    if all_technology and industry_id not in TECH_OK_INDUSTRIES:
        notes.append("all events are technology for a non-technology industry")
        return True
    if industry_id in NON_TECH_INDUSTRIES and "technology" in types:
        notes.append("non-technology industry contains technology event_type")
        return True
    return False


def detect_impact_issue(events: list[dict[str, Any]], notes: list[str]) -> bool:
    if not events:
        return False
    impacts = [str(event.get("impact") or "") for event in events]
    if len(events) >= 2 and all(item == "positive" for item in impacts):
        notes.append("all override events are positive")
        return True
    return False


def detect_confidence_issue(events: list[dict[str, Any]], notes: list[str]) -> bool:
    if not events:
        return False
    confidences = [str(event.get("confidence") or "") for event in events]
    if len(events) >= 2 and all(item == "high" for item in confidences):
        notes.append("all override events are high confidence")
        return True
    return False


def detect_stopword_theme_issue(themes: list[str], notes: list[str]) -> bool:
    bad = [theme for theme in themes if normalized_term(theme) in STOPWORD_TERMS]
    if bad:
        notes.append(f"generic catalyst theme terms remain: {bad}")
        return True
    return False


def detect_status_consistency_issue(snapshot: dict[str, Any], events: list[dict[str, Any]], notes: list[str]) -> bool:
    if not snapshot or not events:
        return False
    status = str(snapshot.get("review_status") or "")
    evidence = str(snapshot.get("evidence_level") or "")
    has_active = bool(snapshot.get("active_catalyst_themes") or snapshot.get("active_catalysts"))
    event_text = " ".join(
        str(event.get(key) or "")
        for event in events
        for key in ("title", "titleZh", "description", "descriptionZh")
    ).lower()
    has_strong_positive_high = any(
        event.get("impact") == "positive" and event.get("confidence") == "high"
        for event in events
    ) or any(term in event_text for term in STRONG_VALIDATION_TERMS)
    has_divergence_low = (
        any(event.get("confidence") == "low" for event in events)
        and any(term in event_text for term in DIVERGENCE_TERMS)
    )

    if status in {"diverging", "weakening", "insufficient_evidence"} and has_strong_positive_high:
        notes.append(f"snapshot status={status} but events still contain strong positive/high validation")
        return True
    if evidence == "low" and has_strong_positive_high:
        notes.append("snapshot evidence=low but events still contain strong positive/high validation")
        return True
    if status == "reinforced" and evidence == "high" and has_active and has_divergence_low:
        notes.append("snapshot reinforced/high with active themes but events contain divergence/low-confidence conclusion")
        return True
    return False


def detect_old_override_issue(override: Any, events: list[dict[str, Any]], notes: list[str]) -> bool:
    if not isinstance(override, dict) or not events:
        return False
    if len(events) < 2:
        return False
    template_like = all(
        event.get("event_type") == "technology"
        and event.get("impact") == "positive"
        and event.get("confidence") == "high"
        for event in events
    )
    if template_like:
        notes.append("existing override still looks like technology/positive/high template output")
        return True
    return False


def detect_markdown_export_issue(
    industry: dict[str, Any],
    framework: dict[str, Any],
    snapshot: dict[str, Any],
    notes: list[str],
) -> bool:
    context = minimal_export_context(industry, framework, snapshot)
    try:
        markdown = build_industry_markdown(context, "en")
    except Exception as exc:
        notes.append(f"markdown export failed during audit: {exc}")
        return True
    lowered = markdown.lower()
    if "effective framework events:" in lowered or "{'date'" in markdown or "'event_type'" in markdown:
        notes.append("markdown export contains raw effective framework events dict")
        return True
    return False


def collect_theme_names(snapshot: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in (
        "active_catalysts",
        "active_catalysts_zh",
        "emerging_catalysts",
        "emerging_catalysts_zh",
    ):
        for item in snapshot.get(key) or []:
            names.append(str(item))
    for key in (
        "active_catalyst_themes",
        "active_catalyst_themes_zh",
        "emerging_catalyst_themes",
        "emerging_catalyst_themes_zh",
    ):
        for item in snapshot.get(key) or []:
            if isinstance(item, dict):
                names.append(str(item.get("theme") or ""))
                names.append(str(item.get("theme_zh") or ""))
            else:
                names.append(str(item))
    return [name for name in names if name]


def minimal_export_context(industry: dict[str, Any], framework: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    events = framework.get("events") or []
    return {
        "industry_id": industry.get("id"),
        "industry_name": industry.get("name"),
        "chinese_name": industry.get("chineseName"),
        "display_category": industry.get("category"),
        "trend_summary": industry.get("summary") or "",
        "overall_view": {
            "overall_status": industry.get("status") or "",
            "trend_stage": industry.get("trendStage") or "",
            "price_confirmation": "N/A",
            "news_heat": "N/A",
            "priced_in_risk": "N/A",
            "key_tags": [],
            "one_line_view": "audit",
        },
        "framework_scores": {},
        "market_confirmation": {},
        "catalysts": {
            "heat_score": framework.get("heat_score"),
            "heat_level": framework.get("heat_level"),
            "heat_direction": framework.get("heat_direction"),
            "summary": framework.get("summary"),
            "summaryZh": framework.get("summaryZh"),
            "events": events,
        },
        "catalyst_framework": {
            "is_override": bool(framework.get("is_override")),
            "updated_at": framework.get("updated_at"),
            "base_framework_dates": framework.get("base_framework_dates") or [],
            "events": events,
        },
        "catalyst_review": {
            "review_status": snapshot.get("review_status"),
            "evidence_level": snapshot.get("evidence_level"),
            "active_catalyst_themes": snapshot.get("active_catalyst_themes") or [],
            "emerging_catalyst_themes": snapshot.get("emerging_catalyst_themes") or [],
        },
        "dynamic_catalyst_snapshot": snapshot,
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


def compact_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "industry_id": row["industry_id"],
            "industry_name_zh": row["industry_name_zh"],
            "issue_level": row["issue_level"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def normalized_term(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def print_report(title: str, payload: object) -> None:
    print(f"\n## {title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
