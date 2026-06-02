"""Audit V4.10 catalyst review without network access."""

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
from src.industry_catalyst_review import (  # noqa: E402
    EVIDENCE_LEVELS,
    REVIEW_STATUSES,
    build_catalyst_review,
)


REQUIRED_FIELDS = [
    "review_status",
    "review_status_zh",
    "evidence_level",
    "evidence_level_zh",
    "supported_catalysts",
    "emerging_catalysts",
    "weak_or_missing_evidence",
    "coverage_note",
    "coverage_note_zh",
    "one_line_review",
    "one_line_review_zh",
    "reviewed_at",
]


def main() -> int:
    issues = []
    sample_news = {
        "live_news_count_7d": 2,
        "items": [
            {
                "title": "Nvidia GPU demand keeps AI chip catalyst active",
                "matched_keywords": ["Nvidia", "GPU", "chip"],
                "relevance": "high",
            }
        ],
    }
    review = build_catalyst_review("semiconductor", get_catalyst_data("semiconductor"), sample_news, language="zh")
    for field in REQUIRED_FIELDS:
        if field not in review:
            issues.append(f"missing review field: {field}")
    if review.get("review_status") not in REVIEW_STATUSES:
        issues.append(f"invalid review_status: {review.get('review_status')}")
    if review.get("evidence_level") not in EVIDENCE_LEVELS:
        issues.append(f"invalid evidence_level: {review.get('evidence_level')}")
    if not review.get("review_status_zh") or not review.get("one_line_review_zh"):
        issues.append("missing zh review text")

    no_news_review = build_catalyst_review(
        "cpo_optical_module",
        get_catalyst_data("cpo_optical_module"),
        {"live_news_count_7d": 0, "items": []},
        language="zh",
    )
    if no_news_review.get("review_status") != "insufficient_evidence":
        issues.append("high-heat no-news review should be insufficient_evidence")

    print_report("CATALYST REVIEW SAMPLE", review)
    print_report("CATALYST REVIEW ISSUES", issues)
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
