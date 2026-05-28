"""Local V4.1 catalyst and news-heat framework data.

This module intentionally uses manual framework data only. It is not connected
to live news, filings, or automated analysis.
"""

from __future__ import annotations

from typing import Any

from src.industry_trend_data import industryTrendData


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

CATALYST_GUIDE = {
    "zh": {
        "title": "催化事件说明",
        "event_types_title": "事件类型说明",
        "impact_title": "影响方向说明",
        "confidence_title": "可信度说明",
        "heat_title": "新闻热度说明",
        "columns": {"item": "项目", "meaning": "含义"},
        "event_types": {
            "政策": "政策事件指政府、监管机构、产业政策、补贴、限制、准入规则等变化。它可能改变行业需求、供给、盈利预期或估值环境。",
            "财报": "财报事件指公司季度或年度业绩、业绩指引、利润率、订单、库存等信息。它通常用于验证行业趋势是否转化为真实经营结果。",
            "订单": "订单事件指客户订单、合同、出货、采购计划或 backlog 变化。它通常是判断产业需求是否真实存在的重要线索。",
            "资本开支": "资本开支事件指云厂商、制造商、能源公司、政府或企业扩大投资。它通常会影响上游设备、材料、基础设施和供应链需求。",
            "技术": "技术事件指新产品、技术路线、性能突破、成本下降、产业标准变化等。它可能改变行业竞争格局或打开新的需求空间。",
            "宏观": "宏观事件指利率、汇率、通胀、就业、流动性、经济周期等变化。它通常影响行业估值、需求弹性和风险偏好。",
            "供应链": "供应链事件指产能、库存、交付周期、原材料、物流、供应瓶颈等变化。它可能影响价格、利润率和出货节奏。",
            "价格周期": "价格周期事件指产品价格、商品价格、库存周期、供需缺口等变化。它常见于半导体、资源品、光伏、化工等周期属性较强的行业。",
            "监管": "监管事件指反垄断、出口管制、金融监管、行业规范、安全审查等变化。它可能改变行业竞争规则或风险溢价。",
            "地缘政治": "地缘政治事件指贸易摩擦、制裁、冲突、供应链重构、国家安全相关限制等。它可能影响全球产业链和资产风险偏好。",
            "产品": "产品事件指新品发布、产品迭代、商业化进展、客户验证等。它通常用于观察技术路线是否进入实际市场应用。",
        },
        "impact": {
            "正面": "事件倾向于增强行业需求、盈利预期、价格确认或市场关注度。",
            "中性": "事件对行业趋势影响有限，更多是信息更新。",
            "负面": "事件可能压制需求、利润率、估值或市场风险偏好。",
            "混合": "事件同时包含正面和负面因素，需要结合后续数据观察。",
        },
        "confidence": {
            "高": "事件来源或数据较明确，和行业趋势的关联较直接。",
            "中": "事件有一定参考价值，但仍需要更多数据验证。",
            "低": "事件更多是早期信号、市场传闻或间接线索，需要谨慎解读。",
        },
        "heat": {
            "新闻热度分": "用于描述该行业在 V4.1 本地框架中的关注度强弱，不代表实时新闻统计。",
            "热度等级": "低、中、高、很高，用于快速描述关注度区间。",
            "热度方向": "升温、稳定、降温、分化，用于描述关注度变化的方向。",
        },
    },
    "en": {
        "title": "Catalyst Event Guide",
        "event_types_title": "Event Type Guide",
        "impact_title": "Impact Direction Guide",
        "confidence_title": "Confidence Guide",
        "heat_title": "News Heat Guide",
        "columns": {"item": "Item", "meaning": "Meaning"},
        "event_types": {
            "Policy": "Policy events refer to changes in government actions, regulators, industry policy, subsidies, restrictions, access rules, or similar conditions. They may affect demand, supply, earnings expectations, or valuation conditions.",
            "Earnings": "Earnings events refer to quarterly or annual results, guidance, margins, orders, inventory, and related operating data. They help validate whether an industry trend is translating into operating results.",
            "Order": "Order events refer to customer orders, contracts, shipments, procurement plans, or backlog changes. They are useful clues for judging whether industrial demand is materializing.",
            "Capex": "Capex events refer to expanded investment by cloud vendors, manufacturers, energy companies, governments, or enterprises. They often affect upstream equipment, materials, infrastructure, and supply-chain demand.",
            "Technology": "Technology events refer to new products, technical routes, performance breakthroughs, cost reductions, or industry-standard changes. They may reshape competition or open new demand space.",
            "Macro": "Macro events refer to rates, currencies, inflation, employment, liquidity, and economic cycles. They often affect valuation, demand elasticity, and risk appetite.",
            "Supply Chain": "Supply-chain events refer to capacity, inventory, delivery cycles, raw materials, logistics, and supply bottlenecks. They may affect prices, margins, and shipment timing.",
            "Price Cycle": "Price-cycle events refer to changes in product prices, commodity prices, inventory cycles, and supply-demand gaps. They are common in industries with stronger cyclical attributes.",
            "Regulation": "Regulation events refer to antitrust actions, export controls, financial regulation, industry rules, and security reviews. They may change competitive rules or risk premiums.",
            "Geopolitical": "Geopolitical events refer to trade friction, sanctions, conflicts, supply-chain restructuring, and national-security restrictions. They may affect global supply chains and asset risk appetite.",
            "Product": "Product events refer to launches, iterations, commercialization progress, and customer validation. They help observe whether a technical route is entering real market application.",
        },
        "impact": {
            "Positive": "The event tends to strengthen industry demand, earnings expectations, price confirmation, or market attention.",
            "Neutral": "The event has limited effect on the industry trend and is mainly an information update.",
            "Negative": "The event may weigh on demand, margins, valuation, or market risk appetite.",
            "Mixed": "The event contains both positive and negative elements and requires follow-up data.",
        },
        "confidence": {
            "High": "The event source or data is relatively clear and directly connected to the industry trend.",
            "Medium": "The event has reference value, but still requires more data validation.",
            "Low": "The event is more of an early signal, market rumor, or indirect clue and should be interpreted cautiously.",
        },
        "heat": {
            "News Heat Score": "Describes attention strength in the V4.1 local framework. It is not a live news statistic.",
            "Heat Level": "Low, Medium, High, and Very High provide a quick attention-range label.",
            "Heat Direction": "Rising, Stable, Falling, and Mixed describe the direction of attention changes.",
        },
    },
}

EVENT_TYPE_LABELS["zh"]["consumer_demand"] = "消费需求"
CATALYST_GUIDE["zh"]["event_types"]["消费需求"] = (
    "消费需求事件指客流、复购、消费场景、渠道动销、用户活跃度或服务需求变化。它通常用于观察终端需求是否改善。"
)
CATALYST_GUIDE["en"]["event_types"]["Consumer Demand"] = (
    "Consumer-demand events refer to traffic, repeat purchases, consumption scenarios, channel activity, "
    "user engagement, or service demand changes. They help observe whether end demand is improving."
)


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


CATALYST_PROFILE_BY_CATEGORY = {
    "Technology Growth": {
        "score": 6.8,
        "level": "High",
        "direction": "Stable",
        "summary": "{name} catalysts focus on technology cycles, product validation, capex visibility, and supply-chain execution.",
        "summaryZh": "{nameZh}催化主要关注技术周期、产品验证、资本开支可见度与供应链执行。",
        "events": [
            (
                "technology",
                "Technology route validation remains important",
                "技术路线验证仍是重要线索",
                "mixed",
                "The framework tracks technical progress and commercial validation as catalyst inputs.",
                "框架关注技术进展与商业化验证作为催化输入。",
            ),
            (
                "capex",
                "Capex visibility supports demand monitoring",
                "资本开支可见度支撑需求观察",
                "positive",
                "Infrastructure and enterprise spending are used as framework clues for demand strength.",
                "基础设施与企业支出被作为需求强度的框架线索。",
            ),
        ],
    },
    "New Energy & Manufacturing": {
        "score": 5.9,
        "level": "Medium",
        "direction": "Mixed",
        "summary": "{name} catalysts focus on policy support, order visibility, capacity digestion, and price-cycle repair.",
        "summaryZh": "{nameZh}催化主要关注政策支持、订单可见度、产能消化与价格周期修复。",
        "events": [
            (
                "policy",
                "Policy and project visibility remain key variables",
                "政策与项目可见度仍是关键变量",
                "mixed",
                "The framework tracks policy signals and project timelines as catalysts for manufacturing demand.",
                "框架将政策信号与项目节奏作为制造需求的催化线索。",
            ),
            (
                "price_cycle",
                "Price-cycle repair remains a validation item",
                "价格周期修复仍是验证项",
                "mixed",
                "Pricing, inventory, and utilization are monitored as validation variables.",
                "价格、库存与产能利用率被作为验证变量观察。",
            ),
        ],
    },
    "Commodities": {
        "score": 6.4,
        "level": "Medium",
        "direction": "Stable",
        "summary": "{name} catalysts focus on macro expectations, supply constraints, price cycles, and geopolitical risk.",
        "summaryZh": "{nameZh}催化主要关注宏观预期、供给约束、价格周期与地缘政治风险。",
        "events": [
            (
                "macro",
                "Macro expectations remain a core catalyst input",
                "宏观预期仍是核心催化输入",
                "mixed",
                "The framework tracks rates, currency, and growth expectations as commodity catalyst variables.",
                "框架将利率、汇率与增长预期作为资源品催化变量。",
            ),
            (
                "price_cycle",
                "Supply-demand balance drives price-cycle monitoring",
                "供需平衡驱动价格周期观察",
                "mixed",
                "Inventory, output, and demand gaps are used to monitor price-cycle risk.",
                "库存、产量与需求缺口被用于观察价格周期风险。",
            ),
        ],
    },
    "Consumer": {
        "score": 5.6,
        "level": "Medium",
        "direction": "Mixed",
        "summary": "{name} catalysts focus on consumer demand, product cycles, channel activity, and macro sensitivity.",
        "summaryZh": "{nameZh}催化主要关注消费需求、产品周期、渠道活跃度与宏观敏感度。",
        "events": [
            (
                "consumer_demand",
                "End-demand repair is the main framework clue",
                "终端需求修复是主要框架线索",
                "mixed",
                "Traffic, channel activity, and user engagement are monitored as demand indicators.",
                "客流、渠道动销与用户活跃度被作为需求指标观察。",
            ),
            (
                "earnings",
                "Margin and revenue validation remain important",
                "利润率与收入验证仍然重要",
                "neutral",
                "Operating data is used to check whether demand signals translate into results.",
                "经营数据用于观察需求信号是否转化为业绩结果。",
            ),
        ],
    },
    "Financial & Real Estate": {
        "score": 5.7,
        "level": "Medium",
        "direction": "Mixed",
        "summary": "{name} catalysts focus on rates, policy, regulation, asset quality, and valuation sensitivity.",
        "summaryZh": "{nameZh}催化主要关注利率、政策、监管、资产质量与估值敏感度。",
        "events": [
            (
                "macro",
                "Rate and liquidity expectations remain central",
                "利率与流动性预期仍是核心变量",
                "mixed",
                "The framework tracks rate sensitivity and liquidity as financial-cycle catalysts.",
                "框架将利率敏感度与流动性作为金融周期催化变量。",
            ),
            (
                "regulation",
                "Regulatory signals shape risk premiums",
                "监管信号影响风险溢价",
                "neutral",
                "Policy and regulatory changes may affect competitive rules and valuation conditions.",
                "政策与监管变化可能影响竞争规则与估值环境。",
            ),
        ],
    },
    "Healthcare": {
        "score": 6.1,
        "level": "Medium",
        "direction": "Stable",
        "summary": "{name} catalysts focus on regulation, product milestones, clinical validation, and policy review.",
        "summaryZh": "{nameZh}催化主要关注监管、产品节点、临床验证与政策审查。",
        "events": [
            (
                "product",
                "Product milestones remain key framework inputs",
                "产品节点仍是关键框架输入",
                "mixed",
                "The framework tracks approvals, launches, and validation timelines as catalyst clues.",
                "框架将审批、发布与验证节奏作为催化线索。",
            ),
            (
                "regulation",
                "Regulatory review affects validation timing",
                "监管审查影响验证节奏",
                "neutral",
                "Review rules and policy changes may affect commercialization and risk perception.",
                "审查规则与政策变化可能影响商业化节奏和风险认知。",
            ),
        ],
    },
    "Cyclical & Industrial": {
        "score": 5.8,
        "level": "Medium",
        "direction": "Mixed",
        "summary": "{name} catalysts focus on price cycles, orders, macro demand, supply chains, and policy visibility.",
        "summaryZh": "{nameZh}催化主要关注价格周期、订单、宏观需求、供应链与政策可见度。",
        "events": [
            (
                "price_cycle",
                "Price-cycle and utilization signals remain important",
                "价格周期与开工信号仍然重要",
                "mixed",
                "The framework tracks pricing, utilization, and inventory as cyclical validation inputs.",
                "框架将价格、开工率与库存作为周期验证输入。",
            ),
            (
                "order",
                "Order visibility supports demand validation",
                "订单可见度支撑需求验证",
                "neutral",
                "Backlog, shipments, and project progress are used as demand clues.",
                "订单积压、出货与项目进度被作为需求线索。",
            ),
        ],
    },
}


CATALYST_SCORE_OVERRIDES = {
    "cloud_computing": (7.0, "High", "Stable"),
    "data_center": (7.6, "High", "Rising"),
    "cybersecurity": (6.7, "High", "Stable"),
    "consumer_electronics": (5.8, "Medium", "Mixed"),
    "robotics": (7.2, "High", "Rising"),
    "battery": (5.9, "Medium", "Mixed"),
    "energy_storage": (6.4, "Medium", "Stable"),
    "wind_power": (5.4, "Medium", "Mixed"),
    "power_equipment": (6.6, "High", "Stable"),
    "industrial_automation": (6.2, "Medium", "Stable"),
    "aluminum": (5.8, "Medium", "Mixed"),
    "lithium": (5.6, "Medium", "Mixed"),
    "rare_earth": (6.5, "Medium", "Stable"),
    "natural_gas": (6.2, "Medium", "Mixed"),
    "coal": (5.3, "Medium", "Stable"),
    "liquor": (5.2, "Medium", "Stable"),
    "food_beverage": (5.4, "Medium", "Stable"),
    "tourism": (5.9, "Medium", "Mixed"),
    "hotel": (5.6, "Medium", "Mixed"),
    "aviation": (6.0, "Medium", "Mixed"),
    "gaming": (6.1, "Medium", "Stable"),
    "e_commerce": (6.3, "Medium", "Stable"),
    "insurance": (5.8, "Medium", "Stable"),
    "brokerage": (6.1, "Medium", "Mixed"),
    "reits": (5.5, "Medium", "Mixed"),
    "innovative_drugs": (6.7, "High", "Stable"),
    "cxo": (5.8, "Medium", "Mixed"),
    "medical_devices": (6.0, "Medium", "Stable"),
    "biotechnology": (6.4, "Medium", "Mixed"),
    "ai_healthcare": (6.8, "High", "Rising"),
    "chemicals": (5.7, "Medium", "Mixed"),
    "cement": (4.9, "Medium", "Stable"),
    "shipping": (6.0, "Medium", "Mixed"),
    "ports": (5.5, "Medium", "Stable"),
    "logistics": (5.8, "Medium", "Stable"),
}


def _make_framework_event(
    *,
    date: str,
    event_type: str,
    title: str,
    title_zh: str,
    impact: str,
    description: str,
    description_zh: str,
) -> dict[str, str]:
    return {
        "date": date,
        "title": title,
        "titleZh": title_zh,
        "event_type": event_type,
        "event_typeZh": EVENT_TYPE_LABELS["zh"].get(event_type, event_type),
        "impact": impact,
        "impactZh": IMPACT_LABELS["zh"].get(impact, impact),
        "confidence": "medium",
        "confidenceZh": CONFIDENCE_LABELS["zh"].get("medium", "中"),
        "description": description,
        "descriptionZh": description_zh,
    }


def _build_category_catalyst_record(industry: dict[str, Any]) -> dict[str, Any]:
    profile = CATALYST_PROFILE_BY_CATEGORY.get(industry.get("category"), CATALYST_PROFILE_BY_CATEGORY["Cyclical & Industrial"])
    score, level, direction = CATALYST_SCORE_OVERRIDES.get(
        industry["id"],
        (profile["score"], profile["level"], profile["direction"]),
    )
    name = str(industry.get("name", industry["id"]))
    name_zh = str(industry.get("chineseName", name))
    events = []
    for index, (event_type, title, title_zh, impact, description, description_zh) in enumerate(profile["events"]):
        events.append(
            _make_framework_event(
                date=f"2026-05-{27 - index:02d}",
                event_type=event_type,
                title=f"{name}: {title}",
                title_zh=f"{name_zh}：{title_zh}",
                impact=impact,
                description=description,
                description_zh=description_zh,
            )
        )
    return {
        "heat_score": score,
        "heat_level": level,
        "heat_direction": direction,
        "summary": profile["summary"].format(name=name),
        "summaryZh": profile["summaryZh"].format(nameZh=name_zh),
        "events": events,
    }


def _ensure_minimum_events(industry_id: str, payload: dict[str, Any], industry: dict[str, Any]) -> None:
    if len(payload.get("events", [])) >= 2:
        return
    fallback = _build_category_catalyst_record(industry)
    existing_types = {event.get("event_type") for event in payload.get("events", [])}
    for event in fallback["events"]:
        if event.get("event_type") in existing_types and len(fallback["events"]) > 1:
            continue
        payload.setdefault("events", []).append(event)
        if len(payload["events"]) >= 2:
            return
    while len(payload.get("events", [])) < 2:
        payload.setdefault("events", []).append(fallback["events"][0].copy())


def _complete_all_catalyst_data() -> None:
    for industry in industryTrendData:
        industry_id = industry["id"]
        if industry_id not in INDUSTRY_CATALYST_DATA:
            INDUSTRY_CATALYST_DATA[industry_id] = _build_category_catalyst_record(industry)
        _ensure_minimum_events(industry_id, INDUSTRY_CATALYST_DATA[industry_id], industry)


INDUSTRY_CATALYST_DATA["memory"] = {
    "heat_score": 7.7,
    "heat_level": "High",
    "heat_direction": "Mixed",
    "summary": "Memory catalyst tracking focuses on HBM demand, DRAM / NAND pricing, enterprise SSD demand, and supplier capex discipline.",
    "summaryZh": "存储芯片催化框架重点观察 HBM 需求、DRAM / NAND 价格周期、企业级 SSD 需求和存储厂商资本开支纪律。",
    "events": [
        {
            "date": "2026-05-27",
            "title": "HBM demand remains tied to AI accelerator cycles",
            "titleZh": "HBM 需求仍与 AI 加速器周期高度相关",
            "event_type": "technology",
            "event_typeZh": "技术",
            "impact": "positive",
            "impactZh": "正面",
            "confidence": "medium",
            "confidenceZh": "中",
            "description": "The local framework treats HBM qualification and capacity progress as a key signal for high-end memory demand.",
            "descriptionZh": "本地框架将 HBM 验证与产能进度作为观察高端存储需求的重要线索。",
        },
        {
            "date": "2026-05-26",
            "title": "DRAM and NAND pricing cycle remains a core variable",
            "titleZh": "DRAM 与 NAND 价格周期仍是核心变量",
            "event_type": "price_cycle",
            "event_typeZh": "价格周期",
            "impact": "mixed",
            "impactZh": "混合",
            "confidence": "medium",
            "confidenceZh": "中",
            "description": "Memory pricing can strengthen or weaken by product tier, inventory position, and customer demand.",
            "descriptionZh": "存储价格会随产品层级、库存位置和客户需求变化而增强或转弱。",
        },
        {
            "date": "2026-05-25",
            "title": "Enterprise SSD demand provides a data-center demand signal",
            "titleZh": "企业级 SSD 需求提供数据中心需求线索",
            "event_type": "order",
            "event_typeZh": "订单",
            "impact": "positive",
            "impactZh": "正面",
            "confidence": "medium",
            "confidenceZh": "中",
            "description": "Enterprise SSD activity is used as a framework signal for storage upgrades in data centers.",
            "descriptionZh": "企业级 SSD 活跃度被用于观察数据中心存储升级需求。",
        },
        {
            "date": "2026-05-24",
            "title": "Supplier capex discipline affects later-cycle supply risk",
            "titleZh": "存储厂商资本开支纪律影响后续供给风险",
            "event_type": "capex",
            "event_typeZh": "资本开支",
            "impact": "mixed",
            "impactZh": "混合",
            "confidence": "medium",
            "confidenceZh": "中",
            "description": "Capacity expansion pace can affect supply discipline and future pricing conditions.",
            "descriptionZh": "产能扩张节奏会影响供给纪律和后续价格环境。",
        },
    ],
}


_complete_all_catalyst_data()


def get_catalyst_data(industry_id: str) -> dict[str, Any] | None:
    """Return local V4.1 catalyst data for one industry."""

    return INDUSTRY_CATALYST_DATA.get(industry_id)


def localized_label(mapping: dict[str, dict[str, str]], value: object, lang: str) -> str:
    """Return localized label for a framework code."""

    raw = str(value or "")
    return mapping.get(lang, {}).get(raw, raw)
