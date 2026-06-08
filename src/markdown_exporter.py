"""Build daily investment context Markdown for external AI analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_daily_markdown_context(
    *,
    date: str | None = None,
    report_date: str | None = None,
    final_decision: dict[str, Any],
    data_quality_summary: str,
    market_rows: list[dict[str, Any]],
    fund_rows: list[dict[str, Any]],
    news_rows: list[dict[str, Any]],
    theme_rows: list[dict[str, Any]],
    public_mode: bool = False,
) -> str:
    """Build a public/private-safe daily Markdown context."""

    date_text = date or report_date or datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# 每日投资上下文 {date_text}",
        "",
        "## 1. 今日市场状态",
        f"- market_mode: {_safe(final_decision.get('market_mode'))}",
        f"- risk_discipline: {_safe(final_decision.get('risk_discipline'))}",
        f"- one_line_summary: {_safe(final_decision.get('one_line_summary') or final_decision.get('top_summary'))}",
        f"- data_quality_summary: {_safe(data_quality_summary)}",
        "",
        "## 2. 核心资产表现",
        _markdown_table(
            market_rows,
            ["资产", "今日涨跌", "RSI", "距离高点回撤", "1月收益", "3月收益", "数据质量"],
        ),
        "",
        "## 3. 我的持有基金观察",
        _markdown_table(
            fund_rows,
            ["基金名称", "基金代码", "主题", "最新净值日期", "最新单位净值", "基金真实日涨跌幅", "申购/限购状态", "数据质量", "参考市场"],
        ),
        "",
        "## 4. 今日新闻摘要",
    ]

    if news_rows:
        for index, item in enumerate(news_rows, start=1):
            content = _safe(item.get("新闻内容"))
            if item.get("新闻数据质量") == "title_only" and "正文不可用" not in content:
                content = f"正文不可用，仅基于标题判断。{content}"
            lines.extend(
                [
                    f"### 新闻 {index}: {_safe(item.get('标题'))}",
                    f"- 来源: {_safe(item.get('来源'))}",
                    f"- 新闻内容: {content}",
                    f"- 投资解读: {_safe(item.get('投资解读'))}",
                    f"- 对今日动作的影响: {_safe(item.get('对今日动作的影响'))}",
                    f"- 后续观察点: {_safe(item.get('后续观察点'))}",
                    f"- 新闻数据质量: {_safe(item.get('新闻数据质量'))}",
                    "",
                ]
            )
    else:
        lines.extend(["暂无可解析新闻。", ""])

    lines.extend(["## 5. 行业主题观察"])
    if theme_rows:
        for item in theme_rows:
            lines.extend(
                [
                    f"### {_safe(item.get('主题'))}",
                    f"- 当前阶段: {_safe(item.get('当前阶段'))}",
                    f"- 核心驱动: {_safe(item.get('核心驱动'))}",
                    f"- 今日市场信号: {_safe(item.get('今日市场信号'))}",
                    f"- 相关公司: {_safe(item.get('相关公司'))}",
                    f"- 相关基金: {_safe(item.get('相关基金'))}",
                    f"- 数据质量: {_safe(item.get('数据质量'))}",
                    f"- 后续观察点: {_safe(item.get('后续观察点'))}",
                    "",
                ]
            )
    else:
        lines.extend(["暂无行业主题数据。", ""])

    lines.extend(
        [
            "## 6. 今日需要 AI 帮我判断的问题",
            "1. 今天是健康回踩还是急跌冲击？",
            "2. 当前是否适合继续按计划执行？",
            "3. 哪些基金的主题暴露最接近今天的主线？",
            "4. 新闻是否改变了半导体 / CPO / CPU 的中期逻辑？",
            "5. 明天我应该重点观察哪些指标？",
            "",
            "## 7. 重要约束",
            "- 这不是投资建议。",
            "- 回测不是预测未来。",
            "- 新闻不能直接触发买入。",
            "- 任何加仓都要结合风险承受能力和个人资金安排。",
            "- 当前系统不输出具体买入金额，只提供分析上下文。",
            "",
        ]
    )
    if public_mode:
        lines.append("> Public 模式：已隐藏真实持仓金额、具体执行金额、本地路径和 private debug 信息。")
    return "\n".join(lines)


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """Build a Markdown table with stable N/A fallback."""

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    if not rows:
        lines.append("| " + " | ".join(["N/A"] * len(columns)) + " |")
        return "\n".join(lines)
    for row in rows:
        lines.append("| " + " | ".join(_safe(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def _safe(value: Any) -> str:
    """Format a Markdown-safe scalar value."""

    if value is None:
        return "N/A"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return "N/A"
    return text.replace("|", "\\|").replace("\n", " ")
