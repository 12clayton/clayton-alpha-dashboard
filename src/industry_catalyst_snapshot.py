"""V4.12 dynamic catalyst snapshot layer.

This module builds local daily catalyst snapshots from V4.1 catalyst framework
data, cached V4.2 live-news observations, and V4.10 catalyst review results. It
does not fetch news or rewrite the V4.1 catalyst source data.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.industry_catalyst_themes import normalize_catalyst_themes


CATALYST_SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "data" / "industry_catalyst"
LATEST_CATALYST_SNAPSHOT_PATH = CATALYST_SNAPSHOT_DIR / "latest_catalyst_snapshot.json"

SNAPSHOT_REQUIRED_FIELDS = [
    "industry_id",
    "framework_record_dates",
    "snapshot_generated_at",
    "review_status",
    "review_status_zh",
    "evidence_level",
    "evidence_level_zh",
    "active_catalysts",
    "active_catalysts_zh",
    "active_catalyst_themes",
    "active_catalyst_themes_zh",
    "emerging_catalysts",
    "emerging_catalysts_zh",
    "emerging_catalyst_themes",
    "emerging_catalyst_themes_zh",
    "cooling_catalysts",
    "cooling_catalysts_zh",
    "coverage_note",
    "coverage_note_zh",
    "one_line_snapshot",
    "one_line_snapshot_zh",
]

STATUS_ZH = {
    "reinforced": "强化",
    "stable": "稳定",
    "diverging": "分化",
    "weakening": "减弱",
    "insufficient_evidence": "证据不足",
}

EVIDENCE_ZH = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "insufficient": "不足",
}


def build_dynamic_catalyst_snapshot(
    industry_id: str,
    catalyst_data: dict[str, Any] | None,
    live_news_data: dict[str, Any] | None,
    catalyst_review: dict[str, Any] | None,
    language: str = "zh",
) -> dict[str, Any]:
    """Build a deterministic dynamic catalyst snapshot without network access."""

    catalyst_data = catalyst_data or {}
    live_news_data = live_news_data or {}
    catalyst_review = catalyst_review or {}
    status = str(catalyst_review.get("review_status") or "insufficient_evidence")
    evidence = str(catalyst_review.get("evidence_level") or "insufficient")
    supported = [str(item) for item in catalyst_review.get("supported_catalysts") or [] if item]
    review_emerging = [str(item) for item in catalyst_review.get("emerging_catalysts") or [] if item]
    weak_or_missing = [str(item) for item in catalyst_review.get("weak_or_missing_evidence") or [] if item]
    news_clues = extract_news_clues(live_news_data)
    active_themes = catalyst_review.get("active_catalyst_themes") or normalize_catalyst_themes(industry_id, supported, language)
    emerging_themes = catalyst_review.get("emerging_catalyst_themes") or normalize_catalyst_themes(industry_id, review_emerging or news_clues, language)

    active = supported if status in {"reinforced", "stable"} else []
    emerging = unique_keep_order([*review_emerging, *[item for item in news_clues if item not in set(active)]])
    cooling = weak_or_missing if status == "weakening" else []
    if status == "insufficient_evidence":
        emerging = []
        cooling = []

    return {
        "industry_id": industry_id,
        "framework_record_dates": framework_record_dates(catalyst_data),
        "snapshot_generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_status": status,
        "review_status_zh": str(catalyst_review.get("review_status_zh") or STATUS_ZH.get(status, status)),
        "evidence_level": evidence,
        "evidence_level_zh": str(catalyst_review.get("evidence_level_zh") or EVIDENCE_ZH.get(evidence, evidence)),
        "active_catalysts": active,
        "active_catalysts_zh": active,
        "active_catalyst_themes": active_themes if status in {"reinforced", "stable"} else [],
        "active_catalyst_themes_zh": active_themes if status in {"reinforced", "stable"} else [],
        "emerging_catalysts": emerging[:8],
        "emerging_catalysts_zh": emerging[:8],
        "emerging_catalyst_themes": emerging_themes[:6],
        "emerging_catalyst_themes_zh": emerging_themes[:6],
        "cooling_catalysts": cooling[:8],
        "cooling_catalysts_zh": cooling[:8],
        "coverage_note": snapshot_coverage_note(status, catalyst_review, "en"),
        "coverage_note_zh": snapshot_coverage_note(status, catalyst_review, "zh"),
        "one_line_snapshot": one_line_snapshot(status, evidence, bool(active), "en"),
        "one_line_snapshot_zh": one_line_snapshot(status, evidence, bool(active), "zh"),
    }


def framework_record_dates(catalyst_data: dict[str, Any]) -> list[str]:
    dates = [str(event.get("date", "")) for event in catalyst_data.get("events", []) or [] if event.get("date")]
    return unique_keep_order(dates)


def extract_news_clues(live_news_data: dict[str, Any]) -> list[str]:
    clues: list[str] = []
    for item in live_news_data.get("items", []) or []:
        if item.get("relevance", "high") not in {"high", "medium"}:
            continue
        clues.extend(str(keyword) for keyword in item.get("matched_keywords", []) or [] if keyword)
    counts = Counter(clues)
    return [item for item, _count in counts.most_common(10)]


def snapshot_coverage_note(status: str, review: dict[str, Any], language: str) -> str:
    if language == "zh":
        if status == "insufficient_evidence":
            return "当前新闻源证据不足，可能受覆盖限制影响；这不代表本地催化框架失效。"
        return str(review.get("coverage_note_zh") or "动态快照基于当前实时新闻观察和催化复核结果生成。")
    if status == "insufficient_evidence":
        return "Current news evidence is limited and may reflect source coverage limits. This does not invalidate the local catalyst framework."
    return str(review.get("coverage_note") or "The snapshot is generated from current live-news observations and catalyst review results.")


def one_line_snapshot(status: str, evidence: str, has_active: bool, language: str) -> str:
    if language == "zh":
        if status == "reinforced":
            return "当前实时新闻对本地催化框架形成较强验证，活跃催化线索较明确。"
        if status == "stable":
            return "当前实时新闻对本地催化框架形成有限但有效支持。"
        if status == "diverging":
            return "当前实时新闻出现部分新线索，和本地催化框架存在一定分化。"
        if status == "weakening":
            return "当前实时新闻支持力度下降，部分催化线索需要后续复核。"
        return "当前新闻源证据不足，暂不能形成有效动态催化验证。"
    if status == "reinforced":
        return "Live news provides strong validation for the local catalyst framework."
    if status == "stable":
        return "Live news provides limited but useful support for the local catalyst framework."
    if status == "diverging":
        return "Live news contains some emerging clues that diverge from the local catalyst framework."
    if status == "weakening":
        return "Live-news support is weakening, so some catalyst clues need later review."
    return "Current news evidence is insufficient for an effective dynamic catalyst validation."


def ensure_catalyst_snapshot_cache() -> Path:
    CATALYST_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if not LATEST_CATALYST_SNAPSHOT_PATH.exists():
        LATEST_CATALYST_SNAPSHOT_PATH.write_text(
            json.dumps({"industries": {}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return LATEST_CATALYST_SNAPSHOT_PATH


def load_catalyst_snapshot_cache() -> dict[str, Any]:
    ensure_catalyst_snapshot_cache()
    try:
        payload = json.loads(LATEST_CATALYST_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        payload = {"industries": {}}
    if not isinstance(payload, dict):
        return {"industries": {}}
    payload.setdefault("industries", {})
    return payload


def read_dynamic_catalyst_snapshot(industry_id: str) -> dict[str, Any] | None:
    cached = load_catalyst_snapshot_cache().get("industries", {}).get(industry_id)
    return cached if isinstance(cached, dict) else None


def save_dynamic_catalyst_snapshot(snapshot: dict[str, Any], *, save_history: bool = True) -> None:
    industry_id = str(snapshot.get("industry_id", ""))
    if not industry_id:
        return
    cache = load_catalyst_snapshot_cache()
    cache.setdefault("industries", {})[industry_id] = snapshot
    cache["last_updated"] = datetime.now().isoformat(timespec="seconds")
    ensure_catalyst_snapshot_cache()
    LATEST_CATALYST_SNAPSHOT_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    if save_history:
        history_path = CATALYST_SNAPSHOT_DIR / f"catalyst_snapshot_{datetime.now().strftime('%Y-%m-%d')}.json"
        try:
            history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"industries": {}}
        except Exception:
            history = {"industries": {}}
        history.setdefault("industries", {})[industry_id] = snapshot
        history["last_updated"] = cache["last_updated"]
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
