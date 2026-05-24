"""Backtest pure DCA vs opportunity-tier DCA for QDII proxy assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


START_DATE = "2010-01-01"
END_DATE = "2018-12-31"
DOWNLOAD_END_DATE = "2019-01-01"

REPORT_DIR = Path("reports")
SUMMARY_PATH = REPORT_DIR / "backtest_2010_2018_summary.md"
RESULTS_PATH = REPORT_DIR / "backtest_2010_2018_results.csv"
TACTICAL_LOG_PATH = REPORT_DIR / "backtest_2010_2018_tactical_cash_log.csv"

CORE_WEIGHTS = {
    "QQQ": 0.40,
    "SEMI": 0.30,
    "SPY": 0.20,
    "GLD": 0.10,
}
TACTICAL_WEIGHTS = {
    "SEMI": 0.70,
    "QQQ": 0.20,
    "GLD": 0.10,
}


@dataclass
class BacktestConfig:
    start_date: str = START_DATE
    end_date: str = END_DATE
    base_daily_amount: float = 60.0
    opportunity_daily_amount: float = 100.0
    tactical_cash_total: float = 5000.0
    level2_tactical_amount: float = 500.0
    level3_tactical_amount: float = 1000.0
    single_tactical_cap: float = 1000.0
    max_acceptable_drawdown: float = -0.20
    rsi_window: int = 14
    ma_window: int = 60
    recent_high_window: int = 252


@dataclass
class PortfolioState:
    units: dict[str, float]
    invested: float = 0.0
    tactical_cash_remaining: float = 0.0


def main() -> None:
    """Run the backtest and write report files."""

    config = BacktestConfig()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    prices, download_error = download_prices()
    if download_error:
        write_error_outputs(download_error)
        print(f"Backtest failed: {download_error}")
        return

    selected_prices, semi_symbol, data_note = select_backtest_assets(prices, config)
    if selected_prices.empty:
        message = "No usable price data after applying the requested backtest window."
        write_error_outputs(message)
        print(f"Backtest failed: {message}")
        return

    indicators = build_indicators(selected_prices, config)
    pure_result = run_strategy(
        prices=selected_prices,
        indicators=indicators,
        config=config,
        semi_symbol=semi_symbol,
        strategy="pure_dca",
    )
    system_result = run_strategy(
        prices=selected_prices,
        indicators=indicators,
        config=config,
        semi_symbol=semi_symbol,
        strategy="system_dca",
    )

    results = pd.DataFrame([pure_result["metrics"], system_result["metrics"]])
    results.to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")

    tactical_log = pd.DataFrame(system_result["tactical_log"])
    tactical_columns = ["date", "level", "amount", "allocation", "trigger_reason", "cash_remaining"]
    if tactical_log.empty:
        tactical_log = pd.DataFrame(columns=tactical_columns)
    tactical_log = tactical_log.reindex(columns=tactical_columns)
    tactical_log.to_csv(TACTICAL_LOG_PATH, index=False, encoding="utf-8-sig")

    write_summary(
        results=results,
        pure_metrics=pure_result["metrics"],
        system_metrics=system_result["metrics"],
        tactical_log=tactical_log,
        semi_symbol=semi_symbol,
        data_note=data_note,
        config=config,
        start_date=selected_prices.index[0].date().isoformat(),
        end_date=selected_prices.index[-1].date().isoformat(),
    )

    print(f"Backtest completed. Summary: {SUMMARY_PATH}")
    print(f"Results CSV: {RESULTS_PATH}")
    print(f"Tactical cash log: {TACTICAL_LOG_PATH}")


def download_prices() -> tuple[pd.DataFrame, str | None]:
    """Download adjusted close prices and keep failures non-fatal."""

    symbols = ["QQQ", "SMH", "SOXX", "SPY", "GLD"]
    try:
        import yfinance as yf

        raw = yf.download(
            tickers=symbols,
            start=START_DATE,
            end=DOWNLOAD_END_DATE,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception as exc:
        return pd.DataFrame(), f"yfinance data download failed: {exc}"

    if raw.empty:
        return pd.DataFrame(), "yfinance returned an empty dataset."

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns.get_level_values(0):
            return pd.DataFrame(), "yfinance response did not contain Close prices."
        prices = raw["Close"].copy()
    else:
        prices = raw[["Close"]].copy()
        prices.columns = symbols[:1]

    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()
    for symbol in symbols:
        if symbol not in prices.columns:
            prices[symbol] = pd.NA

    prices = prices.reindex(columns=symbols).dropna(how="all")
    return prices, None


def select_backtest_assets(prices: pd.DataFrame, config: BacktestConfig) -> tuple[pd.DataFrame, str, str]:
    """Choose SMH or SOXX and trim to the valid common backtest window."""

    note_parts = []
    start_timestamp = pd.Timestamp(config.start_date)
    start_tolerance = start_timestamp + pd.Timedelta(days=10)

    smh_first = first_valid_date(prices.get("SMH"))
    soxx_first = first_valid_date(prices.get("SOXX"))
    if smh_first is not None and smh_first <= start_tolerance:
        semi_symbol = "SMH"
        note_parts.append("SMH has usable data from the first trading days of the requested window.")
    elif soxx_first is not None and soxx_first <= start_tolerance:
        semi_symbol = "SOXX"
        note_parts.append("SMH data was insufficient near the requested start date, so SOXX was used for the semiconductor sleeve.")
    elif smh_first is not None:
        semi_symbol = "SMH"
        note_parts.append(f"SMH and SOXX were not usable near the requested start date; backtest starts from {smh_first.date().isoformat()}.")
    elif soxx_first is not None:
        semi_symbol = "SOXX"
        note_parts.append(f"SMH was unavailable and SOXX starts from {soxx_first.date().isoformat()}; backtest starts from that available date.")
    else:
        return pd.DataFrame(), "SEMI", "No usable semiconductor proxy data was available."

    selected = pd.DataFrame(
        {
            "QQQ": prices["QQQ"],
            "SEMI": prices[semi_symbol],
            "SPY": prices["SPY"],
            "GLD": prices["GLD"],
        }
    )
    valid_starts = [first_valid_date(selected[column]) for column in selected.columns]
    valid_starts = [date for date in valid_starts if date is not None]
    if not valid_starts:
        return pd.DataFrame(), semi_symbol, "No selected asset had usable data."

    actual_start = max([start_timestamp, *valid_starts])
    selected = selected.loc[actual_start : pd.Timestamp(config.end_date)].dropna(how="any")
    if selected.empty:
        return selected, semi_symbol, "Selected assets had no complete overlapping data."

    if selected.index[0] > start_timestamp:
        note_parts.append(f"Common complete data begins on {selected.index[0].date().isoformat()}; earlier dates were excluded.")

    return selected, semi_symbol, " ".join(note_parts)


def first_valid_date(series: pd.Series | None) -> pd.Timestamp | None:
    """Return the first non-null timestamp in a price series."""

    if series is None:
        return None
    clean = series.dropna()
    if clean.empty:
        return None
    return pd.Timestamp(clean.index[0])


def build_indicators(prices: pd.DataFrame, config: BacktestConfig) -> dict[str, pd.DataFrame]:
    """Calculate RSI, 60-day moving average and rolling drawdown without future data."""

    rsi_table = prices.apply(lambda column: calculate_rsi(column, config.rsi_window))
    ma_table = prices.rolling(window=config.ma_window, min_periods=config.ma_window).mean()
    recent_high = prices.rolling(
        window=config.recent_high_window,
        min_periods=1,
    ).max()
    drawdown = prices / recent_high - 1
    return {
        "rsi": rsi_table,
        "ma60": ma_table,
        "drawdown": drawdown,
    }


def calculate_rsi(price: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI from current and previous prices only."""

    delta = price.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + relative_strength))


def run_strategy(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    config: BacktestConfig,
    semi_symbol: str,
    strategy: str,
) -> dict[str, Any]:
    """Run one DCA strategy over the selected price history."""

    state = PortfolioState(
        units={symbol: 0.0 for symbol in CORE_WEIGHTS},
        tactical_cash_remaining=config.tactical_cash_total if strategy == "system_dca" else 0.0,
    )
    daily_rows = []
    tactical_log = []

    for date, price_row in prices.iterrows():
        portfolio_value_before = calculate_portfolio_value(state.units, price_row)
        current_drawdown = calculate_current_drawdown(daily_rows, portfolio_value_before)

        daily_amount = config.base_daily_amount
        level = 0
        level_reason = "Level 0: no clear pullback opportunity."
        tactical_amount = 0.0
        tactical_allocation: dict[str, float] = {}

        if strategy == "system_dca":
            level, level_reason = classify_opportunity_level(date, price_row, indicators)
            if level >= 1:
                daily_amount = config.opportunity_daily_amount
            tactical_amount, tactical_allocation = build_tactical_allocation(
                date=date,
                prices=price_row,
                level=level,
                indicators=indicators,
                config=config,
                state=state,
                current_drawdown=current_drawdown,
            )

        invest_by_weight(state, price_row, daily_amount, CORE_WEIGHTS)

        if tactical_amount > 0 and tactical_allocation:
            invest_by_weight(state, price_row, tactical_amount, tactical_allocation)
            state.tactical_cash_remaining -= tactical_amount
            tactical_log.append(
                {
                    "date": date.date().isoformat(),
                    "level": f"Level {level}",
                    "amount": round(tactical_amount, 2),
                    "allocation": format_allocation(tactical_allocation, semi_symbol),
                    "trigger_reason": level_reason,
                    "cash_remaining": round(state.tactical_cash_remaining, 2),
                }
            )

        end_value = calculate_portfolio_value(state.units, price_row)
        market_return = 0.0
        if daily_rows and daily_rows[-1]["portfolio_value"] > 0:
            market_return = portfolio_value_before / daily_rows[-1]["portfolio_value"] - 1
        daily_rows.append(
            {
                "date": date,
                "strategy": strategy,
                "portfolio_value": end_value,
                "invested": state.invested,
                "daily_amount": daily_amount,
                "tactical_amount": tactical_amount,
                "market_return": market_return,
                "level": level,
            }
        )

    daily_result = pd.DataFrame(daily_rows).set_index("date")
    metrics = calculate_metrics(
        daily_result=daily_result,
        strategy=strategy,
        tactical_log=tactical_log,
        config=config,
    )
    return {
        "daily_result": daily_result,
        "metrics": metrics,
        "tactical_log": tactical_log,
    }


def classify_opportunity_level(
    date: pd.Timestamp,
    prices: pd.Series,
    indicators: dict[str, pd.DataFrame],
) -> tuple[int, str]:
    """Classify the daily opportunity level using QQQ and semiconductor data."""

    checks = []
    for symbol in ["QQQ", "SEMI"]:
        rsi = indicators["rsi"].at[date, symbol]
        ma60 = indicators["ma60"].at[date, symbol]
        drawdown = indicators["drawdown"].at[date, symbol]
        price = prices[symbol]
        if pd.isna(rsi) or pd.isna(ma60) or pd.isna(drawdown):
            continue
        checks.append(
            {
                "symbol": symbol,
                "rsi": float(rsi),
                "above_ma": bool(price >= ma60),
                "near_ma": bool(price >= ma60 * 0.97),
                "drawdown": float(drawdown),
            }
        )

    level3 = [
        item for item in checks
        if -0.15 <= item["drawdown"] <= -0.10 and 35 <= item["rsi"] <= 50 and item["near_ma"]
    ]
    if level3:
        return 3, build_level_reason(level3, "10%-15% drawdown, RSI 35-50, price not clearly below 60-day MA")

    level2 = [
        item for item in checks
        if -0.10 <= item["drawdown"] <= -0.05 and 45 <= item["rsi"] <= 60 and item["above_ma"]
    ]
    if level2:
        return 2, build_level_reason(level2, "5%-10% drawdown, RSI 45-60, price above 60-day MA")

    level1 = [
        item for item in checks
        if 45 <= item["rsi"] <= 60 and item["above_ma"]
    ]
    if level1:
        return 1, build_level_reason(level1, "RSI 45-60 and price above 60-day MA")

    return 0, "Level 0: no clear pullback opportunity."


def build_level_reason(items: list[dict[str, Any]], condition: str) -> str:
    """Build a readable trigger reason."""

    symbols = ", ".join(item["symbol"] for item in items)
    details = "; ".join(
        f"{item['symbol']} drawdown {item['drawdown']:.2%}, RSI {item['rsi']:.1f}" for item in items
    )
    return f"{symbols} met {condition}. {details}."


def build_tactical_allocation(
    date: pd.Timestamp,
    prices: pd.Series,
    level: int,
    indicators: dict[str, pd.DataFrame],
    config: BacktestConfig,
    state: PortfolioState,
    current_drawdown: float,
) -> tuple[float, dict[str, float]]:
    """Return tactical cash amount and allocation when all constraints pass."""

    if level not in {2, 3}:
        return 0.0, {}
    if state.tactical_cash_remaining <= 0:
        return 0.0, {}
    if current_drawdown <= config.max_acceptable_drawdown:
        return 0.0, {}

    qqq_rsi = indicators["rsi"].at[date, "QQQ"]
    semi_rsi = indicators["rsi"].at[date, "SEMI"]
    if (not pd.isna(qqq_rsi) and qqq_rsi > 70) or (not pd.isna(semi_rsi) and semi_rsi > 70):
        return 0.0, {}

    qqq_ma = indicators["ma60"].at[date, "QQQ"]
    semi_ma = indicators["ma60"].at[date, "SEMI"]
    qqq_below_ma = not pd.isna(qqq_ma) and prices["QQQ"] < qqq_ma
    semi_below_ma = not pd.isna(semi_ma) and prices["SEMI"] < semi_ma

    if not TACTICAL_WEIGHTS:
        return 0.0, {}

    if qqq_below_ma and semi_below_ma:
        return 0.0, {}

    requested = config.level3_tactical_amount if level == 3 else config.level2_tactical_amount
    amount = min(requested, config.single_tactical_cap, state.tactical_cash_remaining)
    if amount <= 0:
        return 0.0, {}
    return amount, TACTICAL_WEIGHTS.copy()


def invest_by_weight(
    state: PortfolioState,
    prices: pd.Series,
    amount: float,
    weights: dict[str, float],
) -> None:
    """Buy fractional units according to the supplied weights."""

    if amount <= 0:
        return
    for symbol, weight in weights.items():
        cash = amount * weight
        state.units[symbol] += cash / float(prices[symbol])
    state.invested += amount


def calculate_portfolio_value(units: dict[str, float], prices: pd.Series) -> float:
    """Mark portfolio value to market."""

    return float(sum(units[symbol] * float(prices[symbol]) for symbol in units))


def calculate_current_drawdown(daily_rows: list[dict[str, Any]], value: float) -> float:
    """Calculate current drawdown from past portfolio values only."""

    if not daily_rows:
        return 0.0
    previous_peak = max(row["portfolio_value"] for row in daily_rows)
    if previous_peak <= 0:
        return 0.0
    return value / previous_peak - 1


def calculate_metrics(
    daily_result: pd.DataFrame,
    strategy: str,
    tactical_log: list[dict[str, Any]],
    config: BacktestConfig,
) -> dict[str, Any]:
    """Calculate headline performance metrics."""

    values = daily_result["portfolio_value"]
    invested = float(daily_result["invested"].iloc[-1])
    ending_value = float(values.iloc[-1])
    total_return = ending_value / invested - 1 if invested > 0 else 0.0
    years = max((daily_result.index[-1] - daily_result.index[0]).days / 365.25, 1 / 365.25)
    annualized_return = (ending_value / invested) ** (1 / years) - 1 if invested > 0 else 0.0
    drawdown = values / values.cummax() - 1
    max_drawdown = float(drawdown.min())
    daily_returns = daily_result["market_return"].iloc[1:].dropna()
    sharpe = 0.0
    if not daily_returns.empty and daily_returns.std() != 0:
        sharpe = float((daily_returns.mean() / daily_returns.std()) * (252 ** 0.5))

    return {
        "strategy": strategy,
        "total_invested": round(invested, 2),
        "ending_value": round(ending_value, 2),
        "total_return": round(total_return, 6),
        "annualized_return": round(annualized_return, 6),
        "max_drawdown": round(max_drawdown, 6),
        "sharpe_ratio": round(sharpe, 6),
        "tactical_cash_uses": len(tactical_log),
        "tactical_cash_total_used": 0.0 if strategy == "pure_dca" else round(sum(item["amount"] for item in tactical_log), 2),
    }


def format_allocation(allocation: dict[str, float], semi_symbol: str) -> str:
    """Format tactical allocation for CSV and Markdown outputs."""

    names = {"SEMI": semi_symbol, "QQQ": "QQQ", "GLD": "GLD"}
    return "; ".join(f"{names.get(symbol, symbol)} {weight:.0%}" for symbol, weight in allocation.items())


def write_summary(
    results: pd.DataFrame,
    pure_metrics: dict[str, Any],
    system_metrics: dict[str, Any],
    tactical_log: pd.DataFrame,
    semi_symbol: str,
    data_note: str,
    config: BacktestConfig,
    start_date: str,
    end_date: str,
) -> None:
    """Write the Markdown summary report."""

    excess_profit = system_metrics["ending_value"] - pure_metrics["ending_value"]
    better = excess_profit > 0
    keep_decision = "值得保留" if better else "暂不值得保留"
    keep_reason = (
        "策略B在本次历史区间内期末资产高于普通定投。"
        if better
        else "策略B在本次历史区间内没有跑赢普通定投，或额外复杂度没有得到收益补偿。"
    )

    metrics_table = results.copy()
    for column in ["total_return", "annualized_return", "max_drawdown"]:
        metrics_table[column] = metrics_table[column].map(lambda value: f"{value:.2%}")
    metrics_table["sharpe_ratio"] = metrics_table["sharpe_ratio"].map(lambda value: f"{value:.2f}")

    if tactical_log.empty:
        tactical_section = "本次回测没有触发机动资金使用。"
    else:
        tactical_section = dataframe_to_markdown(tactical_log)

    content = f"""# Backtest 2010-2018: pure_dca vs system_dca

## 回测范围

- 区间：{start_date} 至 {end_date}
- 资产代理：QQQ 40%，{semi_symbol} 30%，SPY 20%，GLD 10%
- 半导体代理说明：{data_note}
- 资金口径：使用人民币投入金额购买美元计价 ETF 代理份额，未建模汇率、申赎费、基金溢价、税费和滑点；两组策略使用同一口径，便于相对比较。
- 指标计算：RSI、60日均线和近期高点回撤均只使用当日及历史数据，不使用未来数据。

## 策略参数

- 策略A pure_dca：每个交易日固定投入 ¥{config.base_daily_amount:.0f}，按目标权重分配，不使用机动资金。
- 策略B system_dca：正常每日 ¥{config.base_daily_amount:.0f}；Level 1/2/3 每日 ¥{config.opportunity_daily_amount:.0f}；机动资金总额 ¥{config.tactical_cash_total:.0f}，单次最高 ¥{config.single_tactical_cap:.0f}。
- Level 2 机动资金：¥{config.level2_tactical_amount:.0f}；Level 3 机动资金：¥{config.level3_tactical_amount:.0f}；投向为半导体 70%、QQQ 20%、GLD 10%。
- 禁止机动资金：QQQ 或半导体 RSI > 70、组合当前回撤超过 -20%、没有明确 allocation_plan、机动资金用完等情况。

## 核心结果

{dataframe_to_markdown(metrics_table)}

## 策略B相对策略A

- 策略B期末资产比策略A：{excess_profit:,.2f} 元
- 结论：{keep_decision}
- 判断：{keep_reason}

## 机动资金使用记录

{tactical_section}

## 风险提示

历史回测不代表未来收益。本报告仅用于研究和策略复盘，不构成投资建议，也不代表任何基金或 ETF 的未来表现。
"""
    SUMMARY_PATH.write_text(content, encoding="utf-8")


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    """Render a small DataFrame as a Markdown table without optional dependencies."""

    if frame.empty:
        return ""
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in frame.columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_error_outputs(message: str) -> None:
    """Write failure reports without crashing the program."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "strategy": "error",
                "error": message,
            }
        ]
    ).to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["date", "level", "amount", "allocation", "trigger_reason", "cash_remaining"]).to_csv(
        TACTICAL_LOG_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    SUMMARY_PATH.write_text(
        f"""# Backtest 2010-2018: failed

数据下载或处理失败，程序已停止且未崩溃。

错误原因：{message}

历史回测不代表未来收益。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
