"""Drop-in Streamlit multi-alpha strategy research page.
Place under the root `pages/` directory of Clayton Alpha Dashboard.
"""
from __future__ import annotations
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.multi_alpha_strategy import StrategyConfig, backtest, yahoo_download, validate_ohlc

st.set_page_config(page_title="Multi-Alpha Strategy Lab", page_icon="🧪", layout="wide")
st.title("多策略研究实验室 / Multi-Alpha Strategy Lab")
st.warning("历史 ETF 模拟，非投资建议。原文 QuantConnect 业绩未复现；期权 Collar 仅为触发信号，不计入收益。")
st.caption("Research prototype · Copula GDX/GLD + HMM market regime + QQQ momentum · No live trading")
st.warning(
    "This module is NOT the source report's QuantConnect implementation. "
    "The protective options collar is an activation signal only; option trades, bid/ask, "
    "Greeks, expiry, assignment, and option P&L are NOT modeled. "
    "Results below are independent ETF-only simulations, not verified strategy returns."
)

with st.expander("Source-paper reported results (reference, not reproduced)", expanded=False):
    a,b,c,d = st.columns(4)
    a.metric("Paper's reported CAGR", "20.64%")
    b.metric("Paper's reported max drawdown", "15.40%")
    c.metric("Paper's reported Sharpe", "0.89")
    d.metric("Paper's reported orders", "619")
    st.caption("Math 585, Team 4, pp. 19 & 23–24. Original QuantConnect report is a separate external backtest. "
               "Please retain attribution to Zhengwei Tong, Haiwei Du, Patrick Zhu, and Isaac Vergara.")

st.subheader("1. Data & assumptions")
source = st.radio("Market data", ["Yahoo Finance (adjusted OHLC)", "Upload OHLC CSV"], horizontal=True)
with st.expander("CSV schema", expanded=False):
    st.code("date,symbol,high,low,close\n2025-01-02,SPY,600,590,595\n...", language="csv")
    st.write("Required symbols: SPY, QQQ, SHV, GDX, GLD. Common trading dates only; no forward filling.")

c1,c2,c3 = st.columns(3)
start_day = c1.date_input("Backtest start", value=date(2020, 1, 1), min_value=date(2010, 1, 1))
end_day = c2.date_input("Backtest end", value=date.today())
method = c3.selectbox("Risk-state model", ["HMM (causal filtered)", "Volatility baseline"])

with st.expander("Strategy parameters", expanded=False):
    ca,cb,cc,cd = st.columns(4)
    pair_weight = ca.slider("Pair: abs weight per leg", .05, .50, .50, .05)
    momentum_weight = cb.slider("QQQ/SHV sleeve weight", .1, .75, .75, .05)
    gross_cap = cc.slider("Gross exposure cap", 0.5, 1.75, 1.0, .05)
    fees = cd.slider("Trading cost (bps / traded notional)", 0, 100, 10, 5)
    st.caption("Paper uses +/-0.50 for each pair leg and up to 0.75 momentum; combined gross "
               "exposure can reach 1.75. This page caps it at 1.00 by default.")

cfg = StrategyConfig(
    pair_leg_weight=pair_weight, momentum_weight=momentum_weight, gross_cap=gross_cap,
    charge_bps=float(fees), regime_method="hmm" if method.startswith("HMM") else "volatility",
)

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo(start, end):
    return yahoo_download(start, end)

run = False
if source.startswith("Upload"):
    uploaded = st.file_uploader("Upload long-form OHLC CSV", type="csv")
    if uploaded is not None:
        run = st.button("Run independent backtest", type="primary")
else:
    uploaded = None
    run = st.button("Fetch data & run independent backtest", type="primary")

if run:
    st.session_state.pop("multi_alpha_result", None)
    try:
        if end_day < start_day:
            raise ValueError("结束日期不得早于开始日期")
        with st.spinner("Computing point-in-time signals, risk regimes and strategy results..."):
            if uploaded is not None:
                prices = validate_ohlc(pd.read_csv(uploaded))
            else:
                # 4+ years warm-up for HMM and copula. Start output at chosen date.
                fetch_start = (start_day - timedelta(days=1600)).isoformat()
                prices = get_yahoo(fetch_start, (end_day + timedelta(days=1)).isoformat())
            prices = prices.loc[:pd.Timestamp(end_day)]
            result = backtest(prices, cfg, start=start_day.isoformat())
            st.session_state["multi_alpha_result"] = result
            st.session_state["multi_alpha_source"] = source
    except Exception as e:
        st.error(f"Could not finish the backtest: {e}")

if "multi_alpha_result" in st.session_state:
    r = st.session_state["multi_alpha_result"]
    df = r["daily"]
    m = r["metrics"]
    st.caption(f"已计算数据来源：{st.session_state.get('multi_alpha_source')}；区间：{df.index.min().date()} 至 {df.index.max().date()}。参数修改后请重新运行。")
    st.subheader("2. Independent ETF-only backtest")
    a,b,c,d = st.columns(4)
    a.metric("CAGR (simulation)", f"{m['cagr']:.2%}")
    b.metric("Maximum drawdown", f"{m['max_drawdown']:.2%}")
    c.metric("Sharpe (0% RF)", f"{m['sharpe']:.2f}")
    d.metric("Annualized volatility", f"{m['volatility']:.2%}")
    st.line_chart(df[["portfolio_equity", "qqq_buyhold"]].rename(columns={"portfolio_equity":"Multi-alpha (excl. options)", "qqq_buyhold":"QQQ buy & hold"}))
    st.caption("Signals from close[t] are applied to returns[t+1]. Trading/borrow costs are illustrative. "
               "QQQ benchmark is buy-and-hold, while the source report used other benchmark definitions.")

    st.subheader("3. Explainable signals")
    a,b,c = st.columns(3)
    a.metric("HMM-model coverage", f"{m['hmm_fraction']:.1%}")
    b.metric("Collar-trigger days*", str(m["collar_trigger_days"]))
    c.metric("Estimated annual turnover", f"{m['annualized_turnover']:.1f}x")
    st.caption("*Signal only, NOT executed option orders. If HMM cannot fit, the system labels and uses a volatility-baseline fallback.")
    st.line_chart(df[["mi", "crisis_probability"]].rename(columns={"mi":"Clayton MI (GDX|GLD)", "crisis_probability":"Stress probability"}))
    st.line_chart(df[["var95", "cvar95", "var99", "cvar99"]], y_label="fraction of portfolio equity")
    fields = ["mi", "kendall_tau", "high_vol", "regime_source", "pair_direction", "momentum_on", "sma200", "roc120", "adx14", "collar_trigger_only", "weight_GDX", "weight_GLD", "weight_QQQ", "weight_SHV"]
    st.dataframe(df[fields].tail(20).sort_index(ascending=False), use_container_width=True)
    st.download_button("Download daily audit & signals CSV", df.to_csv().encode("utf-8-sig"), file_name="multi_alpha_audit.csv", mime="text/csv")

st.divider()
st.caption("Paper strategy: GDX/GLD Clayton copula (252-day rolling Kendall tau, MI 0.05/0.95); "
           "two-state SPY HMM and 2-day confirmation; QQQ SMA200/ROC120/ADX14, else SHV; "
           "high-volatility collar signal. Original report authors: Tong, Du, Zhu & Vergara. "
           "This tool is for research/education and not an investment recommendation.")
