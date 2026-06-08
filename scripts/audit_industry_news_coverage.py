"""Audit V4.14 industry news coverage without network access."""

from __future__ import annotations

import json
import sys
import types
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_news_config import get_industry_news_config  # noqa: E402
from src.industry_news_provider import NEWS_CACHE_PATH, ensure_news_relevance, parse_news_time  # noqa: E402
from src.industry_trend_data import industryTrendData  # noqa: E402


COVERAGE_STATUSES = {
    "good",
    "thin_keywords",
    "low_relevance_pollution",
    "no_recent_news",
    "no_config",
    "unknown",
}


def main() -> int:
    cache = load_cache_read_only()
    rows = [audit_industry(str(industry.get("id", "")), cache) for industry in industryTrendData]
    summary = Counter(row["coverage_status"] for row in rows)
    thin_keyword_rows = [
        row for row in rows if row["coverage_status"] in {"thin_keywords", "no_config"}
    ]

    print_report("NEWS COVERAGE SUMMARY", {status: summary.get(status, 0) for status in sorted(COVERAGE_STATUSES)})
    print_report("NEWS COVERAGE ROWS", rows)
    print_report(
        "KEYWORD ATTENTION LIST",
        [
            {
                "industry_id": row["industry_id"],
                "coverage_status": row["coverage_status"],
                "search_query_count": row["search_query_count"],
                "relevance_keyword_count": row["relevance_keyword_count"],
            }
            for row in sorted(
                thin_keyword_rows,
                key=lambda item: (item["has_news_config"], item["relevance_keyword_count"], item["search_query_count"]),
            )[:12]
        ],
    )
    return 0


def audit_industry(industry_id: str, cache: dict[str, Any]) -> dict[str, Any]:
    config = get_industry_news_config(industry_id)
    has_config = bool(config)
    search_query_count = count_list(config.get("search_queries"))
    relevance_keyword_count = count_list(config.get("relevance_keywords"))
    theme_count = len(config.get("theme_keywords", {})) if isinstance(config.get("theme_keywords"), dict) else 0
    high_medium_count_7d, low_news_count, latest_news_time = cached_news_metrics(industry_id, cache)
    low_to_high_ratio = round(low_news_count / high_medium_count_7d, 2) if high_medium_count_7d else None
    coverage_status = classify_coverage_status(
        has_config=has_config,
        search_query_count=search_query_count,
        relevance_keyword_count=relevance_keyword_count,
        high_medium_count_7d=high_medium_count_7d,
        low_news_count=low_news_count,
        low_to_high_ratio=low_to_high_ratio,
    )
    return {
        "industry_id": industry_id,
        "has_news_config": has_config,
        "search_query_count": search_query_count,
        "relevance_keyword_count": relevance_keyword_count,
        "theme_count": theme_count,
        "cached_high_medium_news_count_7d": high_medium_count_7d,
        "cached_low_news_count": low_news_count,
        "low_to_high_ratio": low_to_high_ratio,
        "latest_news_time": latest_news_time,
        "coverage_status": coverage_status,
    }


def classify_coverage_status(
    *,
    has_config: bool,
    search_query_count: int,
    relevance_keyword_count: int,
    high_medium_count_7d: int,
    low_news_count: int,
    low_to_high_ratio: float | None,
) -> str:
    if not has_config:
        return "no_config"
    if search_query_count < 3 or relevance_keyword_count < 8:
        return "thin_keywords"
    if low_news_count >= 10 and high_medium_count_7d <= 2:
        return "low_relevance_pollution"
    if high_medium_count_7d == 0:
        return "no_recent_news"
    if high_medium_count_7d >= 5 and low_to_high_ratio is not None and low_to_high_ratio <= 3:
        return "good"
    return "unknown"


def cached_news_metrics(industry_id: str, cache: dict[str, Any]) -> tuple[int, int, str]:
    cached = cache.get("industries", {}).get(industry_id, {})
    if not isinstance(cached, dict):
        return 0, 0, ""
    raw_items = []
    for key in ("items", "low_relevance_items"):
        values = cached.get(key)
        if isinstance(values, list):
            raw_items.extend(item for item in values if isinstance(item, dict))

    now = datetime.now(timezone.utc)
    high_medium_count_7d = 0
    low_news_count = 0
    valid_times = []
    for raw_item in raw_items:
        item = ensure_news_relevance(raw_item, industry_id)
        parsed = parse_news_time(item.get("published_at"))
        if parsed is not None:
            valid_times.append(parsed)
        if item.get("relevance") == "low":
            low_news_count += 1
            continue
        if item.get("relevance") in {"high", "medium"} and parsed is not None and now - parsed <= timedelta(days=7):
            high_medium_count_7d += 1

    latest_news_time = max(valid_times).isoformat() if valid_times else ""
    return high_medium_count_7d, low_news_count, latest_news_time


def load_cache_read_only() -> dict[str, Any]:
    if not NEWS_CACHE_PATH.exists():
        return {"industries": {}}
    try:
        payload = json.loads(NEWS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"industries": {}}
    if not isinstance(payload, dict):
        return {"industries": {}}
    industries = payload.get("industries")
    if not isinstance(industries, dict):
        payload["industries"] = {}
    return payload


def count_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def print_report(title: str, payload: object) -> None:
    print(f"\n## {title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
