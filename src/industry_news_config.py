"""Centralized industry news configuration for coverage audits and providers.

This file is a deterministic local configuration layer. It does not add news
sources, call external services, or change market/risk judgment rules.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


INDUSTRY_NEWS_CONFIG: dict[str, dict[str, Any]] = {
    "semiconductor": {
        "search_queries": [
            "Nvidia AI chip HBM",
            "SK Hynix Nvidia AI memory",
            "Micron HBM AI memory",
            "TSMC advanced packaging",
            "Broadcom Marvell AI chip",
            "semiconductor AI data center capex",
        ],
        "relevance_keywords": [
            "semiconductor",
            "chip",
            "AI chip",
            "GPU",
            "ASIC",
            "HBM",
            "DRAM",
            "AI memory",
            "Nvidia",
            "Micron",
            "SK Hynix",
            "TSMC",
            "Broadcom",
            "Marvell",
            "advanced packaging",
            "CoWoS",
            "foundry",
        ],
        "exclude_keywords": ["crypto", "bitcoin", "gaming laptop"],
        "theme_keywords": {
            "AI 芯片链条扩散": ["AI chip", "GPU", "ASIC", "Nvidia", "Broadcom", "Marvell"],
            "HBM / DRAM 存储链强化": ["HBM", "DRAM", "AI memory", "Micron", "SK Hynix"],
            "先进封装与高端算力供给约束": ["advanced packaging", "CoWoS", "TSMC", "foundry"],
            "AI 数据中心基础设施需求": ["AI data center", "data center capex", "AI infrastructure"],
        },
        "coverage_notes_zh": "重点覆盖 AI 芯片、HBM/DRAM、先进封装、晶圆代工与数据中心资本开支链条。",
        "coverage_notes": "Focuses on AI chips, HBM/DRAM, advanced packaging, foundry capacity, and data-center capex.",
        "preferred_sources": [],
    },
    "cpo_optical_module": {
        "search_queries": [
            "co-packaged optics",
            "CPO switch Nvidia",
            "silicon photonics data center",
            "800G optical module",
            "1.6T optical module",
            "AI optical interconnect",
            "data center optical interconnect",
            "optical transceiver AI data center",
            "linear drive optics LPO",
            "LPO optical module",
        ],
        "relevance_keywords": [
            "CPO",
            "co-packaged optics",
            "optical module",
            "silicon photonics",
            "800G",
            "1.6T",
            "LPO",
            "linear drive optics",
            "data center switch",
            "AI optical interconnect",
            "optical transceiver",
            "bandwidth",
            "光模块",
            "硅光",
            "共封装光学",
            "高速光互连",
        ],
        "exclude_keywords": ["camera lens", "fiber internet plan"],
        "theme_keywords": {
            "CPO 技术路线验证": ["CPO", "co-packaged optics", "data center switch"],
            "硅光路线推进": ["silicon photonics", "硅光"],
            "高速光模块升级周期": ["optical module", "800G", "1.6T", "bandwidth"],
            "AI 数据中心光互连需求": ["AI optical interconnect", "optical transceiver", "data center optical interconnect"],
        },
        "coverage_notes_zh": "重点覆盖 CPO、硅光、高速光模块、LPO 与 AI 数据中心光互连需求。",
        "coverage_notes": "Focuses on CPO, silicon photonics, high-speed modules, LPO, and AI data-center optical interconnects.",
        "preferred_sources": [],
    },
    "gold": {
        "search_queries": ["gold real yields", "gold central bank buying", "gold dollar treasury yields"],
        "relevance_keywords": ["gold", "real yield", "real yields", "treasury yields", "central bank buying", "dollar", "inflation", "geopolitical", "precious metal", "黄金"],
        "exclude_keywords": ["golden retriever", "gold medal"],
        "theme_keywords": {
            "美元与实际利率压力": ["dollar", "real yield", "treasury yields"],
            "央行购金需求": ["central bank buying", "central banks", "黄金"],
            "通胀与地缘风险": ["inflation", "geopolitical", "safe haven"],
        },
        "coverage_notes_zh": "重点覆盖实际利率、美元、央行购金、通胀与地缘风险。",
        "coverage_notes": "Focuses on real yields, the dollar, central-bank demand, inflation, and geopolitical risk.",
        "preferred_sources": [],
    },
    "real_estate": {
        "search_queries": ["REITs interest rates", "commercial real estate refinancing", "real estate occupancy rates"],
        "relevance_keywords": ["real estate", "property", "REIT", "REITs", "commercial real estate", "refinancing", "mortgage rate", "occupancy", "rental", "房地产", "地产"],
        "exclude_keywords": ["metaverse real estate"],
        "theme_keywords": {
            "融资与利率压力": ["interest rates", "refinancing", "mortgage rate"],
            "商业地产出租率": ["commercial real estate", "occupancy", "office"],
            "REITs 现金流观察": ["REIT", "REITs", "distribution"],
        },
        "coverage_notes_zh": "重点覆盖利率、再融资、出租率与 REITs 现金流。",
        "coverage_notes": "Focuses on rates, refinancing, occupancy, and REIT cash-flow signals.",
        "preferred_sources": [],
    },
    "liquor": {
        "search_queries": ["baijiu channel inventory", "premium liquor consumption", "China liquor wholesale price"],
        "relevance_keywords": ["liquor", "baijiu", "premium liquor", "channel inventory", "wholesale price", "consumption", "白酒", "批价", "库存"],
        "exclude_keywords": ["liquor license crime"],
        "theme_keywords": {
            "渠道库存与批价": ["channel inventory", "wholesale price", "库存", "批价"],
            "高端消费需求": ["premium liquor", "consumption", "banquet"],
            "节庆动销观察": ["holiday", "festival", "demand"],
        },
        "coverage_notes_zh": "重点覆盖渠道库存、批价与高端消费需求。",
        "coverage_notes": "Focuses on inventory, wholesale pricing, and premium consumption demand.",
        "preferred_sources": [],
    },
    "battery": {
        "search_queries": ["lithium battery supply demand", "EV battery cathode material", "battery energy storage demand"],
        "relevance_keywords": ["battery", "lithium battery", "cathode", "anode", "separator", "electrolyte", "energy storage", "EV battery", "LFP", "solid-state battery", "电池", "锂电池"],
        "exclude_keywords": ["phone battery tips"],
        "theme_keywords": {
            "动力电池需求": ["EV battery", "lithium battery", "LFP"],
            "材料价格与供需": ["cathode", "anode", "electrolyte", "separator"],
            "储能需求扩散": ["energy storage", "battery storage"],
        },
        "coverage_notes_zh": "重点覆盖动力电池、材料供需、储能与固态电池路线。",
        "coverage_notes": "Focuses on EV batteries, material supply-demand, storage demand, and solid-state routes.",
        "preferred_sources": [],
    },
    "ev": {
        "search_queries": ["electric vehicle deliveries", "EV price competition", "China EV exports"],
        "relevance_keywords": ["EV", "electric vehicle", "vehicle deliveries", "price competition", "charging", "battery electric", "China EV", "新能源汽车", "电动车"],
        "exclude_keywords": ["ev tax form"],
        "theme_keywords": {
            "销量与交付节奏": ["deliveries", "sales", "vehicle deliveries"],
            "价格竞争与利润压力": ["price competition", "discount", "margin"],
            "出口与海外需求": ["exports", "overseas", "China EV"],
        },
        "coverage_notes_zh": "重点覆盖交付、价格竞争、出口和充电基础设施。",
        "coverage_notes": "Focuses on deliveries, price competition, exports, and charging infrastructure.",
        "preferred_sources": [],
    },
    "solar": {
        "search_queries": ["solar module price", "photovoltaic supply demand", "solar inverter demand"],
        "relevance_keywords": ["solar", "photovoltaic", "PV", "module price", "inverter", "renewable energy", "installation", "polysilicon", "光伏", "组件"],
        "exclude_keywords": ["solar eclipse"],
        "theme_keywords": {
            "组件价格与供需": ["module price", "photovoltaic", "polysilicon"],
            "逆变器与装机需求": ["inverter", "installation", "renewable energy"],
            "海外政策与贸易": ["tariff", "policy", "exports"],
        },
        "coverage_notes_zh": "重点覆盖组件价格、装机需求、逆变器与海外政策。",
        "coverage_notes": "Focuses on module prices, installations, inverters, and overseas policy.",
        "preferred_sources": [],
    },
    "data_center": {
        "search_queries": ["AI data center capex", "data center power demand", "hyperscale data center buildout"],
        "relevance_keywords": ["data center", "datacenter", "AI data center", "hyperscale", "capex", "power demand", "cooling", "server", "数据中心"],
        "exclude_keywords": ["data center sports"],
        "theme_keywords": {
            "AI 数据中心扩建": ["AI data center", "hyperscale", "buildout"],
            "电力与散热约束": ["power demand", "cooling", "electricity"],
            "服务器与资本开支": ["server", "capex", "infrastructure"],
        },
        "coverage_notes_zh": "重点覆盖 AI 数据中心扩建、电力散热约束与资本开支。",
        "coverage_notes": "Focuses on AI data-center buildout, power/cooling constraints, and capex.",
        "preferred_sources": [],
    },
    "cloud_computing": {
        "search_queries": ["cloud computing AI revenue", "hyperscaler cloud capex", "enterprise cloud spending"],
        "relevance_keywords": ["cloud", "cloud computing", "hyperscaler", "AWS", "Azure", "Google Cloud", "enterprise cloud", "AI revenue", "云计算"],
        "exclude_keywords": ["cloudy weather"],
        "theme_keywords": {
            "云厂商 AI 收入": ["AI revenue", "AWS", "Azure", "Google Cloud"],
            "资本开支与算力投入": ["hyperscaler", "capex", "infrastructure"],
            "企业云支出": ["enterprise cloud", "cloud spending"],
        },
        "coverage_notes_zh": "重点覆盖云厂商 AI 收入、资本开支和企业云支出。",
        "coverage_notes": "Focuses on AI cloud revenue, hyperscaler capex, and enterprise cloud spending.",
        "preferred_sources": [],
    },
    "cybersecurity": {
        "search_queries": ["cybersecurity spending AI", "security software earnings", "cloud security demand"],
        "relevance_keywords": ["cybersecurity", "security software", "cloud security", "endpoint security", "zero trust", "ransomware", "identity security", "网络安全"],
        "exclude_keywords": ["home security camera"],
        "theme_keywords": {
            "安全软件支出": ["security software", "cybersecurity spending"],
            "云安全与身份安全": ["cloud security", "identity security", "zero trust"],
            "勒索攻击风险": ["ransomware", "breach", "attack"],
        },
        "coverage_notes_zh": "重点覆盖安全软件支出、云安全、身份安全和攻击风险。",
        "coverage_notes": "Focuses on security software spending, cloud/identity security, and attack risk.",
        "preferred_sources": [],
    },
    "innovative_drugs": {
        "search_queries": ["innovative drug clinical trial", "biopharma FDA approval", "GLP-1 oncology drug pipeline"],
        "relevance_keywords": ["innovative drug", "biopharma", "clinical trial", "FDA approval", "pipeline", "oncology", "GLP-1", "pharma", "创新药"],
        "exclude_keywords": ["illegal drugs"],
        "theme_keywords": {
            "临床与审批进展": ["clinical trial", "FDA approval", "pipeline"],
            "重点治疗领域": ["oncology", "GLP-1", "immunology"],
            "授权合作与出海": ["licensing", "partnership", "overseas"],
        },
        "coverage_notes_zh": "重点覆盖临床进展、审批、管线与授权合作。",
        "coverage_notes": "Focuses on clinical progress, approvals, pipelines, and licensing partnerships.",
        "preferred_sources": [],
    },
    "cxo": {
        "search_queries": ["CRO CDMO demand", "biopharma outsourcing CXO", "pharma R&D outsourcing"],
        "relevance_keywords": ["CXO", "CRO", "CDMO", "outsourcing", "biopharma outsourcing", "pharma R&D", "clinical research", "医药外包"],
        "exclude_keywords": ["chief experience officer"],
        "theme_keywords": {
            "研发外包需求": ["CRO", "clinical research", "pharma R&D"],
            "生产外包景气": ["CDMO", "manufacturing", "outsourcing"],
            "海外订单与政策": ["overseas", "policy", "biopharma outsourcing"],
        },
        "coverage_notes_zh": "重点覆盖 CRO/CDMO 需求、研发生产外包和海外订单。",
        "coverage_notes": "Focuses on CRO/CDMO demand, R&D/manufacturing outsourcing, and overseas orders.",
        "preferred_sources": [],
    },
    "medical_devices": {
        "search_queries": ["medical devices demand", "medtech earnings", "surgical robot medical device"],
        "relevance_keywords": ["medical devices", "medtech", "device demand", "surgical robot", "diagnostics", "imaging equipment", "hospital capex", "医疗器械"],
        "exclude_keywords": ["consumer wearable review"],
        "theme_keywords": {
            "医院设备采购": ["hospital capex", "imaging equipment", "device demand"],
            "创新器械放量": ["surgical robot", "diagnostics", "medtech"],
            "监管与集采影响": ["regulation", "procurement", "pricing"],
        },
        "coverage_notes_zh": "重点覆盖医院采购、创新器械、监管和价格压力。",
        "coverage_notes": "Focuses on hospital procurement, innovative devices, regulation, and pricing pressure.",
        "preferred_sources": [],
    },
    "e_commerce": {
        "search_queries": ["e-commerce retail sales", "online retail platform competition", "cross-border e-commerce demand"],
        "relevance_keywords": ["e-commerce", "ecommerce", "online retail", "marketplace", "cross-border", "GMV", "platform competition", "电商"],
        "exclude_keywords": ["ecommerce website builder"],
        "theme_keywords": {
            "线上零售需求": ["online retail", "retail sales", "GMV"],
            "平台竞争格局": ["marketplace", "platform competition"],
            "跨境电商需求": ["cross-border", "exports"],
        },
        "coverage_notes_zh": "重点覆盖线上零售、平台竞争、GMV 和跨境需求。",
        "coverage_notes": "Focuses on online retail, platform competition, GMV, and cross-border demand.",
        "preferred_sources": [],
    },
    "tourism": {
        "search_queries": ["tourism travel demand", "China outbound travel", "hotel airline travel bookings"],
        "relevance_keywords": ["tourism", "travel", "outbound travel", "bookings", "leisure demand", "visitor arrivals", "holiday travel", "旅游"],
        "exclude_keywords": ["space tourism"],
        "theme_keywords": {
            "出行需求修复": ["travel demand", "bookings", "visitor arrivals"],
            "出境游节奏": ["outbound travel", "international travel"],
            "假期消费观察": ["holiday travel", "leisure demand"],
        },
        "coverage_notes_zh": "重点覆盖出行预订、出境游、游客量与假期消费。",
        "coverage_notes": "Focuses on bookings, outbound travel, visitor arrivals, and holiday demand.",
        "preferred_sources": [],
    },
    "hotel": {
        "search_queries": ["hotel occupancy rate", "hospitality RevPAR", "travel lodging demand"],
        "relevance_keywords": ["hotel", "hospitality", "occupancy", "RevPAR", "lodging", "room rate", "travel demand", "酒店"],
        "exclude_keywords": ["hotel california"],
        "theme_keywords": {
            "入住率与房价": ["occupancy", "room rate", "RevPAR"],
            "商旅与休闲需求": ["travel demand", "business travel", "leisure"],
            "酒店集团经营": ["hospitality", "lodging", "hotel"],
        },
        "coverage_notes_zh": "重点覆盖入住率、RevPAR、房价和商旅休闲需求。",
        "coverage_notes": "Focuses on occupancy, RevPAR, room rates, and business/leisure travel demand.",
        "preferred_sources": [],
    },
    "banking": {
        "search_queries": ["bank net interest margin", "bank loan growth", "bank asset quality"],
        "relevance_keywords": ["bank", "banking", "net interest margin", "NIM", "loan growth", "deposit", "asset quality", "credit risk", "银行"],
        "exclude_keywords": ["food bank"],
        "theme_keywords": {
            "息差与负债成本": ["net interest margin", "NIM", "deposit"],
            "信贷增长": ["loan growth", "credit demand"],
            "资产质量": ["asset quality", "credit risk", "nonperforming"],
        },
        "coverage_notes_zh": "重点覆盖息差、信贷增长、存款成本与资产质量。",
        "coverage_notes": "Focuses on NIM, loan growth, deposit costs, and asset quality.",
        "preferred_sources": [],
    },
    "insurance": {
        "search_queries": ["insurance premium growth", "insurer investment income", "life insurance sales"],
        "relevance_keywords": ["insurance", "insurer", "premium growth", "life insurance", "property casualty", "underwriting", "investment income", "保险"],
        "exclude_keywords": ["car insurance quote"],
        "theme_keywords": {
            "保费增长": ["premium growth", "life insurance", "property casualty"],
            "投资收益与利率": ["investment income", "bond yield", "rates"],
            "承保质量": ["underwriting", "claims", "combined ratio"],
        },
        "coverage_notes_zh": "重点覆盖保费增长、投资收益、利率和承保质量。",
        "coverage_notes": "Focuses on premium growth, investment income, rates, and underwriting quality.",
        "preferred_sources": [],
    },
    "shipping": {
        "search_queries": ["shipping freight rates", "container shipping demand", "dry bulk tanker rates"],
        "relevance_keywords": ["shipping", "freight rates", "container shipping", "dry bulk", "tanker", "charter rates", "port congestion", "航运"],
        "exclude_keywords": ["free shipping"],
        "theme_keywords": {
            "运价周期": ["freight rates", "charter rates", "shipping"],
            "集运与干散货需求": ["container shipping", "dry bulk", "tanker"],
            "港口拥堵与供给": ["port congestion", "capacity", "vessel"],
        },
        "coverage_notes_zh": "重点覆盖运价、集运、干散货、油轮和港口拥堵。",
        "coverage_notes": "Focuses on freight rates, container shipping, dry bulk, tankers, and port congestion.",
        "preferred_sources": [],
    },
    "logistics": {
        "search_queries": ["logistics supply chain demand", "parcel delivery volume", "freight logistics pricing"],
        "relevance_keywords": ["logistics", "supply chain", "parcel delivery", "freight", "warehouse", "last mile", "shipping volume", "物流"],
        "exclude_keywords": ["logic puzzle"],
        "theme_keywords": {
            "快递与包裹量": ["parcel delivery", "shipping volume", "last mile"],
            "供应链景气": ["supply chain", "warehouse", "logistics"],
            "货运价格": ["freight", "pricing", "transport"],
        },
        "coverage_notes_zh": "重点覆盖包裹量、供应链需求、仓储和货运价格。",
        "coverage_notes": "Focuses on parcel volume, supply-chain demand, warehousing, and freight pricing.",
        "preferred_sources": [],
    },
}


def get_industry_news_config(industry_id: str) -> dict[str, Any]:
    """Return a defensive copy of the configured news layer for one industry."""

    return deepcopy(INDUSTRY_NEWS_CONFIG.get(industry_id, {}))


def configured_industry_ids() -> set[str]:
    """Return industry IDs with explicit V4.14 news coverage configuration."""

    return set(INDUSTRY_NEWS_CONFIG)
