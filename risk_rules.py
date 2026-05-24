from __future__ import annotations

import pandas as pd


TECH_CATEGORIES = ["nasdaq100", "global_growth", "global_tech", "ai_semiconductor"]
CRITICAL_KEYS = ["SPY", "QQQ", "SOXX", "VIX", "DGS10"]


def _metric(market: pd.DataFrame, proxy: str, column: str) -> float | None:
    matched = market.loc[market["proxy"] == proxy, column]
    if matched.empty or pd.isna(matched.iloc[0]):
        return None
    return float(matched.iloc[0])


def _quality(market: pd.DataFrame, proxy: str) -> str:
    matched = market.loc[market["proxy"] == proxy, "data_quality"]
    if matched.empty or pd.isna(matched.iloc[0]):
        return "missing"
    return str(matched.iloc[0])


def _weight_of(category: pd.DataFrame, name: str) -> float:
    matched = category.loc[category["category"] == name, "current_weight"]
    if matched.empty or pd.isna(matched.iloc[0]):
        return 0.0
    return float(matched.iloc[0])


def _target_of(category: pd.DataFrame, name: str) -> float:
    matched = category.loc[category["category"] == name, "target_weight"]
    if matched.empty or pd.isna(matched.iloc[0]):
        return 0.0
    return float(matched.iloc[0])


def evaluate_data_quality(market: pd.DataFrame) -> dict[str, object]:
    qualities = {str(row["proxy"]): str(row["data_quality"]) for _, row in market.iterrows()}
    missing = [key for key in CRITICAL_KEYS if qualities.get(key, "missing") == "missing"]
    stale = [key for key, quality in qualities.items() if quality == "stale"]
    reasons: list[str] = []

    if missing:
        reasons.append(f"关键数据缺失：{'、'.join(missing)}")
    if stale:
        reasons.append(f"使用本地缓存：{'、'.join(stale)}")
    if any(key in stale for key in ["VIX", "DGS10"]):
        reasons.append("宏观信号不新鲜")
    if any(key in stale for key in ["QQQ", "SOXX"]):
        reasons.append("QQQ 或 SOXX 为缓存数据，禁止触发额外加仓")

    if missing:
        label = "missing"
    elif stale:
        label = "partial stale"
    else:
        label = "fresh"

    allow_extra_add = label == "fresh"
    return {
        "label": label,
        "allow_extra_add": allow_extra_add,
        "missing": missing,
        "stale": stale,
        "reasons": reasons,
    }


def build_advice(market: pd.DataFrame, category: pd.DataFrame, quality_summary: dict[str, object]) -> list[str]:
    advice: list[str] = []
    allow_extra_add = bool(quality_summary["allow_extra_add"])

    qqq = _metric(market, "QQQ", "return_pct")
    spy = _metric(market, "SPY", "return_pct")
    gld = _metric(market, "GLD", "return_pct")
    soxx = _metric(market, "SOXX", "return_pct")
    vix = _metric(market, "VIX", "value")
    dgs10_change = _metric(market, "DGS10", "us10y_change")
    qqq_drawdown = _metric(market, "QQQ", "drawdown_from_high")

    if quality_summary["label"] != "fresh":
        advice.append("数据不新鲜，今日不触发额外加仓；等待行情数据恢复。")
    if "VIX" in quality_summary["stale"] or "DGS10" in quality_summary["stale"]:
        advice.append("宏观信号不新鲜，VIX 或 10年期美债数据仅供观察。")
    if quality_summary["missing"]:
        advice.append("关键数据存在缺失，额外加仓结论不能超过观察。")

    if qqq is not None and soxx is not None and qqq < 0 and soxx - qqq < -0.02:
        advice.append("半导体链明显弱于纳指，AI/半导体相关定投不要额外加码。")

    if qqq is not None and spy is not None and qqq < 0 and spy < 0 and qqq < spy:
        advice.append("科技成长弱于大盘，纳指和全球成长仓位短期承压。")

    if gld is not None and spy is not None and gld < 0 and spy < 0:
        advice.append("黄金短期没有发挥避险作用，不能把黄金当成单日对冲工具。")

    tech_weight = sum(_weight_of(category, item) for item in TECH_CATEGORIES)
    if tech_weight > 0.50:
        advice.append("组合科技成长暴露偏高，后续新增资金应控制节奏。")

    sp500_weight = _weight_of(category, "sp500")
    sp500_target = _target_of(category, "sp500")
    if sp500_target - sp500_weight > 0.05:
        advice.append("标普500核心仓低于目标，可优先承接后续定投。")

    gold_weight = _weight_of(category, "gold")
    gold_target = _target_of(category, "gold")
    if gold_target - gold_weight > 0.02:
        advice.append("黄金仓位低于目标，可作为分散风险的小比例补充。")

    extra_conditions = [
        qqq_drawdown is not None and qqq_drawdown <= -0.08,
        vix is not None and vix >= 25,
        dgs10_change is not None and dgs10_change <= 0,
        soxx is not None and qqq is not None and soxx >= qqq - 0.02,
    ]

    if allow_extra_add and all(extra_conditions):
        advice.append("额外加仓观察条件部分满足：QQQ 回撤较深、VIX 偏高、美债收益率未上行、半导体相对企稳。可只考虑小额分批，不追高。")
    elif not allow_extra_add:
        advice.append("额外加仓保护已启用：数据质量不是 fresh，今日只观察，不做额外加仓判断。")
    else:
        advice.append("额外加仓条件尚未充分满足，继续执行长期定投，不主动放大进攻仓位。")

    advice.append("核心建议：原仓持有，定投继续执行，不建议额外追高科技成长。如果市场连续大跌，等待 SOXX/QQQ 企稳后再考虑额外加仓。")
    return advice
