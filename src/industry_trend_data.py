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

CORE_INDUSTRY_OVERRIDES = {
    "cpo_optical_module": {
        "status": "Diverging",
        "trendStage": "Stage 4: High-heat Divergence",
        "summary": (
            "CPO / Optical Module remains tied to AI data-center traffic growth, but mock signals show "
            "sub-sector dispersion between high-speed modules, components, and capacity expansion."
        ),
    },
    "gold": {
        "status": "Trend Intact",
        "trendStage": "Stage 3: Maintrend Expansion",
        "summary": (
            "Gold shows a resilient trend profile in the mock framework, supported by macro hedging demand, "
            "real-rate sensitivity, and central-bank reserve narratives."
        ),
    },
    "banking": {
        "status": "Diverging",
        "trendStage": "Stage 2: Trend Confirmation",
        "summary": (
            "Banking is classified as a diverging financial theme in the mock framework, with balance-sheet "
            "quality, rate-cycle expectations, and credit demand producing uneven confirmation."
        ),
    },
}

industryTrendData = [
    {**record, **CORE_INDUSTRY_OVERRIDES.get(record["id"], {})}
    for record in industryTrendData
]

CORE_INDUSTRY_LOCALIZED_OVERRIDES = {
    "semiconductor": {
        "chineseName": "半导体",
        "aliases": ["chip", "semis", "semiconductor", "半导体", "芯片"],
        "trendStageZh": "第四阶段：高热分化",
        "overviewZh": "半导体是重要的科技周期方向，当前框架重点观察 AI 算力、存储修复、先进封装和设备国产化等线索。",
        "summaryZh": "半导体在 mock 框架中处于趋势仍在但内部开始分化的状态，AI 芯片、HBM 与先进封装是主要观察轴。",
        "trendStageExplanationZh": "行业关注度较高，价格确认较强，但不同子行业之间的表现和估值压力开始分化。",
        "keyDrivers": [
            {
                "name": "AI compute demand",
                "nameZh": "AI 算力需求",
                "status": "Strong",
                "explanation": "Accelerator and server demand remains the central growth narrative.",
                "explanationZh": "加速芯片和 AI 服务器需求仍是核心趋势线索。",
            },
            {
                "name": "HBM growth",
                "nameZh": "HBM 增长",
                "status": "Strong",
                "explanation": "High-bandwidth memory capacity is a key bottleneck and validation signal.",
                "explanationZh": "高带宽存储产能是重要瓶颈，也是趋势验证信号。",
            },
            {
                "name": "Advanced packaging",
                "nameZh": "先进封装",
                "status": "Strong",
                "explanation": "Packaging capacity and process upgrades connect design demand with production reality.",
                "explanationZh": "封装产能和工艺升级连接设计需求与制造落地。",
            },
        ],
        "subSectors": [
            {"name": "AI Chips", "nameZh": "AI 芯片", "status": "Strong"},
            {"name": "Memory", "nameZh": "存储", "status": "Recovering"},
            {"name": "Foundry", "nameZh": "晶圆代工", "status": "Diverging"},
            {"name": "Semiconductor Equipment", "nameZh": "半导体设备", "status": "Moderate-Strong"},
        ],
        "industryChainZh": {
            "upstream": ["设备", "材料", "EDA", "IP"],
            "midstream": ["设计", "晶圆代工", "封装测试"],
            "downstream": ["AI 服务器", "消费电子", "汽车电子", "工业应用"],
        },
        "catalystsZh": ["云厂商资本开支变化", "HBM 产能变化", "先进封装扩产进度"],
        "riskSignalsZh": ["估值压力", "库存周期反转", "资本支出放缓"],
    },
    "cpo_optical_module": {
        "chineseName": "CPO / 光模块",
        "trendStageZh": "第四阶段：高热分化",
        "overviewZh": "CPO / 光模块与 AI 数据中心流量增长密切相关，当前重点观察高速光模块、光芯片、交换机和产能扩张节奏。",
        "summaryZh": "CPO / 光模块在 mock 框架中处于高热分化阶段，需求叙事较强，但不同环节的价格确认和产能节奏并不完全一致。",
        "trendStageExplanationZh": "行业热度较高，代表性公司表现分化，趋势需要继续观察价格确认和供应链兑现度。",
        "keyDrivers": [
            {"name": "AI data-center bandwidth demand", "nameZh": "AI 数据中心带宽需求", "status": "Strong", "explanation": "AI cluster scaling increases high-speed optical interconnect demand.", "explanationZh": "AI 集群扩张提升高速光互连需求。"},
            {"name": "800G / 1.6T upgrade", "nameZh": "800G / 1.6T 升级", "status": "Strong", "explanation": "Module speed upgrades drive product-mix changes.", "explanationZh": "光模块速率升级带动产品结构变化。"},
            {"name": "Silicon photonics and CPO roadmap", "nameZh": "硅光与 CPO 路线", "status": "Diverging", "explanation": "Technology roadmaps may differ across modules, components, and equipment.", "explanationZh": "硅光、CPO 封装和传统光模块路线的推进节奏可能分化。"},
        ],
        "subSectors": [
            {"name": "Optical Modules", "nameZh": "光模块", "status": "Strong"},
            {"name": "Optical Chips", "nameZh": "光芯片", "status": "Moderate-Strong"},
            {"name": "Switching Equipment", "nameZh": "交换设备", "status": "Diverging"},
            {"name": "Fiber Components", "nameZh": "光器件", "status": "Moderate"},
        ],
        "industryChainZh": {
            "upstream": ["光芯片", "激光器", "连接器", "材料"],
            "midstream": ["光模块", "CPO 封装", "交换设备"],
            "downstream": ["AI 数据中心", "云计算网络", "高速通信"],
        },
        "catalystsZh": ["云厂商网络升级", "800G / 1.6T 放量", "AI 集群建设节奏"],
        "riskSignalsZh": ["订单节奏波动", "产能释放过快", "价格竞争加剧"],
    },
    "gold": {
        "chineseName": "黄金",
        "trendStageZh": "第三阶段：主升扩散",
        "overviewZh": "黄金趋势主要与实际利率、美元流动性、央行储备和避险需求相关，当前框架关注价格趋势和矿业股确认度。",
        "summaryZh": "黄金在 mock 框架中趋势仍在，宏观对冲需求和央行储备叙事提供支撑，但仍需观察实际利率和美元变化。",
        "trendStageExplanationZh": "价格趋势相对清晰，相关 ETF 与矿业股的同步确认度是关键观察点。",
        "keyDrivers": [
            {"name": "Real-rate sensitivity", "nameZh": "实际利率敏感度", "status": "Strong", "explanation": "Gold is sensitive to real-rate expectations.", "explanationZh": "黄金对实际利率预期较为敏感。"},
            {"name": "Reserve demand", "nameZh": "储备需求", "status": "Moderate-Strong", "explanation": "Central-bank reserve narratives support long-cycle attention.", "explanationZh": "央行储备叙事支撑长期关注度。"},
            {"name": "Miner confirmation", "nameZh": "矿业股确认", "status": "Diverging", "explanation": "Mining equities may diverge from bullion due to costs and margins.", "explanationZh": "矿业股可能因成本和利润率与金价表现分化。"},
        ],
        "subSectors": [
            {"name": "Bullion ETFs", "nameZh": "黄金 ETF", "status": "Strong"},
            {"name": "Gold Miners", "nameZh": "黄金矿业股", "status": "Diverging"},
            {"name": "Precious Metals", "nameZh": "贵金属", "status": "Moderate-Strong"},
        ],
        "industryChainZh": {
            "upstream": ["金矿资源", "采矿设备", "冶炼"],
            "midstream": ["金条金币", "黄金 ETF", "矿业公司"],
            "downstream": ["央行储备", "珠宝消费", "风险对冲需求"],
        },
        "catalystsZh": ["实际利率变化", "美元指数变化", "央行购金节奏"],
        "riskSignalsZh": ["实际利率回升", "美元走强", "矿业股利润率承压"],
    },
    "banking": {
        "chineseName": "银行",
        "trendStageZh": "第二阶段：趋势确认",
        "overviewZh": "银行主题主要受利率周期、信贷需求、资产质量和资本市场风险偏好影响，当前框架将其识别为分化状态。",
        "summaryZh": "银行在 mock 框架中处于分化观察阶段，利率预期、资产质量和信贷需求共同影响价格确认。",
        "trendStageExplanationZh": "行业尚处于确认阶段，代表性银行之间的价格表现和基本验证存在差异。",
        "keyDrivers": [
            {"name": "Rate-cycle expectations", "nameZh": "利率周期预期", "status": "Moderate", "explanation": "Rate expectations affect net-interest-margin visibility.", "explanationZh": "利率预期影响净息差可见度。"},
            {"name": "Credit demand", "nameZh": "信贷需求", "status": "Diverging", "explanation": "Loan demand differs across consumer, corporate, and capital-market segments.", "explanationZh": "居民、企业和资本市场相关信贷需求存在分化。"},
            {"name": "Asset quality", "nameZh": "资产质量", "status": "Moderate", "explanation": "Credit costs and asset quality remain key validation factors.", "explanationZh": "信用成本和资产质量是重要验证因素。"},
        ],
        "subSectors": [
            {"name": "Large Banks", "nameZh": "大型银行", "status": "Moderate"},
            {"name": "Regional Banks", "nameZh": "区域银行", "status": "Diverging"},
            {"name": "Capital Markets Banks", "nameZh": "资本市场型银行", "status": "Recovering"},
        ],
        "industryChainZh": {
            "upstream": ["存款负债", "批发融资", "资本金"],
            "midstream": ["贷款", "投行业务", "财富管理", "交易业务"],
            "downstream": ["居民部门", "企业部门", "资本市场"],
        },
        "catalystsZh": ["利率路径变化", "信贷需求修复", "资产质量披露"],
        "riskSignalsZh": ["信用成本上升", "净息差承压", "流动性风险偏好下降"],
    },
}

industryTrendData = [
    {**record, **CORE_INDUSTRY_LOCALIZED_OVERRIDES.get(record["id"], {})}
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

GENERIC_INDUSTRY_TEMPLATE.update(
    {
        "chineseName": "通用行业框架",
        "trendStageZh": "第二阶段：趋势确认",
        "overviewZh": "该模板用于展示尚未映射到 mock 数据集的行业通用趋势研究框架。",
        "summaryZh": "当前未找到精确行业映射，因此展示通用趋势框架，重点观察价格确认、基本验证、估值压力和宏观敏感度。",
        "trendStageExplanationZh": "在专门行业信号可用之前，先展示通用趋势确认阶段。",
        "keyDrivers": [
            {"name": "Demand visibility", "nameZh": "需求可见度", "status": "Moderate", "explanation": "Track end-market demand and order-cycle changes.", "explanationZh": "观察终端需求和订单周期变化。"},
            {"name": "Supply discipline", "nameZh": "供给纪律", "status": "Moderate", "explanation": "Watch capacity additions, inventory, and pricing conditions.", "explanationZh": "观察产能、库存和价格环境。"},
            {"name": "Policy or technology shift", "nameZh": "政策或技术变化", "status": "Emerging", "explanation": "Monitor regulation, subsidies, standards, or product transitions.", "explanationZh": "观察监管、补贴、标准或产品迭代。"},
        ],
        "subSectors": [
            {"name": "Upstream inputs", "nameZh": "上游投入", "status": "Framework"},
            {"name": "Core producers", "nameZh": "核心生产环节", "status": "Framework"},
            {"name": "Downstream applications", "nameZh": "下游应用", "status": "Framework"},
        ],
        "industryChainZh": {
            "upstream": ["资源", "零部件", "技术投入"],
            "midstream": ["生产制造", "平台服务", "渠道分发"],
            "downstream": ["企业用户", "消费者", "公共部门需求"],
        },
        "catalystsZh": ["需求周期变化", "政策更新", "供应链价格变化"],
        "riskSignalsZh": ["市场确认偏弱", "基本验证不足", "估值压力上升"],
    }
)
