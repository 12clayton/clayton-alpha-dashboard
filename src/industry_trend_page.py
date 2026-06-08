"""Streamlit page for the Industry Trend Search Engine."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.industry_catalyst_data import (
    CATALYST_GUIDE,
    CONFIDENCE_LABELS,
    EVENT_TYPE_LABELS,
    HEAT_DIRECTION_LABELS,
    HEAT_LEVEL_LABELS,
    IMPACT_LABELS,
    get_catalyst_data,
    localized_label,
)
from src.industry_catalyst_framework_store import (
    apply_snapshot_as_framework_override,
    get_base_catalyst_framework,
    get_effective_catalyst_framework,
)
from src.industry_catalyst_review import build_catalyst_review
from src.industry_catalyst_snapshot import (
    build_dynamic_catalyst_snapshot,
    read_dynamic_catalyst_snapshot,
    save_dynamic_catalyst_snapshot,
)
from src.industry_catalyst_themes import theme_display_name, theme_reason
from src.industry_export import build_industry_export_context, build_industry_json, build_industry_markdown
from src.industry_market_data import get_market_confirmation_data
from src.industry_news_provider import read_industry_news, refresh_industry_news
from src.industry_overall_view import OVERALL_TEXT, compute_overall_view, format_overall_score
from src.industry_trend_data import INDUSTRY_CATEGORIES
from src.industry_trend_search import find_industry_trend


TEXT = {
    "zh": {
        "language_label": "语言",
        "search_placeholder": "搜索行业或主题...",
        "page_title": "行业趋势搜索引擎",
        "page_subtitle": "输入行业关键词，生成趋势阶段、驱动因素、市场确认、基本面验证与产业链图谱。",
        "version": "V1/V2 框架 · V3 市场数据",
        "recognition": "识别结果",
        "category": "行业分类",
        "fallback_title": "未找到精确匹配",
        "fallback_body": "正在展示通用行业趋势分析框架",
        "trend_summary": "趋势摘要",
        "trend_stage": "趋势阶段",
        "framework_scores": "框架评分（V1/V2 模拟框架）",
        "live_title": "真实市场价格确认数据（V3 实时市场数据）",
        "live_intro": "该模块使用公开行情数据计算行业代表 ETF / 龙头股的趋势确认情况。它只反映市场价格层面，不代表完整产业基本面结论。",
        "price_score_note": "该分数仅基于公开行情数据计算，用于观察价格层面的趋势确认情况，不代表完整产业基本面结论。",
        "live_unavailable": "实时市场确认数据暂不可用，当前仍展示 V1/V2 模拟框架。",
        "no_market_mapping": "当前行业尚未配置 V3 市场价格代理样本，因此暂不展示实时市场价格确认数据。当前仍展示 V1/V2 模拟框架。",
        "cpo_note": "CPO / Optical Module 暂无专用 ETF，本模块使用代表性公司作为价格代理样本。",
        "cxo_proxy_note": "CXO 暂无专用 ETF，本模块使用生命科学服务与医药外包代表公司作为价格代理样本。",
        "memory_proxy_note": "存储芯片暂无纯粹专用 ETF，本模块使用半导体 ETF 和代表性存储公司作为价格代理样本。",
        "wind_power_proxy_note": "风电使用全球风电 ETF 与代表公司作为价格代理，部分 OTC ticker 可能不稳定。",
        "proxy_note": "当前行业使用代表性公司组合作为市场价格代理。",
        "sic_proxy_note": "SiC 暂无专用 ETF，本模块使用代表性功率半导体公司作为价格代理样本。",
        "data_source": "数据源",
        "updated": "更新时间",
        "benchmark": "基准",
        "valid_samples": "有效样本",
        "failed": "下载失败",
        "none": "无",
        "mock_confirmation": "Mock 市场确认",
        "price_score": "市场价格确认分",
        "ma20_ratio": "站上 MA20 比例",
        "ma50_ratio": "站上 MA50 比例",
        "ma200_ratio": "站上 MA200 比例",
        "avg_3m": "平均 3个月表现",
        "median_3m": "中位数 3个月表现",
        "benchmark_3m": "基准 3个月表现",
        "relative_strength": "相对强弱",
        "ticker": "代码",
        "sample_type": "样本类型",
        "latest_close": "最新收盘价",
        "above_ma20": "站上 MA20",
        "above_ma50": "站上 MA50",
        "above_ma200": "站上 MA200",
        "return_1m": "1个月表现",
        "return_3m": "3个月表现",
        "return_6m": "6个月表现",
        "audit_title": "数据计算审计",
        "close_21d": "21日前收盘价",
        "close_63d": "63日前收盘价",
        "close_126d": "126日前收盘价",
        "key_drivers": "核心驱动因素",
        "key_drivers_desc": "核心驱动因素用于观察行业趋势背后的需求、供给、技术和政策线索。",
        "subsectors": "子行业与相关主题",
        "subsectors_desc": "相关方向可能同步确认、滞后修复，也可能与行业主线发生分化。",
        "chain_map": "产业链地图",
        "chain_desc": "产业链地图用于区分上游投入、中游生产或平台环节，以及面向需求端的应用层。",
        "catalysts": "关键催化因素",
        "catalysts_desc": "催化因素是可能改变趋势确认度、热度等级或基本验证强度的事件与数据点。",
        "risk_signals": "趋势风险信号",
        "risk_desc": "风险信号用于提示趋势质量可能转弱、拥挤度升高或内部一致性下降的环节。",
        "universe": "内置 mock 行业范围",
        "upstream": "上游",
        "midstream": "中游",
        "downstream": "下游",
        "yes": "是",
        "sample_etf": "ETF",
        "sample_leader": "龙头股",
        "sample_benchmark": "基准",
        "refresh_market_data": "刷新市场数据",
        "failure_reasons": "失败原因",
        "failure_ticker": "代码",
        "failure_reason": "原因",
    },
    "en": {
        "language_label": "Language",
        "search_placeholder": "Search industry or theme...",
        "page_title": "Industry Trend Search Engine",
        "page_subtitle": "Enter an industry keyword to generate trend stage, drivers, market confirmation, validation, and industry-chain mapping.",
        "version": "V1/V2 Framework · V3 Market Data",
        "recognition": "Recognized",
        "category": "Category",
        "fallback_title": "No exact match found",
        "fallback_body": "Showing a general industry trend framework",
        "trend_summary": "Trend Summary",
        "trend_stage": "Trend Stage",
        "framework_scores": "Framework Scores (V1/V2 Mock Framework)",
        "live_title": "Live Market Price Confirmation (V3 Market Data)",
        "live_intro": "This module uses public price data to calculate trend confirmation for representative ETFs and leading companies. It reflects market prices only, not a full fundamental industry conclusion.",
        "price_score_note": "This score is calculated from public price data only. It reflects market-price confirmation, not a full fundamental industry conclusion.",
        "live_unavailable": "Live market confirmation data is unavailable. The V1/V2 mock framework remains displayed.",
        "no_market_mapping": "This industry does not yet have a configured V3 market-price proxy set. The page is currently showing the V1/V2 mock framework only.",
        "cpo_note": "CPO / Optical Module has no dedicated ETF for now, so this module uses representative companies as price proxy samples.",
        "cxo_proxy_note": "CXO has no dedicated ETF for now, so this module uses representative life-science services and outsourcing companies as price proxy samples.",
        "memory_proxy_note": "Memory has no pure dedicated ETF for now, so this module uses semiconductor ETFs and representative memory companies as price proxy samples.",
        "wind_power_proxy_note": "Wind power uses a global wind ETF and representative companies as price proxy samples. Some OTC tickers may be less stable.",
        "proxy_note": "This industry currently uses a representative company basket as a market-price proxy.",
        "sic_proxy_note": "SiC has no dedicated ETF for now, so this module uses representative power-semiconductor companies as price proxy samples.",
        "data_source": "Data Source",
        "updated": "Updated",
        "benchmark": "Benchmark",
        "valid_samples": "Valid Samples",
        "failed": "Failed Tickers",
        "none": "None",
        "mock_confirmation": "Mock Market Confirmation",
        "price_score": "Market Price Confirmation Score",
        "ma20_ratio": "Above MA20 Ratio",
        "ma50_ratio": "Above MA50 Ratio",
        "ma200_ratio": "Above MA200 Ratio",
        "avg_3m": "Average 3M Return",
        "median_3m": "Median 3M Return",
        "benchmark_3m": "Benchmark 3M Return",
        "relative_strength": "Relative Strength",
        "ticker": "Ticker",
        "sample_type": "Sample Type",
        "latest_close": "Latest Close",
        "above_ma20": "Above MA20",
        "above_ma50": "Above MA50",
        "above_ma200": "Above MA200",
        "return_1m": "1M Return",
        "return_3m": "3M Return",
        "return_6m": "6M Return",
        "audit_title": "Data Calculation Audit",
        "close_21d": "Close 21d ago",
        "close_63d": "Close 63d ago",
        "close_126d": "Close 126d ago",
        "key_drivers": "Key Trend Drivers",
        "key_drivers_desc": "Core drivers observe demand, supply, technology, and policy clues behind the industry trend.",
        "subsectors": "Sub-Sectors & Related Themes",
        "subsectors_desc": "Related areas may confirm, lag, recover, or diverge from the headline industry trend.",
        "chain_map": "Industry Chain Map",
        "chain_desc": "The chain map separates upstream inputs, midstream production or platform layers, and downstream demand applications.",
        "catalysts": "Key Catalysts",
        "catalysts_desc": "Catalysts are events or data points that may change trend confirmation, heat level, or validation strength.",
        "risk_signals": "Trend Risk Signals",
        "risk_desc": "Risk signals highlight areas where trend quality may weaken, crowding may rise, or internal consistency may decline.",
        "universe": "Built-in mock industry universe",
        "upstream": "Upstream",
        "midstream": "Midstream",
        "downstream": "Downstream",
        "yes": "Yes",
        "sample_etf": "ETF",
        "sample_leader": "Leader",
        "sample_benchmark": "Benchmark",
        "refresh_market_data": "Refresh market data",
        "failure_reasons": "Failure Reasons",
        "failure_ticker": "Ticker",
        "failure_reason": "Reason",
    },
}

STATUS_COLORS = {
    "Strong Trend": "#22C55E",
    "Trend Intact": "#38BDF8",
    "Diverging": "#FBBF24",
    "Weakening": "#F97316",
    "Broken Trend": "#EF4444",
    "Overheated": "#F59E0B",
    "Strong": "#22C55E",
    "Moderate-Strong": "#38BDF8",
    "Moderate": "#CBD5E1",
    "Recovering": "#A78BFA",
    "Stable": "#94A3B8",
    "Framework": "#CBD5E1",
    "Emerging": "#2DD4BF",
}

STATUS_LABELS = {
    "zh": {
        "Strong Trend": "强趋势",
        "Trend Intact": "趋势仍在",
        "Diverging": "分化",
        "Weakening": "转弱",
        "Broken Trend": "趋势破坏",
        "Overheated": "过热",
        "Strong": "强",
        "Moderate-Strong": "中等偏强",
        "Moderate": "中等",
        "Recovering": "修复中",
        "Stable": "稳定",
        "Framework": "框架观察",
        "Emerging": "正在形成",
    },
    "en": {},
}

CATEGORY_LABELS = {
    "zh": {
        "Technology Growth": "科技成长",
        "New Energy & Manufacturing": "新能源与制造",
        "Commodities": "大宗商品",
        "Consumer": "消费",
        "Financial & Real Estate": "金融地产",
        "Healthcare": "医疗健康",
        "Cyclical & Industrial": "周期与工业",
        "Generic": "通用框架",
    },
    "en": {},
}

METRIC_LABELS = {
    "zh": {
        "Trend Score": "趋势评分",
        "Market Confirmation": "市场确认",
        "Fundamental Validation": "基本验证",
        "Valuation Pressure": "估值压力",
        "Macro Sensitivity": "宏观敏感度",
        "Heat Level": "热度等级",
    },
    "en": {
        "Trend Score": "Trend Score",
        "Market Confirmation": "Market Confirmation",
        "Fundamental Validation": "Fundamental Validation",
        "Valuation Pressure": "Valuation Pressure",
        "Macro Sensitivity": "Macro Sensitivity",
        "Heat Level": "Heat Level",
    },
}

HEAT_LABELS = {
    "zh": {"Low": "低", "Moderate": "中等", "High": "高", "Very High": "很高"},
    "en": {},
}

TREND_STAGE_LABELS_ZH = {
    "Stage 1: Low-attention Accumulation": "第一阶段：低关注酝酿",
    "Stage 2: Trend Confirmation": "第二阶段：趋势确认",
    "Stage 3: Maintrend Expansion": "第三阶段：主升扩散",
    "Stage 4: High-heat Divergence": "第四阶段：高热分化",
    "Stage 5: Overpriced Volatility": "第五阶段：高估值波动",
    "Stage 6: Trend Cooling": "第六阶段：趋势降温",
}

TREND_STATUS_EXPLANATIONS = {
    "zh": {
        "Strong Trend": {
            "label": "强趋势",
            "bias": "明显利好",
            "explanation": "行业处于较明确的上行趋势中，价格确认、热度或框架信号较强。但如果估值压力同步升高，也需要观察是否进入高热阶段。",
        },
        "Trend Intact": {
            "label": "趋势仍在",
            "bias": "偏利好",
            "explanation": "行业主线尚未被破坏，价格与框架信号仍支持趋势延续。相比强趋势，它更偏稳态确认。",
        },
        "Diverging": {
            "label": "分化",
            "bias": "中性偏谨慎",
            "explanation": "行业内部开始出现强弱差异。它不等于趋势结束，但说明市场不再无差别定价，趋势可能从普遍扩散进入精选阶段。",
        },
        "Overheated": {
            "label": "过热",
            "bias": "短期风险",
            "explanation": "市场关注度和估值压力偏高。行业趋势可能仍在，但价格层面已经反映较多乐观预期，后续波动和回撤风险上升。",
        },
        "Weakening": {
            "label": "转弱",
            "bias": "偏风险",
            "explanation": "行业趋势开始失去价格或框架支持，可能是短期调整，也可能是趋势退潮的早期信号，需要继续观察后续是否修复。",
        },
        "Broken Trend": {
            "label": "趋势破坏",
            "bias": "明显风险",
            "explanation": "行业趋势结构明显恶化，市场价格确认不足，框架信号偏弱。通常意味着该行业不再处于有效趋势阶段。",
        },
    },
    "en": {
        "Strong Trend": {
            "label": "Strong Trend",
            "bias": "Strong positive",
            "explanation": "The industry is in a clear upward trend with strong price confirmation, heat, or framework signals. If valuation pressure rises at the same time, it may be moving toward a high-heat phase.",
        },
        "Trend Intact": {
            "label": "Trend Intact",
            "bias": "Positive",
            "explanation": "The main industry trend has not broken. Price and framework signals still support continuation. Compared with Strong Trend, this is more of a steady confirmation state.",
        },
        "Diverging": {
            "label": "Diverging",
            "bias": "Neutral-cautious",
            "explanation": "Internal dispersion is increasing. This does not mean the trend has ended, but the market is no longer pricing the whole industry uniformly.",
        },
        "Overheated": {
            "label": "Overheated",
            "bias": "Short-term risk",
            "explanation": "Attention and valuation pressure are elevated. The trend may still exist, but price already reflects substantial optimism and volatility risk is higher.",
        },
        "Weakening": {
            "label": "Weakening",
            "bias": "Risk-tilted",
            "explanation": "The industry is losing price or framework support. It may be a short-term adjustment or an early cooling signal that needs follow-up confirmation.",
        },
        "Broken Trend": {
            "label": "Broken Trend",
            "bias": "Negative",
            "explanation": "The trend structure has deteriorated, market-price confirmation is insufficient, and framework signals are weak. The industry is usually no longer in an effective trend phase.",
        },
    },
}

TREND_STAGE_EXPLANATIONS = {
    "zh": {
        "Stage 1: Low-attention Accumulation": {
            "label": "第一阶段：低关注酝酿",
            "explanation": "行业有早期变化，但市场关注度不高。",
        },
        "Stage 2: Trend Confirmation": {
            "label": "第二阶段：趋势确认",
            "explanation": "龙头开始走强，市场开始确认行业逻辑。",
        },
        "Stage 3: Maintrend Expansion": {
            "label": "第三阶段：主升扩散",
            "explanation": "趋势进入主升阶段，产业链扩散和市场价格共振。",
        },
        "Stage 4: High-heat Divergence": {
            "label": "第四阶段：高热分化",
            "explanation": "热度较高，龙头可能仍强，但行业内部开始分化。",
        },
        "Stage 5: Overpriced Volatility": {
            "label": "第五阶段：高估值波动",
            "explanation": "估值压力和拥挤度较高，趋势可能仍在，但波动加大。",
        },
        "Stage 6: Trend Cooling": {
            "label": "第六阶段：趋势降温",
            "explanation": "热度、价格确认或基本面预期开始下降，趋势进入降温阶段。",
        },
    },
    "en": {
        "Stage 1: Low-attention Accumulation": {
            "label": "Stage 1: Low-attention Accumulation",
            "explanation": "The industry shows early changes, but market attention remains low.",
        },
        "Stage 2: Trend Confirmation": {
            "label": "Stage 2: Trend Confirmation",
            "explanation": "Leaders begin to strengthen and the market starts confirming the industry logic.",
        },
        "Stage 3: Maintrend Expansion": {
            "label": "Stage 3: Maintrend Expansion",
            "explanation": "The trend enters its main expansion phase, with industry-chain breadth and price confirmation reinforcing each other.",
        },
        "Stage 4: High-heat Divergence": {
            "label": "Stage 4: High-heat Divergence",
            "explanation": "Heat is elevated. Leaders may remain strong, but internal divergence starts to increase.",
        },
        "Stage 5: Overpriced Volatility": {
            "label": "Stage 5: Overpriced Volatility",
            "explanation": "Valuation pressure and crowding are high. The trend may still exist, but volatility increases.",
        },
        "Stage 6: Trend Cooling": {
            "label": "Stage 6: Trend Cooling",
            "explanation": "Heat, price confirmation, or fundamental expectations begin to decline, and the trend enters a cooling phase.",
        },
    },
}

TREND_STAGE_GUIDE = {
    "zh": [
        {
            "stage": "1",
            "key": "Stage 1: Low-attention Accumulation",
            "name": "第一阶段：低关注酝酿",
            "meaning": "行业有早期变化，但市场关注度不高，价格确认通常较弱。",
        },
        {
            "stage": "2",
            "key": "Stage 2: Trend Confirmation",
            "name": "第二阶段：趋势确认",
            "meaning": "龙头开始走强，市场开始确认行业逻辑，价格确认和基本面验证同步增强。",
        },
        {
            "stage": "3",
            "key": "Stage 3: Maintrend Expansion",
            "name": "第三阶段：主升扩散",
            "meaning": "趋势进入主升阶段，产业链扩散和市场价格共振，行业关注度明显提升。",
        },
        {
            "stage": "4",
            "key": "Stage 4: High-heat Divergence",
            "name": "第四阶段：高热分化",
            "meaning": "热度较高，龙头可能仍强，但行业内部开始分化，估值压力上升。",
        },
        {
            "stage": "5",
            "key": "Stage 5: Overpriced Volatility",
            "name": "第五阶段：高估值波动",
            "meaning": "估值压力和拥挤度较高，趋势可能仍在，但价格波动和回撤风险上升。",
        },
        {
            "stage": "6",
            "key": "Stage 6: Trend Cooling",
            "name": "第六阶段：趋势降温",
            "meaning": "热度、价格确认或基本面预期开始下降，趋势进入降温阶段。",
        },
    ],
    "en": [
        {
            "stage": "1",
            "key": "Stage 1: Low-attention Accumulation",
            "name": "Stage 1: Low-attention Accumulation",
            "meaning": "Early industry changes are emerging, but market attention and price confirmation remain limited.",
        },
        {
            "stage": "2",
            "key": "Stage 2: Trend Confirmation",
            "name": "Stage 2: Trend Confirmation",
            "meaning": "Leaders start to outperform, and the market begins to validate the industry logic.",
        },
        {
            "stage": "3",
            "key": "Stage 3: Maintrend Expansion",
            "name": "Stage 3: Maintrend Expansion",
            "meaning": "The trend enters an expansion phase, with supply-chain diffusion and stronger market confirmation.",
        },
        {
            "stage": "4",
            "key": "Stage 4: High-heat Divergence",
            "name": "Stage 4: High-heat Divergence",
            "meaning": "Attention is elevated, leaders may remain strong, but internal dispersion and valuation pressure rise.",
        },
        {
            "stage": "5",
            "key": "Stage 5: Overpriced Volatility",
            "name": "Stage 5: Overpriced Volatility",
            "meaning": "Valuation pressure and crowding are high. The trend may still exist, but volatility risk increases.",
        },
        {
            "stage": "6",
            "key": "Stage 6: Trend Cooling",
            "name": "Stage 6: Trend Cooling",
            "meaning": "Attention, price confirmation, or fundamental expectations begin to decline.",
        },
    ],
}


def render_industry_trend_search_page(lang: str | None = None, show_language_picker: bool = True) -> None:
    """Render the industry trend search page."""

    _apply_industry_css()
    if show_language_picker or lang is None:
        lang = render_language_picker()
    text = TEXT[lang]

    _render_html(
        f"""
        <div class="industry-hero">
            <div>
                <h1>{escape(text["page_title"])}</h1>
                <p>{escape(text["page_subtitle"])}</p>
            </div>
            <div class="industry-version">{escape(text["version"])}</div>
        </div>
        """
    )

    query = st.text_input(
        text["search_placeholder"],
        value="Semiconductor",
        placeholder=text["search_placeholder"],
        label_visibility="collapsed",
    )
    industry, matched = find_industry_trend(query)
    render_recognition_result(industry, matched, lang)

    market_result = get_market_confirmation_data(industry.get("id", ""))
    catalyst = get_effective_catalyst_framework(str(industry.get("id", "")))
    live_news = read_industry_news(str(industry.get("id", "")))
    render_industry_overview(industry, lang)
    render_overall_view_card(industry, market_result, catalyst, lang)
    render_export_context(industry, market_result, catalyst, live_news, lang)
    render_score_grid(industry, lang)
    render_market_price_summary(industry, market_result, lang)
    render_news_heat_summary(catalyst, live_news, lang)

    with st.expander("市场价格明细" if lang == "zh" else "Market Price Details", expanded=False):
        render_market_price_details(industry, market_result, lang)
    with st.expander("新闻与催化事件" if lang == "zh" else "News & Catalysts", expanded=False):
        render_news_and_catalyst_details(industry, catalyst, live_news, lang)
    with st.expander("产业链与风险信号" if lang == "zh" else "Industry Chain & Risk Signals", expanded=False):
        left, right = st.columns([1.35, 1])
        with left:
            render_key_drivers(industry, lang)
            render_industry_chain(industry, lang)
        with right:
            render_subsectors(industry, lang)
            render_risk_signals(industry, lang)
    with st.expander("说明 Guide" if lang == "zh" else "Guides", expanded=False):
        render_trend_explanation_cards(industry, lang)
        render_trend_status_guide(lang, wrap=False)
        render_trend_stage_guide(lang, current_stage=str(industry.get("trendStage", "")), wrap=False)
        render_catalyst_event_guide(lang, wrap=False)
    with st.expander("开发者信息" if lang == "zh" else "Developer Details", expanded=False):
        render_developer_details(industry, market_result, live_news, lang)


def render_language_picker() -> str:
    """Render language selector and return language code."""

    _, right = st.columns([4, 1])
    with right:
        selection = st.selectbox(
            "语言 / Language",
            ["中文", "English"],
            index=0,
            label_visibility="collapsed",
        )
    return "zh" if selection == "中文" else "en"


def render_overall_view_card(industry: dict, market_result: dict, catalyst: dict | None, lang: str) -> None:
    """Render a compact deterministic overall view."""

    text = OVERALL_TEXT[lang]
    price_score = market_result.get("score") if market_result.get("available") else None
    ma50_ratio = market_result.get("above_ma50_ratio") if market_result.get("available") else None
    heat_score = catalyst.get("heat_score") if catalyst else None
    overall = compute_overall_view(
        framework_trend_score=industry.get("trendScore"),
        market_price_confirmation_score=price_score,
        news_heat_score=heat_score,
        valuation_pressure=industry.get("valuationPressure"),
        fundamental_validation=industry.get("fundamentalValidation"),
        ma50_ratio=ma50_ratio,
        trend_stage=trend_stage_text(industry, lang),
        lang=lang,
    )
    with st.container(border=True):
        st.markdown(f"### {text['title']}")
        c1, c2, c3, c4, c5 = st.columns([1.35, 1.35, 1, 1, 1])
        with c1:
            st.metric(text["overall_status"], overall["status_label"])
        with c2:
            st.metric(text["trend_stage"], trend_stage_text(industry, lang))
        with c3:
            st.metric(text["price_confirmation"], format_overall_score(price_score, lang))
        with c4:
            st.metric(text["news_heat"], format_overall_score(heat_score, lang))
        with c5:
            st.metric(text["priced_in_risk"], overall["priced_in_risk_label"])
        st.markdown(f"**{text['key_tags']}**: {', '.join(overall['tags'])}")
        st.markdown(f"**{text['one_line']}**: {overall['one_line']}")


def render_export_context(
    industry: dict,
    market_result: dict,
    catalyst: dict | None,
    live_news: dict,
    lang: str,
) -> None:
    """Render local Markdown / JSON export controls."""

    title = "导出分析上下文" if lang == "zh" else "Export Analysis Context"
    md_label = "复制用 Markdown" if lang == "zh" else "Copy-ready Markdown"
    md_download = "下载 Markdown" if lang == "zh" else "Download Markdown"
    json_download = "下载 JSON" if lang == "zh" else "Download JSON"
    catalyst_review = build_catalyst_review(
        str(industry.get("id", "")),
        catalyst,
        live_news,
        language=lang,
    )
    context = build_industry_export_context(
        industry=industry,
        market_result=market_result,
        catalyst=catalyst,
        live_news=live_news,
        catalyst_review=catalyst_review,
        dynamic_catalyst_snapshot=get_current_dynamic_snapshot(
            str(industry.get("id", "")),
            catalyst,
            live_news,
            catalyst_review,
            lang,
            prefer_cache=False,
        ),
        lang=lang,
        trend_stage=trend_stage_text(industry, lang),
        category=category_label(industry, lang),
        trend_summary=build_trend_summary(industry, lang),
    )
    markdown_text = build_industry_markdown(context, lang)
    json_text = build_industry_json(context)
    industry_id = str(industry.get("id", "industry"))
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    with st.expander(title, expanded=False):
        st.text_area(md_label, markdown_text, height=260)
        left, right = st.columns(2)
        with left:
            st.download_button(
                md_download,
                data=markdown_text.encode("utf-8"),
                file_name=f"industry_analysis_{industry_id}_{today}.md",
                mime="text/markdown",
                width="stretch",
            )
        with right:
            st.download_button(
                json_download,
                data=json_text.encode("utf-8"),
                file_name=f"industry_analysis_{industry_id}_{today}.json",
                mime="application/json",
                width="stretch",
            )


def render_industry_overview(industry: dict, lang: str) -> None:
    """Render headline industry context."""

    text = TEXT[lang]
    status = translate_status(industry["status"], lang)
    color = STATUS_COLORS.get(industry["status"], "#CBD5E1")
    title = industry_title_html(industry, lang)
    kicker = industry_category_path(industry, lang)
    _render_html(
        f"""
        <section class="industry-panel">
            <div class="industry-kicker">{escape(kicker)}</div>
            <div class="industry-title-row">
                <h2>{title}</h2>
                <span class="industry-badge" style="border-color:{color}; color:{color};">{escape(status)}</span>
            </div>
            <p>{escape(get_localized(industry, "overview", lang))}</p>
            <div class="summary-box">
                <div class="stage-label">{escape(text["trend_summary"])}</div>
                <div class="summary-text">{escape(build_trend_summary(industry, lang))}</div>
            </div>
            <div class="stage-box">
                <div class="stage-label">{escape(text["trend_stage"])}</div>
                <div class="stage-value">{escape(trend_stage_text(industry, lang))}</div>
                <div class="stage-note">{escape(get_localized(industry, "trendStageExplanation", lang))}</div>
            </div>
        </section>
        """
    )


def render_trend_explanation_cards(industry: dict, lang: str) -> None:
    """Render localized explanations for the current trend status and stage."""

    status_info = trend_status_info(str(industry.get("status", "")), lang)
    stage_info = trend_stage_info(str(industry.get("trendStage", "")), lang)
    headings = {
        "zh": ("趋势状态解释", "趋势阶段解释", "倾向"),
        "en": ("Trend Status Explanation", "Trend Stage Explanation", "Bias"),
    }
    status_heading, stage_heading, bias_label = headings[lang]
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown(f"**{status_heading}**")
            st.markdown(f"{status_info['label']} · {bias_label}: {status_info['bias']}")
            st.markdown(status_info["explanation"])
    with right:
        with st.container(border=True):
            st.markdown(f"**{stage_heading}**")
            st.markdown(stage_info["label"])
            st.markdown(stage_info["explanation"])


def render_score_grid(industry: dict, lang: str) -> None:
    """Render V1/V2 framework score cards."""

    text = TEXT[lang]
    st.markdown(f"### {text['framework_scores']}")
    score_items = [
        ("Trend Score", industry["trendScore"], framework_explanation("trend", lang)),
        ("Market Confirmation", industry["marketConfirmation"], framework_explanation("market", lang)),
        ("Fundamental Validation", industry["fundamentalValidation"], framework_explanation("validation", lang)),
        ("Valuation Pressure", industry["valuationPressure"], framework_explanation("valuation", lang)),
        ("Macro Sensitivity", industry["macroSensitivity"], framework_explanation("macro", lang)),
        ("Heat Level", industry["heatLevel"], framework_explanation("heat", lang)),
    ]
    for row_start in range(0, len(score_items), 3):
        cols = st.columns(3)
        for col, item in zip(cols, score_items[row_start : row_start + 3]):
            label, value, explanation = item
            with col:
                if label == "Heat Level":
                    render_heat_card_native(str(value), explanation, lang)
                else:
                    render_score_card_native(label, float(value), explanation, lang)


def render_score_card_native(label: str, value: float, explanation: str, lang: str) -> None:
    """Render one score card without raw HTML."""

    pct = max(0.0, min(value / 10, 1.0))
    with st.container(border=True):
        st.markdown(f"**{METRIC_LABELS[lang].get(label, label)}**")
        st.metric(label="Score", value=f"{value:.1f}", label_visibility="collapsed")
        st.progress(pct)
        st.markdown(explanation)


def render_heat_card_native(heat_level: str, explanation: str, lang: str) -> None:
    """Render heat-level card without raw HTML."""

    heat_progress = {
        "Low": 0.25,
        "Moderate": 0.5,
        "High": 0.75,
        "Very High": 1.0,
    }.get(heat_level, 0.5)
    with st.container(border=True):
        st.markdown(f"**{METRIC_LABELS[lang]['Heat Level']}**")
        st.metric(label="Heat Level", value=HEAT_LABELS[lang].get(heat_level, heat_level), label_visibility="collapsed")
        st.progress(heat_progress)
        st.markdown(explanation)


def render_live_market_confirmation(
    industry: dict,
    lang: str,
    result: dict | None = None,
    mode: str = "simple",
) -> None:
    """Render live price-based market confirmation data."""

    text = TEXT[lang]
    st.markdown(f"### {text['live_title']}")
    st.markdown(text["live_intro"])
    st.caption(text["price_score_note"])

    refresh_clicked = st.button(text["refresh_market_data"], key=f"refresh_market_data_{industry.get('id', 'unknown')}")
    if refresh_clicked:
        get_market_confirmation_data.clear()
    result = get_market_confirmation_data(industry.get("id", "")) if refresh_clicked or result is None else result
    if not result.get("available"):
        if result.get("reason_code") == "no_market_mapping":
            st.info(text["no_market_mapping"])
            return
        st.info(text["live_unavailable"])
        return

    if result.get("proxy_note_key"):
        st.info(text.get(result["proxy_note_key"], text["proxy_note"]))
    elif industry.get("id") == "cpo_optical_module":
        st.info(text["cpo_note"])
    elif result.get("no_dedicated_etf") or not result.get("has_etf_sample"):
        st.info(text["proxy_note"])

    if mode in {"detailed", "developer"}:
        render_market_meta_strip(result, lang)
    if mode == "developer":
        render_failure_reasons(result, lang)
    render_live_market_metrics(industry, result, lang)

    details = result.get("details") or []
    if details and mode in {"detailed", "developer"}:
        st.dataframe(build_market_detail_table(details, lang), width="stretch", hide_index=True)
        if mode == "developer":
            with st.expander(text["audit_title"], expanded=False):
                st.dataframe(build_market_audit_table(details, lang), width="stretch", hide_index=True)


def render_market_price_summary(industry: dict, result: dict, lang: str) -> None:
    """Render compact V3 market-price summary."""

    text = TEXT[lang]
    st.markdown(f"### {text['live_title']}")
    if not result.get("available"):
        if result.get("reason_code") == "no_market_mapping":
            st.info(text["no_market_mapping"])
        else:
            st.info(text["live_unavailable"])
        return
    items = [
        (text["price_score"], format_score(result.get("score"))),
        (text["ma50_ratio"], format_ratio_with_count(result, "above_ma50")),
        (text["median_3m"], format_percent(result.get("median_3m_return"))),
        (text["relative_strength"], format_percent(result.get("relative_strength"))),
        ("V3 状态" if lang == "zh" else "V3 Status", "正常" if lang == "zh" else "Available"),
    ]
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            st.metric(label, value)


def render_market_price_details(industry: dict, result: dict, lang: str) -> None:
    """Render ticker-level V3 market-price details."""

    text = TEXT[lang]
    if st.button(text["refresh_market_data"], key=f"refresh_market_detail_{industry.get('id', 'unknown')}"):
        get_market_confirmation_data.clear()
        result = get_market_confirmation_data(industry.get("id", ""))
    if not result.get("available"):
        st.info(text["live_unavailable"])
        return
    render_market_meta_strip(result, lang)
    details = result.get("details") or []
    if details:
        st.dataframe(build_market_detail_table(details, lang), width="stretch", hide_index=True)


def render_developer_details(industry: dict, result: dict, live_news: dict, lang: str) -> None:
    """Render folded developer diagnostics."""

    if result.get("available"):
        failures = result.get("failed_ticker_details") or []
        if failures:
            text = TEXT[lang]
            rows = [
                {
                    text["failure_ticker"]: item.get("ticker", ""),
                    text["failure_reason"]: failure_reason_label(item.get("reason", ""), lang),
                    "debug": item.get("debug", ""),
                }
                for item in failures
            ]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        details = result.get("details") or []
        if details:
            st.dataframe(build_market_audit_table(details, lang), width="stretch", hide_index=True)
    st.json(
        {
            "industry_id": industry.get("id"),
            "market_status": "available" if result.get("available") else result.get("reason_code"),
            "failed_tickers": result.get("failed_tickers") or [],
            "live_news_status": live_news.get("live_news_status"),
            "live_news_last_updated": live_news.get("live_news_last_updated"),
        }
    )


CATALYST_TEXT = {
    "zh": {
        "title": "新闻热度与催化事件（V4.1 Framework）",
        "note": "V4.1 使用本地催化事件框架，事件日期为框架记录日期，不代表实时新闻发布时间。",
        "missing": "当前行业尚未配置 V4.1 催化事件框架数据。",
        "heat_score": "热度分数",
        "heat_level": "热度等级",
        "heat_direction": "热度方向",
        "date": "框架日期",
        "event": "事件",
        "type": "类型",
        "impact": "影响",
        "confidence": "可信度",
        "description": "说明",
    },
    "en": {
        "title": "News Heat & Catalysts (V4.1 Framework)",
        "note": "V4.1 uses local catalyst framework data. Event dates are framework record dates, not live news publication dates.",
        "missing": "This industry does not yet have V4.1 catalyst framework data configured.",
        "heat_score": "Heat Score",
        "heat_level": "Heat Level",
        "heat_direction": "Heat Direction",
        "date": "Framework Date",
        "event": "Event",
        "type": "Type",
        "impact": "Impact",
        "confidence": "Confidence",
        "description": "Description",
    },
}

CATALYST_TEXT["zh"].update(
    {
        "title": "本地催化框架（V4.1）",
        "note": "V4.1 是本地行业研究框架，事件日期为框架记录日期，不会自动每日改写；V4.12 会基于实时新闻与复核结果生成动态快照。",
    }
)
CATALYST_TEXT["en"].update(
    {
        "title": "Local Catalyst Framework (V4.1)",
        "note": "V4.1 is a local industry research framework. Event dates are framework record dates and are not automatically overwritten daily. V4.12 generates a dynamic snapshot based on live news and catalyst review results.",
    }
)

CATALYST_TEXT["zh"].update(
    {
        "framework_status": "框架状态",
        "framework_updated": "框架已更新",
        "framework_base": "使用基础本地框架",
        "latest_framework_updated_at": "最新框架更新时间",
        "base_framework_dates": "基础框架记录日期",
        "framework_events_updated": "事件表使用最新框架事件。",
        "framework_summary_only_note": "当前更新仅包含摘要，事件仍沿用基础框架；基础框架记录日期仅作为历史说明。",
        "framework_base_date_note": "当前框架摘要已更新；事件表中的日期仍为基础框架记录日期，仅作为历史说明，不代表更新未生效。",
        "framework_no_events": "暂无可展示的催化事件。",
    }
)
CATALYST_TEXT["en"].update(
    {
        "framework_status": "Framework Status",
        "framework_updated": "Framework Updated",
        "framework_base": "Using Base Local Framework",
        "latest_framework_updated_at": "Latest Framework Updated At",
        "base_framework_dates": "Base Framework Record Dates",
        "framework_events_updated": "The event table uses updated framework events.",
        "framework_summary_only_note": "This update contains summary changes only; events still fall back to the base framework. Base framework record dates are historical context.",
        "framework_base_date_note": "The framework summary has been updated; event dates shown here are still base framework record dates for historical context, not evidence that the update failed.",
        "framework_no_events": "No catalyst events to display.",
    }
)


def render_news_heat_catalysts(
    industry: dict,
    lang: str,
    catalyst: dict | None = None,
    mode: str = "simple",
) -> None:
    """Render local V4.1 catalyst framework data for one industry."""

    text = CATALYST_TEXT[lang]
    st.markdown(f"### {text['title']}")
    st.caption(text["note"])
    catalyst = catalyst or get_effective_catalyst_framework(str(industry.get("id", "")))
    if not catalyst:
        st.info(text["missing"])
        return

    cols = st.columns(3)
    with cols[0]:
        st.metric(text["heat_score"], format_score(catalyst.get("heat_score")))
    with cols[1]:
        st.metric(text["heat_level"], localized_label(HEAT_LEVEL_LABELS, catalyst.get("heat_level"), lang))
    with cols[2]:
        st.metric(
            text["heat_direction"],
            localized_label(HEAT_DIRECTION_LABELS, catalyst.get("heat_direction"), lang),
        )
    summary_key = "summaryZh" if lang == "zh" else "summary"
    st.markdown(str(catalyst.get(summary_key) or catalyst.get("summary") or ""))
    render_catalyst_framework_meta(catalyst, lang)

    events, uses_base_event_fallback = framework_events_for_display(industry, catalyst)
    if catalyst.get("is_override"):
        if uses_base_event_fallback:
            st.info(text["framework_summary_only_note"])
        elif framework_events_use_base_dates(catalyst, events):
            st.info(text["framework_base_date_note"])
        else:
            st.caption(text["framework_events_updated"])

    rows = []
    for event in events:
        rows.append(
            {
                text["date"]: event.get("date", ""),
                text["event"]: event.get("titleZh" if lang == "zh" else "title", ""),
                text["type"]: event.get("event_typeZh")
                if lang == "zh"
                else localized_label(EVENT_TYPE_LABELS, event.get("event_type"), lang),
                text["impact"]: event.get("impactZh")
                if lang == "zh"
                else localized_label(IMPACT_LABELS, event.get("impact"), lang),
                text["confidence"]: event.get("confidenceZh")
                if lang == "zh"
                else localized_label(CONFIDENCE_LABELS, event.get("confidence"), lang),
                text["description"]: event.get("descriptionZh" if lang == "zh" else "description", ""),
            }
        )
    if rows and mode in {"detailed", "developer"}:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    elif mode in {"detailed", "developer"}:
        st.info(text["framework_no_events"])


def render_catalyst_framework_meta(catalyst: dict, lang: str) -> None:
    """Render effective V4.1 framework metadata."""

    text = CATALYST_TEXT[lang]
    base_dates = ", ".join(str(item) for item in (catalyst.get("base_framework_dates") or [])) or text["missing"]
    status_text = text["framework_updated"] if catalyst.get("is_override") else text["framework_base"]
    items = [(text["framework_status"], status_text), (text["base_framework_dates"], base_dates)]
    if catalyst.get("is_override"):
        items.insert(1, (text["latest_framework_updated_at"], format_datetime_compact(catalyst.get("updated_at"), lang)))
    render_compact_info_items(items, columns=2)


def framework_events_for_display(industry: dict, catalyst: dict) -> tuple[list[dict], bool]:
    """Return events for the V4.1 table and whether they fall back to base events."""

    events = [
        event
        for event in (catalyst.get("events") or [])
        if isinstance(event, dict)
    ]
    if not catalyst.get("is_override"):
        return events, False

    override = catalyst.get("override") if isinstance(catalyst.get("override"), dict) else {}
    override_events = override.get("events")
    if isinstance(override_events, list) and not override_events:
        base = get_base_catalyst_framework(str(industry.get("id", ""))) or {}
        base_events = [
            event
            for event in (base.get("events") or [])
            if isinstance(event, dict)
        ]
        return base_events, True

    return events, False


def framework_events_use_base_dates(catalyst: dict, events: list[dict]) -> bool:
    """Detect overrides whose event rows still carry base framework record dates."""

    if not catalyst.get("is_override") or not events:
        return False
    base_dates = {
        str(item)
        for item in (catalyst.get("base_framework_dates") or [])
        if item
    }
    if not base_dates:
        return False
    event_dates = {
        str(event.get("date", ""))
        for event in events
        if event.get("date")
    }
    if not event_dates or not event_dates.issubset(base_dates):
        return False
    updated_date = str(catalyst.get("updated_at") or "")[:10]
    return bool(updated_date and updated_date not in event_dates)


def render_news_heat_summary(catalyst: dict | None, live_news: dict, lang: str) -> None:
    """Render compact V4 heat and live-news summary."""

    text = CATALYST_TEXT[lang]
    live_text = LIVE_NEWS_TEXT[lang]
    st.markdown(f"### {text['title']}")
    if not catalyst:
        st.info(text["missing"])
        return
    cols = st.columns(4)
    with cols[0]:
        st.metric(text["heat_score"], format_score(catalyst.get("heat_score")))
    with cols[1]:
        st.metric(text["heat_direction"], localized_label(HEAT_DIRECTION_LABELS, catalyst.get("heat_direction"), lang))
    with cols[2]:
        st.metric(live_text["count_7d"], str(live_news.get("live_news_count_7d", 0)))
    with cols[3]:
        status = str(live_news.get("live_news_status", "not_configured"))
        st.metric(live_text["status"], live_text["statuses"].get(status, status))
    summary_key = "summaryZh" if lang == "zh" else "summary"
    st.markdown(str(catalyst.get(summary_key) or catalyst.get("summary") or ""))
    render_catalyst_framework_meta(catalyst, lang)


def render_news_and_catalyst_details(
    industry: dict,
    catalyst: dict | None,
    live_news: dict,
    lang: str,
) -> None:
    """Render event table, news refresh, and cached live news list."""

    render_news_heat_catalysts(industry, lang, catalyst=catalyst, mode="detailed")
    live_news = render_live_news_watch(industry, lang, cached_result=live_news, mode="detailed")
    review = build_catalyst_review(
        str(industry.get("id", "")),
        catalyst,
        live_news,
        language=lang,
    )
    render_dynamic_catalyst_snapshot(industry, catalyst, live_news, review, lang)
    expander_title = "查看催化复核细节（V4.10）" if lang == "zh" else "View Catalyst Review Details (V4.10)"
    with st.expander(expander_title, expanded=False):
        render_catalyst_review(industry, catalyst, live_news, lang, review=review)


CATALYST_REVIEW_TEXT = {
    "zh": {
        "title": "催化复核（V4.10）",
        "note": "V4.10 使用实时新闻观察结果复核本地催化框架，但不会自动改写框架数据。",
        "status": "复核状态",
        "evidence": "证据强度",
        "one_line": "一句话复核",
        "supported": "已被实时新闻支持的催化线索",
        "emerging": "新出现的催化线索",
        "weak": "证据不足或覆盖不足说明",
        "coverage": "覆盖说明",
        "reviewed_at": "复核时间",
        "none": "暂无",
    },
    "en": {
        "title": "Catalyst Review (V4.10)",
        "note": "V4.10 reviews the local catalyst framework using live news observations, but does not automatically rewrite framework data.",
        "status": "Review Status",
        "evidence": "Evidence Level",
        "one_line": "One-line Review",
        "supported": "Catalyst Clues Supported by Live News",
        "emerging": "Emerging Catalyst Clues",
        "weak": "Weak or Missing Evidence",
        "coverage": "Coverage Note",
        "reviewed_at": "Reviewed At",
        "none": "N/A",
    },
}


def render_catalyst_review(
    industry: dict,
    catalyst: dict | None,
    live_news: dict,
    lang: str,
    review: dict | None = None,
) -> dict:
    """Render V4.10 deterministic catalyst review."""

    text = CATALYST_REVIEW_TEXT[lang]
    review = review or build_catalyst_review(
        str(industry.get("id", "")),
        catalyst,
        live_news,
        language=lang,
    )
    st.markdown(f"### {text['title']}")
    st.caption(text["note"])
    status = review["review_status_zh"] if lang == "zh" else review["review_status"]
    evidence = review["evidence_level_zh"] if lang == "zh" else review["evidence_level"]
    render_compact_info_items(
        [
            (text["status"], status),
            (text["evidence"], evidence),
            (text["reviewed_at"], format_datetime_compact(review.get("reviewed_at"), lang)),
        ],
        columns=3,
    )
    one_line = review["one_line_review_zh"] if lang == "zh" else review["one_line_review"]
    coverage = review["coverage_note_zh"] if lang == "zh" else review["coverage_note"]
    st.markdown(f"**{text['one_line']}**：{one_line}")
    st.caption(f"{text['coverage']}：{coverage}")
    rows = [
        (text["supported"], review.get("supported_catalysts") or []),
        (text["emerging"], review.get("emerging_catalysts") or []),
        (text["weak"], review.get("weak_or_missing_evidence") or []),
    ]
    for label, values in rows:
        value_text = ", ".join(str(value) for value in values) if values else text["none"]
        st.markdown(f"**{label}**：{value_text}")

    return review


CATALYST_SNAPSHOT_TEXT = {
    "zh": {
        "title": "动态催化快照（V4.12）",
        "note": "V4.12 基于实时新闻与催化复核结果生成动态快照，但不会自动改写 V4.1 本地框架数据。",
        "generated_at": "快照更新时间",
        "framework_dates": "本地框架记录日期",
        "status": "动态状态",
        "evidence": "证据强度",
        "one_line": "一句话快照",
        "active": "当前活跃催化",
        "emerging": "新出现催化线索",
        "cooling": "降温催化线索",
        "coverage": "覆盖说明",
        "none": "暂无",
    },
    "en": {
        "title": "Dynamic Catalyst Snapshot (V4.12)",
        "note": "V4.12 generates a dynamic snapshot from live news and catalyst review results, but does not automatically rewrite V4.1 local framework data.",
        "generated_at": "Snapshot Updated",
        "framework_dates": "Framework Record Dates",
        "status": "Dynamic Status",
        "evidence": "Evidence Level",
        "one_line": "One-line Snapshot",
        "active": "Active Catalysts",
        "emerging": "Emerging Catalyst Clues",
        "cooling": "Cooling Catalyst Clues",
        "coverage": "Coverage Note",
        "none": "N/A",
    },
}

CATALYST_SNAPSHOT_TEXT["zh"].update(
    {
        "active": "当前活跃催化主题",
        "emerging": "新出现催化主题",
        "apply_framework": "应用为最新催化框架",
        "apply_success": "已应用为最新催化框架。页面刷新后 V4.1 将显示更新后的框架。",
    }
)
CATALYST_SNAPSHOT_TEXT["en"].update(
    {
        "active": "Active Catalyst Themes",
        "emerging": "Emerging Catalyst Themes",
        "apply_framework": "Apply as Latest Catalyst Framework",
        "apply_success": "Applied as latest catalyst framework. V4.1 will show the updated framework after refresh.",
    }
)


def get_current_dynamic_snapshot(
    industry_id: str,
    catalyst: dict | None,
    live_news: dict,
    catalyst_review: dict,
    lang: str,
    *,
    prefer_cache: bool = True,
) -> dict:
    """Read cached V4.12 snapshot first, or build one locally without network access."""

    if prefer_cache:
        cached = read_dynamic_catalyst_snapshot(industry_id)
        if cached:
            return cached
    return build_dynamic_catalyst_snapshot(
        industry_id,
        catalyst,
        live_news,
        catalyst_review,
        language=lang,
    )


def render_dynamic_catalyst_snapshot(
    industry: dict,
    catalyst: dict | None,
    live_news: dict,
    catalyst_review: dict,
    lang: str,
) -> None:
    """Render and cache the V4.12 dynamic catalyst snapshot."""

    text = CATALYST_SNAPSHOT_TEXT[lang]
    industry_id = str(industry.get("id", ""))
    snapshot = build_dynamic_catalyst_snapshot(
        industry_id,
        catalyst,
        live_news,
        catalyst_review,
        language=lang,
    )
    save_dynamic_catalyst_snapshot(snapshot)
    st.markdown(f"### {text['title']}")
    st.caption(text["note"])
    dates = ", ".join(snapshot.get("framework_record_dates") or []) or text["none"]
    status = snapshot.get("review_status_zh") if lang == "zh" else snapshot.get("review_status")
    evidence = snapshot.get("evidence_level_zh") if lang == "zh" else snapshot.get("evidence_level")
    render_compact_info_items(
        [
            (text["generated_at"], format_datetime_compact(snapshot.get("snapshot_generated_at"), lang)),
            (text["framework_dates"], dates),
            (text["status"], status or text["none"]),
            (text["evidence"], evidence or text["none"]),
        ],
        columns=2,
    )
    one_line = snapshot.get("one_line_snapshot_zh") if lang == "zh" else snapshot.get("one_line_snapshot")
    coverage = snapshot.get("coverage_note_zh") if lang == "zh" else snapshot.get("coverage_note")
    st.markdown(f"**{text['one_line']}**: {one_line or text['none']}")
    st.caption(f"{text['coverage']}: {coverage or text['none']}")
    render_catalyst_theme_group(text["active"], snapshot.get("active_catalyst_themes") or [], lang, text["none"])
    render_catalyst_theme_group(text["emerging"], snapshot.get("emerging_catalyst_themes") or [], lang, text["none"])
    cooling_values = snapshot.get("cooling_catalysts_zh") if lang == "zh" else snapshot.get("cooling_catalysts")
    cooling_text = ", ".join(str(value) for value in (cooling_values or [])) if cooling_values else text["none"]
    st.markdown(f"**{text['cooling']}**: {cooling_text}")
    if st.button(text["apply_framework"], key=f"apply_catalyst_framework_{industry_id}", width="content"):
        apply_snapshot_as_framework_override(industry_id, None, snapshot, catalyst_review, live_news)
        st.success(text["apply_success"])
        st.rerun()


def render_catalyst_theme_group(label: str, themes: list[dict], lang: str, empty_text: str) -> None:
    """Render normalized catalyst themes instead of raw keyword strings."""

    st.markdown(f"**{label}**")
    if not themes:
        st.caption(empty_text)
        return
    for theme in themes:
        terms = ", ".join(str(item) for item in (theme.get("matched_terms") or [])[:6])
        reason = theme_reason(theme, lang)
        name = theme_display_name(theme, lang)
        suffix = f"（{terms}）" if lang == "zh" and terms else f" ({terms})" if terms else ""
        st.markdown(f"- **{name}**{suffix}")
        if reason:
            st.caption(reason)


def render_catalyst_event_guide(lang: str, title_override: str | None = None, wrap: bool = True) -> None:
    """Render the local V4.1 catalyst guide."""

    guide = CATALYST_GUIDE[lang]
    title = title_override or guide["title"]
    if wrap:
        with st.expander(title, expanded=False):
            render_catalyst_event_guide(lang, title_override=title_override, wrap=False)
        return
    st.markdown(f"**{title}**")
    for section_key, section_title_key in [
        ("event_types", "event_types_title"),
        ("impact", "impact_title"),
        ("confidence", "confidence_title"),
        ("heat", "heat_title"),
    ]:
        st.markdown(f"**{guide[section_title_key]}**")
        st.dataframe(
            catalyst_guide_frame(guide[section_key], guide["columns"]),
            width="stretch",
            hide_index=True,
        )


def catalyst_guide_frame(items: dict[str, str], columns: dict[str, str]) -> pd.DataFrame:
    """Build a two-column guide dataframe."""

    return pd.DataFrame([{columns["item"]: key, columns["meaning"]: value} for key, value in items.items()])


LIVE_NEWS_TEXT = {
    "zh": {
        "title": "实时新闻观察（V4.2 Lite）",
        "note": "V4.2 仅展示当前新闻源抓取到的高相关新闻，用于辅助观察，不代表完整新闻覆盖。",
        "unavailable": "实时新闻暂不可用，当前仍展示 V4.1 本地催化事件框架。",
        "refresh": "刷新新闻数据",
        "source": "数据源",
        "updated": "新闻缓存更新时间",
        "count_7d": "最近7天高相关新闻数量",
        "latest": "最近高相关新闻时间",
        "status": "实时新闻状态",
        "cache_missing": "暂无缓存新闻。请点击刷新新闻数据。",
        "no_high_relevance": "新闻缓存已更新，但当前来源暂无高相关实时新闻。该结果可能受 Yahoo Finance / yfinance 对细分主题覆盖限制影响。",
        "time": "时间",
        "title_col": "标题",
        "publisher": "来源",
        "tickers": "相关代码",
        "keywords": "匹配关键词",
        "link": "链接",
        "na": "暂无",
        "statuses": {
            "available": "可用",
            "no_recent_news": "暂无近期新闻",
            "fetch_failed": "抓取失败",
            "not_configured": "未配置",
        },
    },
    "en": {
        "title": "Live News Watch (V4.2 Lite)",
        "note": "V4.2 shows high-relevance news captured by the current source and does not represent complete news coverage.",
        "unavailable": "Live news is currently unavailable. The page is still showing the V4.1 local catalyst framework.",
        "refresh": "Refresh News Data",
        "source": "Data Source",
        "updated": "News Cache Updated",
        "count_7d": "7D High-relevance News Count",
        "latest": "Latest High-relevance News Time",
        "status": "Live News Status",
        "cache_missing": "No cached news yet. Use Refresh News Data.",
        "no_high_relevance": "News cache is updated, but no high-relevance live news is available from the current source. This may reflect limited Yahoo Finance / yfinance coverage for niche themes.",
        "time": "Time",
        "title_col": "Title",
        "publisher": "Source",
        "tickers": "Related Tickers",
        "keywords": "Matched Keywords",
        "link": "Link",
        "na": "N/A",
        "statuses": {
            "available": "available",
            "no_recent_news": "no_recent_news",
            "fetch_failed": "fetch_failed",
            "not_configured": "not_configured",
        },
    },
}


LIVE_NEWS_TEXT["zh"].update(
    {
        "news_source": "新闻来源",
        "source_type": "来源类型",
        "no_high_relevance": "当前已刷新可用新闻源，但暂无高相关实时新闻。该结果可能受当前新闻源覆盖限制影响。",
    }
)
LIVE_NEWS_TEXT["en"].update(
    {
        "news_source": "News Source",
        "source_type": "Source Type",
        "no_high_relevance": "Available news sources have been refreshed, but no high-relevance live news is available. This may reflect coverage limits of the current sources.",
    }
)


def render_live_news_watch(
    industry: dict,
    lang: str,
    cached_result: dict | None = None,
    mode: str = "simple",
) -> dict:
    """Render V4.2 cached live-news watch module."""

    text = LIVE_NEWS_TEXT[lang]
    st.markdown(f"### {text['title']}")
    st.caption(text["note"])
    if st.button(text["refresh"], key=f"refresh_news_{industry.get('id')}", width="content"):
        news_result = refresh_industry_news(industry)
    else:
        news_result = cached_result or read_industry_news(str(industry.get("id", "")))

    status = str(news_result.get("live_news_status", "not_configured"))
    if status == "fetch_failed":
        st.info(text["unavailable"])
    elif news_result.get("failed_reason") == "cache_missing":
        st.info(text["cache_missing"])

    source_names = news_result.get("source_names") or []
    source_types = news_result.get("source_types") or []
    source_value = ", ".join(source_names) if source_names else news_result.get("source") or text["na"]
    source_type_value = ", ".join(source_types) if source_types else text["na"]
    render_compact_info_items(
        [
            (text["news_source"], source_value),
            (text["source_type"], source_type_value),
            (text["updated"], format_datetime_compact(news_result.get("live_news_last_updated"), lang)),
            (text["count_7d"], str(news_result.get("live_news_count_7d", 0))),
            (text["latest"], format_datetime_compact(news_result.get("latest_news_time"), lang)),
        ],
        columns=2,
    )
    st.caption(f"{text['status']}: {text['statuses'].get(status, status)}")

    if mode == "simple":
        return news_result

    rows = []
    for item in (news_result.get("items") or [])[:5]:
        rows.append(
            {
                text["time"]: item.get("published_at", ""),
                text["title_col"]: item.get("title", ""),
                text["publisher"]: item.get("publisher", ""),
                text["tickers"]: ", ".join(item.get("related_tickers", [])),
                text["keywords"]: ", ".join(item.get("matched_keywords", [])),
                text["link"]: item.get("link", ""),
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.info(text["no_high_relevance"])
    return news_result


def render_market_meta_strip(result: dict, lang: str) -> None:
    """Render compact market data metadata."""

    text = TEXT[lang]
    failed_tickers = result.get("failed_tickers") or []
    failed_text = ", ".join(failed_tickers) if failed_tickers else text["none"]
    _render_html(
        f"""
        <div class="market-meta-strip">
            {escape(text["data_source"])}：{escape(result.get("data_source", "Yahoo Finance via yfinance"))}
            <span>｜</span> {escape(text["updated"])}：{escape(result.get("last_updated") or "N/A")}
            <span>｜</span> {escape(text["benchmark"])}：{escape(result.get("benchmark_ticker") or "N/A")}
            <span>｜</span> {escape(text["valid_samples"])}：{escape(result.get("valid_ticker_count", 0))}
            <span>｜</span> {escape(text["failed"])}：{escape(failed_text)}
        </div>
        """
    )


def render_failure_reasons(result: dict, lang: str) -> None:
    """Render failed ticker reasons when present."""

    failures = result.get("failed_ticker_details") or []
    if not failures:
        return
    text = TEXT[lang]
    rows = [
        {
            text["failure_ticker"]: item.get("ticker", ""),
            text["failure_reason"]: failure_reason_label(item.get("reason", ""), lang),
            "debug": item.get("debug", ""),
        }
        for item in failures
    ]
    with st.expander(text["failure_reasons"], expanded=False):
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_live_market_metrics(industry: dict, result: dict, lang: str) -> None:
    """Render live market confirmation metrics."""

    text = TEXT[lang]
    metric_items = [
        (text["mock_confirmation"], format_score(industry.get("marketConfirmation"))),
        (text["price_score"], format_score(result.get("score"))),
        (text["ma20_ratio"], format_ratio_with_count(result, "above_ma20")),
        (text["ma50_ratio"], format_ratio_with_count(result, "above_ma50")),
        (text["ma200_ratio"], format_ratio_with_count(result, "above_ma200")),
        (text["avg_3m"], format_percent(result.get("average_3m_return"))),
        (text["median_3m"], format_percent(result.get("median_3m_return"))),
        (text["benchmark_3m"], format_percent(result.get("benchmark_3m_return"))),
        (text["relative_strength"], format_percent(result.get("relative_strength"))),
    ]
    for row_start in range(0, len(metric_items), 3):
        cols = st.columns(3)
        for col, (label, value) in zip(cols, metric_items[row_start : row_start + 3]):
            with col:
                st.metric(label, value)


def build_market_detail_table(details: list[dict], lang: str) -> pd.DataFrame:
    """Build a display table for ticker-level market confirmation data."""

    text = TEXT[lang]
    rows = []
    for item in details:
        rows.append(
            {
                text["ticker"]: item.get("ticker", ""),
                text["sample_type"]: sample_type_label(item.get("sample_type"), lang),
                text["latest_close"]: format_price(item.get("latest_close")),
                text["above_ma20"]: format_bool(item.get("above_ma20"), lang),
                text["above_ma50"]: format_bool(item.get("above_ma50"), lang),
                text["above_ma200"]: format_bool(item.get("above_ma200"), lang),
                text["return_1m"]: format_percent(item.get("return_1m")),
                text["return_3m"]: format_percent(item.get("return_3m")),
                text["return_6m"]: format_percent(item.get("return_6m")),
            }
        )
    return pd.DataFrame(rows)


def build_market_audit_table(details: list[dict], lang: str) -> pd.DataFrame:
    """Build a return-calculation audit table."""

    text = TEXT[lang]
    rows = []
    for item in details:
        rows.append(
            {
                text["ticker"]: item.get("ticker", ""),
                text["latest_close"]: format_price(item.get("latest_close")),
                text["close_21d"]: format_price(item.get("close_21d_ago")),
                text["close_63d"]: format_price(item.get("close_63d_ago")),
                text["close_126d"]: format_price(item.get("close_126d_ago")),
                text["return_1m"]: format_percent(item.get("return_1m")),
                text["return_3m"]: format_percent(item.get("return_3m")),
                text["return_6m"]: format_percent(item.get("return_6m")),
            }
        )
    return pd.DataFrame(rows)


def render_key_drivers(industry: dict, lang: str) -> None:
    """Render key trend drivers."""

    text = TEXT[lang]
    rows = "".join(
        render_labeled_row(
            item_text(driver, "name", lang),
            driver["status"],
            item_text(driver, "explanation", lang),
            lang,
        )
        for driver in industry["keyDrivers"]
    )
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>{escape(text["key_drivers"])}</h3>
            <p>{escape(text["key_drivers_desc"])}</p>
            {rows}
        </section>
        """
    )


def render_subsectors(industry: dict, lang: str) -> None:
    """Render sub-sector chips."""

    text = TEXT[lang]
    chips = "".join(
        f'<span class="theme-chip">{escape(item_text(item, "name", lang))} | {escape(translate_status(item["status"], lang))}</span>'
        for item in industry["subSectors"]
    )
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>{escape(text["subsectors"])}</h3>
            <p>{escape(text["subsectors_desc"])}</p>
            <div class="chip-wrap">{chips}</div>
        </section>
        """
    )


def render_industry_chain(industry: dict, lang: str) -> None:
    """Render upstream, midstream, and downstream chain map."""

    text = TEXT[lang]
    chain = industry_chain(industry, lang)
    columns = [
        (text["upstream"], chain.get("upstream", [])),
        (text["midstream"], chain.get("midstream", [])),
        (text["downstream"], chain.get("downstream", [])),
    ]
    body = ""
    for title, values in columns:
        items = "".join(f"<li>{escape(value)}</li>" for value in values)
        body += f'<div class="chain-column"><h4>{escape(title)}</h4><ul>{items}</ul></div>'
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>{escape(text["chain_map"])}</h3>
            <p>{escape(text["chain_desc"])}</p>
            <div class="chain-grid">{body}</div>
        </section>
        """
    )


def render_catalysts(industry: dict, lang: str) -> None:
    """Render catalysts."""

    text = TEXT[lang]
    items = "".join(f"<li>{escape(item)}</li>" for item in list_text(industry, "catalysts", lang))
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>{escape(text["catalysts"])}</h3>
            <p>{escape(text["catalysts_desc"])}</p>
            <ul class="clean-list">{items}</ul>
        </section>
        """
    )


def render_risk_signals(industry: dict, lang: str) -> None:
    """Render trend risk signals."""

    text = TEXT[lang]
    items = "".join(f"<li>{escape(item)}</li>" for item in list_text(industry, "riskSignals", lang))
    _render_html(
        f"""
        <section class="industry-panel">
            <h3>{escape(text["risk_signals"])}</h3>
            <p>{escape(text["risk_desc"])}</p>
            <ul class="clean-list">{items}</ul>
        </section>
        """
    )


def render_labeled_row(name: str, status: str, explanation: str, lang: str) -> str:
    """Return a compact driver row."""

    color = STATUS_COLORS.get(status, "#CBD5E1")
    return f"""
        <div class="driver-row">
            <div>
                <strong>{escape(name)}</strong>
                <p>{escape(explanation)}</p>
            </div>
            <span style="border-color:{color}; color:{color};">{escape(translate_status(status, lang))}</span>
        </div>
        """


def render_available_universe(lang: str) -> None:
    """Render the built-in mock universe."""

    text = TEXT[lang]
    with st.expander(text["universe"], expanded=False):
        for category, items in INDUSTRY_CATEGORIES.items():
            labels = "、".join(item[2] for item in items) if lang == "zh" else ", ".join(item[1] for item in items)
            title = CATEGORY_LABELS[lang].get(category, category)
            st.markdown(f"**{title}**: {labels}")


def render_recognition_result(industry: dict, matched: bool, lang: str) -> None:
    """Render neutral search recognition feedback."""

    text = TEXT[lang]
    if not matched:
        _render_html(
            f"""
            <div class="recognition-panel recognition-fallback">
                <strong>{escape(text["fallback_title"])}</strong>
                <span>{escape(text["fallback_body"])}</span>
            </div>
            """
        )
        return
    _render_html(
        f"""
        <div class="recognition-panel">
            <div><strong>{escape(text["recognition"])}：</strong>{escape(industry_name(industry, lang))}</div>
            <div><strong>{escape(text["category"])}：</strong>{escape(industry_category_path(industry, lang))}</div>
        </div>
        """
    )


def build_trend_summary(industry: dict, lang: str) -> str:
    """Build a neutral summary when mock data does not provide one."""

    summary = get_localized(industry, "summary", lang, default="")
    if summary:
        return summary
    status = translate_status(industry.get("status", "Diverging"), lang)
    stage = trend_stage_text(industry, lang)
    score = industry.get("trendScore", 0)
    market = industry.get("marketConfirmation", 0)
    validation = industry.get("fundamentalValidation", 0)
    pressure = industry.get("valuationPressure", 0)
    if lang == "en":
        return (
            f"The mock framework classifies this industry as {status}, with trend stage {stage}. "
            f"Trend score is {score:.1f}, market confirmation is {market:.1f}, validation is {validation:.1f}, "
            f"and valuation pressure is {pressure:.1f}. This is a neutral trend framework."
        )
    return (
        f"当前 mock 框架将该行业识别为“{status}”，趋势阶段为 {stage}。"
        f"趋势评分 {score:.1f}，市场确认 {market:.1f}，基本验证 {validation:.1f}，"
        f"估值压力 {pressure:.1f}；整体用于趋势研究观察，不包含交易动作判断。"
    )


def framework_explanation(kind: str, lang: str) -> str:
    """Return framework score explanation."""

    zh = {
        "trend": "综合观察市场确认、热度、基本验证与风险信号后的趋势质量。",
        "market": "观察价格趋势、代表性标的表现和行业内部一致性。",
        "validation": "观察需求、利润率、产能利用率和政策线索是否支持趋势。",
        "valuation": "观察预期水平与趋势验证强度之间是否存在压力。",
        "macro": "观察利率、汇率、商品价格、政策周期和全球需求的影响。",
        "heat": "观察行业关注度、拥挤度和短期叙事密度。",
    }
    en = {
        "trend": "Composite trend quality from confirmation, heat, validation, and risk signals.",
        "market": "Observes price trend, representative securities, and internal consistency.",
        "validation": "Observes whether demand, margins, utilization, and policy clues support the trend.",
        "valuation": "Observes expectation pressure relative to trend validation.",
        "macro": "Observes rates, currency, commodity prices, policy cycle, and global demand exposure.",
        "heat": "Observes attention level, crowding, and short-term narrative density.",
    }
    return (zh if lang == "zh" else en)[kind]


def get_localized(record: dict, field: str, lang: str, default: str | None = None) -> str:
    """Return localized text, preferring the active language before falling back."""

    if lang == "zh":
        value = record.get(f"{field}Zh")
        if value:
            return str(value)
        value = record.get(field)
        if value:
            return str(value)
        return "" if default is None else str(default)
    value = record.get(field)
    if value:
        return str(value)
    value = record.get(field, default if default is not None else "")
    return "" if value is None else str(value)


def item_text(record: dict, field: str, lang: str) -> str:
    """Return localized nested item text with fallback."""

    if lang == "zh" and record.get(f"{field}Zh"):
        return str(record[f"{field}Zh"])
    return str(record.get(field, ""))


def list_text(industry: dict, field: str, lang: str) -> list[str]:
    """Return localized list text with fallback."""

    if lang == "zh" and industry.get(f"{field}Zh"):
        return list(industry[f"{field}Zh"])
    return list(industry.get(field, []))


def industry_chain(industry: dict, lang: str) -> dict:
    """Return localized industry chain with fallback."""

    if lang == "zh" and industry.get("industryChainZh"):
        return industry["industryChainZh"]
    return industry.get("industryChain", {})


def industry_name(industry: dict, lang: str) -> str:
    """Return localized industry display name."""

    return str(industry.get("chineseName") if lang == "zh" else industry.get("name"))


def industry_title_html(industry: dict, lang: str) -> str:
    """Return localized industry title markup."""

    if lang == "zh":
        subtitle = f'<div class="industry-title-sub">{escape(industry.get("name", ""))}</div>'
        return f'{escape(industry_name(industry, lang))}{subtitle}'
    return escape(industry_name(industry, lang))


def trend_stage_text(industry: dict, lang: str) -> str:
    """Return localized trend stage."""

    if lang == "zh":
        if industry.get("trendStageZh"):
            return str(industry["trendStageZh"])
        return TREND_STAGE_LABELS_ZH.get(str(industry.get("trendStage", "")), str(industry.get("trendStage", "")))
    return str(industry.get("trendStage", ""))


def translate_status(status: str, lang: str) -> str:
    """Translate status labels for display."""

    return STATUS_LABELS[lang].get(str(status), str(status))


def trend_status_info(status: str, lang: str) -> dict[str, str]:
    """Return localized status explanation."""

    return TREND_STATUS_EXPLANATIONS[lang].get(
        status,
        {
            "label": translate_status(status, lang),
            "bias": "N/A",
            "explanation": "N/A",
        },
    )


def trend_stage_info(stage: str, lang: str) -> dict[str, str]:
    """Return localized stage explanation."""

    label = trend_stage_text({"trendStage": stage}, lang)
    return TREND_STAGE_EXPLANATIONS[lang].get(stage, {"label": label, "explanation": "N/A"})


def render_trend_status_guide(lang: str, wrap: bool = True) -> None:
    """Render a compact trend status guide table."""

    headings = {
        "zh": ("趋势状态说明", "状态", "倾向", "解释"),
        "en": ("Trend Status Guide", "Status", "Bias", "Explanation"),
    }
    title, status_col, bias_col, explanation_col = headings[lang]
    rows = [
        {
            status_col: info["label"],
            bias_col: info["bias"],
            explanation_col: info["explanation"],
        }
        for info in TREND_STATUS_EXPLANATIONS[lang].values()
    ]
    if wrap:
        with st.expander(title, expanded=False):
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        return
    st.markdown(f"**{title}**")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_trend_stage_guide(lang: str, current_stage: str | None = None, wrap: bool = True) -> None:
    """Render the full 1-6 trend lifecycle guide."""

    headings = {
        "zh": ("趋势阶段说明", "阶段", "名称", "含义", "当前阶段"),
        "en": ("Trend Stage Guide", "Stage", "Name", "Meaning", "Current Stage"),
    }
    title, stage_col, name_col, meaning_col, current_label = headings[lang]
    rows = []
    for item in TREND_STAGE_GUIDE[lang]:
        is_current = bool(current_stage and item["key"] == current_stage)
        rows.append(
            {
                stage_col: f"{item['stage']} · {current_label}" if is_current else item["stage"],
                name_col: item["name"],
                meaning_col: item["meaning"],
            }
        )
    if wrap:
        with st.expander(title, expanded=False):
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        return
    st.markdown(f"**{title}**")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def category_label(industry: dict, lang: str) -> str:
    """Return localized category label with a theme-specific refinement."""

    if lang == "zh" and industry.get("categoryZh"):
        return str(industry["categoryZh"])
    if lang == "zh" and industry.get("id") == "gold":
        return "贵金属"
    if lang == "en" and industry.get("id") == "gold":
        return "Precious Metals"
    return CATEGORY_LABELS[lang].get(str(industry.get("category", "")), str(industry.get("category", "")))


def industry_category_path(industry: dict, lang: str) -> str:
    """Return localized category path shown in page headers."""

    if lang == "zh":
        if industry.get("id") == "gold":
            return f"{CATEGORY_LABELS[lang].get(str(industry.get('category', '')), str(industry.get('category', '')))} / 贵金属 / {industry_name(industry, lang)}"
        return f"{category_label(industry, lang)} / {industry_name(industry, lang)}"
    if industry.get("id") == "gold":
        return f"{industry.get('category', '')} / Precious Metals / {industry_name(industry, lang)}"
    return f"{industry.get('category', '')} / {industry_name(industry, lang)}"


def sample_type_label(value: object, lang: str) -> str:
    """Return localized sample type label."""

    text = TEXT[lang]
    mapping = {
        "ETF": text["sample_etf"],
        "Leader": text["sample_leader"],
        "Benchmark": text["sample_benchmark"],
    }
    return mapping.get(str(value), str(value or "N/A"))


def failure_reason_label(reason: object, lang: str) -> str:
    """Return localized failed-download reason."""

    raw = str(reason or "")
    if raw == "yahoo_no_price_data":
        return "Yahoo Finance returned no price data" if lang == "en" else "Yahoo Finance 暂时未返回价格数据"
    if lang == "en":
        return raw
    mapping = {
        "empty data": "无可用数据",
        "missing close": "缺少收盘价",
        "insufficient history": "历史数据不足",
        "metric calculation failed": "指标计算失败",
    }
    return mapping.get(raw, raw)


def format_score(value: object) -> str:
    """Format a 0-10 score."""

    if value is None:
        return "N/A"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "N/A"


def format_datetime_compact(value: object, lang: str = "zh") -> str:
    """Format ISO-like timestamps for compact UI display."""

    if not value:
        return "N/A" if lang == "en" else "暂无"
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(parsed):
        return "N/A" if lang == "en" else "暂无"
    try:
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(value)


def render_compact_info_items(items: list[tuple[str, object]], columns: int = 2) -> None:
    """Render small informational fields without large Streamlit metrics."""

    if not items:
        return
    column_count = max(1, min(columns, len(items)))
    cols = st.columns(column_count)
    for index, (label, value) in enumerate(items):
        with cols[index % column_count]:
            st.caption(f"**{label}**: {value}")


def format_ratio_with_count(result: dict, key: str) -> str:
    """Format a ratio as a percentage with numerator and denominator."""

    ratio = result.get(f"{key}_ratio")
    count = result.get(f"{key}_count", 0)
    total = result.get(f"{key}_total", 0)
    if ratio is None or not total:
        return "N/A"
    return f"{format_percent(ratio)} ({count}/{total})"


def format_price(value: object) -> str:
    """Format a price value."""

    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def format_percent(value: object) -> str:
    """Format a decimal return or ratio as a percentage."""

    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_bool(value: object, lang: str) -> str:
    """Format boolean flags for table display."""

    if value is None:
        return "N/A"
    return TEXT[lang]["yes"] if bool(value) else "—"


def escape(value: object) -> str:
    """Escape text for local HTML snippets."""

    return html.escape(str(value))


def _render_html(markup: str) -> None:
    """Render trusted local HTML for this Streamlit page."""

    st.markdown(markup, unsafe_allow_html=True)


def _apply_industry_css() -> None:
    """Apply page-scoped dashboard styling."""

    _render_html(
        """
        <style>
        .block-container {
            padding-top: 2.5rem;
        }
        div[data-testid="stTextInput"] input {
            border-color: rgba(148, 163, 184, 0.35) !important;
            box-shadow: none !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: rgba(56, 189, 248, 0.7) !important;
            box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.25) !important;
        }
        .industry-hero {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 16px;
            padding: 20px 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(15, 23, 42, 0.72);
            border-radius: 8px;
        }
        .industry-hero h1 {
            margin: 0;
            font-size: 30px;
            line-height: 1.2;
        }
        .industry-hero p {
            margin: 6px 0 0;
            color: #CBD5E1;
        }
        .industry-version {
            color: #38BDF8;
            border: 1px solid rgba(56, 189, 248, 0.42);
            border-radius: 999px;
            padding: 6px 10px;
            white-space: nowrap;
            font-size: 13px;
        }
        .industry-panel {
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.58);
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
        }
        .industry-panel h2, .industry-panel h3, .industry-panel h4 {
            margin-top: 0;
        }
        .industry-panel p, .driver-row p {
            color: #CBD5E1;
            line-height: 1.5;
        }
        .industry-kicker {
            color: #94A3B8;
            font-size: 13px;
            margin-bottom: 6px;
        }
        .industry-title-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
        }
        .industry-title-sub {
            color: #94A3B8;
            font-size: 14px;
            font-weight: 500;
            margin-top: 4px;
        }
        .industry-badge, .driver-row span {
            border: 1px solid;
            border-radius: 999px;
            padding: 5px 9px;
            font-size: 12px;
            white-space: nowrap;
            background: rgba(15, 23, 42, 0.72);
        }
        .summary-box, .stage-box {
            margin-top: 12px;
            padding: 12px;
            background: rgba(15, 23, 42, 0.52);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 6px;
        }
        .stage-box {
            background: rgba(30, 41, 59, 0.72);
            border-left: 3px solid #38BDF8;
        }
        .stage-label {
            color: #94A3B8;
            font-size: 12px;
        }
        .stage-value {
            color: #F8FAFC;
            font-size: 18px;
            font-weight: 700;
            margin: 3px 0;
        }
        .stage-note, .summary-text {
            color: #CBD5E1;
            line-height: 1.55;
            margin-top: 4px;
        }
        .recognition-panel, .market-meta-strip {
            margin: 10px 0 12px;
            padding: 10px 12px;
            border: 1px solid rgba(56, 189, 248, 0.28);
            background: rgba(15, 23, 42, 0.48);
            border-radius: 8px;
            color: #E5E7EB;
            font-size: 14px;
            line-height: 1.55;
        }
        .recognition-panel {
            display: grid;
            gap: 4px;
        }
        .recognition-panel strong {
            color: #F8FAFC;
        }
        .recognition-fallback {
            border-color: rgba(251, 191, 36, 0.42);
            background: rgba(113, 63, 18, 0.18);
        }
        .market-meta-strip span {
            color: #94A3B8;
        }
        .driver-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 0;
            border-top: 1px solid rgba(148, 163, 184, 0.16);
        }
        .driver-row:first-of-type {
            border-top: 0;
        }
        .driver-row p {
            margin: 4px 0 0;
        }
        .chip-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .theme-chip {
            display: inline-flex;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: rgba(30, 41, 59, 0.78);
            color: #E5E7EB;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 13px;
        }
        .chain-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }
        .chain-column {
            background: rgba(30, 41, 59, 0.62);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            padding: 12px;
        }
        .chain-column ul, .clean-list {
            margin-bottom: 0;
            padding-left: 18px;
        }
        @media (max-width: 900px) {
            .chain-grid {
                grid-template-columns: 1fr;
            }
            .industry-hero, .industry-title-row, .driver-row {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        </style>
        """
    )
