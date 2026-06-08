"""Updatable V4.1 catalyst framework store.

This module keeps the source V4.1 catalyst data immutable and applies local
overrides from data/industry_catalyst/framework_overrides.json when present.
Overrides are only written by explicit user action.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.industry_catalyst_data import get_catalyst_data
from src.industry_catalyst_themes import theme_display_name


CATALYST_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "industry_catalyst"
FRAMEWORK_OVERRIDES_PATH = CATALYST_STORE_DIR / "framework_overrides.json"

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
    return normalize_effective_framework(effective)


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
    active = [str(item) for item in snapshot.get("active_catalysts") or [] if item]
    emerging = [str(item) for item in snapshot.get("emerging_catalysts") or [] if item]
    active_themes = snapshot.get("active_catalyst_themes") or []
    emerging_themes = snapshot.get("emerging_catalyst_themes") or []
    active_theme_names_zh = theme_names(active_themes, "zh") or active
    active_theme_names = theme_names(active_themes, "en") or active
    emerging_theme_names_zh = theme_names(emerging_themes, "zh") or emerging
    emerging_theme_names = theme_names(emerging_themes, "en") or emerging
    one_line_zh = str(snapshot.get("one_line_snapshot_zh") or "")
    one_line = str(snapshot.get("one_line_snapshot") or "")
    summary_zh = build_override_summary(active_theme_names_zh, emerging_theme_names_zh, one_line_zh, "zh")
    summary = build_override_summary(active_theme_names, emerging_theme_names, one_line, "en")
    evidence = str(snapshot.get("evidence_level") or catalyst_review.get("evidence_level") or "medium")
    events = build_override_events(
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
        "events": events or copy.deepcopy(base_framework.get("events") or []),
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
        events[0]["descriptionZh"] = (
            f"V4.12 \u52a8\u6001\u5feb\u7167\u8bc6\u522b\u5230\u65b0\u589e\u7ebf\u7d22\uff1a"
            f"{'\u3001'.join(emerging_zh[:8])}\u3002"
        )
    if active:
        active_index = 1 if emerging and len(events) > 1 else 0
        if active_index < len(events):
            events[active_index]["titleZh"] = f"{active[0]}获得实时新闻验证"
            events[active_index]["title"] = f"{active[0]} validated by live news"
            events[active_index]["titleZh"] = f"{active_zh[0]}\u83b7\u5f97\u5b9e\u65f6\u65b0\u95fb\u9a8c\u8bc1"
            events[active_index]["descriptionZh"] = (
                f"\u5f53\u524d\u6d3b\u8dc3\u50ac\u5316\u5305\u62ec\uff1a{'\u3001'.join(active_zh[:8])}\u3002"
            )
    return events[:3]


def theme_names(themes: list[dict[str, Any]], language: str) -> list[str]:
    return [theme_display_name(theme, language) for theme in themes if theme_display_name(theme, language)]


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
