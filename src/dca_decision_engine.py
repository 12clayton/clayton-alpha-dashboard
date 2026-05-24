"""Daily DCA decision engine for research-only investment monitoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


DEFAULT_PORTFOLIO_PATH = Path("config/portfolio.yaml")
DEFAULT_POLICY_PATH = Path("config/dca_policy.yaml")


def build_dca_decision(
    risk_table: pd.DataFrame,
    market_regime: str,
    news_digest: dict | None = None,
    portfolio_path: str | Path = DEFAULT_PORTFOLIO_PATH,
    policy_path: str | Path = DEFAULT_POLICY_PATH,
) -> dict:
    """Build a research-only daily DCA decision."""

    # 配置和风险表分离，后续更新组合不需要改代码。
    portfolio = load_yaml(portfolio_path)
    policy = load_yaml(policy_path)
    funds = portfolio.get("funds", [])

    # 先计算组合暴露，再判断当前属于哪个定投模式。
    portfolio_state = summarize_portfolio_state(funds=funds, risk_table=risk_table, policy=policy)
    mode, mode_reasons = classify_dca_mode(
        risk_table=risk_table,
        market_regime=market_regime,
        portfolio_state=portfolio_state,
        policy=policy,
        news_digest=news_digest,
    )

    # 根据模式生成每只基金的今日金额和原因。
    fund_plan = allocate_daily_dca(
        funds=funds,
        risk_table=risk_table,
        mode=mode,
        policy=policy,
        portfolio_state=portfolio_state,
    )
    daily_total = sum(item["suggested_daily_dca"] for item in fund_plan)

    # 机动资金只在大机会档考虑，并且单次不超过一个 tranche。
    tactical_plan = build_tactical_cash_plan(
        funds=funds,
        risk_table=risk_table,
        mode=mode,
        policy=policy,
        portfolio_state=portfolio_state,
    )
    news_link_result = build_news_link_result(risk_table=risk_table, news_digest=news_digest)

    main_directions = [item["theme"] for item in fund_plan if item["suggested_daily_dca"] > item["base_daily_dca"]]
    blocked_directions = [item["theme"] for item in fund_plan if item["suggested_daily_dca"] < item["base_daily_dca"]]
    gold_plan = next((item for item in fund_plan if item["theme"] == "黄金"), None)

    return {
        "mode": mode,
        "mode_reasons": mode_reasons,
        "suggested_daily_total": daily_total,
        "use_tactical_cash": tactical_plan["use_tactical_cash"],
        "tactical_cash_amount": tactical_plan["amount"],
        "tactical_cash_target": tactical_plan["target"],
        "tactical_cash_remaining": tactical_plan["remaining_cash"],
        "tactical_cash_reason": tactical_plan["reason"],
        "tactical_cash_risk": tactical_plan["risk"],
        "fund_plan": fund_plan,
        "main_directions": unique_keep_order(main_directions) or ["保持基础定投"],
        "blocked_directions": unique_keep_order(blocked_directions) or ["暂无需要降低的方向"],
        "gold_action": gold_plan["reason"] if gold_plan else "未配置黄金基金。",
        "near_drawdown_limit": portfolio_state["estimated_drawdown"] <= policy.get("max_drawdown_tolerance", -0.20) * 0.9,
        "portfolio_state": portfolio_state,
        "one_sentence": build_one_sentence(mode=mode, daily_total=daily_total, tactical_plan=tactical_plan),
        "news_link_notes": news_link_result["notes"],
        "news_action_tags": news_link_result["action_tags"],
        "disclaimer": "本结果仅用于研究观察、风险提示和定投辅助，不构成投资建议，不自动交易，不连接券商账户。",
    }


def load_yaml(path: str | Path) -> dict:
    """Load a YAML file as a dictionary."""

    # 文件缺失时抛出清楚错误，避免默默生成错误计划。
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def summarize_portfolio_state(funds: list[dict], risk_table: pd.DataFrame, policy: dict) -> dict:
    """Summarize portfolio exposure and drawdown state."""

    total_amount = sum(float(fund.get("current_amount", 0) or 0) for fund in funds)
    total_amount = total_amount if total_amount > 0 else 1.0

    # 计算黄金和高波动方向占比，用于黄金补仓和风险阈值判断。
    gold_amount = sum(float(fund.get("current_amount", 0) or 0) for fund in funds if fund.get("theme") == "黄金")
    high_vol_amount = sum(
        float(fund.get("current_amount", 0) or 0) for fund in funds if bool(fund.get("is_high_volatility"))
    )

    weighted_drawdown = 0.0
    for fund in funds:
        amount = float(fund.get("current_amount", 0) or 0)
        proxy = fund.get("proxy_symbol")
        weighted_drawdown += (amount / total_amount) * risk_value(risk_table, proxy, "latest_drawdown")

    return {
        "total_amount": total_amount,
        "gold_weight": gold_amount / total_amount,
        "high_volatility_weight": high_vol_amount / total_amount,
        "estimated_drawdown": weighted_drawdown,
        "gold_below_min": gold_amount / total_amount < policy.get("gold_target_weight_min", 0.06),
        "gold_above_max": gold_amount / total_amount > policy.get("gold_target_weight_max", 0.08),
    }


def classify_dca_mode(
    risk_table: pd.DataFrame,
    market_regime: str,
    portfolio_state: dict,
    policy: dict,
    news_digest: dict | None = None,
) -> tuple[str, list[str]]:
    """Classify today's DCA mode."""

    # 防守档优先级最高，避免系统性风险里误触发进攻。
    growth_symbols = ["QQQ", "SMH", "SOXX"]
    all_growth_weak = all(risk_regime(risk_table, symbol) == "risk-off" for symbol in growth_symbols)
    defense_weak = risk_regime(risk_table, "GLD") == "risk-off" and risk_regime(risk_table, "TLT") == "risk-off"
    near_limit = portfolio_state["estimated_drawdown"] <= policy.get("max_drawdown_tolerance", -0.20) * 0.9
    high_vol_over_cap = portfolio_state["high_volatility_weight"] > policy.get("high_volatility_max_weight", 0.75)

    if market_regime == "risk-off" or (all_growth_weak and defense_weak) or near_limit or high_vol_over_cap:
        return "defense_mode", [
            "总体市场或高波动方向偏弱，优先控制组合回撤。",
            "若高波动资产占比超过上限，应暂停加速并等待风险释放。",
            "不使用机动资金大额进攻，仅保留研究观察和基础定投辅助。",
        ]

    # 大机会档：5%-15% 回撤且长期结构未完全破坏。
    opportunity_symbols = [symbol for symbol in growth_symbols if is_opportunity_pullback(risk_table, symbol)]
    if opportunity_symbols and market_regime != "risk-off":
        return "opportunity_mode", [
            f"{'、'.join(opportunity_symbols)} 出现 5%-15% 回撤但长期趋势尚未完全破坏。",
            "可研究是否小份额使用机动资金，单次不超过一个 tranche。",
        ]

    # 进攻档：趋势仍在，短线回踩，RSI 回落到 45-60。
    attack_symbols = [symbol for symbol in growth_symbols if is_attack_setup(risk_table, symbol)]
    news_links = (news_digest or {}).get("dca_links", {})
    if news_links.get("dollar_and_yields_strong") or "reduce_aggression" in news_links.get("action_tags", []):
        return "normal_mode", [
            "美元和美债收益率相关新闻显示成长股估值压力上升。",
            "今日不提高高波动资产定投，维持基础节奏并观察价格风险状态。",
        ]
    if attack_symbols and market_regime in ["risk-on", "neutral"]:
        return "attack_mode", [
            f"{'、'.join(attack_symbols)} 趋势仍在且 RSI 回到 45-60 区间。",
            "今日可研究把日定投提高到 80-100 元，优先高景气方向。",
        ]
    if news_links.get("semiconductor_cpo_positive") and any(is_healthy_pullback(risk_table, symbol) for symbol in growth_symbols):
        return "attack_mode", [
            "半导体 / CPO 新闻偏积极，且成长方向出现健康回踩。",
            "新闻仅作为辅助条件，今日可研究把日定投提高到 80-100 元，不动用大额机动资金。",
        ]

    return "normal_mode", [
        "总体市场不是系统性 risk-off，但也没有出现明确大机会。",
        "按基础每日 60 元定投计划执行更稳妥。",
    ]


def allocate_daily_dca(
    funds: list[dict],
    risk_table: pd.DataFrame,
    mode: str,
    policy: dict,
    portfolio_state: dict,
) -> list[dict]:
    """Allocate today's DCA amount for each fund."""

    plan = []
    for fund in funds:
        base_amount = float(fund.get("base_daily_dca", 0) or 0)
        max_amount = float(fund.get("max_daily_dca", base_amount) or 0)
        amount = base_amount
        reason = "按基础定投计划观察执行。"
        proxy = fund.get("proxy_symbol")
        theme = fund.get("theme", "")

        if mode == "defense_mode":
            amount, reason = defense_amount(fund, portfolio_state, policy)
        elif mode == "attack_mode":
            amount, reason = attack_amount(fund, risk_table, base_amount, max_amount)
        elif mode == "opportunity_mode":
            amount, reason = opportunity_amount(fund, risk_table, base_amount, max_amount)

        # 黄金单独应用目标仓位规则，定位是防守缓冲而不是主攻方向。
        if theme == "黄金":
            amount, reason = apply_gold_rule(amount, reason, fund, risk_table, portfolio_state, policy)

        plan.append(
            {
                "fund_name": fund.get("fund_name", ""),
                "fund_code": fund.get("fund_code", ""),
                "theme": theme,
                "proxy_symbol": proxy,
                "base_daily_dca": base_amount,
                "max_daily_dca": max_amount,
                "suggested_daily_dca": round(amount, 2),
                "priority_rank": int(fund.get("priority_rank", 99) or 99),
                "reason": reason,
            }
        )

    # 如果非防守档且总额超过上限，按优先级做一次保守缩放。
    total = sum(item["suggested_daily_dca"] for item in plan)
    max_budget = policy.get("max_daily_budget", 100)
    if total > max_budget:
        scale_plan_to_budget(plan, max_budget)

    return sorted(plan, key=lambda item: item["priority_rank"])


def defense_amount(fund: dict, portfolio_state: dict, policy: dict) -> tuple[float, str]:
    """Return amount and reason for defense mode."""

    base_amount = float(fund.get("base_daily_dca", 0) or 0)
    theme = fund.get("theme", "")

    if theme == "标普500":
        return min(base_amount, 10), "防守档下保留标普500小额基础观察。"
    if theme == "黄金" and portfolio_state["gold_below_min"]:
        return min(float(fund.get("max_daily_dca", 0) or 0), 5), "黄金低于 6%，只允许小额分批补充防守缓冲。"
    if bool(fund.get("is_high_volatility")):
        return min(base_amount, 5), "防守档下降低高波动方向，不做加速。"
    return min(base_amount, 5), "防守档下控制新增风险暴露。"


def attack_amount(fund: dict, risk_table: pd.DataFrame, base_amount: float, max_amount: float) -> tuple[float, str]:
    """Return amount and reason for attack mode."""

    priority = int(fund.get("priority_rank", 99) or 99)
    proxy = fund.get("proxy_symbol")
    theme = fund.get("theme", "")

    if theme == "黄金":
        return 0, "进攻档不额外追黄金，黄金只作为防守缓冲观察。"
    if priority <= 2 and is_trend_alive(risk_table, proxy):
        return max(base_amount, min(max_amount, base_amount + 10)), "进攻档优先增加半导体、CPO、CPU、AI 成长方向。"
    if bool(fund.get("is_high_volatility")) and is_trend_alive(risk_table, proxy):
        return min(max_amount, base_amount + 5), "高波动成长方向趋势仍在，小幅提高日定投辅助金额。"
    return base_amount, "保持基础金额，等待更清晰的回踩或机会。"


def opportunity_amount(fund: dict, risk_table: pd.DataFrame, base_amount: float, max_amount: float) -> tuple[float, str]:
    """Return amount and reason for opportunity mode."""

    priority = int(fund.get("priority_rank", 99) or 99)
    proxy = fund.get("proxy_symbol")

    if priority <= 2 and is_opportunity_pullback(risk_table, proxy):
        return min(max_amount, max(base_amount + 15, 20)), "大机会档优先观察半导体、CPO、CPU 相关方向。"
    if bool(fund.get("is_high_volatility")) and is_trend_alive(risk_table, proxy):
        return min(max_amount, base_amount + 5), "成长方向有回撤机会，但仍需分批而非一次性加满。"
    return base_amount, "不属于今日主攻方向，保持基础计划。"


def apply_gold_rule(
    amount: float,
    reason: str,
    fund: dict,
    risk_table: pd.DataFrame,
    portfolio_state: dict,
    policy: dict,
) -> tuple[float, str]:
    """Apply the gold target-weight rule."""

    gold_regime = risk_regime(risk_table, fund.get("proxy_symbol"))
    if portfolio_state["gold_above_max"]:
        return 0, "黄金仓位已高于 8%，暂停补仓观察。"
    if portfolio_state["gold_below_min"]:
        if gold_regime == "risk-off":
            return min(float(fund.get("max_daily_dca", 0) or 0), 5), "黄金低于 6% 但 GLD risk-off，只允许小额分批补。"
        return min(float(fund.get("max_daily_dca", 0) or 0), 10), "黄金低于 6%，允许小额补充防守缓冲。"
    return min(amount, 0), "黄金位于目标仓位 6%-8% 附近，不作为今日主攻方向。"


def build_tactical_cash_plan(
    funds: list[dict],
    risk_table: pd.DataFrame,
    mode: str,
    policy: dict,
    portfolio_state: dict,
) -> dict:
    """Build tactical cash usage suggestion."""

    cash = float(policy.get("tactical_cash", 5000) or 0)
    tranche = float(policy.get("single_tranche_amount", 1000) or 1000)
    reserve_floor = cash * 0.60

    if mode != "opportunity_mode":
        return no_tactical_cash(cash, "今日不是大机会档，不动用机动资金。")

    if portfolio_state["estimated_drawdown"] <= policy.get("max_drawdown_tolerance", -0.20) * 0.9:
        return no_tactical_cash(cash, "组合回撤接近 -20% 风险阈值，不使用机动资金进攻。")

    targets = [
        fund for fund in funds
        if int(fund.get("priority_rank", 99) or 99) <= 2 and is_opportunity_pullback(risk_table, fund.get("proxy_symbol"))
    ]
    if not targets:
        return no_tactical_cash(cash, "没有半导体、CPO、CPU 方向触发合格的大机会回撤。")

    amount = min(tranche, max(0, cash - reserve_floor))
    amount = min(amount, 1000)
    if amount <= 0:
        return no_tactical_cash(cash, "需要保留至少 60% 机动资金，当前不建议动用。")

    target_theme = " / ".join(unique_keep_order([fund.get("theme", "") for fund in targets]))
    return {
        "use_tactical_cash": True,
        "amount": amount,
        "target": target_theme,
        "remaining_cash": cash - amount,
        "reason": f"{target_theme} 出现 5%-15% 回撤且长期趋势未完全破坏，触发大机会观察。",
        "risk": "机动资金仅建议分批观察使用；若后续跌破长期趋势或市场转为系统性 risk-off，应停止加速。",
    }


def no_tactical_cash(cash: float, reason: str) -> dict:
    """Return a no tactical cash plan."""

    return {
        "use_tactical_cash": False,
        "amount": 0,
        "target": "暂无",
        "remaining_cash": cash,
        "reason": reason,
        "risk": "未使用机动资金，继续等待更明确的大机会或风险释放。",
    }


def is_attack_setup(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check attack-mode setup."""

    return (
        is_trend_alive(risk_table, symbol)
        and risk_value(risk_table, symbol, "daily_return") < 0
        and 45 <= risk_value(risk_table, symbol, "rsi") <= 60
    )


def is_opportunity_pullback(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check opportunity-mode pullback."""

    drawdown = risk_value(risk_table, symbol, "latest_drawdown")
    return -0.15 <= drawdown <= -0.05 and is_trend_alive(risk_table, symbol)


def is_healthy_pullback(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check whether a pullback is healthy enough for attack mode."""

    drawdown = risk_value(risk_table, symbol, "latest_drawdown")
    rsi = risk_value(risk_table, symbol, "rsi")
    return -0.08 <= drawdown <= -0.01 and 45 <= rsi <= 65 and is_trend_alive(risk_table, symbol)


def build_news_link_result(risk_table: pd.DataFrame, news_digest: dict | None) -> dict:
    """Build DCA notes and action tags linked to today's news digest."""

    links = (news_digest or {}).get("dca_links", {})
    notes = []
    action_tags = []
    growth_hot = any(risk_value(risk_table, symbol, "rsi") > 70 for symbol in ["QQQ", "SMH", "SOXX"])

    if links.get("semiconductor_cpo_positive") and growth_hot:
        notes.append("半导体 / CPO 新闻偏积极，但 QQQ、SMH 或 SOXX RSI 高于 70，基本面和情绪虽强但短线不追高。")
        action_tags.append("do_not_chase")
    if links.get("semiconductor_cpo_positive") and any(is_healthy_pullback(risk_table, symbol) for symbol in ["QQQ", "SMH", "SOXX"]):
        notes.append("半导体 / CPO 新闻积极且出现健康回踩，可作为提高今日定投到 80-100 元的辅助观察条件。")
        action_tags.append("small_acceleration")
    if links.get("dollar_and_yields_strong"):
        notes.append("美元和美债收益率同时走强，成长股估值压力上升。")
        action_tags.append("reduce_aggression")
    if links.get("gold_positive") and risk_regime(risk_table, "GLD") != "risk-on":
        notes.append("黄金新闻偏积极但 GLD 趋势仍弱，黄金只作为防守缓冲分批观察，不追涨。")
        action_tags.append("maintain_dca")
    if links.get("sic_major_positive"):
        notes.append("碳化硅出现产业链积极信号，加入观察池，不触发自动买入。")
        action_tags.append("watchlist_only")

    return {
        "notes": notes or ["今日新闻未改变定投辅助框架，继续以价格风险状态和仓位纪律为主。"],
        "action_tags": unique_keep_order(action_tags) or ["maintain_dca"],
    }


def is_trend_alive(risk_table: pd.DataFrame, symbol: str) -> bool:
    """Check whether long-term trend is not fully broken."""

    row = risk_row(risk_table, symbol)
    if row is None:
        return False
    if row.get("risk_regime") == "risk-off":
        return False

    last_price = coerce_float(row.get("last_price"), 0)
    long_ma = coerce_float(row.get("long_ma"), 0)
    return long_ma <= 0 or last_price >= long_ma * 0.97


def risk_row(risk_table: pd.DataFrame, symbol: str | None) -> pd.Series | None:
    """Return one risk row by proxy symbol."""

    if not symbol or "symbol" not in risk_table.columns:
        return None
    matched = risk_table.loc[risk_table["symbol"] == symbol]
    if matched.empty:
        return None
    return matched.iloc[0]


def risk_value(risk_table: pd.DataFrame, symbol: str | None, column: str) -> float:
    """Return a numeric risk value."""

    row = risk_row(risk_table, symbol)
    if row is None:
        return 0.0
    return coerce_float(row.get(column), 0.0)


def risk_regime(risk_table: pd.DataFrame, symbol: str | None) -> str:
    """Return risk regime for a symbol."""

    row = risk_row(risk_table, symbol)
    if row is None:
        return ""
    return str(row.get("risk_regime", ""))


def coerce_float(value, default: float) -> float:
    """Convert values to float with fallback."""

    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def scale_plan_to_budget(plan: list[dict], max_budget: float) -> None:
    """Scale suggested amounts down to the max daily budget."""

    total = sum(item["suggested_daily_dca"] for item in plan)
    if total <= 0:
        return
    scale = max_budget / total
    for item in plan:
        item["suggested_daily_dca"] = round(item["suggested_daily_dca"] * scale, 2)
        item["reason"] += " 因总额超过每日上限，已按比例压缩。"


def unique_keep_order(values: list[str]) -> list[str]:
    """Return unique non-empty values while preserving order."""

    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_one_sentence(mode: str, daily_total: float, tactical_plan: dict) -> str:
    """Build one sentence conclusion."""

    if tactical_plan["use_tactical_cash"]:
        return f"今日为 {mode}，日定投辅助金额约 {daily_total:.0f} 元，并可研究小额动用机动资金 {tactical_plan['amount']:.0f} 元。"
    return f"今日为 {mode}，日定投辅助金额约 {daily_total:.0f} 元，不建议动用机动资金。"
