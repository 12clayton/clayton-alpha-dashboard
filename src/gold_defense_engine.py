"""Gold defense monitoring helpers for the Streamlit dashboard."""

from __future__ import annotations

import pandas as pd


def evaluate_gold_defense(portfolio: dict, asset_table: pd.DataFrame) -> dict:
    """Evaluate gold defense mode without affecting the main DCA decision."""

    gold_weight = calculate_gold_weight(portfolio)
    signals = {symbol: extract_asset_signal(asset_table, symbol) for symbol in ["GC=F", "GLD", "UUP", "TLT", "DFII10"]}
    signals["UUP"] = classify_uup_signal(signals["UUP"])
    missing = [symbol for symbol, signal in signals.items() if signal["status"] == "data_unavailable"]
    core_missing = [symbol for symbol in ["GC=F", "GLD", "UUP"] if symbol in missing]

    if core_missing:
        return build_result("gold_wait", gold_weight, signals, "¥30 或暂停一次", "黄金核心数据缺失，默认等待。", missing)

    gld = signals["GLD"]
    futures = signals["GC=F"]
    uup = signals["UUP"]
    real_rate = signals["DFII10"]

    gold_trend_bad = gld["risk_status"] == "risk-off" or futures["risk_status"] == "risk-off"
    gold_overheated = max(gld["rsi"], futures["rsi"]) > 70
    dollar_strong = uup["risk_status"] in {"risk-on", "dollar_strength_pressure"}
    real_rate_up = real_rate["status"] == "ok" and real_rate["risk_status"] == "risk-on"

    if gold_weight > 0.10 or gold_overheated:
        return build_result("gold_pause", gold_weight, signals, "暂停", "黄金仓位或短线热度偏高。", missing)
    if 0.08 <= gold_weight <= 0.10:
        return build_result("gold_hold", gold_weight, signals, "维持", "黄金仓位已接近防守目标。", missing)
    if gold_weight < 0.08 and (gold_trend_bad or dollar_strong or real_rate_up):
        return build_result(
            "gold_wait",
            gold_weight,
            signals,
            "¥30 或暂停一次",
            "黄金仓位仍低于目标，但 GC=F 趋势偏弱或美元偏强，因此只允许小额防守补仓，不追涨。",
            missing,
        )
    if gold_weight < 0.08:
        pullback = min(gld["drawdown"], futures["drawdown"]) < -0.04
        suggestion = "¥90–105" if pullback else "¥60"
        return build_result("gold_accumulate", gold_weight, signals, suggestion, "黄金仓位低，且趋势和宏观压力未明显恶化。", missing)

    return build_result("gold_hold", gold_weight, signals, "维持", "黄金仓位处于中性观察区间。", missing)


def calculate_gold_weight(portfolio: dict) -> float:
    """Calculate gold fund weight from local portfolio config."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "current_amount" not in funds.columns:
        return 0.0
    total = pd.to_numeric(funds["current_amount"], errors="coerce").sum()
    if not total:
        return 0.0
    theme = funds.get("theme", pd.Series(dtype=str)).fillna("").astype(str)
    gold_amount = pd.to_numeric(funds.loc[theme.str.contains("黄金", na=False), "current_amount"], errors="coerce").sum()
    return float(gold_amount / total) if total else 0.0


def extract_asset_signal(asset_table: pd.DataFrame, symbol: str) -> dict:
    """Extract risk status, RSI, and drawdown for one asset."""

    if asset_table.empty or "代码" not in asset_table.columns:
        return unavailable_signal(symbol)
    row = asset_table.loc[asset_table["代码"].astype(str) == symbol]
    if row.empty:
        return unavailable_signal(symbol)
    record = row.iloc[0]
    return {
        "symbol": symbol,
        "status": "ok",
        "risk_status": str(record.get("风险状态", "data_unavailable")),
        "rsi": parse_float(record.get("RSI数值", record.get("RSI", 0))),
        "drawdown": parse_float(record.get("当前回撤数值", record.get("当前回撤", 0))),
    }


def unavailable_signal(symbol: str) -> dict:
    """Return a stable unavailable signal."""

    return {"symbol": symbol, "status": "data_unavailable", "risk_status": "data_unavailable", "rsi": 0.0, "drawdown": 0.0}


def classify_uup_signal(signal: dict) -> dict:
    """Classify UUP by RSI because dollar strength pressures gold directly."""

    if signal["status"] == "data_unavailable":
        return signal
    adjusted = dict(signal)
    rsi = adjusted.get("rsi", 0.0)
    if rsi > 70:
        adjusted["risk_status"] = "dollar_strength_pressure"
    elif 45 <= rsi <= 60:
        adjusted["risk_status"] = "neutral"
    elif rsi < 40:
        adjusted["risk_status"] = "dollar_weakness_supportive"
    return adjusted


def parse_float(value) -> float:
    """Parse numeric values safely."""

    try:
        text = str(value).replace("%", "").strip()
        number = float(text)
        return number / 100 if "%" in str(value) else number
    except (TypeError, ValueError):
        return 0.0


def build_result(mode: str, gold_weight: float, signals: dict, suggestion: str, reason: str, missing: list[str]) -> dict:
    """Build a dashboard-ready result."""

    return {
        "gold_mode": mode,
        "gold_weight": gold_weight,
        "signals": signals,
        "suggestion": suggestion,
        "reason": reason,
        "missing_data": missing,
        "data_warning": build_data_warning(missing),
    }


def build_data_warning(missing: list[str]) -> str:
    """Return an accurate missing-data warning."""

    if not missing:
        return ""
    if missing == ["DFII10"]:
        return "部分宏观数据缺失：DFII10 实际利率暂不可用；黄金判断已基于 GC=F、GLD、UUP 和当前黄金仓位生成。"
    if "DFII10" in missing:
        others = "、".join(symbol for symbol in missing if symbol != "DFII10")
        return f"部分黄金/宏观数据缺失：{others}、DFII10 暂不可用；黄金判断已转为保守等待。"
    return f"部分黄金数据缺失：{'、'.join(missing)}；黄金判断已转为保守等待。"
