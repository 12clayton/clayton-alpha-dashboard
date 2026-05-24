"""Public RSS news loader for Streamlit Cloud deployments."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import pandas as pd
import yaml


PUBLIC_GOOGLE_QUERIES = [
    "Nvidia AI semiconductor",
    "Broadcom AI chip",
    "semiconductor CPO optical interconnect",
    "gold dollar real yield",
]

NEWS_COLUMNS = [
    "title",
    "source",
    "published_at",
    "url",
    "summary",
    "raw_text_available",
    "theme_tags",
    "themes",
    "news_type",
    "data_quality",
    "importance_score",
    "sentiment",
    "need_attention",
]


def load_public_news(
    sources_path: Path,
    cache_path: Path | None = None,
    max_items: int = 12,
) -> pd.DataFrame:
    """Load public RSS news and return dashboard-ready rows."""

    sources = build_public_news_sources(sources_path)
    rows = []
    for source in sources:
        rows.extend(fetch_rss_source(source))
    frame = normalize_news_rows(rows)
    if frame.empty and cache_path is not None:
        frame = load_public_news_cache(cache_path)
    elif not frame.empty and cache_path is not None:
        save_public_news_cache(frame, cache_path)
    if frame.empty:
        return pd.DataFrame(columns=NEWS_COLUMNS)
    return frame.sort_values(["importance_score", "published_at"], ascending=[False, False]).head(max_items).reset_index(drop=True)


def build_public_news_sources(sources_path: Path) -> list[dict]:
    """Load configured RSS sources and append public Google News searches."""

    sources = []
    config = load_yaml(sources_path)
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        if str(source.get("source_type", "")).lower() != "rss":
            continue
        sources.append(
            {
                "source_name": source.get("source_name", "RSS"),
                "url": source.get("url", ""),
                "themes": source.get("themes", []),
            }
        )

    sources.extend(
        {
            "source_name": f"Google News - {query}",
            "url": google_news_url(query),
            "themes": [],
        }
        for query in PUBLIC_GOOGLE_QUERIES
    )
    return [source for source in sources if source["url"]]


def fetch_rss_source(source: dict) -> list[dict]:
    """Fetch one RSS source safely."""

    try:
        feed = feedparser.parse(source["url"])
    except Exception:
        return []
    rows = []
    for entry in feed.entries[:8]:
        title = clean_text(entry.get("title", ""))
        if not title:
            continue
        summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
        tags = classify_theme_tags(f"{title} {summary}", source.get("themes", []))
        rows.append(
            {
                "title": title,
                "source": source.get("source_name", "RSS"),
                "published_at": parse_entry_time(entry),
                "url": entry.get("link", ""),
                "summary": build_public_summary(title, summary),
                "raw_text_available": bool(summary),
                "theme_tags": tags,
                "themes": tags,
                "news_type": classify_news_type(f"{title} {summary}"),
                "data_quality": "rss_summary" if summary else "title_only",
                "importance_score": score_public_news(title, summary, tags),
                "sentiment": infer_sentiment(f"{title} {summary}"),
                "need_attention": bool(tags),
            }
        )
    return rows


def normalize_news_rows(rows: list[dict]) -> pd.DataFrame:
    """Deduplicate and normalize RSS rows."""

    if not rows:
        return pd.DataFrame(columns=NEWS_COLUMNS)
    frame = pd.DataFrame(rows)
    for column in NEWS_COLUMNS:
        if column not in frame.columns:
            frame[column] = "" if column not in {"theme_tags", "themes"} else [[] for _ in range(len(frame))]
    frame["_dedupe_key"] = frame["title"].astype(str).map(lambda value: re.sub(r"\W+", "", value.lower())[:120])
    frame = frame.sort_values("importance_score", ascending=False).drop_duplicates("_dedupe_key")
    return frame[NEWS_COLUMNS]


def build_public_summary(title: str, summary: str) -> str:
    """Return honest summary text without pretending to read full articles."""

    if summary:
        return summary[:500]
    return f"正文不可用，仅基于标题判断。以下为标题层面的保守解读：{title}"


def classify_theme_tags(text: str, configured_themes: list[str]) -> list[str]:
    """Map text to public investment themes."""

    lower = text.lower()
    tags = list(configured_themes or [])
    rules = {
        "semiconductor": ["nvidia", "gpu", "blackwell", "ai chip", "semiconductor", "tsmc", "broadcom", "micron"],
        "cpo": ["cpo", "optical", "photonics", "transceiver", "800g", "1.6t", "interconnect", "marvell", "credo", "lumentum", "coherent"],
        "cpu": ["cpu", "asic", "intel", "amd", "arm", "custom silicon"],
        "gold": ["gold", "dollar", "real yield", "treasury", "fed", "inflation", "gld", "uup", "tlt"],
        "macro": ["oil", "inflation", "bond yield", "risk-on", "risk-off", "wall street", "asian shares"],
    }
    for theme, keywords in rules.items():
        if any(keyword in lower for keyword in keywords) and theme not in tags:
            tags.append(theme)
    return tags or ["market"]


def classify_news_type(text: str) -> str:
    """Classify public news type."""

    lower = text.lower()
    if any(keyword in lower for keyword in ["earnings", "revenue", "profit", "guidance", "order", "contract"]):
        return "硬催化"
    if any(keyword in lower for keyword in ["fed", "inflation", "treasury", "dollar", "oil", "yield"]):
        return "宏观环境"
    if any(keyword in lower for keyword in ["surge", "fall", "rally", "slides", "wall street", "asian shares"]):
        return "市场情绪"
    if any(keyword in lower for keyword in ["interview", "says", "conference", "summit"]):
        return "软信号"
    return "软信号"


def score_public_news(title: str, summary: str, tags: list[str]) -> int:
    """Score public news relevance."""

    text = f"{title} {summary}".lower()
    score = 1 + min(len(tags), 4)
    if any(name in text for name in ["nvidia", "broadcom", "tsmc", "amd", "micron"]):
        score += 3
    if any(theme in tags for theme in ["semiconductor", "cpo", "cpu"]):
        score += 2
    if "gold" in tags or "macro" in tags:
        score += 1
    return score


def infer_sentiment(text: str) -> str:
    """Infer lightweight sentiment for compatibility with dashboard cards."""

    lower = text.lower()
    if any(keyword in lower for keyword in ["surge", "rally", "beats", "strong", "record", "jumps"]):
        return "positive"
    if any(keyword in lower for keyword in ["falls", "slides", "miss", "weak", "risk", "warning"]):
        return "negative"
    return "neutral"


def google_news_url(query: str) -> str:
    """Build Google News RSS search URL."""

    return f"https://news.google.com/rss/search?q={quote_plus(query + ' when:2d')}&hl=en-US&gl=US&ceid=US:en"


def parse_entry_time(entry) -> str:
    """Parse RSS published time."""

    raw = entry.get("published", "") or entry.get("updated", "")
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(raw)


def save_public_news_cache(frame: pd.DataFrame, cache_path: Path) -> None:
    """Save public news cache when filesystem is writable."""

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(frame.to_json(orient="records", force_ascii=False), encoding="utf-8")
    except Exception:
        return


def load_public_news_cache(cache_path: Path) -> pd.DataFrame:
    """Load public news cache if available."""

    if not cache_path.exists():
        return pd.DataFrame(columns=NEWS_COLUMNS)
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return normalize_news_rows(data)
    except Exception:
        return pd.DataFrame(columns=NEWS_COLUMNS)


def clean_html(value: str) -> str:
    """Remove HTML tags and collapse whitespace."""

    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return clean_text(text)


def clean_text(value: str) -> str:
    """Normalize text."""

    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_yaml(path: Path) -> dict:
    """Load YAML safely."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
