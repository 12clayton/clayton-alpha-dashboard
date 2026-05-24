"""Local Streamlit dashboard for Global QDII risk monitoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.data_fetcher import fetch_price_data
from src.indicators import build_indicator_table
from src.risk_model import classify_asset_risk, summarize_market_regime


# 项目路径集中放在顶部，后续接 API 或调整文件位置时更容易维护。
ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config" / "assets.yaml"
HOLDINGS_PATH = ROOT_DIR / "holdings.csv"
PORTFOLIO_PATH = ROOT_DIR / "portfolio.csv"
QDII_PREMIUM_PATH = ROOT_DIR / "config" / "qdii_premium.csv"
PRICE_CACHE_PATH = ROOT_DIR / "data" / "price_cache.csv"


st.set_page_config(
    page_title="Global QDII Risk Monitor",
    layout="wide",
)


def main() -> None:
    """Render the full dashboard."""

    # 载入基础配置、行情和风险表；所有页面共享同一份数据。
    config = load_config()
    assets = config["assets"]
    risk_rules = config.get("risk_rules", {})
    prices, data_quality = load_prices(assets)
    risk_table = build_risk_table(prices, data_quality, risk_rules)
    market_regime, market_reason = summarize_market_regime(risk_table)

    # 顶部区域展示项目名称和总体状态，让用户一打开就知道今天环境。
    st.title("Global QDII Risk Monitor")
    st.caption("本地投资研究仪表盘，只输出观察和风险提示，不执行自动交易。")
    render_top_metrics(risk_table, market_regime, market_reason)

    tabs = st.tabs(
        [
            "全球市场总览",
            "我的持仓",
            "QDII溢价",
            "行业趋势雷达",
            "黄金/美元/美债/BTC联动",
            "风险等级",
            "每日操作建议",
        ]
    )

    # 每个标签页只负责一个观察问题，避免一个页面塞太多信息。
    with tabs[0]:
        render_global_overview(prices, risk_table, assets)

    with tabs[1]:
        render_holdings(prices, risk_table)

    with tabs[2]:
        render_qdii_premium()

    with tabs[3]:
        render_industry_radar(risk_table, assets)

    with tabs[4]:
        render_cross_asset_linkage(prices)

    with tabs[5]:
        render_risk_levels(risk_table, market_regime, market_reason)

    with tabs[6]:
        render_daily_advice(risk_table, market_regime)


@st.cache_data(ttl=60 * 30)
def load_config() -> dict:
    """Load asset configuration from YAML."""

    # 使用 YAML 管理资产清单，后续新增基金或指数不需要改代码。
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


@st.cache_data(ttl=60 * 30)
def load_prices(assets: list[dict]) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load prices from yfinance first, then local CSV cache."""

    # 数据层沿用 src/data_fetcher.py 的逻辑：线上优先，缓存兜底。
    return fetch_price_data(
        assets=assets,
        period="1y",
        cache_path=PRICE_CACHE_PATH,
    )


def build_risk_table(
    prices: pd.DataFrame,
    data_quality: dict[str, str],
    risk_rules: dict,
) -> pd.DataFrame:
    """Build the dashboard risk table."""

    # 先计算技术指标，再把数据质量纳入风险判断。
    indicator_table = build_indicator_table(
        prices=prices,
        short_window=risk_rules.get("short_ma_window", 20),
        long_window=risk_rules.get("long_ma_window", 60),
        rsi_window=risk_rules.get("rsi_window", 14),
    )
    return classify_asset_risk(indicator_table, data_quality, risk_rules)


def render_top_metrics(risk_table: pd.DataFrame, market_regime: str, market_reason: str) -> None:
    """Render headline metrics."""

    # 用几个紧凑指标显示整体风险、强弱资产数量和数据新鲜度。
    fresh_count = int((risk_table["data_quality"] == "fresh").sum())
    risk_on_count = int((risk_table["risk_regime"] == "risk-on").sum())
    risk_off_count = int((risk_table["risk_regime"] == "risk-off").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总体风险状态", market_regime)
    col2.metric("Risk-on 数量", risk_on_count)
    col3.metric("Risk-off 数量", risk_off_count)
    col4.metric("新鲜数据", f"{fresh_count}/{len(risk_table)}")
    st.info(market_reason)


def render_global_overview(
    prices: pd.DataFrame,
    risk_table: pd.DataFrame,
    assets: list[dict],
) -> None:
    """Render the global market overview page."""

    st.subheader("全球市场总览")

    # 价格曲线默认展示所有资产的归一化走势，便于比较不同价格单位的资产。
    normalized = normalize_prices(prices)
    st.line_chart(normalized, height=360)

    asset_map = {asset["symbol"]: asset for asset in assets}
    overview = risk_table.copy()
    overview["资产"] = overview["symbol"].map(lambda x: asset_map.get(x, {}).get("name", x))
    overview["主题"] = overview["symbol"].map(lambda x: asset_map.get(x, {}).get("theme", ""))
    overview["日涨跌"] = overview["daily_return"].map(format_percent)
    overview["当前回撤"] = overview["latest_drawdown"].map(format_percent)
    overview["RSI"] = overview["rsi"].map(format_number)

    # 表格保留核心字段，适合日常快速扫描。
    st.dataframe(
        overview[
            [
                "资产",
                "symbol",
                "主题",
                "last_date",
                "last_price",
                "日涨跌",
                "RSI",
                "当前回撤",
                "data_quality",
                "risk_regime",
                "risk_reason",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_holdings(prices: pd.DataFrame, risk_table: pd.DataFrame) -> None:
    """Render the holdings page."""

    st.subheader("我的持仓")

    # 优先读取实际持仓文件；如果没有，就读取组合权重文件作为备选。
    holdings = read_csv_if_exists(HOLDINGS_PATH)
    if holdings.empty:
        holdings = read_csv_if_exists(PORTFOLIO_PATH)

    if holdings.empty:
        st.warning("未找到 holdings.csv 或 portfolio.csv。")
        return

    # 为持仓补充代理资产的最新风险状态。
    risk_lookup = risk_table.set_index("symbol")[["risk_regime", "risk_reason", "daily_return"]]
    proxy_column = "proxy" if "proxy" in holdings.columns else None
    if proxy_column:
        holdings = holdings.join(risk_lookup, on=proxy_column)

    # 如果有 amount 字段，用金额聚合；否则使用 weight 字段展示权重。
    value_column = "amount" if "amount" in holdings.columns else "weight"
    if value_column in holdings.columns and "category" in holdings.columns:
        category_view = holdings.groupby("category", as_index=False)[value_column].sum()
        fig = px.pie(category_view, names="category", values=value_column, hole=0.45)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(holdings, use_container_width=True, hide_index=True)


def render_qdii_premium() -> None:
    """Render the QDII premium page."""

    st.subheader("QDII溢价")

    # QDII 溢价先用 CSV 管理，后续可替换为基金估值或交易所行情 API。
    premium = read_csv_if_exists(QDII_PREMIUM_PATH)
    if premium.empty:
        st.warning("未找到 config/qdii_premium.csv。")
        return

    premium["premium_pct"] = pd.to_numeric(premium["premium_pct"], errors="coerce")
    premium["溢价状态"] = premium["premium_pct"].map(classify_premium)

    col1, col2 = st.columns([1, 2])
    with col1:
        high_premium = int((premium["premium_pct"] > 3).sum())
        st.metric("高溢价数量", high_premium)
        st.caption("溢价超过 3% 时，申购或买入成本需要额外留意。")
    with col2:
        fig = px.bar(
            premium,
            x="fund",
            y="premium_pct",
            color="溢价状态",
            labels={"premium_pct": "溢价率(%)", "fund": "基金"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(premium, use_container_width=True, hide_index=True)


def render_industry_radar(risk_table: pd.DataFrame, assets: list[dict]) -> None:
    """Render the industry trend radar page."""

    st.subheader("行业趋势雷达")

    # 以主题为维度聚合趋势分数，用雷达图观察强弱结构。
    asset_map = {asset["symbol"]: asset for asset in assets}
    radar = risk_table.copy()
    radar["theme"] = radar["symbol"].map(lambda x: asset_map.get(x, {}).get("theme", x))
    radar["trend_score"] = radar.apply(calculate_trend_score, axis=1)
    radar_view = radar.groupby("theme", as_index=False)["trend_score"].mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=radar_view["trend_score"],
            theta=radar_view["theme"],
            fill="toself",
            name="趋势强度",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(radar_view.sort_values("trend_score", ascending=False), hide_index=True)


def render_cross_asset_linkage(prices: pd.DataFrame) -> None:
    """Render gold, dollar, treasury, and BTC linkage page."""

    st.subheader("黄金/美元/美债/BTC联动")

    # 选取避险和流动性相关资产，观察近 90 日归一化走势和相关性。
    linkage_symbols = [symbol for symbol in ["GLD", "UUP", "TLT", "BTC-USD"] if symbol in prices.columns]
    if not linkage_symbols:
        st.warning("缺少 GLD、UUP、TLT 或 BTC-USD 数据。")
        return

    linkage_prices = prices[linkage_symbols].dropna(how="all").tail(90)
    st.line_chart(normalize_prices(linkage_prices), height=340)

    returns = linkage_prices.pct_change().dropna(how="all")
    if not returns.empty:
        correlation = returns.corr()
        fig = px.imshow(
            correlation,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
        )
        st.plotly_chart(fig, use_container_width=True)


def render_risk_levels(risk_table: pd.DataFrame, market_regime: str, market_reason: str) -> None:
    """Render the risk level page."""

    st.subheader("风险等级")

    # 把文字状态转为分数，方便在柱状图里比较。
    score_map = {"risk-on": 30, "neutral": 60, "risk-off": 85}
    risk_view = risk_table.copy()
    risk_view["risk_score"] = risk_view["risk_regime"].map(score_map).fillna(60)

    fig = px.bar(
        risk_view.sort_values("risk_score", ascending=False),
        x="symbol",
        y="risk_score",
        color="risk_regime",
        labels={"risk_score": "风险分数", "symbol": "资产代码"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**总体状态：** {market_regime}")
    st.write(market_reason)
    st.dataframe(
        risk_view[["symbol", "risk_regime", "risk_score", "data_quality", "risk_reason"]],
        use_container_width=True,
        hide_index=True,
    )


def render_daily_advice(risk_table: pd.DataFrame, market_regime: str) -> None:
    """Render daily operation advice page."""

    st.subheader("每日操作建议")

    # 建议只写观察动作，不写自动交易或强制买卖指令。
    advice_items = build_daily_advice(risk_table, market_regime)
    for title, body in advice_items:
        st.markdown(f"**{title}**")
        st.write(body)

    st.divider()
    st.caption("以上内容仅为研究观察和风险提示，不构成投资建议，也不会触发自动交易。")


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    """Read a CSV file if it exists."""

    # CSV 读取失败时返回空表，让页面显示友好提示。
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Normalize prices to 100 at the first valid point."""

    # 归一化能把股票、债券、黄金和 BTC 放在同一张图里比较。
    clean_prices = prices.dropna(how="all")
    if clean_prices.empty:
        return clean_prices

    first_valid = clean_prices.apply(lambda column: column.dropna().iloc[0] if not column.dropna().empty else pd.NA)
    return clean_prices.divide(first_valid).multiply(100)


def calculate_trend_score(row: pd.Series) -> float:
    """Calculate a 0-100 trend score for radar charts."""

    # 分数由趋势、RSI 和回撤共同构成，越高代表趋势越强。
    score = 50.0

    if not pd.isna(row.get("last_price")) and not pd.isna(row.get("long_ma")):
        score += 20 if row["last_price"] > row["long_ma"] else -20

    if not pd.isna(row.get("short_ma")) and not pd.isna(row.get("long_ma")):
        score += 15 if row["short_ma"] > row["long_ma"] else -15

    if not pd.isna(row.get("rsi")):
        score += min(max((row["rsi"] - 50) * 0.6, -15), 15)

    if not pd.isna(row.get("latest_drawdown")):
        score += max(row["latest_drawdown"] * 100, -20)

    return float(min(max(score, 0), 100))


def classify_premium(premium_pct: float) -> str:
    """Classify QDII premium level."""

    # 溢价分层只作为成本提示，不作为交易信号。
    if pd.isna(premium_pct):
        return "缺少数据"
    if premium_pct >= 3:
        return "高溢价"
    if premium_pct <= -1:
        return "折价"
    return "正常"


def build_daily_advice(risk_table: pd.DataFrame, market_regime: str) -> list[tuple[str, str]]:
    """Build research-only daily advice."""

    # 总体环境决定今天观察的主语气。
    if market_regime == "risk-off":
        overview = "市场偏防守，优先检查高波动资产和 QDII 溢价，不急于提高风险暴露。"
    elif market_regime == "risk-on":
        overview = "市场风险偏好较好，可继续观察趋势资产是否保持在长期均线上方。"
    else:
        overview = "市场信号混合，今天更适合做仓位复盘和风险观察。"

    stale_count = int((risk_table["data_quality"] != "fresh").sum())
    risk_off_assets = risk_table.loc[risk_table["risk_regime"] == "risk-off", "symbol"].tolist()
    overheated_assets = risk_table.loc[risk_table["rsi"] >= 70, "symbol"].tolist()

    # 每条建议都避免写成自动下单指令，只保留人工观察动作。
    items = [
        ("总体观察", overview),
        (
            "数据质量",
            f"当前有 {stale_count} 个资产不是 fresh 数据；这些资产的结论应降低权重。"
            if stale_count
            else "当前核心行情数据为 fresh，可正常参考仪表盘结论。",
        ),
        (
            "重点风险",
            "、".join(risk_off_assets) + " 处于 risk-off，建议重点复盘回撤和持仓占比。"
            if risk_off_assets
            else "暂未发现明确 risk-off 资产，继续观察趋势能否延续。",
        ),
        (
            "短线过热",
            "、".join(overheated_assets) + " RSI 偏高，适合关注波动放大风险。"
            if overheated_assets
            else "暂未发现 RSI 明显过热资产。",
        ),
    ]
    return items


def format_number(value) -> str:
    """Format a number for display."""

    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2f}"


def format_percent(value) -> str:
    """Format a decimal as a percentage."""

    if pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:.2f}%"


if __name__ == "__main__":
    main()
