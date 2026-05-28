"""Lightweight overall-view rules for industry trend pages."""

from __future__ import annotations

from typing import Any


OVERALL_TEXT = {
    "zh": {
        "title": "综合判断",
        "overall_status": "综合状态",
        "trend_stage": "趋势阶段",
        "price_confirmation": "价格确认",
        "news_heat": "新闻热度",
        "priced_in_risk": "透支风险",
        "key_tags": "关键标签",
        "one_line": "一句话解释",
        "status_labels": {
            "healthy_alignment": "趋势健康共振",
            "heat_price_divergence": "热度价格背离",
            "strong_framework_weak_price": "框架强但价格弱",
            "high_heat_divergence": "高热分化",
            "early_watch": "早期观察",
            "weakening_trend": "趋势转弱",
            "insufficient_data": "数据不足",
        },
        "risk_labels": {
            "low": "低",
            "medium": "中",
            "high": "高",
            "insufficient_data": "数据不足",
        },
        "tags": {
            "high_heat": "热度高",
            "weak_price": "价格确认弱",
            "strong_framework": "框架信号强",
            "insufficient_market": "市场确认不足",
            "strong_price": "价格确认较强",
            "heat_support": "热度配合",
            "high_valuation": "估值压力高",
            "weak_breadth": "价格广度弱",
            "watch": "观察阶段",
            "limited_data": "数据不足",
        },
        "views": {
            "heat_price_divergence": "该行业新闻热度较高，但市场价格确认不足，说明叙事仍活跃但价格层面尚未形成有效共振。",
            "strong_framework_weak_price": "该行业框架信号仍有支撑，但市场价格确认偏弱，需要观察价格广度和相对强弱是否修复。",
            "healthy_alignment": "该行业框架信号、新闻热度和市场价格确认相对一致，趋势质量较为健康。",
            "high_heat_divergence": "该行业热度较高且估值压力上升，趋势可能仍在，但内部分化和波动风险加大。",
            "weakening_trend": "该行业市场价格确认不足，MA50 广度较弱，趋势质量正在下降。",
            "early_watch": "该行业已有一定信号，但价格和热度尚未形成强共振，仍处观察阶段。",
            "insufficient_data": "当前数据不足以形成完整综合判断，仍展示已有框架信息。",
        },
        "score_na": "数据不足",
    },
    "en": {
        "title": "Overall View",
        "overall_status": "Overall Status",
        "trend_stage": "Trend Stage",
        "price_confirmation": "Price Confirmation",
        "news_heat": "News Heat",
        "priced_in_risk": "Priced-in Risk",
        "key_tags": "Key Tags",
        "one_line": "One-line View",
        "status_labels": {
            "healthy_alignment": "Healthy Trend Alignment",
            "heat_price_divergence": "Heat-Price Divergence",
            "strong_framework_weak_price": "Strong Framework, Weak Price",
            "high_heat_divergence": "High-heat Divergence",
            "early_watch": "Early Watch",
            "weakening_trend": "Weakening Trend",
            "insufficient_data": "Insufficient Data",
        },
        "risk_labels": {
            "low": "Low",
            "medium": "Medium",
            "high": "High",
            "insufficient_data": "Insufficient Data",
        },
        "tags": {
            "high_heat": "High heat",
            "weak_price": "Weak price confirmation",
            "strong_framework": "Strong framework signal",
            "insufficient_market": "Insufficient market confirmation",
            "strong_price": "Stronger price confirmation",
            "heat_support": "Heat support",
            "high_valuation": "High valuation pressure",
            "weak_breadth": "Weak price breadth",
            "watch": "Watch stage",
            "limited_data": "Limited data",
        },
        "views": {
            "heat_price_divergence": "News heat is elevated, but market-price confirmation is still weak, suggesting active narratives without effective price alignment.",
            "strong_framework_weak_price": "The framework signal remains supportive, but market-price confirmation is weak, so price breadth and relative strength need further observation.",
            "healthy_alignment": "Framework signal, news heat, and market-price confirmation are relatively aligned, suggesting healthier trend quality.",
            "high_heat_divergence": "Heat is elevated and valuation pressure is rising. The trend may still exist, but internal dispersion and volatility risk are higher.",
            "weakening_trend": "Market-price confirmation is insufficient and MA50 breadth is weak, suggesting declining trend quality.",
            "early_watch": "Some signals are present, but price and heat have not formed strong alignment yet, so the industry remains in watch mode.",
            "insufficient_data": "Current data is insufficient for a complete overall view, so available framework information is still shown.",
        },
        "score_na": "Insufficient Data",
    },
}


def compute_overall_view(
    *,
    framework_trend_score: object,
    market_price_confirmation_score: object,
    news_heat_score: object,
    valuation_pressure: object,
    fundamental_validation: object,
    ma50_ratio: object,
    trend_stage: str,
    lang: str,
) -> dict[str, Any]:
    """Compute a deterministic product-level overall view."""

    framework = _to_float(framework_trend_score)
    price = _to_float(market_price_confirmation_score)
    heat = _to_float(news_heat_score)
    valuation = _to_float(valuation_pressure)
    validation = _to_float(fundamental_validation)
    ma50 = _to_float(ma50_ratio)
    status_key = "insufficient_data"
    tag_keys: list[str] = ["limited_data"]

    has_core_data = framework is not None and price is not None and heat is not None
    if has_core_data:
        tag_keys = []
        if price < 4.0 and ma50 is not None and ma50 < 0.30:
            status_key = "weakening_trend"
            tag_keys = ["weak_breadth", "insufficient_market"]
        elif heat >= 7.0 and price < 4.5:
            status_key = "heat_price_divergence"
            tag_keys = ["high_heat", "weak_price"]
        elif framework >= 6.5 and price < 4.5:
            status_key = "strong_framework_weak_price"
            tag_keys = ["strong_framework", "insufficient_market"]
        elif heat >= 7.0 and valuation is not None and valuation >= 7.0 and price >= 4.5:
            status_key = "high_heat_divergence"
            tag_keys = ["high_heat", "high_valuation"]
        elif price >= 6.5 and heat >= 6.0 and framework >= 6.0:
            status_key = "healthy_alignment"
            tag_keys = ["strong_price", "heat_support"]
        elif heat < 6.5 and 4.0 <= price < 6.5:
            status_key = "early_watch"
            tag_keys = ["watch"]
        else:
            status_key = "early_watch"
            tag_keys = ["watch"]

    risk_key = compute_priced_in_risk(
        news_heat_score=heat,
        market_price_confirmation_score=price,
        valuation_pressure=valuation,
        fundamental_validation=validation,
    )
    text = OVERALL_TEXT[lang]
    return {
        "status_key": status_key,
        "status_label": text["status_labels"][status_key],
        "priced_in_risk_key": risk_key,
        "priced_in_risk_label": text["risk_labels"][risk_key],
        "tag_keys": tag_keys,
        "tags": [text["tags"][key] for key in tag_keys],
        "one_line": text["views"][status_key],
        "trend_stage": trend_stage,
        "price_score": price,
        "news_heat_score": heat,
    }


def compute_priced_in_risk(
    *,
    news_heat_score: float | None,
    market_price_confirmation_score: float | None,
    valuation_pressure: float | None,
    fundamental_validation: float | None,
) -> str:
    """Compute priced-in risk from heat, price, valuation, and validation."""

    if (
        news_heat_score is None
        or market_price_confirmation_score is None
        or valuation_pressure is None
        or fundamental_validation is None
    ):
        return "insufficient_data"
    if (
        news_heat_score >= 7.0
        and market_price_confirmation_score >= 7.0
        and valuation_pressure >= 7.0
        and fundamental_validation <= 6.0
    ):
        return "high"
    if news_heat_score >= 6.5 and market_price_confirmation_score >= 6.0 and valuation_pressure >= 6.5:
        return "medium"
    return "low"


def format_overall_score(value: object, lang: str) -> str:
    """Format a nullable score for product summary cards."""

    number = _to_float(value)
    if number is None:
        return OVERALL_TEXT[lang]["score_na"]
    return f"{number:.1f}"


def _to_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
