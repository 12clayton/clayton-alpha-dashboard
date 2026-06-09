"""Updatable V4.1 catalyst framework store.

This module keeps the source V4.1 catalyst data immutable and applies local
overrides from data/industry_catalyst/framework_overrides.json when present.
Overrides are only written by explicit user action.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.industry_catalyst_data import get_catalyst_data
from src.industry_catalyst_themes import theme_display_name


CATALYST_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "industry_catalyst"
FRAMEWORK_OVERRIDES_PATH = CATALYST_STORE_DIR / "framework_overrides.json"
LATEST_CATALYST_SNAPSHOT_PATH = CATALYST_STORE_DIR / "latest_catalyst_snapshot.json"

FRAMEWORK_REQUIRED_FIELDS = [
    "heat_score",
    "heat_level",
    "heat_direction",
    "summary",
    "summaryZh",
    "events",
    "is_override",
    "updated_at",
    "base_framework_dates",
]

INVALID_CATALYST_THEME_TERMS = {
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

EVENT_TYPE_ZH = {
    "macro": "宏观",
    "rates": "利率",
    "monetary_policy": "货币政策",
    "safe_haven": "避险",
    "central_bank_demand": "央行需求",
    "capex": "资本开支",
    "demand": "需求",
    "consumption": "消费",
    "channel": "渠道",
    "inventory": "库存",
    "pricing": "价格",
    "supply_chain": "供应链",
    "product": "产品",
    "technology": "技术",
    "price_cycle": "价格周期",
    "policy": "政策",
    "risk": "风险",
    "mixed": "混合",
}

IMPACT_ZH = {
    "positive": "正面",
    "neutral": "中性",
    "negative": "负面",
    "mixed": "混合",
}

CONFIDENCE_ZH = {"high": "高", "medium": "中", "low": "低"}


def ensure_framework_store() -> Path:
    """Create the local catalyst framework override file if needed."""

    CATALYST_STORE_DIR.mkdir(parents=True, exist_ok=True)
    if not FRAMEWORK_OVERRIDES_PATH.exists():
        FRAMEWORK_OVERRIDES_PATH.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
    return FRAMEWORK_OVERRIDES_PATH


def load_framework_overrides() -> dict[str, Any]:
    """Read local framework overrides without failing the page."""

    ensure_framework_store()
    try:
        payload = json.loads(FRAMEWORK_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_framework_overrides(overrides: dict[str, Any]) -> None:
    """Persist framework overrides."""

    ensure_framework_store()
    FRAMEWORK_OVERRIDES_PATH.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")


def get_base_catalyst_framework(industry_id: str) -> dict[str, Any] | None:
    """Return a copy of the base V4.1 catalyst framework."""

    base = get_catalyst_data(industry_id)
    if not base:
        return None
    output = copy.deepcopy(base)
    output["is_override"] = False
    output["updated_at"] = ""
    output["source"] = "V4.1 Local Catalyst Framework"
    output["base_framework_dates"] = framework_record_dates(output)
    return output


def get_effective_catalyst_framework(industry_id: str) -> dict[str, Any] | None:
    """Return base framework plus local override when one exists."""

    base = get_base_catalyst_framework(industry_id)
    if not base:
        return None
    override = load_framework_overrides().get(industry_id)
    if not isinstance(override, dict):
        return base
    effective = copy.deepcopy(base)
    for key in [
        "summary",
        "summaryZh",
        "heat_score",
        "heat_level",
        "heat_direction",
        "events",
        "source",
        "updated_at",
        "base_framework_dates",
    ]:
        if key in override:
            effective[key] = copy.deepcopy(override[key])
    effective["is_override"] = True
    effective["override"] = copy.deepcopy(override)
    effective["base_framework_dates"] = override.get("base_framework_dates") or base.get("base_framework_dates") or []
    return reconcile_effective_framework_with_snapshot(industry_id, normalize_effective_framework(effective))


def write_framework_override(industry_id: str, override: dict[str, Any]) -> dict[str, Any]:
    """Write one explicit local framework override."""

    overrides = load_framework_overrides()
    overrides[industry_id] = override
    save_framework_overrides(overrides)
    return get_effective_catalyst_framework(industry_id) or override


def remove_framework_override(industry_id: str) -> None:
    """Remove one override; used by audits and maintenance only."""

    overrides = load_framework_overrides()
    if industry_id in overrides:
        overrides.pop(industry_id)
        save_framework_overrides(overrides)


def build_framework_override_from_snapshot(
    industry_id: str,
    base_framework: dict[str, Any] | None,
    snapshot: dict[str, Any],
    catalyst_review: dict[str, Any] | None,
    live_news: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build an explicit override from V4.12 snapshot and current news context."""

    base_framework = base_framework or get_base_catalyst_framework(industry_id) or {}
    catalyst_review = catalyst_review or {}
    live_news = live_news or {}
    today = datetime.now().strftime("%Y-%m-%d")
    updated_at = datetime.now().isoformat(timespec="seconds")
    active = clean_catalyst_names([str(item) for item in snapshot.get("active_catalysts") or [] if item])
    emerging = clean_catalyst_names([str(item) for item in snapshot.get("emerging_catalysts") or [] if item])
    active_themes = snapshot.get("active_catalyst_themes") or []
    emerging_themes = snapshot.get("emerging_catalyst_themes") or []
    active_theme_names_zh = clean_catalyst_names(theme_names(active_themes, "zh")) or active
    active_theme_names = clean_catalyst_names(theme_names(active_themes, "en")) or active
    emerging_theme_names_zh = clean_catalyst_names(theme_names(emerging_themes, "zh")) or emerging
    emerging_theme_names = clean_catalyst_names(theme_names(emerging_themes, "en")) or emerging
    one_line_zh = str(snapshot.get("one_line_snapshot_zh") or "")
    one_line = str(snapshot.get("one_line_snapshot") or "")
    summary_zh = build_override_summary(active_theme_names_zh, emerging_theme_names_zh, one_line_zh, "zh")
    summary = build_override_summary(active_theme_names, emerging_theme_names, one_line, "en")
    evidence = str(snapshot.get("evidence_level") or catalyst_review.get("evidence_level") or "medium")
    events = build_semantic_override_events(
        industry_id,
        today,
        active_theme_names,
        emerging_theme_names,
        evidence,
        snapshot,
        live_news,
        active_zh=active_theme_names_zh,
        emerging_zh=emerging_theme_names_zh,
    )
    return {
        "updated_at": updated_at,
        "source": "V4.12 Dynamic Catalyst Snapshot",
        "base_framework_dates": framework_record_dates(base_framework),
        "summaryZh": summary_zh,
        "summary": summary,
        "heat_score": base_framework.get("heat_score"),
        "heat_level": base_framework.get("heat_level"),
        "heat_level_zh": localized_heat_level(base_framework.get("heat_level")),
        "heat_direction": "Rising" if snapshot.get("review_status") == "reinforced" else base_framework.get("heat_direction"),
        "heat_direction_zh": "升温" if snapshot.get("review_status") == "reinforced" else localized_heat_direction(base_framework.get("heat_direction")),
        "events": events,
    }


def apply_snapshot_as_framework_override(
    industry_id: str,
    base_framework: dict[str, Any] | None,
    snapshot: dict[str, Any],
    catalyst_review: dict[str, Any] | None,
    live_news: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build and write a local override from the current dynamic snapshot."""

    override = build_framework_override_from_snapshot(industry_id, base_framework, snapshot, catalyst_review, live_news)
    return write_framework_override(industry_id, override)


def normalize_effective_framework(framework: dict[str, Any]) -> dict[str, Any]:
    """Normalize event zh field variants for page/export compatibility."""

    output = copy.deepcopy(framework)
    events = []
    for event in output.get("events", []) or []:
        if not isinstance(event, dict):
            continue
        normalized = dict(event)
        if "event_typeZh" not in normalized and "event_type_zh" in normalized:
            normalized["event_typeZh"] = normalized.get("event_type_zh")
        if "impactZh" not in normalized and "impact_zh" in normalized:
            normalized["impactZh"] = normalized.get("impact_zh")
        if "confidenceZh" not in normalized and "confidence_zh" in normalized:
            normalized["confidenceZh"] = normalized.get("confidence_zh")
        events.append(normalized)
    output["events"] = events
    output.setdefault("base_framework_dates", framework_record_dates(output))
    output.setdefault("updated_at", "")
    output.setdefault("is_override", False)
    return output


def reconcile_effective_framework_with_snapshot(industry_id: str, framework: dict[str, Any]) -> dict[str, Any]:
    """Keep old overrides consistent with the latest V4.12 snapshot at read time."""

    if not framework.get("is_override"):
        return framework
    snapshot = read_latest_catalyst_snapshot(industry_id)
    if not snapshot:
        return framework
    events = framework.get("events") or []
    should_rebuild = snapshot_is_newer_than_framework(snapshot, framework) and needs_snapshot_event_rebuild(events, snapshot)
    if industry_id == "liquor" and needs_liquor_semantic_rebuild(events):
        should_rebuild = True
    if not should_rebuild:
        return framework

    active = clean_catalyst_names(snapshot.get("active_catalysts") or [])
    emerging = clean_catalyst_names(snapshot.get("emerging_catalysts") or [])
    active_themes = snapshot.get("active_catalyst_themes") or []
    emerging_themes = snapshot.get("emerging_catalyst_themes") or []
    active_theme_names_zh = clean_catalyst_names(theme_names(active_themes, "zh")) or active
    active_theme_names = clean_catalyst_names(theme_names(active_themes, "en")) or active
    emerging_theme_names_zh = clean_catalyst_names(theme_names(emerging_themes, "zh")) or emerging
    emerging_theme_names = clean_catalyst_names(theme_names(emerging_themes, "en")) or emerging
    event_date = str(snapshot.get("snapshot_generated_at") or framework.get("updated_at") or datetime.now().date())[:10]
    evidence = str(snapshot.get("evidence_level") or "medium")
    rebuilt = copy.deepcopy(framework)
    rebuilt["events"] = build_semantic_override_events(
        industry_id,
        event_date,
        active_theme_names,
        emerging_theme_names,
        evidence,
        snapshot,
        {"live_news_count_7d": snapshot_news_count(snapshot)},
        active_zh=active_theme_names_zh,
        emerging_zh=emerging_theme_names_zh,
    )
    rebuilt["summaryZh"] = build_override_summary(
        active_theme_names_zh,
        emerging_theme_names_zh,
        str(snapshot.get("one_line_snapshot_zh") or ""),
        "zh",
    )
    rebuilt["summary"] = build_override_summary(
        active_theme_names,
        emerging_theme_names,
        str(snapshot.get("one_line_snapshot") or ""),
        "en",
    )
    return rebuilt


def read_latest_catalyst_snapshot(industry_id: str) -> dict[str, Any] | None:
    if not LATEST_CATALYST_SNAPSHOT_PATH.exists():
        return None
    try:
        payload = json.loads(LATEST_CATALYST_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    snapshot = payload.get("industries", {}).get(industry_id) if isinstance(payload, dict) else None
    return snapshot if isinstance(snapshot, dict) else None


def snapshot_is_newer_than_framework(snapshot: dict[str, Any], framework: dict[str, Any]) -> bool:
    snapshot_time = str(snapshot.get("snapshot_generated_at") or "")
    framework_time = str(framework.get("updated_at") or "")
    if not snapshot_time or not framework_time:
        return bool(snapshot_time)
    return snapshot_time > framework_time


def needs_snapshot_event_rebuild(events: list[dict[str, Any]], snapshot: dict[str, Any]) -> bool:
    status = str(snapshot.get("review_status") or "")
    evidence = normalize_evidence_level(snapshot.get("evidence_level"))
    has_active = bool(snapshot.get("active_catalyst_themes") or snapshot.get("active_catalysts"))
    event_text = " ".join(
        str(event.get(key) or "")
        for event in events
        for key in ("title", "titleZh", "description", "descriptionZh")
    ).lower()
    has_low_divergence = any(event.get("confidence") == "low" for event in events) and any(
        term in event_text
        for term in ("diverge", "diverging", "待验证", "分化", "å¾…éªŒè¯", "åˆ†åŒ–")
    )
    has_strong_positive_high = any(
        event.get("impact") == "positive" and event.get("confidence") == "high"
        for event in events
    ) and any(
        term in event_text
        for term in ("strongly validates", "较强验证", "å½¢æˆè¾ƒå¼ºéªŒè¯")
    )
    if status == "reinforced" and evidence == "high" and has_active and has_low_divergence:
        return True
    if (status in {"diverging", "weakening", "insufficient_evidence"} or evidence == "low") and has_strong_positive_high:
        return True
    return False


def needs_liquor_semantic_rebuild(events: list[dict[str, Any]]) -> bool:
    if not events:
        return False
    all_technology = all(event.get("event_type") == "technology" for event in events)
    all_positive = all(event.get("impact") == "positive" for event in events)
    text = " ".join(
        str(event.get(key) or "")
        for event in events
        for key in ("title", "titleZh", "description", "descriptionZh")
    ).lower()
    has_news_core = "news" in text or "新闻" in text or "æ–°é—»" in text
    return all_technology or all_positive or has_news_core


def snapshot_news_count(snapshot: dict[str, Any]) -> int:
    text = " ".join(str(snapshot.get(key) or "") for key in ("coverage_note", "coverage_note_zh"))
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def framework_record_dates(framework: dict[str, Any]) -> list[str]:
    dates = [str(event.get("date", "")) for event in framework.get("events", []) or [] if isinstance(event, dict) and event.get("date")]
    return unique_keep_order(dates)


def build_override_summary(active: list[str], emerging: list[str], one_line: str, language: str) -> str:
    if language == "zh":
        active_text = "、".join(active[:5])
        emerging_text = "、".join(emerging[:6])
        parts = []
        if active_text:
            parts.append(f"当前活跃催化包括 {active_text}")
        if emerging_text:
            parts.append(f"新出现线索包括 {emerging_text}")
        if one_line:
            parts.append(one_line)
        return "；".join(parts) or "当前使用动态催化快照更新本地框架。"
    active_text = ", ".join(active[:5])
    emerging_text = ", ".join(emerging[:6])
    parts = []
    if active_text:
        parts.append(f"Active catalyst themes include {active_text}")
    if emerging_text:
        parts.append(f"Emerging clues include {emerging_text}")
    if one_line:
        parts.append(one_line)
    return "; ".join(parts) or "The local framework has been updated from the dynamic catalyst snapshot."


def build_override_events(
    today: str,
    active: list[str],
    emerging: list[str],
    evidence: str,
    snapshot: dict[str, Any],
    live_news: dict[str, Any],
    active_zh: list[str] | None = None,
    emerging_zh: list[str] | None = None,
) -> list[dict[str, Any]]:
    events = []
    active_zh = active_zh or active
    emerging_zh = emerging_zh or emerging
    confidence = "high" if evidence == "high" else "medium"
    confidence_zh = "高" if evidence == "high" else "中"
    if emerging:
        events.append(
            framework_event(
                today,
                "新催化线索出现",
                "Emerging catalyst clues detected",
                f"V4.12 动态快照识别到新增线索：{'、'.join(emerging[:8])}。",
                f"V4.12 dynamic snapshot identified emerging clues: {', '.join(emerging[:8])}.",
                confidence,
                confidence_zh,
            )
        )
    if active:
        events.append(
            framework_event(
                today,
                "核心催化线索获得实时新闻验证",
                "Core catalyst themes validated by live news",
                f"当前活跃催化包括：{'、'.join(active[:8])}。",
                f"Current active catalyst themes include: {', '.join(active[:8])}.",
                confidence,
                confidence_zh,
            )
        )
    if evidence == "high":
        events.append(
            framework_event(
                today,
                "实时新闻对本地框架形成较强验证",
                "Live news strongly validates local catalyst framework",
                str(snapshot.get("coverage_note_zh") or "当前实时新闻对本地框架形成较强验证。"),
                str(snapshot.get("coverage_note") or "Current live news strongly validates the local framework."),
                "high",
                "高",
            )
        )
    if emerging and events:
        events[0]["titleZh"] = f"{emerging[0]}成为新增催化线索"
        events[0]["title"] = f"{emerging[0]} becomes an emerging catalyst clue"
        events[0]["titleZh"] = f"{emerging_zh[0]}\u6210\u4e3a\u65b0\u589e\u50ac\u5316\u7ebf\u7d22"
        emerging_zh_text = "、".join(emerging_zh[:8])
        events[0]["descriptionZh"] = (
            f"V4.12 动态快照识别到新增线索：{emerging_zh_text}。"
        )
    if active:
        active_index = 1 if emerging and len(events) > 1 else 0
        if active_index < len(events):
            events[active_index]["titleZh"] = f"{active[0]}获得实时新闻验证"
            events[active_index]["title"] = f"{active[0]} validated by live news"
            events[active_index]["titleZh"] = f"{active_zh[0]}获得实时新闻验证"
            active_zh_text = "、".join(active_zh[:8])
            events[active_index]["descriptionZh"] = (
                f"V4.12 动态快照显示这些催化线索获得实时新闻支持：{active_zh_text}。"
            )
    return events


def build_semantic_override_events(
    industry_id: str,
    today: str,
    active: list[str],
    emerging: list[str],
    evidence: str,
    snapshot: dict[str, Any],
    live_news: dict[str, Any],
    active_zh: list[str] | None = None,
    emerging_zh: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build V4.1 override events with status-aware semantics."""

    events: list[dict[str, Any]] = []
    status = str(snapshot.get("review_status") or "")
    evidence = normalize_evidence_level(evidence)
    active = clean_catalyst_names(active)
    emerging = clean_catalyst_names(emerging)
    active_zh = clean_catalyst_names(active_zh or active)
    emerging_zh = clean_catalyst_names(emerging_zh or emerging)
    high_medium_news_count = count_high_medium_news(live_news)
    can_strongly_validate = (
        status == "reinforced"
        and evidence == "high"
        and bool(active)
        and high_medium_news_count >= 3
    )
    has_reinforced_active_evidence = status == "reinforced" and evidence == "high" and bool(active)

    if status == "insufficient_evidence" and not emerging:
        return []

    if active and status in {"reinforced", "stable"}:
        first = active[0]
        first_zh = active_zh[0] if active_zh else first
        event_type = infer_event_type(industry_id, [*active, *active_zh])
        impact = infer_event_impact(status, evidence, has_active=True, strong_validation=can_strongly_validate)
        impact = adjust_liquor_event_impact(industry_id, event_type, [*active, *active_zh], impact)
        confidence = infer_event_confidence(
            evidence,
            status,
            high_medium_news_count,
            has_active=True,
            strong_validation=can_strongly_validate,
        )
        events.append(
            semantic_framework_event(
                today,
                f"{first_zh}获得实时新闻支持",
                f"{first} receives live-news support",
                f"V4.12 动态快照显示当前状态为强化、证据强度较高，活跃催化线索获得实时新闻支持：{'、'.join(active_zh[:8])}。",
                f"V4.12 dynamic snapshot is reinforced with high evidence; active catalyst themes receive live-news support: {', '.join(active[:8])}.",
                event_type,
                impact,
                confidence,
            )
        )

    if emerging and not has_reinforced_active_evidence:
        first = emerging[0]
        first_zh = emerging_zh[0] if emerging_zh else first
        event_type = infer_event_type(industry_id, [*emerging, *emerging_zh])
        impact = infer_event_impact(status, evidence, has_active=bool(active), strong_validation=False)
        impact = adjust_liquor_event_impact(industry_id, event_type, [*emerging, *emerging_zh], impact)
        confidence = infer_event_confidence(
            evidence,
            status,
            high_medium_news_count,
            has_active=False,
            strong_validation=False,
        )
        events.append(
            semantic_framework_event(
                today,
                f"{first_zh}成为新线索待验证",
                f"{first} remains an emerging clue for validation",
                f"V4.12 动态快照识别到新线索：{'、'.join(emerging_zh[:8]) or '暂无明确新增线索'}；需要继续观察其与本地框架的匹配度。",
                f"V4.12 dynamic snapshot identified emerging clues: {', '.join(emerging[:8]) or 'no clear emerging clue'}; fit with the local framework still needs validation.",
                event_type,
                impact,
                confidence,
            )
        )

    if status == "diverging":
        clues = emerging_zh or clean_catalyst_names(snapshot.get("emerging_catalysts_zh") or [])
        clue_text_zh = "、".join(clues[:6]) or "新催化线索"
        clue_text = ", ".join((emerging or clues)[:6]) or "new catalyst clues"
        event_type = infer_event_type(industry_id, [*emerging, *clues])
        events.append(
            semantic_framework_event(
                today,
                "出现新催化线索，但与本地框架存在分化",
                "Emerging clues diverge from the local framework",
                f"V4.12 显示 {clue_text_zh} 仍处于分化或待验证状态，不生成强验证结论。",
                f"V4.12 shows {clue_text} remains diverging or unvalidated, so no strong validation event is generated.",
                event_type,
                "mixed",
                "low" if evidence == "low" else "medium",
            )
        )

    if status == "insufficient_evidence" and emerging:
        for event in events:
            event["impact"] = "neutral"
            event["impactZh"] = IMPACT_ZH["neutral"]
            event["confidence"] = "low"
            event["confidenceZh"] = CONFIDENCE_ZH["low"]

    if can_strongly_validate:
        event_type = infer_event_type(industry_id, [*active, *active_zh])
        impact = adjust_liquor_event_impact(industry_id, event_type, [*active, *active_zh], "positive")
        events.append(
            semantic_framework_event(
                today,
                "实时新闻对本地框架形成较强验证",
                "Live news strongly validates the local catalyst framework",
                str(snapshot.get("coverage_note_zh") or "当前实时新闻对本地框架形成较强验证，但仍需结合价格确认观察。"),
                str(snapshot.get("coverage_note") or "Current live news strongly validates the local framework, while price confirmation still needs monitoring."),
                event_type,
                impact,
                "high",
            )
        )

    return events


def theme_names(themes: list[dict[str, Any]], language: str) -> list[str]:
    return clean_catalyst_names([theme_display_name(theme, language) for theme in themes])


def clean_catalyst_names(values: list[Any] | tuple[Any, ...] | set[Any] | None) -> list[str]:
    output = []
    for value in values or []:
        text = str(value).strip()
        if not text or is_invalid_catalyst_theme(text):
            continue
        output.append(text)
    return unique_keep_order(output)


def is_invalid_catalyst_theme(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return True
    compact = normalized.replace(" ", "").replace("_", "")
    if normalized in INVALID_CATALYST_THEME_TERMS or compact in INVALID_CATALYST_THEME_TERMS:
        return True
    return len(normalized) < 3 and not any("\u4e00" <= char <= "\u9fff" for char in normalized)


def normalize_evidence_level(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"high", "medium", "low"}:
        return raw
    if raw in {"insufficient", "none", "missing"}:
        return "low"
    return "medium"


def count_high_medium_news(live_news: dict[str, Any]) -> int:
    explicit = live_news.get("live_news_count_7d")
    if isinstance(explicit, int):
        return explicit
    count = 0
    for item in live_news.get("items", []) or []:
        if isinstance(item, dict) and item.get("relevance", "high") in {"high", "medium"}:
            count += 1
    return count


def infer_event_impact(status: str, evidence: str, *, has_active: bool, strong_validation: bool) -> str:
    if status == "reinforced":
        if strong_validation:
            return "positive"
        return "mixed" if evidence == "high" else "neutral"
    if status == "stable":
        return "mixed" if has_active else "neutral"
    if status == "diverging":
        return "mixed"
    if status == "weakening":
        return "negative" if evidence == "high" else "mixed"
    if status == "insufficient_evidence":
        return "neutral"
    return "mixed"


def adjust_liquor_event_impact(industry_id: str, event_type: str, values: list[Any], fallback: str) -> str:
    if industry_id != "liquor":
        return fallback
    text = " ".join(str(value) for value in values if value).lower()
    compact = text.replace(" ", "")
    if event_type == "policy" or contains_any(text, compact, ["anti-corruption", "banquet ban", "反腐", "禁酒令"]):
        return "negative"
    if contains_any(text, compact, ["price inversion", "down", "decline", "pressure", "价格倒挂", "下行", "压力"]):
        return "negative" if event_type in {"pricing", "inventory"} else "mixed"
    if event_type in {"channel", "inventory", "pricing"}:
        return "mixed"
    if contains_any(text, compact, ["recovery", "improve", "复苏", "改善", "旺季"]):
        return "positive"
    if event_type in {"consumption", "demand"}:
        return "mixed" if fallback == "neutral" else fallback
    return fallback


def infer_event_confidence(
    evidence: str,
    status: str,
    high_medium_news_count: int,
    *,
    has_active: bool,
    strong_validation: bool,
) -> str:
    if strong_validation:
        return "high"
    if status in {"diverging", "insufficient_evidence"}:
        return "low" if evidence == "low" or not has_active else "medium"
    if evidence == "high" and high_medium_news_count >= 3 and has_active:
        return "medium"
    if evidence == "low" or high_medium_news_count < 3:
        return "low" if not has_active else "medium"
    return "medium"


def infer_event_type(industry_id: str, values: list[Any]) -> str:
    text = " ".join(str(value) for value in values if value).lower()
    compact = text.replace(" ", "")
    if industry_id == "liquor":
        if contains_any(text, compact, ["policy", "anti-corruption", "banquet ban", "tax", "反腐", "禁酒令", "税", "政策"]):
            return "policy"
        if contains_any(text, compact, ["risk", "pressure", "价格倒挂", "下行", "压力", "风险"]):
            if contains_any(text, compact, ["channel", "dealer", "渠道", "经销商"]):
                return "channel"
            if contains_any(text, compact, ["inventory", "destocking", "库存", "去库存"]):
                return "inventory"
            if contains_any(text, compact, ["price", "pricing", "批价", "提价", "价格"]):
                return "pricing"
            return "risk"
        if contains_any(text, compact, ["channel", "dealer", "sell-through", "渠道", "经销商", "动销"]):
            return "channel"
        if contains_any(text, compact, ["inventory", "destocking", "库存", "去库存"]):
            return "inventory"
        if contains_any(text, compact, ["price", "pricing", "批价", "提价", "价格"]):
            return "pricing"
        if contains_any(text, compact, ["consumption", "consumer", "banquet", "gift", "spring festival", "mid-autumn", "消费", "宴席", "礼赠", "春节", "中秋", "白酒", "高端酒", "次高端", "茅台", "五粮液", "泸州老窖", "liquor", "baijiu"]):
            return "consumption"
        if contains_any(text, compact, ["demand", "需求", "复苏"]):
            return "demand"
    if industry_id == "gold":
        if contains_any(text, compact, ["real yield", "treasury yield", "yield", "rates", "实际利率", "美债收益率", "利率"]):
            return "rates"
        if contains_any(text, compact, ["central bank", "央行购金", "央行"]):
            return "central_bank_demand"
        if contains_any(text, compact, ["geopolitical", "war", "safe haven", "地缘", "避险"]):
            return "safe_haven"
        if contains_any(text, compact, ["dollar", "inflation", "美元", "通胀"]):
            return "macro"
    if industry_id in {"memory", "semiconductor"}:
        if contains_any(text, compact, ["hbm", "dram", "nand", "ssd", "memory", "存储"]):
            return "product"
        if contains_any(text, compact, ["price cycle", "pricing", "价格周期", "涨价"]):
            return "price_cycle"
    if industry_id == "ai_compute":
        if contains_any(text, compact, ["cloud capex", "data center capex", "capex", "资本开支"]):
            return "capex"
        if contains_any(text, compact, ["ai server", "power", "cooling", "服务器", "电力", "散热"]):
            return "supply_chain"
        if contains_any(text, compact, ["gpu", "accelerator", "加速器"]):
            return "product"
    if industry_id == "cpo_optical_module":
        if contains_any(text, compact, ["800g", "1.6t", "transceiver", "optical module", "光模块"]):
            return "product"
        if contains_any(text, compact, ["cpo", "co-packaged", "silicon photonics", "硅光"]):
            return "technology"
        if contains_any(text, compact, ["interconnect", "bandwidth", "光互连", "带宽"]):
            return "demand"
    if industry_id == "semiconductor":
        if contains_any(text, compact, ["advanced packaging", "cowos", "先进封装"]):
            return "technology"
        if contains_any(text, compact, ["foundry", "capacity", "tsmc", "产能"]):
            return "supply_chain"
        if contains_any(text, compact, ["ai infrastructure", "cloud capex", "capex", "资本开支"]):
            return "capex"
    if contains_any(text, compact, ["capex", "资本开支"]):
        return "capex"
    if contains_any(text, compact, ["demand", "需求"]):
        return "demand"
    if contains_any(text, compact, ["supply", "capacity", "inventory", "供应", "产能", "库存"]):
        return "supply_chain"
    if contains_any(text, compact, ["policy", "政策"]):
        return "policy"
    if contains_any(text, compact, ["risk", "风险"]):
        return "risk"
    if contains_any(text, compact, ["product", "产品", "commercial", "商业化"]):
        return "product"
    if contains_any(text, compact, ["technology", "tech", "技术"]):
        return "technology"
    return "mixed"


def contains_any(text: str, compact: str, needles: list[str]) -> bool:
    for needle in needles:
        lowered = needle.lower()
        if lowered in text or lowered.replace(" ", "") in compact:
            return True
    return False


def semantic_framework_event(
    date: str,
    title_zh: str,
    title: str,
    description_zh: str,
    description: str,
    event_type: str,
    impact: str,
    confidence: str,
) -> dict[str, Any]:
    return {
        "date": date,
        "titleZh": title_zh,
        "title": title,
        "event_type": event_type,
        "event_typeZh": EVENT_TYPE_ZH.get(event_type, event_type),
        "impact": impact,
        "impactZh": IMPACT_ZH.get(impact, impact),
        "confidence": confidence,
        "confidenceZh": CONFIDENCE_ZH.get(confidence, confidence),
        "descriptionZh": description_zh,
        "description": description,
    }


def framework_event(
    date: str,
    title_zh: str,
    title: str,
    description_zh: str,
    description: str,
    confidence: str,
    confidence_zh: str,
) -> dict[str, Any]:
    return {
        "date": date,
        "titleZh": title_zh,
        "title": title,
        "event_type": "technology",
        "event_typeZh": "技术",
        "impact": "positive",
        "impactZh": "正面",
        "confidence": confidence,
        "confidenceZh": confidence_zh,
        "descriptionZh": description_zh,
        "description": description,
    }


def localized_heat_level(value: Any) -> str:
    return {"Low": "低", "Medium": "中", "High": "高", "Very High": "很高"}.get(str(value or ""), str(value or ""))


def localized_heat_direction(value: Any) -> str:
    return {"Rising": "升温", "Stable": "稳定", "Falling": "降温", "Mixed": "分化"}.get(str(value or ""), str(value or ""))


def unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
