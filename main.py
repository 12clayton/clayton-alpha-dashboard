"""One-click entry point for the Global QDII risk monitor."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.data_fetcher import fetch_price_data
from src.dca_decision_engine import build_dca_decision
from src.fund_nav_provider import update_fund_nav_cache
from src.indicators import build_indicator_table
from src.news_digest import build_news_digest
from src.report_generator import generate_markdown_report
from src.risk_model import classify_asset_risk, summarize_market_regime


CONFIG_PATH = Path("config/assets.yaml")


def main() -> None:
    """Run the full research workflow."""

    # 第一步：读取资产配置和风险模型参数。
    config = load_config(CONFIG_PATH)
    assets = config["assets"]
    risk_rules = config.get("risk_rules", {})

    # 第二步：获取价格数据；如果线上数据失败，会自动尝试缓存。
    prices, data_quality = fetch_price_data(
        assets=assets,
        period="1y",
        cache_path=Path("data/price_cache.csv"),
    )

    # 第三步：计算均线、RSI、最大回撤等指标。
    indicator_table = build_indicator_table(
        prices=prices,
        short_window=risk_rules.get("short_ma_window", 20),
        long_window=risk_rules.get("long_ma_window", 60),
        rsi_window=risk_rules.get("rsi_window", 14),
    )

    # 第四步：根据指标和数据质量判断每个资产的风险状态。
    risk_table = classify_asset_risk(
        indicator_table=indicator_table,
        data_quality=data_quality,
        risk_rules=risk_rules,
    )

    # 第五步：汇总总体市场状态，作为报告开头的总览。
    market_regime, market_reason = summarize_market_regime(risk_table)

    # 第六步：生成每日投资资讯摘要；抓取失败时模块会降级为提示，不自动交易。
    news_digest = build_news_digest(
        sources_path=Path("config/news_sources.yaml"),
        keywords_path=Path("config/news_keywords.yaml"),
        report_dir=Path("reports"),
    )

    # 第七步：生成每日定投辅助决策；只输出研究观察，不连接交易账户。
    dca_decision = build_dca_decision(
        risk_table=risk_table,
        market_regime=market_regime,
        news_digest=news_digest,
        portfolio_path=Path("config/portfolio.yaml"),
        policy_path=Path("config/dca_policy.yaml"),
    )

    # 第八步：更新基金真实净值缓存；失败时页面会显示 missing_nav，不影响日报生成。
    update_fund_nav_cache(
        portfolio_path=Path("config/portfolio.yaml"),
        cache_path=Path("data/fund_nav_cache.csv"),
        aliases_path=Path("config/fund_code_aliases.yaml"),
    )

    # 第九步：生成每日 Markdown 报告。
    report_path = generate_markdown_report(
        risk_table=risk_table,
        assets=assets,
        market_regime=market_regime,
        market_reason=market_reason,
        dca_decision=dca_decision,
        news_digest=news_digest,
        report_dir=Path("reports"),
    )

    # 第十步：在终端输出报告位置，便于用户快速打开查看。
    print(f"Daily risk report generated: {report_path}")


def load_config(config_path: Path) -> dict:
    """Load YAML configuration from disk."""

    # 配置文件是项目的研究资产入口，缺失时直接提示明确错误。
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # 使用 safe_load 读取 YAML，避免执行任何非数据内容。
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # 做最基础的配置校验，保证后续流程拿到资产列表。
    if not config or "assets" not in config:
        raise ValueError("config/assets.yaml must contain an assets list.")

    return config


if __name__ == "__main__":
    main()
