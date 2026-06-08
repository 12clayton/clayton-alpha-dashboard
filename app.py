"""Streamlit website for viewing the latest daily risk report."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import html
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import yaml

from src.news_digest import analyze_manual_news, save_manual_news_note
from src.daily_tactical_engine import TacticalInputs, daily_tactical_engine
from src.fund_nav_provider import get_latest_fund_navs_for_funds, normalize_fund_code
from src.gold_defense_engine import evaluate_gold_defense
from src.public_data_loader import (
    PUBLIC_TICKERS,
    build_public_asset_table,
    infer_public_market_status,
    load_public_ohlc_data,
    load_public_market_snapshot,
)
from src.public_news_loader import load_public_news
from src.data_quality import (
    classify_market_data_quality as dq_market_quality,
    classify_fund_nav_quality as dq_fund_nav_quality,
    classify_news_quality as dq_news_quality,
    classify_theme_quality as dq_theme_quality,
    format_data_quality_badge,
    summarize_overall_data_quality,
)
from src.markdown_exporter import build_daily_markdown_context


ROOT_DIR = Path(__file__).parent
REPORTS_DIR = ROOT_DIR / "reports"
PORTFOLIO_PATH = ROOT_DIR / "config" / "portfolio.yaml"
PORTFOLIO_PUBLIC_PATH = ROOT_DIR / "config" / "portfolio_public.yaml"
POLICY_PATH = ROOT_DIR / "config" / "dca_policy.yaml"
USER_PROFILE_PATH = ROOT_DIR / "config" / "user_profile.yaml"
APP_MODE_PATH = ROOT_DIR / "config" / "app_mode.yaml"
GOLD_REPLENISHMENT_PATH = ROOT_DIR / "config" / "gold_replenishment.yaml"
FUND_TRADE_RULES_PATH = ROOT_DIR / "config" / "fund_trade_rules.yaml"
FUND_NAV_CACHE_PATH = ROOT_DIR / "data" / "fund_nav_cache.csv"
FUND_CODE_ALIASES_PATH = ROOT_DIR / "config" / "fund_code_aliases.yaml"
NEWS_SOURCES_PATH = ROOT_DIR / "config" / "news_sources.yaml"
PUBLIC_NEWS_CACHE_PATH = ROOT_DIR / "data" / "public_news_cache.json"
BACKUPS_DIR = ROOT_DIR / "backups"
EXECUTION_REVIEW_PATH = REPORTS_DIR / "execution_review.csv"

EXECUTION_REVIEW_COLUMNS = [
    "日期",
    "今日模式",
    "实际执行金额",
    "黄金是否补仓",
    "备注",
]


st.set_page_config(
    page_title="Clayton Alpha Dashboard",
    layout="wide",
)


def main() -> None:
    """Render the investment monitoring website."""

    profile = load_user_profile()
    app_mode = load_app_mode()
    apply_custom_css()

    latest_report = find_latest_report()
    public_snapshot = pd.DataFrame()
    using_public_fallback = False
    if latest_report is None and is_public_mode(app_mode):
        public_snapshot = load_public_market_snapshot()
        asset_table = build_public_asset_table(public_snapshot)
        market_status = infer_public_market_status(public_snapshot)
        report_text = build_public_snapshot_report(asset_table, market_status)
        report_date = datetime.now().strftime("%Y-%m-%d")
        news_text = "## 每日投资资讯摘要\n\n公网新闻源暂不可用，新闻页保留研究框架。"
        news_csv = None
        dca_table = pd.DataFrame()
        news_items = load_public_news(NEWS_SOURCES_PATH, PUBLIC_NEWS_CACHE_PATH)
        if not news_items.empty:
            news_text = build_public_news_text(news_items)
        using_public_fallback = True
    elif latest_report is None:
        st.warning("当前 reports 文件夹没有 daily risk report，请先运行：python main.py")
        report_text = ""
        report_date = "unknown"
        market_status = "unknown"
        news_text = load_latest_news_text(report_text)
        news_csv = find_latest_news_csv()
        asset_table = parse_asset_table(report_text)
        dca_table = parse_markdown_table(report_text, "基金")
        news_items = load_latest_news_items(news_csv, news_text)
        if is_public_mode(app_mode) and news_items.empty:
            news_items = load_public_news(NEWS_SOURCES_PATH, PUBLIC_NEWS_CACHE_PATH)
            if not news_items.empty:
                news_text = build_public_news_text(news_items)
    else:
        report_text = latest_report.read_text(encoding="utf-8")
        report_date = extract_report_date(latest_report, report_text)
        market_status = extract_market_status(report_text)
        news_text = load_latest_news_text(report_text)
        news_csv = find_latest_news_csv()
        asset_table = parse_asset_table(report_text)
        dca_table = parse_markdown_table(report_text, "基金")
        news_items = load_latest_news_items(news_csv, news_text)
    portfolio = load_yaml(active_portfolio_path(app_mode))
    policy = load_yaml(POLICY_PATH)
    if using_public_fallback:
        final_decision = build_public_fallback_decision(public_snapshot)
    else:
        final_decision = build_final_decision(portfolio, policy, asset_table, market_status, report_text, news_text)

    selected_page = render_sidebar(profile, report_date, app_mode)
    render_mode_banner(app_mode)
    render_top_action_bar(app_mode)

    if selected_page == "首页 / 今日驾驶舱":
        render_home_page(profile, portfolio, policy, asset_table, dca_table, latest_report, report_date, market_status, app_mode, final_decision, news_items)
    elif selected_page == "每日定投决策":
        render_dca_decision_page(final_decision, app_mode, asset_table, news_items, portfolio)
    elif selected_page == "当前持仓结构":
        render_portfolio_structure_page(portfolio, app_mode)
        if is_private_mode(app_mode):
            render_portfolio_snapshot_page(portfolio, policy)
    elif selected_page == "我的基金每日表现":
        render_fund_monitor_page(portfolio, final_decision, app_mode)
    elif selected_page == "持仓校准":
        render_portfolio_calibration_page(portfolio, latest_report, app_mode)
    elif selected_page == "每日 Markdown 生成":
        render_daily_markdown_page(report_date, final_decision, asset_table, news_items, portfolio, app_mode)
    elif selected_page == "主题暴露分析":
        render_theme_exposure_page(portfolio, app_mode)
    elif selected_page == "组合 X-Ray":
        render_portfolio_xray_page(portfolio, app_mode)
    elif selected_page == "行业研究 / Clayton Theme Research":
        render_theme_research_page(portfolio, asset_table, news_items, final_decision, app_mode)
    elif selected_page == "黄金仓位进度":
        render_gold_progress_page(portfolio, policy, app_mode)
    elif selected_page == "市场图表与阶段收益":
        render_market_charts_page(portfolio, app_mode, asset_table, news_csv, latest_report)
    elif selected_page == "回撤风险仪表盘":
        render_drawdown_dashboard_page(asset_table, report_text)
        render_semiconductor_watch_page(asset_table, dca_table)
    elif selected_page == "新闻与主题观察":
        render_news_digest_page(news_text, news_items, app_mode, final_decision)
        render_news_radar_page(news_items)
        render_theme_news_page(news_items, ["semiconductor", "cpo", "cpu"], "半导体 / CPO / CPU 新闻")
        render_theme_news_page(news_items, ["gold", "macro"], "黄金 / 美元 / 美债新闻")
        render_theme_news_page(news_items, ["sic"], "碳化硅观察池")
        render_news_dca_impact_page(news_text, app_mode, final_decision)
    elif selected_page == "手动新闻解析":
        render_manual_news_page(app_mode)
    elif selected_page == "策略回测 / 模型研究":
        render_model_research_page(asset_table, report_text)
    elif selected_page == "执行复盘记录":
        render_execution_review_page(final_decision, app_mode)
    elif selected_page == "部署健康检查":
        render_deployment_health_check(app_mode, public_snapshot, using_public_fallback)

    with st.expander("完整日报与市场结构", expanded=False):
        render_risk_chart(asset_table, "home_report_expander")
        render_asset_table(asset_table)
        render_market_structure(report_text)
        if is_private_mode(app_mode):
            render_full_report(report_text)
        else:
            st.info("Public 模式隐藏完整 Markdown 原文，避免泄露真实持仓金额、具体执行金额或本地路径。")

    render_footer()


def find_latest_report() -> Path | None:
    """Find the latest daily report in reports directory."""

    # 根据文件修改时间选择最新报告，兼容同一天重复生成的情况。
    reports = sorted(
        REPORTS_DIR.glob("daily_risk_report_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


def build_public_snapshot_report(asset_table: pd.DataFrame, market_status: str) -> str:
    """Build a lightweight public report from market snapshot data."""

    lines = [
        "# Public Market Snapshot",
        "",
        f"报告日期：{datetime.now().strftime('%Y-%m-%d')}",
        f"总体市场状态：{market_status}",
        "",
        "## 资产风险观察",
        "",
    ]
    if asset_table.empty:
        lines.append("公开市场数据暂不可用。")
        return "\n".join(lines)
    columns = ["资产", "代码", "最新价格", "今日涨跌幅", "RSI", "当前回撤", "风险状态"]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in asset_table.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    lines.extend(
        [
            "",
            "## 市场结构解读",
            "",
            "公网展示版使用公开市场行情自动生成，仅用于模型展示和风险观察。",
        ]
    )
    return "\n".join(lines)


def build_public_news_text(news_items: pd.DataFrame) -> str:
    """Build lightweight public news Markdown from RSS rows."""

    lines = ["## 每日投资资讯摘要", "", "公网展示版使用公开 RSS 新闻源生成基础投研摘要。"]
    if news_items.empty:
        lines.append("公网新闻源暂不可用，保留研究框架。")
        return "\n".join(lines)
    lines.extend(["", "### 今日公开新闻源", ""])
    for _, item in news_items.head(8).iterrows():
        title = str(item.get("title", ""))
        url = str(item.get("url", ""))
        source = str(item.get("source", "RSS"))
        themes = ", ".join(parse_news_themes(item.get("themes", [])))
        lines.append(f"- [{title}]({url}) | 来源：{source} | 主题：{themes}")
    return "\n".join(lines)


def build_public_fallback_decision(snapshot: pd.DataFrame) -> dict:
    """Build public-only fallback display decision when no daily report exists."""

    mode = "normal_dca"
    discipline = "normal"
    if not snapshot.empty:
        focus = snapshot.loc[snapshot["代码"].isin(["QQQ", "SMH"])]
        if not focus.empty and (pd.to_numeric(focus["RSI数值"], errors="coerce") > 70).any():
            discipline = "do_not_chase"
    if discipline == "do_not_chase":
        return {
            "market_mode": "normal_dca",
            "daily_dca_amount": 60,
            "use_tactical_cash": False,
            "tactical_cash_amount": 0,
            "fund_allocation": do_not_chase_allocation(),
            "gold_action": "公网展示：黄金按两周计划择时观察，不纳入每日基础定投。",
            "risk_discipline": "do_not_chase",
            "top_summary": "公开行情显示短线偏热",
            "cash_explanation": "公网展示模式不显示具体执行金额，也不生成买入指令。",
            "explanation": ["public fallback：QQQ/SMH RSI 偏热，基础计划继续，但不加速、不追高。"],
            "tactical_cash_action": "不作为当前核心展示字段",
        }
    return {
        "market_mode": "normal_dca",
        "daily_dca_amount": 60,
        "use_tactical_cash": False,
        "tactical_cash_amount": 0,
        "fund_allocation": do_not_chase_allocation(),
        "gold_action": "公网展示：黄金按两周计划择时观察，不纳入每日基础定投。",
        "risk_discipline": "normal",
        "top_summary": "公开行情中性观察",
        "cash_explanation": "公网展示模式不显示具体执行金额，也不生成买入指令。",
        "explanation": ["public fallback：未检测到明显过热，展示为 normal_dca。"],
        "tactical_cash_action": "不作为当前核心展示字段",
    }


def load_user_profile() -> dict:
    """Load user profile with safe defaults."""

    defaults = {
        "user_name": "Clayton",
        "dashboard_title": "Clayton Alpha Dashboard",
        "language": "zh",
        "visual_style": "dark_terminal_value",
        "motivation_style": "mixed_value_discipline",
        "current_status": "进攻但不追高",
        "current_discipline": "按计划执行，不追高",
        "current_main_theme": "半导体 / CPO",
        "current_defense": "黄金低仓位，小额补",
        "base_daily_dca": 60,
        "max_daily_dca": 100,
        "tactical_cash": 5000,
        "max_drawdown_tolerance": -0.20,
        "show_investor_photos": False,
        "app_version": "v0.3 Alpha",
    }
    loaded = load_yaml(USER_PROFILE_PATH)
    return {**defaults, **loaded}


def load_app_mode() -> dict:
    """Load public/private mode configuration with private defaults."""

    defaults = {
        "mode": "private",
        "public_mode_settings": {
            "hide_real_amounts": True,
            "hide_tactical_cash_amount": True,
            "disable_portfolio_editing": True,
            "disable_tactical_cash_editing": True,
            "hide_config_paths": True,
            "hide_backup_paths": True,
            "hide_sensitive_pages": True,
            "show_readonly_dashboard_only": True,
        },
        "private_mode_settings": {
            "show_real_amounts": True,
            "show_tactical_cash_amount": True,
            "enable_portfolio_editing": True,
            "enable_tactical_cash_editing": True,
            "show_config_paths": True,
            "show_backup_paths": True,
        },
    }
    loaded = load_yaml(APP_MODE_PATH)
    merged = {**defaults, **loaded}
    merged["mode"] = str(merged.get("mode", "private")).lower()
    forced_mode = os.environ.get("APP_MODE", "").strip().lower()
    if not forced_mode:
        forced_mode = streamlit_secret("APP_MODE").strip().lower()
    if forced_mode in {"public", "private"}:
        merged["mode"] = forced_mode
    elif is_streamlit_cloud_environment():
        merged["mode"] = "public"
    if merged["mode"] not in {"private", "public"}:
        merged["mode"] = "private"
    merged["public_mode_settings"] = {
        **defaults["public_mode_settings"],
        **loaded.get("public_mode_settings", {}),
    }
    merged["private_mode_settings"] = {
        **defaults["private_mode_settings"],
        **loaded.get("private_mode_settings", {}),
    }
    return merged


def is_streamlit_cloud_environment() -> bool:
    """Detect hosted Streamlit environments and default them to public mode."""

    cloud_env_keys = [
        "STREAMLIT_CLOUD",
        "STREAMLIT_COMMUNITY_CLOUD",
        "STREAMLIT_SHARING_MODE",
        "IS_STREAMLIT_CLOUD",
    ]
    if any(os.environ.get(key) for key in cloud_env_keys):
        return True
    return Path("/mount/src").exists()


def streamlit_secret(key: str) -> str:
    """Read one Streamlit secret safely."""

    try:
        value = st.secrets.get(key, "")
    except Exception:
        return ""
    return str(value or "")


def active_portfolio_path(app_mode: dict) -> Path:
    """Use public portfolio config for public deployments."""

    if is_public_mode(app_mode) and PORTFOLIO_PUBLIC_PATH.exists():
        return PORTFOLIO_PUBLIC_PATH
    return PORTFOLIO_PATH


def is_public_mode(app_mode: dict) -> bool:
    """Return whether dashboard is in public mode."""

    return app_mode.get("mode") == "public"


def is_private_mode(app_mode: dict) -> bool:
    """Return whether dashboard is in private mode."""

    return not is_public_mode(app_mode)


def mask_sensitive_value(value=None) -> str:
    """Mask sensitive amount values in public mode."""

    return "已隐藏"


def mask_amounts_in_text(text: str) -> str:
    """Mask currency and obvious amount values in public text."""

    masked = str(text)
    masked = re.sub(r"[¥￥]\s?[\d,]+(?:\.\d+)?(?:\s?[–-]\s?[\d,]+(?:\.\d+)?)?", "金额已隐藏", masked)
    masked = re.sub(r"(?<![\dA-Za-z])\d+(?:\.\d+)?\s?元", "已隐藏", masked)
    masked = re.sub(r"(daily_dca_amount|tactical_cash_amount)\s*[:=]\s*[\d,.]+", r"\1=已隐藏", masked)
    masked = re.sub(r"今日金额仍为\s*金额已隐藏", "今日按系统纪律执行，不展示金额", masked)
    masked = re.sub(r"今日最终动作：执行\s*金额已隐藏", "今日最终动作：按系统纪律执行", masked)
    masked = re.sub(r"执行\s*金额已隐藏", "按计划执行", masked)
    masked = re.sub(r"维持基础定投\s*金额已隐藏", "维持基础定投节奏", masked)
    masked = re.sub(r"基础定投\s*金额已隐藏", "基础定投金额已隐藏", masked)
    masked = re.sub(r"建议金额[:：]\s*金额已隐藏", "建议金额：已隐藏", masked)
    masked = re.sub(r"使用金额[^。\n]*", "使用金额：已隐藏", masked)
    masked = re.sub(r"机动资金[^。\n]*", "机动资金：已隐藏", masked)
    return masked


def public_text(text: str, app_mode: dict) -> str:
    """Mask execution amounts in public mode while preserving NAV/percent data."""

    return mask_amounts_in_text(str(text)) if is_public_mode(app_mode) else str(text)


def show_sensitive_paths(app_mode: dict) -> bool:
    """Check whether local paths may be shown."""

    return is_private_mode(app_mode)


def apply_custom_css() -> None:
    """Apply dark financial terminal styling."""

    st.markdown(
        """
        <style>
        :root {
            --bg: #111827;
            --panel: #1F2937;
            --panel-2: #243244;
            --gold: #D4AF37;
            --text: #F3F4F6;
            --body: #E5E7EB;
            --muted: #CBD5E1;
            --weak: #94A3B8;
            --green: #22C55E;
            --yellow: #FBBF24;
            --red: #EF4444;
            --blue: #38BDF8;
            --orange: #F97316;
            --defense: #94A3B8;
        }
        .stApp {
            background: linear-gradient(135deg, #111827 0%, #172033 45%, #1E293B 100%);
            color: var(--text);
        }
        [data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid rgba(212, 175, 55, 0.16);
        }
        [data-testid="stSidebar"] * {
            color: var(--body);
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--muted) !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            background: rgba(31, 41, 55, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.12);
            border-radius: 10px;
            padding: 8px 10px;
            margin-bottom: 6px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: rgba(56, 189, 248, 0.12);
            border-color: rgba(212, 175, 55, 0.45);
            box-shadow: inset 3px 0 0 rgba(212, 175, 55, 0.78);
        }
        h1, h2, h3 {
            color: var(--text);
            letter-spacing: 0;
        }
        p, li, .stMarkdown, .stText, .stCaptionContainer {
            color: var(--body);
        }
        .hero-card {
            background: linear-gradient(135deg, #1E293B 0%, #243B55 100%);
            border: 1px solid rgba(212,175,55,0.22);
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 12px 26px rgba(15,23,42,0.26), 0 0 18px rgba(212,175,55,0.07);
            margin-bottom: 14px;
        }
        .hero-title {
            color: var(--gold);
            font-size: 32px;
            font-weight: 760;
            margin: 0;
            line-height: 1.15;
        }
        .hero-subtitle {
            color: var(--muted);
            font-size: 14px;
            margin-top: 6px;
            line-height: 1.45;
        }
        .hero-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-top: 16px;
        }
        .hero-mini {
            background: rgba(31, 41, 55, 0.76);
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 10px;
            padding: 10px 12px;
            min-height: auto;
        }
        .hero-mini .label {
            color: var(--muted);
            font-size: 13px;
            margin-bottom: 5px;
            line-height: 1.35;
        }
        .hero-mini .value {
            color: var(--text);
            font-size: 15px;
            font-weight: 700;
            line-height: 1.4;
            white-space: normal;
            overflow: visible;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .terminal-clock {
            font-family: Consolas, Menlo, monospace;
            color: #22C55E;
            background: #1F2937;
            border: 1px solid rgba(34,197,94,0.35);
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 28px;
            text-align: center;
            letter-spacing: 1px;
        }
        .status-card, .metric-card {
            background: rgba(31, 41, 55, 0.92);
            border: 1px solid rgba(212, 175, 55, 0.16);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: 0 8px 18px rgba(15,23,42,0.20);
            min-height: auto;
            height: auto;
        }
        .status-card .label, .metric-card .label {
            color: var(--muted);
            font-size: 14px;
            margin-bottom: 7px;
            line-height: 1.35;
        }
        .status-card .value {
            color: var(--text);
            font-size: 16px;
            font-weight: 720;
            line-height: 1.42;
            white-space: normal;
            overflow: visible;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .metric-card .value {
            color: var(--text);
            font-size: 28px;
            font-weight: 720;
            line-height: 1.2;
            white-space: normal;
            overflow: visible;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .alpha-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 12px 0;
        }
        .alpha-card {
            background: rgba(31, 41, 55, 0.92);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 10px;
            padding: 11px 12px;
            height: auto;
            min-height: 82px;
            box-shadow: 0 8px 18px rgba(15,23,42,0.18);
        }
        .alpha-card.gold-border {
            border-color: rgba(212,175,55,0.50);
        }
        .alpha-label {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.35;
            margin-bottom: 6px;
        }
        .alpha-value {
            color: var(--text);
            font-size: 16px;
            font-weight: 720;
            line-height: 1.45;
            white-space: normal;
            overflow: visible;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .alpha-value.main-number {
            font-size: 28px;
            line-height: 1.2;
        }
        .alpha-note {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.5;
            margin: 4px 0 8px 0;
        }
        .gold-border { border-color: rgba(212,175,55,0.58); }
        .green-value { color: var(--green) !important; }
        .orange-value { color: var(--orange) !important; }
        .blue-value { color: var(--blue) !important; }
        .gold-value { color: var(--gold) !important; }
        .red-value { color: var(--red) !important; }
        .muted { color: var(--muted); }
        .motivation {
            margin: 12px 0 16px 0;
            background: rgba(212,175,55,0.10);
            border-left: 3px solid var(--gold);
            padding: 12px 14px;
            border-radius: 10px;
            color: var(--text);
            font-size: 15px;
            line-height: 1.5;
        }
        .block-container {
            padding-top: 24px;
            max-width: 1380px;
        }
        .stButton > button {
            background: #243244;
            color: var(--text);
            border: 1px solid rgba(212,175,55,0.26);
            border-radius: 10px;
        }
        .stButton > button:hover {
            border-color: var(--gold);
            color: var(--gold);
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #334155;
            border-radius: 12px;
            background: #1F2937;
        }
        [data-testid="stTable"] {
            color: var(--body);
        }
        div[data-testid="stDataFrame"] div[role="columnheader"] {
            background: #243244 !important;
            color: var(--text) !important;
            border-color: #334155 !important;
        }
        div[data-testid="stDataFrame"] div[role="gridcell"] {
            color: var(--body) !important;
            border-color: #334155 !important;
        }
        div[data-testid="stDataFrame"] div[role="row"]:nth-child(even) div[role="gridcell"] {
            background: #273449 !important;
        }
        div[data-testid="stDataFrame"] div[role="row"]:nth-child(odd) div[role="gridcell"] {
            background: #1F2937 !important;
        }
        .footer-risk {
            margin-top: 26px;
            color: var(--weak);
            font-size: 13px;
            border-top: 1px solid rgba(148,163,184,0.16);
            padding-top: 14px;
        }
        .plain-explain-card {
            background: rgba(36, 50, 68, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-left: 3px solid rgba(212, 175, 55, 0.72);
            border-radius: 12px;
            padding: 14px 16px;
            margin: 10px 0;
            box-shadow: 0 8px 18px rgba(15,23,42,0.16);
        }
        .plain-explain-card strong {
            color: var(--gold);
        }
        .plain-explain-card div {
            color: var(--body);
            line-height: 1.65;
        }
        .final-action-panel {
            background: linear-gradient(135deg, rgba(30,41,59,.98), rgba(36,50,68,.96));
            border: 1px solid rgba(56,189,248,.28);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 14px;
            box-shadow: 0 10px 24px rgba(15,23,42,.22);
        }
        .section-title {
            font-size: 22px;
            line-height: 1.25;
            margin: 0 0 10px 0;
            color: var(--text);
            font-weight: 760;
        }
        .decision-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
        }
        .decision-card {
            background: rgba(31,41,55,.88);
            border: 1px solid rgba(148,163,184,.18);
            border-radius: 10px;
            padding: 10px 12px;
            min-height: 72px;
        }
        .decision-label {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.35;
            margin-bottom: 5px;
        }
        .decision-value {
            color: var(--text);
            font-size: 17px;
            font-weight: 720;
            line-height: 1.38;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .decision-value.big {
            font-size: 30px;
            color: var(--green);
            line-height: 1.1;
        }
        .compact-table {
            font-size: 14px;
        }
        @media (max-width: 900px) {
            .hero-grid, .alpha-grid, .decision-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .hero-title {
                font-size: 30px;
            }
        }
        @media (max-width: 560px) {
            .hero-grid, .alpha-grid, .decision-grid {
                grid-template-columns: 1fr;
            }
            .hero-card {
                padding: 18px 16px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(profile: dict, report_date: str, app_mode: dict) -> str:
    """Render sidebar navigation and metadata."""

    pages = [
        "首页 / 今日驾驶舱",
        "每日定投决策",
        "每日 Markdown 生成",
        "我的基金每日表现",
        "持仓校准",
        "市场图表与阶段收益",
        "新闻与主题观察",
        "策略回测 / 模型研究",
        "执行复盘记录",
        "当前持仓结构",
        "组合 X-Ray",
        "行业研究 / Clayton Theme Research",
        "主题暴露分析",
        "黄金仓位进度",
        "回撤风险仪表盘",
        "手动新闻解析",
        "部署健康检查",
    ]
    if is_public_mode(app_mode):
        pages = [
            "首页 / 今日驾驶舱",
            "每日定投决策",
            "每日 Markdown 生成",
            "我的基金每日表现",
            "市场图表与阶段收益",
            "新闻与主题观察",
            "策略回测 / 模型研究",
            "组合 X-Ray",
            "行业研究 / Clayton Theme Research",
            "主题暴露分析",
            "黄金仓位进度",
            "回撤风险仪表盘",
            "手动新闻解析",
            "部署健康检查",
        ]
    now = datetime.now()
    with st.sidebar:
        st.markdown(f"### {profile['user_name']} Alpha Desk")
        st.caption(f"当前模式：{app_mode.get('mode', 'private')}")
        selected_page = st.radio("页面导航", pages, label_visibility="collapsed")
        st.divider()
        st.caption(f"当前日期：{format_chinese_date(now)}")
        render_small_clock()
        st.caption(f"当前报告日期：{report_date}")
        st.caption(f"系统版本：{profile['app_version']}")
        st.divider()
        st.warning("仅供研究观察，不构成投资建议")
        st.caption("不自动交易，不连接券商账户。")
    return selected_page


def render_mode_banner(app_mode: dict) -> None:
    """Render public/private mode banner."""

    if is_public_mode(app_mode):
        st.info("当前为 Public 展示模式：已隐藏真实持仓金额、具体执行金额和本地路径，仅供朋友临时查看。")


def render_top_action_bar(app_mode: dict) -> None:
    """Render top action buttons."""

    col1, col2 = st.columns([1, 5])
    with col1:
        if is_private_mode(app_mode):
            if st.button("重新生成报告"):
                regenerate_report()
        else:
            st.button("重新生成报告", disabled=True, help="Public 模式禁止运行 main.py")
    with col2:
        st.caption("本系统仅用于研究观察、风险提示和定投辅助，不构成投资建议；不自动交易，不连接券商账户。")

def render_home_page(
    profile: dict,
    portfolio: dict,
    policy: dict,
    asset_table: pd.DataFrame,
    dca_table: pd.DataFrame,
    latest_report: Path | None,
    report_date: str,
    market_status: str,
    app_mode: dict,
    final_decision: dict,
    news_items: pd.DataFrame,
) -> None:
    """Render dashboard home page."""

    now = datetime.now()
    render_today_final_action(final_decision, portfolio, asset_table, app_mode)
    st.markdown(
        f"""
        <div class="hero-card">
          <div class="hero-title">{profile['dashboard_title']}</div>
          <div class="hero-subtitle">全球资产 · QDII · 半导体 · CPO · 黄金 · 风险纪律</div>
          <div style="margin-top:18px;color:#E5E7EB;font-size:18px;">{greeting(now)}，{profile['user_name']}</div>
          <div class="muted" style="margin-top:4px;">{format_chinese_date(now)}</div>
          <div class="hero-grid">
            <div class="hero-mini"><div class="label">今日状态</div><div class="value green-value">{decision_market_mode(final_decision)}</div></div>
            <div class="hero-mini"><div class="label">今日纪律</div><div class="value orange-value">{public_text(decision_risk_discipline_label(final_decision), app_mode)}</div></div>
            <div class="hero-mini"><div class="label">今日主线</div><div class="value blue-value">{public_text(final_decision['top_summary'], app_mode)}</div></div>
            <div class="hero-mini"><div class="label">今日防守</div><div class="value gold-value">{public_text(final_decision['gold_action'], app_mode)}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_big_clock()
    motivation = daily_motivation(now)
    st.markdown(f'<div class="motivation">Clayton 今日提醒：{motivation}</div>', unsafe_allow_html=True)

    render_data_quality_overview(asset_table, portfolio, news_items, app_mode)
    render_clayton_alpha_model(portfolio, asset_table, market_status, app_mode, final_decision)
    render_home_news_summary(news_items, final_decision, app_mode)
    render_gold_defense_monitor(portfolio, asset_table, app_mode)
    with st.expander("更多账户与风险指标", expanded=False):
        render_status_cards(profile, final_decision, app_mode)
        render_core_dashboard_cards(profile, portfolio, policy, asset_table, dca_table, app_mode, final_decision)
    if show_sensitive_paths(app_mode):
        render_config_status(latest_report)
    render_header(report_date, market_status)
    if not asset_table.empty:
        render_metric_cards(asset_table)
    else:
        st.info("暂无报告，请先运行 python main.py")


def render_data_quality_overview(
    asset_table: pd.DataFrame,
    portfolio: dict,
    news_items: pd.DataFrame,
    app_mode: dict,
) -> None:
    """Render compact data-quality summary for the daily cockpit."""

    market_statuses = extract_asset_table_quality_statuses(asset_table)
    fund_statuses = load_home_fund_quality_statuses(portfolio)
    news_quality = dq_news_quality(news_items, public_fallback=is_public_mode(app_mode) and news_items.empty)
    theme_statuses = market_statuses if market_statuses else ["missing"]
    summary = summarize_overall_data_quality(
        market_quality=market_statuses,
        fund_quality=fund_statuses,
        news_quality=news_quality,
        theme_quality=theme_statuses,
    )

    st.markdown('<div class="section-title">数据质量总览</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    group_names = ["市场数据", "基金净值", "新闻数据", "行业研究"]
    for index, name in enumerate(group_names):
        group = summary["groups"][name]
        cols[index].metric(name, format_data_quality_badge(group))
        cols[index].caption(group["explanation"])
    cols[4].metric("今日结论置信度", summary["confidence"])

    if is_private_mode(app_mode):
        with st.expander("数据质量调试信息", expanded=False):
            st.write(
                {
                    "market_quality": market_statuses,
                    "fund_nav_quality": fund_statuses,
                    "news_quality": news_quality,
                    "confidence": summary["confidence"],
                }
            )


def extract_asset_table_quality_statuses(asset_table: pd.DataFrame) -> list[str]:
    """Extract rough market-data quality from the asset table."""

    if asset_table is None or asset_table.empty:
        return ["missing"]
    if "data_quality" in asset_table.columns:
        statuses = [str(value) for value in asset_table["data_quality"].dropna().tolist()]
        return statuses or ["partial"]
    return ["fresh"]


def load_home_fund_quality_statuses(portfolio: dict) -> list[str]:
    """Load lightweight fund NAV quality statuses for the home summary."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        return ["missing"]
    try:
        navs = load_or_fetch_fund_navs(funds)
    except Exception:
        return ["missing"]
    if navs.empty:
        return ["missing"]
    return [dq_fund_nav_quality(row.to_dict())["status"] for _, row in navs.iterrows()]


def render_big_clock() -> None:
    """Render large local clock with lightweight JS."""

    components.html(
        """
        <style>
        body { margin: 0; background: transparent; }
        .terminal-clock {
            font-family: Consolas, Menlo, monospace;
            color: #22C55E;
            background: #1F2937;
            border: 1px solid rgba(34,197,94,0.35);
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 30px;
            text-align: center;
            letter-spacing: 1px;
            box-sizing: border-box;
            width: 100%;
        }
        </style>
        <div class="terminal-clock" id="alpha-clock">--:--:--</div>
        <script>
        function tick(){
          const now = new Date();
          const h = String(now.getHours()).padStart(2,'0');
          const m = String(now.getMinutes()).padStart(2,'0');
          const s = String(now.getSeconds()).padStart(2,'0');
          document.getElementById('alpha-clock').textContent = h + ':' + m + ':' + s;
        }
        tick();
        setInterval(tick, 1000);
        </script>
        """,
        height=70,
    )


def render_small_clock() -> None:
    """Render small sidebar clock."""

    components.html(
        """
        <div style="font-family:Consolas,Menlo,monospace;color:#22C55E;background:#1F2937;border:1px solid rgba(34,197,94,.3);border-radius:8px;padding:8px;text-align:center;font-size:16px;" id="side-clock">--:--:--</div>
        <script>
        function tickSide(){
          const now = new Date();
          document.getElementById('side-clock').textContent =
            String(now.getHours()).padStart(2,'0') + ':' +
            String(now.getMinutes()).padStart(2,'0') + ':' +
            String(now.getSeconds()).padStart(2,'0');
        }
        tickSide();
        setInterval(tickSide, 1000);
        </script>
        """,
        height=46,
    )


def render_today_final_action(final_decision: dict, portfolio: dict, asset_table: pd.DataFrame, app_mode: dict) -> None:
    """Render the first-screen final action panel."""

    decision = enforce_display_guardrails(final_decision)
    portfolio = load_yaml(active_portfolio_path(app_mode)) or portfolio
    private_mode = is_private_mode(app_mode)
    gold_result = evaluate_gold_defense(portfolio, asset_table)
    gold_status = build_gold_cycle_status(gold_result)
    one_liner = build_today_one_liner(decision)

    st.markdown('<div class="final-action-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">今日最终动作</div>', unsafe_allow_html=True)
    if private_mode:
        cards = [
            ("今日模式", decision_market_mode(decision), ""),
            ("今日行动", "按当前定投计划执行", "big"),
            ("黄金", gold_status, ""),
            ("一句话结论", one_liner, ""),
            ("今日纪律提醒", decision_risk_discipline_label(decision), ""),
            ("本轮黄金观察", "按两周计划择时", ""),
            ("最终金额来源", "final_decision", ""),
        ]
    else:
        cards = [
            ("今日模式", decision_market_mode(decision), ""),
            ("今日行动", "按计划执行 / 不展示金额", "big"),
            ("黄金", "按两周计划观察", ""),
            ("一句话结论", public_text(one_liner, app_mode), ""),
            ("今日纪律提醒", public_text(decision_risk_discipline_label(decision), app_mode), ""),
            ("本轮黄金观察", "按计划观察，不展示金额", ""),
            ("最终金额来源", "final_decision", ""),
        ]
    html_parts = ['<div class="decision-grid">']
    for label, value, extra in cards:
        html_parts.append(
            f'<div class="decision-card"><div class="decision-label">{html.escape(label)}</div>'
            f'<div class="decision-value {extra}">{html.escape(str(value))}</div></div>'
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    st.markdown("**今日基金观察方向**")
    st.dataframe(build_tactical_allocation_display(decision, private_mode), use_container_width=True, hide_index=True)
    with st.expander("为什么这么做", expanded=False):
        st.write(public_text(build_daily_decision_explanation(decision_market_mode(decision), decision_risk_discipline_label(decision), decision, asset_table, pd.DataFrame(), portfolio), app_mode))
        st.write("黄金按两周防守补仓计划单独观察；本页面不生成具体买入金额。")
    st.markdown("</div>", unsafe_allow_html=True)


def enforce_display_guardrails(final_decision: dict) -> dict:
    """Apply display-only guardrails so old modules cannot override final_decision."""

    decision = dict(final_decision)
    if decision.get("market_mode") == "do_not_chase":
        decision["market_mode"] = "normal_dca"
        decision["risk_discipline"] = "do_not_chase"
    if decision_risk_discipline_code(decision) == "do_not_chase":
        decision["use_tactical_cash"] = False
        decision["tactical_cash_amount"] = 0
        decision["tactical_cash_action"] = "不作为当前核心展示字段"
        decision.setdefault("risk_discipline_text", "基础计划继续，但短线偏热，不追高，不加速。")
    return decision


def build_today_one_liner(decision: dict) -> str:
    """Return a compact final-action sentence."""

    if decision_risk_discipline_code(decision) == "do_not_chase":
        return "主线仍在，但短线偏热，按当前计划执行，不追高。"
    if decision["market_mode"] == "defense_mode":
        return "市场偏防守，控制新增风险。"
    if decision["market_mode"] == "healthy_pullback":
        return "出现健康回踩，可关注但仍需纪律确认。"
    if decision["market_mode"] == "strong_opportunity":
        return "出现强机会信号，仍需分批和纪律执行。"
    return "按当前计划执行，等待更高赔率机会。"


def build_gold_cycle_status(gold_result: dict) -> str:
    """Return gold cycle status text."""

    gold_record = load_gold_replenishment_record()
    if gold_record.get("cycle_status") in {"已补", "等待下一轮"} and gold_record.get("amount", 0) > 0:
        return "已补 / 等待下一轮"
    mode = gold_result.get("gold_mode", "gold_wait")
    if mode == "gold_pause":
        return "暂停"
    if mode == "gold_hold":
        return "等待下一轮"
    if mode == "gold_accumulate":
        return "未补 / 按计划观察"
    return "未补 / 等待"


def load_gold_replenishment_record() -> dict:
    """Load current gold replenishment record."""

    record = load_yaml(GOLD_REPLENISHMENT_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    amount = parse_float_plain(record.get("today_gold_replenishment_amount", 0))
    record_date = str(record.get("date", ""))
    if record_date != today or amount <= 0:
        return {"date": record_date, "amount": 0.0, "cycle_status": "未补"}
    return {"date": record_date, "amount": amount, "cycle_status": "已补"}


def parse_float_plain(value) -> float:
    """Parse a plain numeric value."""

    try:
        return float(str(value).replace("¥", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def render_tactical_cash_checklist(asset_table: pd.DataFrame, market_status: str, final_decision: dict, app_mode: dict) -> None:
    """Render tactical cash trigger checklist."""

    st.markdown("### 灵活资金触发检查")
    qqq = risk_row_from_asset_table(asset_table, ["QQQ"])
    smh = risk_row_from_asset_table(asset_table, ["SMH", "SOXX"])
    qqq_drawdown = row_float(qqq, "当前回撤数值")
    smh_drawdown = row_float(smh, "当前回撤数值")
    qqq_rsi = row_float(qqq, "RSI数值")
    smh_rsi = row_float(smh, "RSI数值")
    drawdown_ok = any(value is not None and -0.18 <= value <= -0.10 for value in [qqq_drawdown, smh_drawdown])
    rsi_ok = any(value is not None and 35 <= value <= 50 for value in [qqq_rsi, smh_rsi])
    trend_ok = infer_above_ma60(qqq) is True or infer_above_ma60(smh) is True
    risk_off = "risk-off" in str(market_status).lower()
    do_not_chase = decision_risk_discipline_code(final_decision) == "do_not_chase"
    final_use = final_decision["use_tactical_cash"] and not do_not_chase

    rows = [
        {"检查项": "QQQ/SMH 回撤是否达到 10%–18%", "结果": "是" if drawdown_ok else "否"},
        {"检查项": "RSI 是否在 35–50", "结果": "是" if rsi_ok else "否"},
        {"检查项": "是否未跌破长期趋势", "结果": "是" if trend_ok else "否"},
        {"检查项": "是否 risk-off", "结果": "是" if risk_off else "否"},
        {"检查项": "是否 do_not_chase", "结果": "是" if do_not_chase else "否"},
        {"检查项": "最终结论", "结果": "动用" if final_use else "不动用"},
        {"检查项": "使用金额", "结果": "不展示金额" if is_public_mode(app_mode) else (f"¥{final_decision.get('tactical_cash_amount', 0):,.0f}" if final_use else "¥0")},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_home_news_summary(news_items: pd.DataFrame, final_decision: dict, app_mode: dict | None = None) -> None:
    """Render only the overall news judgment on the home page."""

    st.markdown("### 每日投资简报")
    text = build_news_overall_judgment(news_items, final_decision)
    st.info(public_text(text, app_mode or {"mode": "private"}))


def render_status_cards(profile: dict, final_decision: dict | None = None, app_mode: dict | None = None) -> None:
    """Render four status cards."""

    final_decision = final_decision or {}
    app_mode = app_mode or {"mode": "private"}
    cards = [
        ("今日状态", decision_market_mode(final_decision) if final_decision else profile["current_status"], "green-value gold-border"),
        ("今日纪律", public_text(decision_risk_discipline_label(final_decision) if final_decision else profile["current_discipline"], app_mode), "orange-value"),
        ("今日主线", public_text(final_decision.get("top_summary", profile["current_main_theme"]), app_mode), "blue-value"),
        ("今日防守", public_text(final_decision.get("gold_action", profile["current_defense"]), app_mode), "gold-value"),
    ]
    cols = st.columns(4)
    for col, (label, value, css_class) in zip(cols, cards):
        col.markdown(
            f"""
            <div class="status-card {'gold-border' if 'gold-border' in css_class else ''}">
              <div class="label">{label}</div>
              <div class="value {css_class}">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_core_dashboard_cards(
    profile: dict,
    portfolio: dict,
    policy: dict,
    asset_table: pd.DataFrame,
    dca_table: pd.DataFrame,
    app_mode: dict,
    final_decision: dict,
) -> None:
    """Render core dashboard cards."""

    metrics = calculate_dashboard_metrics(profile, portfolio, policy, asset_table, dca_table, app_mode, final_decision)
    dca_label = "今日行动"
    rows = [
        [
            ("总资产", metrics["total_amount"], "gold-value"),
            (dca_label, metrics["daily_dca"], "green-value"),
            ("风险纪律", metrics["risk_discipline"], "orange-value"),
            ("黄金仓位进度", metrics["gold_weight"], "gold-value"),
        ],
        [
            ("高波动资产占比", metrics["high_vol_weight"], "blue-value"),
            ("当前回撤风险", metrics["drawdown_risk"], "red-value"),
            ("risk-on 资产数量", metrics["risk_on_count"], "green-value"),
            ("risk-off 资产数量", metrics["risk_off_count"], "red-value"),
        ],
    ]
    for row in rows:
        cols = st.columns(4)
        for col, (label, value, css_class) in zip(cols, row):
            col.markdown(
                f"""
                <div class="metric-card">
                  <div class="label">{label}</div>
                  <div class="value {css_class}">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_clayton_alpha_model(
    portfolio: dict,
    asset_table: pd.DataFrame,
    market_status: str,
    app_mode: dict,
    final_decision: dict,
) -> None:
    """Render the Clayton Alpha dynamic tactical engine on the home page."""

    tactical_inputs = build_tactical_inputs(portfolio, asset_table, market_status)
    decision = final_decision
    private_mode = is_private_mode(app_mode)
    st.markdown("### Clayton Alpha Model")
    st.markdown(
        '<div class="alpha-note">纳指科技核心 + 半导体 / CPO / CPU 主攻 + 黄金防守。目标是在回撤不明显失控的前提下，争取长期跑赢纳指100。本模块只解释结构和风险纪律，不生成具体买入金额。</div>',
        unsafe_allow_html=True,
    )

    cards = [
        ("纳指科技", "37%", "blue-value"),
        ("半导体 / CPO / CPU / AI算力", "53%", "blue-value"),
        ("黄金防守", "10%", "gold-value"),
        ("今日纪律", decision_risk_discipline_label(decision), "orange-value"),
    ]
    card_html = ['<div class="alpha-grid">']
    for label, value, extra_class in cards:
        card_html.append(
            f'<div class="alpha-card"><div class="alpha-label">{html.escape(label)}</div>'
            f'<div class="alpha-value {extra_class}">{html.escape(str(value))}</div></div>'
        )
    card_html.append('</div>')
    st.markdown("".join(card_html), unsafe_allow_html=True)

    explanation_text = "\uff1b".join(decision.get("explanation", []))
    with st.expander("模型解释与仓位偏离", expanded=False):
        st.write(explanation_text)

        if private_mode:
            deviation = build_target_deviation_display(tactical_inputs.fund_deviation or {})
            if not deviation.empty:
                st.dataframe(deviation, use_container_width=True, hide_index=True)
        else:
            st.caption("Public 模式隐藏真实持仓金额、具体执行金额和敏感账户数据，仅展示模型比例与市场模式。")


def render_gold_defense_monitor(portfolio: dict, asset_table: pd.DataFrame, app_mode: dict) -> None:
    """Render gold defense monitor without changing the main DCA framework."""

    portfolio = load_yaml(active_portfolio_path(app_mode)) or portfolio
    result = evaluate_gold_defense(portfolio, asset_table)
    signals = result["signals"]
    private_mode = is_private_mode(app_mode)
    weight_text = f"{result['gold_weight']:.2%}" if private_mode else gold_target_public_text(result["gold_weight"])
    cycle_status = build_gold_cycle_status(result)
    if not private_mode:
        cycle_status = mask_amounts_in_text(cycle_status).replace("建议 金额已隐藏", "建议按计划观察")
    gold_record = load_gold_replenishment_record()
    executed_amount = gold_record.get("amount", 0)
    suggestion_text = "按计划观察，不展示金额"
    if executed_amount > 0:
        suggestion_text = "本轮已执行"

    st.markdown("### 黄金防守监控")
    if result["data_warning"]:
        st.warning(result["data_warning"])
    st.caption("黄金模块只影响易方达黄金ETF联接A的两周补仓观察，不影响半导体/CPO/CPU主攻框架；本模块不生成具体买入金额。")
    if executed_amount > 0:
        detail = "本轮黄金补仓已执行，等待下一轮两周检查。黄金额外补仓不纳入本页每日执行口径。"
        st.success(public_text(detail, app_mode))

    cards = [
        ("黄金目标仓位", "8%–10%", "gold-value"),
        ("当前黄金仓位", weight_text, "gold-value"),
        ("本轮两周补仓状态", cycle_status, "gold-value"),
        ("今日黄金补仓状态", "已执行" if executed_amount > 0 else "按计划观察", "gold-value"),
        ("本轮两周黄金补仓建议", suggestion_text, "gold-value"),
        ("gold_mode", result["gold_mode"], "green-value" if result["gold_mode"] == "gold_accumulate" else "orange-value"),
        ("GC=F 状态", format_gold_signal(signals["GC=F"]), "gold-value"),
        ("美元/UUP 状态", format_gold_signal(signals["UUP"]), "blue-value"),
        ("实际利率/DFII10 状态", format_gold_signal(signals["DFII10"]), "orange-value"),
    ]
    card_html = ['<div class="alpha-grid">']
    for label, value, css_class in cards:
        card_html.append(
            f'<div class="alpha-card"><div class="alpha-label">{html.escape(label)}</div>'
            f'<div class="alpha-value {css_class}">{html.escape(str(value))}</div></div>'
        )
    card_html.append("</div>")
    st.markdown("".join(card_html), unsafe_allow_html=True)
    with st.expander("黄金判断细节", expanded=False):
        st.write(result["reason"])
        if signals["UUP"].get("risk_status") == "dollar_strength_pressure":
            st.write("美元偏强会压制黄金，因此黄金只小额补或等待，不追涨。")
        st.write(f"GLD 状态：{format_gold_signal(signals['GLD'])}")


def format_gold_signal(signal: dict) -> str:
    """Format one gold signal for display."""

    if signal["status"] == "data_unavailable":
        return "data_unavailable"
    if signal["symbol"] == "UUP" and signal["risk_status"] == "dollar_strength_pressure":
        return f"美元偏强 / dollar_strength_pressure / RSI {signal['rsi']:.1f}"
    if signal["symbol"] == "UUP" and signal["risk_status"] == "dollar_weakness_supportive":
        return f"dollar_weakness_supportive / RSI {signal['rsi']:.1f}"
    return f"{signal['risk_status']} / RSI {signal['rsi']:.1f}"


def gold_target_public_text(weight: float) -> str:
    """Describe gold weight safely in public mode."""

    if weight < 0.08:
        return "低于目标"
    if weight <= 0.10:
        return "接近目标"
    return "高于目标"


def build_tactical_inputs(portfolio: dict, asset_table: pd.DataFrame, market_status: str) -> TacticalInputs:
    """Build tactical inputs from the parsed daily report and portfolio config."""

    qqq = risk_row_from_asset_table(asset_table, ["QQQ"])
    smh = risk_row_from_asset_table(asset_table, ["SMH", "SOXX"])
    gld = risk_row_from_asset_table(asset_table, ["GLD"])

    gold_weight = portfolio_proxy_weight(portfolio, ["GLD"])
    sp500_weight = portfolio_proxy_weight(portfolio, ["SPY"])
    deviations = calculate_target_deviations(portfolio)

    qqq_regime = row_text(qqq, "风险状态")
    smh_regime = row_text(smh, "风险状态")
    risk_status = market_status or "normal"
    if qqq_regime == "risk-off" and smh_regime == "risk-off":
        risk_status = "risk-off"

    return TacticalInputs(
        qqq_rsi=row_float(qqq, "RSI数值"),
        smh_rsi=row_float(smh, "RSI数值"),
        qqq_drawdown=row_float(qqq, "当前回撤数值"),
        smh_drawdown=row_float(smh, "当前回撤数值"),
        qqq_above_ma60=infer_above_ma60(qqq),
        smh_above_ma60=infer_above_ma60(smh),
        gld_rsi=row_float(gld, "RSI数值"),
        market_risk_status=risk_status,
        current_gold_weight=gold_weight,
        current_sp500_weight=sp500_weight,
        fund_deviation=deviations,
    )


def risk_row_from_asset_table(asset_table: pd.DataFrame, symbols: list[str]) -> pd.Series | None:
    """Return the first matching risk row for the requested symbols."""

    if asset_table.empty or "代码" not in asset_table.columns:
        return None
    matched = asset_table.loc[asset_table["代码"].isin(symbols)]
    if matched.empty:
        return None
    return matched.iloc[0]


def row_float(row: pd.Series | None, column: str) -> float | None:
    """Read a numeric value from a row."""

    if row is None or column not in row.index or pd.isna(row[column]):
        return None
    try:
        return float(row[column])
    except (TypeError, ValueError):
        return None


def row_text(row: pd.Series | None, column: str) -> str:
    """Read a text value from a row."""

    if row is None or column not in row.index:
        return ""
    return str(row[column]).strip()


def infer_above_ma60(row: pd.Series | None) -> bool | None:
    """Infer price-vs-60-day-MA from the existing risk status when MA is not shown."""

    if row is None:
        return None
    regime = row_text(row, "风险状态")
    if regime == "risk-off":
        return False
    if regime in {"risk-on", "neutral"}:
        return True
    return None


def portfolio_proxy_weight(portfolio: dict, proxy_symbols: list[str]) -> float | None:
    """Calculate portfolio weight for one or more proxy symbols."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "current_amount" not in funds.columns or "proxy_symbol" not in funds.columns:
        return None
    total = funds["current_amount"].sum()
    if not total:
        return None
    amount = funds.loc[funds["proxy_symbol"].isin(proxy_symbols), "current_amount"].sum()
    return float(amount / total)


def calculate_target_deviations(portfolio: dict) -> dict[str, float]:
    """Calculate current minus target weight by fund for private display."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "current_amount" not in funds.columns or "target_weight" not in funds.columns:
        return {}
    total = funds["current_amount"].sum()
    if not total:
        return {}
    deviations = {}
    for _, fund in funds.iterrows():
        name = str(fund.get("fund_name", ""))
        current = float(fund.get("current_amount", 0) or 0) / total
        target = float(fund.get("target_weight", 0) or 0)
        deviations[name] = current - target
    return deviations


def build_tactical_allocation_display(decision: dict, private_mode: bool) -> pd.DataFrame:
    """Build amount-free fund direction table from final_decision context."""

    rows = []
    allocation = decision.get("fund_allocation") or do_not_chase_allocation()
    for fund_name in allocation.keys():
        rows.append(
            {
                "基金": fund_name,
                "主题": public_fund_theme_label(fund_name),
                "组合角色": public_fund_role_label(fund_name),
                "今日状态": "按计划 / 观察",
                "说明": "不输出具体买入金额，按当前定投计划执行。",
            }
        )
    gold_action = decision.get("gold_action")
    if gold_action:
        rows.append({"基金": "黄金", "主题": "防守缓冲", "组合角色": "两周计划观察", "今日状态": "按计划观察", "说明": "黄金单独观察，不在本表输出金额。"})
    return pd.DataFrame(rows)


def public_fund_theme_label(fund_name: str) -> str:
    """Return public-safe theme label for allocation rows."""

    text = str(fund_name)
    if "纳指" in text or "纳斯达克" in text:
        return "纳指底盘"
    if "国富" in text:
        return "科技互联观察"
    if "成长" in text:
        return "全球成长观察"
    if "浦银" in text or "智能科技" in text:
        return "智能科技观察"
    if "标普" in text:
        return "全球宽基观察"
    if "日经" in text:
        return "暂停观察"
    return "主题观察"


def public_fund_role_label(fund_name: str) -> str:
    """Return public-safe role label for allocation rows."""

    text = str(fund_name)
    if "纳指" in text or "纳斯达克" in text:
        return "科技核心"
    if "黄金" in text:
        return "防守缓冲"
    if "标普" in text:
        return "宽基底仓"
    if "日经" in text:
        return "观察"
    return "主线观察"


def build_allocation_summary_text(decision: dict, private_mode: bool) -> str:
    """Return a short allocation summary for compact cards."""

    if not private_mode:
        return "隐藏金额，仅展示方向"
    parts = [f"{name} \u00a5{amount}" for name, amount in decision["fund_allocation"].items()]
    return " / ".join(parts)


def build_target_deviation_display(deviations: dict[str, float]) -> pd.DataFrame:
    """Build private target-deviation table."""

    return pd.DataFrame(
        [
            {"基金": name, "偏离目标": format_percent_plain(value)}
            for name, value in deviations.items()
        ]
    )


def public_tactical_status(decision: dict) -> str:
    """Return public-safe tactical cash status."""

    if decision["market_mode"] == "strong_opportunity":
        return "出现机会提示，金额隐藏"
    return "不动用"


def decision_market_mode(decision: dict) -> str:
    """Return display-safe market mode with old do_not_chase mapped to normal_dca."""

    mode = str(decision.get("market_mode", "normal_dca") or "normal_dca")
    return "normal_dca" if mode == "do_not_chase" else mode


def decision_risk_discipline_code(decision: dict) -> str:
    """Return the normalized risk-discipline code while keeping old decisions compatible."""

    raw = str(decision.get("risk_discipline", "") or "").lower()
    mode = str(decision.get("market_mode", "") or "").lower()
    if "do_not_chase" in raw or "do_not_chase" in mode or "不追高" in raw or "短线偏热" in raw:
        return "do_not_chase"
    if "defense" in raw or mode == "defense_mode" or "防守" in raw:
        return "defense_first"
    if "wait_for_pullback" in raw or "等待回踩" in raw:
        return "wait_for_pullback"
    if "no_acceleration" in raw or "不加速" in raw:
        return "no_acceleration"
    return "normal"


def decision_risk_discipline_label(decision: dict) -> str:
    """Return human-readable risk discipline."""

    labels = {
        "normal": "正常执行",
        "do_not_chase": "短线偏热，不追高",
        "wait_for_pullback": "等待回踩，分批观察",
        "no_acceleration": "不加速",
        "defense_first": "防守优先",
    }
    return labels.get(decision_risk_discipline_code(decision), "正常执行")


def decision_blocks_acceleration(decision: dict) -> bool:
    """Return whether acceleration and tactical cash are blocked by discipline."""

    return decision_risk_discipline_code(decision) in {"do_not_chase", "defense_first", "no_acceleration"}


def build_final_decision(
    portfolio: dict,
    policy: dict,
    asset_table: pd.DataFrame,
    market_status: str,
    report_text: str,
    news_text: str,
) -> dict:
    """Build the single final daily decision used by all display modules."""

    tactical_inputs = build_tactical_inputs(portfolio, asset_table, market_status)
    decision = daily_tactical_engine(tactical_inputs)
    final_decision = normalize_tactical_decision(decision, policy)

    if should_force_do_not_chase(asset_table, report_text, news_text, tactical_inputs):
        final_decision = force_do_not_chase(final_decision)

    return final_decision


def normalize_tactical_decision(decision: dict, policy: dict) -> dict:
    """Normalize tactical-engine output to the shared final_decision schema."""

    original_mode = decision.get("market_mode", "normal_dca")
    discipline_code = str(decision.get("risk_discipline", "normal") or "normal")
    mode = "normal_dca" if original_mode == "do_not_chase" else original_mode
    if original_mode == "do_not_chase":
        discipline_code = "do_not_chase"
    use_tactical_cash = mode == "strong_opportunity" and discipline_code not in {"do_not_chase", "defense_first", "no_acceleration"}
    tactical_cash = float(policy.get("tactical_cash", 0) or 0)
    tactical_cash_amount = round(tactical_cash * 0.10, 2) if use_tactical_cash else 0
    raw_allocation = dict(decision.get("fund_allocation", {}))
    gold_daily_amount = raw_allocation.pop("黄金", 0) or 0
    gold_action = decision.get("gold_action", "")

    if discipline_code == "do_not_chase":
        top_summary = "主线仍在，但短线偏热"
        risk_discipline = "do_not_chase"
        risk_discipline_text = "基础定投继续，但短线偏热，不追高，不加速，不动用灵活资金。"
        cash_explanation = "存在过热或追高风险，灵活资金留给更大回撤/高赔率机会。"
        fund_allocation = do_not_chase_allocation()
        gold_action = "按两周计划择时观察；回调明显时可提高节奏，过热时暂停或降低节奏。"
        tactical_cash_amount = 0
        use_tactical_cash = False
    elif mode == "defense_mode":
        top_summary = "防守状态，控制新增风险"
        risk_discipline = "defense_first"
        risk_discipline_text = "防守优先，不加速成长股，不动用灵活资金。"
        cash_explanation = "市场处于防守状态，灵活资金继续保留。"
    elif mode == "strong_opportunity":
        top_summary = "强机会观察，可提高执行金额"
        risk_discipline = discipline_code if discipline_code != "normal" else "wait_for_pullback"
        risk_discipline_text = "出现强机会信号，灵活资金只能分批使用。"
        cash_explanation = "仅在回撤和趋势条件同时满足时，提示使用少量灵活资金。"
    elif mode == "healthy_pullback":
        top_summary = "健康回踩，小幅加速"
        risk_discipline = discipline_code if discipline_code != "normal" else "normal"
        risk_discipline_text = "健康回踩，可提高基础定投节奏，但不一定动用灵活资金。"
        cash_explanation = "只是健康回踩，不属于需要动用灵活资金的大机会。"
    else:
        top_summary = "维持基础定投"
        risk_discipline = discipline_code if discipline_code in {"wait_for_pullback", "no_acceleration"} else "normal"
        risk_discipline_text = "按基础节奏执行，不动用灵活资金。"
        cash_explanation = "没有明确高赔率机会，灵活资金继续等待。"

    if discipline_code != "do_not_chase":
        fund_allocation = normalize_non_gold_allocation(raw_allocation, int(decision.get("daily_dca_amount", 60) or 60))
        if gold_daily_amount:
            gold_action = f"{decision.get('gold_action', '')} 黄金不计入每日定投，转入两周防守补仓观察。"

    return {
        "market_mode": mode,
        "risk_discipline": risk_discipline,
        "risk_discipline_text": risk_discipline_text,
        "daily_dca_amount": 60 if discipline_code == "do_not_chase" else int(decision.get("daily_dca_amount", 60) or 60),
        "use_tactical_cash": use_tactical_cash,
        "tactical_cash_amount": tactical_cash_amount,
        "fund_allocation": fund_allocation,
        "gold_action": gold_action,
        "top_summary": top_summary,
        "cash_explanation": cash_explanation,
        "explanation": decision.get("explanation", []),
        "tactical_cash_action": decision.get("tactical_cash_action", ""),
    }


def should_force_do_not_chase(
    asset_table: pd.DataFrame,
    report_text: str,
    news_text: str,
    tactical_inputs: TacticalInputs,
) -> bool:
    """Return whether overheat/do-not-chase hard rules must override all other modes."""

    combined_text = f"{report_text}\n{news_text}"
    if "do_not_chase" in combined_text:
        return True
    if "RSI" in combined_text and "70" in combined_text and ("不追高" in combined_text or "高于 70" in combined_text or "高于70" in combined_text):
        return True
    if any(_value_above(value, 70) for value in [tactical_inputs.qqq_rsi, tactical_inputs.smh_rsi]):
        return True
    soxx = risk_row_from_asset_table(asset_table, ["SOXX"])
    if _value_above(row_float(soxx, "RSI数值"), 70):
        return True
    return False


def force_do_not_chase(decision: dict) -> dict:
    """Force do_not_chase as a discipline without cancelling base DCA."""

    forced = dict(decision)
    forced.update(
        {
            "market_mode": "normal_dca",
            "risk_discipline": "do_not_chase",
            "risk_discipline_text": "基础定投继续，但短线偏热，不追高，不加速，不动用灵活资金。",
            "daily_dca_amount": 60,
            "use_tactical_cash": False,
            "tactical_cash_amount": 0,
            "top_summary": "主线仍在，但短线偏热",
            "cash_explanation": "存在过热或追高风险，灵活资金留给更大回撤/高赔率机会。",
            "gold_action": "按两周计划择时观察；回调明显时可提高节奏，过热时暂停或降低节奏。",
            "fund_allocation": do_not_chase_allocation(),
            "explanation": ["QQQ、SMH 或 SOXX 存在 RSI 过热 / do_not_chase 信号：基础定投继续，但不加速、不追高、不动用灵活资金。"],
            "tactical_cash_action": "不动用灵活加仓资金",
        }
    )
    return forced


def do_not_chase_allocation() -> dict[str, int]:
    """Return the fixed do_not_chase allocation."""

    return {
        "广发纳指100": 10,
        "浦银全球智能科技": 15,
        "国富全球科技互联": 15,
        "易方达全球成长": 20,
        "摩根标普500": 0,
        "华安日经225": 0,
    }


def _value_above(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def calculate_dashboard_metrics(
    profile: dict,
    portfolio: dict,
    policy: dict,
    asset_table: pd.DataFrame,
    dca_table: pd.DataFrame,
    app_mode: dict,
    final_decision: dict | None = None,
) -> dict:
    """Calculate dashboard metrics with safe fallbacks."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    total = float(funds["current_amount"].sum()) if not funds.empty and "current_amount" in funds.columns else None
    gold_weight = None
    high_vol_weight = None
    if total and total > 0:
        gold_weight = float(funds.loc[funds["theme"] == "黄金", "current_amount"].sum() / total) if "theme" in funds.columns else None
        high_vol_weight = (
            float(funds.loc[funds["is_high_volatility"].astype(bool), "current_amount"].sum() / total)
            if "is_high_volatility" in funds.columns
            else None
        )

    drawdown = None
    if not asset_table.empty and "当前回撤数值" in asset_table.columns:
        drawdown = asset_table["当前回撤数值"].dropna().min()

    return {
        "total_amount": mask_sensitive_value(total) if is_public_mode(app_mode) else format_currency(total),
        "daily_dca": "按当前定投计划执行",
        "risk_discipline": decision_risk_discipline_label(final_decision or {}),
        "gold_weight": format_percent_plain(gold_weight),
        "high_vol_weight": format_percent_plain(high_vol_weight),
        "drawdown_risk": format_percent_plain(drawdown),
        "risk_on_count": safe_count(asset_table, "风险状态", "risk-on"),
        "risk_off_count": safe_count(asset_table, "风险状态", "risk-off"),
    }


def find_latest_news_digest() -> Path | None:
    """Find the latest standalone news digest."""

    reports = sorted(
        REPORTS_DIR.glob("news_digest_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


def find_latest_news_csv() -> Path | None:
    """Find the latest standalone news CSV."""

    reports = sorted(
        REPORTS_DIR.glob("news_digest_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return reports[0] if reports else None


def load_latest_news_text(report_text: str) -> str:
    """Load news digest from daily report first, then standalone digest."""

    section = extract_section(report_text, "每日投资资讯摘要")
    if section:
        return "## 每日投资资讯摘要\n\n" + section

    news_path = find_latest_news_digest()
    if news_path:
        return news_path.read_text(encoding="utf-8")

    return "## 每日投资资讯摘要\n\n- 暂无新闻摘要。请先运行：python main.py"


def regenerate_report() -> None:
    """Run main.py and refresh the page."""

    # 使用当前 Python 解释器执行 main.py，避免不同环境里的 python 命令不一致。
    result = subprocess.run(
        [sys.executable, str(ROOT_DIR / "main.py")],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        st.error("报告重新生成失败，请检查本地 Python 环境和依赖。")
        if result.stderr:
            st.code(result.stderr)
        return

    st.success("报告已重新生成。")
    st.rerun()


def render_header(report_date: str, market_status: str) -> None:
    """Render report date and headline market status."""

    # 顶部只保留最关键的两个信息：今天是什么报告、总体状态是什么。
    col1, col2 = st.columns(2)
    col1.metric("报告日期", report_date)
    col2.metric("总体市场状态", market_status or "unknown")


def render_config_status(latest_report: Path | None) -> None:
    """Render config paths and timestamps."""

    # 这些路径和时间帮助确认网页当前读写的是哪一份本地配置。
    col1, col2 = st.columns(2)
    col1.caption(f"当前读取的 portfolio.yaml 路径：{PORTFOLIO_PATH}")
    col2.caption(f"当前读取的 dca_policy.yaml 路径：{POLICY_PATH}")

    col3, col4 = st.columns(2)
    col3.caption(f"最后保存时间：{format_path_mtime(latest_existing_path([PORTFOLIO_PATH, POLICY_PATH]))}")
    col4.caption(f"最后报告生成时间：{format_path_mtime(latest_report)}")


def render_deployment_health_check(app_mode: dict, public_snapshot: pd.DataFrame | None = None, using_public_fallback: bool = False) -> None:
    """Render public-safe deployment checks without exposing local paths."""

    st.subheader("部署健康检查")
    snapshot = public_snapshot if public_snapshot is not None and not public_snapshot.empty else load_public_market_snapshot()
    available_count = 0 if snapshot.empty else int((snapshot["data_quality"] != "missing").sum())
    missing_count = len(PUBLIC_TICKERS) - available_count
    checks = [
        {"检查项": "app_mode", "状态": app_mode.get("mode", "unknown")},
        {"检查项": "是否 public", "状态": "是" if is_public_mode(app_mode) else "否"},
        {"检查项": "敏感金额隐藏", "状态": "是" if is_public_mode(app_mode) else "private 显示"},
        {"检查项": "public_data_loader", "状态": "可用"},
        {"检查项": "market snapshot", "状态": "成功" if available_count else "全部缺失"},
        {"检查项": "可用 ticker 数量", "状态": str(available_count)},
        {"检查项": "缺失 ticker 数量", "状态": str(missing_count)},
        {"检查项": "reports 缺失 fallback", "状态": "已使用 public fallback" if using_public_fallback else "未触发"},
        {"检查项": "requirements.txt", "状态": "存在" if (ROOT_DIR / "requirements.txt").exists() else "缺失"},
        {"检查项": "Streamlit config", "状态": "存在" if (ROOT_DIR / ".streamlit" / "config.toml").exists() else "缺失"},
        {"检查项": "public portfolio", "状态": "存在" if PORTFOLIO_PUBLIC_PATH.exists() else "缺失"},
        {"检查项": "app mode config", "状态": "存在" if APP_MODE_PATH.exists() else "缺失"},
    ]
    st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True)
    if is_public_mode(app_mode):
        st.info("Public 模式已隐藏真实持仓金额、具体执行金额、本地路径、配置路径和调试信息。")
    else:
        st.warning("当前为 private 模式。部署到公网前请设置环境变量 APP_MODE=public，或确认 Streamlit Cloud 自动识别为 public。")


def render_portfolio_calibration_page(portfolio: dict, latest_report: Path | None, app_mode: dict) -> None:
    """Render editable portfolio calibration page."""

    if is_public_mode(app_mode):
        st.warning("Public 模式禁止持仓校准和任何本地写入。")
        return

    st.subheader("持仓校准 / 金额编辑")
    st.caption("所有修改只写入本地 YAML 文件，不连接券商账户，不保存账号密码，不自动交易。")
    st.write(f"当前读取的 portfolio.yaml 路径：`{PORTFOLIO_PATH}`")
    st.write(f"最后保存时间：{format_path_mtime(PORTFOLIO_PATH)}")
    st.write(f"最后报告生成时间：{format_path_mtime(latest_report)}")

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("portfolio.yaml 中没有 funds 配置。")
        return

    editable_columns = [
        "fund_name",
        "fund_code",
        "current_amount",
        "base_daily_dca",
        "max_daily_dca",
        "target_weight",
        "theme",
        "risk_level",
        "role_in_portfolio",
        "is_high_volatility",
        "priority_rank",
    ]
    visible_columns = [column for column in editable_columns if column in funds.columns]
    helper_columns = [column for column in ["proxy_symbol", "is_core_holding"] if column in funds.columns]
    display_columns = visible_columns + helper_columns

    edited = st.data_editor(
        funds[display_columns],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=helper_columns,
        key="portfolio_editor",
    )

    if st.button("保存持仓配置", type="primary"):
        updated_funds = merge_edited_funds(original=funds, edited=edited)
        payload = {"funds": normalize_funds_for_yaml(updated_funds)}
        backup_path = backup_yaml(PORTFOLIO_PATH, "portfolio")
        write_yaml(PORTFOLIO_PATH, payload)
        st.success(f"持仓配置已保存，旧文件已备份到：{backup_path}")
        show_main_run_result(run_main_py())


def render_tactical_cash_management_page(policy: dict, latest_report: Path | None, app_mode: dict) -> None:
    """Render editable tactical cash policy page."""

    if is_public_mode(app_mode):
        st.warning("Public 模式禁止机动资金管理和任何本地写入。")
        return

    st.subheader("机动资金管理")
    st.caption("这些参数只用于本地研究观察和定投辅助，不会触发任何交易动作。")
    st.write(f"当前读取的 dca_policy.yaml 路径：`{POLICY_PATH}`")
    st.write(f"最后保存时间：{format_path_mtime(POLICY_PATH)}")
    st.write(f"最后报告生成时间：{format_path_mtime(latest_report)}")

    with st.form("policy_form"):
        col1, col2, col3 = st.columns(3)
        tactical_cash = col1.number_input("当前机动资金余额 tactical_cash", value=float(policy.get("tactical_cash", 5000)), step=100.0)
        base_daily_budget = col2.number_input("正常每日定投金额 base_daily_budget", value=float(policy.get("base_daily_budget", 60)), step=5.0)
        max_daily_budget = col3.number_input("每日最大定投金额 max_daily_budget", value=float(policy.get("max_daily_budget", 100)), step=5.0)

        col4, col5, col6 = st.columns(3)
        max_drawdown_tolerance = col4.number_input(
            "最大可接受回撤 max_drawdown_tolerance",
            value=float(policy.get("max_drawdown_tolerance", -0.20)),
            step=0.01,
            format="%.2f",
        )
        gold_target_weight_min = col5.number_input(
            "黄金目标下限 gold_target_weight_min",
            value=float(policy.get("gold_target_weight_min", 0.06)),
            step=0.01,
            format="%.2f",
        )
        gold_target_weight_max = col6.number_input(
            "黄金目标上限 gold_target_weight_max",
            value=float(policy.get("gold_target_weight_max", 0.08)),
            step=0.01,
            format="%.2f",
        )

        col7, col8, col9 = st.columns(3)
        high_volatility_max_weight = col7.number_input(
            "高波动资产上限 high_volatility_max_weight",
            value=float(policy.get("high_volatility_max_weight", 0.75)),
            step=0.01,
            format="%.2f",
        )
        tactical_cash_tranches = col8.number_input(
            "机动资金份数 tactical_cash_tranches",
            value=int(policy.get("tactical_cash_tranches", 5)),
            step=1,
            min_value=1,
        )
        single_tranche_amount = col9.number_input(
            "单份机动资金 single_tranche_amount",
            value=float(policy.get("single_tranche_amount", 1000)),
            step=100.0,
        )

        submitted = st.form_submit_button("保存机动资金配置", type="primary")

    updated_policy = {
        "base_daily_budget": base_daily_budget,
        "max_daily_budget": max_daily_budget,
        "tactical_cash": tactical_cash,
        "max_drawdown_tolerance": max_drawdown_tolerance,
        "gold_target_weight_min": gold_target_weight_min,
        "gold_target_weight_max": gold_target_weight_max,
        "high_volatility_max_weight": high_volatility_max_weight,
        "tactical_cash_tranches": tactical_cash_tranches,
        "single_tranche_amount": single_tranche_amount,
    }

    if submitted:
        backup_path = backup_yaml(POLICY_PATH, "dca_policy")
        write_yaml(POLICY_PATH, normalize_policy_for_yaml(updated_policy))
        st.success(f"机动资金配置已保存，旧文件已备份到：{backup_path}")
        show_main_run_result(run_main_py())

    st.markdown("**当前页面中的规则预览**")
    st.json(normalize_policy_for_yaml(updated_policy))


def render_portfolio_snapshot_page(portfolio: dict, policy: dict) -> None:
    """Render portfolio snapshot and calibration freshness."""

    st.subheader("持仓快照")
    st.caption("快照来自本地 portfolio.yaml，不连接任何投资账户。")

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("未找到持仓配置。")
        return

    last_calibration = latest_backup_time("portfolio") or path_mtime(PORTFOLIO_PATH)
    st.write(f"每次手动校准的最近时间：{format_datetime(last_calibration)}")
    if last_calibration and datetime.now() - last_calibration > timedelta(days=7):
        st.warning("距离上次手动校准已超过 7 天，建议更新真实持仓金额。")

    total_amount = float(funds["current_amount"].sum())
    funds["weight"] = funds["current_amount"] / total_amount if total_amount else 0
    gold_weight = float(funds.loc[funds["theme"] == "黄金", "current_amount"].sum() / total_amount) if total_amount else 0
    high_vol_weight = (
        float(funds.loc[funds["is_high_volatility"].astype(bool), "current_amount"].sum() / total_amount)
        if total_amount and "is_high_volatility" in funds.columns
        else 0
    )

    min_gold = float(policy.get("gold_target_weight_min", 0.06))
    max_gold = float(policy.get("gold_target_weight_max", 0.08))

    col1, col2, col3 = st.columns(3)
    col1.metric("当前总资产", f"¥{total_amount:,.2f}")
    col2.metric("黄金仓位", f"{gold_weight:.2%}")
    col3.metric("高波动资产占比", f"{high_vol_weight:.2%}")

    if min_gold <= gold_weight <= max_gold:
        st.success("黄金仓位位于 6%-8% 目标区间。")
    elif gold_weight < min_gold:
        st.info("黄金仓位低于 6%，可在报告规则中作为小额防守缓冲观察。")
    else:
        st.warning("黄金仓位高于 8%，报告规则会倾向暂停补仓观察。")

    display = funds[["fund_name", "fund_code", "theme", "current_amount", "weight"]].copy()
    display["weight"] = display["weight"].map(lambda value: f"{value:.2%}")
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_metric_cards(asset_table: pd.DataFrame) -> None:
    """Render core dashboard metric cards."""

    # 这些卡片帮助快速判断风险分布和短线压力。
    total_count = len(asset_table)
    risk_on_count = int((asset_table["风险状态"] == "risk-on").sum())
    neutral_count = int((asset_table["风险状态"] == "neutral").sum())
    risk_off_count = int((asset_table["风险状态"] == "risk-off").sum())
    hot_rsi_count = int((asset_table["RSI数值"] > 70).sum())
    deep_drawdown_count = int((asset_table["当前回撤数值"] < -0.10).sum())

    cols = st.columns(6)
    cols[0].metric("总资产数量", total_count)
    cols[1].metric("risk-on", risk_on_count)
    cols[2].metric("neutral", neutral_count)
    cols[3].metric("risk-off", risk_off_count)
    cols[4].metric("RSI > 70", hot_rsi_count)
    cols[5].metric("回撤 > 10%", deep_drawdown_count)


def greeting(now: datetime) -> str:
    """Return time-based greeting."""

    if now.hour < 12:
        return "早上好"
    if now.hour < 18:
        return "下午好"
    return "晚上好"


def format_chinese_date(now: datetime) -> str:
    """Format date as YYYY-MM-DD weekday."""

    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{now:%Y-%m-%d} {weekdays[now.weekday()]}"


def daily_motivation(now: datetime) -> str:
    """Return a deterministic daily motivation sentence."""

    quotes = [
        "慢慢变富，比快速证明自己更重要。",
        "今天不需要战胜市场，只需要战胜冲动。",
        "真正的进攻，是机会来临时你还有现金。",
        "不追高，不恐慌，不把纪律浪费在情绪里。",
        "市场每天都开门，但好机会不会每天出现。",
        "你要做的是积累筹码，不是每天证明自己正确。",
        "进攻要有，但必须等赔率站在你这边。",
        "现金不是躺平，是等待错误定价的子弹。",
        "复利最怕中断，投资最怕冲动。",
        "当市场很热时，纪律比观点更值钱。",
        "好公司也需要好价格，好主题也需要好节奏。",
        "真正的耐心，是在看懂机会前不急着下注。",
        "每日计划是底盘，风险纪律是锋刃。",
        "上涨时保持清醒，下跌时保持结构。",
        "不要因为热闹提高仓位，要因为赔率提高仓位。",
        "机会不是喊出来的，是跌出来、等出来的。",
        "高波动资产给收益，也会测试纪律。",
        "今天的克制，是未来进攻的资金来源。",
        "半导体可以进攻，但不能用情绪追价。",
        "黄金是缓冲，不是炫耀观点的地方。",
        "一笔好投资，往往先表现为一段无聊的坚持。",
        "不要把短期波动误认为长期判断。",
        "当市场奖励冲动时，更要保护纪律。",
        "你不需要抓住每一次上涨，只需要别错过真正的大机会。",
        "现金管理决定你能不能在下跌时保持主动。",
        "每日计划不是小事，长期复利会让它变重。",
        "最好的系统，是让你在情绪强烈时仍按规则行动。",
        "看得懂才加速，看不懂就保持基础定投。",
        "真正的风险不是下跌，而是下跌时没有计划。",
        "好机会出现前，先把仓位和现金准备好。",
        "别让新闻替你下单，新闻只负责提醒你观察。",
        "估值压力上升时，少一点进攻就是一种进攻。",
        "在市场兴奋时留现金，在市场悲观时留勇气。",
        "主线可以坚定，买点必须克制。",
        "长期主义不是盲目持有，而是有纪律地持有。",
        "先活下来，再变强；先守纪律，再谈超额收益。",
        "今天的目标不是满仓正确，而是持续正确。",
        "执行纪律不该被普通波动消耗。",
        "复利需要时间，也需要少犯大错。",
        "你可以偏激进，但不能没有刹车。",
        "价格回踩时再进攻，比情绪高涨时追逐更有质量。",
        "市场会诱惑你频繁行动，系统提醒你慢一点。",
        "把每一次加速都当成稀缺资源。",
        "黄金低仓位时可以补，但不要把防守当主攻。",
        "等待不是错过，等待是在筛选赔率。",
        "大机会来临前，账户里要有现金，心里要有规则。",
        "别为了今天好看，牺牲明天的主动权。",
        "纪律不是保守，纪律是进攻的前提。",
        "真正优秀的投资者，敢于在无聊时坚持。",
        "市场的噪音很多，复利的路径很窄。",
        "今天少一点冲动，未来多一点选择。",
        "当你想加速时，先看 RSI，再看现金，再看回撤。",
        "半导体是主线，纪律是底线。",
        "好主题不等于好买点。",
        "如果没有大机会，就让基础定投自己工作。",
        "不要急着证明判断，先确保计划能活过波动。",
        "耐心的价值，在于它没有被提前浪费。",
        "回撤不是敌人，无计划的回撤才是。",
        "长期收益来自少数正确的大动作和多数正确的小动作。",
        "今天按规则做，明天才有资格进攻。",
    ]
    day_index = int(now.strftime("%Y%m%d")) % len(quotes)
    return quotes[day_index]


def extract_dca_total(dca_table: pd.DataFrame) -> float | None:
    """Extract total suggested DCA from DCA table."""

    if dca_table.empty or "今日建议金额" not in dca_table.columns:
        return None
    values = dca_table["今日建议金额"].map(lambda value: parse_currency(value))
    total = values.dropna().sum()
    return float(total) if total else None


def parse_currency(value) -> float | None:
    """Parse currency-like strings."""

    try:
        return float(str(value).replace("¥", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def format_currency(value) -> str:
    """Format currency value."""

    if value is None or pd.isna(value):
        return "暂无数据"
    return f"¥{float(value):,.0f}"


def format_percent_plain(value) -> str:
    """Format decimal percent."""

    if value is None or pd.isna(value):
        return "暂无数据"
    return f"{float(value):.2%}"


def format_number_plain(value, decimals: int = 4) -> str:
    """Format a numeric value without exposing account amounts."""

    if value is None or pd.isna(value):
        return "暂无数据"
    return f"{float(value):.{decimals}f}"


def load_fund_trade_rules() -> dict:
    """Load local fund trade rules safely."""

    rules = load_yaml(FUND_TRADE_RULES_PATH)
    return rules.get("fund_trade_rules", rules) if isinstance(rules, dict) else {}


def safe_count(data: pd.DataFrame, column: str, value: str) -> str:
    """Count values safely."""

    if data.empty or column not in data.columns:
        return "暂无数据"
    return str(int((data[column] == value).sum()))


def render_footer() -> None:
    """Render risk footer."""

    st.markdown(
        """
        <div class="footer-risk">
        本系统仅用于研究观察、风险提示和定投辅助，不构成投资建议；不自动交易，不连接券商账户。
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_dark_plotly_layout(fig):
    """Apply the dashboard dark theme to Plotly charts."""

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#1F2937",
        font_color="#E5E7EB",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def dashboard_plotly_key(page_name: str, section_name: str, chart_type: str, symbol: str = "all") -> str:
    """Build a unique key for dashboard Plotly charts."""

    return (
        "plotly_dashboard_"
        f"{sanitize_plotly_key(page_name)}_"
        f"{sanitize_plotly_key(section_name)}_"
        f"{sanitize_plotly_key(chart_type)}_"
        f"{sanitize_plotly_key(symbol)}"
    )


def render_risk_chart(asset_table: pd.DataFrame, section_name: str = "default") -> None:
    """Render risk-status distribution chart."""

    if asset_table.empty or "风险状态" not in asset_table.columns:
        st.info("暂无资产风险表格，请先生成日报。")
        return

    # 用简单柱状图展示 risk-on、neutral、risk-off 的数量分布。
    distribution = (
        asset_table["风险状态"]
        .value_counts()
        .rename_axis("风险状态")
        .reset_index(name="数量")
    )
    fig = px.bar(
        distribution,
        x="风险状态",
        y="数量",
        color="风险状态",
        color_discrete_map={"risk-on": "#16a34a", "neutral": "#ca8a04", "risk-off": "#dc2626"},
        text="数量",
    )
    apply_dark_plotly_layout(fig)
    fig.update_layout(showlegend=False, height=280, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=dashboard_plotly_key("model_research", section_name, "risk_distribution"),
    )


def render_asset_table(asset_table: pd.DataFrame) -> None:
    """Render the asset risk observation table."""

    st.subheader("资产风险观察")
    if asset_table.empty:
        st.info("暂无资产风险表格，请先生成日报。")
        return

    # 对风险状态列加颜色，绿色/黄色/红色对应三种状态。
    display_table = asset_table.drop(columns=["RSI数值", "当前回撤数值"], errors="ignore")
    styled_table = display_table.style.map(color_risk_status, subset=["风险状态"])
    st.dataframe(styled_table, use_container_width=True, hide_index=True)


def render_dca_decision_page(
    final_decision: dict,
    app_mode: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    portfolio: dict,
) -> None:
    """Render amount-free daily decision context from final_decision."""

    st.subheader("每日定投决策")
    mode = normalize_current_market_mode(final_decision, asset_table)
    discipline = current_risk_discipline_text(final_decision, asset_table)
    action = current_action_suggestion(mode, discipline)

    col1, col2, col3 = st.columns(3)
    col1.metric("今日市场状态", mode)
    col2.metric("今日风险纪律", discipline)
    col3.metric("今日行动建议", action)

    st.info(build_daily_decision_explanation(mode, discipline, final_decision, asset_table, news_items, portfolio))
    st.markdown("#### 核心资产观察")
    st.dataframe(build_core_asset_decision_rows(asset_table), use_container_width=True, hide_index=True)
    st.markdown("#### 基金观察方向")
    st.dataframe(build_tactical_allocation_display(final_decision, is_private_mode(app_mode)), use_container_width=True, hide_index=True)
    render_final_decision_plain_language(final_decision, app_mode)
    st.caption("本页只输出市场状态、风险纪律和行动方向，不生成具体买入金额；不构成投资建议，不自动交易。")


def render_public_dca_decision_page(final_decision: dict) -> None:
    """Render public-safe DCA decision without any execution amounts."""

    col1, col2, col3 = st.columns(3)
    col1.metric("今日模式", decision_market_mode(final_decision))
    col2.metric("今日行动", "按计划执行")
    col3.metric("风险纪律", decision_risk_discipline_label(final_decision))
    st.markdown(f"**执行纪律：** {mask_amounts_in_text(decision_risk_discipline_label(final_decision))}")
    st.markdown("**今日基金观察方向**")
    st.dataframe(build_tactical_allocation_display(final_decision, private_mode=False), use_container_width=True, hide_index=True)


def normalize_current_market_mode(final_decision: dict, asset_table: pd.DataFrame) -> str:
    """Return execution-state mode without using do_not_chase as the market mode."""

    mode = str(final_decision.get("market_mode") or "normal_dca")
    if mode == "do_not_chase":
        return "normal_dca"
    if sharp_pullback_detected(asset_table):
        return "sharp_pullback_probe"
    allowed = {"normal_dca", "sharp_pullback_probe", "healthy_pullback", "strong_opportunity", "defense_mode"}
    return mode if mode in allowed else "normal_dca"


def current_risk_discipline_text(final_decision: dict, asset_table: pd.DataFrame) -> str:
    """Translate risk discipline to the current non-amount execution language."""

    code = decision_risk_discipline_code(final_decision)
    rsi_hot = False
    if not asset_table.empty and "RSI数值" in asset_table.columns and "资产" in asset_table.columns:
        core = asset_table[asset_table["资产"].astype(str).str.contains("QQQ|SMH|SOXX", case=False, na=False)]
        rsi_hot = bool((pd.to_numeric(core["RSI数值"], errors="coerce") > 70).any())
    if code == "do_not_chase" or rsi_hot:
        return "短线偏热，不追高"
    if code == "defense_first":
        return "防守优先"
    if sharp_pullback_detected(asset_table):
        return "急跌试探，等待确认"
    if normalize_current_market_mode(final_decision, asset_table) == "healthy_pullback":
        return "健康回踩，可关注加仓"
    return "正常执行"


def current_action_suggestion(mode: str, discipline: str) -> str:
    """Return amount-free action suggestion."""

    if "不追高" in discipline:
        return "暂不追高"
    if mode == "sharp_pullback_probe":
        return "等待确认"
    if mode == "healthy_pullback":
        return "可小额观察"
    if mode == "strong_opportunity":
        return "复盘后再决定"
    if mode == "defense_mode":
        return "降低进攻"
    return "继续按计划"


def sharp_pullback_detected(asset_table: pd.DataFrame) -> bool:
    """Detect a fast pullback that is not yet a confirmed healthy pullback."""

    if asset_table.empty or "当前回撤数值" not in asset_table.columns or "资产" not in asset_table.columns:
        return False
    core = asset_table[asset_table["资产"].astype(str).str.contains("QQQ|SMH|SOXX", case=False, na=False)]
    drawdowns = pd.to_numeric(core.get("当前回撤数值"), errors="coerce")
    return bool(((drawdowns <= -0.05) & (drawdowns > -0.10)).any())


def build_core_asset_decision_rows(asset_table: pd.DataFrame) -> pd.DataFrame:
    """Build concise explanations for core assets."""

    rows = []
    for symbol in ["QQQ", "SMH", "SOXX", "GLD", "UUP", "TLT"]:
        row = risk_row_from_asset_table(asset_table, [symbol])
        if not row:
            rows.append({"资产": symbol, "观察": "数据不足", "说明": "暂无法判断。"})
            continue
        rsi = row_float(row, "RSI数值")
        drawdown = row_float(row, "当前回撤数值")
        rows.append(
            {
                "资产": symbol,
                "观察": str(row.get("风险状态", "N/A")),
                "说明": explain_core_asset(symbol, rsi, drawdown, str(row.get("风险状态", ""))),
            }
        )
    return pd.DataFrame(rows)


def explain_core_asset(symbol: str, rsi: float | None, drawdown: float | None, risk_status: str) -> str:
    """Explain one core asset in plain Chinese."""

    rsi_text = "RSI缺失" if rsi is None else f"RSI {rsi:.1f}"
    dd_text = "回撤缺失" if drawdown is None else f"回撤 {drawdown:.1%}"
    if rsi is not None and rsi > 70:
        return f"{rsi_text}，短线偏热；{symbol} 可继续观察，但不追高。"
    if drawdown is not None and -0.10 <= drawdown <= -0.05 and rsi is not None and 45 <= rsi <= 60:
        return f"{dd_text}，{rsi_text}，接近健康回踩观察区。"
    if "risk-off" in risk_status:
        return f"{symbol} 偏弱，先控制进攻节奏。"
    return f"{symbol} 当前状态为 {risk_status or 'normal'}；{rsi_text}，{dd_text}。"


def build_daily_decision_explanation(
    mode: str,
    discipline: str,
    final_decision: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    portfolio: dict,
) -> str:
    """Build a compact non-amount explanation for the daily decision page."""

    news_signal = "新闻数据不足，暂只看市场数据。"
    if not news_items.empty:
        news_signal = "新闻用于确认主线和风险，不覆盖 final_decision，也不生成买入金额。"
    theme_signal = "行业研究只提供主题强弱和观察池，不生成具体买入金额。"
    return (
        f"今日处于 {mode}，风险纪律为“{discipline}”。"
        "QQQ、SMH、SOXX 用来观察科技和半导体主线；GLD、UUP、TLT 用来观察黄金、防守和美元/利率压力。"
        f"{news_signal}{theme_signal} 今日行动口径是：{current_action_suggestion(mode, discipline)}。"
    )


def render_daily_markdown_page(
    report_date: str,
    final_decision: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    portfolio: dict,
    app_mode: dict,
) -> None:
    """Render daily Markdown exporter page."""

    st.subheader("每日 Markdown 生成")
    st.info("这个页面用于生成每日投资上下文 Markdown，方便复制给 AI 进行二次分析。它不直接给出买入金额，也不构成投资建议。")
    date_text = report_date if report_date and report_date != "unknown" else datetime.now().strftime("%Y-%m-%d")
    if st.button("生成今日 Markdown", type="primary") or "daily_markdown_context" not in st.session_state:
        st.session_state["daily_markdown_context"] = build_current_daily_markdown(
            date_text,
            final_decision,
            asset_table,
            news_items,
            portfolio,
            app_mode,
        )
    markdown_text = st.session_state.get("daily_markdown_context", "")
    if st.button("复制用 Markdown"):
        st.info("请在下方文本框内使用 Ctrl+A / Ctrl+C 复制；浏览器权限限制下，Streamlit 服务器端不能直接写入剪贴板。")
    st.text_area("复制用 Markdown", markdown_text, height=520)
    st.download_button(
        "下载 .md 文件",
        data=markdown_text.encode("utf-8"),
        file_name=f"daily_investment_context_{date_text}.md",
        mime="text/markdown",
    )


def build_current_daily_markdown(
    date_text: str,
    final_decision: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    portfolio: dict,
    app_mode: dict,
) -> str:
    """Assemble current website state into one safe Markdown context."""

    return build_daily_markdown_context(
        date=date_text,
        final_decision={
            "market_mode": normalize_current_market_mode(final_decision, asset_table),
            "risk_discipline": current_risk_discipline_text(final_decision, asset_table),
            "one_line_summary": build_today_one_liner(enforce_display_guardrails(final_decision)),
        },
        market_rows=build_markdown_market_rows(asset_table),
        fund_rows=build_markdown_fund_rows(portfolio, final_decision, app_mode),
        news_rows=build_markdown_news_rows(news_items, app_mode, final_decision),
        theme_rows=build_markdown_theme_rows(portfolio, asset_table, news_items, final_decision, app_mode),
        data_quality_summary=build_markdown_data_quality_summary(asset_table, portfolio, news_items),
        public_mode=is_public_mode(app_mode),
    )


def build_markdown_market_rows(asset_table: pd.DataFrame) -> list[dict]:
    """Build core market rows for Markdown."""

    symbols = ["QQQ", "SMH", "SOXX", "GLD", "SPY", "UUP", "TLT", "GC=F"]
    rows = []
    market_data = load_chart_market_data(symbols, "1y")
    for symbol in symbols:
        row = risk_row_from_asset_table(asset_table, [symbol])
        frame = market_data.get(symbol)
        latest = None
        if not is_empty_chart_frame(frame):
            enriched = add_chart_indicators(frame).dropna(subset=["Close"])
            if not enriched.empty:
                latest = enriched.iloc[-1]
        rows.append(
            {
                "资产": symbol,
                "今日涨跌": format_percent_plain(float(latest.get("TodayReturn")) if latest is not None and pd.notna(latest.get("TodayReturn")) else row_float(row, "今日涨跌幅数值")),
                "RSI": format_number_plain(float(latest.get("RSI14")) if latest is not None and pd.notna(latest.get("RSI14")) else row_float(row, "RSI数值")),
                "距离高点回撤": format_percent_plain(float(latest.get("Drawdown")) if latest is not None and pd.notna(latest.get("Drawdown")) else row_float(row, "当前回撤数值")),
                "1月收益": format_period_return(calculate_period_return(frame, "1m")),
                "3月收益": format_period_return(calculate_period_return(frame, "3m")),
                "数据质量": "fresh" if latest is not None else "missing",
            }
        )
    return rows


def build_markdown_fund_rows(portfolio: dict, final_decision: dict, app_mode: dict) -> list[dict]:
    """Build amount-free fund rows for Markdown."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        return []
    proxy_symbols = sorted({symbol for _, fund in funds.iterrows() for symbol in fund_proxy_basket(fund)})
    proxy_data = load_chart_market_data(proxy_symbols, "1y") if proxy_symbols else {}
    nav_cache = load_or_fetch_fund_navs(funds)
    trade_rules = load_fund_trade_rules()
    table = build_fund_monitor_table(funds, proxy_data, nav_cache, trade_rules, final_decision, app_mode)
    rows = []
    for _, item in table.iterrows():
        rows.append(
            {
                "基金名称": item.get("基金名称", "N/A"),
                "基金代码": item.get("基金代码", "N/A"),
                "主题": item.get("theme", "N/A"),
                "最新净值日期": item.get("nav_date", "N/A") or "N/A",
                "最新单位净值": format_number_plain(item.get("nav")),
                "基金真实日涨跌幅": format_percent_plain(item.get("daily_return")),
                "申购/限购状态": item.get("申购状态 / 限购状态", "N/A"),
                "数据质量": item.get("数据质量", "N/A"),
                "参考市场": item.get("参考市场", "N/A"),
            }
        )
    return rows


def build_markdown_news_rows(news_items: pd.DataFrame, app_mode: dict, final_decision: dict) -> list[dict]:
    """Build four-part news notes for Markdown."""

    if news_items.empty:
        return []
    rows = []
    ranked = rank_news_items(news_items).head(5)
    for _, item in ranked.iterrows():
        card = build_news_card(item, app_mode, final_decision)
        rows.append(
            {
                "标题": card.get("title", "N/A"),
                "来源": card.get("source_time", "N/A"),
                "新闻内容": card.get("content", "正文不可用，仅基于标题判断。"),
                "投资解读": card.get("interpretation", "N/A"),
                "对今日动作的影响": card.get("action", "不改变 final_decision，不生成买入金额。"),
                "后续观察点": card.get("watch_points", "N/A"),
                "新闻数据质量": card.get("data_quality", "N/A"),
            }
        )
    return rows


def build_markdown_theme_rows(
    portfolio: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    final_decision: dict,
    app_mode: dict,
) -> list[dict]:
    """Build theme observation rows for Markdown."""

    configs = theme_research_configs()
    symbols = sorted({symbol for config in configs for symbol in config.get("proxy_basket", []) if symbol != "DFII10"})
    theme_market_data = load_chart_market_data(symbols, "1y") if symbols else {}
    rows = []
    for config in configs:
        state = build_theme_research_state(config, portfolio, asset_table, news_items, app_mode, theme_market_data)
        funds = state.get("fund_mapping", [])
        rows.append(
            {
                "主题": state.get("name", "N/A"),
                "当前阶段": state.get("status", "N/A"),
                "核心驱动": "；".join(state.get("drivers", [])[:3]) or "N/A",
                "今日市场信号": state.get("signal", {}).get("summary", state.get("status", "N/A")) if isinstance(state.get("signal"), dict) else state.get("status", "N/A"),
                "相关公司": " / ".join(state.get("watchlist", [])[:8]) or "N/A",
                "相关基金": " / ".join([str(fund.get("基金", fund.get("fund_name", ""))) for fund in funds[:4]]) if isinstance(funds, list) else "N/A",
                "数据质量": state.get("signal", {}).get("data_quality", "N/A") if isinstance(state.get("signal"), dict) else "N/A",
                "后续观察点": theme_today_action_text(state, final_decision),
            }
        )
    return rows


def build_markdown_data_quality_summary(asset_table: pd.DataFrame, portfolio: dict, news_items: pd.DataFrame) -> str:
    """Build compact Markdown data quality summary."""

    market_status = "正常" if not asset_table.empty else "缺失"
    fund_status = "可读取组合基金列表" if portfolio.get("funds") else "缺失"
    news_status = "正常" if not news_items.empty else "缺失"
    confidence = "中" if market_status == "正常" else "低"
    return f"市场数据：{market_status}；基金净值：{fund_status}；新闻数据：{news_status}；今日结论置信度：{confidence}。"


def render_tactical_cash_page(final_decision: dict, app_mode: dict) -> None:
    """Render tactical cash usage page from final_decision only."""

    st.subheader("\u673a\u52a8\u8d44\u91d1\u4f7f\u7528\u5efa\u8bae")
    private_mode = is_private_mode(app_mode)
    if not private_mode:
        st.info(f"专业判断：是否使用灵活资金：{'是' if final_decision['use_tactical_cash'] else '否'}。Public 模式不展示金额。")
        st.write(mask_amounts_in_text(final_decision["cash_explanation"]))
        st.write("对我今天的动作：按系统纪律执行，不展示具体金额。")
        return
    if final_decision["use_tactical_cash"]:
        amount = f"\u00a5{final_decision['tactical_cash_amount']:,.0f}" if private_mode else "\u91d1\u989d\u5df2\u9690\u85cf"
        st.success(f"\u4e13\u4e1a\u5224\u65ad\uff1a\u662f\u5426\u4f7f\u7528\u673a\u52a8\u8d44\u91d1\uff1a\u662f\u3002\u5efa\u8bae\u91d1\u989d\uff1a{amount}")
        st.write(final_decision["cash_explanation"])
    else:
        st.info("\u4e13\u4e1a\u5224\u65ad\uff1a\u662f\u5426\u4f7f\u7528\u673a\u52a8\u8d44\u91d1\uff1a\u5426")
        st.write("\u4eca\u65e5\u4e0d\u52a8\u7528\u673a\u52a8\u8d44\u91d1")
        st.write("\u5efa\u8bae\u4f7f\u7528\u91d1\u989d\uff1a\u00a50")
        st.write("\u539f\u56e0\uff1a\u77ed\u7ebf\u504f\u70ed\uff0c\u57fa\u7840\u5b9a\u6295\u7ee7\u7eed\uff0c\u4f46\u4e0d\u52a0\u901f\u3001\u4e0d\u52a8\u7528\u7075\u6d3b\u8d44\u91d1\u3002" if decision_risk_discipline_code(final_decision) == "do_not_chase" else final_decision["cash_explanation"])
        st.write("\u4eba\u8bdd\u89e3\u91ca\uff1a\u8fd9\u7b14\u94b1\u7559\u7ed9\u5927\u56de\u64a4\u6216\u9ad8\u8d54\u7387\u673a\u4f1a\uff0c\u4eca\u5929\u4e0d\u52a8\u7528\u3002")
        st.write(f"\u5bf9\u6211\u4eca\u5929\u7684\u52a8\u4f5c\uff1a\u7ef4\u6301\u57fa\u7840\u5b9a\u6295 \u00a5{final_decision['daily_dca_amount']}\uff0c\u4e0d\u52a8\u7528\u7075\u6d3b\u8d44\u91d1\u3002")

    st.warning("\u673a\u52a8\u8d44\u91d1\u53ea\u8bfb\u53d6 final_decision\uff1b\u65e7\u5f15\u64ce\u6a21\u5f0f\u3001\u65b0\u95fb\u5c0f\u52a0\u901f\u6807\u7b7e\u6216\u65e5\u62a5\u65e7\u91d1\u989d\u4e0d\u80fd\u8986\u76d6\u6700\u7ec8\u663e\u793a\u3002")


def render_final_decision_plain_language(final_decision: dict, app_mode: dict) -> None:
    """Render plain-language cards aligned with final_decision."""

    today_action = "按当前定投计划执行；不在本页生成具体买入金额。"
    if is_public_mode(app_mode):
        today_action = "按系统纪律执行，不展示具体金额。"

    cards = [
        {
            "专业判断": f"今日模式：{decision_market_mode(final_decision)}；今日纪律：{decision_risk_discipline_label(final_decision)}",
            "人话解释": final_decision["top_summary"],
            "对我今天的动作": public_text(today_action, app_mode),
        },
        {
            "专业判断": "金额口径：不由当前页面生成",
            "人话解释": "本页负责解释市场状态和风险纪律，具体执行由你按当前计划或外部分析维护。",
            "对我今天的动作": current_action_suggestion(decision_market_mode(final_decision), decision_risk_discipline_label(final_decision)),
        },
    ]
    for card in cards:
        st.markdown(
            f"""
            <div class="explain-card">
              <div><strong>专业判断：</strong>{html.escape(card['专业判断'])}</div>
              <div><strong>人话解释：</strong>{html.escape(card['人话解释'])}</div>
              <div><strong>对我今天的动作：</strong>{html.escape(card['对我今天的动作'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


TERM_EXPLANATIONS = {
    "QQQ": "纳斯达克100ETF，可代表美股科技股温度。",
    "SMH": "半导体ETF，可代表全球半导体龙头趋势。",
    "SOXX": "半导体ETF，可代表半导体板块趋势。",
    "RSI": "短线热度指标，超过70代表短线偏热。",
    "GLD": "黄金ETF，可代表黄金趋势。",
    "TLT": "长期美债ETF，可代表美债防守资产趋势。",
    "UUP": "美元指数ETF，可代表美元强弱。",
    "risk-on": "市场风险偏好较高。",
    "risk-off": "市场风险偏好较低。",
    "健康回踩": "短线回调但中长期趋势没有破坏。",
    "机动资金": "专门留给大机会的备用资金。",
    "防守缓冲": "用黄金/现金等降低组合波动。",
}


def render_plain_language_explanations(text: str, source: str, app_mode: dict | None = None) -> None:
    """Render plain-language explanations for professional terms."""

    explanations = build_plain_language_explanations(text, source)
    if not explanations:
        return

    st.markdown("#### 人话解释")
    for item in explanations:
        judgment = html.escape(item["judgment"])
        plain_text = mask_amounts_in_text(item["plain"]) if app_mode and is_public_mode(app_mode) else item["plain"]
        action_text = mask_amounts_in_text(item["action"]) if app_mode and is_public_mode(app_mode) else item["action"]
        plain = html.escape(plain_text)
        action = html.escape(action_text)
        st.markdown(
            f"""
            <div class="plain-explain-card">
              <div><strong>专业判断：</strong>{judgment}</div>
              <div><strong>人话解释：</strong>{plain}</div>
              <div><strong>对我今天的动作：</strong>{action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_plain_language_explanations(text: str, source: str) -> list[dict]:
    """Build professional judgment, plain explanation, and action rows."""

    candidates = extract_professional_judgment_lines(text)
    if not candidates:
        candidates = [text.strip()] if text.strip() else []

    explanations = []
    seen = set()
    for line in candidates:
        judgment = clean_markdown_line(line)
        if not judgment or judgment in seen:
            continue
        seen.add(judgment)

        matched_terms = [term for term in TERM_EXPLANATIONS if term in judgment]
        if not matched_terms and not contains_action_signal(judgment):
            continue

        explanations.append(
            {
                "judgment": judgment,
                "plain": explain_in_plain_chinese(judgment, matched_terms, source),
                "action": explain_today_action(judgment, source),
            }
        )
        if len(explanations) >= 6:
            break

    return explanations


def extract_professional_judgment_lines(text: str) -> list[str]:
    """Extract lines likely to contain investment jargon or action signals."""

    signals = list(TERM_EXPLANATIONS) + [
        "过热",
        "回踩",
        "回撤",
        "加速",
        "提高",
        "不追高",
        "动用",
        "小额补",
        "do_not_chase",
        "small_acceleration",
        "reduce_aggression",
        "wait_for_pullback",
        "maintain_dca",
        "watchlist_only",
    ]
    lines = []
    for raw_line in text.splitlines():
        line = clean_markdown_line(raw_line)
        if not line:
            continue
        if any(signal in line for signal in signals):
            lines.append(line)
    return lines


def clean_markdown_line(line: str) -> str:
    """Remove light Markdown markers from a report line."""

    cleaned = line.strip()
    cleaned = re.sub(r"^[-*]\s*", "", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("`", "")
    return cleaned.strip()


def contains_action_signal(text: str) -> bool:
    """Check whether text contains DCA action language."""

    return any(
        signal in text
        for signal in [
            "维持",
            "基础定投",
            "80",
            "100",
            "机动资金",
            "不追高",
            "等待回踩",
            "观察池",
            "降低进攻",
        ]
    )


def explain_in_plain_chinese(judgment: str, matched_terms: list[str], source: str) -> str:
    """Explain a professional judgment in plain Chinese."""

    text = judgment
    if "RSI" in text and ("70" in text or "过热" in text):
        return "纳指科技或半导体短线涨得偏热，继续上涨不代表现在追高的性价比好。"
    if any(term in text for term in ["QQQ", "SMH", "SOXX"]) and "健康回踩" in text:
        return "科技和半导体主线没有坏，只是短线降温，这类回踩比直线追高更适合观察加速。"
    if "risk-off" in text:
        return "市场风险偏好下降，高波动资产更容易一起回撤，此时重点是保护节奏和现金。"
    if "risk-on" in text:
        return "市场整体愿意承担风险，成长资产环境较顺，但仍要看短线是否过热。"
    if "GLD" in text or "黄金" in text:
        return "黄金主要是组合的防守缓冲，低仓位可以小额补，但不适合当成主攻方向追涨。"
    if "TLT" in text:
        return "长期美债如果也弱，说明传统防守资产没有很好地保护组合波动。"
    if "UUP" in text or "美元" in text:
        return "美元偏强通常会压制成长股估值，也可能影响 QDII 汇率和溢价风险。"
    if "机动资金" in text:
        return "这笔钱是留给大回撤或高赔率机会的，不应该被普通波动或情绪提前消耗。"
    if "防守缓冲" in text:
        return "组合里需要有黄金、现金等缓冲资产，避免科技方向波动时回撤太硬。"
    if "do_not_chase" in text:
        return "这代表短线不追高：主题可能仍好，但当前价格或情绪不适合临时加速。"
    if "small_acceleration" in text:
        return "这代表小幅加速观察：如果价格回踩健康，可以把日定投从60元提高到80–100元区间。"
    if "reduce_aggression" in text:
        return "这代表降低进攻：宏观或市场压力偏大，高波动资产暂时不要加速。"
    if "wait_for_pullback" in text:
        return "这代表等待回踩：方向可以继续看，但买点还不够舒服。"
    if "watchlist_only" in text:
        return "这代表只进观察池：先跟踪产业变化，不直接变成今天的定投动作。"
    if "maintain_dca" in text:
        return "这代表维持基础定投：没有足够理由加速，也没有必要停止计划。"

    term_text = "；".join(TERM_EXPLANATIONS[term] for term in matched_terms)
    if term_text:
        return f"{term_text} 放到今天的语境里看，重点是判断该维持基础定投、等待回踩，还是降低进攻。"
    if source == "news":
        return "新闻只说明情绪和基本面线索，不能单独决定今天加仓。"
    return "这条判断用于辅助今天定投节奏，不是自动买卖指令。"


def explain_today_action(judgment: str, source: str) -> str:
    """Translate a judgment into today's DCA action language."""

    text = judgment
    if "RSI" in text and ("70" in text or "过热" in text):
        return "按当前计划执行，不因为短线过热临时追高。"
    if "do_not_chase" in text or "不追高" in text:
        return "保持基础定投，不因为新闻或上涨情绪临时追高。"
    if "small_acceleration" in text or "提高到80" in text or "提高到 80" in text:
        return "可以观察是否提高节奏，但仍不自动交易，也不输出具体金额。"
    if "reduce_aggression" in text or "risk-off" in text or "降低进攻" in text:
        return "不提高高波动方向节奏，优先控制回撤。"
    if "wait_for_pullback" in text or "等待回踩" in text:
        return "继续等更舒服的回踩位置，不因为主题热门而提前加速。"
    if "watchlist_only" in text or "观察池" in text:
        return "只加入观察池，不直接变成今天的执行动作。"
    if "GLD" in text or "黄金" in text:
        return "黄金低仓位时只做小额防守补充，不追涨，不替代半导体/CPO主线。"
    if "机动资金" in text:
        return "备用资金不作为当前页面的核心执行字段。"
    if source == "news":
        return "新闻仅作为辅助，默认按当前计划执行，等价格和风险指标确认。"
    return "维持当前定投计划，手动复盘后再决定是否加速。"


def render_portfolio_structure_page(portfolio: dict, app_mode: dict) -> None:
    """Render current portfolio structure."""

    st.subheader("当前持仓结构")
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("未找到 config/portfolio.yaml。")
        return

    total_amount = funds["current_amount"].sum()
    if is_public_mode(app_mode):
        st.metric("当前记录持仓金额", mask_sensitive_value(total_amount))
        display = build_public_portfolio_view(funds)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption("Public 模式仅展示主题、风险等级和脱敏占比区间。")
        return

    st.metric("当前记录持仓金额", f"¥{total_amount:,.2f}")
    fig = px.pie(funds, names="fund_name", values="current_amount", hole=0.45)
    apply_dark_plotly_layout(fig)
    st.plotly_chart(fig, use_container_width=True, key="plotly_portfolio_structure_pie")
    st.dataframe(funds, use_container_width=True, hide_index=True)


def build_public_portfolio_view(funds: pd.DataFrame) -> pd.DataFrame:
    """Build a public-safe portfolio table."""

    display = funds.copy()
    total = display["current_amount"].sum() if "current_amount" in display.columns else 0
    if total and "current_amount" in display.columns:
        display["持仓占比区间"] = (display["current_amount"] / total).map(percent_range)
    else:
        display["持仓占比区间"] = "已隐藏"
    display["current_amount"] = mask_sensitive_value()
    columns = [
        column
        for column in ["fund_name", "fund_code", "theme", "risk_level", "role_in_portfolio", "持仓占比区间", "current_amount"]
        if column in display.columns
    ]
    return display[columns].rename(columns={"current_amount": "持仓金额"})


def render_fund_monitor_page(portfolio: dict, final_decision: dict, app_mode: dict) -> None:
    """Render daily monitor for the user's actual fund list."""

    st.subheader("我的基金每日表现 / Fund Monitor")
    st.caption("该页面只做基金层面的研究观察，不生成新的买入金额。最终动作仍读取 final_decision。")
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("未找到 portfolio.yaml 中的基金列表。")
        return
    if is_public_mode(app_mode):
        render_public_fund_monitor_page(funds, final_decision)
        return

    proxy_symbols = sorted({symbol for _, fund in funds.iterrows() for symbol in fund_proxy_basket(fund)})
    proxy_data = load_chart_market_data(proxy_symbols, "1y") if proxy_symbols else {}
    nav_cache = load_or_fetch_fund_navs(funds)
    trade_rules = load_yaml(FUND_TRADE_RULES_PATH).get("fund_trade_rules", {})
    monitor = build_fund_monitor_table(funds, proxy_data, nav_cache, trade_rules, final_decision, app_mode)
    render_fund_monitor_overview(monitor, final_decision)

    display = monitor.copy()
    if is_public_mode(app_mode):
        display["当前金额"] = mask_sensitive_value()
        display["当前组合占比"] = display["current_weight"].map(percent_range)
        display["偏离金额"] = "已隐藏"
    else:
        display["当前金额"] = display["current_amount"].map(lambda value: format_currency(value) if value is not None else "数据缺失 / 未匹配")
        display["当前组合占比"] = display["current_weight"].map(format_percent_plain)
        display["偏离金额"] = display["weight_gap_amount"].map(lambda value: format_currency(value) if value is not None else "数据缺失 / 未匹配")

    display["目标占比"] = display["target_weight"].map(format_percent_plain)
    display["偏离程度"] = display["weight_gap"].map(format_percent_plain)
    display["最新净值日期"] = display["nav_date"].map(format_nav_date)
    display["最新单位净值"] = display["nav"].map(format_nav_value)
    display["基金真实日涨跌幅"] = display["daily_return"].map(lambda value: format_percent_plain(value) if value is not None and pd.notna(value) else "N/A")
    display["参考市场今日涨跌"] = display["proxy_today_return"].map(lambda value: format_percent_plain(value) if value is not None and pd.notna(value) else "数据不足")
    display["参考市场 RSI"] = display["proxy_rsi"].map(lambda value: f"{value:.1f}" if value is not None and pd.notna(value) else "数据不足")
    display["数据质量"] = display["数据质量"].map(format_nav_quality_display)

    columns = [
        "基金名称",
        "基金代码",
        "当前金额",
        "当前组合占比",
        "目标占比",
        "偏离程度",
        "最新净值日期",
        "最新单位净值",
        "基金真实日涨跌幅",
        "申购状态 / 限购状态",
        "数据质量",
        "参考市场",
        "参考市场今日涨跌",
        "参考市场 RSI",
        "今日动作说明",
    ]
    st.dataframe(display[columns], use_container_width=True, hide_index=True)

    st.info("QDII 基金净值可能滞后 1 个交易日。页面以基金公司/天天基金已公布净值为准；参考市场仅用于理解方向，不等于基金当日真实涨跌。")

    if is_private_mode(app_mode):
        with st.expander("基金代码匹配调试", expanded=False):
            debug_columns = [
                "基金名称",
                "normalized_name",
                "fund_code_source",
                "基金代码",
                "是否成功获取净值",
                "数据质量",
            ]
            st.dataframe(monitor[[column for column in debug_columns if column in monitor.columns]], use_container_width=True, hide_index=True)
        with st.expander("基金净值接口调试信息", expanded=False):
            debug_columns = [
                "基金名称",
                "基金代码",
                "nav_date",
                "data_source",
                "数据质量",
                "error_message",
            ]
            st.dataframe(monitor[[column for column in debug_columns if column in monitor.columns]], use_container_width=True, hide_index=True)

    st.markdown("### 单基金详情")
    for _, row in monitor.iterrows():
        with st.expander(str(row["基金名称"]), expanded=False):
            render_fund_detail(row, proxy_data)


def render_public_fund_monitor_page(funds: pd.DataFrame, final_decision: dict) -> None:
    """Render public-safe fund NAV and reference-market monitor."""

    st.info("公网不展示真实持仓金额和账户数据；基金净值、日涨跌幅和申购状态属于公开数据，若接口可用则正常展示。参考市场仅用于理解方向，不等于基金真实涨跌。")
    proxy_symbols = sorted({symbol for _, fund in funds.iterrows() for symbol in fund_proxy_basket(fund)})
    proxy_data = load_chart_market_data(proxy_symbols, "1y") if proxy_symbols else {}
    nav_cache = load_or_fetch_fund_navs(funds)
    trade_rules = load_yaml(FUND_TRADE_RULES_PATH).get("fund_trade_rules", {})
    overview_rows = []
    rows = []
    for _, fund in funds.iterrows():
        basket = fund_proxy_basket(fund)
        signal = aggregate_fund_proxy_signal(basket, proxy_data)
        nav = find_fund_nav_record(fund, nav_cache)
        trade_rule = match_trade_rule(fund, trade_rules)
        data_quality = classify_fund_nav_quality(nav, signal)
        daily_return = parse_numeric_amount(nav.get("daily_return"))
        nav_value = parse_numeric_amount(nav.get("nav"))
        overview_rows.append({"基金名称": fund.get("fund_name", ""), "daily_return": daily_return, "data_quality": data_quality})
        rows.append(
            {
                "基金名称": fund.get("fund_name", ""),
                "基金代码": normalize_fund_code(fund.get("fund_code", "")) or normalize_fund_code(nav.get("fund_code", "")) or "基金代码缺失",
                "主题": fund.get("theme", ""),
                "目标占比": format_percent_plain(parse_numeric_amount(fund.get("target_weight"))),
                "最新净值日期": format_nav_date(nav.get("nav_date", "")),
                "最新单位净值": format_nav_value(nav_value),
                "基金真实日涨跌幅": format_percent_plain(daily_return) if daily_return is not None and pd.notna(daily_return) else "N/A",
                "申购状态 / 限购状态": public_trade_status(format_purchase_status(nav, trade_rule)),
                "参考市场": " / ".join(signal["used_symbols"]) if signal["used_symbols"] else "missing",
                "参考市场今日涨跌": format_percent_plain(signal["today_return"]) if signal["today_return"] is not None else "数据不足",
                "参考市场 RSI": f"{signal['rsi']:.1f}" if signal["rsi"] is not None else "数据不足",
                "数据质量": format_nav_quality_display(data_quality),
                "今日动作说明": "不生成买入金额；最终动作仍读取 final_decision。",
            }
        )
    render_public_fund_monitor_overview(pd.DataFrame(overview_rows))
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"当前 public 展示模式：{decision_market_mode(final_decision)} / {decision_risk_discipline_label(final_decision)}。不显示真实持仓金额、每日买入金额或账户数据。")


def render_public_fund_monitor_overview(monitor: pd.DataFrame) -> None:
    """Render public fund NAV overview without private amounts."""

    if monitor.empty:
        return
    valid = monitor.dropna(subset=["daily_return"]).copy()
    updated_count = int(len(valid))
    pending_count = int(len(monitor) - updated_count)
    average_return = valid["daily_return"].mean() if not valid.empty else None
    best = valid.loc[valid["daily_return"].idxmax(), "基金名称"] if not valid.empty else "N/A"
    worst = valid.loc[valid["daily_return"].idxmin(), "基金名称"] if not valid.empty else "N/A"
    cols = st.columns(5)
    cols[0].metric("已更新基金数量", updated_count)
    cols[1].metric("待更新基金数量", pending_count)
    cols[2].metric("今日基金平均涨跌", format_percent_plain(average_return) if average_return is not None else "N/A")
    cols[3].metric("今日涨幅最大基金", best)
    cols[4].metric("今日跌幅最大基金", worst)
    if pending_count:
        st.warning("部分基金净值尚未公布或接口不可用，暂不计算完整组合涨跌。")


def public_trade_status(status: str) -> str:
    """Hide purchase-limit amounts while keeping public buyability status."""

    text = str(status or "申购状态未知")
    text = re.sub(r"限购\s*[\d,.]+", "限购额度已隐藏", text)
    text = re.sub(r"单日限购\s*[\d,.]+", "单日限购额度已隐藏", text)
    return mask_amounts_in_text(text)


def load_or_fetch_fund_navs(funds: pd.DataFrame) -> pd.DataFrame:
    """Delegate real NAV loading/fetching to the provider layer."""

    return get_latest_fund_navs_for_funds(
        funds=funds,
        cache_path=FUND_NAV_CACHE_PATH,
        aliases_path=FUND_CODE_ALIASES_PATH,
    )


def build_fund_monitor_table(
    funds: pd.DataFrame,
    proxy_data: dict[str, pd.DataFrame],
    nav_cache: pd.DataFrame,
    trade_rules: dict,
    final_decision: dict,
    app_mode: dict,
) -> pd.DataFrame:
    """Build fund monitor rows from real NAV data and separate proxy references."""

    funds = funds.copy()
    funds["current_amount_numeric"] = pd.to_numeric(funds.get("current_amount", pd.Series(dtype=float)), errors="coerce")
    total_amount = funds["current_amount_numeric"].sum()
    rows = []
    for _, fund in funds.iterrows():
        amount = parse_numeric_amount(fund.get("current_amount"))
        current_weight = amount / total_amount if amount is not None and total_amount else None
        target_weight = parse_numeric_amount(fund.get("target_weight")) or 0.0
        weight_gap = current_weight - target_weight if current_weight is not None else None
        basket = fund_proxy_basket(fund)
        proxy_signal = aggregate_fund_proxy_signal(basket, proxy_data)
        nav = find_fund_nav_record(fund, nav_cache)
        trade_rule = match_trade_rule(fund, trade_rules)
        data_quality = classify_fund_nav_quality(nav, proxy_signal)
        action = fund_action_suggestion(final_decision, proxy_signal, weight_gap, fund, trade_rule, data_quality)
        rows.append(
            {
                "基金名称": fund.get("fund_name", ""),
                "基金代码": normalize_fund_code(fund.get("fund_code", "")) or normalize_fund_code(nav.get("fund_code", "")) or "基金代码缺失",
                "current_amount": amount,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "weight_gap": weight_gap,
                "weight_gap_amount": (weight_gap * total_amount) if weight_gap is not None and total_amount else None,
                "nav_date": nav.get("nav_date", ""),
                "nav": parse_numeric_amount(nav.get("nav")),
                "daily_return": parse_numeric_amount(nav.get("daily_return")),
                "申购状态 / 限购状态": format_purchase_status(nav, trade_rule),
                "参考市场": " / ".join(proxy_signal["used_symbols"]) if proxy_signal["used_symbols"] else "missing",
                "proxy_today_return": proxy_signal["today_return"],
                "proxy_rsi": proxy_signal["rsi"],
                "proxy_drawdown": proxy_signal["drawdown_from_high"],
                "数据质量": data_quality,
                "今日动作说明": action,
                "role_in_portfolio": fund.get("role_in_portfolio", ""),
                "theme": fund.get("theme", ""),
                "proxy_basket": basket,
                "missing_symbols": proxy_signal["missing_symbols"],
                "data_source": nav.get("data_source", ""),
                "error_message": nav.get("error_message", ""),
                "normalized_name": nav.get("normalized_name", normalize_fund_name(fund.get("fund_name", ""))),
                "fund_code_source": nav.get("fund_code_source", "missing"),
                "是否成功获取净值": "是" if data_quality not in {"missing_code", "missing_nav"} else "否",
            }
        )
    return pd.DataFrame(rows)


def find_fund_nav_record(fund: pd.Series, nav_cache: pd.DataFrame) -> dict:
    """Find one NAV record by normalized fund code."""

    code = normalize_fund_code(fund.get("fund_code", ""))
    name = str(fund.get("fund_name", ""))
    if nav_cache.empty:
        return {"data_quality": "missing_nav", "data_source": "missing_nav", "purchase_status": "未知", "error_message": "缓存缺失"}
    if code and "fund_code" in nav_cache.columns:
        matched = nav_cache.loc[nav_cache["fund_code"].astype(str).map(normalize_fund_code) == code]
        if not matched.empty:
            return matched.iloc[0].to_dict()
    if "fund_name" in nav_cache.columns:
        matched = nav_cache.loc[nav_cache["fund_name"].astype(str) == name]
        if not matched.empty:
            return matched.iloc[0].to_dict()
    if not code:
        return {"data_quality": "missing_code", "data_source": "missing_nav", "purchase_status": "基金代码缺失", "error_message": "基金代码缺失"}
    return {"fund_code": code, "data_quality": "missing_nav", "data_source": "missing_nav", "purchase_status": "未知", "error_message": "缓存缺失"}


def classify_fund_nav_quality(nav: dict, proxy_signal: dict) -> str:
    """Classify real NAV freshness; proxy data never fills fund return."""

    if not nav:
        return "missing_nav"
    quality = str(nav.get("data_quality", "") or "")
    if quality:
        return quality
    detail = dq_fund_nav_quality(nav)
    status = detail["status"]
    if status == "missing":
        return "missing_nav"
    if status == "manual":
        return "manual_nav"
    if status == "stale":
        return "nav_pending"
    return status


def format_nav_quality_display(value) -> str:
    """Display fund NAV quality while preserving important NAV-specific causes."""

    raw = str(value or "").strip()
    labels = {
        "missing_code": "缺失｜基金代码缺失",
        "missing_nav": "缺失｜真实净值缺失",
        "nav_pending": "注意｜净值待更新",
        "manual_nav": "注意｜手动录入",
        "stale_cache": "注意｜缓存滞后",
        "cache": "注意｜使用缓存",
        "fresh": "OK｜数据正常",
    }
    return labels.get(raw, format_data_quality_badge(raw))


def match_trade_rule(fund: pd.Series, trade_rules: dict) -> dict:
    """Match manual trade rule by fund alias."""

    for alias, rule in trade_rules.items():
        if match_fund_by_alias(pd.DataFrame([fund.to_dict()]), alias) is not None:
            return rule or {}
    return {}


def format_purchase_status(nav: dict, trade_rule: dict) -> str:
    """Combine NAV purchase status and manual trade restrictions."""

    if str(nav.get("data_quality", "")) == "missing_code":
        return "基金代码缺失，无法获取真实净值"
    if trade_rule:
        if not bool(trade_rule.get("buyable", True)):
            return f"交易受限：{trade_rule.get('note', '当前不可购买')}"
        limit = trade_rule.get("daily_limit")
        if limit not in {None, "", "null"}:
            return f"可申购，限购 {limit}；{trade_rule.get('note', '')}".strip("；")
    raw_status = nav.get("purchase_status", "")
    status = "" if raw_status is None or pd.isna(raw_status) else str(raw_status)
    return status or "申购状态未知"


def format_nav_value(value) -> str:
    """Format fund NAV value."""

    amount = parse_numeric_amount(value)
    return "N/A" if amount is None else f"{amount:.4f}"


def format_nav_date(value) -> str:
    """Format NAV date with pending fallback."""

    if value is None or pd.isna(value):
        return "基金净值待更新"
    text = str(value).strip()
    return text if text else "基金净值待更新"


def render_fund_detail(row: pd.Series, proxy_data: dict[str, pd.DataFrame]) -> None:
    """Render one fund detail expander."""

    st.write(f"基金角色：{row.get('role_in_portfolio', '')}")
    st.write(f"主题：{row.get('theme', '')}")
    st.write(f"proxy_basket：{' / '.join(row.get('proxy_basket', []))}")
    st.write(f"缺失 proxy：{' / '.join(row.get('missing_symbols', [])) or '无'}")
    period_rows = []
    for symbol in row.get("proxy_basket", []):
        frame = proxy_data.get(symbol)
        period_rows.append(
            {
                "参考市场": symbol,
                "1月": format_period_return(calculate_period_return(frame, "1个月")),
                "3月": format_period_return(calculate_period_return(frame, "3个月")),
                "6月": format_period_return(calculate_period_return(frame, "6个月")),
                "YTD": format_period_return(calculate_period_return(frame, "YTD")),
                "1年": format_period_return(calculate_period_return(frame, "1年")),
            }
        )
    if period_rows:
        st.dataframe(pd.DataFrame(period_rows), use_container_width=True, hide_index=True)
    st.write(f"与目标仓位偏离：{format_percent_plain(row.get('weight_gap'))}")
    st.write(
        f"今日解释：该基金主要映射到 {row.get('theme', '')}。基金真实日涨跌为 {format_percent_plain(row.get('daily_return'))}；"
        f"参考市场 {row.get('参考市场', 'proxy')} 今日表现为 {format_percent_plain(row.get('proxy_today_return'))}。"
        "参考市场只用于理解方向，不等于基金当日真实涨跌。"
    )


def render_fund_monitor_overview(monitor: pd.DataFrame, final_decision: dict) -> None:
    """Render top cards for fund monitor."""

    valid = monitor.dropna(subset=["daily_return", "current_weight", "nav_date"]).copy()
    valid_dates = valid["nav_date"].astype(str).str.strip()
    all_same_nav_date = not valid.empty and valid_dates.nunique() == 1 and len(valid) == len(monitor)
    if all_same_nav_date:
        portfolio_return = float((valid["daily_return"] * valid["current_weight"]).sum())
        portfolio_text = format_percent_plain(portfolio_return)
    else:
        portfolio_text = "真实净值尚未完全公布"
    updated_count = int(valid["daily_return"].notna().sum())
    pending_count = int(len(monitor) - updated_count)
    cache_count = int(monitor["数据质量"].isin(["cache", "stale_cache"]).sum())
    missing_code_count = int((monitor["数据质量"] == "missing_code").sum())
    latest_nav_date = latest_nav_date_text(monitor)
    proxy_direction = infer_proxy_market_direction(monitor)
    quality = fund_monitor_quality_text(monitor)

    cols = st.columns(6)
    cols[0].metric("已公布基金净值组合涨跌", portfolio_text)
    cols[1].metric("已更新 / 待更新", f"{updated_count} / {pending_count}")
    cols[2].metric("使用缓存 / 缺失代码", f"{cache_count} / {missing_code_count}")
    cols[3].metric("最新净值日期", latest_nav_date)
    cols[4].metric("参考市场方向", proxy_direction)
    cols[5].metric("今日纪律", f"{decision_market_mode(final_decision)} / {decision_risk_discipline_label(final_decision)}")
    st.caption(f"数据质量：{quality}")
    if pending_count:
        st.warning("今日基金真实净值尚未完全公布，暂不计算完整真实组合涨跌。")


def latest_nav_date_text(monitor: pd.DataFrame) -> str:
    """Return latest published NAV date text."""

    dates = pd.to_datetime(monitor.get("nav_date", pd.Series(dtype=str)), errors="coerce").dropna()
    if dates.empty:
        return "暂无"
    return dates.max().strftime("%Y-%m-%d")


def infer_proxy_market_direction(monitor: pd.DataFrame) -> str:
    """Infer broad reference-market direction from proxy columns."""

    text = " / ".join(monitor.get("参考市场", pd.Series(dtype=str)).astype(str).tolist())
    returns = pd.to_numeric(monitor.get("proxy_today_return", pd.Series(dtype=float)), errors="coerce")
    avg_return = returns.dropna().mean() if not returns.dropna().empty else None
    if avg_return is None:
        return "数据不足"
    if avg_return > 0.005:
        return "参考市场偏强"
    if avg_return < -0.005:
        return "参考市场偏弱"
    return "参考市场震荡"


def fund_monitor_quality_text(monitor: pd.DataFrame) -> str:
    """Summarize fund monitor data quality."""

    qualities = set(monitor.get("数据质量", pd.Series(dtype=str)).astype(str))
    if qualities == {"fresh"}:
        return "真实净值"
    if "cache" in qualities or "stale_cache" in qualities:
        return "缓存 / 部分真实"
    if "fresh" in qualities and ("stale" in qualities or "nav_pending" in qualities):
        return "净值滞后 / 部分真实"
    if "missing_nav" in qualities or "missing_code" in qualities:
        return "部分缺失"
    return "净值滞后"


def fund_action_suggestion(final_decision: dict, proxy_signal: dict, weight_gap: float | None, fund: pd.Series, trade_rule: dict, data_quality: str) -> str:
    """Return fund-level action language without creating amounts."""

    mode = final_decision.get("market_mode", "normal_dca")
    if decision_risk_discipline_code(final_decision) == "do_not_chase":
        return "按当前计划执行，不追高"
    if trade_rule and not bool(trade_rule.get("buyable", True)):
        return "交易受限；同主题承接需回到每日定投决策页执行"
    if data_quality in {"missing_nav", "missing_code", "nav_pending"}:
        return "基金净值待更新，仅观察参考市场"
    if mode == "defense_mode":
        return "暂停新增或仅观察，控制高波动风险"
    rsi = proxy_signal.get("rsi")
    drawdown = proxy_signal.get("drawdown_from_high")
    if rsi is not None and rsi > 70:
        return "等回踩"
    if drawdown is not None and -0.10 <= drawdown <= -0.05 and rsi is not None and 45 <= rsi <= 60:
        return "可小额承接"
    if weight_gap is not None and weight_gap > 0.03:
        return "暂停新增"
    return "维持基础定投"


def fund_proxy_basket(fund: pd.Series) -> list[str]:
    """Return reference-market basket for one fund; never use it as fund NAV."""

    text = normalize_fund_name(" ".join(str(fund.get(column, "")) for column in ["fund_name", "theme", "role_in_portfolio", "proxy_symbol"]))
    if "黄金" in text or "gld" in text:
        return ["GLD", "GC=F"]
    if "标普" in text or "sp500" in text or "spy" in text:
        return ["SPY"]
    if "日经" in text or "ewj" in text:
        return ["EWJ", "513880.SS"]
    if "浦银" in text or "智能科技" in text:
        return ["SMH", "SOXX", "QQQ"]
    if "国富" in text or "科技互联" in text:
        return ["QQQ", "SMH", "SOXX"]
    if "全球成长" in text:
        return ["QQQ", "ACWI"]
    if "纳斯达克100" in text or "纳指100" in text or "qqq" in text:
        return ["QQQ"]
    proxy = str(fund.get("proxy_symbol", "")).strip()
    return [proxy] if proxy else []


def aggregate_fund_proxy_signal(symbols: list[str], proxy_data: dict[str, pd.DataFrame]) -> dict:
    """Aggregate reference-market return/RSI/drawdown for one fund."""

    signals = []
    missing = []
    for symbol in symbols:
        signal = fund_symbol_signal(symbol, proxy_data.get(symbol))
        if signal:
            signals.append(signal)
        else:
            missing.append(symbol)
    if not signals:
        return {"today_return": None, "rsi": None, "drawdown_from_high": None, "used_symbols": [], "missing_symbols": symbols, "data_quality": "missing"}
    return {
        "today_return": average_or_none([item["today_return"] for item in signals if item["today_return"] is not None]),
        "rsi": average_or_none([item["rsi"] for item in signals if item["rsi"] is not None]),
        "drawdown_from_high": average_or_none([item["drawdown_from_high"] for item in signals if item["drawdown_from_high"] is not None]),
        "used_symbols": [item["symbol"] for item in signals],
        "missing_symbols": missing,
        "data_quality": "reference_market" if not missing else "partial_reference_market",
    }


def fund_symbol_signal(symbol: str, frame: pd.DataFrame | None) -> dict | None:
    """Build one reference-market signal for Fund Monitor."""

    if is_empty_chart_frame(frame):
        return None
    enriched = add_chart_indicators(frame)
    close = pd.to_numeric(enriched["Close"], errors="coerce").dropna()
    if close.empty:
        return None
    latest = enriched.dropna(subset=["Close"]).iloc[-1]
    today_return = float(close.iloc[-1] / close.iloc[-2] - 1) if len(close) >= 2 and close.iloc[-2] else None
    return {
        "symbol": symbol,
        "today_return": today_return,
        "rsi": none_if_na(latest.get("RSI14")),
        "drawdown_from_high": none_if_na(latest.get("drawdown")),
    }

def percent_range(value: float) -> str:
    """Convert a percentage into a coarse public-safe range."""

    if value is None or pd.isna(value):
        return "已隐藏"
    percent = max(float(value) * 100, 0)
    lower = int(percent // 10) * 10
    upper = lower + 10
    if percent < 1:
        return "0%–1%"
    if upper > 100:
        upper = 100
    return f"{lower}%–{upper}%"


def render_theme_exposure_page(portfolio: dict, app_mode: dict) -> None:
    """Render theme exposure page."""

    st.subheader("主题暴露分析")
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("未找到组合配置。")
        return

    exposure = funds.groupby("theme", as_index=False)["current_amount"].sum()
    total = exposure["current_amount"].sum()
    exposure["weight"] = exposure["current_amount"] / total if total else 0
    if is_public_mode(app_mode):
        public_exposure = exposure[["theme", "weight"]].copy()
        public_exposure["weight_range"] = public_exposure["weight"].map(percent_range)
        st.dataframe(public_exposure[["theme", "weight_range"]], use_container_width=True, hide_index=True)
        st.caption("Public 模式仅展示主题暴露区间，不展示真实金额和精确占比。")
        return

    fig = px.bar(exposure, x="theme", y="weight", text=exposure["weight"].map(lambda value: f"{value:.1%}"))
    apply_dark_plotly_layout(fig)
    fig.update_layout(yaxis_tickformat=".0%", height=360)
    st.plotly_chart(fig, use_container_width=True, key="plotly_theme_exposure_bar")
    st.dataframe(exposure, use_container_width=True, hide_index=True)


def render_portfolio_xray_page(portfolio: dict, app_mode: dict) -> None:
    """Render approximate portfolio X-Ray by investment modules."""

    st.subheader("组合 X-Ray")
    st.caption("按 fund theme、proxy_symbol 和 role_in_portfolio 做近似穿透，不代表真实前十大持仓穿透。页面只做研究观察，不生成买入金额。")

    xray = build_portfolio_xray(portfolio)
    if xray.empty:
        st.warning("未找到可分析的 portfolio.yaml 持仓配置。")
        return

    private_mode = is_private_mode(app_mode)
    display = xray.copy()
    if private_mode:
        display["当前金额"] = display["amount"].map(lambda value: f"¥{value:,.2f}")
    display["当前占比"] = display["weight"].map(lambda value: f"{value:.2%}")
    display["目标/状态"] = display["target_label"]
    display["偏离提示"] = display["deviation_label"]
    columns = ["模块", "当前占比", "目标/状态", "偏离提示"]
    if private_mode:
        columns.insert(1, "当前金额")

    cols = st.columns([1, 1])
    with cols[0]:
        fig = px.pie(xray, names="模块", values="weight", hole=0.45)
        apply_dark_plotly_layout(fig)
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True, key=dashboard_plotly_key("portfolio_xray", "module_weight", "pie"))
    with cols[1]:
        target_rows = xray[xray["target_weight"].notna()]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=target_rows["模块"], y=target_rows["weight"], name="当前"))
        fig.add_trace(go.Bar(x=target_rows["模块"], y=target_rows["target_weight"], name="目标"))
        apply_dark_plotly_layout(fig)
        fig.update_layout(barmode="group", height=360, yaxis_tickformat=".0%", margin=dict(l=10, r=10, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True, key=dashboard_plotly_key("portfolio_xray", "current_vs_target", "bar"))

    st.dataframe(display[columns], use_container_width=True, hide_index=True)

    low_modules = xray[(xray["target_weight"].notna()) & (xray["deviation"] < -0.02)]["模块"].astype(str).tolist()
    high_modules = xray[(xray["target_weight"].notna()) & (xray["deviation"] > 0.02)]["模块"].astype(str).tolist()
    priority = low_modules[0] if low_modules else "暂无明显低配模块"
    st.markdown("#### 偏离提示")
    st.write(f"低于目标：{format_list_text(low_modules)}")
    st.write(f"高于目标：{format_list_text(high_modules)}")
    st.write(f"今天新增资金优先观察方向：{priority}。这只是模块偏离提示，不生成买入金额。")

    overlap = build_overlap_warning(portfolio)
    if overlap:
        st.warning(overlap)


def build_portfolio_xray(portfolio: dict) -> pd.DataFrame:
    """Build module-level approximate exposure from local portfolio config."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "current_amount" not in funds.columns:
        return pd.DataFrame()
    funds = funds.copy()
    funds["current_amount"] = pd.to_numeric(funds["current_amount"], errors="coerce").fillna(0)
    total = funds["current_amount"].sum()
    if total <= 0:
        return pd.DataFrame()
    funds["模块"] = funds.apply(classify_xray_module, axis=1)
    grouped = funds.groupby("模块", as_index=False)["current_amount"].sum().rename(columns={"current_amount": "amount"})
    order = ["纳指科技核心", "半导体 / CPO / CPU / AI算力", "黄金", "标普500", "日经225", "其他"]
    grouped["模块"] = pd.Categorical(grouped["模块"], categories=order, ordered=True)
    grouped = grouped.sort_values("模块").reset_index(drop=True)
    grouped["weight"] = grouped["amount"] / total
    targets = {"纳指科技核心": 0.37, "半导体 / CPO / CPU / AI算力": 0.53, "黄金": 0.10}
    grouped["target_weight"] = grouped["模块"].astype(str).map(targets)
    grouped["target_label"] = grouped.apply(format_xray_target, axis=1)
    grouped["deviation"] = grouped.apply(lambda row: row["weight"] - row["target_weight"] if pd.notna(row["target_weight"]) else pd.NA, axis=1)
    grouped["deviation_label"] = grouped.apply(format_xray_deviation, axis=1)
    return grouped


def classify_xray_module(fund: pd.Series) -> str:
    """Classify one fund into an approximate investment module."""

    text = " ".join(str(fund.get(column, "")) for column in ["fund_name", "theme", "role_in_portfolio", "proxy_symbol"]).lower()
    if "黄金" in text or "gld" in text:
        return "黄金"
    if "日经" in text or "japan" in text or "ewj" in text:
        return "日经225"
    if "标普" in text or "sp500" in text or "s&p" in text or "spy" in text:
        return "标普500"
    if any(keyword.lower() in text for keyword in ["半导体", "cpo", "cpu", "ai", "算力", "智能科技", "soxx", "smh"]):
        return "半导体 / CPO / CPU / AI算力"
    if any(keyword.lower() in text for keyword in ["纳斯达克", "纳指", "qqq", "全球成长", "科技成长"]):
        return "纳指科技核心"
    return "其他"


def format_xray_target(row: pd.Series) -> str:
    """Format module target text."""

    module = str(row["模块"])
    if module == "标普500":
        return "暂停新增"
    if module == "日经225":
        return "暂停观察"
    target = row.get("target_weight")
    if pd.isna(target):
        return "无固定目标"
    return f"{target:.0%}"


def format_xray_deviation(row: pd.Series) -> str:
    """Format module deviation text."""

    target = row.get("target_weight")
    if pd.isna(target):
        return "观察"
    deviation = row["weight"] - target
    if deviation < -0.02:
        return f"低于目标 {abs(deviation):.2%}"
    if deviation > 0.02:
        return f"高于目标 {deviation:.2%}"
    return "接近目标"


def format_list_text(items: list[str]) -> str:
    """Format a list for display."""

    return "、".join(items) if items else "暂无"


def build_overlap_warning(portfolio: dict) -> str:
    """Warn when multiple funds likely overlap in tech/AI/semiconductor exposure."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        return ""
    text_columns = [column for column in ["fund_name", "theme", "role_in_portfolio", "proxy_symbol"] if column in funds.columns]
    if not text_columns:
        return ""
    combined = funds[text_columns].fillna("").agg(" ".join, axis=1).str.lower()
    overlap_mask = combined.str.contains("科技|ai|半导体|cpo|cpu|qqq|soxx|smh|纳指|智能科技", regex=True)
    overlap_count = int(overlap_mask.sum())
    if overlap_count >= 3:
        return f"基金重叠提醒：当前有 {overlap_count} 只基金可能集中在科技 / AI / 半导体方向，底层持仓可能高度重叠。此处为近似分析，后续可接入真实前十大持仓穿透。"
    return ""


def render_theme_research_page(
    portfolio: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    final_decision: dict,
    app_mode: dict,
) -> None:
    """Render systematic Clayton Theme Research page."""

    st.subheader("行业研究 / Clayton Theme Research")
    st.caption("行业研究只判断主线、产业链机会、基金映射和观察池；不生成买入金额，最终金额仍由 final_decision 决定。")
    if news_items.empty:
        if is_public_mode(app_mode):
            st.info("当前使用公开市场数据 + 默认行业框架；新闻源暂不可用时，不影响 final_decision。")
        else:
            st.warning("新闻数据不足，使用市场数据和默认框架。")
    elif is_public_mode(app_mode):
        st.info("当前使用公开市场数据 + 公开 RSS 新闻源增强主题状态；新闻不覆盖 final_decision，不生成买入金额。")
    if asset_table.empty:
        st.warning("市场数据暂不可用，主题状态会更偏保守。")

    configs = theme_research_configs()
    proxy_symbols = sorted({symbol for config in configs for symbol in config.get("proxy_basket", [])})
    theme_market_data = load_chart_market_data(proxy_symbols, "1y") if proxy_symbols else {}
    states = [build_theme_research_state(config, portfolio, asset_table, news_items, app_mode, theme_market_data) for config in configs]
    render_theme_research_overview(states, final_decision, app_mode)

    strongest_name = max(states, key=lambda item: item["average_score"])["name"] if states else ""
    for state in states:
        expanded = state["name"] == strongest_name or state["status"] in {"过热不追", "防守观察"}
        with st.expander(f"{state['name']}｜{state['status']}｜综合 {state['average_score']:.1f}/5", expanded=expanded):
            render_theme_research_card(state, final_decision, app_mode)
    if is_private_mode(app_mode):
        with st.expander("基金映射调试信息", expanded=False):
            st.dataframe(build_fund_mapping_debug(portfolio, configs), use_container_width=True, hide_index=True)


def theme_research_configs() -> list[dict]:
    """Return the supported research themes."""

    return [
        {
            "name": "半导体",
            "thesis": "半导体是AI算力、云资本开支和先进制造升级的核心载体，适合作为长期主线跟踪。",
            "drivers": ["AI芯片需求", "云厂商资本开支", "先进制程", "设备与封装瓶颈", "出口管制"],
            "indicators": ["SMH", "SOXX", "NVDA", "TSM", "AVGO", "AMD", "MU"],
            "chain": {"上游": "设备、EDA、晶圆代工", "中游": "GPU、ASIC、存储、封装", "下游": "云厂商、AI应用、服务器"},
            "funds": ["广发纳指100", "浦银全球智能科技", "国富全球科技互联", "易方达全球成长"],
            "watchlist": ["NVDA", "TSM", "AVGO", "AMD", "MU", "SMH", "SOXX"],
            "keywords": ["semiconductor", "chip", "nvidia", "tsmc", "broadcom", "amd", "asml", "gpu", "asic", "memory", "hbm"],
            "proxy_basket": ["SMH", "SOXX"],
        },
        {
            "name": "CPO / 光通信",
            "thesis": "AI数据中心带宽需求提升，光模块和CPO是算力集群扩张的重要瓶颈环节。",
            "drivers": ["800G/1.6T升级", "数据中心互联", "硅光", "网络芯片", "云资本开支"],
            "indicators": ["AVGO", "MRVL", "CRDO", "LITE", "COHR", "SMH"],
            "chain": {"上游": "光芯片、DSP、硅光材料", "中游": "光模块、CPO、交换芯片", "下游": "云厂商、AI集群"},
            "funds": ["国富全球科技互联", "浦银全球智能科技", "易方达全球成长"],
            "watchlist": ["AVGO", "MRVL", "CRDO", "LITE", "COHR", "CPO"],
            "keywords": ["cpo", "optical", "photonics", "transceiver", "800g", "1.6t", "interconnect", "broadcom", "marvell", "credo", "lumentum", "coherent"],
            "proxy_basket": ["AVGO", "MRVL", "CRDO", "LITE", "COHR", "SMH"],
        },
        {
            "name": "CPU / ASIC / AI芯片",
            "thesis": "AI训练和推理会带来GPU、ASIC、CPU协同升级，定制芯片是降本增效的重要方向。",
            "drivers": ["推理需求", "定制ASIC", "服务器CPU升级", "能耗优化", "供应链安全"],
            "indicators": ["AMD", "INTC", "ARM", "AVGO", "NVDA", "SMH"],
            "chain": {"上游": "IP、EDA、先进制程", "中游": "CPU、GPU、ASIC、封装", "下游": "云厂商、企业AI、边缘推理"},
            "funds": ["浦银全球智能科技", "国富全球科技互联", "易方达全球成长", "广发纳指100"],
            "watchlist": ["AMD", "INTC", "ARM", "AVGO", "NVDA", "SMH", "SOXX"],
            "keywords": ["cpu", "asic", "intel", "amd", "arm", "custom silicon", "tpu", "ai chip", "blackwell"],
            "proxy_basket": ["AMD", "INTC", "ARM", "AVGO", "NVDA", "SMH"],
        },
        {
            "name": "存储 / HBM",
            "thesis": "HBM和高端存储是AI服务器性能瓶颈之一，价格周期和供需紧张值得持续观察。",
            "drivers": ["HBM供给", "DRAM/NAND价格", "AI服务器配置升级", "产能分配", "库存周期"],
            "indicators": ["MU", "SK Hynix", "Samsung", "SOXX", "SMH"],
            "chain": {"上游": "设备、材料、封装", "中游": "DRAM、NAND、HBM", "下游": "GPU模组、AI服务器、云厂商"},
            "funds": ["浦银全球智能科技", "国富全球科技互联", "易方达全球成长"],
            "watchlist": ["MU", "SK Hynix", "Samsung", "HBM", "SMH", "SOXX"],
            "keywords": ["hbm", "dram", "nand", "micron", "sk hynix", "samsung", "memory"],
            "proxy_basket": ["MU", "SOXX", "SMH"],
        },
        {
            "name": "AI算力 / 数据中心",
            "thesis": "AI训练与推理需求推动数据中心资本开支，算力、网络、电力和散热共同构成长期基础设施主线。",
            "drivers": ["训练/推理需求", "云厂商CAPEX", "GPU供给", "数据中心建设", "散热和能耗"],
            "indicators": ["QQQ", "NVDA", "SMCI", "VRT", "AVGO", "ETN"],
            "chain": {"上游": "芯片、电力设备、散热", "中游": "服务器、网络、数据中心", "下游": "AI应用、云服务"},
            "funds": ["广发纳指100", "浦银全球智能科技", "国富全球科技互联", "易方达全球成长"],
            "watchlist": ["NVDA", "SMCI", "VRT", "AVGO", "ETN", "QQQ"],
            "keywords": ["nvidia", "gpu", "blackwell", "ai server", "data center", "inference", "training", "cuda"],
            "proxy_basket": ["NVDA", "SMCI", "VRT", "AVGO", "ETN", "QQQ"],
        },
        {
            "name": "SiC / GaN / 功率半导体",
            "thesis": "SiC/GaN服务于新能源车、电力电子和高效电源，是功率半导体升级方向，但周期波动较大。",
            "drivers": ["新能源车需求", "功率器件价格", "产能利用率", "工业电源", "技术替代"],
            "indicators": ["WOLF", "ON", "STM", "IFNNY"],
            "chain": {"上游": "衬底、外延、材料", "中游": "功率器件、模块", "下游": "EV逆变器、光伏、工业电源"},
            "funds": ["浦银全球智能科技", "国富全球科技互联"],
            "watchlist": ["WOLF", "ON", "STM", "IFNNY", "SiC", "GaN"],
            "keywords": ["sic", "silicon carbide", "gan", "power semiconductor", "wolfspeed", "wolf", "on semiconductor", "stmicro"],
            "proxy_basket": ["WOLF", "ON", "STM", "IFNNY", "SMH"],
        },
        {
            "name": "AI电力基础设施",
            "thesis": "AI数据中心扩张会放大电网、变压器、UPS、散热和电力工程需求，是AI主线的配套基础设施。",
            "drivers": ["数据中心用电", "电网扩容", "变压器供给", "UPS与散热", "工程建设周期"],
            "indicators": ["VRT", "ETN", "GEV", "PWR"],
            "chain": {"上游": "铜、变压器、功率器件", "中游": "UPS、散热、电力设备", "下游": "数据中心、电网工程"},
            "funds": ["广发纳指100", "易方达全球成长", "浦银全球智能科技"],
            "watchlist": ["VRT", "ETN", "GEV", "PWR", "AI电力基础设施"],
            "keywords": ["power grid", "data center power", "transformer", "ups", "cooling", "vertiv", "eaton", "ge vernova"],
            "proxy_basket": ["VRT", "ETN", "GEV", "PWR"],
        },
        {
            "name": "黄金 / 美元 / 实际利率",
            "thesis": "黄金是组合防守缓冲，主要受美元、实际利率、避险需求和央行购金影响，不是主攻仓。",
            "drivers": ["实际利率", "美元强弱", "避险需求", "央行购金", "通胀预期"],
            "indicators": ["GC=F", "GLD", "UUP", "TLT", "DFII10"],
            "chain": {"上游": "金矿、央行储备", "中游": "黄金期货、ETF", "下游": "防守配置、避险需求"},
            "funds": ["易方达黄金"],
            "watchlist": ["GC=F", "GLD", "UUP", "TLT", "DFII10"],
            "keywords": ["gold", "comex", "gld", "real yield", "dollar", "uup", "tlt", "dfii10"],
            "proxy_basket": ["GLD", "GC=F", "UUP", "TLT", "DFII10"],
        },
    ]


def build_theme_research_state(
    config: dict,
    portfolio: dict,
    asset_table: pd.DataFrame,
    news_items: pd.DataFrame,
    app_mode: dict,
    theme_market_data: dict[str, pd.DataFrame],
) -> dict:
    """Build current state and scores for one theme."""

    news_hits = match_theme_news(config, news_items)
    signal = aggregate_theme_market_signal(asset_table, theme_market_data, config.get("proxy_basket", []))
    status = classify_theme_status(config["name"], signal, news_hits)
    scores = score_theme(config, signal, news_hits, portfolio)
    average_score = sum(scores.values()) / len(scores)
    return {
        **config,
        "news_hits": news_hits,
        "signal": signal,
        "status": status,
        "scores": scores,
        "average_score": average_score,
        "fund_mapping": build_theme_fund_mapping(config, portfolio, app_mode),
    }


def match_theme_news(config: dict, news_items: pd.DataFrame) -> list[dict]:
    """Find news items matching a research theme by title, summary, and parsed themes."""

    if news_items.empty:
        return []
    keywords = [keyword.lower() for keyword in config.get("keywords", [])]
    matches = []
    for _, item in news_items.iterrows():
        title = str(item.get("title", ""))
        summary = str(item.get("summary", ""))
        themes = " ".join(parse_news_themes(item.get("themes", [])))
        text = f"{title} {summary} {themes}".lower()
        if any(keyword in text for keyword in keywords):
            matches.append(
                {
                    "title": title or "无标题新闻",
                    "source": str(item.get("source", "未知来源")),
                    "importance": pd.to_numeric(item.get("importance_score", 0), errors="coerce"),
                }
            )
    return matches


def aggregate_theme_market_signal(asset_table: pd.DataFrame, market_data: dict[str, pd.DataFrame], proxy_basket: list[str]) -> dict:
    """Aggregate independent proxy-basket signals for one theme."""

    signals = []
    used_symbols = []
    missing_symbols = []
    for symbol in proxy_basket:
        signal = theme_symbol_signal(symbol, asset_table, market_data)
        if signal:
            signals.append(signal)
            used_symbols.append(symbol)
        else:
            missing_symbols.append(symbol)

    fallback_reason = ""
    if not signals:
        fallback_signal = theme_symbol_signal("SMH", asset_table, market_data)
        if fallback_signal:
            signals.append(fallback_signal)
            used_symbols.append("SMH")
            fallback_reason = "当前主题状态暂用 SMH 作为半导体大类代理，不代表该主题独立 RSI。"
        else:
            theme_quality = dq_theme_quality([], proxy_basket, "")
            return {
                "status": "数据暂不可用",
                "rsi": None,
                "drawdown_from_high": None,
                "today_return": None,
                "drawdown": None,
                "risk_status": "data_unavailable",
                "used_symbols": [],
                "missing_symbols": proxy_basket,
                "fallback_reason": "",
                "theme_data_quality": theme_quality["status"],
                "theme_data_quality_label": format_data_quality_badge(theme_quality),
                "theme_data_quality_explanation": theme_quality["explanation"],
                "above_ma60": None,
            }
    elif used_symbols == ["SMH"] and len(proxy_basket) > 1:
        fallback_reason = "当前主题状态暂用 SMH 作为半导体大类代理，不代表该主题独立 RSI。"

    rsi_values = [signal["rsi"] for signal in signals if signal.get("rsi") is not None]
    drawdown_values = [signal["drawdown_from_high"] for signal in signals if signal.get("drawdown_from_high") is not None]
    today_values = [signal["today_return"] for signal in signals if signal.get("today_return") is not None]
    above_values = [signal["above_ma60"] for signal in signals if signal.get("above_ma60") is not None]
    statuses = [signal["risk_status"] for signal in signals if signal.get("risk_status")]
    theme_quality = dq_theme_quality(used_symbols, missing_symbols, fallback_reason)
    return {
        "status": "ok",
        "rsi": average_or_none(rsi_values),
        "drawdown_from_high": average_or_none(drawdown_values),
        "today_return": average_or_none(today_values),
        "drawdown": average_or_none(drawdown_values),
        "risk_status": "risk-off" if "risk-off" in statuses else ("risk-on" if "risk-on" in statuses else "neutral"),
        "used_symbols": used_symbols,
        "missing_symbols": missing_symbols,
        "fallback_reason": fallback_reason,
        "theme_data_quality": theme_quality["status"],
        "theme_data_quality_label": format_data_quality_badge(theme_quality),
        "theme_data_quality_explanation": theme_quality["explanation"],
        "above_ma60": all(above_values) if above_values else None,
    }


def theme_symbol_signal(symbol: str, asset_table: pd.DataFrame, market_data: dict[str, pd.DataFrame]) -> dict | None:
    """Build RSI/drawdown/today-return signal for one symbol from market data or report table."""

    frame = market_data.get(symbol)
    if not is_empty_chart_frame(frame):
        enriched = add_chart_indicators(frame)
        clean = enriched.dropna(subset=["Close"])
        if not clean.empty:
            latest = clean.iloc[-1]
            close = pd.to_numeric(clean["Close"], errors="coerce").dropna()
            today_return = float(close.iloc[-1] / close.iloc[-2] - 1) if len(close) >= 2 and close.iloc[-2] else None
            ma60 = latest.get("MA60")
            latest_close = latest.get("Close")
            market_signal = classify_market_signal(enriched)
            risk_status = "risk-off" if market_signal == "trend_break" else ("risk-on" if market_signal in {"overheat", "normal"} else "neutral")
            return {
                "symbol": symbol,
                "rsi": none_if_na(latest.get("RSI14")),
                "drawdown_from_high": none_if_na(latest.get("drawdown")),
                "today_return": today_return,
                "above_ma60": bool(latest_close >= ma60) if pd.notna(latest_close) and pd.notna(ma60) else None,
                "risk_status": risk_status,
                "source": frame.attrs.get("data_source", "market_data"),
            }

    row = risk_row_from_asset_table(asset_table, [symbol])
    if row is None:
        return None
    return {
        "symbol": symbol,
        "rsi": row_float(row, "RSI数值"),
        "drawdown_from_high": row_float(row, "当前回撤数值"),
        "today_return": row_float(row, "今日涨跌幅数值"),
        "above_ma60": infer_above_ma60(row),
        "risk_status": row_text(row, "风险状态") or "neutral",
        "source": "daily_report",
    }


def average_or_none(values: list[float]) -> float | None:
    """Return simple average for available proxy values."""

    clean = [float(value) for value in values if value is not None and pd.notna(value)]
    return sum(clean) / len(clean) if clean else None


def none_if_na(value) -> float | None:
    """Normalize pandas NA to None."""

    return None if value is None or pd.isna(value) else float(value)


def classify_theme_status(theme_name: str, signal: dict, news_hits: list[dict]) -> str:
    """Classify theme status without changing final_decision."""

    if "黄金" in theme_name:
        return "防守观察" if signal["status"] != "数据暂不可用" else "观察池"
    if signal["status"] == "数据暂不可用":
        return "观察池"
    rsi = signal.get("rsi")
    drawdown = signal.get("drawdown_from_high")
    risk_status = signal.get("risk_status")
    above_ma60 = signal.get("above_ma60")
    if rsi is not None and rsi > 70:
        return "过热不追"
    if risk_status == "risk-off":
        return "趋势走弱"
    if drawdown is not None and -0.10 <= drawdown <= -0.05 and rsi is not None and 45 <= rsi <= 60 and above_ma60 is not False:
        return "健康回踩"
    if risk_status == "risk-on" and news_hits:
        return "主线增强"
    return "观察池"


def score_theme(config: dict, signal: dict, news_hits: list[dict], portfolio: dict) -> dict[str, int]:
    """Score a theme from 1 to 5."""

    risk_status = signal.get("risk_status")
    rsi = signal.get("rsi")
    news_count = len(news_hits)
    industry_score = min(5, 3 + min(news_count, 2))
    trend_score = 1 if signal["status"] == "数据暂不可用" else {"risk-on": 5, "neutral": 3, "risk-off": 2}.get(risk_status, 3)
    valuation_score = 2 if rsi is not None and rsi > 70 else (4 if rsi is not None and 45 <= rsi <= 60 else 3)
    news_score = min(5, 2 + news_count) if news_count else 2
    match_score = min(5, 2 + len(build_theme_related_funds(config, portfolio)))
    return {
        "产业景气度": industry_score,
        "市场趋势": trend_score,
        "估值/拥挤度": valuation_score,
        "新闻质量": news_score,
        "我的组合匹配度": match_score,
    }


def build_theme_related_funds(config: dict, portfolio: dict) -> list[str]:
    """Return configured funds related to a theme."""

    target_names = config.get("funds", [])
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "fund_name" not in funds.columns:
        return target_names
    matched = []
    for target in target_names:
        row = match_fund_by_alias(funds, target)
        matched.append(target if row is None else str(row.get("fund_name", target)))
    return list(dict.fromkeys(matched))


def build_theme_fund_mapping(config: dict, portfolio: dict, app_mode: dict) -> pd.DataFrame:
    """Build public/private-safe fund mapping for a theme."""

    if is_public_mode(app_mode):
        return pd.DataFrame()
    funds = pd.DataFrame(portfolio.get("funds", []))
    related_names = config.get("funds", [])
    rows = []
    if funds.empty:
        return pd.DataFrame()
    amounts = pd.to_numeric(funds.get("current_amount", pd.Series(dtype=float)), errors="coerce")
    total = amounts.sum()
    for name in related_names:
        row = match_fund_by_alias(funds, name)
        item = {"基金": name, "相关度": "强相关" if name in config.get("funds", [])[:3] else "中等相关"}
        if row is None:
            item["匹配状态"] = "数据缺失 / 未匹配"
            item["当前金额"] = "数据缺失 / 未匹配"
            item["当前仓位"] = "数据缺失 / 未匹配"
        else:
            amount = parse_numeric_amount(row.get("current_amount"))
            weight = amount / total if amount is not None and total else None
            item["匹配状态"] = "已匹配"
            item["当前金额"] = format_currency(amount)
            item["当前仓位"] = format_percent_plain(weight)
        rows.append(item)
    return pd.DataFrame(rows)


def normalize_fund_name(value: str) -> str:
    """Normalize fund names for robust matching."""

    text = str(value or "").strip().lower()
    replacements = {
        "（": "(",
        "）": ")",
        " ": "",
        "\u3000": "",
        "-": "",
        "_": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def fund_aliases(short_name: str) -> list[str]:
    """Return matching aliases for configured fund short names."""

    aliases = {
        "广发纳指100": ["广发纳指100", "广发纳斯达克100", "纳斯达克100etf联接", "纳指100"],
        "浦银全球智能科技": ["浦银全球智能科技", "浦银安盛全球智能科技", "全球智能科技"],
        "国富全球科技互联": ["国富全球科技互联", "全球科技互联"],
        "易方达全球成长": ["易方达全球成长", "全球成长"],
        "易方达黄金": ["易方达黄金", "黄金etf联接", "000307"],
        "摩根标普500": ["摩根标普500", "标普500", "sp500"],
        "华安日经225": ["华安日经225", "日经225"],
    }
    return aliases.get(short_name, [short_name])


def match_fund_by_alias(funds: pd.DataFrame, short_name: str) -> pd.Series | None:
    """Match a fund by normalized aliases."""

    if funds.empty or "fund_name" not in funds.columns:
        return None
    normalized_aliases = [normalize_fund_name(alias) for alias in fund_aliases(short_name)]
    for _, fund in funds.iterrows():
        candidates = [
            normalize_fund_name(fund.get("fund_name", "")),
            normalize_fund_name(fund.get("fund_code", "")),
            normalize_fund_name(fund.get("theme", "")),
        ]
        if any(alias and any(alias in candidate for candidate in candidates) for alias in normalized_aliases):
            return fund
    return None


def parse_numeric_amount(value) -> float | None:
    """Parse current_amount without silently converting missing values to zero."""

    try:
        if value is None or pd.isna(value):
            return None
        return float(str(value).replace(",", "").replace("¥", "").strip())
    except (TypeError, ValueError):
        return None


def build_fund_mapping_debug(portfolio: dict, configs: list[dict]) -> pd.DataFrame:
    """Build private debug table for fund-name matching and weights."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        return pd.DataFrame()
    amounts = pd.to_numeric(funds.get("current_amount", pd.Series(dtype=float)), errors="coerce")
    total = amounts.sum()
    rows = []
    for _, fund in funds.iterrows():
        amount = parse_numeric_amount(fund.get("current_amount"))
        matched_themes = []
        for config in configs:
            for short_name in config.get("funds", []):
                matched = match_fund_by_alias(pd.DataFrame([fund.to_dict()]), short_name)
                if matched is not None:
                    matched_themes.append(config["name"])
                    break
        rows.append(
            {
                "原始基金名称": fund.get("fund_name", ""),
                "normalized_name": normalize_fund_name(fund.get("fund_name", "")),
                "current_amount": "数据缺失 / 未匹配" if amount is None else amount,
                "calculated_weight": "数据缺失 / 未匹配" if amount is None or not total else format_percent_plain(amount / total),
                "theme": fund.get("theme", ""),
                "role_in_portfolio": fund.get("role_in_portfolio", ""),
                "是否成功匹配到行业主题": "、".join(dict.fromkeys(matched_themes)) if matched_themes else "未匹配",
            }
        )
    return pd.DataFrame(rows)


def render_theme_research_overview(states: list[dict], final_decision: dict, app_mode: dict) -> None:
    """Render top overview for theme research."""

    if not states:
        st.info("暂无主题研究配置。")
        return
    strongest = max(states, key=lambda item: item["average_score"])
    wait_pullback = [item["name"] for item in states if item["status"] == "过热不追"]
    watchlist = [item["name"] for item in states if item["status"] == "观察池"]
    defense = [item["name"] for item in states if item["status"] == "防守观察"]
    cols = st.columns(5)
    cols[0].metric("当前最强主题", strongest["name"])
    cols[1].metric("等待回踩", format_list_text(wait_pullback))
    cols[2].metric("观察池主题", format_list_text(watchlist[:2]))
    cols[3].metric("当前防守主题", format_list_text(defense))
    cols[4].metric("是否改变 final_decision", "否")
    amount_text = f"¥{final_decision.get('daily_dca_amount', 60)}" if is_private_mode(app_mode) else "不展示金额"
    st.info(public_text(
        f"当前 final_decision 为 {decision_market_mode(final_decision)} / {decision_risk_discipline_label(final_decision)}，今日金额：{amount_text}。"
        "行业研究不能覆盖 do_not_chase / defense_mode，也不生成买入金额。"
    , app_mode))


def render_theme_research_card(state: dict, final_decision: dict, app_mode: dict) -> None:
    """Render one theme research card."""

    st.markdown(f"**一句话 thesis：** {state['thesis']}")
    cols = st.columns(3)
    cols[0].markdown("**核心驱动因素**\n\n" + " / ".join(state["drivers"]))
    cols[1].markdown("**关键观察指标**\n\n" + " / ".join(state["indicators"]))
    signal = state["signal"]
    cols[2].markdown(
        "**当前状态**\n\n"
        f"{state['status']}  \n"
        f"RSI：{format_theme_signal_value(signal.get('rsi'))}  \n"
        f"today_return：{format_theme_signal_value(signal.get('today_return'), percent=True)}  \n"
        f"drawdown_from_high：{format_theme_signal_value(signal.get('drawdown_from_high'), percent=True)}"
    )
    proxy_text = " / ".join(signal.get("used_symbols", [])) or "数据暂不可用"
    missing_text = " / ".join(signal.get("missing_symbols", [])) or "无"
    st.caption(f"数据代理：{proxy_text}")
    st.caption(f"缺失数据：{missing_text}")
    st.caption(f"主题数据质量：{signal.get('theme_data_quality_label', '注意｜部分可用')}")
    if signal.get("missing_symbols"):
        st.warning("部分主题数据不足，已使用可用 proxy 计算。")
    if signal.get("fallback_reason"):
        st.warning(signal["fallback_reason"])
    if signal.get("theme_data_quality") in {"partial", "proxy", "missing"}:
        st.info(f"置信度提示：{signal.get('theme_data_quality_explanation', '主题数据不完整，结论需降权参考。')}")
    if signal.get("today_return") is not None and signal.get("today_return") > 0 and signal.get("rsi") is not None and signal.get("rsi") > 70:
        st.info("当日上涨，但处于过热区，不属于健康回踩。")

    chain_rows = [{"环节": key, "内容": value} for key, value in state["chain"].items()]
    st.dataframe(pd.DataFrame(chain_rows), use_container_width=True, hide_index=True)

    score_df = pd.DataFrame([{"评分项": key, "分数": value} for key, value in state["scores"].items()])
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    if not state["fund_mapping"].empty:
        st.markdown("**我的基金映射**")
        st.dataframe(state["fund_mapping"], use_container_width=True, hide_index=True)
    elif is_private_mode(app_mode):
        st.caption("暂无明确基金映射。")

    st.markdown("**观察股票 / ETF**")
    st.write("、".join(state["watchlist"]))

    if state["news_hits"]:
        st.markdown("**相关新闻线索**")
        st.dataframe(pd.DataFrame(state["news_hits"]).head(5), use_container_width=True, hide_index=True)
    else:
        st.caption("新闻数据不足或暂无高相关资讯，使用默认研究框架。")

    st.markdown("**对今日动作的影响**")
    st.write(public_text(theme_today_action_text(state, final_decision), app_mode))


def format_theme_signal_value(value, percent: bool = False) -> str:
    """Format a signal value."""

    if value is None or pd.isna(value):
        return "数据暂不可用"
    return f"{value:.2%}" if percent else f"{value:.1f}"


def theme_today_action_text(state: dict, final_decision: dict) -> str:
    """Translate theme state into action language without creating amounts."""

    mode = final_decision.get("market_mode", "normal_dca")
    discipline = decision_risk_discipline_code(final_decision)
    if discipline == "do_not_chase":
        return "不改变今日动作；按当前计划执行。基础计划继续，但行业利好只作为方向确认，不触发加速。"
    if mode == "defense_mode":
        return "不改变今日动作；当前防守优先，行业利好不覆盖 defense_mode。"
    if state["status"] == "健康回踩":
        return "健康回踩时可作为观察依据，但本页不输出具体买入金额。"
    if state["status"] == "过热不追":
        return "当前过热，不追高；本页不输出具体买入金额。"
    if state["status"] == "防守观察":
        return "黄金/美元/实际利率只影响防守观察和两周黄金补仓节奏，不影响主攻仓金额。"
    if state["status"] == "趋势走弱":
        return "趋势走弱，作为风险提示；本页不输出具体买入金额。"
    return "只作为观察池和主线跟踪，不改变今日动作；本页不输出具体买入金额。"


def render_gold_progress_page(portfolio: dict, policy: dict, app_mode: dict) -> None:
    """Render gold allocation progress."""

    st.subheader("黄金仓位进度")
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        st.warning("未找到组合配置。")
        return

    total = funds["current_amount"].sum()
    gold_amount = funds.loc[funds["theme"] == "黄金", "current_amount"].sum()
    gold_weight = gold_amount / total if total else 0
    min_weight = float(policy.get("gold_target_weight_min", 0.06))
    max_weight = float(policy.get("gold_target_weight_max", 0.08))

    if is_public_mode(app_mode):
        if min_weight <= gold_weight <= max_weight:
            st.success("黄金仓位处于目标区间。")
        elif gold_weight < min_weight:
            st.info("黄金仓位低于目标区间，可作为防守缓冲观察。")
        else:
            st.warning("黄金仓位高于目标区间，适合暂停补仓观察。")
        st.caption("Public 模式仅展示是否达标，不展示真实金额和精确仓位。")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("黄金当前仓位", f"{gold_weight:.2%}")
    col2.metric("目标下限", f"{min_weight:.2%}")
    col3.metric("目标上限", f"{max_weight:.2%}")
    st.progress(min(max(gold_weight / max_weight, 0), 1))

    if gold_weight < min_weight:
        st.info("黄金低于 6%，仅适合小额分批补充防守缓冲。")
    elif gold_weight > max_weight:
        st.warning("黄金超过 8%，暂停补仓观察。")
    else:
        st.success("黄金处于目标仓位区间，维持防守缓冲观察。")


CHART_ASSETS = {
    "QQQ": "纳指100",
    "SMH": "半导体",
    "SOXX": "半导体辅助",
    "GLD": "黄金ETF",
    "GC=F": "COMEX Gold Futures",
    "SPY": "标普500",
    "UUP": "美元",
    "TLT": "长期美债",
}


def render_market_charts_page(
    portfolio: dict,
    app_mode: dict,
    asset_table: pd.DataFrame,
    news_csv: Path | None,
    latest_report: Path | None,
) -> None:
    """Render market charts, period returns, and relative strength."""

    st.subheader("市场图表与阶段收益")
    st.info("市场图表用于辅助判断，不直接触发买入。最终动作仍以 final_decision 为准。")

    full_data = load_chart_market_data(list(CHART_ASSETS.keys()), "5y")
    render_market_chart_conclusion(full_data)
    render_period_return_table(full_data)
    with st.expander("数据健康检查", expanded=False):
        render_data_health_check(full_data, asset_table, news_csv, latest_report)

    comparison_period_label = st.radio("归一化收益走势图周期", ["3个月", "6个月", "1年", "3年", "5年"], horizontal=True)
    comparison_assets = st.multiselect(
        "选择收益对比资产",
        options=list(CHART_ASSETS.keys()),
        default=["QQQ", "SMH", "GLD", "SPY"],
        format_func=lambda ticker: f"{ticker}：{CHART_ASSETS[ticker]}",
    )
    render_normalized_return_chart(full_data, comparison_assets, comparison_period_label)

    st.markdown("### K线与技术状态")
    period_label = st.radio("K线周期", ["3个月", "6个月", "1年", "3年", "5年"], horizontal=True)
    default_assets = list(CHART_ASSETS.keys())
    selected_assets = st.multiselect(
        "选择资产",
        options=list(CHART_ASSETS.keys()),
        default=default_assets,
        format_func=lambda ticker: f"{ticker}：{CHART_ASSETS[ticker]}",
    )

    if not selected_assets:
        st.info("请选择至少一个资产。")
        return

    market_data = {symbol: filter_chart_period(full_data.get(symbol, pd.DataFrame()), period_label) for symbol in selected_assets}
    render_chart_group("核心资产图表", ["QQQ", "SMH", "GLD"], market_data, portfolio, app_mode)
    render_relative_strength_chart("进攻观察：SMH/QQQ 相对强弱", "SMH", "QQQ", market_data, "进攻观察")
    render_relative_strength_chart("进攻观察：SOXX/QQQ 相对强弱", "SOXX", "QQQ", market_data, "进攻观察")
    render_chart_group("进攻观察", ["SOXX"], market_data, portfolio, app_mode)
    render_chart_group("防守观察", ["GLD", "GC=F", "UUP", "TLT"], market_data, portfolio, app_mode)
    render_relative_strength_chart("基准观察：QQQ/SPY 相对强弱", "QQQ", "SPY", market_data, "基准观察")
    render_relative_strength_chart("防守观察：GLD/SPY 相对强弱", "GLD", "SPY", market_data, "防守观察")
    render_chart_group("基准观察", ["SPY"], market_data, portfolio, app_mode)


def load_chart_market_data(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Load OHLC data from yfinance and fall back to local close-price cache."""

    data = load_public_ohlc_data(symbols, period)
    missing = [symbol for symbol, frame in data.items() if frame is None or frame.empty]
    if missing:
        fallback = load_price_cache_for_charts(missing)
        data.update({symbol: fallback.get(symbol, pd.DataFrame()) for symbol in missing})
    return data


def download_yahoo_chart_api(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Fallback to Yahoo Chart API when yfinance fails."""

    ranges = {"3mo": "3mo", "6mo": "6mo", "1y": "1y", "3y": "3y", "5y": "5y"}
    result = {symbol: pd.DataFrame() for symbol in symbols}
    for symbol in symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            response = requests.get(
                url,
                params={"range": ranges.get(period, period), "interval": "1d", "events": "history"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()["chart"]["result"][0]
            timestamps = pd.to_datetime(payload.get("timestamp", []), unit="s")
            quote = payload.get("indicators", {}).get("quote", [{}])[0]
            frame = pd.DataFrame(
                {
                    "Open": quote.get("open", []),
                    "High": quote.get("high", []),
                    "Low": quote.get("low", []),
                    "Close": quote.get("close", []),
                },
                index=timestamps,
            )
            normalized = normalize_ohlc_frame(frame)
            if not normalized.empty:
                normalized.attrs["data_source"] = "yahoo_chart_api"
            result[symbol] = normalized
        except Exception:
            result[symbol] = pd.DataFrame()
    return result


def normalize_ohlc_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLC data columns for charting."""

    if frame.empty:
        return pd.DataFrame()
    frame = frame.copy()
    frame.index = pd.to_datetime(frame.index)
    column_map = {column: str(column).title() for column in frame.columns}
    frame = frame.rename(columns=column_map)
    required = [column for column in ["Open", "High", "Low", "Close"] if column in frame.columns]
    if "Close" not in frame.columns:
        return pd.DataFrame()
    return frame[required].dropna(how="all").sort_index()


def load_price_cache_for_charts(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Load cached close prices when online OHLC is unavailable."""

    cache_path = ROOT_DIR / "data" / "price_cache.csv"
    if not cache_path.exists():
        return {symbol: pd.DataFrame() for symbol in symbols}
    try:
        cached = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    except Exception:
        return {symbol: pd.DataFrame() for symbol in symbols}
    result = {}
    for symbol in symbols:
        if symbol in cached.columns:
            close = pd.to_numeric(cached[symbol], errors="coerce").dropna()
            frame = pd.DataFrame({"Close": close}, index=close.index).sort_index()
            frame.attrs["data_source"] = "cache"
            result[symbol] = frame
        else:
            result[symbol] = pd.DataFrame()
    return result


def render_data_health_check(
    market_data: dict[str, pd.DataFrame],
    asset_table: pd.DataFrame,
    news_csv: Path | None,
    latest_report: Path | None,
) -> None:
    """Render market/news/report data health without blocking the page."""

    rows = []
    for symbol in CHART_ASSETS:
        frame = market_data.get(symbol)
        missing = is_empty_chart_frame(frame)
        source = "missing" if missing else str(frame.attrs.get("data_source", "unknown"))
        latest_time = "暂无"
        if not missing:
            latest_index = pd.to_datetime(frame.index, errors="coerce")
            latest_time = str(latest_index.max().date()) if not latest_index.empty and pd.notna(latest_index.max()) else "暂无"
        quality = dq_market_quality(frame, latest_time if latest_time != "暂无" else None, source)
        rows.append(
            {
                "ticker": symbol,
                "最近更新时间": latest_time,
                "数据源": source,
                "data_quality": format_data_quality_badge(quality),
                "是否缺失": "是" if missing else "否",
                "是否使用缓存": "是" if source == "cache" else "否",
                "说明": quality["explanation"],
            }
        )

    dfii10 = risk_row_from_asset_table(asset_table, ["DFII10"])
    dfii10_ok = dfii10 is not None and row_text(dfii10, "风险状态") not in {"", "data_unavailable"}
    news_ok = bool(news_csv and news_csv.exists())
    report_time = format_path_mtime(latest_report)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    cols = st.columns(3)
    cols[0].metric("DFII10 实际利率", "可用" if dfii10_ok else "不可用")
    cols[1].metric("新闻抓取", "成功" if news_ok else "暂无 CSV")
    cols[2].metric("最新报告生成时间", report_time)
    if any(row["是否缺失"] == "是" for row in rows) or not dfii10_ok or not news_ok:
        st.warning("数据不足，建议谨慎参考今日结论。")


def is_empty_chart_frame(frame: pd.DataFrame | None) -> bool:
    """Return True when market chart data is missing or unusable."""

    return frame is None or not isinstance(frame, pd.DataFrame) or frame.empty or "Close" not in frame.columns


def filter_chart_period(frame: pd.DataFrame | None, period_label: str) -> pd.DataFrame:
    """Filter a chart frame by selected period label."""

    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    offsets = {
        "3个月": pd.DateOffset(months=3),
        "6个月": pd.DateOffset(months=6),
        "1年": pd.DateOffset(years=1),
        "3年": pd.DateOffset(years=3),
        "5年": pd.DateOffset(years=5),
    }
    if period_label not in offsets:
        return frame.copy()
    cutoff = pd.Timestamp.today().normalize() - offsets[period_label]
    return frame.loc[frame.index >= cutoff].copy()


def normalize_non_gold_allocation(allocation: dict, target_amount: int) -> dict:
    """Remove gold from daily DCA allocation and keep the displayed total aligned."""

    cleaned = {name: int(amount or 0) for name, amount in allocation.items() if name != "黄金"}
    current_total = sum(cleaned.values())
    missing = target_amount - current_total
    if missing > 0 and cleaned:
        preferred = "易方达全球成长" if "易方达全球成长" in cleaned else next(iter(cleaned))
        cleaned[preferred] += missing
    return cleaned


def render_market_chart_conclusion(market_data: dict[str, pd.DataFrame]) -> None:
    """Render top-level chart conclusion."""

    qqq_3y = calculate_period_return(market_data.get("QQQ", pd.DataFrame()), "3年")
    smh_3y = calculate_period_return(market_data.get("SMH", pd.DataFrame()), "3年")
    gld_3y = calculate_period_return(market_data.get("GLD", pd.DataFrame()), "3年")
    spy_3y = calculate_period_return(market_data.get("SPY", pd.DataFrame()), "3年")
    smh_vs_qqq = compare_period_returns(smh_3y, qqq_3y)
    qqq_vs_spy = compare_period_returns(qqq_3y, spy_3y)
    gld_defense = compare_period_returns(gld_3y, spy_3y)
    smh_qqq_direction = relative_strength_direction(market_data, "SMH", "QQQ")
    qqq_spy_direction = relative_strength_direction(market_data, "QQQ", "SPY")
    gld_spy_direction = relative_strength_direction(market_data, "GLD", "SPY")
    smh_frame = market_data.get("SMH")
    smh_signal = classify_market_signal(add_chart_indicators(smh_frame)) if not is_empty_chart_frame(smh_frame) else "normal"
    main_attack_strong = smh_vs_qqq == "是" or smh_qqq_direction == "上升"

    cols = st.columns(4)
    cols[0].metric("QQQ近3年收益率", format_period_return(qqq_3y))
    cols[1].metric("SMH近3年收益率", format_period_return(smh_3y))
    cols[2].metric("GLD近3年收益率", format_period_return(gld_3y))
    cols[3].metric("SPY近3年收益率", format_period_return(spy_3y))

    conclusion_rows = [
        {"观察项": "SMH 是否跑赢 QQQ", "结论": smh_vs_qqq, "辅助信号": f"SMH/QQQ：{smh_qqq_direction}"},
        {"观察项": "QQQ 是否跑赢 SPY", "结论": qqq_vs_spy, "辅助信号": f"QQQ/SPY：{qqq_spy_direction}"},
        {"观察项": "GLD 是否发挥防守", "结论": "是" if gld_defense == "是" or gld_spy_direction == "上升" else "否", "辅助信号": f"GLD/SPY：{gld_spy_direction}"},
        {"观察项": "当前主攻仓是否仍强于纳指", "结论": "是" if main_attack_strong else "否", "辅助信号": f"SMH signal：{smh_signal}"},
        {"观察项": "当前是否过热", "结论": "是" if smh_signal == "overheat" else "否", "辅助信号": "RSI/均线综合"},
        {"观察项": "当前是否健康回踩", "结论": "是" if smh_signal == "healthy_pullback" else "否", "辅助信号": "回撤 + RSI 区间"},
    ]
    st.dataframe(pd.DataFrame(conclusion_rows), use_container_width=True, hide_index=True)


def render_period_return_table(market_data: dict[str, pd.DataFrame]) -> None:
    """Render period return table for configured chart assets."""

    st.markdown("### 阶段收益率")
    rows = []
    periods = ["1个月", "3个月", "6个月", "YTD", "1年", "3年", "5年"]
    for symbol, name in CHART_ASSETS.items():
        frame = market_data.get(symbol, pd.DataFrame())
        row = {"ticker": symbol, "资产": name}
        for period in periods:
            row[period] = format_period_return(calculate_period_return(frame, period))
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def calculate_period_return(frame: pd.DataFrame | None, period_label: str) -> float | None:
    """Calculate current close / period start close - 1."""

    if is_empty_chart_frame(frame):
        return None
    close = pd.to_numeric(frame["Close"], errors="coerce").dropna().sort_index()
    if len(close) < 2:
        return None
    end_price = close.iloc[-1]
    end_date = close.index[-1]
    if period_label == "YTD":
        start_date = pd.Timestamp(year=end_date.year, month=1, day=1)
    else:
        offsets = {
            "1个月": pd.DateOffset(months=1),
            "3个月": pd.DateOffset(months=3),
            "6个月": pd.DateOffset(months=6),
            "1年": pd.DateOffset(years=1),
            "3年": pd.DateOffset(years=3),
            "5年": pd.DateOffset(years=5),
        }
        start_date = end_date - offsets[period_label]
    if close.index.min() > start_date + pd.Timedelta(days=10):
        return None
    start_series = close.loc[close.index >= start_date]
    if start_series.empty or start_series.iloc[0] == 0:
        return None
    return float(end_price / start_series.iloc[0] - 1)


def format_period_return(value: float | None) -> str:
    """Format period return for display."""

    if value is None or pd.isna(value):
        return "数据不足"
    return f"{value:.2%}"


def compare_period_returns(left: float | None, right: float | None) -> str:
    """Compare two period returns."""

    if left is None or right is None or pd.isna(left) or pd.isna(right):
        return "数据不足"
    return "是" if left > right else "否"


def render_normalized_return_chart(market_data: dict[str, pd.DataFrame], symbols: list[str], period_label: str) -> None:
    """Render normalized performance chart with start value = 100."""

    st.markdown("### 归一化收益走势图")
    fig = go.Figure()
    added = 0
    skipped = []
    for symbol in symbols:
        frame = filter_chart_period(market_data.get(symbol), period_label)
        if is_empty_chart_frame(frame):
            skipped.append(symbol)
            continue
        close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if close.empty or close.iloc[0] == 0:
            skipped.append(symbol)
            continue
        normalized = close / close.iloc[0] * 100
        fig.add_trace(go.Scatter(x=normalized.index, y=normalized, mode="lines", name=symbol))
        added += 1
    if skipped and added > 0:
        st.warning("部分资产数据暂不可用，已跳过。")
    if added == 0:
        st.info("该周期暂无足够数据生成收益对比图。")
        return
    apply_dark_plotly_layout(fig)
    fig.update_layout(height=420, yaxis_title="起点=100", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=market_plotly_key("阶段收益", "_".join(symbols) or "none", "normalized_return"),
    )


def render_chart_group(title: str, symbols: list[str], market_data: dict[str, pd.DataFrame], portfolio: dict, app_mode: dict) -> None:
    """Render a group of asset charts."""

    available_symbols = [symbol for symbol in symbols if symbol in market_data]
    if not available_symbols:
        return
    st.markdown(f"### {title}")
    for symbol in available_symbols:
        frame = market_data.get(symbol, pd.DataFrame())
        render_single_market_chart(title, symbol, frame, portfolio, app_mode)


def render_single_market_chart(group_name: str, symbol: str, frame: pd.DataFrame, portfolio: dict, app_mode: dict) -> None:
    """Render one asset chart and technical state."""

    label = CHART_ASSETS.get(symbol, symbol)
    st.markdown(f"#### {symbol}：{label}")
    if is_empty_chart_frame(frame):
        st.info("该资产数据暂不可用。")
        return

    enriched = add_chart_indicators(frame)
    signal = classify_market_signal(enriched)
    latest_drawdown = float(enriched["drawdown"].dropna().iloc[-1]) if not enriched["drawdown"].dropna().empty else 0.0
    latest_rsi = enriched["RSI14"].dropna().iloc[-1] if not enriched["RSI14"].dropna().empty else pd.NA
    latest_ma60 = enriched["MA60"].dropna().iloc[-1] if not enriched["MA60"].dropna().empty else pd.NA

    cols = st.columns(4)
    cols[0].metric("market signal", signal)
    cols[1].metric("RSI 14", "暂无" if pd.isna(latest_rsi) else f"{latest_rsi:.1f}")
    cols[2].metric("当前回撤", f"{latest_drawdown:.2%}")
    cols[3].metric("60日均线", "暂无" if pd.isna(latest_ma60) else f"{latest_ma60:.2f}")

    fig = go.Figure()
    if {"Open", "High", "Low", "Close"}.issubset(enriched.columns):
        fig.add_trace(
            go.Candlestick(
                x=enriched.index,
                open=enriched["Open"],
                high=enriched["High"],
                low=enriched["Low"],
                close=enriched["Close"],
                name=symbol,
            )
        )
    else:
        fig.add_trace(go.Scatter(x=enriched.index, y=enriched["Close"], mode="lines", name="Close"))
    fig.add_trace(go.Scatter(x=enriched.index, y=enriched["MA20"], mode="lines", name="MA20", line=dict(color="#38BDF8")))
    fig.add_trace(go.Scatter(x=enriched.index, y=enriched["MA60"], mode="lines", name="MA60", line=dict(color="#D4AF37")))
    apply_dark_plotly_layout(fig)
    fig.update_layout(height=420, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=market_plotly_key(group_name, symbol, "price"),
    )

    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=enriched.index, y=enriched["RSI14"], mode="lines", name="RSI14", line=dict(color="#F97316")))
    rsi_fig.add_hline(y=70, line_dash="dash", line_color="#EF4444")
    rsi_fig.add_hline(y=50, line_dash="dot", line_color="#94A3B8")
    apply_dark_plotly_layout(rsi_fig)
    rsi_fig.update_layout(height=210, margin=dict(l=20, r=20, t=20, b=20), yaxis_range=[0, 100])
    st.plotly_chart(
        rsi_fig,
        use_container_width=True,
        key=market_plotly_key(group_name, symbol, "rsi"),
    )

    if is_private_mode(app_mode):
        mapping = fund_mapping_for_symbol(portfolio, symbol)
        if mapping:
            st.caption(f"相关基金映射：{mapping}")


def add_chart_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Add MA, RSI, and drawdown series."""

    enriched = frame.copy()
    close = pd.to_numeric(enriched["Close"], errors="coerce")
    enriched["MA20"] = close.rolling(20, min_periods=5).mean()
    enriched["MA60"] = close.rolling(60, min_periods=20).mean()
    enriched["RSI14"] = calculate_rsi_series(close, 14)
    enriched["drawdown"] = close / close.cummax() - 1
    return enriched


def calculate_rsi_series(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI for chart display."""

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window, min_periods=window).mean()
    avg_loss = loss.rolling(window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def classify_market_signal(frame: pd.DataFrame) -> str:
    """Classify the latest technical signal."""

    clean = frame.dropna(subset=["Close"])
    if clean.empty:
        return "normal"
    latest = clean.iloc[-1]
    rsi_value = latest.get("RSI14")
    drawdown = latest.get("drawdown", 0)
    ma60 = latest.get("MA60")
    close = latest.get("Close")
    if pd.notna(rsi_value) and rsi_value > 70:
        return "overheat"
    if pd.notna(ma60) and pd.notna(close) and close < ma60:
        return "trend_break"
    if -0.10 <= drawdown <= -0.05 and pd.notna(rsi_value) and 45 <= rsi_value <= 60:
        return "healthy_pullback"
    if -0.18 <= drawdown < -0.10 and pd.notna(rsi_value) and 35 <= rsi_value <= 50:
        return "strong_opportunity"
    return "normal"


def render_relative_strength_chart(title: str, numerator: str, denominator: str, market_data: dict[str, pd.DataFrame], group_name: str) -> None:
    """Render relative strength line chart."""

    if numerator not in market_data or denominator not in market_data:
        return
    left = market_data[numerator]
    right = market_data[denominator]
    if is_empty_chart_frame(left) or is_empty_chart_frame(right):
        st.info("部分资产数据暂不可用，已跳过。")
        return
    ratio = (left["Close"] / right["Close"]).dropna()
    if ratio.empty:
        return
    st.markdown(f"### {title}")
    st.caption(relative_strength_explanation(numerator, denominator, ratio))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ratio.index, y=ratio, mode="lines", name=f"{numerator}/{denominator}"))
    apply_dark_plotly_layout(fig)
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(
        fig,
        use_container_width=True,
        key=market_plotly_key(group_name, f"{numerator}_{denominator}", "relative_strength"),
    )


def market_plotly_key(group_name: str, symbol: str, chart_type: str) -> str:
    """Build a stable unique key for market Plotly charts."""

    safe_group = sanitize_plotly_key(group_name)
    safe_symbol = sanitize_plotly_key(symbol)
    safe_chart_type = sanitize_plotly_key(chart_type)
    return f"plotly_market_{safe_group}_{safe_symbol}_{safe_chart_type}"


def sanitize_plotly_key(value: str) -> str:
    """Sanitize ticker/group values for Streamlit keys."""

    return (
        str(value)
        .replace("=", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("：", "_")
        .replace("·", "_")
    )


def relative_strength_direction(market_data: dict[str, pd.DataFrame], numerator: str, denominator: str) -> str:
    """Return whether relative strength is rising or falling."""

    left = market_data.get(numerator, pd.DataFrame())
    right = market_data.get(denominator, pd.DataFrame())
    if is_empty_chart_frame(left) or is_empty_chart_frame(right):
        return "数据不足"
    ratio = (left["Close"] / right["Close"]).dropna()
    if len(ratio) < 21:
        return "数据不足"
    return "上升" if ratio.iloc[-1] > ratio.iloc[-21] else "下降"


def relative_strength_explanation(numerator: str, denominator: str, ratio: pd.Series) -> str:
    """Explain relative strength chart in plain language."""

    direction = "上升" if len(ratio) >= 21 and ratio.iloc[-1] > ratio.iloc[-21] else "下降"
    explanations = {
        ("SMH", "QQQ"): "SMH / QQQ 上升：半导体强于纳指。",
        ("SOXX", "QQQ"): "SOXX / QQQ 上升：半导体板块强于纳指。",
        ("QQQ", "SPY"): "QQQ / SPY 上升：科技强于大盘。",
        ("GLD", "SPY"): "GLD / SPY 上升：防守资产强于股票。",
    }
    return f"{explanations.get((numerator, denominator), f'{numerator}/{denominator} 上升代表分子资产更强')} 当前20日方向：{direction}。"


def fund_mapping_for_symbol(portfolio: dict, symbol: str) -> str:
    """Map chart symbols to configured funds in private mode."""

    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty or "proxy_symbol" not in funds.columns:
        return ""
    matched = funds.loc[funds["proxy_symbol"].astype(str) == symbol]
    if matched.empty:
        return ""
    return "；".join(matched["fund_name"].astype(str).tolist())


def render_drawdown_dashboard_page(asset_table: pd.DataFrame, report_text: str) -> None:
    """Render drawdown risk dashboard."""

    st.subheader("回撤风险仪表盘")
    if asset_table.empty:
        st.info("暂无资产风险表格，请先生成日报。")
        return

    drawdown_view = asset_table[["代码", "资产", "当前回撤", "当前回撤数值", "风险状态"]].copy()
    fig = px.bar(
        drawdown_view.sort_values("当前回撤数值"),
        x="代码",
        y="当前回撤数值",
        color="风险状态",
        color_discrete_map={"risk-on": "#16a34a", "neutral": "#ca8a04", "risk-off": "#dc2626"},
    )
    apply_dark_plotly_layout(fig)
    fig.update_layout(yaxis_tickformat=".0%", height=360)
    st.plotly_chart(fig, use_container_width=True, key="plotly_drawdown_dashboard_bar")

    threshold_line = find_sentence(report_text, ["-20%", "风险阈值"])
    st.write(threshold_line or "组合是否接近 -20% 风险阈值，请参考每日定投决策章节。")


def render_semiconductor_watch_page(asset_table: pd.DataFrame, dca_table: pd.DataFrame) -> None:
    """Render semiconductor, CPO, and CPU watch page."""

    st.subheader("半导体 / CPO / CPU 观察区")
    if asset_table.empty:
        st.info("暂无资产风险表格，请先生成日报。")
        return

    symbols = ["SMH", "SOXX", "QQQ"]
    watch = asset_table.loc[asset_table["代码"].isin(symbols)]
    if not watch.empty:
        st.dataframe(watch, use_container_width=True, hide_index=True)
    else:
        st.info("当前报告没有半导体 / CPO / CPU 代理资产数据。")

    if not dca_table.empty and "主题" in dca_table.columns:
        focus = dca_table[dca_table["主题"].str.contains("半导体|CPO|CPU|AI", na=False)]
        if not focus.empty:
            st.markdown("**相关基金今日定投辅助**")
            st.dataframe(focus, use_container_width=True, hide_index=True)


def render_news_digest_page(news_text: str, news_items: pd.DataFrame, app_mode: dict, final_decision: dict) -> None:
    """Render daily news digest."""

    st.subheader("新闻与主题观察")
    if is_public_mode(app_mode) and news_items.empty:
        st.info("公网新闻源暂不可用，新闻页保留研究框架。")
    if not news_items.empty:
        col1, col2 = st.columns(2)
        col1.metric("新闻条数", len(news_items))
        source_count = news_items["source"].nunique() if "source" in news_items.columns else 0
        col2.metric("数据源数量", source_count)
        if "published_at" in news_items.columns:
            latest_time = news_items["published_at"].dropna().astype(str).max()
            st.caption(f"新闻抓取/发布时间参考：{latest_time}")
    news_quality = dq_news_quality(news_items, public_fallback=is_public_mode(app_mode) and news_items.empty)
    st.caption(f"新闻数据质量：{format_data_quality_badge(news_quality)}｜{news_quality['explanation']}")

    st.markdown("#### 今日新闻总判断")
    st.info(public_text(build_news_overall_judgment(news_items, final_decision), app_mode))
    render_news_cards(news_items, app_mode, final_decision)

    with st.expander("原始 Markdown 摘要", expanded=False):
        if is_template_news_summary(news_text):
            st.info("当前新闻 Markdown 缓存包含旧模板摘要，主卡片已忽略这些旧字段，并基于标题/source/time 重新构造四段式投研笔记。")
        else:
            st.markdown(news_text)
    if not news_items.empty and "url" in news_items.columns:
        with st.expander("新闻原始链接", expanded=False):
            for _, item in news_items.iterrows():
                title = item.get("title", "")
                url = item.get("url", "")
                if url:
                    st.markdown(f"- [{title}]({url})")
    st.caption("新闻可能存在延迟、误报或来源偏差，仅用于研究观察和定投辅助。")


def render_news_cards(news_items: pd.DataFrame, app_mode: dict, final_decision: dict) -> None:
    """Render structured news cards with content summary and action translation."""

    if news_items.empty:
        if is_public_mode(app_mode):
            st.info("暂无实时新闻缓存。公网版仍保留新闻投研框架：新闻只用于解释主线、风险和观察池，不覆盖 final_decision。")
        else:
            st.info("暂无可解析的新闻条目。")
        return

    ranked = rank_news_items(news_items).head(5)
    st.markdown("#### 重点投研笔记")
    for _, item in ranked.iterrows():
        card = build_news_card(item, app_mode, final_decision)
        st.markdown(
            f"""
            <div class="plain-explain-card">
              <div><strong>标题：</strong>{html.escape(card['title'])}</div>
              <div class="muted">{html.escape(card['source'])} · {html.escape(card['published_at'])}</div>
              <p><strong>新闻内容：</strong>{html.escape(card['news_content'])}</p>
              <p><strong>投资解读：</strong>{html.escape(card['investment_reading'])}</p>
              <p><strong>对我的动作：</strong>{html.escape(card['today_action'])}</p>
              <p><strong>后续观察点：</strong>{html.escape(card['follow_up'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"技术分类详情：{card['title'][:40]}", expanded=False):
            st.write(f"新闻类型：{card['news_type']}")
            st.write(f"标签：{card['labels']}")
            st.markdown(f"影响基金：{card['fund_impact_html']}", unsafe_allow_html=True)
            st.write(f"观察池：{card['watchlist']}")

    remaining = rank_news_items(news_items).iloc[5:]
    if not remaining.empty:
        with st.expander("其余新闻", expanded=False):
            st.dataframe(remaining, use_container_width=True, hide_index=True)


def rank_news_items(news_items: pd.DataFrame) -> pd.DataFrame:
    """Rank news by relevance to the user's priority themes."""

    priority = ["semiconductor", "cpo", "cpu", "memory", "ai", "gold", "macro", "sic"]
    ranked = news_items.copy()
    if "themes" not in ranked.columns:
        ranked["themes"] = [[] for _ in range(len(ranked))]
    ranked["_parsed_themes"] = ranked["themes"].map(parse_news_themes)
    ranked["_priority"] = ranked["_parsed_themes"].map(lambda themes: sum(1 for theme in priority if theme in themes))
    ranked["_importance"] = pd.to_numeric(ranked.get("importance_score", 0), errors="coerce").fillna(0)
    return ranked.sort_values(["_priority", "_importance"], ascending=False).drop(columns=["_priority", "_importance", "_parsed_themes"])


def build_news_overall_judgment(news_items: pd.DataFrame, final_decision: dict) -> str:
    """Build the daily overall news judgment without creating independent amounts."""

    mode = final_decision.get("market_mode", "normal_dca")
    discipline = decision_risk_discipline_label(final_decision)
    if news_items.empty:
        return "今日新闻数据不足，不改变 final_decision。今日按当前计划执行。"

    ranked = rank_news_items(news_items).head(3)
    contexts = [classify_news_context(str(item.get("title", "")), parse_news_themes(item.get("themes", []))) for _, item in ranked.iterrows()]
    all_labels = {label for context in contexts for label in context["labels"]}
    mainline = bool({"半导体", "CPO", "CPU", "存储", "AI算力", "数据中心", "AI应用", "Agentic AI"}.intersection(all_labels))
    risk = bool({"宏观风险", "美元", "美债", "出口管制", "地缘风险"}.intersection(all_labels))
    supports_accel = mainline and mode not in {"defense_mode"} and not decision_blocks_acceleration(final_decision)
    top_titles = "；".join(str(title) for title in ranked.get("title", pd.Series(dtype=str)).head(3).tolist())
    return (
        f"今日最重要的新闻：{top_titles or '暂无高相关标题'}。"
        f"今日主线{'有所增强' if mainline else '没有明显增强'}；"
        f"{'风险信号有所上升' if risk else '未见明显新增风险信号'}；"
        f"{'健康回踩时可作为加速依据' if supports_accel else '不改变 final_decision'}。"
        f"今日最终动作：按当前计划执行，{discipline}。新闻只负责解释和确认方向，不生成买入金额。"
    )


def build_news_card(item: pd.Series, app_mode: dict, final_decision: dict) -> dict:
    """Build one investment-note style news card."""

    title = str(item.get("title", ""))
    themes = parse_news_themes(item.get("themes", []))
    raw_summary = str(item.get("summary", "") or "").strip()
    summary = "" if is_template_news_summary(raw_summary) else raw_summary
    context = classify_news_context(title, themes, summary)
    labels = context["labels"]
    sentiment = sentiment_to_cn(str(item.get("sentiment", "neutral")))
    body_available = bool(summary and summary.lower() != "nan" and summary not in {title, "None"})
    if str(item.get("data_quality", "")).lower() == "title_only" or item.get("raw_text_available") is False:
        body_available = False
    return {
        "title": title or "无标题新闻",
        "source": str(item.get("source", "未知来源")),
        "published_at": str(item.get("published_at", "发布时间未知")) or "发布时间未知",
        "news_content": build_news_content(title, summary, labels, context, body_available),
        "investment_reading": build_news_investment_reading(labels, context, sentiment),
        "fund_impact_html": format_fund_impact(context["fund_impact"], is_private_mode(app_mode)),
        "news_type": context.get("catalyst_type", "软信号"),
        "labels": "、".join(labels),
        "watchlist": build_news_watchlist(context["watchlist"], labels),
        "today_action": public_text(translate_news_action(labels, themes, final_decision), app_mode),
        "follow_up": build_news_follow_up(labels, context["watchlist"]),
    }


def is_template_news_summary(summary: str) -> bool:
    """Detect old cached template summaries and stop using them as article content."""

    if not summary:
        return False
    markers = [
        "新闻核心是",
        "重要性来自",
        "当前情绪判断为",
        "动作标签为",
        "仅用于研究观察",
        "maintain_dca",
        "watchlist_only",
        "wait_for_pullback",
    ]
    return any(marker in summary for marker in markers)


def parse_news_themes(themes) -> list[str]:
    """Normalize theme values from CSV/list fields."""

    if isinstance(themes, list):
        return [str(theme).strip() for theme in themes if str(theme).strip()]
    if themes is None:
        return []
    if isinstance(themes, float) and pd.isna(themes):
        return []
    raw = str(themes).replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    return [theme.strip() for theme in raw.split(",") if theme.strip()]


def classify_news_context(title: str, themes: list[str], summary: str = "") -> dict:
    """Classify a news item with title-specific investment context."""

    text = f"{title} {summary}".lower()
    labels = []
    event_type = "低相关噪音"
    catalyst_type = detect_news_catalyst_type(text)
    watchlist = {"ETF观察": [], "股票观察": [], "宏观观察": []}
    market_reaction = "低相关噪音"

    def add(*items):
        for item in items:
            if item not in labels:
                labels.append(item)

    def add_watch(kind: str, *items):
        for item in items:
            if item not in watchlist[kind]:
                watchlist[kind].append(item)

    if any(word in text for word in ["asian shares", "asia stocks", "asian markets", "wall street resumes", "ai rally", "oil prices slip", "oil slips"]):
        add("宏观风险偏好", "AI主线情绪", "油价", "亚洲科技股")
        event_type = "宏观环境"
        catalyst_type = "宏观环境"
        add_watch("ETF观察", "QQQ", "SMH", "SOXX", "SPY")
        add_watch("股票观察", "NVDA", "AVGO", "TSM", "AMD", "MU")
        add_watch("宏观观察", "油价", "美债收益率", "美元指数")
        market_reaction = "宏观情绪改善叠加AI主线反弹，属于方向确认，不是单家公司硬催化"
    elif any(word in text for word in ["jensen huang", "ai jobs", "ai tool", "agentic", "ai adoption"]):
        add("AI应用", "Agentic AI", "纳指科技", "长期AI需求")
        event_type = "观点采访 / AI应用扩散"
        catalyst_type = "软信号"
        add_watch("ETF观察", "QQQ")
        add_watch("股票观察", "MSFT", "GOOGL", "META", "NVDA")
        add_watch("宏观观察", "科技股风险偏好")
        market_reaction = "主线增强，但偏长期需求确认"
    elif "nvidia" in text and any(word in text for word in ["earnings", "revenue", "profit", "guidance", "results"]):
        add("AI芯片", "GPU", "数据中心", "半导体", "AI算力")
        event_type = "硬催化：财报 / 业绩指引"
        catalyst_type = "硬催化"
        add_watch("ETF观察", "QQQ", "SMH", "SOXX")
        add_watch("股票观察", "NVDA", "AVGO", "TSM", "AMD", "MU")
        add_watch("宏观观察", "美债收益率", "美元指数")
        market_reaction = "AI芯片需求被业绩验证，属于比情绪新闻更强的基本面线索"
    elif "nvidia" in text and any(word in text for word in ["china", "h20", "export", "restriction", "curb"]):
        add("AI芯片", "半导体", "中国市场", "出口管制", "地缘风险")
        event_type = "政策 / 地缘风险"
        catalyst_type = "硬催化" if any(word in text for word in ["ban", "rule", "policy", "license", "restriction"]) else "软信号"
        add_watch("ETF观察", "QQQ", "SMH", "SOXX")
        add_watch("股票观察", "NVDA", "TSM", "AMD")
        add_watch("宏观观察", "出口管制", "中美科技政策")
        market_reaction = "主线仍强，但地缘和政策风险上升"
    elif "nvidia" in text or "nvda" in text:
        add("AI芯片", "GPU", "数据中心", "半导体", "AI算力")
        event_type = "个股异动 / AI芯片龙头事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "QQQ", "SMH", "SOXX")
        add_watch("股票观察", "NVDA", "AVGO", "TSM", "AMD", "MU")
        add_watch("宏观观察", "科技股风险偏好")
        market_reaction = "主线增强，若价格过热则可能利好兑现"
    elif "intel" in text or "intc" in text:
        add("CPU", "代工", "美国制造", "半导体")
        event_type = "个股异动 / CPU / 代工事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "SMH", "SOXX", "QQQ")
        add_watch("股票观察", "INTC", "AMD", "ARM")
        add_watch("宏观观察", "美国制造政策", "半导体补贴")
        market_reaction = "CPU和美国制造链条关注度上升"
    elif "broadcom" in text or "avgo" in text:
        add("AI ASIC", "网络芯片", "数据中心", "CPO相关", "半导体")
        event_type = "AI ASIC / 数据中心事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "SMH", "SOXX", "QQQ")
        add_watch("股票观察", "AVGO", "MRVL", "CRDO", "LITE", "COHR")
        add_watch("宏观观察", "云资本开支", "数据中心需求")
        market_reaction = "AI ASIC和数据中心链条增强"
    elif any(word in text for word in ["atxsummit", "summit", "conference", "public ai"]):
        add("AI应用", "政策", "低相关")
        event_type = "会议 / 观点"
        catalyst_type = "软信号"
        add_watch("ETF观察", "QQQ")
        add_watch("股票观察", "MSFT", "GOOGL", "META")
        add_watch("宏观观察", "AI政策氛围")
        market_reaction = "偏方向观察，不直接改变交易节奏"
    elif any(word in text for word in ["micron", " hbm", "memory", "dram", "nand"]):
        add("存储", "HBM", "AI算力")
        event_type = "存储 / HBM事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "SMH", "SOXX")
        add_watch("股票观察", "MU", "SK Hynix", "Samsung")
        add_watch("宏观观察", "DRAM价格", "HBM供给")
        market_reaction = "AI算力上游景气度可能增强"
    elif any(word in text for word in ["cpo", "optical", "800g", "1.6t", "coherent", "lumentum", "silicon photonics"]):
        add("CPO", "数据中心")
        event_type = "CPO / 光通信事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "SMH", "SOXX")
        add_watch("股票观察", "AVGO", "MRVL", "CRDO", "LITE", "COHR")
        add_watch("宏观观察", "800G/1.6T需求", "云资本开支")
        market_reaction = "CPO链条关注度上升"
    elif any(word in text for word in ["gold", "gld", "comex", "real yield", "safe haven", "bullion"]):
        add("黄金", "GLD", "GC=F")
        if any(word in text for word in ["dollar", "yield", "real yield", "fed", "rate"]):
            add("美元", "实际利率")
        event_type = "黄金 / 防守资产事件"
        catalyst_type = "软信号"
        add_watch("ETF观察", "GLD", "TLT", "UUP")
        add_watch("股票观察", "黄金矿业股")
        add_watch("宏观观察", "美元指数", "实际利率", "DFII10", "美债收益率")
        market_reaction = "只影响黄金防守模块，不影响半导体主攻仓"
    elif any(word in text for word in ["fed", "federal reserve", "treasury", "yield", "dxy", "dollar", "cpi", "pce", "inflation", "oil"]):
        add("宏观风险", "风险偏好")
        if any(word in text for word in ["dollar", "dxy"]):
            add("美元")
        if any(word in text for word in ["treasury", "yield", "rate", "fed", "cpi", "pce", "inflation"]):
            add("美债")
        if "oil" in text:
            add("油价")
        event_type = "宏观流动性事件"
        catalyst_type = "硬催化" if any(word in text for word in ["fed", "cpi", "pce", "rate", "policy"]) else "软信号"
        add_watch("ETF观察", "QQQ", "SPY", "UUP", "TLT")
        add_watch("股票观察", "大型科技股")
        add_watch("宏观观察", "油价", "美债收益率", "美元指数", "通胀数据")
        market_reaction = "成长股估值压力可能上升"
    elif any(word in text for word in ["sic", "silicon carbide", "wolfspeed", "gan", "infineon"]):
        add("碳化硅", "SiC/GaN")
        event_type = "碳化硅 / 功率半导体事件"
        catalyst_type = detect_news_catalyst_type(text)
        add_watch("ETF观察", "SMH", "SOXX")
        add_watch("股票观察", "WOLF", "ON", "STM", "IFNNY")
        add_watch("宏观观察", "新能源车需求", "功率半导体价格")
        market_reaction = "进入观察池，不直接纳入主定投"

    labels = list(dict.fromkeys(labels)) or conservative_labels_from_themes(themes)
    return {
        "labels": labels,
        "event_type": event_type,
        "catalyst_type": catalyst_type,
        "watchlist": watchlist,
        "market_reaction": market_reaction,
        "fund_impact": build_fund_impact_groups(labels),
    }


def conservative_labels_from_themes(themes: list[str]) -> list[str]:
    """Use CSV themes only as a conservative fallback when title/content has no clear object."""

    mapping = {
        "semiconductor": "半导体",
        "cpo": "CPO",
        "cpu": "CPU",
        "memory": "存储",
        "ai": "AI算力",
        "gold": "黄金",
        "macro": "宏观风险",
        "sic": "碳化硅",
        "qdii": "QDII/汇率",
    }
    labels = [mapping[theme] for theme in themes if theme in mapping]
    return list(dict.fromkeys(labels)) or ["其他"]


def detect_news_catalyst_type(text: str) -> str:
    """Classify title-level catalyst strength."""

    hard_words = ["earnings", "revenue", "profit", "guidance", "order", "orders", "policy", "ban", "tariff", "shipment", "sales"]
    return "硬催化" if any(word in text for word in hard_words) else "软信号"


def sentiment_to_cn(sentiment: str) -> str:
    """Translate news sentiment."""

    return {"positive": "偏利好", "negative": "偏利空", "mixed": "中性", "neutral": "中性", "ignore_noise": "噪音/低相关"}.get(sentiment, "中性")


def build_news_content(title: str, summary: str, labels: list[str], context: dict, body_available: bool) -> str:
    """Write the first paragraph: what the news itself says."""

    if body_available:
        if str(summary).startswith("正文不可用，仅基于标题判断"):
            return shorten_text(summary, 260)
        return shorten_text(
            enrich_news_summary(summary, title, labels, context),
            260,
        )
    title_story = build_title_based_news_story(title, labels, context)
    return (
        f"正文不可用，仅基于标题判断。以下为标题层面的解读，具体细节需要等待更多来源确认。{title_story}"
    )


def enrich_news_summary(summary: str, title: str, labels: list[str], context: dict) -> str:
    """Turn available summary into a more natural news-content paragraph."""

    base = summary.strip()
    if len(base) < 40:
        base = build_title_based_news_story(title, labels, context)
    if context.get("catalyst_type") == "硬催化":
        return f"{base} 这类新闻更接近财报、订单、业绩指引或政策落地，需要重点核对具体数据和管理层指引。"
    if context.get("catalyst_type") == "宏观环境":
        return f"{base} 这类新闻反映的是宏观环境和市场风险偏好变化，不是单家公司订单或财报催化。"
    return f"{base} 这类新闻更偏情绪、观点或市场氛围，需要后续价格和基本面继续验证。"


def build_title_based_news_story(title: str, labels: list[str], context: dict) -> str:
    """Build a concrete title-based story without falling back to label soup."""

    text = title.lower()
    if {"宏观风险偏好", "AI主线情绪", "油价"}.intersection(labels):
        return (
            "从标题看，这篇新闻主要说亚洲股市上涨，原因可能是油价回落缓解了通胀和利率压力，同时美股AI板块重新反弹，带动全球科技股风险偏好恢复。"
            "这更像是一条市场行情回顾新闻，而不是某家公司订单或财报变化。由于缺少正文，无法确认具体国家、板块和公司贡献。"
        )
    if "Nvidia" in infer_news_subject(title, labels) or "nvidia" in text:
        return "从标题看，新闻围绕英伟达展开，市场可能在重新评估AI芯片、GPU和数据中心需求。由于缺少正文，暂时无法确认这是财报指引、订单变化，还是单纯股价异动。"
    if "Broadcom" in infer_news_subject(title, labels) or "broadcom" in text or "avgo" in text:
        return "从标题看，新闻围绕博通展开，可能涉及AI ASIC、网络芯片或数据中心互联需求。由于缺少正文，暂时只能把它当作AI算力链条的观察线索。"
    if "Intel" in infer_news_subject(title, labels) or "intel" in text:
        return "从标题看，新闻围绕英特尔展开，可能涉及CPU、晶圆代工、美国制造或股价异动。由于缺少正文，不能确认变化来自业务改善、政策支持，还是短线情绪。"
    if "黄金" in labels:
        return "从标题看，新闻围绕黄金或黄金ETF展开，可能与美元、实际利率、避险需求或央行购金有关。由于缺少正文，暂时只能判断它影响黄金防守模块。"
    if any(label in labels for label in ["美元", "美债", "宏观风险", "油价"]):
        return "从标题看，新闻主要涉及宏观变量，例如油价、美元、美债收益率、通胀或美联储预期。这类新闻通常通过估值和风险偏好影响科技成长资产。"
    return f"标题显示这是一条关于{context['event_type']}的新闻，主要对象可能是{infer_news_subject(title, labels)}。"


def build_news_investment_reading(labels: list[str], context: dict, sentiment: str) -> str:
    """Write the second paragraph: why it matters for investing."""

    affected = infer_affected_direction(labels)
    catalyst = context.get("catalyst_type", "软信号")
    reaction = context.get("market_reaction", "低相关噪音")
    strength = "证据强度较高" if catalyst == "硬催化" else ("主要是宏观环境变化" if catalyst == "宏观环境" else "证据强度中等偏弱")
    if {"宏观风险偏好", "AI主线情绪", "油价"}.intersection(labels):
        return (
            "这属于宏观情绪改善叠加AI主线反弹的软信号，不是财报、订单或资本开支指引这类硬催化。"
            "它能说明市场仍愿意交易AI、半导体和科技成长方向，但证据强度不足以单独改变今日动作。"
        )
    if any(label in labels for label in ["半导体", "CPO", "CPU", "AI芯片", "AI ASIC", "存储", "HBM", "数据中心", "AI算力"]):
        detail = "它影响AI算力、半导体、CPO、CPU或存储链条的景气预期。关键是需求能否落实到订单、价格、财报或资本开支指引。"
    elif "黄金" in labels:
        detail = "它影响黄金防守模块，关键看美元和实际利率是否压制黄金，而不是改变半导体/CPO主攻仓。"
    elif any(label in labels for label in ["美元", "美债", "宏观风险", "风险偏好", "油价", "宏观风险偏好"]):
        detail = "它影响风险偏好和成长股估值环境，美元或美债收益率走强时，纳指科技通常更容易承压。"
    elif any(label in labels for label in ["碳化硅", "SiC/GaN"]):
        detail = "它影响功率半导体观察池，更多是产业链线索，不直接进入主定投框架。"
    else:
        detail = "它更像背景信息，相关性有限，需要等待更多价格和基本面验证。"
    return f"这属于{catalyst}，{strength}；主要影响{affected}。{detail}当前市场反应可以理解为：{reaction}。"


def infer_news_subject(title: str, labels: list[str]) -> str:
    """Infer main subject for natural-language news content."""

    text = title.lower()
    subjects = []
    subject_keywords = {
        "Nvidia": ["nvidia", "nvda"],
        "Broadcom": ["broadcom", "avgo"],
        "Intel": ["intel", "intc"],
        "AMD": ["amd"],
        "台积电": ["tsmc", "tsm"],
        "美光": ["micron", " mu "],
        "黄金": ["gold", "gld", "comex"],
        "美联储/利率": ["fed", "federal reserve", "rate", "yield"],
        "美元": ["dollar", "dxy", "uup"],
        "亚洲股市": ["asian shares", "asia stocks"],
        "油价": ["oil"],
    }
    padded = f" {text} "
    for subject, keywords in subject_keywords.items():
        if any(keyword in padded for keyword in keywords):
            subjects.append(subject)
    if subjects:
        return "、".join(subjects)
    return "、".join(labels[:3]) if labels else "相关市场或公司"


def infer_news_background(labels: list[str]) -> str:
    """Infer background from labels."""

    if any(label in labels for label in ["半导体", "AI芯片", "AI算力", "数据中心"]):
        return "AI资本开支、芯片供需和科技股风险偏好仍是市场主线"
    if any(label in labels for label in ["CPO", "网络芯片"]):
        return "AI数据中心带宽升级正在推动光通信和网络芯片关注度上升"
    if any(label in labels for label in ["CPU", "AI ASIC"]):
        return "AI推理和云厂商自研芯片正在改变CPU、GPU和ASIC的竞争格局"
    if any(label in labels for label in ["存储", "HBM"]):
        return "AI服务器对HBM和高端存储需求较强，价格和产能周期重要"
    if "黄金" in labels:
        return "黄金主要受美元、实际利率和避险需求影响"
    if any(label in labels for label in ["美元", "美债", "宏观风险"]):
        return "利率、通胀、美元和流动性会影响全球风险资产估值"
    return "市场仍在寻找能被业绩或宏观数据验证的线索"


def infer_affected_direction(labels: list[str]) -> str:
    """List affected investment directions."""

    allowed = ["AI算力", "半导体", "CPO", "CPU", "存储", "SiC/GaN", "黄金", "美元", "美债", "宏观风险", "风险偏好", "宏观风险偏好", "AI主线情绪", "油价", "亚洲科技股"]
    mapped = []
    for label in labels:
        if label in allowed:
            mapped.append(label)
        elif label in {"AI芯片", "AI ASIC", "数据中心", "HBM"}:
            mapped.append("AI算力")
            mapped.append("半导体")
        elif label in {"碳化硅"}:
            mapped.append("SiC/GaN")
        elif label in {"纳指科技", "AI应用", "Agentic AI"}:
            mapped.append("风险偏好")
    return "、".join(dict.fromkeys(mapped)) or "其他"


def shorten_text(text: str, limit: int) -> str:
    """Keep card paragraphs compact."""

    clean = " ".join(str(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def build_fund_impact_groups(labels: list[str]) -> dict[str, list[str]]:
    """Group affected funds by relevance without forcing every fund into every news item."""

    impact = {"强相关": [], "中等相关": [], "低相关": [], "无直接影响": []}
    growth_labels = {"半导体", "CPO", "CPU", "AI芯片", "AI ASIC", "AI算力", "存储", "HBM", "数据中心"}
    ai_app_labels = {"AI应用", "Agentic AI", "纳指科技", "长期AI需求"}
    macro_risk_sentiment = {"宏观风险偏好", "AI主线情绪", "油价", "亚洲科技股"}
    macro_labels = {"美元", "美债", "宏观风险", "出口管制", "地缘风险"}
    if macro_risk_sentiment.intersection(labels):
        impact["强相关"] += ["广发纳指100", "易方达全球成长"]
        impact["中等相关"] += ["浦银全球智能科技", "国富全球科技互联"]
        impact["低相关"] += ["摩根标普500", "易方达黄金"]
        impact["无直接影响"].append("华安日经225")
    if growth_labels.intersection(labels):
        impact["强相关"] += ["浦银全球智能科技", "国富全球科技互联", "易方达全球成长"]
        impact["中等相关"].append("广发纳指100")
    if ai_app_labels.intersection(labels):
        impact["强相关"] += ["广发纳指100", "易方达全球成长"]
        impact["中等相关"] += ["国富全球科技互联", "浦银全球智能科技"]
    if "黄金" in labels:
        impact["强相关"].append("易方达黄金")
        impact["低相关"] += ["浦银全球智能科技", "国富全球科技互联", "广发纳指100"]
    if macro_labels.intersection(labels):
        impact["中等相关"] += ["广发纳指100", "摩根标普500", "易方达全球成长"]
    if {"碳化硅", "SiC/GaN"}.intersection(labels):
        impact["低相关"].append("碳化硅观察方向")
    if not any(impact[group] for group in ["强相关", "中等相关", "低相关"]):
        impact["无直接影响"].append("现有基金暂无明确直接映射")
    return {group: list(dict.fromkeys(values)) for group, values in impact.items() if values}


def format_fund_impact(impact: dict[str, list[str]], private_mode: bool) -> str:
    """Format fund impact groups as safe HTML."""

    if not private_mode:
        public_groups = [group for group, values in impact.items() if values and group != "无直接影响"]
        return html.escape("Public 模式仅显示方向相关度：" + ("、".join(public_groups) if public_groups else "暂无直接影响"))
    parts = []
    for group, values in impact.items():
        parts.append(f"{html.escape(group)}：{html.escape('、'.join(values))}")
    return "<br>".join(parts) if parts else "暂无直接影响"


def build_news_watchlist(watchlist: list[str], labels: list[str]) -> str:
    """Build observation pool text."""

    if isinstance(watchlist, dict):
        etfs = watchlist.get("ETF观察", [])
        stocks = watchlist.get("股票观察", [])
        macros = watchlist.get("宏观观察", [])
    else:
        etfs, stocks, macros = [], list(watchlist or []), []
    if not any([etfs, stocks, macros]):
        etfs = ["QQQ", "SPY"] if "风险偏好" in labels or "宏观风险偏好" in labels else []
        stocks = [label for label in labels if label not in {"宏观风险", "风险偏好"}]
    parts = []
    if etfs:
        parts.append(f"ETF观察：{'、'.join(etfs)}")
    if stocks:
        parts.append(f"股票观察：{'、'.join(stocks)}")
    if macros:
        parts.append(f"宏观观察：{'、'.join(macros)}")
    return "；".join(parts) + "。观察，不等于今天买入；若无美股账户，仅作为基金方向参考。"


def translate_news_action(labels: list[str], themes: list[str], final_decision: dict) -> str:
    """Translate news into action without overriding final_decision."""

    mode = final_decision.get("market_mode", "normal_dca")
    discipline = decision_risk_discipline_code(final_decision)
    if discipline == "do_not_chase":
        return "不改变今日 final_decision。当前纪律为 do_not_chase，按当前计划执行，不追高，不加速。"
    if mode == "defense_mode":
        return "不改变今日 final_decision。当前处于 defense_mode，继续维持系统纪律，降低进攻。"
    if "黄金" in labels or "gold" in themes:
        return "不改变今日 final_decision。黄金按两周计划择时，只影响黄金防守补仓判断，不影响每日主定投金额。"
    if {"semiconductor", "cpo", "cpu"}.intersection(themes) or {"半导体", "CPO", "CPU", "AI芯片", "AI ASIC"}.intersection(labels):
        return "不改变今日 final_decision。它可作为主线仍在的观察信号，健康回踩时可作为辅助依据；本页不输出具体金额。"
    if "sic" in themes or {"碳化硅", "SiC/GaN"}.intersection(labels):
        return "不改变今日 final_decision。只加入观察池，不触发今日动作。"
    return "不改变今日 final_decision；本页不输出具体金额。"


def build_news_follow_up(labels: list[str], watchlist: list[str]) -> str:
    """Build the fourth paragraph: what to watch next."""

    if {"宏观风险偏好", "AI主线情绪", "油价"}.intersection(labels):
        return "后续重点看 QQQ / SMH 是否继续强于 SPY，油价和美债收益率是否继续回落，以及 NVDA、AVGO、TSM、AMD、MU 是否继续领涨。"
    points = []
    if any(label in labels for label in ["宏观风险偏好", "AI主线情绪", "亚洲科技股"]):
        points.append("看 QQQ / SMH 是否继续强于 SPY")
        points.append("看油价、美债收益率和美元指数是否继续回落或保持稳定")
    if any(label in labels for label in ["半导体", "AI芯片", "AI ASIC", "AI算力", "数据中心"]):
        points.append("看 QQQ / SMH 是否继续强于 SPY")
        points.append("看 NVDA、AVGO、TSM、AMD、MU 是否继续领涨")
    if "CPO" in labels:
        points.append("看 CPO 相关公司如 AVGO、MRVL、CRDO、LITE、COHR 是否跟随")
    if any(label in labels for label in ["CPU", "AI ASIC"]):
        points.append("看 AMD、INTC、ARM 和定制芯片链条是否有持续订单或指引")
    if any(label in labels for label in ["存储", "HBM"]):
        points.append("看美光、SK Hynix、Samsung 以及 HBM 价格和供给是否继续改善")
    if any(label in labels for label in ["美元", "美债", "宏观风险"]):
        points.append("看美债收益率和美元是否回落")
    if "黄金" in labels:
        points.append("看黄金是否继续受美元和实际利率压制")
        points.append("看 GLD / GC=F 是否重新站稳趋势")
    if any(label in labels for label in ["碳化硅", "SiC/GaN"]):
        points.append("看 WOLF、ON、STM、IFNNY 是否出现基本面改善，而不是单日反弹")
    if not points:
        points.append("看相关资产价格是否有连续性，避免只被单条新闻情绪带动")
    return "；".join(dict.fromkeys(points[:3])) + "。"


def render_news_radar_page(news_items: pd.DataFrame) -> None:
    """Render theme news radar."""

    st.subheader("主题新闻雷达")
    if news_items.empty:
        st.info("公网新闻源暂不可用，保留研究框架。")
        return

    exploded = news_items.explode("themes")
    radar = exploded.groupby("themes", as_index=False).agg(
        news_count=("title", "count"),
        important_count=("need_attention", "sum"),
    )
    fig = px.bar(radar, x="themes", y="news_count", color="important_count", text="news_count")
    apply_dark_plotly_layout(fig)
    fig.update_layout(height=360)
    st.plotly_chart(fig, use_container_width=True, key="plotly_news_radar_bar")
    st.dataframe(radar, use_container_width=True, hide_index=True)


def render_theme_news_page(news_items: pd.DataFrame, themes: list[str], title: str) -> None:
    """Render a filtered news page."""

    st.subheader(title)
    if news_items.empty:
        st.info("公网新闻源暂不可用，保留研究框架。")
        return

    mask = news_items["themes"].map(lambda item_themes: any(theme in item_themes for theme in themes))
    filtered = news_items.loc[mask]
    if filtered.empty:
        st.info("暂无匹配资讯。")
        return

    st.dataframe(filtered, use_container_width=True, hide_index=True)


def render_news_dca_impact_page(news_text: str, app_mode: dict, final_decision: dict) -> None:
    """Render news impact on today's DCA plan."""

    st.subheader("新闻对今日定投影响")
    st.info(news_final_conclusion(final_decision, app_mode))
    card_cols = st.columns(3)
    card_cols[0].markdown(
        "**主线新闻**\n\n半导体 / CPO / CPU / AI算力新闻偏积极时，只作为主线观察信号。"
    )
    card_cols[1].markdown(
        "**加速条件**\n\n若 QQQ、SMH 或 SOXX RSI > 70，则新闻利好只作为观察，不触发加速。\n\n"
        "健康回踩定义：回撤 5%–10%，RSI 45–60，价格未明显跌破60日均线。"
    )
    card_cols[2].markdown(
        "**黄金动作**\n\n黄金按两周计划择时观察。"
        "Public 模式不展示具体补仓金额。"
    )
    st.caption(f"当前最终模式：{decision_market_mode(final_decision)}；执行纪律：{public_text(decision_risk_discipline_label(final_decision), app_mode)}")
    st.warning("新闻只用于确认主线和风险，不覆盖 do_not_chase / defense_mode；不触发自动买入、卖出或券商账户操作。")
    return


def news_final_conclusion(final_decision: dict, app_mode: dict) -> str:
    """Return the news-module conclusion from final_decision only."""

    mode = final_decision["market_mode"]
    discipline = decision_risk_discipline_code(final_decision)
    if is_public_mode(app_mode):
        if discipline == "do_not_chase":
            return "今日结论：主线可能仍在，但短线偏热；基础节奏按系统纪律执行，不追高，不展示金额。"
        conclusions = {
            "normal_dca": "今日结论：新闻仅作为辅助，按系统纪律执行，不展示金额。",
            "healthy_pullback": "今日结论：新闻与健康回踩共振时可按规则提高节奏，但不展示金额。",
            "strong_opportunity": "今日结论：新闻与回撤机会共振时可提示分批观察，但不展示金额。",
            "defense_mode": "今日结论：市场处于防守状态，新闻利好不触发加速。",
        }
        return conclusions.get(mode, conclusions["normal_dca"])
    if discipline == "do_not_chase":
        return "今日结论：新闻偏积极也只作为主线确认；按当前计划执行，不追高，不生成买入金额。"
    conclusions = {
        "normal_dca": "今日结论：新闻仅作为辅助，按当前计划执行。",
        "healthy_pullback": "今日结论：新闻与健康回踩共振时可作为观察依据，但不生成买入金额。",
        "strong_opportunity": "今日结论：新闻与回撤机会共振时需要复盘确认，但不生成买入金额。",
        "defense_mode": "今日结论：市场处于防守状态，新闻利好不触发加速。",
    }
    return conclusions.get(mode, conclusions["normal_dca"])


def render_manual_news_page(app_mode: dict) -> None:
    """Render manual news parsing page."""

    st.subheader("手动新闻解析")
    st.caption("可粘贴新闻链接、文章标题或正文。解析结果只用于研究观察和定投辅助，不自动交易。")

    raw_text = st.text_area(
        "粘贴新闻链接、标题或正文",
        height=220,
        placeholder="https://... 或者粘贴文章标题 / 正文",
    )
    if st.button("解析新闻", type="primary"):
        if not raw_text.strip():
            st.warning("请先粘贴新闻链接、标题或正文。")
            return
        st.session_state["manual_news_analysis"] = analyze_manual_news(raw_text)

    analysis = st.session_state.get("manual_news_analysis")
    if not analysis:
        return

    if analysis.get("fetched_error"):
        st.warning(analysis["fetched_error"])

    st.markdown("**文章核心观点**")
    st.write(analysis["summary"])
    col1, col2, col3 = st.columns(3)
    col1.metric("输入类型", analysis["input_type"])
    col2.metric("利好/利空方向", analysis["sentiment"])
    col3.metric("动作标签", analysis["action_tag"])

    st.write(f"涉及主题：{', '.join(analysis['matched_themes'])}")
    st.write(f"对我的持仓影响：{analysis['portfolio_impact']}")
    st.write(f"对今日定投影响：{analysis['dca_impact']}")
    st.write(f"是否进入观察池：{'是' if analysis['is_watchlist'] else '否'}")
    st.write(f"是否只是情绪噪音：{'是' if analysis['is_noise'] else '否'}")

    if is_public_mode(app_mode):
        st.button("保存到手动新闻笔记", disabled=True, help="Public 模式禁止写入本地文件。")
        return

    if st.button("保存到手动新闻笔记"):
        path = save_manual_news_note(analysis)
        st.success(f"已保存到：{path}")


def render_model_research_page(asset_table: pd.DataFrame, report_text: str) -> None:
    """Render model research/backtest placeholder without changing reports."""

    st.subheader("策略回测 / 模型研究")
    st.info("当前页面为只读研究入口，不修改回测报告，不改变 final_decision。")
    render_risk_chart(asset_table, "model_research")
    render_market_structure(report_text)
    st.caption("后续可在这里接入独立回测结果、模型参数比较和历史执行复盘。")


def render_execution_review_page(final_decision: dict, app_mode: dict) -> None:
    """Render manual execution review records."""

    st.subheader("执行复盘记录")
    if is_public_mode(app_mode):
        st.info("Public 模式隐藏执行复盘编辑。")
        return

    reviews = load_execution_reviews()
    default_row = {
        "日期": datetime.now().strftime("%Y-%m-%d"),
        "今日模式": decision_market_mode(final_decision),
        "建议基础定投金额": final_decision["daily_dca_amount"],
        "实际执行金额": final_decision["daily_dca_amount"],
        "黄金是否补仓": "",
        "灵活资金是否动用": "是" if final_decision["use_tactical_cash"] else "否",
        "备注": "",
    }
    st.caption("用于手动记录实际执行，不自动交易，不连接账户。")
    if reviews.empty:
        reviews = pd.DataFrame([default_row], columns=EXECUTION_REVIEW_COLUMNS)
    edited = st.data_editor(
        reviews,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="execution_review_editor",
    )
    if st.button("保存执行复盘记录", type="primary"):
        backup_path = backup_file(EXECUTION_REVIEW_PATH, "execution_review", ".csv")
        normalized = normalize_execution_reviews(edited)
        normalized.to_csv(EXECUTION_REVIEW_PATH, index=False, encoding="utf-8-sig")
        st.success(f"执行复盘记录已保存，旧文件已备份到：{backup_path}")


def load_execution_reviews() -> pd.DataFrame:
    """Load execution review records."""

    if not EXECUTION_REVIEW_PATH.exists():
        return pd.DataFrame(columns=EXECUTION_REVIEW_COLUMNS)
    try:
        data = pd.read_csv(EXECUTION_REVIEW_PATH, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=EXECUTION_REVIEW_COLUMNS)
    return normalize_execution_reviews(data)


def normalize_execution_reviews(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize execution review records before display/save."""

    normalized = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(columns=EXECUTION_REVIEW_COLUMNS)
    for column in EXECUTION_REVIEW_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""
    normalized = normalized[EXECUTION_REVIEW_COLUMNS]
    text_view = normalized.fillna("").astype(str)
    blank_rows = text_view.apply(lambda row: row.str.strip().eq("").all(), axis=1)
    return normalized.loc[~blank_rows].copy()


def render_market_structure(report_text: str) -> None:
    """Render market-structure interpretation."""

    st.subheader("市场结构解读")
    section = extract_section(report_text, "市场结构解读")
    if not section:
        st.info("当前报告尚未包含市场结构解读。点击“重新生成报告”后可查看新版解释层。")
        return

    st.markdown(section)

    # 从结构解读中提取四个核心观察问题，方便首页快速扫读。
    structure_items = [
        ("科技成长是否强", find_sentence(section, ["科技成长", "成长风格"])),
        ("半导体是否强", find_sentence(report_text, ["半导体", "AI/半导体"])),
        ("黄金/美债是否提供防守", find_sentence(section, ["黄金", "美债", "防守"])),
        ("美元是否对风险资产构成压力", find_sentence(section, ["美元", "压力"])),
    ]

    cols = st.columns(4)
    for col, (title, body) in zip(cols, structure_items):
        col.markdown(f"**{title}**")
        col.write(body or "暂无明确结论")



def sanitize_full_report_for_display(report_text: str) -> str:
    """Hide stale report decision blocks that are superseded by final_decision."""

    if not report_text:
        return report_text
    replacement = (
        "## \u6211\u7684\u6bcf\u65e5\u5b9a\u6295\u51b3\u7b56\n\n"
        "> \u9875\u9762\u5df2\u7edf\u4e00\u7531 final_decision \u8986\u76d6\u4eca\u65e5\u51b3\u7b56\u3002\u8bf7\u4ee5\u4e0a\u65b9\u201c\u6bcf\u65e5\u5b9a\u6295\u51b3\u7b56 / Clayton Alpha Model / \u65b0\u95fb\u5bf9\u4eca\u65e5\u5b9a\u6295\u5f71\u54cd\u201d\u4e3a\u51c6\uff1b"
        "\u65e7\u65e5\u62a5\u4e2d\u7684\u65e7\u5f15\u64ce\u6a21\u5f0f\u3001\u65e7\u91d1\u989d\u548c\u673a\u52a8\u8d44\u91d1\u4f59\u989d\u4e0d\u518d\u4f5c\u4e3a\u6700\u7ec8\u663e\u793a\u3002\n"
    )
    return re.sub(
        "## \u6211\u7684\u6bcf\u65e5\u5b9a\u6295\u51b3\u7b56\\s*\\n.*?(?=\\n## |\\Z)",
        replacement,
        report_text,
        flags=re.S,
    )


def render_full_report(report_text: str) -> None:
    """Render full Markdown report."""

    st.subheader("完整 Markdown 报告原文")
    if not report_text:
        st.info("暂无日报原文，请先运行 python main.py。")
        return

    st.markdown(sanitize_full_report_for_display(report_text))


def parse_asset_table(report_text: str) -> pd.DataFrame:
    """Parse the asset table from the Markdown report."""

    # 找到包含“资产”和“风险状态”的 Markdown 表格作为资产风险表。
    lines = report_text.splitlines()
    table_lines = []
    capture = False

    for line in lines:
        if line.startswith("| 资产 |") and "风险状态" in line:
            capture = True
        if capture and line.startswith("|"):
            table_lines.append(line)
        elif capture:
            break

    if len(table_lines) < 3:
        return pd.DataFrame()

    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(cells)

    table = pd.DataFrame(rows, columns=headers)

    # 增加数值列，供指标卡片计算使用。
    table["RSI数值"] = table["RSI"].map(parse_number)
    table["当前回撤数值"] = table["当前回撤"].map(parse_percent)
    return table


def parse_markdown_table(report_text: str, first_header: str) -> pd.DataFrame:
    """Parse a Markdown table by its first header name."""

    lines = report_text.splitlines()
    table_lines = []
    capture = False

    for line in lines:
        if line.startswith(f"| {first_header} |"):
            capture = True
        if capture and line.startswith("|"):
            table_lines.append(line)
        elif capture:
            break

    if len(table_lines) < 3:
        return pd.DataFrame()

    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(cells)

    return pd.DataFrame(rows, columns=headers)


def parse_news_items(news_text: str) -> pd.DataFrame:
    """Parse news bullet items from Markdown text."""

    rows = []
    for line in news_text.splitlines():
        if not line.startswith("- [") or "主题：" not in line:
            continue
        title_match = re.search(r"- \[(.*?)\]\((.*?)\)", line)
        if not title_match:
            continue
        title = title_match.group(1)
        url = title_match.group(2)
        source = extract_pipe_value(line, "来源")
        published_at = extract_pipe_value(line, "时间")
        themes = [theme.strip() for theme in extract_pipe_value(line, "主题").split(",") if theme.strip()]
        direction = extract_pipe_value(line, "方向")
        impact = extract_pipe_value(line, "影响")
        need_attention = "需要关注" in line
        rows.append(
            {
                "title": title,
                "url": url,
                "source": source,
                "published_at": published_at,
                "themes": themes,
                "impact_direction": direction,
                "portfolio_impact": impact,
                "need_attention": need_attention,
            }
        )
    return pd.DataFrame(rows)


def load_latest_news_items(news_csv: Path | None, news_text: str) -> pd.DataFrame:
    """Load latest news items from CSV first, then Markdown fallback."""

    if news_csv and news_csv.exists():
        try:
            data = pd.read_csv(news_csv)
            if "matched_themes" in data.columns:
                data["themes"] = data["matched_themes"].fillna("").map(
                    lambda value: [theme.strip() for theme in str(value).split(",") if theme.strip()]
                )
            elif "themes" in data.columns:
                data["themes"] = data["themes"].fillna("").map(
                    lambda value: [theme.strip() for theme in str(value).split(",") if theme.strip()]
                )
            else:
                data["themes"] = [[] for _ in range(len(data))]
            if "need_attention" not in data.columns:
                data["need_attention"] = data.get("importance_score", 0).fillna(0).astype(float) >= 5
            return data
        except Exception:
            return parse_news_items(news_text)

    return parse_news_items(news_text)


def extract_pipe_value(line: str, label: str) -> str:
    """Extract a value from a pipe-delimited news bullet."""

    match = re.search(rf"{label}：([^|]+)", line)
    return match.group(1).strip() if match else ""


def load_yaml(path: Path) -> dict:
    """Load YAML file if it exists."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_yaml(path: Path, payload: dict) -> None:
    """Write YAML using safe_dump."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)


def backup_yaml(path: Path, prefix: str) -> Path:
    """Back up a YAML file before overwriting it."""

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"{prefix}_{timestamp}.yaml"
    if path.exists():
        shutil.copy2(path, backup_path)
    else:
        backup_path.write_text("# original file did not exist\n", encoding="utf-8")
    return backup_path


def backup_file(path: Path, prefix: str, suffix: str) -> Path:
    """Back up a local file before overwriting it."""

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"{prefix}_{timestamp}{suffix}"
    if path.exists():
        shutil.copy2(path, backup_path)
    else:
        backup_path.write_text("# original file did not exist\n", encoding="utf-8")
    return backup_path


def merge_edited_funds(original: pd.DataFrame, edited: pd.DataFrame) -> pd.DataFrame:
    """Merge editable columns back into the original fund table."""

    # 只覆盖页面展示的编辑列，避免 proxy_symbol 等内部字段被误删。
    result = original.copy()
    for column in edited.columns:
        result[column] = edited[column]
    return result


def normalize_funds_for_yaml(funds: pd.DataFrame) -> list[dict]:
    """Normalize portfolio rows for YAML serialization."""

    numeric_columns = {
        "current_amount": float,
        "base_daily_dca": float,
        "max_daily_dca": float,
        "target_weight": float,
        "priority_rank": int,
    }
    boolean_columns = {"is_high_volatility", "is_core_holding"}
    records = []

    for row in funds.where(pd.notna(funds), None).to_dict("records"):
        normalized = {}
        for key, value in row.items():
            if key in numeric_columns and value is not None:
                normalized[key] = numeric_columns[key](value)
            elif key in boolean_columns and value is not None:
                normalized[key] = bool(value)
            else:
                normalized[key] = to_builtin(value)
        records.append(normalized)
    return records


def normalize_policy_for_yaml(policy: dict) -> dict:
    """Normalize policy values for YAML serialization."""

    return {
        "base_daily_budget": float(policy["base_daily_budget"]),
        "max_daily_budget": float(policy["max_daily_budget"]),
        "tactical_cash": float(policy["tactical_cash"]),
        "max_drawdown_tolerance": float(policy["max_drawdown_tolerance"]),
        "gold_target_weight_min": float(policy["gold_target_weight_min"]),
        "gold_target_weight_max": float(policy["gold_target_weight_max"]),
        "high_volatility_max_weight": float(policy["high_volatility_max_weight"]),
        "tactical_cash_tranches": int(policy["tactical_cash_tranches"]),
        "single_tranche_amount": float(policy["single_tranche_amount"]),
    }


def to_builtin(value):
    """Convert pandas/numpy scalar values to plain Python values."""

    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value
    return value


def run_main_py() -> subprocess.CompletedProcess:
    """Run main.py and return the completed process."""

    return subprocess.run(
        [sys.executable, str(ROOT_DIR / "main.py")],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def show_main_run_result(result: subprocess.CompletedProcess) -> None:
    """Show main.py execution result without crashing the page."""

    if result.returncode == 0:
        st.success("已重新运行 main.py 并生成新的报告。")
        if result.stdout:
            st.code(result.stdout)
    else:
        st.error("main.py 运行失败，配置已保存但报告未成功生成。")
        if result.stderr:
            st.code(result.stderr)
        elif result.stdout:
            st.code(result.stdout)


def path_mtime(path: Path | None) -> datetime | None:
    """Return file modification time."""

    if path is None or not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)


def format_path_mtime(path: Path | None) -> str:
    """Format file modification time."""

    return format_datetime(path_mtime(path))


def format_datetime(value: datetime | None) -> str:
    """Format datetime for display."""

    if value is None:
        return "暂无"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def latest_existing_path(paths: list[Path]) -> Path | None:
    """Return the most recently modified existing path."""

    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def latest_backup_time(prefix: str) -> datetime | None:
    """Return latest backup time by prefix."""

    backups = sorted(BACKUPS_DIR.glob(f"{prefix}_*.yaml"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not backups:
        return None
    return path_mtime(backups[0])


def extract_subsection(section_text: str, subsection_title: str) -> str:
    """Extract a third-level subsection from section text."""

    pattern = rf"### {re.escape(subsection_title)}\n\n(.*?)(?=\n### |\Z)"
    match = re.search(pattern, section_text, flags=re.S)
    return match.group(1).strip() if match else ""


def extract_report_date(report_path: Path, report_text: str) -> str:
    """Extract report date from title or file name."""

    # 优先从标题读取日期，失败时使用文件名中的日期。
    title_match = re.search(r"Daily Report - (\d{4}-\d{2}-\d{2})", report_text)
    if title_match:
        return title_match.group(1)

    file_match = re.search(r"daily_risk_report_(\d{4}-\d{2}-\d{2})", report_path.name)
    return file_match.group(1) if file_match else "unknown"


def extract_market_status(report_text: str) -> str:
    """Extract overall market status from Markdown text."""

    match = re.search(r"市场状态：\*\*(risk-on|neutral|risk-off)\*\*", report_text)
    return match.group(1) if match else "unknown"


def extract_section(report_text: str, section_title: str) -> str:
    """Extract one Markdown section by title."""

    pattern = rf"## {re.escape(section_title)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, report_text, flags=re.S)
    return match.group(1).strip() if match else ""


def find_sentence(text: str, keywords: list[str]) -> str:
    """Find the first bullet sentence containing all keywords."""

    # 简单搜索 bullet 文本，避免引入复杂 Markdown 解析器。
    for line in text.splitlines():
        if line.startswith("- ") and all(keyword in line for keyword in keywords):
            return line[2:].strip()
    for line in text.splitlines():
        if line.startswith("- ") and any(keyword in line for keyword in keywords):
            return line[2:].strip()
    return ""


def parse_number(value: str) -> float:
    """Parse a plain numeric string."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_percent(value: str) -> float:
    """Parse a percentage string into decimal form."""

    try:
        return float(str(value).replace("%", "")) / 100
    except (TypeError, ValueError):
        return float("nan")


def color_risk_status(value: str) -> str:
    """Return CSS for risk status labels."""

    if value == "risk-on":
        return "background-color: #dcfce7; color: #166534; font-weight: 600"
    if value == "neutral":
        return "background-color: #fef9c3; color: #854d0e; font-weight: 600"
    if value == "risk-off":
        return "background-color: #fee2e2; color: #991b1b; font-weight: 600"
    return ""


if __name__ == "__main__":
    main()

