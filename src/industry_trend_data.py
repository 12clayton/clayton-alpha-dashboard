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

if not any(record["id"] == "healthcare" for record in industryTrendData):
    industryTrendData.append(
        _build_record(
            ("healthcare", "Healthcare", "医药", ["healthcare", "medical", "pharma", "医药", "医疗"]),
            "Healthcare",
        )
    )


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

EXTRA_ALIAS_OVERRIDES = {
    "ai_compute": ["ai compute", "gpu", "ai infrastructure", "AI算力", "算力", "AI基础设施"],
    "sic": ["sic", "silicon carbide", "SiC", "碳化硅"],
    "ev": ["ev", "electric vehicle", "新能源汽车", "新能源车", "电动车"],
    "solar": ["solar", "photovoltaic", "pv", "光伏", "太阳能"],
    "energy_storage": ["energy storage", "储能", "储能系统"],
    "battery": ["battery", "lithium battery", "电池", "锂电池"],
    "robotics": ["robotics", "robot", "humanoid", "机器人", "具身智能"],
    "copper": ["copper", "铜", "工业金属"],
    "oil": ["oil", "crude oil", "原油", "石油"],
    "defense": ["defense", "aerospace defense", "军工", "国防军工"],
    "brokerage": ["brokerage", "securities firm", "券商", "证券"],
    "real_estate": ["real estate", "property", "房地产", "地产"],
}

industryTrendData = [
    {**record, "aliases": EXTRA_ALIAS_OVERRIDES.get(record["id"], record.get("aliases", []))}
    for record in industryTrendData
]


def _localized_theme(
    *,
    chinese_name: str,
    category_zh: str,
    stage_zh: str,
    overview_zh: str,
    summary_zh: str,
    drivers: list[tuple[str, str, str]],
    subsectors: list[tuple[str, str]],
    chain: dict[str, list[str]],
    catalysts: list[str],
    risks: list[str],
    status: str = "Diverging",
    stage: str = "Stage 2: Trend Confirmation",
    trend_score: float = 6.2,
    market_confirmation: float = 6.1,
    fundamental_validation: float = 5.8,
    valuation_pressure: float = 5.9,
    heat_level: str = "Moderate",
) -> dict:
    return {
        "chineseName": chinese_name,
        "categoryZh": category_zh,
        "status": status,
        "trendStage": stage,
        "trendStageZh": stage_zh,
        "trendScore": trend_score,
        "marketConfirmation": market_confirmation,
        "fundamentalValidation": fundamental_validation,
        "valuationPressure": valuation_pressure,
        "heatLevel": heat_level,
        "overviewZh": overview_zh,
        "summaryZh": summary_zh,
        "trendStageExplanationZh": "当前为中性 mock 框架判断，重点观察价格确认、基本验证和产业链内部一致性。",
        "keyDrivers": [
            {
                "name": name,
                "nameZh": name_zh,
                "status": status_label,
                "explanation": f"{name} is tracked as a neutral framework driver.",
                "explanationZh": explanation_zh,
            }
            for name, name_zh, status_label, explanation_zh in drivers
        ],
        "subSectors": [
            {"name": name, "nameZh": name_zh, "status": status_label}
            for name, name_zh, status_label in subsectors
        ],
        "industryChainZh": chain,
        "catalystsZh": catalysts,
        "riskSignalsZh": risks,
    }


V32_LOCALIZED_OVERRIDES = {
    "ai_compute": _localized_theme(
        chinese_name="AI 算力",
        category_zh="科技成长",
        stage_zh="第三阶段：主升扩散",
        overview_zh="AI 算力关注 GPU、网络、服务器、电源散热和数据中心基础设施等环节。",
        summary_zh="AI 算力处于中性偏强的趋势观察阶段，价格确认需要同时观察芯片、服务器和电力散热链条。",
        status="Trend Intact",
        stage="Stage 3: Maintrend Expansion",
        trend_score=7.1,
        market_confirmation=7.0,
        fundamental_validation=6.8,
        valuation_pressure=7.2,
        heat_level="High",
        drivers=[
            ("AI infrastructure capex", "AI 基础设施资本开支", "Strong", "云厂商和企业 AI 基础设施投入是主要观察线索。"),
            ("Accelerator demand", "加速芯片需求", "Strong", "GPU 和加速卡需求影响算力链条景气度。"),
            ("Power and cooling constraints", "电力与散热约束", "Diverging", "电力、散热和机柜交付可能造成环节分化。"),
        ],
        subsectors=[("AI chips", "AI 芯片", "Strong"), ("Servers", "服务器", "Moderate-Strong"), ("Networking", "高速网络", "Strong"), ("Power cooling", "电源散热", "Diverging")],
        chain={"upstream": ["芯片", "电源", "散热", "高速网络"], "midstream": ["AI 服务器", "机柜", "数据中心集成"], "downstream": ["云厂商", "企业 AI 应用", "模型训练与推理"]},
        catalysts=["云资本开支变化", "AI 服务器交付节奏", "数据中心电力约束变化"],
        risks=["估值压力", "供应链交付不均衡", "资本开支节奏放缓"],
    ),
    "cpu": _localized_theme(
        chinese_name="CPU",
        category_zh="科技成长",
        stage_zh="第二阶段：趋势确认",
        overview_zh="CPU 关注通用计算、服务器处理器、PC 周期和代工产能等环节。",
        summary_zh="CPU 处于趋势确认阶段，服务器和端侧需求修复是主要观察点。",
        drivers=[("Server CPU cycle", "服务器 CPU 周期", "Moderate", "服务器更新周期影响需求确认。"), ("PC recovery", "PC 需求修复", "Recovering", "PC 出货和库存变化影响短期表现。"), ("Foundry supply", "代工供给", "Moderate", "先进制程产能影响产品迭代。")],
        subsectors=[("Server CPU", "服务器 CPU", "Moderate"), ("PC CPU", "PC CPU", "Recovering"), ("Mobile processors", "移动处理器", "Diverging")],
        chain={"upstream": ["EDA", "IP", "先进制程"], "midstream": ["CPU 设计", "晶圆代工", "封装测试"], "downstream": ["服务器", "PC", "移动设备"]},
        catalysts=["服务器更新周期", "PC 库存变化", "先进制程产品发布"],
        risks=["需求修复不均衡", "竞争格局变化", "库存周期反复"],
    ),
    "cloud_computing": _localized_theme(
        chinese_name="云计算",
        category_zh="科技成长",
        stage_zh="第二阶段：趋势确认",
        overview_zh="云计算关注云厂商资本开支、企业 IT 支出、软件订阅和 AI 云服务需求。",
        summary_zh="云计算处于趋势确认阶段，AI 云需求与企业软件支出共同影响价格确认。",
        drivers=[("Cloud capex", "云资本开支", "Moderate-Strong", "云厂商资本开支决定基础设施需求。"), ("Enterprise software demand", "企业软件需求", "Moderate", "企业 IT 支出影响云软件景气度。"), ("AI cloud services", "AI 云服务", "Strong", "AI 服务增加算力和平台需求。")],
        subsectors=[("Cloud platforms", "云平台", "Strong"), ("SaaS", "SaaS 软件", "Moderate"), ("Cloud infrastructure", "云基础设施", "Moderate-Strong")],
        chain={"upstream": ["芯片", "服务器", "网络设备"], "midstream": ["云平台", "数据库", "SaaS"], "downstream": ["企业客户", "开发者", "AI 应用"]},
        catalysts=["云收入增长", "AI 服务渗透率", "企业软件预算变化"],
        risks=["资本开支波动", "企业预算收缩", "估值压力"],
    ),
    "data_center": _localized_theme(
        chinese_name="数据中心",
        category_zh="科技成长",
        stage_zh="第三阶段：主升扩散",
        stage="Stage 3: Maintrend Expansion",
        overview_zh="数据中心关注机柜、电力、散热、服务器、网络设备和云厂商扩容节奏。",
        summary_zh="数据中心处于主升扩散观察阶段，电力和散热约束使链条内部表现可能分化。",
        status="Trend Intact",
        trend_score=7.0,
        market_confirmation=6.9,
        heat_level="High",
        drivers=[("Power capacity", "电力容量", "Strong", "电力供给是数据中心扩张的重要约束。"), ("Cooling demand", "散热需求", "Moderate-Strong", "高密度机柜提高散热系统需求。"), ("AI server deployment", "AI 服务器部署", "Strong", "AI 服务器交付影响数据中心建设节奏。")],
        subsectors=[("Power equipment", "电力设备", "Strong"), ("Cooling systems", "散热系统", "Moderate-Strong"), ("Network equipment", "网络设备", "Strong")],
        chain={"upstream": ["电力设备", "芯片", "服务器", "散热材料"], "midstream": ["数据中心建设", "机柜集成", "运维服务"], "downstream": ["云厂商", "AI 训练", "企业计算"]},
        catalysts=["云厂商扩容", "电力审批进度", "AI 服务器交付"],
        risks=["电力瓶颈", "建设节奏延后", "资本开支波动"],
    ),
    "sic": _localized_theme(
        chinese_name="碳化硅",
        category_zh="新能源与制造",
        stage_zh="第二阶段：趋势确认",
        overview_zh="碳化硅关注功率半导体、车载逆变器、充电桩和工业电源等应用。",
        summary_zh="碳化硅处于趋势确认阶段，需求增长与价格压力需要同步观察。",
        drivers=[("EV inverter demand", "车载逆变器需求", "Moderate", "新能源车逆变器是重要应用场景。"), ("Industrial power demand", "工业电源需求", "Moderate", "工业和能源场景提供增量需求。"), ("Substrate supply", "衬底供给", "Diverging", "衬底供给与价格变化可能造成分化。")],
        subsectors=[("Substrates", "衬底", "Diverging"), ("Power devices", "功率器件", "Moderate"), ("Modules", "功率模块", "Moderate")],
        chain={"upstream": ["衬底", "外延片", "设备"], "midstream": ["功率器件", "模块封装", "测试"], "downstream": ["新能源车", "充电桩", "工业电源"]},
        catalysts=["新能源车需求变化", "衬底价格变化", "功率模块放量"],
        risks=["价格竞争", "产能释放过快", "下游需求波动"],
    ),
    "ev": _localized_theme(
        chinese_name="新能源车",
        category_zh="新能源与制造",
        stage_zh="第二阶段：趋势确认",
        overview_zh="新能源车关注整车销量、价格竞争、供应链成本和智能化配置。",
        summary_zh="新能源车处于趋势确认阶段，销量修复和价格竞争共同影响趋势质量。",
        drivers=[("Delivery growth", "交付增长", "Moderate", "销量和交付节奏是核心观察指标。"), ("Price competition", "价格竞争", "Diverging", "价格策略影响利润率和行业分化。"), ("Smart features", "智能化配置", "Moderate", "智能驾驶和座舱配置影响产品竞争力。")],
        subsectors=[("EV makers", "整车", "Diverging"), ("Battery chain", "电池链", "Moderate"), ("Charging", "充电设施", "Recovering")],
        chain={"upstream": ["电池材料", "芯片", "电机电控"], "midstream": ["整车制造", "电池系统", "智能驾驶"], "downstream": ["消费者", "充电网络", "出行服务"]},
        catalysts=["月度交付", "价格策略变化", "智能驾驶功能迭代"],
        risks=["价格竞争加剧", "需求波动", "供应链成本变化"],
    ),
    "solar": _localized_theme(
        chinese_name="光伏",
        category_zh="新能源与制造",
        stage_zh="第六阶段：趋势降温",
        stage="Stage 6: Trend Cooling",
        overview_zh="光伏关注装机需求、组件价格、硅料供需和海外政策环境。",
        summary_zh="光伏处于趋势降温观察阶段，价格压力和供需再平衡是主要变量。",
        status="Weakening",
        trend_score=5.4,
        market_confirmation=5.2,
        valuation_pressure=5.7,
        drivers=[("Installation demand", "装机需求", "Moderate", "全球装机需求影响出货节奏。"), ("Module pricing", "组件价格", "Weakening", "价格压力影响利润率。"), ("Supply rebalancing", "供需再平衡", "Diverging", "硅料、硅片和组件环节再平衡速度不同。")],
        subsectors=[("Polysilicon", "硅料", "Weakening"), ("Modules", "组件", "Diverging"), ("Inverters", "逆变器", "Recovering")],
        chain={"upstream": ["硅料", "硅片", "银浆"], "midstream": ["电池片", "组件", "逆变器"], "downstream": ["电站", "工商业屋顶", "户用需求"]},
        catalysts=["装机数据", "组件价格变化", "海外政策变化"],
        risks=["产能过剩", "价格压力", "贸易政策变化"],
    ),
    "energy_storage": _localized_theme(
        chinese_name="储能",
        category_zh="新能源与制造",
        stage_zh="第二阶段：趋势确认",
        overview_zh="储能关注电池系统、逆变器、电网侧项目和工商业储能需求。",
        summary_zh="储能处于趋势确认阶段，项目落地和盈利模型仍需持续观察。",
        drivers=[("Grid storage projects", "电网侧项目", "Moderate", "项目招标和并网节奏影响需求。"), ("Commercial storage", "工商业储能", "Moderate", "电价机制影响工商业储能回报。"), ("Battery cost", "电池成本", "Diverging", "电池价格变化影响系统成本。")],
        subsectors=[("Battery systems", "电池系统", "Moderate"), ("PCS", "储能变流器", "Moderate"), ("Grid projects", "电网侧项目", "Diverging")],
        chain={"upstream": ["电芯", "BMS", "PCS"], "midstream": ["储能系统集成", "项目建设", "运维"], "downstream": ["电网侧", "工商业", "户用储能"]},
        catalysts=["储能招标", "电价机制变化", "电池成本变化"],
        risks=["项目收益波动", "价格竞争", "并网节奏延后"],
    ),
    "battery": _localized_theme(
        chinese_name="电池",
        category_zh="新能源与制造",
        stage_zh="第二阶段：趋势确认",
        overview_zh="电池关注动力电池、储能电池、材料价格和产能利用率。",
        summary_zh="电池处于趋势确认阶段，需求修复和材料价格变化共同影响链条表现。",
        drivers=[("EV battery demand", "动力电池需求", "Moderate", "新能源车销量影响动力电池需求。"), ("Storage battery demand", "储能电池需求", "Moderate-Strong", "储能项目增加电池需求来源。"), ("Material prices", "材料价格", "Diverging", "锂、镍等材料价格影响利润率。")],
        subsectors=[("Cells", "电芯", "Moderate"), ("Materials", "电池材料", "Diverging"), ("Storage batteries", "储能电池", "Moderate-Strong")],
        chain={"upstream": ["锂资源", "正负极材料", "隔膜", "电解液"], "midstream": ["电芯", "电池包", "BMS"], "downstream": ["新能源车", "储能", "消费电子"]},
        catalysts=["电池装机数据", "材料价格变化", "储能订单"],
        risks=["产能利用率下降", "材料价格波动", "价格竞争"],
    ),
    "robotics": _localized_theme(
        chinese_name="机器人",
        category_zh="科技成长",
        stage_zh="第二阶段：趋势确认",
        overview_zh="机器人关注工业自动化、手术机器人、仓储物流和具身智能等方向。",
        summary_zh="机器人处于趋势确认阶段，应用落地和成本下降是主要观察点。",
        drivers=[("Industrial automation", "工业自动化", "Moderate", "制造业自动化升级影响需求。"), ("Embodied AI", "具身智能", "Emerging", "AI 模型进展提升长期关注度。"), ("Medical robotics", "医疗机器人", "Moderate-Strong", "手术机器人是成熟应用方向。")],
        subsectors=[("Industrial robots", "工业机器人", "Moderate"), ("Medical robots", "医疗机器人", "Moderate-Strong"), ("Humanoid robots", "人形机器人", "Emerging")],
        chain={"upstream": ["减速器", "伺服系统", "传感器", "芯片"], "midstream": ["机器人本体", "控制系统", "系统集成"], "downstream": ["制造业", "医疗", "物流", "服务场景"]},
        catalysts=["应用场景落地", "核心零部件降本", "AI 模型能力提升"],
        risks=["商业化进度慢", "成本下降不及预期", "订单波动"],
    ),
    "copper": _localized_theme(
        chinese_name="铜",
        category_zh="大宗商品",
        stage_zh="第二阶段：趋势确认",
        overview_zh="铜关注全球制造业需求、电网投资、新能源用铜和矿端供给。",
        summary_zh="铜处于趋势确认阶段，宏观需求和供给扰动共同影响价格确认。",
        drivers=[("Grid investment", "电网投资", "Moderate-Strong", "电网建设提升铜需求。"), ("Mine supply", "矿端供给", "Diverging", "矿山扰动影响供应预期。"), ("Global demand", "全球需求", "Moderate", "制造业周期影响铜价趋势。")],
        subsectors=[("Copper miners", "铜矿企业", "Moderate-Strong"), ("Copper ETFs", "铜 ETF", "Moderate"), ("Industrial metals", "工业金属", "Diverging")],
        chain={"upstream": ["铜矿", "冶炼", "精炼"], "midstream": ["铜材", "线缆", "合金"], "downstream": ["电网", "新能源", "建筑", "制造业"]},
        catalysts=["电网投资数据", "矿端供给扰动", "制造业景气变化"],
        risks=["全球需求走弱", "美元走强", "库存上升"],
    ),
    "oil": _localized_theme(
        chinese_name="原油",
        category_zh="大宗商品",
        stage_zh="第二阶段：趋势确认",
        overview_zh="原油关注供需平衡、库存、OPEC 产量政策和全球出行需求。",
        summary_zh="原油处于趋势确认阶段，供给纪律和需求变化共同影响价格表现。",
        drivers=[("Supply discipline", "供给纪律", "Moderate", "产量政策影响供给预期。"), ("Inventory cycle", "库存周期", "Diverging", "库存变化影响短期价格确认。"), ("Travel demand", "出行需求", "Moderate", "交通和航空需求影响消费端。")],
        subsectors=[("Oil ETFs", "原油 ETF", "Moderate"), ("Integrated oil", "综合油气", "Moderate"), ("Oil services", "油服", "Diverging")],
        chain={"upstream": ["勘探", "开采", "油服"], "midstream": ["运输", "管道", "炼化"], "downstream": ["成品油", "化工", "航空和交通"]},
        catalysts=["OPEC 产量政策", "库存数据", "全球需求变化"],
        risks=["需求走弱", "供应意外增加", "地缘风险波动"],
    ),
    "defense": _localized_theme(
        chinese_name="军工",
        category_zh="周期与工业",
        stage_zh="第二阶段：趋势确认",
        overview_zh="军工关注国防预算、订单节奏、航空航天和电子系统需求。",
        summary_zh="军工处于趋势确认阶段，预算和订单兑现节奏是主要观察点。",
        drivers=[("Defense budget", "国防预算", "Moderate-Strong", "预算变化影响行业需求。"), ("Order delivery", "订单交付", "Moderate", "订单交付节奏影响业绩验证。"), ("Aerospace systems", "航空航天系统", "Moderate", "航空航天装备是重要方向。")],
        subsectors=[("Aerospace", "航空航天", "Moderate"), ("Defense electronics", "军工电子", "Moderate-Strong"), ("Shipbuilding", "舰船装备", "Diverging")],
        chain={"upstream": ["材料", "电子元件", "发动机"], "midstream": ["整机装备", "系统集成", "军工电子"], "downstream": ["国防需求", "航空航天", "安全保障"]},
        catalysts=["国防预算变化", "订单交付节奏", "航空航天项目进展"],
        risks=["订单节奏延后", "成本压力", "估值压力"],
    ),
    "healthcare": _localized_theme(
        chinese_name="医药",
        category_zh="医疗健康",
        stage_zh="第二阶段：趋势确认",
        overview_zh="医药关注创新药、医疗服务、器械、生物科技和支付政策等方向。",
        summary_zh="医药处于趋势确认阶段，产品周期、支付环境和市场风险偏好共同影响价格确认。",
        drivers=[("Product cycle", "产品周期", "Moderate", "新产品和适应症拓展影响增长验证。"), ("Policy environment", "政策环境", "Diverging", "支付和监管环境影响估值与需求。"), ("Biotech funding", "生物科技融资", "Moderate", "融资环境影响研发型公司表现。")],
        subsectors=[("Innovative drugs", "创新药", "Diverging"), ("Medical devices", "医疗器械", "Moderate"), ("Biotechnology", "生物科技", "Moderate")],
        chain={"upstream": ["研发", "原料", "临床服务"], "midstream": ["药品", "器械", "生产制造"], "downstream": ["医院", "药房", "患者需求"]},
        catalysts=["新产品进展", "医保和支付政策", "研发数据披露"],
        risks=["政策不确定性", "研发失败", "支付压力"],
    ),
    "brokerage": _localized_theme(
        chinese_name="券商",
        category_zh="金融地产",
        stage_zh="第二阶段：趋势确认",
        overview_zh="券商关注交易活跃度、资本市场融资、财富管理和利率环境。",
        summary_zh="券商处于趋势确认阶段，市场成交和资本市场活动是主要观察变量。",
        drivers=[("Trading activity", "交易活跃度", "Moderate", "成交额影响经纪业务收入。"), ("Capital markets activity", "资本市场活动", "Diverging", "融资和承销环境影响投行业务。"), ("Wealth management", "财富管理", "Moderate", "客户资产规模影响长期收入质量。")],
        subsectors=[("Retail brokers", "零售券商", "Moderate"), ("Investment banks", "投行券商", "Diverging"), ("Wealth platforms", "财富平台", "Moderate")],
        chain={"upstream": ["客户资产", "交易系统", "资本金"], "midstream": ["经纪业务", "投行业务", "财富管理"], "downstream": ["个人客户", "机构客户", "资本市场"]},
        catalysts=["市场成交额变化", "IPO 和再融资节奏", "财富管理规模变化"],
        risks=["市场活跃度下降", "投行业务放缓", "利率波动"],
    ),
    "real_estate": _localized_theme(
        chinese_name="房地产",
        category_zh="金融地产",
        stage_zh="第二阶段：趋势确认",
        overview_zh="房地产关注 REITs、商业地产、住宅销售、融资环境和利率周期。",
        summary_zh="房地产处于趋势确认阶段，不同资产类型的价格确认和基本验证存在分化。",
        drivers=[("Rate cycle", "利率周期", "Moderate", "利率变化影响估值和融资成本。"), ("Property demand", "物业需求", "Diverging", "商业地产和住宅需求存在分化。"), ("Balance-sheet repair", "资产负债表修复", "Moderate", "融资环境影响行业稳定性。")],
        subsectors=[("REITs", "REITs", "Moderate"), ("Industrial properties", "产业地产", "Moderate-Strong"), ("Retail properties", "零售地产", "Diverging")],
        chain={"upstream": ["土地", "融资", "建筑材料"], "midstream": ["开发运营", "物业管理", "REITs"], "downstream": ["租户", "消费者", "企业需求"]},
        catalysts=["利率变化", "租金和空置率变化", "融资环境改善"],
        risks=["利率上行", "空置率上升", "资产估值压力"],
    ),
}

for shared_id in ["innovative_drugs", "biotechnology", "medical_devices"]:
    V32_LOCALIZED_OVERRIDES[shared_id] = {
        **V32_LOCALIZED_OVERRIDES["healthcare"],
        "chineseName": {
            "innovative_drugs": "创新药",
            "biotechnology": "生物科技",
            "medical_devices": "医疗器械",
        }[shared_id],
    }

industryTrendData = [
    {**record, **V32_LOCALIZED_OVERRIDES.get(record["id"], {})}
    for record in industryTrendData
]

LIQUOR_DATA_OVERRIDE = {
    "categoryZh": "消费 / 白酒",
    "status": "Diverging",
    "trendStage": "Stage 2: Trend Confirmation",
    "trendStageZh": "第二阶段：趋势确认",
    "trendScore": 5.8,
    "marketConfirmation": 5.4,
    "fundamentalValidation": 5.7,
    "valuationPressure": 6.1,
    "heatLevel": "Moderate",
    "overview": (
        "Liquor is tracked as a consumer-demand and channel-inventory theme, with premium demand, "
        "wholesale price stability, banquet activity, and brand concentration as the main framework inputs."
    ),
    "overviewZh": "白酒作为消费需求与渠道库存主题进行观察，重点关注高端需求、批价稳定性、宴席场景、商务消费和品牌集中度。",
    "summary": (
        "Liquor remains in a neutral framework stage. Demand recovery, channel inventory, and wholesale "
        "price stability are the main variables for trend confirmation."
    ),
    "summaryZh": "白酒处于中性趋势确认观察阶段，需求修复、渠道库存和批价稳定性是判断趋势质量的核心变量。",
    "keyDrivers": [
        {
            "name": "Premium liquor demand",
            "nameZh": "高端酒需求",
            "status": "Moderate",
            "explanation": "Premium demand is used to observe the resilience of higher-end consumption scenarios.",
            "explanationZh": "高端酒需求用于观察较高端消费场景的韧性。",
        },
        {
            "name": "Channel inventory",
            "nameZh": "渠道库存",
            "status": "Diverging",
            "explanation": "Distributor inventory changes affect shipment rhythm and channel confidence.",
            "explanationZh": "经销渠道库存变化会影响出货节奏和渠道信心。",
        },
        {
            "name": "Wholesale price stability",
            "nameZh": "批价稳定性",
            "status": "Moderate",
            "explanation": "Wholesale price stability is an important clue for channel health.",
            "explanationZh": "批价稳定性是观察渠道健康度的重要线索。",
        },
        {
            "name": "Banquet and business consumption",
            "nameZh": "宴席与商务消费",
            "status": "Moderate",
            "explanation": "Banquet and business consumption scenarios influence demand visibility.",
            "explanationZh": "宴席与商务消费场景影响需求可见度。",
        },
        {
            "name": "Brand concentration",
            "nameZh": "品牌集中度",
            "status": "Moderate-Strong",
            "explanation": "Brand concentration affects pricing power and demand resilience.",
            "explanationZh": "品牌集中度影响定价能力和需求韧性。",
        },
    ],
    "subSectors": [
        {"name": "Premium baijiu", "nameZh": "高端白酒", "status": "Moderate-Strong"},
        {"name": "Sub-premium baijiu", "nameZh": "次高端白酒", "status": "Diverging"},
        {"name": "Regional brands", "nameZh": "区域酒", "status": "Moderate"},
        {"name": "Mass-market liquor", "nameZh": "大众酒", "status": "Stable"},
        {"name": "Distribution channels", "nameZh": "经销渠道", "status": "Diverging"},
    ],
    "industryChain": {
        "upstream": ["Grain", "Packaging materials", "Fermentation starters", "Base liquor"],
        "midstream": ["Liquor production", "Brand operation", "Channel distribution", "Inventory management"],
        "downstream": ["Banquet consumption", "Business consumption", "Gift demand", "Personal consumption"],
    },
    "industryChainZh": {
        "upstream": ["粮食", "包装材料", "酒曲", "基酒"],
        "midstream": ["白酒生产", "品牌运营", "渠道分销", "库存管理"],
        "downstream": ["宴席消费", "商务消费", "礼赠需求", "个人消费"],
    },
    "catalysts": [
        "Banquet consumption recovery",
        "Wholesale price stabilization",
        "Channel inventory digestion",
        "Brand concentration changes",
    ],
    "catalystsZh": [
        "宴席消费修复",
        "批价企稳",
        "渠道库存消化",
        "品牌集中度变化",
    ],
    "riskSignals": [
        "Wholesale price decline",
        "Rising channel inventory",
        "Weaker-than-expected consumption recovery",
        "Marketing expense pressure",
        "Policy or business-consumption constraints",
    ],
    "riskSignalsZh": [
        "批价下行",
        "渠道库存升高",
        "消费修复不及预期",
        "费用投放压力",
        "政策或商务消费约束",
    ],
}

industryTrendData = [
    {**record, **LIQUOR_DATA_OVERRIDE} if record["id"] == "liquor" else record
    for record in industryTrendData
]


def _semantic_quality_override(
    subsectors: list[tuple[str, str]],
    chain: dict[str, list[str]],
    chain_zh: dict[str, list[str]],
) -> dict:
    return {
        "subSectors": [
            {"name": name, "nameZh": name_zh, "status": "Framework"}
            for name, name_zh in subsectors
        ],
        "industryChain": chain,
        "industryChainZh": chain_zh,
    }


SEMANTIC_QUALITY_OVERRIDES = {
    "food_beverage": _semantic_quality_override(
        [("Staple food", "主食"), ("Beverages", "饮料"), ("Condiments", "调味品"), ("Dairy products", "乳制品"), ("Retail channels", "零售渠道")],
        {"upstream": ["Agricultural inputs", "Packaging", "Food ingredients"], "midstream": ["Food processing", "Brand operation", "Distribution"], "downstream": ["Retail", "Restaurants", "Household consumption"]},
        {"upstream": ["农产品", "包装材料", "食品原料"], "midstream": ["食品加工", "品牌运营", "渠道分销"], "downstream": ["零售渠道", "餐饮渠道", "家庭消费"]},
    ),
    "tourism": _semantic_quality_override(
        [("Domestic travel", "国内游"), ("Outbound travel", "出境游"), ("Scenic spots", "景区"), ("Travel agencies", "旅行社"), ("Online travel platforms", "在线旅游平台")],
        {"upstream": ["Transport capacity", "Hotel supply", "Tourism resources"], "midstream": ["Travel products", "Booking platforms", "Tour operators"], "downstream": ["Leisure travelers", "Family travel", "Business travel"]},
        {"upstream": ["交通运力", "酒店供给", "旅游资源"], "midstream": ["旅游产品", "预订平台", "旅行服务商"], "downstream": ["休闲游客", "家庭出游", "商务出行"]},
    ),
    "hotel": _semantic_quality_override(
        [("Luxury hotels", "高端酒店"), ("Business hotels", "商务酒店"), ("Economy hotels", "经济型酒店"), ("Resort hotels", "度假酒店"), ("Hotel management", "酒店管理")],
        {"upstream": ["Property assets", "Labor", "Supplies"], "midstream": ["Hotel operation", "Room pricing", "Membership systems"], "downstream": ["Business guests", "Tourists", "Meetings and events"]},
        {"upstream": ["物业资产", "人力服务", "酒店用品"], "midstream": ["酒店运营", "房价管理", "会员体系"], "downstream": ["商务客群", "旅游客群", "会议活动"]},
    ),
    "aviation": _semantic_quality_override(
        [("Full-service airlines", "全服务航空"), ("Low-cost airlines", "低成本航空"), ("Airports", "机场"), ("Aircraft leasing", "飞机租赁"), ("Air travel services", "航空出行服务")],
        {"upstream": ["Aircraft", "Aviation fuel", "Airport slots"], "midstream": ["Passenger airlines", "Route networks", "Revenue management"], "downstream": ["Business travel", "Leisure travel", "Cargo demand"]},
        {"upstream": ["飞机", "航油", "机场时刻"], "midstream": ["客运航空", "航线网络", "收益管理"], "downstream": ["商务出行", "休闲出行", "货运需求"]},
    ),
    "gaming": _semantic_quality_override(
        [("Mobile games", "移动游戏"), ("PC games", "PC 游戏"), ("Console games", "主机游戏"), ("Game publishing", "游戏发行"), ("Esports", "电竞")],
        {"upstream": ["Game IP", "Development talent", "Content tools"], "midstream": ["Game development", "Publishing", "Live operations"], "downstream": ["Players", "Streaming communities", "Esports audiences"]},
        {"upstream": ["游戏 IP", "研发人才", "内容工具"], "midstream": ["游戏研发", "游戏发行", "长线运营"], "downstream": ["玩家用户", "直播社区", "电竞观众"]},
    ),
    "e_commerce": _semantic_quality_override(
        [("Marketplace platforms", "综合电商"), ("Cross-border e-commerce", "跨境电商"), ("Live commerce", "直播电商"), ("Logistics services", "履约物流"), ("Merchant services", "商家服务")],
        {"upstream": ["Merchants", "Brands", "Warehousing"], "midstream": ["E-commerce platforms", "Payment and fulfillment", "Marketing services"], "downstream": ["Online consumers", "Private-domain traffic", "Cross-border buyers"]},
        {"upstream": ["商家", "品牌", "仓储"], "midstream": ["电商平台", "支付与履约", "营销服务"], "downstream": ["线上消费者", "私域流量", "跨境买家"]},
    ),
    "banking": _semantic_quality_override(
        [("Large banks", "大型银行"), ("Regional banks", "区域银行"), ("Retail banking", "零售银行"), ("Corporate banking", "对公银行"), ("Wealth management", "财富管理")],
        {"upstream": ["Deposits", "Capital", "Funding markets"], "midstream": ["Lending", "Asset-liability management", "Risk control"], "downstream": ["Households", "Corporates", "Public-sector clients"]},
        {"upstream": ["存款", "资本金", "同业资金"], "midstream": ["信贷投放", "资产负债管理", "风险控制"], "downstream": ["居民客户", "企业客户", "公共部门客户"]},
    ),
    "insurance": _semantic_quality_override(
        [("Life insurance", "寿险"), ("Property insurance", "财险"), ("Health insurance", "健康险"), ("Reinsurance", "再保险"), ("Agency channels", "代理人渠道")],
        {"upstream": ["Policyholders", "Capital", "Actuarial data"], "midstream": ["Underwriting", "Claims management", "Investment portfolio"], "downstream": ["Households", "Corporates", "Healthcare services"]},
        {"upstream": ["投保客户", "资本金", "精算数据"], "midstream": ["承保", "理赔管理", "投资组合"], "downstream": ["居民客户", "企业客户", "医疗服务"]},
    ),
    "brokerage": _semantic_quality_override(
        [("Retail brokerage", "零售经纪"), ("Investment banking", "投行业务"), ("Asset management", "资产管理"), ("Wealth platforms", "财富平台"), ("Institutional services", "机构业务")],
        {"upstream": ["Client assets", "Market liquidity", "Capital base"], "midstream": ["Brokerage services", "Capital markets services", "Wealth management"], "downstream": ["Retail clients", "Institutional clients", "Listed companies"]},
        {"upstream": ["客户资产", "市场流动性", "资本金"], "midstream": ["经纪业务", "资本市场服务", "财富管理"], "downstream": ["个人客户", "机构客户", "上市公司"]},
    ),
    "real_estate": _semantic_quality_override(
        [("Residential property", "住宅地产"), ("Commercial property", "商业地产"), ("Industrial parks", "产业园区"), ("Property services", "物业服务"), ("REITs", "REITs")],
        {"upstream": ["Land", "Financing", "Building materials"], "midstream": ["Development", "Property operation", "Asset management"], "downstream": ["Homebuyers", "Tenants", "Enterprises"]},
        {"upstream": ["土地", "融资", "建筑材料"], "midstream": ["开发建设", "物业运营", "资产管理"], "downstream": ["购房者", "租户", "企业客户"]},
    ),
    "reits": _semantic_quality_override(
        [("Industrial REITs", "产业园 REITs"), ("Warehouse REITs", "仓储物流 REITs"), ("Retail REITs", "零售 REITs"), ("Infrastructure REITs", "基础设施 REITs"), ("Data-center REITs", "数据中心 REITs")],
        {"upstream": ["Underlying assets", "Sponsors", "Debt financing"], "midstream": ["REIT operation", "Asset management", "Rental collection"], "downstream": ["Tenants", "Institutional capital", "Public investors"]},
        {"upstream": ["底层资产", "原始权益人", "债务融资"], "midstream": ["REITs 运营", "资产管理", "租金回收"], "downstream": ["租户", "机构资金", "公众投资者"]},
    ),
    "healthcare": _semantic_quality_override(
        [("Pharmaceuticals", "药品"), ("Medical services", "医疗服务"), ("Medical devices", "医疗器械"), ("Biotechnology", "生物科技"), ("Healthcare IT", "医疗信息化")],
        {"upstream": ["Research inputs", "Clinical resources", "Regulatory pathways"], "midstream": ["Drug development", "Device manufacturing", "Healthcare services"], "downstream": ["Hospitals", "Patients", "Payers"]},
        {"upstream": ["研发资源", "临床资源", "监管路径"], "midstream": ["药物研发", "器械制造", "医疗服务"], "downstream": ["医院", "患者", "支付方"]},
    ),
    "innovative_drugs": _semantic_quality_override(
        [("Oncology drugs", "肿瘤药"), ("Autoimmune drugs", "自免药"), ("Metabolic drugs", "代谢药"), ("Biologics", "生物药"), ("Licensing deals", "授权合作")],
        {"upstream": ["Targets", "Research platforms", "Clinical resources"], "midstream": ["Preclinical research", "Clinical trials", "Registration"], "downstream": ["Hospitals", "Patients", "Payers"]},
        {"upstream": ["靶点", "研发平台", "临床资源"], "midstream": ["临床前研究", "临床试验", "注册申报"], "downstream": ["医院", "患者", "支付方"]},
    ),
    "cxo": _semantic_quality_override(
        [("CRO", "CRO"), ("CDMO", "CDMO"), ("Clinical services", "临床服务"), ("Laboratory services", "实验室服务"), ("Manufacturing services", "生产服务")],
        {"upstream": ["Drug sponsors", "Research demand", "Clinical projects"], "midstream": ["CRO services", "CDMO manufacturing", "Project delivery"], "downstream": ["Biotech clients", "Pharma clients", "Regulatory filings"]},
        {"upstream": ["药企客户", "研发需求", "临床项目"], "midstream": ["CRO 服务", "CDMO 生产", "项目交付"], "downstream": ["Biotech 客户", "药企客户", "注册申报"]},
    ),
    "medical_devices": _semantic_quality_override(
        [("Imaging equipment", "影像设备"), ("Consumables", "医用耗材"), ("IVD", "体外诊断"), ("Surgical devices", "手术器械"), ("Homecare devices", "家用医疗设备")],
        {"upstream": ["Components", "Medical materials", "Regulatory standards"], "midstream": ["Device design", "Manufacturing", "Quality control"], "downstream": ["Hospitals", "Clinics", "Homecare users"]},
        {"upstream": ["零部件", "医用材料", "监管标准"], "midstream": ["器械设计", "生产制造", "质量控制"], "downstream": ["医院", "诊所", "家庭用户"]},
    ),
    "biotechnology": _semantic_quality_override(
        [("Gene therapy", "基因治疗"), ("Cell therapy", "细胞治疗"), ("Antibody drugs", "抗体药物"), ("Research tools", "科研工具"), ("Platform technologies", "平台技术")],
        {"upstream": ["Biology research", "Lab resources", "Clinical resources"], "midstream": ["Platform development", "Clinical validation", "Manufacturing process"], "downstream": ["Pharma partners", "Hospitals", "Patients"]},
        {"upstream": ["生物学研究", "实验资源", "临床资源"], "midstream": ["平台开发", "临床验证", "生产工艺"], "downstream": ["药企合作方", "医院", "患者"]},
    ),
    "ai_healthcare": _semantic_quality_override(
        [("AI diagnosis", "AI 诊断"), ("Clinical workflow", "临床流程"), ("Medical imaging AI", "医学影像 AI"), ("Drug discovery AI", "AI 药物发现"), ("Hospital software", "医院软件")],
        {"upstream": ["Medical data", "Algorithms", "Clinical validation"], "midstream": ["Software products", "Workflow integration", "Regulatory review"], "downstream": ["Hospitals", "Doctors", "Patients"]},
        {"upstream": ["医疗数据", "算法模型", "临床验证"], "midstream": ["软件产品", "流程集成", "监管审评"], "downstream": ["医院", "医生", "患者"]},
    ),
    "chemicals": _semantic_quality_override(
        [("Basic chemicals", "基础化工"), ("Specialty chemicals", "精细化工"), ("Agrochemicals", "农化"), ("Materials chemicals", "材料化工"), ("Chemical distribution", "化工流通")],
        {"upstream": ["Crude oil", "Coal", "Natural gas", "Minerals"], "midstream": ["Chemical production", "Processing", "Inventory management"], "downstream": ["Agriculture", "Manufacturing", "Consumer goods"]},
        {"upstream": ["原油", "煤炭", "天然气", "矿产"], "midstream": ["化工生产", "加工制造", "库存管理"], "downstream": ["农业", "制造业", "消费品"]},
    ),
    "cement": _semantic_quality_override(
        [("Clinker", "熟料"), ("Cement", "水泥"), ("Ready-mix concrete", "商混"), ("Aggregates", "骨料"), ("Regional producers", "区域水泥企业")],
        {"upstream": ["Limestone", "Coal", "Electricity"], "midstream": ["Clinker production", "Cement grinding", "Concrete mixing"], "downstream": ["Infrastructure", "Real estate construction", "Rural construction"]},
        {"upstream": ["石灰石", "煤炭", "电力"], "midstream": ["熟料生产", "水泥粉磨", "商混搅拌"], "downstream": ["基建", "房地产施工", "农村建设"]},
    ),
    "shipping": _semantic_quality_override(
        [("Container shipping", "集装箱航运"), ("Dry bulk", "干散货"), ("Oil tankers", "油运"), ("LNG shipping", "LNG 航运"), ("Shipping services", "航运服务")],
        {"upstream": ["Ships", "Fuel", "Port capacity"], "midstream": ["Fleet operation", "Route scheduling", "Freight pricing"], "downstream": ["Exporters", "Importers", "Commodity traders"]},
        {"upstream": ["船舶", "燃料", "港口能力"], "midstream": ["船队运营", "航线调度", "运价管理"], "downstream": ["出口商", "进口商", "大宗商品贸易商"]},
    ),
    "ports": _semantic_quality_override(
        [("Container terminals", "集装箱码头"), ("Bulk terminals", "散货码头"), ("Oil terminals", "油品码头"), ("Port logistics", "港口物流"), ("Free-trade zones", "保税区")],
        {"upstream": ["Berths", "Yard capacity", "Handling equipment"], "midstream": ["Port operation", "Cargo handling", "Customs services"], "downstream": ["Shipping companies", "Exporters", "Importers"]},
        {"upstream": ["泊位", "堆场能力", "装卸设备"], "midstream": ["港口运营", "货物装卸", "通关服务"], "downstream": ["航运公司", "出口商", "进口商"]},
    ),
    "logistics": _semantic_quality_override(
        [("Express delivery", "快递"), ("Freight logistics", "货运物流"), ("Cold-chain logistics", "冷链物流"), ("Warehousing", "仓储"), ("Supply-chain services", "供应链服务")],
        {"upstream": ["Warehouses", "Vehicles", "Labor"], "midstream": ["Sorting", "Transportation", "Route management"], "downstream": ["E-commerce merchants", "Manufacturers", "Consumers"]},
        {"upstream": ["仓库", "车辆", "人力"], "midstream": ["分拣", "运输", "线路管理"], "downstream": ["电商商家", "制造企业", "消费者"]},
    ),
    "defense": _semantic_quality_override(
        [("Aircraft systems", "航空装备"), ("Missile systems", "导弹系统"), ("Defense electronics", "军工电子"), ("Shipbuilding", "舰船装备"), ("Aerospace components", "航天配套")],
        {"upstream": ["Special alloys", "Electronic components", "Precision parts"], "midstream": ["Subsystem manufacturing", "Final assembly", "Testing and delivery"], "downstream": ["Defense customers", "Aerospace programs", "Maintenance demand"]},
        {"upstream": ["特种合金", "电子元器件", "精密零部件"], "midstream": ["分系统制造", "总装集成", "测试交付"], "downstream": ["国防客户", "航天项目", "维修保障需求"]},
    ),
}

industryTrendData = [
    {**record, **SEMANTIC_QUALITY_OVERRIDES.get(record["id"], {})}
    for record in industryTrendData
]

MEMORY_DETAIL = {
    "id": "memory",
    "name": "Memory",
    "chineseName": "存储芯片",
    "category": "Technology Growth",
    "categoryZh": "科技成长 / 半导体 / 存储芯片",
    "aliases": [
        "memory",
        "memory chip",
        "DRAM",
        "NAND",
        "HBM",
        "storage chip",
        "enterprise SSD",
        "存储",
        "存储芯片",
        "存储器",
        "动态随机存储器",
        "闪存",
        "高带宽内存",
        "企业级 SSD",
    ],
    "status": "Diverging",
    "trendStage": "Stage 4: High-heat Divergence",
    "trendStageZh": "第四阶段：高热分化",
    "trendScore": 7.4,
    "heatLevel": "High",
    "marketConfirmation": 7.2,
    "fundamentalValidation": 6.8,
    "valuationPressure": 7.1,
    "macroSensitivity": 6.6,
    "overview": (
        "Memory is an independent semiconductor cycle theme covering HBM, DRAM, NAND, enterprise SSD, "
        "and controller demand. AI server memory density supports higher-end demand, while pricing, "
        "inventory, capacity, and capex cycles can create meaningful dispersion."
    ),
    "overviewZh": (
        "存储芯片是半导体周期中的独立主题，覆盖 HBM、DRAM、NAND、企业级 SSD 和控制器需求。"
        "AI 服务器内存容量提升支撑高端需求，但价格、库存、产能和资本开支周期也会带来波动和分化。"
    ),
    "summary": (
        "Memory is in a high-heat divergence stage: HBM and high-end DRAM are supported by AI compute demand, "
        "while NAND, enterprise SSD, and broader memory pricing still need cycle validation."
    ),
    "summaryZh": (
        "存储芯片处于高热分化阶段：HBM 与高端 DRAM 受 AI 算力需求支撑，"
        "但 NAND、企业级 SSD 和整体存储价格仍需要周期验证。"
    ),
    "trendStageExplanation": (
        "The stage reflects elevated attention around HBM and AI servers, combined with cyclical divergence "
        "across memory products and suppliers."
    ),
    "trendStageExplanationZh": (
        "该阶段反映 HBM 与 AI 服务器带来的高关注度，同时也体现不同存储产品和厂商之间的周期分化。"
    ),
    "keyDrivers": [
        {
            "name": "HBM demand growth",
            "nameZh": "HBM 需求增长",
            "status": "Strong",
            "explanation": "High-bandwidth memory remains closely linked to AI accelerator and server demand.",
            "explanationZh": "高带宽内存与 AI 加速器和服务器需求高度相关，是当前高端存储验证的重要线索。",
        },
        {
            "name": "AI server memory density",
            "nameZh": "AI 服务器内存容量提升",
            "status": "Strong",
            "explanation": "Higher model and inference workloads increase memory capacity and bandwidth requirements.",
            "explanationZh": "模型训练与推理负载提升，带动服务器内存容量和带宽需求上升。",
        },
        {
            "name": "DRAM / NAND price cycle",
            "nameZh": "DRAM / NAND 价格周期",
            "status": "Diverging",
            "explanation": "Pricing recovery can vary by product tier, inventory position, and customer segment.",
            "explanationZh": "价格修复会受到产品层级、库存位置和客户结构影响，行业内部容易出现分化。",
        },
        {
            "name": "Enterprise SSD demand",
            "nameZh": "企业级 SSD 需求",
            "status": "Moderate-Strong",
            "explanation": "Data center storage upgrades provide a second demand layer beyond HBM.",
            "explanationZh": "数据中心存储升级为 HBM 之外提供第二层需求线索。",
        },
        {
            "name": "Memory capex changes",
            "nameZh": "存储厂商资本开支变化",
            "status": "Moderate",
            "explanation": "Capacity plans influence supply discipline and later-cycle pricing risk.",
            "explanationZh": "产能规划会影响供给纪律，并影响后续价格周期风险。"
        },
    ],
    "subSectors": [
        {"name": "HBM", "nameZh": "HBM", "status": "Strong"},
        {"name": "DRAM", "nameZh": "DRAM", "status": "Diverging"},
        {"name": "NAND Flash", "nameZh": "NAND 闪存", "status": "Recovering"},
        {"name": "Enterprise SSD", "nameZh": "企业级 SSD", "status": "Moderate-Strong"},
        {"name": "Memory Controller", "nameZh": "存储控制器", "status": "Moderate"},
        {"name": "Packaging / Advanced Packaging", "nameZh": "封装 / 先进封装", "status": "Strong"},
    ],
    "industryChain": {
        "upstream": ["Semiconductor equipment", "Materials", "Wafers", "EDA"],
        "midstream": ["DRAM", "NAND", "HBM", "Enterprise SSD", "Controllers"],
        "downstream": ["AI servers", "Data centers", "Consumer electronics", "Automotive electronics", "Enterprise storage"],
    },
    "industryChainZh": {
        "upstream": ["半导体设备", "材料", "硅片", "EDA"],
        "midstream": ["DRAM", "NAND", "HBM", "企业级 SSD", "控制器"],
        "downstream": ["AI 服务器", "数据中心", "消费电子", "汽车电子", "企业存储"],
    },
    "catalysts": [
        "HBM capacity and qualification progress",
        "DRAM / NAND pricing recovery",
        "Enterprise SSD demand changes",
        "Memory supplier capex discipline",
    ],
    "catalystsZh": [
        "HBM 产能与验证进度",
        "DRAM / NAND 价格修复",
        "企业级 SSD 需求变化",
        "存储厂商资本开支纪律",
    ],
    "riskSignals": [
        "Memory price pullback",
        "Inventory cycle reversal",
        "Overly rapid capex expansion",
        "AI server demand below expectations",
        "Margin pressure from stronger competition",
    ],
    "riskSignalsZh": [
        "存储价格回落",
        "库存周期反转",
        "资本开支过快扩张",
        "AI 服务器需求低于预期",
        "竞争加剧导致利润率压力",
    ],
}

if not any(record["id"] == "memory" for record in industryTrendData):
    insert_index = next((index + 1 for index, record in enumerate(industryTrendData) if record["id"] == "semiconductor"), 1)
    industryTrendData.insert(insert_index, MEMORY_DETAIL)

CHINESE_NAME_OVERRIDES = {
    "semiconductor": "半导体",
    "cpo_optical_module": "CPO / 光模块",
    "ai_compute": "AI 算力",
    "cpu": "CPU",
    "cloud_computing": "云计算",
    "data_center": "数据中心",
    "cybersecurity": "网络安全",
    "consumer_electronics": "消费电子",
    "robotics": "机器人",
    "ev": "新能源车",
    "battery": "电池",
    "solar": "光伏",
    "energy_storage": "储能",
    "wind_power": "风电",
    "sic": "碳化硅",
    "power_equipment": "电力设备",
    "industrial_automation": "工业自动化",
    "gold": "黄金",
    "copper": "铜",
    "aluminum": "铝",
    "lithium": "锂",
    "rare_earth": "稀土",
    "oil": "原油",
    "natural_gas": "天然气",
    "coal": "煤炭",
    "liquor": "白酒",
    "food_beverage": "食品饮料",
    "tourism": "旅游",
    "hotel": "酒店",
    "aviation": "航空",
    "gaming": "游戏",
    "e_commerce": "电商",
    "banking": "银行",
    "insurance": "保险",
    "brokerage": "券商",
    "real_estate": "房地产",
    "reits": "REITs",
    "healthcare": "医药",
    "innovative_drugs": "创新药",
    "cxo": "医药外包",
    "medical_devices": "医疗器械",
    "biotechnology": "生物科技",
    "ai_healthcare": "AI 医疗",
    "chemicals": "化工",
    "cement": "水泥",
    "shipping": "航运",
    "ports": "港口",
    "logistics": "物流",
    "defense": "军工",
}

CATEGORY_ZH_OVERRIDES = {
    "Technology Growth": "科技成长",
    "New Energy & Manufacturing": "新能源与制造",
    "Commodities": "大宗商品",
    "Consumer": "消费",
    "Financial & Real Estate": "金融地产",
    "Healthcare": "医疗健康",
    "Cyclical & Industrial": "周期与工业",
}

TREND_STAGE_ZH_MAP = {
    "Stage 1: Low-attention Accumulation": "第一阶段：低关注酝酿",
    "Stage 2: Trend Confirmation": "第二阶段：趋势确认",
    "Stage 3: Maintrend Expansion": "第三阶段：主升扩散",
    "Stage 4: High-heat Divergence": "第四阶段：高热分化",
    "Stage 5: Overpriced Volatility": "第五阶段：高估值波动",
    "Stage 6: Trend Cooling": "第六阶段：趋势降温",
}

DRIVER_ZH_MAP = {
    "demand cycle": "需求周期",
    "Policy and capex visibility": "政策与资本开支可见度",
    "Supply-chain pricing power": "供应链定价能力",
}

SUBSECTOR_ZH_MAP = {
    "Component Suppliers": "组件供应商",
    "Infrastructure Providers": "基础设施提供商",
    "Application Layer": "应用层",
}

CHAIN_ZH_MAP = {
    "Raw inputs": "原始投入",
    "Core equipment": "核心设备",
    "Specialized materials": "专用材料",
    "Design tools": "设计工具",
    "Manufacturing": "制造环节",
    "Integration": "集成环节",
    "Platform operators": "平台运营商",
    "Distribution": "分发渠道",
    "Enterprise demand": "企业需求",
    "Consumer adoption": "消费者采用",
    "Public projects": "公共项目",
    "Global channels": "全球渠道",
}

CATALYST_ZH_MAP = {
    "Capacity cycle changes": "产能周期变化",
    "Policy or regulation updates": "政策或监管更新",
    "Demand inflection in downstream applications": "下游应用需求拐点",
}

RISK_ZH_MAP = {
    "Narrative runs ahead of validation": "叙事领先于验证",
    "Margin or pricing divergence": "利润率或价格分化",
    "Macro conditions reduce visibility": "宏观环境降低可见度",
}


def _complete_zh_fields(record: dict) -> dict:
    completed = dict(record)
    industry_id = completed["id"]
    zh_name = CHINESE_NAME_OVERRIDES.get(industry_id, completed.get("chineseName") or completed["name"])
    completed["chineseName"] = zh_name
    completed.setdefault("categoryZh", CATEGORY_ZH_OVERRIDES.get(completed.get("category", ""), completed.get("category", "")))
    completed.setdefault(
        "overviewZh",
        f"{zh_name} 当前使用中性行业趋势框架进行观察，主要参考关注度、价格广度、叙事强度、业绩周期验证和宏观敏感度。",
    )
    completed.setdefault(
        "summaryZh",
        f"{zh_name} 当前处于中性研究框架观察阶段，重点跟踪趋势阶段、市场价格确认、基本验证和风险信号。",
    )
    completed.setdefault("trendStageZh", TREND_STAGE_ZH_MAP.get(completed.get("trendStage", ""), "第二阶段：趋势确认"))
    completed.setdefault(
        "trendStageExplanationZh",
        "该阶段用于描述主题在模拟趋势生命周期中的位置，从低关注酝酿到高热后的降温。",
    )
    completed["keyDrivers"] = [_complete_driver_zh(driver, zh_name) for driver in completed.get("keyDrivers", [])]
    completed["subSectors"] = [_complete_subsector_zh(item, zh_name) for item in completed.get("subSectors", [])]
    completed.setdefault(
        "industryChainZh",
        {
            layer: [CHAIN_ZH_MAP.get(value, value) for value in values]
            for layer, values in completed.get("industryChain", {}).items()
        },
    )
    completed.setdefault("catalystsZh", [CATALYST_ZH_MAP.get(value, value) for value in completed.get("catalysts", [])])
    completed.setdefault("riskSignalsZh", [RISK_ZH_MAP.get(value, value) for value in completed.get("riskSignals", [])])
    return completed


def _complete_driver_zh(driver: dict, zh_name: str) -> dict:
    completed = dict(driver)
    name = str(completed.get("name", ""))
    if "nameZh" not in completed:
        if name.endswith(" demand cycle"):
            completed["nameZh"] = f"{zh_name}需求周期"
        else:
            completed["nameZh"] = DRIVER_ZH_MAP.get(name, name)
    completed.setdefault("explanationZh", f"{completed['nameZh']}用于观察该行业趋势的验证强度和变化节奏。")
    return completed


def _complete_subsector_zh(item: dict, zh_name: str) -> dict:
    completed = dict(item)
    name = str(completed.get("name", ""))
    if "nameZh" not in completed:
        if name.endswith(" Leaders"):
            completed["nameZh"] = f"{zh_name}龙头样本"
        else:
            completed["nameZh"] = SUBSECTOR_ZH_MAP.get(name, name)
    return completed


industryTrendData = [_complete_zh_fields(record) for record in industryTrendData]
GENERIC_INDUSTRY_TEMPLATE = _complete_zh_fields(GENERIC_INDUSTRY_TEMPLATE)
