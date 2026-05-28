"""Audit V4.2 lightweight industry news provider without network access."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_news_provider import (  # noqa: E402
    MAX_TICKERS_PER_FETCH,
    NEWS_CACHE_TTL_HOURS,
    NEWS_ITEM_SCHEMA,
    RELEVANCE_LEVELS,
    cached_news_is_fresh,
    ensure_news_cache,
    industry_news_config,
    load_news_cache,
    normalize_yfinance_news_item,
    read_industry_news,
    save_news_cache,
)
from src.industry_trend_data import industryTrendData  # noqa: E402


def main() -> int:
    issues = []
    cache_path = ensure_news_cache()
    if not cache_path.exists():
        issues.append("cache file was not created")
    if not isinstance(NEWS_CACHE_TTL_HOURS, int) or NEWS_CACHE_TTL_HOURS <= 0:
        issues.append("cache TTL constant is invalid")
    if MAX_TICKERS_PER_FETCH != 3:
        issues.append(f"ticker limit should be 3, got {MAX_TICKERS_PER_FETCH}")

    cache_payload = load_news_cache()
    if not isinstance(cache_payload, dict) or "industries" not in cache_payload:
        issues.append("cache read function returned invalid payload")
    try:
        save_news_cache(cache_payload)
    except Exception as exc:
        issues.append(f"cache write function failed: {exc}")

    sample = read_industry_news("semiconductor")
    if not isinstance(cached_news_is_fresh("semiconductor"), bool):
        issues.append("TTL freshness helper did not return bool")
    for field in ["industry_id", "items", "last_updated", "source", "fetch_status", "failed_reason"]:
        if field not in sample:
            issues.append(f"cached result missing field: {field}")

    schema_item = {field: "" for field in NEWS_ITEM_SCHEMA}
    missing_schema = [field for field in NEWS_ITEM_SCHEMA if field not in schema_item]
    if missing_schema:
        issues.append(f"news item schema missing: {missing_schema}")
    for field in ["matched_keywords", "relevance", "relevance_reason"]:
        if field not in NEWS_ITEM_SCHEMA:
            issues.append(f"news item schema missing required relevance field: {field}")
    if RELEVANCE_LEVELS != {"high", "medium", "low"}:
        issues.append(f"invalid relevance levels: {RELEVANCE_LEVELS}")

    semiconductor_config = industry_news_config("semiconductor")
    high_item = normalize_yfinance_news_item(
        {"title": "Nvidia GPU demand lifts AI chip suppliers", "publisher": "Audit"},
        "semiconductor",
        "NVDA",
        semiconductor_config.get("keywords", []),
    )
    low_item = normalize_yfinance_news_item(
        {"title": "SpaceX IPO speculation grows", "publisher": "Audit"},
        "semiconductor",
        "NVDA",
        semiconductor_config.get("keywords", []),
    )
    if not high_item or high_item.get("relevance") not in RELEVANCE_LEVELS:
        issues.append("high relevance sample did not normalize correctly")
    if high_item and not high_item.get("matched_keywords"):
        issues.append("high relevance sample did not populate matched_keywords")
    if not low_item or low_item.get("relevance") != "low":
        issues.append("low relevance sample did not normalize correctly")
    if high_item and "relevance_reason" not in high_item:
        issues.append("relevance_reason missing from normalized item")

    empty_configs = []
    for industry in industryTrendData:
        config = industry_news_config(str(industry["id"]))
        if not config.get("keywords"):
            empty_configs.append(industry["id"])
    if empty_configs:
        issues.append({"industries_missing_keywords": empty_configs})

    print_report("NEWS CACHE PATH", str(cache_path))
    print_report("NEWS ITEM SCHEMA", NEWS_ITEM_SCHEMA)
    print_report("PROVIDER ISSUES", issues)
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
