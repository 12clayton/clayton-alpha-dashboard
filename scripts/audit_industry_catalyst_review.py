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
from src.industry_catalyst_themes import normalize_catalyst_themes  # noqa: E402


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

    cpo_news_review = build_catalyst_review(
        "cpo_optical_module",
        get_catalyst_data("cpo_optical_module"),
        {
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
        },
        language="zh",
    )
    if cpo_news_review.get("review_status") == "insufficient_evidence":
        issues.append("CPO keyword-matched news should not be insufficient_evidence")
    if cpo_news_review.get("review_status") not in {"stable", "reinforced"}:
        issues.append(f"CPO keyword-matched news should be stable or reinforced, got {cpo_news_review.get('review_status')}")
    if not cpo_news_review.get("supported_catalysts"):
        issues.append("CPO keyword-matched news should populate supported_catalysts")
    semiconductor_themes = normalize_catalyst_themes(
        "semiconductor",
        ["SK Hynix", "DRAM", "Micron", "AI chip", "Broadcom"],
        language="zh",
    )
    semiconductor_theme_names = {item.get("theme_zh") for item in semiconductor_themes}
    if "HBM / DRAM 存储链强化" not in semiconductor_theme_names:
        issues.append("semiconductor memory keywords should map to HBM / DRAM theme")
    if "AI 芯片链条扩散" not in semiconductor_theme_names:
        issues.append("semiconductor AI chip keywords should map to AI chip-chain theme")

    cpo_themes = normalize_catalyst_themes("cpo_optical_module", ["CPO", "silicon photonics"], language="zh")
    cpo_theme_names = {item.get("theme_zh") for item in cpo_themes}
    if "CPO 技术路线验证" not in cpo_theme_names:
        issues.append("CPO keyword should map to CPO technology-route theme")
    if "硅光路线推进" not in cpo_theme_names:
        issues.append("silicon photonics should map to silicon photonics theme")

    gold_themes = normalize_catalyst_themes("gold", ["real yields", "dollar", "central bank buying"], language="zh")
    gold_theme_names = {item.get("theme_zh") for item in gold_themes}
    if "美元与实际利率压力" not in gold_theme_names:
        issues.append("gold real-yield keywords should map to dollar/real-yield theme")
    if "央行购金支撑" not in gold_theme_names:
        issues.append("gold central-bank keywords should map to central-bank support theme")

    broad_fallback = normalize_catalyst_themes("unknown_theme", ["technology", "market", "stock"], language="zh")
    if broad_fallback:
        issues.append("broad fallback terms should not become default themes")

    print_report("CATALYST REVIEW SAMPLE", review)
    print_report("CPO REVIEW SAMPLE", cpo_news_review)
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
