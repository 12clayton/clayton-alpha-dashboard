"""Daily tactical rules for the Clayton Alpha model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TacticalInputs:
    qqq_rsi: float | None
    smh_rsi: float | None
    qqq_drawdown: float | None
    smh_drawdown: float | None
    qqq_above_ma60: bool | None
    smh_above_ma60: bool | None
    gld_rsi: float | None
    market_risk_status: str
    current_gold_weight: float | None = None
    current_sp500_weight: float | None = None
    fund_deviation: dict[str, float] | None = None


def daily_tactical_engine(inputs: TacticalInputs) -> dict:
    """Return today's tactical mode and execution plan."""

    if _missing_core_data(inputs):
        return _build_result(
            market_mode="normal_dca",
            daily_dca_amount=60,
            tactical_cash_action="不动用灵活加仓资金",
            gold_action="数据不足，执行基础定投；黄金按两周计划观察。",
            fund_allocation=_normal_allocation(),
            explanation=["数据不足，执行基础定投。"],
        )

    qqq_hot = _gt(inputs.qqq_rsi, 70)
    smh_hot = _gt(inputs.smh_rsi, 70)
    qqq_far_above = inputs.qqq_above_ma60 is True and _gt(inputs.qqq_rsi, 68)
    smh_far_above = inputs.smh_above_ma60 is True and _gt(inputs.smh_rsi, 68)
    both_below_ma = inputs.qqq_above_ma60 is False and inputs.smh_above_ma60 is False
    risk_status = str(inputs.market_risk_status or "").lower()
    risk_off = "risk-off" in risk_status or "defense" in risk_status

    if both_below_ma or risk_off:
        return _build_result(
            market_mode="defense_mode",
            daily_dca_amount=60,
            tactical_cash_action="不动用灵活加仓资金",
            gold_action="黄金优先；成长股不加速。",
            fund_allocation={
                "广发纳指100": 10,
                "浦银全球智能科技": 10,
                "国富全球科技互联": 10,
                "易方达全球成长": 15,
                "黄金": 15,
                "标普500": 0,
                "日经225": 0,
            },
            explanation=["QQQ 和 SMH 同时跌破 60 日均线，或市场处于 risk-off。"],
        )

    if qqq_hot or smh_hot or qqq_far_above or smh_far_above:
        return _build_result(
            market_mode="do_not_chase",
            daily_dca_amount=60,
            tactical_cash_action="不动用灵活加仓资金",
            gold_action="按两周计划择时补仓；默认 ¥60，回调明显 ¥90–105，过热时 ¥30 或暂停。",
            fund_allocation={
                "广发纳指100": 10,
                "浦银全球智能科技": 15,
                "国富全球科技互联": 15,
                "易方达全球成长": 20,
                "标普500": 0,
                "日经225": 0,
            },
            explanation=["QQQ 或 SMH RSI 高于 70，或短线偏热；绝不动用灵活资金。"],
        )

    strong = _asset_in_range(inputs.qqq_drawdown, -0.18, -0.10) and _asset_in_range(inputs.qqq_rsi, 35, 50)
    strong = strong or (_asset_in_range(inputs.smh_drawdown, -0.18, -0.10) and _asset_in_range(inputs.smh_rsi, 35, 50))
    trend_not_broken = inputs.qqq_above_ma60 is True or inputs.smh_above_ma60 is True
    if strong and trend_not_broken and not risk_off:
        return _build_result(
            market_mode="strong_opportunity",
            daily_dca_amount=100,
            tactical_cash_action="可考虑使用灵活加仓资金的 10%–20%；分配：半导体/CPO/CPU 60%，纳指100 30%，黄金 10%。",
            gold_action="黄金保留 ¥10 防守补充。",
            fund_allocation={
                "广发纳指100": 10,
                "浦银全球智能科技": 30,
                "国富全球科技互联": 25,
                "易方达全球成长": 25,
                "黄金": 10,
                "标普500": 0,
                "日经225": 0,
            },
            explanation=[_strong_reason(inputs)],
        )

    healthy = _asset_in_range(inputs.qqq_drawdown, -0.10, -0.05) and _asset_in_range(inputs.qqq_rsi, 45, 60)
    healthy = healthy or (_asset_in_range(inputs.smh_drawdown, -0.10, -0.05) and _asset_in_range(inputs.smh_rsi, 45, 60))
    if healthy and trend_not_broken and not risk_off:
        return _build_result(
            market_mode="healthy_pullback",
            daily_dca_amount=80,
            tactical_cash_action="不动用灵活加仓资金",
            gold_action="黄金补 ¥5，保持防守层。",
            fund_allocation={
                "广发纳指100": 10,
                "浦银全球智能科技": 20,
                "国富全球科技互联": 20,
                "易方达全球成长": 25,
                "黄金": 5,
                "标普500": 0,
                "日经225": 0,
            },
            explanation=["QQQ 或 SMH 出现 5%–10% 健康回踩，RSI 处于 45–60，趋势未明显破坏。"],
        )

    return _build_result(
        market_mode="normal_dca",
        daily_dca_amount=60,
        tactical_cash_action="不动用灵活加仓资金",
        gold_action="黄金按两周计划择时，不每日固定。",
        fund_allocation=_normal_allocation(),
        explanation=["QQQ/SMH 未过热、未明显破位，市场风险状态正常。"],
    )


def _normal_allocation() -> dict[str, int]:
    return {
        "广发纳指100": 10,
        "浦银全球智能科技": 15,
        "国富全球科技互联": 15,
        "易方达全球成长": 20,
        "黄金": 0,
        "标普500": 0,
        "日经225": 0,
    }


def _build_result(
    market_mode: str,
    daily_dca_amount: int,
    tactical_cash_action: str,
    gold_action: str,
    fund_allocation: dict[str, int],
    explanation: list[str],
) -> dict:
    return {
        "market_mode": market_mode,
        "daily_dca_amount": daily_dca_amount,
        "tactical_cash_action": tactical_cash_action,
        "gold_action": gold_action,
        "fund_allocation": fund_allocation,
        "explanation": explanation,
    }


def _missing_core_data(inputs: TacticalInputs) -> bool:
    required = [
        inputs.qqq_rsi,
        inputs.smh_rsi,
        inputs.qqq_drawdown,
        inputs.smh_drawdown,
        inputs.qqq_above_ma60,
        inputs.smh_above_ma60,
    ]
    return any(value is None for value in required)


def _asset_in_range(value: float | None, lower: float, upper: float) -> bool:
    return value is not None and lower <= value <= upper


def _gt(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def _strong_reason(inputs: TacticalInputs) -> str:
    reasons = []
    if _asset_in_range(inputs.qqq_drawdown, -0.18, -0.10) and _asset_in_range(inputs.qqq_rsi, 35, 50):
        reasons.append(f"QQQ 回撤 {inputs.qqq_drawdown:.1%}，RSI {inputs.qqq_rsi:.1f}")
    if _asset_in_range(inputs.smh_drawdown, -0.18, -0.10) and _asset_in_range(inputs.smh_rsi, 35, 50):
        reasons.append(f"SMH 回撤 {inputs.smh_drawdown:.1%}，RSI {inputs.smh_rsi:.1f}")
    detail = "；".join(reasons) if reasons else "成长资产出现 10%–18% 回撤且 RSI 进入 35–50"
    return f"strong_opportunity 触发原因：{detail}，且趋势没有彻底破坏。"
