"""Markdown report generation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


def generate_markdown_report(
    risk_table: pd.DataFrame,
    assets: list[dict],
    market_regime: str,
    market_reason: str,
    dca_decision: dict | None = None,
    news_digest: dict | None = None,
    report_dir: str | Path = "reports",
) -> Path:
    """Generate a daily Markdown report and return its path."""

    # 报告目录不存在时自动创建，保证一键运行顺利完成。
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    # 使用当前日期命名报告，方便按天归档。
    today = date.today().isoformat()
    report_path = report_dir / f"daily_risk_report_{today}.md"

    # 建立 symbol 到资产配置的映射，用来补充中文名称和主题。
    asset_map = {asset["symbol"]: asset for asset in assets}

    # 拼接 Markdown 内容，保持报告可读且便于版本管理。
    lines = [
        f"# Global QDII Risk Monitor Daily Report - {today}",
        "",
        "## 总体风险状态",
        "",
        f"- 市场状态：**{market_regime}**",
        f"- 观察说明：{market_reason}",
        "",
        "本报告只提供研究观察和风险提示，不包含自动交易或下单建议。",
        "",
        "## 我的每日定投决策",
        "",
        *_build_dca_decision_lines(dca_decision),
        "",
        *_build_news_digest_lines(news_digest),
        "",
        "## 市场结构解读",
        "",
        *_build_market_structure_lines(risk_table),
        "",
        "## 对我的持仓含义",
        "",
        *_build_holding_implication_lines(risk_table),
        "",
        "## 今日观察清单",
        "",
        *_build_watchlist_lines(risk_table),
        "",
        "## 资产风险观察",
        "",
        "| 资产 | 代码 | 主题 | 最新日期 | 最新价格 | 日涨跌 | RSI | 当前回撤 | 最大回撤 | 数据质量 | 风险状态 | 说明 |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]

    # 逐行写入资产观察表，缺失值会显示为 N/A。
    for _, row in risk_table.iterrows():
        asset = asset_map.get(row["symbol"], {})
        lines.append(
            "| {name} | {symbol} | {theme} | {last_date} | {last_price} | {daily_return} | "
            "{rsi} | {latest_drawdown} | {max_drawdown} | {quality} | {regime} | {reason} |".format(
                name=asset.get("name", row["symbol"]),
                symbol=row["symbol"],
                theme=asset.get("theme", ""),
                last_date=row.get("last_date", ""),
                last_price=_format_number(row.get("last_price")),
                daily_return=_format_percent(row.get("daily_return")),
                rsi=_format_number(row.get("rsi")),
                latest_drawdown=_format_percent(row.get("latest_drawdown")),
                max_drawdown=_format_percent(row.get("max_drawdown")),
                quality=row.get("data_quality", ""),
                regime=row.get("risk_regime", ""),
                reason=row.get("risk_reason", ""),
            )
        )

    lines.extend(
        [
            "",
            "## 风险提示",
            "",
            "- QDII 基金可能受海外市场交易时间、汇率、额度、溢价率和节假日影响。",
            "- 黄金、美元、美债与股票资产的相关性会阶段性变化，不能机械理解为固定对冲。",
            "- 半导体、CPO、AI 算力和比特币波动较高，主题热度变化可能放大回撤。",
            "- 数据源可能延迟或缺失；当数据质量不是 fresh 时，应降低结论权重。",
            "",
        ]
    )

    # 使用 UTF-8 写入，确保中文报告正常显示。
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _format_number(value) -> str:
    """Format numeric values for Markdown tables."""

    if pd.isna(value):
        return "N/A"

    return f"{float(value):.2f}"


def _format_percent(value) -> str:
    """Format decimal returns as percentages."""

    if pd.isna(value):
        return "N/A"

    return f"{float(value) * 100:.2f}%"


def _build_dca_decision_lines(dca_decision: dict | None) -> list[str]:
    """Build the daily DCA decision section."""

    # 没有决策结果时保持报告可生成，避免影响原有风险日报流程。
    if not dca_decision:
        return [
            "- 今日模式：暂无",
            "- 今日建议总定投金额：暂无",
            "- 是否使用机动资金：否",
            "- 说明：未生成每日定投决策。此报告仍仅用于研究观察和风险提示。",
        ]

    lines = [
        f"- 今日模式：{dca_decision['mode']}",
        f"- 今日建议总定投金额：¥{dca_decision['suggested_daily_total']:.2f}",
        f"- 是否使用机动资金：{'是' if dca_decision['use_tactical_cash'] else '否'}",
        f"- 机动资金建议使用金额：¥{dca_decision['tactical_cash_amount']:.2f}",
        f"- 今日主攻方向：{'、'.join(dca_decision['main_directions'])}",
        f"- 今日不适合加速的方向：{'、'.join(dca_decision['blocked_directions'])}",
        f"- 黄金是否需要补仓：{dca_decision['gold_action']}",
        f"- 当前组合是否接近 -20% 风险阈值：{'是' if dca_decision['near_drawdown_limit'] else '否'}",
        f"- 今日一句话结论：{dca_decision['one_sentence']}",
        f"- 模式判断原因：{'；'.join(dca_decision['mode_reasons'])}",
        f"- 新闻联动提示：{'；'.join(dca_decision.get('news_link_notes', []))}",
        f"- 新闻联动动作标签：{', '.join(dca_decision.get('news_action_tags', []))}",
        "",
        "### 每只基金今日建议金额",
        "",
        "| 基金 | 代码 | 主题 | 基础金额 | 今日建议金额 | 原因 |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]

    for item in dca_decision["fund_plan"]:
        lines.append(
            "| {fund_name} | {fund_code} | {theme} | ¥{base:.2f} | ¥{suggested:.2f} | {reason} |".format(
                fund_name=item["fund_name"],
                fund_code=item["fund_code"],
                theme=item["theme"],
                base=item["base_daily_dca"],
                suggested=item["suggested_daily_dca"],
                reason=item["reason"],
            )
        )

    lines.extend(
        [
            "",
            "### 机动资金说明",
            "",
            f"- 触发原因：{dca_decision['tactical_cash_reason']}",
            f"- 使用方向：{dca_decision['tactical_cash_target']}",
            f"- 使用金额：¥{dca_decision['tactical_cash_amount']:.2f}",
            f"- 使用后剩余机动资金：¥{dca_decision['tactical_cash_remaining']:.2f}",
            f"- 风险提示：{dca_decision['tactical_cash_risk']}",
            "",
            f"> {dca_decision['disclaimer']}",
        ]
    )

    return lines


def _build_news_digest_lines(news_digest: dict | None) -> list[str]:
    """Build news digest lines for the daily risk report."""

    if not news_digest:
        return [
            "## 每日投资资讯摘要",
            "",
            "- 今日未生成新闻摘要。新闻仅作为研究辅助，不构成投资建议。",
        ]

    lines = [
        "## 每日投资资讯摘要",
        "",
        "新闻只作为研究辅助，可能存在延迟、误报或来源偏差；不构成投资建议，不自动交易。",
        "",
        "### 今日一句话结论",
        "",
        news_digest.get("one_sentence", "今日新闻对定投框架影响有限。"),
        "",
        "### 今日最重要的3条新闻",
        "",
        *_format_news_items(news_digest.get("top_items", [])),
        "",
        "### 半导体 / CPO / CPU 资讯",
        "",
        *_format_news_items(_filter_news_items(news_digest.get("items", []), ["semiconductor", "cpo", "cpu"])),
        "",
        "### 黄金 / 美元 / 美债资讯",
        "",
        *_format_news_items(_filter_news_items(news_digest.get("items", []), ["gold", "macro"])),
        "",
        "### QDII / 汇率 / 溢价风险",
        "",
        *_format_news_items(_filter_news_items(news_digest.get("items", []), ["qdii"])),
        "",
        "### 碳化硅观察池",
        "",
        *_format_news_items(_filter_news_items(news_digest.get("items", []), ["sic"])),
        "",
        "### 对我今日定投的影响",
        "",
        *_build_news_dca_impact_lines(news_digest),
        "",
        "### 噪音新闻过滤说明",
        "",
        f"- {news_digest.get('noise_filter_note', '已过滤低相关资讯。')}",
    ]
    if news_digest.get("errors"):
        lines.extend(["", "### 新闻源异常", "", *[f"- {error}" for error in news_digest["errors"]]])
    return lines


def _format_news_items(items: list[dict]) -> list[str]:
    """Format news items as Markdown bullets."""

    if not items:
        return ["- 暂无匹配资讯。"]
    lines = []
    for item in items[:8]:
        themes = item.get("matched_themes") or item.get("themes") or []
        lines.extend(
            [
                f"- 标题：{item.get('title', '')}",
                f"  - 来源：{item.get('source', '')}",
                f"  - 主题：{', '.join(themes)}",
                f"  - 重要性：{item.get('importance_score', '')}",
                f"  - 摘要：{item.get('summary', '')}",
                f"  - 对我持仓的影响：{item.get('portfolio_impact', '')}",
                f"  - 对今日定投的影响：{item.get('dca_impact', '')}",
                f"  - 动作标签：{item.get('action_tag', '')}",
            ]
        )
    return lines


def _filter_news_items(items: list[dict], themes: list[str]) -> list[dict]:
    """Filter news items by theme."""

    return [
        item
        for item in items
        if any(theme in (item.get("matched_themes") or item.get("themes", [])) for theme in themes)
    ]


def _build_news_dca_impact_lines(news_digest: dict) -> list[str]:
    """Build news-to-DCA impact lines."""

    links = news_digest.get("dca_links", {})
    lines = []
    if links.get("semiconductor_cpo_positive"):
        lines.append("- 半导体 / CPO / CPU 新闻偏积极；若资产 RSI > 70，基本面和情绪虽强但短线不追高。")
        lines.append("- 若同时出现健康回踩，可作为日定投提高到 80-100 元的辅助观察条件。")
    if links.get("dollar_and_yields_strong"):
        lines.append("- 美元和美债收益率同时走强，成长股估值压力上升。")
    if links.get("gold_positive"):
        lines.append("- 黄金相关新闻偏积极；若 GLD 趋势仍弱，只作为防守缓冲分批观察，不追涨。")
    if links.get("sic_major_positive"):
        lines.append("- 碳化硅出现产业链积极信号，加入观察池，不触发自动买入。")
    return lines or ["- 今日新闻没有改变定投辅助框架，继续以价格风险状态和仓位纪律为主。"]


def _build_market_structure_lines(risk_table: pd.DataFrame) -> list[str]:
    """Build market-structure interpretation lines."""

    # 市场结构解读只做相对强弱观察，不给买卖指令。
    equity_score = _average_strength(risk_table, ["SPY", "QQQ", "ACWI", "SMH", "SOXX", "BOTZ"])
    defensive_score = _average_strength(risk_table, ["GLD", "TLT"])
    growth_score = _average_strength(risk_table, ["QQQ", "SMH", "SOXX", "BOTZ"])
    broad_score = _average_strength(risk_table, ["SPY", "ACWI"])
    defense_score = _average_strength(risk_table, ["GLD", "TLT"])
    dollar_score = _average_strength(risk_table, ["UUP"])

    lines = []

    if equity_score > defensive_score + 8:
        lines.append("- 权益资产强于黄金和美债等防御资产，市场结构更偏风险偏好。")
    elif defensive_score > equity_score + 8:
        lines.append("- 防御资产相对强于权益资产，市场结构更偏谨慎。")
    else:
        lines.append("- 权益资产与防御资产强弱接近，市场结构暂未明显倾斜。")

    if growth_score > broad_score + 6:
        lines.append("- 科技成长强于全球宽基，成长风格仍是当前更强的方向。")
    elif broad_score > growth_score + 6:
        lines.append("- 全球宽基强于科技成长，市场风格更偏均衡或防守。")
    else:
        lines.append("- 科技成长与全球宽基强弱接近，风格优势不够明确。")

    if defense_score >= 60:
        lines.append("- 黄金和美债整体仍能提供一定防守观察价值。")
    else:
        lines.append("- 黄金和美债防守信号不足，组合回撤保护需要谨慎评估。")

    if dollar_score >= 70:
        lines.append("- 美元偏强，可能对风险资产形成流动性和估值压力。")
    elif dollar_score <= 40:
        lines.append("- 美元压力偏弱，对风险资产的压制暂不明显。")
    else:
        lines.append("- 美元处于中性区间，对风险资产的压力暂不极端。")

    return lines


def _build_holding_implication_lines(risk_table: pd.DataFrame) -> list[str]:
    """Build implications for the user's holdings."""

    lines = []

    # QQQ、SMH、SOXX 趋势强但 RSI 过热时，强调不宜追高。
    hot_growth_symbols = [
        symbol
        for symbol in ["QQQ", "SMH", "SOXX"]
        if _trend_is_strong(risk_table, symbol) and _value(risk_table, symbol, "rsi") > 70
    ]
    if hot_growth_symbols:
        lines.append(f"- {', '.join(hot_growth_symbols)} 趋势偏强但 RSI 高于 70，短线不宜追高。")

    # 传统防守资产同时 risk-off，说明防守层没有正常发挥。
    if _regime(risk_table, "GLD") == "risk-off" and _regime(risk_table, "TLT") == "risk-off":
        lines.append("- GLD 和 TLT 同时处于 risk-off，传统防守资产偏弱，组合回撤保护不足。")

    # 半导体相对 SPY 更强，提示 AI/半导体主线占优。
    semiconductor_score = _average_strength(risk_table, ["SMH", "SOXX"])
    spy_score = _average_strength(risk_table, ["SPY"])
    if semiconductor_score > spy_score + 5:
        lines.append("- 半导体强于 SPY，AI/半导体主线仍占优。")

    # BTC 回撤超过 30%，明确提示高波动风险。
    btc_drawdown = _value(risk_table, "BTC-USD", "latest_drawdown")
    if btc_drawdown <= -0.30:
        lines.append("- BTC 当前回撤超过 30%，高波动资产风险仍高。")

    if not lines:
        lines.append("- 当前持仓含义以继续观察为主，暂未出现特别突出的单一结构信号。")

    return lines


def _build_watchlist_lines(risk_table: pd.DataFrame) -> list[str]:
    """Build the daily observation checklist."""

    # 观察清单把资产分成几类，帮助用户知道今天该看什么。
    continue_watch = risk_table.loc[
        risk_table["risk_regime"].isin(["risk-on", "neutral"]) & (risk_table["data_quality"] != "missing"),
        "symbol",
    ].tolist()
    overheated = risk_table.loc[risk_table["rsi"].fillna(0) > 70, "symbol"].tolist()
    risk_zone = risk_table.loc[risk_table["risk_regime"] == "risk-off", "symbol"].tolist()
    wait_pullback = risk_table.loc[
        (risk_table["risk_regime"] == "risk-on")
        & (risk_table["rsi"].fillna(0).between(60, 70, inclusive="both"))
        & (risk_table["latest_drawdown"].fillna(0) > -0.05),
        "symbol",
    ].tolist()

    return [
        f"- 可以继续观察：{_join_symbols(continue_watch)}",
        f"- 短线过热：{_join_symbols(overheated)}",
        f"- 处于风险区：{_join_symbols(risk_zone)}",
        f"- 适合等待回踩：{_join_symbols(wait_pullback)}",
    ]


def _average_strength(risk_table: pd.DataFrame, symbols: list[str]) -> float:
    """Calculate an average strength score for a group of symbols."""

    scores = [_strength_score(risk_table, symbol) for symbol in symbols if _has_symbol(risk_table, symbol)]
    if not scores:
        return 50.0

    return sum(scores) / len(scores)


def _strength_score(risk_table: pd.DataFrame, symbol: str) -> float:
    """Convert risk and indicator data into a 0-100 strength score."""

    row = _row(risk_table, symbol)
    if row is None:
        return 50.0

    regime_score = {"risk-on": 75.0, "neutral": 50.0, "risk-off": 25.0}.get(row.get("risk_regime"), 50.0)
    rsi = _coerce_float(row.get("rsi"), 50.0)
    drawdown = _coerce_float(row.get("latest_drawdown"), 0.0)

    # RSI 和回撤微调强弱分，避免只看状态标签。
    score = regime_score + min(max((rsi - 50) * 0.35, -10), 10) + max(drawdown * 100, -15)
    return float(min(max(score, 0), 100))


def _trend_is_strong(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check whether one asset has a strong trend structure."""

    row = _row(risk_table, symbol)
    if row is None:
        return False

    if row.get("risk_regime") == "risk-on":
        return True

    last_price = _coerce_float(row.get("last_price"), 0.0)
    short_ma = _coerce_float(row.get("short_ma"), 0.0)
    long_ma = _coerce_float(row.get("long_ma"), 0.0)
    return last_price > short_ma > long_ma > 0


def _row(risk_table: pd.DataFrame, symbol: str) -> pd.Series | None:
    """Return a row for one symbol."""

    matched = risk_table.loc[risk_table["symbol"] == symbol]
    if matched.empty:
        return None

    return matched.iloc[0]


def _has_symbol(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check whether a symbol exists in the risk table."""

    return not risk_table.loc[risk_table["symbol"] == symbol].empty


def _regime(risk_table: pd.DataFrame, symbol: str) -> str:
    """Return the risk regime for one symbol."""

    row = _row(risk_table, symbol)
    if row is None:
        return ""

    return str(row.get("risk_regime", ""))


def _value(risk_table: pd.DataFrame, symbol: str, column: str) -> float:
    """Return one numeric value from the risk table."""

    row = _row(risk_table, symbol)
    if row is None:
        return 0.0

    return _coerce_float(row.get(column), 0.0)


def _coerce_float(value, default: float) -> float:
    """Convert values to float with a fallback."""

    if pd.isna(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _join_symbols(symbols: list[str]) -> str:
    """Join symbols for report display."""

    if not symbols:
        return "暂无"

    return "、".join(symbols)
