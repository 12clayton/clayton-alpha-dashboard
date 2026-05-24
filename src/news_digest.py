"""Investment news extraction, summarization, and impact analysis."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import pandas as pd
import requests
import yaml


NEWS_SOURCES_PATH = Path("config/news_sources.yaml")
NEWS_KEYWORDS_PATH = Path("config/news_keywords.yaml")
REPORT_DIR = Path("reports")
LOG_DIR = Path("logs")

MAINLINE_THEMES = {"semiconductor", "cpo", "cpu"}
GOLD_MACRO_THEMES = {"gold", "macro"}
SIC_THEMES = {"sic"}
QDII_THEMES = {"qdii"}
HIGH_RELIABILITY_SOURCES = {"Reuters", "Federal Reserve", "FRED", "US Treasury", "CNBC", "MarketWatch", "Yahoo Finance"}
CORE_ASSET_WORDS = {"nvidia", "broadcom", "tsmc", "amd", "asml", "qqq", "nasdaq", "spy", "gld", "btc"}
GENERIC_NOISE_WORDS = {"celebrity", "sports", "movie", "coupon", "lottery", "weather"}
POSITIVE_WORDS = {"beat", "surge", "record", "upgrade", "demand", "approval", "expansion", "rally", "partnership", "growth"}
NEGATIVE_WORDS = {"drop", "fall", "cut", "warning", "delay", "ban", "probe", "lawsuit", "selloff", "weak", "miss"}
MIXED_WORDS = {"but", "however", "mixed", "while", "despite"}
ACTION_TAGS = {
    "maintain_dca",
    "do_not_chase",
    "wait_for_pullback",
    "small_acceleration",
    "watchlist_only",
    "reduce_aggression",
    "ignore_noise",
}


def build_news_digest(
    sources_path: str | Path = NEWS_SOURCES_PATH,
    keywords_path: str | Path = NEWS_KEYWORDS_PATH,
    report_dir: str | Path = REPORT_DIR,
    lookback_hours: int = 24,
) -> dict:
    """Build daily news digest and write Markdown, CSV, and log files."""

    # 每个新闻源独立抓取，任何一个失败都不会中断总流程。
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    sources_config = load_yaml(sources_path)
    keywords = load_yaml(keywords_path)
    sources = [source for source in sources_config.get("sources", []) if source.get("enabled", True)]

    raw_items = []
    errors = []
    for source in sources:
        try:
            raw_items.extend(fetch_source(source, lookback_hours))
        except Exception as exc:
            errors.append(f"{source.get('source_name', 'unknown')}: {exc}")

    analyzed = [analyze_news_item(item, keywords) for item in raw_items]
    deduped, ignored_count = deduplicate_and_filter(analyzed)
    sorted_items = sorted(deduped, key=lambda item: item["importance_score"], reverse=True)
    important_items = [item for item in sorted_items if item["importance_score"] >= 3 and item["action_tag"] != "ignore_noise"]

    digest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "lookback_hours": lookback_hours,
        "source_count": len(sources),
        "items": important_items,
        "top_items": important_items[:3],
        "ignored_noise_count": ignored_count + sum(1 for item in analyzed if item["action_tag"] == "ignore_noise"),
        "errors": errors,
        "one_sentence": build_one_sentence(important_items, errors),
        "theme_summary": build_theme_summary(important_items),
        "dca_links": build_dca_links(important_items),
        "disclaimer": "新闻可能延迟、误报或存在来源偏差，仅用于研究观察和定投辅助，不构成投资建议。",
    }

    md_path = write_news_markdown(digest, report_dir)
    csv_path = write_news_csv(digest, report_dir)
    log_path = write_news_log(digest)
    digest["report_path"] = str(md_path)
    digest["csv_path"] = str(csv_path)
    digest["log_path"] = str(log_path)
    return digest


def load_yaml(path: str | Path) -> dict:
    """Load YAML file."""

    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def fetch_source(source: dict, lookback_hours: int) -> list[dict]:
    """Fetch one configured source."""

    source_type = source.get("source_type", "rss")
    if source_type == "rss":
        return fetch_rss(source, lookback_hours)
    if source_type == "web":
        return fetch_web(source)
    if source_type == "manual":
        return fetch_manual(source)
    return []


def fetch_rss(source: dict, lookback_hours: int) -> list[dict]:
    """Fetch RSS items from the last lookback window."""

    response = requests.get(source["url"], timeout=8, headers={"User-Agent": "Global-QDII-Risk-Monitor/1.0"})
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items = []

    for entry in feed.entries:
        published_at = parse_datetime(entry.get("published") or entry.get("updated") or entry.get("created"))
        if published_at and published_at < cutoff:
            continue
        items.append(
            {
                "title": clean_text(entry.get("title", "")),
                "content": clean_text(entry.get("summary", "")),
                "source": source.get("source_name", ""),
                "source_type": "rss",
                "published_at": published_at.isoformat() if published_at else "",
                "url": entry.get("link", ""),
                "source_themes": source.get("themes", []),
                "language": source.get("language", ""),
            }
        )
    return items


def fetch_web(source: dict) -> list[dict]:
    """Fetch a simple web page title and text snippet."""

    response = requests.get(source["url"], timeout=8, headers={"User-Agent": "Global-QDII-Risk-Monitor/1.0"})
    response.raise_for_status()
    title = extract_html_title(response.text) or source.get("source_name", "Web source")
    text = strip_html(response.text)[:1200]
    return [
        {
            "title": clean_text(title),
            "content": clean_text(text),
            "source": source.get("source_name", ""),
            "source_type": "web",
            "published_at": "",
            "url": source.get("url", ""),
            "source_themes": source.get("themes", []),
            "language": source.get("language", ""),
        }
    ]


def fetch_manual(source: dict) -> list[dict]:
    """Fetch local manual notes, currently supporting QDII premium CSV."""

    path = Path(source.get("url", ""))
    if not path.exists():
        return []
    if path.suffix.lower() != ".csv":
        return []

    data = pd.read_csv(path)
    items = []
    for _, row in data.iterrows():
        title = f"{row.get('fund', 'QDII')} 溢价观察：{row.get('premium_pct', 'N/A')}%"
        content = f"market_price={row.get('market_price', '')}, nav_estimate={row.get('nav_estimate', '')}, note={row.get('note', '')}"
        items.append(
            {
                "title": clean_text(title),
                "content": clean_text(content),
                "source": source.get("source_name", ""),
                "source_type": "manual",
                "published_at": str(row.get("updated_at", "")),
                "url": str(path),
                "source_themes": source.get("themes", []),
                "language": source.get("language", ""),
            }
        )
    return items


def analyze_news_item(item: dict, keywords: dict) -> dict:
    """Analyze one news item into the required structured fields."""

    text = f"{item.get('title', '')} {item.get('content', '')}"
    themes = match_themes(text, keywords, item.get("source_themes", []))
    sentiment = classify_sentiment(text)
    importance = score_importance(item, themes)
    impact_target = classify_impact_target(themes, importance)
    action_tag = decide_action_tag(themes, sentiment, importance, text)
    summary = build_item_summary(item, themes, sentiment, importance, impact_target, action_tag)

    return {
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "published_at": item.get("published_at", ""),
        "url": item.get("url", ""),
        "matched_themes": themes,
        "themes": themes,
        "importance_score": importance,
        "sentiment": sentiment,
        "summary": summary,
        "portfolio_impact": build_portfolio_impact(themes, sentiment),
        "dca_impact": build_dca_impact(themes, sentiment, action_tag),
        "action_tag": action_tag,
        "impact_target": impact_target,
        "related_titles": [],
    }


def match_themes(text: str, keywords: dict, source_themes: list[str]) -> list[str]:
    """Match themes by configured keywords."""

    lowered = text.lower()
    matched = []
    for theme, words in keywords.items():
        if any(str(word).lower() in lowered for word in words):
            matched.append(theme)
    for theme in source_themes:
        if theme not in matched:
            matched.append(theme)
    return matched or ["noise"]


def score_importance(item: dict, themes: list[str]) -> int:
    """Explainable importance scoring system."""

    text = f"{item.get('title', '')} {item.get('content', '')}".lower()
    score = 0
    if MAINLINE_THEMES.intersection(themes):
        score += 3
    if GOLD_MACRO_THEMES.intersection(themes):
        score += 3
    if SIC_THEMES.intersection(themes):
        score += 2
    if any(word in text for word in ["nvidia", "broadcom", "tsmc", "amd", "asml"]):
        score += 3
    if any(word in text for word in CORE_ASSET_WORDS):
        score += 2
    if QDII_THEMES.intersection(themes):
        score += 2
    if any(name.lower() in item.get("source", "").lower() for name in HIGH_RELIABILITY_SOURCES):
        score += 1
    if "noise" in themes or any(word in text for word in GENERIC_NOISE_WORDS) or len(item.get("title", "")) < 12:
        score -= 2
    if not item.get("published_at"):
        score -= 1
    return score


def classify_sentiment(text: str) -> str:
    """Classify sentiment into positive, negative, neutral, or mixed."""

    lowered = text.lower()
    positive = sum(1 for word in POSITIVE_WORDS if word in lowered)
    negative = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    mixed = any(word in lowered for word in MIXED_WORDS)
    if positive and negative or mixed:
        return "mixed"
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def classify_impact_target(themes: list[str], importance: int) -> str:
    """Classify target impacted by the news."""

    if importance <= 0 or "noise" in themes:
        return "噪音"
    if QDII_THEMES.intersection(themes):
        return "QDII / 汇率 / 溢价"
    if "macro" in themes:
        return "宏观流动性"
    if MAINLINE_THEMES.intersection(themes) or "gold" in themes:
        return "我的持仓"
    if "sic" in themes:
        return "我的关注主题"
    return "我的关注主题"


def decide_action_tag(themes: list[str], sentiment: str, importance: int, text: str) -> str:
    """Choose one allowed action tag."""

    lowered = text.lower()
    if importance <= 0 or "noise" in themes:
        return "ignore_noise"
    if "sic" in themes:
        return "watchlist_only"
    if "macro" in themes and any(word in lowered for word in ["yield", "dxy", "dollar", "rate hike"]):
        return "reduce_aggression"
    if MAINLINE_THEMES.intersection(themes) and sentiment == "positive":
        return "wait_for_pullback"
    if MAINLINE_THEMES.intersection(themes) and sentiment in {"negative", "mixed"}:
        return "maintain_dca"
    if "gold" in themes:
        return "maintain_dca"
    if QDII_THEMES.intersection(themes):
        return "maintain_dca"
    return "maintain_dca"


def build_item_summary(item: dict, themes: list[str], sentiment: str, importance: int, impact_target: str, action_tag: str) -> str:
    """Generate compact summary without copying long article text."""

    title = item.get("title", "")
    content = clean_text(item.get("content", ""))
    if content and content != title and len(content) > 40:
        return build_content_based_summary(title, content)
    return build_title_based_summary(title)


def build_content_based_summary(title: str, content: str) -> str:
    """Summarize available article content in natural Chinese."""

    compact = " ".join(content.split())
    if len(compact) > 220:
        compact = compact[:219] + "…"
    return f"这篇新闻主要说：{compact}"


def build_title_based_summary(title: str) -> str:
    """Build a conservative title-level summary when article body is unavailable."""

    lowered = title.lower()
    if "asian shares" in lowered and "oil" in lowered and "ai rally" in lowered:
        return (
            "正文不可用，仅基于标题判断。亚洲股市上涨可能受到油价回落和美股AI板块反弹带动。"
            "这更像市场行情回顾，说明风险偏好改善，但不是单家公司订单或财报催化。"
        )
    if "nvidia" in lowered or "nvda" in lowered:
        return (
            "正文不可用，仅基于标题判断。新闻围绕英伟达或AI芯片链条展开，可能影响GPU、数据中心和半导体情绪。"
            "具体是财报、订单、政策还是股价异动，需要等待更多来源确认。"
        )
    if "broadcom" in lowered or "avgo" in lowered:
        return (
            "正文不可用，仅基于标题判断。新闻围绕博通展开，可能涉及AI ASIC、网络芯片或数据中心互联。"
            "具体影响需要结合正文、订单和业绩指引确认。"
        )
    if "intel" in lowered or "intc" in lowered:
        return (
            "正文不可用，仅基于标题判断。新闻围绕英特尔展开，可能涉及CPU、代工、美国制造或股价异动。"
            "暂不能确认是基本面改善还是短线情绪。"
        )
    if "gold" in lowered or "gld" in lowered or "comex" in lowered:
        return (
            "正文不可用，仅基于标题判断。新闻可能与黄金、美元、实际利率或避险需求有关。"
            "它主要影响黄金防守观察，不直接改变科技主攻方向。"
        )
    return (
        f"正文不可用，仅基于标题判断。标题显示：{title}。"
        "具体事实、公司对象和影响强度需要等待更多来源确认。"
    )


def build_portfolio_impact(themes: list[str], sentiment: str) -> str:
    """Build portfolio impact text."""

    if MAINLINE_THEMES.intersection(themes):
        return "可能影响纳指100 QDII、全球科技、智能科技和 AI/CPO 成长方向的情绪与估值。"
    if "gold" in themes:
        return "可能影响黄金 ETF 联接的防守缓冲价值，但仍需结合 GLD 趋势。"
    if "macro" in themes:
        return "可能通过美元、美债收益率和流动性影响美股科技与 QDII 表现。"
    if "sic" in themes:
        return "进入碳化硅观察池，暂不直接映射到主定投。"
    if "crypto" in themes:
        return "影响高波动风险偏好和 BTC 观察，不直接对应人民币基金操作。"
    if "qdii" in themes:
        return "影响 QDII 溢价、汇率和净值偏离风险。"
    return "与当前持仓相关性较弱。"


def build_dca_impact(themes: list[str], sentiment: str, action_tag: str) -> str:
    """Build DCA impact text."""

    if action_tag == "wait_for_pullback":
        return "主题积极但不直接追高，等待价格回踩和 RSI 降温。"
    if action_tag == "small_acceleration":
        return "若价格也出现健康回踩，可辅助考虑 80-100 元区间。"
    if action_tag == "reduce_aggression":
        return "宏观压力升高，不提高高波动方向定投。"
    if action_tag == "watchlist_only":
        return "加入观察池，不自动纳入主定投。"
    if action_tag == "ignore_noise":
        return "忽略噪音，不影响今日定投。"
    return "维持基础定投框架，继续观察价格和风险状态。"


def deduplicate_and_filter(items: list[dict]) -> tuple[list[dict], int]:
    """Deduplicate news and merge duplicate titles into related_titles."""

    by_key = {}
    ignored = 0
    for item in items:
        key = normalize_title_key(item["title"])
        if not key:
            ignored += 1
            continue
        if key not in by_key:
            by_key[key] = item
            continue
        current = by_key[key]
        if item["importance_score"] > current["importance_score"]:
            item["related_titles"] = current.get("related_titles", []) + [current["title"]]
            by_key[key] = item
        else:
            current.setdefault("related_titles", []).append(item["title"])
    return list(by_key.values()), ignored


def build_theme_summary(items: list[dict]) -> dict:
    """Build theme summary."""

    summary = {}
    for item in items:
        for theme in item["matched_themes"]:
            bucket = summary.setdefault(theme, {"count": 0, "positive": 0, "negative": 0, "important": 0})
            bucket["count"] += 1
            bucket["positive"] += int(item["sentiment"] == "positive")
            bucket["negative"] += int(item["sentiment"] == "negative")
            bucket["important"] += int(item["importance_score"] >= 5)
    return summary


def build_dca_links(items: list[dict]) -> dict:
    """Build signals consumed by DCA engine."""

    action_tags = {item["action_tag"] for item in items}
    titles = " ".join(item["title"].lower() for item in items)
    semi_items = [item for item in items if MAINLINE_THEMES.intersection(item["matched_themes"])]
    return {
        "semiconductor_cpo_positive": any(item["sentiment"] == "positive" for item in semi_items),
        "semiconductor_cpo_important": any(item["importance_score"] >= 5 for item in semi_items),
        "dollar_and_yields_strong": ("dollar" in titles or "dxy" in titles) and ("yield" in titles or "treasury" in titles),
        "gold_positive": any("gold" in item["matched_themes"] and item["sentiment"] == "positive" for item in items),
        "sic_major_positive": any("sic" in item["matched_themes"] and item["importance_score"] >= 5 for item in items),
        "action_tags": sorted(action_tags.intersection(ACTION_TAGS)),
    }


def build_one_sentence(items: list[dict], errors: list[str]) -> str:
    """Build one-sentence conclusion."""

    if not items:
        return "今日未抓取到高重要性投资新闻，定投节奏仍以价格风险状态和仓位纪律为主。"
    top_tags = {item["action_tag"] for item in items[:5]}
    if "reduce_aggression" in top_tags:
        return "今日宏观压力新闻需要关注，成长方向不宜提高进攻性，维持纪律更重要。"
    if "wait_for_pullback" in top_tags:
        return "今日成长主线新闻偏积极，但更适合等待回踩，而不是因为新闻情绪直接追高。"
    if "watchlist_only" in top_tags:
        return "今日有观察池方向新闻，适合记录跟踪，但不改变主定投框架。"
    return "今日新闻对组合的影响以观察为主，维持基础定投框架。"


def write_news_markdown(digest: dict, report_dir: Path) -> Path:
    """Write Markdown digest."""

    today = datetime.now().date().isoformat()
    path = report_dir / f"news_digest_{today}.md"
    path.write_text("\n".join(build_markdown_lines(digest, today)), encoding="utf-8")
    return path


def write_news_csv(digest: dict, report_dir: Path) -> Path:
    """Write CSV digest."""

    today = datetime.now().date().isoformat()
    path = report_dir / f"news_digest_{today}.csv"
    rows = []
    for item in digest["items"]:
        row = item.copy()
        row["matched_themes"] = ",".join(item["matched_themes"])
        row["themes"] = ",".join(item["matched_themes"])
        row["related_titles"] = " || ".join(item.get("related_titles", []))
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def write_news_log(digest: dict) -> Path:
    """Write news digest errors and run metadata to log."""

    today = datetime.now().date().isoformat()
    path = LOG_DIR / f"news_digest_{today}.log"
    lines = [
        f"generated_at={digest['generated_at']}",
        f"source_count={digest['source_count']}",
        f"item_count={len(digest['items'])}",
        f"ignored_noise_count={digest['ignored_noise_count']}",
    ]
    if digest["errors"]:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in digest["errors"])
    else:
        lines.append("errors: none")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_markdown_lines(digest: dict, today: str) -> list[str]:
    """Build Markdown digest lines."""

    return [
        f"# 每日投资新闻摘要 - {today}",
        "",
        "新闻可能延迟、误报或存在来源偏差，不构成投资建议；本系统不自动交易、不连接券商账户。",
        "",
        "## 今日一句话结论",
        "",
        digest["one_sentence"],
        "",
        "## 今日最重要的 3 条新闻",
        "",
        *format_news_blocks(digest["top_items"]),
        "",
        "## 半导体 / CPO / CPU",
        "",
        *format_news_blocks(filter_items(digest["items"], ["semiconductor", "cpo", "cpu"])),
        "",
        "## 黄金 / 美元 / 美债 / 美联储",
        "",
        *format_news_blocks(filter_items(digest["items"], ["gold", "macro"])),
        "",
        "## 碳化硅观察池",
        "",
        *format_news_blocks(filter_items(digest["items"], ["sic"])),
        "",
        "## QDII / 汇率 / 溢价风险",
        "",
        *format_news_blocks(filter_items(digest["items"], ["qdii"])),
        "",
        "## 噪音过滤",
        "",
        f"- 被忽略的低相关新闻数量：{digest['ignored_noise_count']}",
        "",
        "## 今日定投影响总结",
        "",
        *build_dca_summary_lines(digest),
        "",
        f"- 新闻源数量：{digest['source_count']}",
        f"- 抓取时间：{digest['generated_at']}",
    ]


def format_news_blocks(items: list[dict]) -> list[str]:
    """Format structured news blocks."""

    if not items:
        return ["今日无高重要性新闻。"]
    lines = []
    for item in items[:8]:
        lines.extend(
            [
                f"- 标题：{item['title']}",
                f"  - 来源：{item['source']}",
                f"  - 主题：{', '.join(item['matched_themes'])}",
                f"  - 重要性：{item['importance_score']}",
                f"  - 摘要：{item['summary']}",
                f"  - 对我持仓的影响：{item['portfolio_impact']}",
                f"  - 对今日定投的影响：{item['dca_impact']}",
                f"  - 动作标签：{item['action_tag']}",
            ]
        )
    return lines


def build_dca_summary_lines(digest: dict) -> list[str]:
    """Build DCA summary from action tags."""

    tags = set(digest["dca_links"].get("action_tags", []))
    return [
        f"- 是否维持60元基础定投：{'是' if 'reduce_aggression' in tags or not tags else '以价格风险状态为准'}",
        f"- 是否提高到80–100元：{'仅在价格健康回踩时考虑' if 'wait_for_pullback' in tags else '否'}",
        "- 是否动用机动资金：否，新闻不单独触发机动资金使用。",
        f"- 哪些方向不追高：{'半导体 / CPO / CPU' if 'wait_for_pullback' in tags else '暂无明确新闻触发'}",
        f"- 哪些方向等待回踩：{'半导体 / CPO / CPU' if 'wait_for_pullback' in tags else '暂无'}",
        f"- 哪些方向只进观察池：{'碳化硅' if 'watchlist_only' in tags else '暂无'}",
    ]


def filter_items(items: list[dict], themes: list[str]) -> list[dict]:
    """Filter items by themes and importance."""

    return [item for item in items if any(theme in item["matched_themes"] for theme in themes) and item["importance_score"] >= 3]


def analyze_manual_news(raw_text: str, keywords: dict | None = None) -> dict:
    """Analyze pasted URL, title, or article text for Streamlit manual page."""

    keywords = keywords or load_yaml(NEWS_KEYWORDS_PATH)
    input_type = detect_input_type(raw_text)
    fetched_error = ""
    title = clean_text(raw_text)
    content = clean_text(raw_text)
    url = raw_text.strip() if input_type == "URL" else ""

    if input_type == "URL":
        try:
            response = requests.get(url, timeout=8, headers={"User-Agent": "Global-QDII-Risk-Monitor/1.0"})
            response.raise_for_status()
            title = extract_html_title(response.text) or url
            content = strip_html(response.text)[:3000]
        except Exception as exc:
            fetched_error = f"网页抓取失败：{exc}。请粘贴正文。"

    item = {
        "title": title[:220],
        "content": content,
        "source": "Manual Input",
        "source_type": input_type.lower(),
        "published_at": datetime.now().isoformat(timespec="seconds"),
        "url": url,
        "source_themes": [],
        "language": "mixed",
    }
    analysis = analyze_news_item(item, keywords)
    analysis["input_type"] = input_type
    analysis["fetched_error"] = fetched_error
    analysis["is_watchlist"] = analysis["action_tag"] == "watchlist_only"
    analysis["is_noise"] = analysis["action_tag"] == "ignore_noise"
    return analysis


def save_manual_news_note(analysis: dict, report_dir: str | Path = REPORT_DIR) -> Path:
    """Append manual news analysis to daily note file."""

    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    path = report_dir / f"manual_news_notes_{today}.md"
    lines = [
        f"## 手动新闻解析 - {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"- 输入类型：{analysis['input_type']}",
        f"- 标题：{analysis['title']}",
        f"- 涉及主题：{', '.join(analysis['matched_themes'])}",
        f"- 利好/利空方向：{analysis['sentiment']}",
        f"- 文章核心观点：{analysis['summary']}",
        f"- 对我的持仓影响：{analysis['portfolio_impact']}",
        f"- 对今日定投影响：{analysis['dca_impact']}",
        f"- 是否进入观察池：{'是' if analysis['is_watchlist'] else '否'}",
        f"- 是否只是情绪噪音：{'是' if analysis['is_noise'] else '否'}",
        f"- 动作标签：{analysis['action_tag']}",
        "",
        "本解析仅用于研究观察和定投辅助，不构成投资建议，不自动交易。",
        "",
    ]
    with path.open("a", encoding="utf-8") as file:
        file.write("\n".join(lines))
    return path


def detect_input_type(raw_text: str) -> str:
    """Detect whether input is URL, title, or body text."""

    text = raw_text.strip()
    if re.match(r"^https?://", text, flags=re.I):
        return "URL"
    if len(text) <= 180 and "\n" not in text:
        return "标题"
    return "正文文本"


def parse_datetime(value: str | None) -> datetime | None:
    """Parse datetime from RSS/API strings."""

    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(str(value))
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_html_title(html: str) -> str:
    """Extract title from HTML."""

    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return clean_text(match.group(1)) if match else ""


def strip_html(html: str) -> str:
    """Remove scripts, styles, and HTML tags."""

    html = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean_text(html)


def normalize_title_key(title: str) -> str:
    """Normalize title for duplicate detection."""

    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", title.lower())
    words = [word for word in text.split() if len(word) > 2]
    return " ".join(words[:12])


def clean_text(text: str) -> str:
    """Normalize text whitespace."""

    return " ".join(str(text or "").split())
