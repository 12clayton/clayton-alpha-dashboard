"""Local V4.1 catalyst and news-heat framework data.

This module intentionally uses manual framework data only. It is not connected
to live news, filings, or automated analysis.
"""

from __future__ import annotations

from typing import Any


EVENT_TYPE_LABELS = {
    "zh": {
        "policy": "政策",
        "earnings": "财报",
        "order": "订单",
        "capex": "资本开支",
        "technology": "技术",
        "macro": "宏观",
        "supply_chain": "供应链",
        "price_cycle": "价格周期",
        "regulation": "监管",
        "geopolitical": "地缘政治",
        "product": "产品",
    },
    "en": {},
}

HEAT_LEVEL_LABELS = {
    "zh": {"Low": "低", "Medium": "中", "High": "高", "Very High": "很高"},
    "en": {},
}

HEAT_DIRECTION_LABELS = {
    "zh": {"Rising": "升温", "Stable": "稳定", "Falling": "降温", "Mixed": "分化"},
    "en": {},
}

IMPACT_LABELS = {
    "zh": {"positive": "正面", "neutral": "中性", "negative": "负面", "mixed": "混合"},
    "en": {},
}

CONFIDENCE_LABELS = {
    "zh": {"high": "高", "medium": "中", "low": "低"},
    "en": {},
}


INDUSTRY_CATALYST_DATA: dict[str, dict[str, Any]] = {
    "semiconductor": {
        "heat_score": 8.2,
        "heat_level": "High",
        "heat_direction": "Rising",
        "summary": "AI infrastructure demand, HBM capacity, and advanced packaging remain the main framework catalysts.",
        "summaryZh": "AI 基础设施需求、HBM 产能与先进封装仍是主要框架催化线索。",
        "events": [
            {
                "date": "2026-05-27",
                "title": "AI data center capex remains a key driver",
                "titleZh": "AI 数据中心资本开支仍是核心驱动",
                "event_type": "capex",
                "event_typeZh": "资本开支",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Framework data tracks cloud infrastructure spending as a demand signal for chips and equipment.",
                "descriptionZh": "框架数据将云基础设施支出作为芯片与设备需求的观察信号。",
            },
            {
                "date": "2026-05-24",
                "title": "Advanced packaging remains a capacity focus",
                "titleZh": "先进封装仍是产能关注点",
                "event_type": "technology",
                "event_typeZh": "技术",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Packaging capacity is used as a framework proxy for high-end compute supply constraints.",
                "descriptionZh": "封装产能被作为高端算力供给约束的框架代理指标。",
            },
        ],
    },
    "cpo_optical_module": {
        "heat_score": 8.0,
        "heat_level": "High",
        "heat_direction": "Mixed",
        "summary": "Bandwidth upgrade cycles support attention, while product-route validation remains uneven.",
        "summaryZh": "带宽升级周期支撑关注度，但产品路线验证仍存在分化。",
        "events": [
            {
                "date": "2026-05-27",
                "title": "800G and 1.6T upgrade cycle remains central",
                "titleZh": "800G 与 1.6T 升级周期仍是核心线索",
                "event_type": "product",
                "event_typeZh": "产品",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework monitors optical bandwidth upgrades as a demand catalyst for module vendors.",
                "descriptionZh": "框架将光通信带宽升级作为模块厂商需求催化线索。",
            }
        ],
    },
    "ai_compute": {
        "heat_score": 8.5,
        "heat_level": "Very High",
        "heat_direction": "Rising",
        "summary": "AI server, accelerator, and power infrastructure themes remain high-attention framework drivers.",
        "summaryZh": "AI 服务器、加速器与电力基础设施主题仍处于高关注框架区间。",
        "events": [
            {
                "date": "2026-05-27",
                "title": "AI infrastructure buildout remains active",
                "titleZh": "AI 基础设施建设仍保持活跃",
                "event_type": "capex",
                "event_typeZh": "资本开支",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Local framework data tracks infrastructure expansion as a catalyst for compute hardware and power systems.",
                "descriptionZh": "本地框架数据将基础设施扩张作为算力硬件与电力系统的催化线索。",
            }
        ],
    },
    "cpu": {
        "heat_score": 6.4,
        "heat_level": "Medium",
        "heat_direction": "Stable",
        "summary": "CPU catalysts are tied to platform refresh cycles and AI PC adoption, with mixed competitive validation.",
        "summaryZh": "CPU 催化主要来自平台更新周期与 AI PC 渗透，竞争格局验证仍偏分化。",
        "events": [
            {
                "date": "2026-05-25",
                "title": "Platform refresh cycle remains the main watch item",
                "titleZh": "平台更新周期仍是主要观察项",
                "event_type": "product",
                "event_typeZh": "产品",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Framework data treats new platform cycles as demand catalysts, while share shifts remain uncertain.",
                "descriptionZh": "框架将新平台周期视为需求催化，但份额变化仍存在不确定性。",
            }
        ],
    },
    "gold": {
        "heat_score": 7.4,
        "heat_level": "High",
        "heat_direction": "Stable",
        "summary": "Gold catalysts are mainly linked to real-rate expectations, currency volatility, and risk hedging demand.",
        "summaryZh": "黄金催化主要与实际利率预期、汇率波动和风险对冲需求相关。",
        "events": [
            {
                "date": "2026-05-26",
                "title": "Macro uncertainty supports defensive attention",
                "titleZh": "宏观不确定性支撑防御关注度",
                "event_type": "macro",
                "event_typeZh": "宏观",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework tracks macro volatility as a catalyst for gold attention and price confirmation.",
                "descriptionZh": "框架将宏观波动作为黄金关注度与价格确认的催化线索。",
            }
        ],
    },
    "sic": {
        "heat_score": 5.8,
        "heat_level": "Medium",
        "heat_direction": "Mixed",
        "summary": "SiC remains linked to EV power systems, but pricing and capacity-cycle signals are mixed.",
        "summaryZh": "碳化硅仍与新能源车功率系统相关，但价格与产能周期信号偏分化。",
        "events": [
            {
                "date": "2026-05-24",
                "title": "Capacity digestion remains a framework risk",
                "titleZh": "产能消化仍是框架风险点",
                "event_type": "supply_chain",
                "event_typeZh": "供应链",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework monitors capacity utilization and pricing pressure as validation variables.",
                "descriptionZh": "框架关注产能利用率与价格压力作为验证变量。",
            }
        ],
    },
    "solar": {
        "heat_score": 5.2,
        "heat_level": "Medium",
        "heat_direction": "Mixed",
        "summary": "Solar catalysts remain tied to policy support and price-cycle repair, while supply pressure persists.",
        "summaryZh": "光伏催化仍与政策支持和价格周期修复相关，但供给压力仍需观察。",
        "events": [
            {
                "date": "2026-05-26",
                "title": "Price-cycle repair remains the key variable",
                "titleZh": "价格周期修复仍是关键变量",
                "event_type": "price_cycle",
                "event_typeZh": "价格周期",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Framework data treats module and material pricing as catalysts for margin validation.",
                "descriptionZh": "框架将组件与材料价格作为利润率验证的催化线索。",
            }
        ],
    },
    "ev": {
        "heat_score": 6.1,
        "heat_level": "Medium",
        "heat_direction": "Mixed",
        "summary": "EV catalysts are divided between product cycles, pricing pressure, and regional demand strength.",
        "summaryZh": "新能源车催化在产品周期、价格压力与区域需求强度之间分化。",
        "events": [
            {
                "date": "2026-05-25",
                "title": "Product cycles remain active but pricing pressure persists",
                "titleZh": "产品周期仍活跃，但价格压力仍存在",
                "event_type": "product",
                "event_typeZh": "产品",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework separates volume growth from margin pressure when reading EV catalysts.",
                "descriptionZh": "框架在观察新能源车催化时区分销量增长与利润率压力。",
            }
        ],
    },
    "copper": {
        "heat_score": 7.1,
        "heat_level": "High",
        "heat_direction": "Stable",
        "summary": "Copper catalysts are tied to electrification demand, supply constraints, and macro growth expectations.",
        "summaryZh": "铜的催化与电气化需求、供给约束和宏观增长预期相关。",
        "events": [
            {
                "date": "2026-05-27",
                "title": "Supply constraints remain a structural monitor",
                "titleZh": "供给约束仍是结构性观察项",
                "event_type": "supply_chain",
                "event_typeZh": "供应链",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework tracks mine supply and electrification demand as catalyst inputs.",
                "descriptionZh": "框架将矿山供给与电气化需求作为催化输入。",
            }
        ],
    },
    "oil": {
        "heat_score": 6.8,
        "heat_level": "Medium",
        "heat_direction": "Stable",
        "summary": "Oil catalysts are driven by supply discipline, geopolitical risk, and demand-cycle expectations.",
        "summaryZh": "原油催化主要来自供给纪律、地缘政治风险与需求周期预期。",
        "events": [
            {
                "date": "2026-05-26",
                "title": "Supply discipline remains a key framework input",
                "titleZh": "供给纪律仍是关键框架输入",
                "event_type": "geopolitical",
                "event_typeZh": "地缘政治",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework separates supply-side support from demand-cycle uncertainty.",
                "descriptionZh": "框架区分供给侧支撑与需求周期不确定性。",
            }
        ],
    },
    "banking": {
        "heat_score": 5.6,
        "heat_level": "Medium",
        "heat_direction": "Mixed",
        "summary": "Banking catalysts are linked to rate expectations, credit quality, and deposit-cost pressure.",
        "summaryZh": "银行催化与利率预期、信用质量和存款成本压力相关。",
        "events": [
            {
                "date": "2026-05-25",
                "title": "Credit quality remains the main validation item",
                "titleZh": "信用质量仍是主要验证项",
                "event_type": "macro",
                "event_typeZh": "宏观",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "Framework data treats credit cost and yield-curve expectations as catalyst variables.",
                "descriptionZh": "框架将信用成本与收益率曲线预期作为催化变量。",
            }
        ],
    },
    "real_estate": {
        "heat_score": 5.0,
        "heat_level": "Medium",
        "heat_direction": "Mixed",
        "summary": "Real estate catalysts depend on financing conditions, occupancy trends, and rate sensitivity.",
        "summaryZh": "房地产催化取决于融资条件、出租率趋势与利率敏感度。",
        "events": [
            {
                "date": "2026-05-24",
                "title": "Rate sensitivity remains elevated",
                "titleZh": "利率敏感度仍偏高",
                "event_type": "macro",
                "event_typeZh": "宏观",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework monitors financing costs and occupancy data as catalyst inputs.",
                "descriptionZh": "框架关注融资成本与出租率数据作为催化输入。",
            }
        ],
    },
    "defense": {
        "heat_score": 7.7,
        "heat_level": "High",
        "heat_direction": "Stable",
        "summary": "Defense catalysts are tied to budget visibility, order backlog, and geopolitical risk.",
        "summaryZh": "军工催化与预算可见度、订单积压和地缘政治风险相关。",
        "events": [
            {
                "date": "2026-05-27",
                "title": "Budget visibility supports framework heat",
                "titleZh": "预算可见度支撑框架热度",
                "event_type": "policy",
                "event_typeZh": "政策",
                "impact": "positive",
                "impactZh": "正面",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework treats budget visibility and backlog as demand validation clues.",
                "descriptionZh": "框架将预算可见度与订单积压作为需求验证线索。",
            }
        ],
    },
    "healthcare": {
        "heat_score": 6.3,
        "heat_level": "Medium",
        "heat_direction": "Stable",
        "summary": "Healthcare catalysts are linked to product cycles, policy review, and clinical validation timelines.",
        "summaryZh": "医药催化与产品周期、政策审查和临床验证节奏相关。",
        "events": [
            {
                "date": "2026-05-26",
                "title": "Product and clinical milestones remain key",
                "titleZh": "产品与临床节点仍是关键线索",
                "event_type": "product",
                "event_typeZh": "产品",
                "impact": "mixed",
                "impactZh": "混合",
                "confidence": "medium",
                "confidenceZh": "中",
                "description": "The framework tracks product milestones and validation timelines as catalyst inputs.",
                "descriptionZh": "框架将产品节点与验证节奏作为催化输入。",
            }
        ],
    },
}


def get_catalyst_data(industry_id: str) -> dict[str, Any] | None:
    """Return local V4.1 catalyst data for one industry."""

    return INDUSTRY_CATALYST_DATA.get(industry_id)


def localized_label(mapping: dict[str, dict[str, str]], value: object, lang: str) -> str:
    """Return localized label for a framework code."""

    raw = str(value or "")
    return mapping.get(lang, {}).get(raw, raw)
