"""Audit V4.12 dynamic catalyst snapshot without network access."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_catalyst_data import get_catalyst_data  # noqa: E402
from src.industry_catalyst_review import build_catalyst_review  # noqa: E402
from src.industry_catalyst_snapshot import (  # noqa: E402
    SNAPSHOT_REQUIRED_FIELDS,
    build_dynamic_catalyst_snapshot,
    ensure_catalyst_snapshot_cache,
    read_dynamic_catalyst_snapshot,
    save_dynamic_catalyst_snapshot,
)


def main() -> int:
    issues = []
    catalyst = get_catalyst_data("cpo_optical_module")
    live_news = {
        "live_news_count_7d": 2,
        "items": [
            {
                "title": "Lambda highlights Nvidia CPO switch progress",
                "matched_keywords": ["CPO"],
                "relevance": "high",
            },
            {
                "title": "GlobalFoundries expands silicon photonics collaboration",
                "matched_keywords": ["silicon photonics"],
                "relevance": "medium",
            },
        ],
    }
    review = build_catalyst_review("cpo_optical_module", catalyst, live_news, language="zh")
    snapshot = build_dynamic_catalyst_snapshot("cpo_optical_module", catalyst, live_news, review, language="zh")
    missing = [field for field in SNAPSHOT_REQUIRED_FIELDS if field not in snapshot]
    if missing:
        issues.append(f"snapshot missing fields: {missing}")
    if not snapshot.get("review_status_zh") or not snapshot.get("one_line_snapshot_zh"):
        issues.append("snapshot missing zh fields")
    if snapshot.get("review_status") not in {"reinforced", "stable", "diverging", "weakening", "insufficient_evidence"}:
        issues.append(f"invalid snapshot status: {snapshot.get('review_status')}")
    if snapshot.get("review_status") == "stable" and not snapshot.get("active_catalysts"):
        issues.append("stable snapshot should include active catalysts for CPO sample")

    cache_path = ensure_catalyst_snapshot_cache()
    if not cache_path.exists():
        issues.append("snapshot cache file was not created")
    try:
        save_dynamic_catalyst_snapshot(snapshot, save_history=False)
        cached = read_dynamic_catalyst_snapshot("cpo_optical_module")
        if not cached or cached.get("industry_id") != "cpo_optical_module":
            issues.append("snapshot cache read/write failed")
    except Exception as exc:
        issues.append(f"snapshot cache read/write raised: {exc}")

    no_news_review = build_catalyst_review(
        "liquor",
        get_catalyst_data("liquor"),
        {"live_news_count_7d": 0, "items": []},
        language="zh",
    )
    no_news_snapshot = build_dynamic_catalyst_snapshot(
        "liquor",
        get_catalyst_data("liquor"),
        {"live_news_count_7d": 0, "items": []},
        no_news_review,
        language="zh",
    )
    if no_news_snapshot.get("review_status") != "insufficient_evidence":
        issues.append("no-news snapshot should be insufficient_evidence")
    if no_news_snapshot.get("cooling_catalysts"):
        issues.append("insufficient-evidence snapshot should not mark catalysts as cooling")

    print_report("CATALYST SNAPSHOT SAMPLE", snapshot)
    print_report("CATALYST SNAPSHOT CACHE", str(cache_path))
    print_report("CATALYST SNAPSHOT ISSUES", issues)
    return 1 if issues else 0


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
