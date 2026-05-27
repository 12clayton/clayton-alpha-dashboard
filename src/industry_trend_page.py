"""Streamlit page for the Industry Trend Search Engine."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.industry_market_data import get_market_confirmation_data
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


def render_industry_trend_search_page() -> None:
    """Render the industry trend search page."""

    _apply_industry_css()
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

    render_industry_overview(industry, lang)
    render_score_grid(industry, lang)
    render_live_market_confirmation(industry, lang)

    left, right = st.columns([1.35, 1])
    with left:
        render_key_drivers(industry, lang)
        render_industry_chain(industry, lang)
    with right:
        render_subsectors(industry, lang)
        render_catalysts(industry, lang)
        render_risk_signals(industry, lang)

    render_available_universe(lang)


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


def render_live_market_confirmation(industry: dict, lang: str) -> None:
    """Render live price-based market confirmation data."""

    text = TEXT[lang]
    st.markdown(f"### {text['live_title']}")
    st.markdown(text["live_intro"])
    st.caption(text["price_score_note"])

    if st.button(text["refresh_market_data"], key=f"refresh_market_data_{industry.get('id', 'unknown')}"):
        get_market_confirmation_data.clear()

    result = get_market_confirmation_data(industry.get("id", ""))
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

    render_market_meta_strip(result, lang)
    render_failure_reasons(result, lang)
    render_live_market_metrics(industry, result, lang)

    details = result.get("details") or []
    if details:
        st.dataframe(build_market_detail_table(details, lang), use_container_width=True, hide_index=True)
        with st.expander(text["audit_title"], expanded=False):
            st.dataframe(build_market_audit_table(details, lang), use_container_width=True, hide_index=True)


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
        }
        for item in failures
    ]
    with st.expander(text["failure_reasons"], expanded=False):
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
