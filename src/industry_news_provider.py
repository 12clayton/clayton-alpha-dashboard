"""V4.2 lightweight live-news provider for industry trend pages.

This module fetches public Yahoo Finance news through yfinance when explicitly
requested, stores a local JSON cache, and exposes cache-only reads for pages.
It does not summarize, score, or infer investment conclusions.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.industry_market_data import INDUSTRY_MARKET_TICKERS
from src.industry_trend_data import industryTrendData

try:
    import yfinance as yf
except Exception:  # pragma: no cover - optional runtime dependency
    yf = None


NEWS_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "industry_news"
NEWS_CACHE_PATH = NEWS_DATA_DIR / "news_cache.json"
NEWS_CACHE_TTL_HOURS = 6
MAX_NEWS_PER_INDUSTRY = 20
MAX_TICKERS_PER_FETCH = 3

NEWS_ITEM_SCHEMA = [
    "id",
    "industry_id",
    "title",
    "publisher",
    "link",
    "published_at",
    "related_tickers",
    "matched_keywords",
    "relevance",
    "relevance_reason",
    "source",
    "language",
]

LIVE_NEWS_STATUS = {"available", "no_recent_news", "fetch_failed", "not_configured"}
RELEVANCE_LEVELS = {"high", "medium", "low"}

NEWS_KEYWORDS: dict[str, list[str]] = {
    "semiconductor": [
        "semiconductor",
        "chip",
        "chips",
        "AI chip",
        "GPU",
        "HBM",
        "DRAM",
        "NAND",
        "foundry",
        "wafer",
        "advanced packaging",
        "TSMC",
        "Micron",
        "SK Hynix",
        "ASML",
        "Nvidia",
        "AMD",
        "Broadcom",
        "Marvell",
        "半导体",
        "芯片",
        "AI芯片",
        "存储",
        "先进封装",
        "晶圆代工",
        "半导体设备",
    ],
    "memory": ["memory chip", "DRAM", "NAND", "HBM", "enterprise SSD", "high bandwidth memory"],
    "cpo_optical_module": ["optical module", "CPO", "co-packaged optics", "silicon photonics", "800G", "1.6T"],
    "ai_compute": ["AI infrastructure", "AI server", "GPU", "accelerator", "data center capex"],
    "gold": ["gold", "real yield", "central bank buying", "safe haven"],
    "sic": ["silicon carbide", "power semiconductor", "EV inverter"],
    "solar": ["solar", "module price", "inverter", "renewable energy"],
}

LOW_RELEVANCE_TITLE_PATTERNS = [
    "spacex",
    "sofi",
    "trade desk",
    "tariff fears",
    "stock market today",
    "market rally",
    "dow jones",
    "s&p 500",
    "nasdaq futures",
    "crypto",
    "bitcoin",
]

for logger_name in ("yfinance", "peewee"):
    news_logger = logging.getLogger(logger_name)
    news_logger.setLevel(logging.CRITICAL)
    news_logger.propagate = False


def ensure_news_cache() -> Path:
    """Create the news cache directory and file if needed."""

    NEWS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not NEWS_CACHE_PATH.exists():
        NEWS_CACHE_PATH.write_text(json.dumps({"industries": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    return NEWS_CACHE_PATH


def load_news_cache() -> dict[str, Any]:
    """Load local news cache without failing the page."""

    ensure_news_cache()
    try:
        payload = json.loads(NEWS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        payload = {"industries": {}}
    if not isinstance(payload, dict):
        return {"industries": {}}
    payload.setdefault("industries", {})
    return payload


def save_news_cache(cache: dict[str, Any]) -> None:
    """Persist local news cache."""

    ensure_news_cache()
    NEWS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def read_industry_news(industry_id: str) -> dict[str, Any]:
    """Read one industry's cached news result only."""

    cache = load_news_cache()
    cached = cache.get("industries", {}).get(industry_id)
    if cached:
        return enrich_news_metrics(cached, industry_id)
    status = "not_configured" if not industry_news_config(industry_id) else "no_recent_news"
    return enrich_news_metrics(
        {
            "industry_id": industry_id,
            "items": [],
            "last_updated": "",
            "source": "Yahoo Finance",
            "fetch_status": status,
            "failed_reason": "cache_missing",
        },
        industry_id,
    )


def refresh_industry_news(industry: dict[str, Any], *, force: bool = True) -> dict[str, Any]:
    """Fetch and cache live news for one industry."""

    industry_id = str(industry.get("id", ""))
    if not force and cached_news_is_fresh(industry_id):
        return read_industry_news(industry_id)

    config = industry_news_config(industry_id)
    if not config:
        result = {
            "industry_id": industry_id,
            "items": [],
            "last_updated": utc_now_iso(),
            "source": "Yahoo Finance",
            "fetch_status": "not_configured",
            "failed_reason": "no_news_config",
        }
        update_cache(industry_id, result)
        return enrich_news_metrics(result, industry_id)

    try:
        items = fetch_yfinance_news(industry, config)
        status = "available" if items else "no_recent_news"
        failed_reason = str(config.get("_failed_reason") or "")
        if not items and failed_reason:
            status = "fetch_failed"
        result = {
            "industry_id": industry_id,
            "items": items[:MAX_NEWS_PER_INDUSTRY],
            "last_updated": utc_now_iso(),
            "source": "Yahoo Finance",
            "fetch_status": status,
            "failed_reason": failed_reason,
        }
    except Exception as exc:  # pragma: no cover - provider fallback
        result = {
            "industry_id": industry_id,
            "items": [],
            "last_updated": utc_now_iso(),
            "source": "Yahoo Finance",
            "fetch_status": "fetch_failed",
            "failed_reason": str(exc),
        }
    update_cache(industry_id, result)
    return enrich_news_metrics(result, industry_id)


def update_cache(industry_id: str, result: dict[str, Any]) -> None:
    """Update one industry entry in local cache."""

    cache = load_news_cache()
    cache.setdefault("industries", {})[industry_id] = result
    save_news_cache(cache)


def cached_news_is_fresh(industry_id: str) -> bool:
    """Return whether one industry's cached news is still within the TTL."""

    cached = load_news_cache().get("industries", {}).get(industry_id)
    if not cached:
        return False
    updated = parse_news_time(cached.get("last_updated"))
    if updated is None:
        return False
    return datetime.now(timezone.utc) - updated <= timedelta(hours=NEWS_CACHE_TTL_HOURS)


def industry_news_config(industry_id: str) -> dict[str, Any]:
    """Return keywords and representative tickers for one industry."""

    industry = next((item for item in industryTrendData if item.get("id") == industry_id), None)
    if not industry:
        return {}
    mapping = INDUSTRY_MARKET_TICKERS.get(industry_id, {})
    unstable_tickers = set(mapping.get("unstable_tickers", []))
    tickers = [
        ticker
        for ticker in [*mapping.get("etfs", []), *mapping.get("leaders", [])]
        if ticker and ticker not in unstable_tickers
    ][:MAX_TICKERS_PER_FETCH]
    keywords = [
        str(industry.get("name", "")),
        str(industry.get("chineseName", "")),
        *[str(alias) for alias in industry.get("aliases", [])],
        *NEWS_KEYWORDS.get(industry_id, []),
    ]
    return {
        "tickers": [ticker for ticker in tickers if ticker],
        "keywords": unique_keep_order([keyword for keyword in keywords if keyword]),
    }


def fetch_yfinance_news(industry: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch public news from yfinance Ticker.news for configured tickers."""

    if yf is None:
        raise RuntimeError("yfinance is not available")
    industry_id = str(industry.get("id", ""))
    items = []
    failures = []
    for ticker in config.get("tickers", [])[:MAX_TICKERS_PER_FETCH]:
        ticker_news, failure = quiet_ticker_news_result(ticker)
        if failure:
            failures.append(f"{ticker}: {failure}")
            continue
        for raw_item in ticker_news:
            item = normalize_yfinance_news_item(raw_item, industry_id, ticker, config.get("keywords", []))
            if item:
                items.append(item)
    if failures:
        config["_failed_reason"] = "; ".join(failures[:3])
    items = dedupe_news_items(items)
    return sorted(items, key=lambda row: row.get("published_at") or "", reverse=True)[:MAX_NEWS_PER_INDUSTRY]


def quiet_ticker_news(ticker: str) -> list[dict[str, Any]]:
    """Read yfinance news while suppressing provider stdout/stderr."""

    news, _failure = quiet_ticker_news_result(ticker)
    return news


def quiet_ticker_news_result(ticker: str) -> tuple[list[dict[str, Any]], str]:
    """Read one ticker's news and return a short normalized failure reason."""

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            news = yf.Ticker(ticker).news
    except Exception:
        return [], "Yahoo Finance returned no news data"
    if not isinstance(news, list):
        return [], "Yahoo Finance returned no news data"
    return news, ""


def normalize_yfinance_news_item(
    raw_item: dict[str, Any],
    industry_id: str,
    ticker: str,
    keywords: list[str],
) -> dict[str, Any] | None:
    """Normalize yfinance news item to the project schema."""

    content = raw_item.get("content") if isinstance(raw_item.get("content"), dict) else raw_item
    title = str(content.get("title") or raw_item.get("title") or "")
    if not title:
        return None
    link = extract_news_link(content, raw_item)
    publisher = str(content.get("provider", {}).get("displayName") or raw_item.get("publisher") or "")
    published_at = normalize_news_time(content.get("pubDate") or raw_item.get("providerPublishTime"))
    matched = match_keywords(title, keywords)
    item = {
        "id": stable_news_id(industry_id, title, link),
        "industry_id": industry_id,
        "title": title,
        "publisher": publisher,
        "link": link,
        "published_at": published_at,
        "related_tickers": [ticker],
        "matched_keywords": matched,
        "source": "Yahoo Finance",
        "language": "en",
    }
    return ensure_news_relevance(item, industry_id, keywords)


def extract_news_link(content: dict[str, Any], raw_item: dict[str, Any]) -> str:
    """Extract a usable news URL from yfinance variants."""

    click_url = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    canonical_url = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    return str(
        click_url.get("url")
        or canonical_url.get("url")
        or raw_item.get("link")
        or raw_item.get("url")
        or ""
    )


def normalize_news_time(value: object) -> str:
    """Normalize provider time to ISO string."""

    if value is None:
        return ""
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    raw = str(value)
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return raw


def dedupe_news_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate by link first, then normalized title."""

    seen = set()
    output = []
    for item in items:
        key = item.get("link") or normalize_title(str(item.get("title", "")))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def normalize_title(title: str) -> str:
    """Normalize title for duplicate detection."""

    return re.sub(r"[\s\W_]+", "", title.lower())


def match_keywords(title: str, keywords: list[str]) -> list[str]:
    """Simple keyword match against title text."""

    lower_title = title.lower()
    matched = [keyword for keyword in keywords if keyword and str(keyword).lower() in lower_title]
    return unique_keep_order([str(keyword) for keyword in matched])


def ensure_news_relevance(
    item: dict[str, Any],
    industry_id: str,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Backfill keyword matches and relevance fields for fetched or cached news."""

    output = dict(item)
    config_keywords = keywords if keywords is not None else industry_news_config(industry_id).get("keywords", [])
    matched = output.get("matched_keywords") if isinstance(output.get("matched_keywords"), list) else []
    if not matched:
        matched = match_keywords(str(output.get("title", "")), config_keywords)
    output["matched_keywords"] = matched
    relevance, reason = is_news_relevant_to_industry(output, industry_id, config_keywords, output.get("related_tickers") or [])
    output["relevance"] = relevance
    output["relevance_reason"] = reason
    return output


def is_news_relevant_to_industry(
    news_item: dict[str, Any],
    industry_id: str,
    industry_keywords: list[str],
    related_tickers: list[str],
) -> tuple[str, str]:
    """Classify whether a ticker-feed news item is industry-relevant enough for default display."""

    title = str(news_item.get("title", ""))
    matched = news_item.get("matched_keywords") or match_keywords(title, industry_keywords)
    if matched:
        return "high", "title_keyword_match"
    if title_has_low_relevance_pattern(title):
        return "low", "generic_or_unrelated_title"
    if related_tickers:
        return "low", "ticker_feed_without_industry_keyword"
    return "low", "no_industry_keyword_match"


def title_has_low_relevance_pattern(title: str) -> bool:
    """Detect broad market or unrelated company titles that often appear in ticker feeds."""

    lower_title = title.lower()
    return any(pattern in lower_title for pattern in LOW_RELEVANCE_TITLE_PATTERNS)


def enrich_news_metrics(result: dict[str, Any], industry_id: str) -> dict[str, Any]:
    """Add simple V4.2 news metrics without changing V4.1 framework scores."""

    raw_items = result.get("items") if isinstance(result.get("items"), list) else []
    config = industry_news_config(industry_id)
    items_with_relevance = [
        ensure_news_relevance(item, industry_id, config.get("keywords", []))
        for item in raw_items
        if isinstance(item, dict)
    ]
    items = [
        item
        for item in items_with_relevance
        if item.get("relevance") in {"high", "medium"}
    ]
    low_relevance_items = [
        item
        for item in items_with_relevance
        if item.get("relevance") == "low"
    ]
    now = datetime.now(timezone.utc)
    parsed_times = [parse_news_time(item.get("published_at")) for item in items]
    valid_times = [value for value in parsed_times if value is not None]
    count_24h = sum(1 for value in valid_times if now - value <= timedelta(hours=24))
    count_7d = sum(1 for value in valid_times if now - value <= timedelta(days=7))
    latest = max(valid_times).isoformat() if valid_times else ""
    status = result.get("fetch_status") or ("available" if items else "no_recent_news")
    if status == "available" and not items:
        status = "no_recent_news"
    if status not in LIVE_NEWS_STATUS:
        status = "fetch_failed"
    output = dict(result)
    output.update(
        {
            "industry_id": industry_id,
            "items": items[:MAX_NEWS_PER_INDUSTRY],
            "low_relevance_count": len(low_relevance_items),
            "low_relevance_items": low_relevance_items[:MAX_NEWS_PER_INDUSTRY],
            "news_count_24h": count_24h,
            "news_count_7d": count_7d,
            "latest_news_time": latest,
            "live_news_status": status,
            "live_news_count_7d": count_7d,
            "live_news_last_updated": result.get("last_updated", ""),
        }
    )
    return output


def parse_news_time(value: object) -> datetime | None:
    """Parse an ISO time for metric calculation."""

    raw = str(value or "")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def stable_news_id(industry_id: str, title: str, link: str) -> str:
    """Create stable news id."""

    digest = hashlib.sha1(f"{industry_id}|{title}|{link}".encode("utf-8")).hexdigest()[:16]
    return f"{industry_id}_{digest}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
