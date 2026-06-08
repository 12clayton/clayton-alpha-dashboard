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
    GoogleNewsRSSProvider,
    MAX_TICKERS_PER_FETCH,
    NEWS_CACHE_TTL_HOURS,
    NEWS_CACHE_PATH,
    NEWS_ITEM_SCHEMA,
    RELEVANCE_LEVELS,
    YahooFinanceNewsProvider,
    build_google_news_queries,
    cpo_query_without_optical_context,
    cached_news_is_fresh,
    dedupe_news_items,
    ensure_news_relevance,
    enrich_news_metrics,
    industry_news_config,
    load_news_cache,
    normalize_google_rss_item,
    normalize_yfinance_news_item,
    rank_and_limit_news_items,
    read_industry_news,
)
from src.industry_news_config import get_industry_news_config  # noqa: E402
from src.industry_trend_data import industryTrendData  # noqa: E402


def main() -> int:
    issues = []
    cache_path = NEWS_CACHE_PATH
    if not cache_path.exists():
        issues.append("cache file does not exist for read-only audit")
    if not isinstance(NEWS_CACHE_TTL_HOURS, int) or NEWS_CACHE_TTL_HOURS <= 0:
        issues.append("cache TTL constant is invalid")
    if MAX_TICKERS_PER_FETCH != 3:
        issues.append(f"ticker limit should be 3, got {MAX_TICKERS_PER_FETCH}")

    cache_payload = load_news_cache()
    if not isinstance(cache_payload, dict) or "industries" not in cache_payload:
        issues.append("cache read function returned invalid payload")

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
    for field in ["source_name", "source_type", "source_quality"]:
        if field not in NEWS_ITEM_SCHEMA:
            issues.append(f"news item schema missing required V4.11 source field: {field}")
    if RELEVANCE_LEVELS != {"high", "medium", "low"}:
        issues.append(f"invalid relevance levels: {RELEVANCE_LEVELS}")
    if YahooFinanceNewsProvider().source_type != "ticker_news":
        issues.append("YahooFinanceNewsProvider source_type should be ticker_news")
    if GoogleNewsRSSProvider().source_type != "search_rss":
        issues.append("GoogleNewsRSSProvider source_type should be search_rss")

    semiconductor_config = industry_news_config("semiconductor")
    configured_semiconductor = get_industry_news_config("semiconductor")
    if not configured_semiconductor:
        issues.append("industry_news_config.py did not return semiconductor config")
    if not semiconductor_config.get("search_queries"):
        issues.append("configured semiconductor should return search_queries")
    if len(semiconductor_config.get("relevance_keywords", [])) < 8:
        issues.append("configured semiconductor should return relevance_keywords")
    if "Nvidia AI chip HBM" not in build_google_news_queries("semiconductor", semiconductor_config.get("keywords", [])):
        issues.append("configured semiconductor search query should take priority")

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
    for field in ["source_name", "source_type", "source_quality"]:
        if high_item and field not in high_item:
            issues.append(f"normalized item missing source field: {field}")

    cpo_config = industry_news_config("cpo_optical_module")
    if "co-packaged optics" not in cpo_config.get("search_queries", []):
        issues.append("configured CPO search_queries should be exposed")
    if "co-packaged optics" not in cpo_config.get("relevance_keywords", []):
        issues.append("configured CPO relevance_keywords should be exposed")
    cpo_queries = build_google_news_queries("cpo_optical_module", cpo_config.get("keywords", []))
    if not cpo_queries:
        issues.append("configured CPO should return strict Google News queries")
    if any(cpo_query_without_optical_context("cpo_optical_module", query) for query in cpo_queries):
        issues.append(f"CPO queries should all include optical context: {cpo_queries}")
    for broad_query in ["Nvidia AI", "Marvell AI", "Broadcom AI", "semiconductor AI"]:
        if not cpo_query_without_optical_context("cpo_optical_module", broad_query):
            issues.append(f"CPO strict query mode should reject broad query: {broad_query}")
    cpo_high = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "Optical module 800G demand expands in data centers",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    cpo_low = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "Generic market update mentions unrelated companies",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    cpo_stock_low = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "Marvell stock surges on S&P 500 inclusion",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    cpo_margin_low = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "Nvidia's 75% Margins Could Hold Through 2030",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    cpo_silicon_photonics_high = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "Optics and Silicon Photonics: The Next Data Highway Inside Chips",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    cpo_transceiver_high = ensure_news_relevance(
        {
            "industry_id": "cpo_optical_module",
            "title": "800G optical transceiver demand rises for AI data centers",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    gold_config = industry_news_config("gold")
    gold_high = ensure_news_relevance(
        {
            "industry_id": "gold",
            "title": "Gold steadies as real yields and dollar shift",
            "related_tickers": [],
            "matched_keywords": [],
            "source": "Google News RSS",
            "source_name": "Google News RSS",
            "source_type": "search_rss",
            "source_quality": "medium",
        },
        "gold",
        gold_config.get("keywords", []),
    )
    if cpo_high.get("relevance") != "high":
        issues.append("CPO keyword sample should be high relevance")
    if cpo_low.get("relevance") != "low":
        issues.append("CPO non-keyword sample should be low relevance")
    if cpo_stock_low.get("relevance") != "low":
        issues.append("CPO Marvell stock sample should be low relevance")
    if cpo_margin_low.get("relevance") != "low":
        issues.append("CPO Nvidia margin sample should be low relevance")
    if cpo_silicon_photonics_high.get("relevance") not in {"high", "medium"}:
        issues.append("CPO silicon photonics sample should be high or medium relevance")
    if cpo_transceiver_high.get("relevance") not in {"high", "medium"}:
        issues.append("CPO 800G optical transceiver sample should be high or medium relevance")
    cpo_merged = rank_and_limit_news_items(
        [
            {
                "industry_id": "cpo_optical_module",
                "title": f"Yahoo market stock update Nvidia Marvell Broadcom #{index}",
                "publisher": "Yahoo",
                "link": f"https://example.com/yahoo-{index}",
                "published_at": f"2026-06-08T15:{index:02d}:00+00:00",
                "related_tickers": ["NVDA"],
                "matched_keywords": [],
                "source": "Yahoo Finance",
                "source_name": "Yahoo Finance",
                "source_type": "ticker_news",
                "source_quality": "medium",
                "language": "en",
            }
            for index in range(20)
        ]
        + [
            {
                "industry_id": "cpo_optical_module",
                "title": "800G optical transceiver demand rises for AI data centers",
                "publisher": "Google",
                "link": "https://example.com/google-cpo-1",
                "published_at": "2026-06-08T16:01:00+00:00",
                "related_tickers": [],
                "matched_keywords": [],
                "source": "Google News RSS",
                "source_name": "Google News RSS",
                "source_type": "search_rss",
                "source_quality": "medium",
                "language": "en",
            },
            {
                "industry_id": "cpo_optical_module",
                "title": "Silicon photonics optical interconnect advances for data center switches",
                "publisher": "Google",
                "link": "https://example.com/google-cpo-2",
                "published_at": "2026-06-08T16:02:00+00:00",
                "related_tickers": [],
                "matched_keywords": [],
                "source": "Google News RSS",
                "source_name": "Google News RSS",
                "source_type": "search_rss",
                "source_quality": "medium",
                "language": "en",
            },
        ],
        "cpo_optical_module",
        cpo_config.get("keywords", []),
    )
    merged_titles = {str(item.get("title", "")) for item in cpo_merged}
    if "800G optical transceiver demand rises for AI data centers" not in merged_titles:
        issues.append("CPO merge ranking dropped the 800G Google RSS high-relevance item")
    if "Silicon photonics optical interconnect advances for data center switches" not in merged_titles:
        issues.append("CPO merge ranking dropped the silicon photonics Google RSS high-relevance item")
    if len([item for item in cpo_merged if item.get("relevance") == "low"]) >= len(cpo_merged):
        issues.append("CPO merge ranking should not allow low relevance to fill the whole cache")
    cpo_merged_metrics = enrich_news_metrics(
        {
            "industry_id": "cpo_optical_module",
            "items": cpo_merged,
            "last_updated": "2026-06-08T16:03:00+00:00",
            "source": "Yahoo Finance, Google News RSS",
            "source_names": ["Yahoo Finance", "Google News RSS"],
            "source_types": ["ticker_news", "search_rss"],
            "fetch_status": "available",
            "failed_reason": "",
        },
        "cpo_optical_module",
    )
    if cpo_merged_metrics.get("live_news_count_7d", 0) <= 0:
        issues.append("CPO merge ranking should produce live high/medium news count above zero")
    if gold_high.get("relevance") != "high":
        issues.append("Gold real-yields sample should be high relevance")
    fallback_config = industry_news_config("wind_power")
    if fallback_config.get("has_news_config"):
        issues.append("unconfigured wind_power industry should use fallback, not explicit config")
    if not fallback_config.get("keywords"):
        issues.append("unconfigured wind_power industry fallback should return keywords")
    duplicate_items = dedupe_news_items(
        [
            {"title": "Nvidia GPU demand lifts suppliers", "link": "https://example.com/a"},
            {"title": "Nvidia GPU demand lifts suppliers - Yahoo Finance", "link": "https://example.com/b"},
            {"title": "Another title", "link": "https://example.com/a"},
        ]
    )
    if len(duplicate_items) != 1:
        issues.append("multi-source dedupe by link/title did not work")

    legacy_item = ensure_news_relevance(
        {
            "industry_id": "semiconductor",
            "title": "Nvidia GPU news",
            "source": "Yahoo Finance",
        },
        "semiconductor",
        semiconductor_config.get("keywords", []),
    )
    for field in ["source_name", "source_type", "source_quality", "matched_keywords", "relevance_reason"]:
        if field not in legacy_item:
            issues.append(f"legacy cache compatibility missing field: {field}")

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
