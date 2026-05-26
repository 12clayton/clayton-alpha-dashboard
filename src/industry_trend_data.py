"""Mock industry trend data for the Industry Trend Search Engine."""

from __future__ import annotations


TREND_STAGES = [
    "Stage 1: Low-attention Accumulation",
    "Stage 2: Trend Confirmation",
    "Stage 3: Maintrend Expansion",
    "Stage 4: High-heat Divergence",
    "Stage 5: Overpriced Volatility",
    "Stage 6: Trend Cooling",
]

INDUSTRY_STATUSES = [
    "Strong Trend",
    "Trend Intact",
    "Diverging",
    "Weakening",
    "Broken Trend",
    "Overheated",
]

INDUSTRY_CATEGORIES = {
    "Technology Growth": [
        ("semiconductor", "Semiconductor", "半导体", ["chip", "semis", "semiconductor", "半导体", "芯片"]),
        ("cpo_optical_module", "CPO / Optical Module", "CPO / 光模块", ["cpo", "optical module", "光模块", "光通信"]),
        ("ai_compute", "AI Compute", "AI 算力", ["ai compute", "gpu", "ai infrastructure", "算力", "AI算力"]),
        ("cpu", "CPU", "中央处理器", ["cpu", "processor", "processors", "中央处理器"]),
        ("cloud_computing", "Cloud Computing", "云计算", ["cloud", "cloud computing", "云计算", "云服务"]),
        ("data_center", "Data Center", "数据中心", ["data center", "datacenter", "idc", "数据中心"]),
        ("cybersecurity", "Cybersecurity", "网络安全", ["cybersecurity", "security software", "网络安全", "安全软件"]),
        ("consumer_electronics", "Consumer Electronics", "消费电子", ["consumer electronics", "smartphone", "消费电子", "手机产业链"]),
        ("robotics", "Robotics", "机器人", ["robotics", "robot", "humanoid", "机器人", "具身智能"]),
    ],
    "New Energy & Manufacturing": [
        ("ev", "EV", "新能源汽车", ["ev", "electric vehicle", "新能源汽车", "电动车"]),
        ("battery", "Battery", "电池", ["battery", "lithium battery", "电池", "锂电池"]),
        ("solar", "Solar", "光伏", ["solar", "photovoltaic", "pv", "光伏", "太阳能"]),
        ("energy_storage", "Energy Storage", "储能", ["energy storage", "储能", "储能系统"]),
        ("wind_power", "Wind Power", "风电", ["wind", "wind power", "风电"]),
        ("sic", "SiC", "碳化硅", ["sic", "silicon carbide", "碳化硅"]),
        ("power_equipment", "Power Equipment", "电力设备", ["power equipment", "grid equipment", "电力设备", "电网设备"]),
        ("industrial_automation", "Industrial Automation", "工业自动化", ["industrial automation", "automation", "工业自动化", "自动化"]),
    ],
    "Commodities": [
        ("gold", "Gold", "黄金", ["gold", "precious metal", "黄金", "贵金属"]),
        ("copper", "Copper", "铜", ["copper", "铜", "工业金属"]),
        ("aluminum", "Aluminum", "铝", ["aluminum", "aluminium", "铝"]),
        ("lithium", "Lithium", "锂", ["lithium", "锂", "锂资源"]),
        ("rare_earth", "Rare Earth", "稀土", ["rare earth", "rare earths", "稀土"]),
        ("oil", "Oil", "原油", ["oil", "crude oil", "原油", "石油"]),
        ("natural_gas", "Natural Gas", "天然气", ["natural gas", "gas", "天然气"]),
        ("coal", "Coal", "煤炭", ["coal", "煤炭", "动力煤"]),
    ],
    "Consumer": [
        ("liquor", "Liquor", "白酒", ["liquor", "baijiu", "白酒"]),
        ("food_beverage", "Food & Beverage", "食品饮料", ["food beverage", "food & beverage", "食品饮料"]),
        ("tourism", "Tourism", "旅游", ["tourism", "travel", "旅游"]),
        ("hotel", "Hotel", "酒店", ["hotel", "hospitality", "酒店"]),
        ("aviation", "Aviation", "航空", ["aviation", "airline", "航空", "民航"]),
        ("gaming", "Gaming", "游戏", ["gaming", "game", "游戏"]),
        ("e_commerce", "E-commerce", "电商", ["ecommerce", "e-commerce", "online retail", "电商"]),
    ],
    "Financial & Real Estate": [
        ("banking", "Banking", "银行", ["banking", "bank", "银行"]),
        ("insurance", "Insurance", "保险", ["insurance", "保险"]),
        ("brokerage", "Brokerage", "券商", ["brokerage", "securities firm", "券商", "证券"]),
        ("real_estate", "Real Estate", "房地产", ["real estate", "property", "房地产", "地产"]),
        ("reits", "REITs", "不动产信托", ["reits", "reit", "不动产信托", "公募reits"]),
    ],
    "Healthcare": [
        ("innovative_drugs", "Innovative Drugs", "创新药", ["innovative drugs", "biopharma", "创新药"]),
        ("cxo", "CXO", "医药外包", ["cxo", "cro", "cdmo", "医药外包"]),
        ("medical_devices", "Medical Devices", "医疗器械", ["medical devices", "medtech", "医疗器械"]),
        ("biotechnology", "Biotechnology", "生物科技", ["biotechnology", "biotech", "生物科技"]),
        ("ai_healthcare", "AI Healthcare", "AI 医疗", ["ai healthcare", "ai medical", "AI医疗", "医疗AI"]),
    ],
    "Cyclical & Industrial": [
        ("chemicals", "Chemicals", "化工", ["chemicals", "chemical", "化工"]),
        ("cement", "Cement", "水泥", ["cement", "水泥"]),
        ("shipping", "Shipping", "航运", ["shipping", "marine transport", "航运"]),
        ("ports", "Ports", "港口", ["ports", "port", "港口"]),
        ("logistics", "Logistics", "物流", ["logistics", "物流", "供应链"]),
        ("defense", "Defense", "国防军工", ["defense", "aerospace defense", "军工", "国防军工"]),
    ],
}


def _seed_from_text(text: str) -> int:
    return sum(ord(char) for char in text)


def _mock_score(seed: int, offset: int) -> float:
    return round(4.8 + ((seed + offset) % 42) / 10, 1)


def _build_record(item: tuple[str, str, str, list[str]], category: str) -> dict:
    industry_id, name, chinese_name, aliases = item
    seed = _seed_from_text(industry_id)
    status = INDUSTRY_STATUSES[seed % len(INDUSTRY_STATUSES)]
    stage = TREND_STAGES[seed % len(TREND_STAGES)]
    heat_level = ["Low", "Moderate", "High", "Very High"][seed % 4]
    trend_score = _mock_score(seed, 3)
    market_confirmation = _mock_score(seed, 9)
    fundamental_validation = _mock_score(seed, 15)
    valuation_pressure = _mock_score(seed, 21)
    macro_sensitivity = _mock_score(seed, 27)

    return {
        "id": industry_id,
        "name": name,
        "chineseName": chinese_name,
        "category": category,
        "aliases": aliases + [name.lower(), chinese_name],
        "status": status,
        "trendStage": stage,
        "trendScore": trend_score,
        "heatLevel": heat_level,
        "marketConfirmation": market_confirmation,
        "fundamentalValidation": fundamental_validation,
        "valuationPressure": valuation_pressure,
        "macroSensitivity": macro_sensitivity,
        "overview": (
            f"{name} is tracked with a neutral trend framework using mock signals for attention, "
            "price breadth, narrative strength, earnings-cycle validation, and macro exposure."
        ),
        "trendStageExplanation": (
            "The stage label summarizes where the theme sits in the mock trend life cycle, "
            "from low-attention formation to cooling after crowded participation."
        ),
        "heatLevelExplanation": (
            "Heat level reflects attention intensity, market crowding, and short-term narrative density "
            "inside this mock framework."
        ),
        "marketConfirmationExplanation": (
            "Market confirmation measures whether listed proxies, breadth, and relative strength appear aligned "
            "with the industry narrative."
        ),
        "fundamentalValidationExplanation": (
            "Fundamental validation reviews whether revenue, margin, capex, utilization, or policy signals "
            "support the observed trend."
        ),
        "valuationPressureExplanation": (
            "Valuation pressure indicates how much expectation appears embedded relative to the mock growth "
            "and cycle assumptions."
        ),
        "macroSensitivityExplanation": (
            "Macro sensitivity captures exposure to rates, currency, commodity costs, policy cycles, and global demand."
        ),
        "keyDrivers": [
            {
                "name": f"{name} demand cycle",
                "status": "Strong" if trend_score >= 7 else "Moderate",
                "explanation": "Demand indicators in the mock setup show meaningful but category-dependent momentum.",
            },
            {
                "name": "Policy and capex visibility",
                "status": "Moderate",
                "explanation": "Policy, enterprise spending, or capacity plans provide a second layer of validation.",
            },
            {
                "name": "Supply-chain pricing power",
                "status": "Diverging" if valuation_pressure >= 7 else "Stable",
                "explanation": "Pricing and margins are not uniform across the chain, creating different trend quality by layer.",
            },
        ],
        "subSectors": [
            {"name": f"{name} Leaders", "status": "Strong"},
            {"name": "Component Suppliers", "status": "Moderate"},
            {"name": "Infrastructure Providers", "status": "Diverging"},
            {"name": "Application Layer", "status": "Recovering"},
        ],
        "industryChain": {
            "upstream": ["Raw inputs", "Core equipment", "Specialized materials", "Design tools"],
            "midstream": ["Manufacturing", "Integration", "Platform operators", "Distribution"],
            "downstream": ["Enterprise demand", "Consumer adoption", "Public projects", "Global channels"],
        },
        "catalysts": [
            "Capacity cycle changes",
            "Policy or regulation updates",
            "Demand inflection in downstream applications",
        ],
        "riskSignals": [
            "Narrative runs ahead of validation",
            "Margin or pricing divergence",
            "Macro conditions reduce visibility",
        ],
    }


industryTrendData = [
    _build_record(item, category)
    for category, items in INDUSTRY_CATEGORIES.items()
    for item in items
]


SEMICONDUCTOR_DETAIL = {
    "id": "semiconductor",
    "name": "Semiconductor",
    "chineseName": "半导体",
    "category": "Technology Growth",
    "aliases": ["chip", "semis", "semiconductor", "半导体", "芯片"],
    "status": "Trend Intact",
    "trendStage": "Stage 4: High-heat Divergence",
    "trendScore": 7.6,
    "heatLevel": "High",
    "marketConfirmation": 8.1,
    "fundamentalValidation": 7.4,
    "valuationPressure": 7.8,
    "macroSensitivity": 6.9,
    "overview": (
        "Semiconductor remains a structurally important technology cycle with AI compute, memory recovery, "
        "advanced packaging, and equipment localization acting as the main mock research anchors."
    ),
    "trendStageExplanation": (
        "The industry shows broad attention and strong market confirmation, while internal performance and "
        "valuation pressure are beginning to diverge across sub-sectors."
    ),
    "heatLevelExplanation": (
        "High heat level indicates elevated participation and dense narratives, especially around AI chips, "
        "HBM, and advanced packaging capacity."
    ),
    "marketConfirmationExplanation": (
        "Mock market signals show strong relative performance across several semiconductor proxies, though "
        "the breadth is less uniform than the headline narrative."
    ),
    "fundamentalValidationExplanation": (
        "Fundamental validation is moderate-strong, supported by AI server demand and memory recovery, with "
        "consumer electronics still more uneven."
    ),
    "valuationPressureExplanation": (
        "Elevated valuation pressure suggests that future growth assumptions are already heavily reflected "
        "in some parts of the chain."
    ),
    "macroSensitivityExplanation": (
        "The industry is moderately sensitive to rates, export controls, capex cycles, and global electronics demand."
    ),
    "keyDrivers": [
        {"name": "AI compute demand", "status": "Strong", "explanation": "Accelerator and server demand remains the central growth narrative."},
        {"name": "HBM growth", "status": "Strong", "explanation": "High-bandwidth memory capacity is a key bottleneck and validation signal."},
        {"name": "Advanced packaging", "status": "Strong", "explanation": "Packaging capacity and process upgrades connect design demand with production reality."},
    ],
    "subSectors": [
        {"name": "AI Chips", "status": "Strong"},
        {"name": "Memory", "status": "Recovering"},
        {"name": "Foundry", "status": "Diverging"},
        {"name": "Semiconductor Equipment", "status": "Moderate-Strong"},
    ],
    "industryChain": {
        "upstream": ["Equipment", "Materials", "EDA", "IP"],
        "midstream": ["Design", "Foundry", "Packaging & Testing"],
        "downstream": ["AI servers", "Consumer electronics", "Automotive", "Industrial"],
    },
    "catalysts": ["Cloud capex changes", "HBM capacity", "Advanced packaging expansion"],
    "riskSignals": ["Valuation pressure", "Inventory cycle reversal", "Capex slowdown"],
}

industryTrendData = [
    SEMICONDUCTOR_DETAIL if record["id"] == "semiconductor" else record
    for record in industryTrendData
]

GENERIC_INDUSTRY_TEMPLATE = {
    "id": "generic_industry_framework",
    "name": "General Industry Framework",
    "chineseName": "通用行业框架",
    "category": "Generic",
    "aliases": [],
    "status": "Diverging",
    "trendStage": "Stage 2: Trend Confirmation",
    "trendScore": 5.8,
    "heatLevel": "Moderate",
    "marketConfirmation": 5.6,
    "fundamentalValidation": 5.2,
    "valuationPressure": 5.9,
    "macroSensitivity": 6.0,
    "overview": (
        "This template provides a neutral framework for industries that are not yet mapped in the mock dataset."
    ),
    "trendStageExplanation": "A generic stage is shown until dedicated industry signals are available.",
    "heatLevelExplanation": "Heat level should be interpreted as a placeholder for attention and crowding.",
    "marketConfirmationExplanation": "Market confirmation would later combine proxy breadth and relative strength.",
    "fundamentalValidationExplanation": "Fundamental validation would later use revenue, margin, utilization, and order-cycle data.",
    "valuationPressureExplanation": "Valuation pressure would later compare expectation levels with growth validation.",
    "macroSensitivityExplanation": "Macro sensitivity would later measure rates, currency, policy, and demand-cycle impact.",
    "keyDrivers": [
        {"name": "Demand visibility", "status": "Moderate", "explanation": "Track end-market demand and order-cycle changes."},
        {"name": "Supply discipline", "status": "Moderate", "explanation": "Watch capacity additions, inventory, and pricing conditions."},
        {"name": "Policy or technology shift", "status": "Emerging", "explanation": "Monitor regulation, subsidies, standards, or product transitions."},
    ],
    "subSectors": [
        {"name": "Upstream inputs", "status": "Framework"},
        {"name": "Core producers", "status": "Framework"},
        {"name": "Downstream applications", "status": "Framework"},
    ],
    "industryChain": {
        "upstream": ["Resources", "Components", "Technology inputs"],
        "midstream": ["Production", "Platforms", "Service providers"],
        "downstream": ["Enterprise users", "Consumers", "Public sector demand"],
    },
    "catalysts": ["Demand-cycle inflection", "Policy update", "Supply-chain pricing change"],
    "riskSignals": ["Weak market confirmation", "Limited fundamental validation", "Elevated valuation pressure"],
}
