"""Risk regime model for monitored assets."""

from __future__ import annotations

import pandas as pd


def classify_asset_risk(
    indicator_table: pd.DataFrame,
    data_quality: dict[str, str],
    risk_rules: dict,
) -> pd.DataFrame:
    """Classify each asset as risk-on, neutral, or risk-off."""

    rows = []

    # 逐个资产生成风险标签和中文解释，方便报告直接展示。
    for _, row in indicator_table.iterrows():
        symbol = row["symbol"]
        quality = data_quality.get(symbol, "missing")
        regime, reason = _classify_single_asset(row=row, quality=quality, risk_rules=risk_rules)

        risk_row = row.to_dict()
        risk_row["data_quality"] = quality
        risk_row["risk_regime"] = regime
        risk_row["risk_reason"] = reason
        rows.append(risk_row)

    return pd.DataFrame(rows)


def summarize_market_regime(risk_table: pd.DataFrame) -> tuple[str, str]:
    """Summarize the overall market regime from all monitored assets."""

    # 数据缺失较多时，总体状态优先给出谨慎观察。
    missing_count = int((risk_table["data_quality"] == "missing").sum())
    if missing_count > 0:
        return "neutral", f"{missing_count} 个资产缺少有效数据，总体结论降级为观察。"

    # 用 risk-on / risk-off 数量做一个简单的总览，不做交易指令。
    risk_on_count = int((risk_table["risk_regime"] == "risk-on").sum())
    risk_off_count = int((risk_table["risk_regime"] == "risk-off").sum())

    if risk_off_count > risk_on_count:
        return "risk-off", "偏弱资产数量更多，组合观察上应提高风险警惕。"

    if risk_on_count >= risk_off_count + 2:
        return "risk-on", "偏强资产数量明显更多，市场风险偏好相对较高。"

    return "neutral", "强弱信号接近，当前更适合继续观察。"


def _classify_single_asset(row: pd.Series, quality: str, risk_rules: dict) -> tuple[str, str]:
    """Classify one asset using trend, RSI, drawdown, and data quality."""

    # 数据不可用时不做强结论，避免把数据问题误判成市场信号。
    if quality == "missing":
        return "neutral", "缺少有效价格数据，仅保留观察。"

    if quality == "stale":
        return "neutral", "使用缓存数据，信号不新鲜，仅作为参考。"

    # 样本不足导致关键指标为空时，也只输出中性观察。
    if pd.isna(row["short_ma"]) or pd.isna(row["long_ma"]) or pd.isna(row["rsi"]):
        return "neutral", "历史样本不足，均线或 RSI 尚未形成。"

    latest_price = row["last_price"]
    short_ma = row["short_ma"]
    long_ma = row["long_ma"]
    rsi_value = row["rsi"]
    latest_dd = row["latest_drawdown"]

    # 明显跌破长期均线且回撤较深，判定为 risk-off。
    if latest_price < long_ma and latest_dd <= risk_rules.get("risk_off_drawdown", -0.15):
        return "risk-off", "价格低于长期均线且当前回撤较深。"

    # 短期均线低于长期均线，同时 RSI 偏弱，说明动能不足。
    if short_ma < long_ma and rsi_value < risk_rules.get("weak_rsi", 40):
        return "risk-off", "短期趋势弱于长期趋势，RSI 也处于偏弱区间。"

    # 价格站上短长期均线，且 RSI 没有明显过热，判定为 risk-on。
    if latest_price > short_ma > long_ma and rsi_value < risk_rules.get("overheated_rsi", 70):
        return "risk-on", "价格位于短期和长期均线上方，趋势结构偏强。"

    # RSI 过热时不追高，给出中性但带提示的状态。
    if rsi_value >= risk_rules.get("overheated_rsi", 70):
        return "neutral", "RSI 偏高，趋势虽强但短线可能过热。"

    return "neutral", "趋势和动能信号混合，暂未形成明确风险状态。"
