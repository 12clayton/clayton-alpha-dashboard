"""V4.2 lightweight live-news provider for industry trend pages.

This module fetches public Yahoo Finance news through yfinance when explicitly
requested, stores a local JSON cache, and exposes cache-only reads for pages.
It does not summarize, score, or infer investment conclusions.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import hashlib
import io
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from src.industry_market_data import INDUSTRY_MARKET_TICKERS
from src.industry_news_config import get_industry_news_config
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
MAX_GOOGLE_NEWS_QUERIES_PER_INDUSTRY = 3
MAX_ITEMS_PER_GOOGLE_QUERY = 5
LOW_RELEVANCE_CACHE_LIMIT = 5
LOW_RELEVANCE_PER_SOURCE_LIMIT = 5

CPO_QUERY_CONTEXT_TERMS = [
    "optical",
    "optics",
    "photonics",
    "transceiver",
    "interconnect",
    "cpo",
    "co-packaged",
    "lpo",
    "800g",
    "1.6t",
    "光模块",
    "硅光",
    "光互连",
]

ENABLE_YAHOO_NEWS = True
ENABLE_GOOGLE_NEWS_RSS = True
ENABLE_CHINESE_NEWS_RSS = False

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
    "source_name",
    "source_type",
    "source_quality",
    "language",
]

LIVE_NEWS_STATUS = {"available", "no_recent_news", "fetch_failed", "not_configured"}
RELEVANCE_LEVELS = {"high", "medium", "low"}
RELEVANCE_SORT_RANK = {"high": 0, "medium": 1, "low": 2}

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

GOOGLE_NEWS_QUERIES: dict[str, list[str]] = {
    "semiconductor": [
        "semiconductor AI chip",
        "HBM Micron Nvidia",
        "advanced packaging TSMC",
    ],
    "cpo_optical_module": [
        "optical module 800G",
        "co-packaged optics CPO",
        "silicon photonics data center",
    ],
    "gold": [
        "gold real yields",
        "gold central bank buying",
        "gold dollar treasury yields",
    ],
    "real_estate": [
        "REITs interest rates",
        "commercial real estate refinancing",
        "real estate occupancy rates",
    ],
    "liquor": [
        "baijiu channel inventory",
        "premium liquor consumption",
        "China liquor wholesale price",
    ],
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


@dataclass
class NewsProviderResult:
    """Normalized provider output for one industry refresh."""

    provider_name: str
    source_type: str
    source_quality: str
    items: list[dict[str, Any]]
    fetch_status: str = "available"
    failed_reason: str = ""


class YahooFinanceNewsProvider:
    """Yahoo Finance ticker-news provider backed by yfinance."""

    provider_name = "Yahoo Finance"
    source_type = "ticker_news"
    source_quality = "medium"

    def fetch(self, industry: dict[str, Any], config: dict[str, Any]) -> NewsProviderResult:
        try:
            items = fetch_yfinance_news(industry, config)
            failed_reason = str(config.get("_failed_reason") or "")
            status = "available" if items else "no_recent_news"
            if not items and failed_reason:
                status = "fetch_failed"
            return NewsProviderResult(
                provider_name=self.provider_name,
                source_type=self.source_type,
                source_quality=self.source_quality,
                items=items,
                fetch_status=status,
                failed_reason=failed_reason,
            )
        except Exception as exc:  # pragma: no cover - provider fallback
            return NewsProviderResult(
                provider_name=self.provider_name,
                source_type=self.source_type,
                source_quality=self.source_quality,
                items=[],
                fetch_status="fetch_failed",
                failed_reason=str(exc),
            )


class GoogleNewsRSSProvider:
    """Google News RSS search provider using industry keyword queries."""

    provider_name = "Google News RSS"
    source_type = "search_rss"
    source_quality = "medium"

    def fetch(self, industry: dict[str, Any], config: dict[str, Any]) -> NewsProviderResult:
        industry_id = str(industry.get("id", ""))
        queries = config.get("search_queries") or build_google_news_queries(industry_id, config.get("keywords", []))
        if not queries:
            return NewsProviderResult(
                provider_name=self.provider_name,
                source_type=self.source_type,
                source_quality=self.source_quality,
                items=[],
                fetch_status="not_configured",
                failed_reason="no_google_news_query",
            )
        items: list[dict[str, Any]] = []
        failures: list[str] = []
        for query in queries[:MAX_GOOGLE_NEWS_QUERIES_PER_INDUSTRY]:
            query_items, failure = fetch_google_news_rss(industry_id, query, config.get("keywords", []))
            if failure:
                failures.append(f"{query}: {failure}")
            items.extend(query_items[:MAX_ITEMS_PER_GOOGLE_QUERY])
        items = dedupe_news_items(items)
        status = "available" if items else "no_recent_news"
        if not items and failures:
            status = "fetch_failed"
        return NewsProviderResult(
            provider_name=self.provider_name,
            source_type=self.source_type,
            source_quality=self.source_quality,
            items=items[:MAX_NEWS_PER_INDUSTRY],
            fetch_status=status,
            failed_reason="; ".join(failures[:3]),
        )


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
            "source": "",
            "source_names": [],
            "source_types": [],
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
            "source": "",
            "source_names": [],
            "source_types": [],
            "fetch_status": "not_configured",
            "failed_reason": "no_news_config",
        }
        update_cache(industry_id, result)
        return enrich_news_metrics(result, industry_id)

    provider_results = fetch_news_from_enabled_providers(industry, config)
    all_items: list[dict[str, Any]] = []
    failed_reasons: list[str] = []
    provider_names: list[str] = []
    provider_types: list[str] = []
    for provider_result in provider_results:
        provider_names.append(provider_result.provider_name)
        provider_types.append(provider_result.source_type)
        all_items.extend(provider_result.items)
        if provider_result.failed_reason:
            failed_reasons.append(f"{provider_result.provider_name}: {provider_result.failed_reason}")

    items = rank_and_limit_news_items(all_items, industry_id, config.get("keywords", []))
    status = "available" if items else "no_recent_news"
    if not items and failed_reasons:
        status = "fetch_failed"
    result = {
        "industry_id": industry_id,
        "items": items,
        "last_updated": utc_now_iso(),
        "source": ", ".join(unique_keep_order(provider_names)),
        "source_names": unique_keep_order(provider_names),
        "source_types": unique_keep_order(provider_types),
        "fetch_status": status,
        "failed_reason": "; ".join(failed_reasons[:4]),
    }
    update_cache(industry_id, result)
    return enrich_news_metrics(result, industry_id)


def rank_and_limit_news_items(
    items: list[dict[str, Any]],
    industry_id: str,
    keywords: list[str],
) -> list[dict[str, Any]]:
    """Re-rank merged provider items by relevance before final cache truncation."""

    relevant_items = [
        ensure_news_relevance(item, industry_id, keywords)
        for item in items
        if isinstance(item, dict)
    ]
    deduped_items = dedupe_news_items(relevant_items)
    ranked_items = sorted(deduped_items, key=news_cache_sort_key)
    high_medium_items = [
        item
        for item in ranked_items
        if item.get("relevance") in {"high", "medium"}
    ]
    if len(high_medium_items) >= MAX_NEWS_PER_INDUSTRY:
        return high_medium_items[:MAX_NEWS_PER_INDUSTRY]

    output = list(high_medium_items)
    low_by_source: dict[str, int] = {}
    low_kept = 0
    for item in ranked_items:
        if item.get("relevance") != "low":
            continue
        if low_kept >= LOW_RELEVANCE_CACHE_LIMIT or len(output) >= MAX_NEWS_PER_INDUSTRY:
            break
        source_name = str(item.get("source_name") or item.get("source") or "unknown")
        if low_by_source.get(source_name, 0) >= LOW_RELEVANCE_PER_SOURCE_LIMIT:
            continue
        output.append(item)
        low_kept += 1
        low_by_source[source_name] = low_by_source.get(source_name, 0) + 1
    return output


def news_cache_sort_key(item: dict[str, Any]) -> tuple[int, float]:
    """Sort high/medium first, newest first within each relevance level."""

    relevance = str(item.get("relevance") or "low")
    parsed = parse_news_time(item.get("published_at"))
    timestamp = parsed.timestamp() if parsed is not None else 0.0
    return (RELEVANCE_SORT_RANK.get(relevance, RELEVANCE_SORT_RANK["low"]), -timestamp)


def fetch_news_from_enabled_providers(industry: dict[str, Any], config: dict[str, Any]) -> list[NewsProviderResult]:
    """Fetch one industry from all enabled news providers."""

    providers = []
    if ENABLE_YAHOO_NEWS:
        providers.append(YahooFinanceNewsProvider())
    if ENABLE_GOOGLE_NEWS_RSS:
        providers.append(GoogleNewsRSSProvider())
    results: list[NewsProviderResult] = []
    for provider in providers:
        try:
            results.append(provider.fetch(industry, config))
        except Exception as exc:  # pragma: no cover - defensive provider isolation
            results.append(
                NewsProviderResult(
                    provider_name=getattr(provider, "provider_name", "Unknown"),
                    source_type=getattr(provider, "source_type", "unknown"),
                    source_quality=getattr(provider, "source_quality", "low"),
                    items=[],
                    fetch_status="fetch_failed",
                    failed_reason=str(exc),
                )
            )
    return results


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
    configured = get_industry_news_config(industry_id)
    mapping = INDUSTRY_MARKET_TICKERS.get(industry_id, {})
    unstable_tickers = set(mapping.get("unstable_tickers", []))
    tickers = [
        ticker
        for ticker in [*mapping.get("etfs", []), *mapping.get("leaders", [])]
        if ticker and ticker not in unstable_tickers
    ][:MAX_TICKERS_PER_FETCH]
    fallback_keywords = [
        str(industry.get("name", "")),
        str(industry.get("chineseName", "")),
        *[str(alias) for alias in industry.get("aliases", [])],
        *NEWS_KEYWORDS.get(industry_id, []),
    ]
    relevance_keywords = [str(keyword) for keyword in configured.get("relevance_keywords", [])]
    keywords = [*relevance_keywords, *fallback_keywords]
    return {
        "tickers": [ticker for ticker in tickers if ticker],
        "keywords": unique_keep_order([keyword for keyword in keywords if keyword]),
        "search_queries": unique_keep_order([str(query) for query in configured.get("search_queries", []) if query]),
        "relevance_keywords": unique_keep_order([keyword for keyword in relevance_keywords if keyword]),
        "exclude_keywords": unique_keep_order([str(keyword) for keyword in configured.get("exclude_keywords", []) if keyword]),
        "coverage_notes": str(configured.get("coverage_notes", "")),
        "coverage_notes_zh": str(configured.get("coverage_notes_zh", "")),
        "preferred_sources": list(configured.get("preferred_sources", [])),
        "has_news_config": bool(configured),
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
        "source_name": "Yahoo Finance",
        "source_type": "ticker_news",
        "source_quality": "medium",
        "language": "en",
    }
    return ensure_news_relevance(item, industry_id, keywords)


def build_google_news_queries(industry_id: str, keywords: list[str]) -> list[str]:
    """Build a small set of Google News RSS queries for one industry."""

    configured_queries = get_industry_news_config(industry_id).get("search_queries", [])
    if configured_queries:
        return limit_google_news_queries(industry_id, [str(query) for query in configured_queries if query])
    configured = GOOGLE_NEWS_QUERIES.get(industry_id)
    if configured:
        return limit_google_news_queries(industry_id, configured)
    cleaned = [
        keyword
        for keyword in keywords
        if keyword
        and len(str(keyword)) >= 3
        and not re.search(r"[\u4e00-\u9fff]", str(keyword))
    ]
    return limit_google_news_queries(industry_id, [str(keyword) for keyword in cleaned])


def limit_google_news_queries(industry_id: str, queries: list[str]) -> list[str]:
    """Apply provider query limits and CPO-specific context filtering."""

    filtered = [
        query
        for query in unique_keep_order([str(query) for query in queries if query])
        if not cpo_query_without_optical_context(industry_id, query)
    ]
    return filtered[:MAX_GOOGLE_NEWS_QUERIES_PER_INDUSTRY]


def cpo_query_without_optical_context(industry_id: str, query: str) -> bool:
    """Return true when a CPO query lacks optical-network context."""

    if industry_id != "cpo_optical_module":
        return False
    lower_query = query.lower()
    return not any(term in lower_query for term in CPO_QUERY_CONTEXT_TERMS)


def fetch_google_news_rss(
    industry_id: str,
    query: str,
    keywords: list[str],
) -> tuple[list[dict[str, Any]], str]:
    """Fetch one Google News RSS query and normalize its news items."""

    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    try:
        xml_text = quiet_urlopen_text(url)
    except Exception:
        return [], "Google News RSS returned no data"
    if not xml_text:
        return [], "Google News RSS returned no data"
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], "Google News RSS returned invalid RSS"
    items: list[dict[str, Any]] = []
    for raw_item in root.findall(".//item")[:MAX_ITEMS_PER_GOOGLE_QUERY]:
        item = normalize_google_rss_item(raw_item, industry_id, keywords)
        if item:
            items.append(item)
    return items, ""


def quiet_urlopen_text(url: str) -> str:
    """Read RSS text while suppressing provider stdout/stderr."""

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 IndustryTrendSearchEngine/1.0"})
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        with urlopen(request, timeout=6) as response:  # noqa: S310 - controlled public RSS URL
            return response.read().decode("utf-8", errors="replace")


def normalize_google_rss_item(
    raw_item: ET.Element,
    industry_id: str,
    keywords: list[str],
) -> dict[str, Any] | None:
    """Normalize Google News RSS item to the project schema."""

    title = text_from_child(raw_item, "title")
    if not title:
        return None
    link = text_from_child(raw_item, "link")
    publisher = ""
    source_node = raw_item.find("source")
    if source_node is not None and source_node.text:
        publisher = source_node.text.strip()
    published_at = normalize_rss_time(text_from_child(raw_item, "pubDate"))
    matched = match_keywords(title, keywords)
    item = {
        "id": stable_news_id(industry_id, title, link),
        "industry_id": industry_id,
        "title": title,
        "publisher": publisher,
        "link": link,
        "published_at": published_at,
        "related_tickers": [],
        "matched_keywords": matched,
        "source": "Google News RSS",
        "source_name": "Google News RSS",
        "source_type": "search_rss",
        "source_quality": "medium",
        "language": infer_news_language(title),
    }
    return ensure_news_relevance(item, industry_id, keywords)


def text_from_child(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def normalize_rss_time(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return normalize_news_time(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def infer_news_language(title: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", title):
        return "zh"
    if title:
        return "en"
    return "unknown"


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

    seen_links = set()
    seen_titles = set()
    output = []
    for item in items:
        link_key = str(item.get("link") or "").strip()
        title_key = normalize_title(str(item.get("title", "")))
        if link_key and link_key in seen_links:
            continue
        if title_key and title_key in seen_titles:
            continue
        if link_key:
            seen_links.add(link_key)
        if title_key:
            seen_titles.add(title_key)
        output.append(item)
    return output


def normalize_title(title: str) -> str:
    """Normalize title for duplicate detection."""

    stripped = re.sub(
        r"\s+[-|]\s+(yahoo finance|reuters|bloomberg|cnbc|marketwatch|the motley fool|investor's business daily|ap news|associated press)$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[\s\W_]+", "", stripped.lower())


def match_keywords(title: str, keywords: list[str]) -> list[str]:
    """Simple keyword match against title text."""

    lower_title = title.lower()
    matched = [keyword for keyword in keywords if keyword and keyword_matches_title(str(keyword), lower_title)]
    return unique_keep_order([str(keyword) for keyword in matched])


def keyword_matches_title(keyword: str, lower_title: str) -> bool:
    """Match phrases by substring and short ASCII terms by token boundary."""

    lower_keyword = keyword.lower()
    if not lower_keyword:
        return False
    if re.fullmatch(r"[a-z0-9]{2,4}", lower_keyword):
        return re.search(rf"(?<![a-z0-9]){re.escape(lower_keyword)}(?![a-z0-9])", lower_title) is not None
    return lower_keyword in lower_title


def ensure_news_relevance(
    item: dict[str, Any],
    industry_id: str,
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Backfill keyword matches and relevance fields for fetched or cached news."""

    output = dict(item)
    config_keywords = keywords if keywords is not None else industry_news_config(industry_id).get("keywords", [])
    output = ensure_news_source_fields(output)
    if not isinstance(output.get("related_tickers"), list):
        output["related_tickers"] = []
    matched = output.get("matched_keywords") if isinstance(output.get("matched_keywords"), list) else []
    if not matched:
        matched = match_keywords(str(output.get("title", "")), config_keywords)
    output["matched_keywords"] = matched
    relevance, reason = is_news_relevant_to_industry(output, industry_id, config_keywords, output.get("related_tickers") or [])
    output["relevance"] = relevance
    output["relevance_reason"] = reason
    return output


def ensure_news_source_fields(item: dict[str, Any]) -> dict[str, Any]:
    """Backfill V4.11 source fields for old cache items."""

    output = dict(item)
    source = str(output.get("source") or "")
    source_name = str(output.get("source_name") or source or "Yahoo Finance")
    related_tickers = output.get("related_tickers") if isinstance(output.get("related_tickers"), list) else []
    output["source"] = source or source_name
    output["source_name"] = source_name
    output["source_type"] = str(output.get("source_type") or ("ticker_news" if related_tickers else "unknown"))
    quality = str(output.get("source_quality") or "medium")
    output["source_quality"] = quality if quality in {"high", "medium", "low"} else "medium"
    output["language"] = str(output.get("language") or infer_news_language(str(output.get("title", ""))))
    return output


def is_news_relevant_to_industry(
    news_item: dict[str, Any],
    industry_id: str,
    industry_keywords: list[str],
    related_tickers: list[str],
) -> tuple[str, str]:
    """Classify whether a ticker-feed news item is industry-relevant enough for default display."""

    title = str(news_item.get("title", ""))
    exclude_keywords = industry_news_config(industry_id).get("exclude_keywords", [])
    if match_keywords(title, exclude_keywords):
        return "low", "configured_exclude_keyword_match"
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
    source_names = unique_keep_order(
        [
            str(item.get("source_name") or item.get("source") or "")
            for item in items_with_relevance
            if item.get("source_name") or item.get("source")
        ]
    )
    source_types = unique_keep_order(
        [
            str(item.get("source_type") or "")
            for item in items_with_relevance
            if item.get("source_type")
        ]
    )
    if not source_names and result.get("source_names"):
        source_names = list(result.get("source_names") or [])
    if not source_types and result.get("source_types"):
        source_types = list(result.get("source_types") or [])
    if not source_names and result.get("source"):
        source_names = [part.strip() for part in str(result.get("source")).split(",") if part.strip()]
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
            "source": result.get("source") or ", ".join(source_names),
            "source_names": source_names,
            "source_types": source_types,
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
