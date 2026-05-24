"""Backtest Clayton Nasdaq-Plus Aggressive Model against QQQ DCA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


START_DATE = "2006-01-01"
END_DATE = "2025-12-31"
DOWNLOAD_END_DATE = "2026-01-01"

REPORT_DIR = Path("reports")
SUMMARY_PATH = REPORT_DIR / "nasdaq_plus_aggressive_summary.md"
RESULTS_PATH = REPORT_DIR / "nasdaq_plus_aggressive_results.csv"
YEARLY_PATH = REPORT_DIR / "nasdaq_plus_aggressive_yearly.csv"
TACTICAL_LOG_PATH = REPORT_DIR / "nasdaq_plus_aggressive_tactical_cash_log.csv"

PERIODS = {
    "train_2006_2015": ("2006-01-01", "2015-12-31"),
    "validation_2016_2020": ("2016-01-01", "2020-12-31"),
    "live_check_2021_2025": ("2021-01-01", "2025-12-31"),
    "full_2006_2025": ("2006-01-01", "2025-12-31"),
    "out_of_sample_2016_2025": ("2016-01-01", "2025-12-31"),
}


@dataclass
class BacktestConfig:
    start_date: str = START_DATE
    end_date: str = END_DATE
    rsi_window: int = 14
    ma_window: int = 60
    recent_high_window: int = 252
    normal_daily_amount: float = 60.0
    attack_daily_amount: float = 100.0
    tactical_cooldown_days: int = 20
    quarterly_use_cap: float = 0.40
    tactical_reserve_floor: float = 0.40
    tactical_min_ratio: float = 0.10
    tactical_max_ratio: float = 0.15


@dataclass
class PortfolioState:
    units: dict[str, float]
    cash: float = 0.0
    invested: float = 0.0
    cooldown_remaining: int = 0


def main() -> None:
    """Run all strategy and period comparisons."""

    config = BacktestConfig()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    prices, error = download_prices()
    if error:
        write_error_outputs(error)
        print(f"Backtest failed: {error}")
        return

    prices, data_note = select_prices(prices, config)
    if prices.empty:
        message = "No complete overlapping QQQ/SMH/GLD data was available for the requested range."
        write_error_outputs(message)
        print(f"Backtest failed: {message}")
        return

    indicators = build_indicators(prices, config)
    strategy_runs = {
        strategy: run_strategy(prices, indicators, config, strategy)
        for strategy in ["qqq_pure_dca", "tech_plus_dca", "clayton_nasdaq_plus_aggressive"]
    }

    period_results = build_period_results(prices, indicators, config)
    yearly_results = build_yearly_results(prices, indicators, config)
    tactical_log = pd.DataFrame(strategy_runs["clayton_nasdaq_plus_aggressive"]["tactical_log"])
    tactical_columns = [
        "date",
        "level",
        "amount",
        "allocation",
        "trigger_reason",
        "cash_before",
        "cash_after",
        "quarter_used_ratio",
        "cooldown_days",
    ]
    if tactical_log.empty:
        tactical_log = pd.DataFrame(columns=tactical_columns)
    tactical_log = tactical_log.reindex(columns=tactical_columns)

    period_results.to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
    yearly_results.to_csv(YEARLY_PATH, index=False, encoding="utf-8-sig")
    tactical_log.to_csv(TACTICAL_LOG_PATH, index=False, encoding="utf-8-sig")

    write_summary(
        prices=prices,
        data_note=data_note,
        period_results=period_results,
        yearly_results=yearly_results,
        tactical_log=tactical_log,
        strategy_runs=strategy_runs,
        config=config,
    )

    print(f"Backtest completed. Summary: {SUMMARY_PATH}")
    print(f"Results CSV: {RESULTS_PATH}")
    print(f"Yearly CSV: {YEARLY_PATH}")
    print(f"Tactical cash log: {TACTICAL_LOG_PATH}")


def download_prices() -> tuple[pd.DataFrame, str | None]:
    """Download adjusted close prices from Yahoo Finance."""

    yfinance_error = ""
    try:
        import yfinance as yf

        raw = yf.download(
            tickers=["QQQ", "SMH", "GLD"],
            start=START_DATE,
            end=DOWNLOAD_END_DATE,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception as exc:
        raw = pd.DataFrame()
        yfinance_error = f"yfinance data download failed: {exc}"

    if not raw.empty:
        if isinstance(raw.columns, pd.MultiIndex):
            if "Close" not in raw.columns.get_level_values(0):
                yfinance_error = "yfinance response did not contain Close prices."
            else:
                prices = raw["Close"].copy()
                prices.index = pd.to_datetime(prices.index)
                for symbol in ["QQQ", "SMH", "GLD"]:
                    if symbol not in prices.columns:
                        prices[symbol] = pd.NA
                prices = prices[["QQQ", "SMH", "GLD"]].sort_index().dropna(how="all")
                prices.attrs["data_source"] = "yfinance"
                return prices, None
        else:
            prices = raw[["Close"]].copy()
            prices.columns = ["QQQ"]
            prices.index = pd.to_datetime(prices.index)
            for symbol in ["QQQ", "SMH", "GLD"]:
                if symbol not in prices.columns:
                    prices[symbol] = pd.NA
            prices = prices[["QQQ", "SMH", "GLD"]].sort_index().dropna(how="all")
            prices.attrs["data_source"] = "yfinance"
            return prices, None
    elif not yfinance_error:
        yfinance_error = "yfinance returned an empty dataset."

    fallback_prices, fallback_error = download_prices_from_yahoo_chart()
    if fallback_error:
        return pd.DataFrame(), f"{yfinance_error}; fallback Yahoo chart download failed: {fallback_error}"
    fallback_prices.attrs["data_source"] = f"Yahoo chart API fallback because {yfinance_error}"
    return fallback_prices, None


def download_prices_from_yahoo_chart() -> tuple[pd.DataFrame, str | None]:
    """Download adjusted close prices directly from Yahoo chart JSON."""

    try:
        import requests
    except Exception as exc:
        return pd.DataFrame(), f"requests import failed: {exc}"

    period1 = int(datetime(2006, 1, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    series_map = {}

    for symbol in ["QQQ", "SMH", "GLD"]:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
        )
        try:
            response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            payload = response.json()
            chart = payload.get("chart", {})
            if chart.get("error"):
                return pd.DataFrame(), str(chart["error"])
            result = (chart.get("result") or [])[0]
            timestamps = result.get("timestamp") or []
            adjclose = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose") or []
        except Exception as exc:
            return pd.DataFrame(), f"{symbol}: {exc}"

        if not timestamps or not adjclose:
            return pd.DataFrame(), f"{symbol}: empty chart data"

        index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
        series_map[symbol] = pd.Series(adjclose, index=index, name=symbol, dtype="float64")

    prices = pd.concat(series_map.values(), axis=1).sort_index().dropna(how="all")
    return prices[["QQQ", "SMH", "GLD"]], None


def select_prices(prices: pd.DataFrame, config: BacktestConfig) -> tuple[pd.DataFrame, str]:
    """Trim to complete overlapping data."""

    selected = prices.loc[pd.Timestamp(config.start_date) : pd.Timestamp(config.end_date)].dropna(how="any")
    if selected.empty:
        return selected, "No complete overlapping data."
    first_date = selected.index[0].date().isoformat()
    last_date = selected.index[-1].date().isoformat()
    source = prices.attrs.get("data_source", "unknown source")
    note = f"Data source: {source}. Complete overlapping QQQ/SMH/GLD data runs from {first_date} to {last_date}."
    if first_date != config.start_date:
        note += " The requested start date was a non-trading day or lacked complete data, so the first complete trading day was used."
    return selected, note


def build_indicators(prices: pd.DataFrame, config: BacktestConfig) -> dict[str, pd.DataFrame]:
    """Build indicators using current and past prices only."""

    rsi_table = prices.apply(lambda column: calculate_rsi(column, config.rsi_window))
    ma60 = prices.rolling(window=config.ma_window, min_periods=config.ma_window).mean()
    recent_high = prices.rolling(window=config.recent_high_window, min_periods=1).max()
    drawdown = prices / recent_high - 1
    return {
        "rsi": rsi_table,
        "ma60": ma60,
        "drawdown": drawdown,
    }


def calculate_rsi(price: pd.Series, window: int) -> pd.Series:
    """Calculate rolling RSI."""

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
    strategy: str,
) -> dict[str, Any]:
    """Run a single strategy over the full history."""

    state = PortfolioState(units={"QQQ": 0.0, "SMH": 0.0, "GLD": 0.0})
    daily_rows = []
    tactical_log = []
    quarter_usage: dict[str, float] = {}
    quarter_cash_basis: dict[str, float] = {}

    for date, price_row in prices.iterrows():
        value_before = portfolio_value(state, price_row)
        previous_value = daily_rows[-1]["portfolio_value"] if daily_rows else 0.0
        market_return = value_before / previous_value - 1 if previous_value > 0 else 0.0

        if state.cooldown_remaining > 0:
            state.cooldown_remaining -= 1

        daily_plan = build_daily_plan(date, price_row, indicators, state, config, strategy)
        invest_plan(state, price_row, daily_plan["investments"], daily_plan["cash_add"])

        tactical_amount = 0.0
        tactical_level = 0
        if strategy == "clayton_nasdaq_plus_aggressive":
            quarter = quarter_key(date)
            quarter_cash_basis.setdefault(quarter, state.cash)
            tactical_amount, tactical_level, reason = build_tactical_trade(
                date=date,
                prices=price_row,
                indicators=indicators,
                state=state,
                config=config,
                quarter_usage=quarter_usage,
                quarter_cash_basis=quarter_cash_basis,
            )
            if tactical_amount > 0:
                cash_before = state.cash
                tactical_investments = {
                    "SMH": tactical_amount * 0.75,
                    "QQQ": tactical_amount * 0.20,
                    "GLD": tactical_amount * 0.05,
                }
                invest_plan(state, price_row, tactical_investments, cash_add=0.0, use_existing_cash=True)
                state.cooldown_remaining = config.tactical_cooldown_days
                quarter_usage[quarter] = quarter_usage.get(quarter, 0.0) + tactical_amount
                tactical_log.append(
                    {
                        "date": date.date().isoformat(),
                        "level": f"Level {tactical_level}",
                        "amount": round(tactical_amount, 2),
                        "allocation": "SMH 75%; QQQ 20%; GLD 5%",
                        "trigger_reason": reason,
                        "cash_before": round(cash_before, 2),
                        "cash_after": round(state.cash, 2),
                        "quarter_used_ratio": round(quarter_usage[quarter] / max(quarter_cash_basis[quarter], 1.0), 6),
                        "cooldown_days": config.tactical_cooldown_days,
                    }
                )

        end_value = portfolio_value(state, price_row)
        daily_rows.append(
            {
                "date": date,
                "strategy": strategy,
                "portfolio_value": end_value,
                "invested": state.invested,
                "cash": state.cash,
                "market_return": market_return,
                "daily_mode": daily_plan["mode"],
                "daily_amount": daily_plan["daily_amount"],
                "tactical_amount": tactical_amount,
                "tactical_level": tactical_level,
            }
        )

    daily = pd.DataFrame(daily_rows).set_index("date")
    return {
        "daily": daily,
        "tactical_log": tactical_log,
    }


def build_daily_plan(
    date: pd.Timestamp,
    prices: pd.Series,
    indicators: dict[str, pd.DataFrame],
    state: PortfolioState,
    config: BacktestConfig,
    strategy: str,
) -> dict[str, Any]:
    """Build normal daily investment plan."""

    if strategy == "qqq_pure_dca":
        return {
            "mode": "normal",
            "daily_amount": 60.0,
            "investments": {"QQQ": 60.0},
            "cash_add": 0.0,
        }
    if strategy == "tech_plus_dca":
        return {
            "mode": "normal",
            "daily_amount": 60.0,
            "investments": {"QQQ": 36.0, "SMH": 24.0},
            "cash_add": 0.0,
        }

    if is_healthy_pullback(date, prices, indicators):
        gld_cash = split_gld_cash_for_target(state, prices, 10.0, config)
        return {
            "mode": "attack",
            "daily_amount": 100.0,
            "investments": {"SMH": 60.0, "QQQ": 30.0, "GLD": gld_cash["GLD"]},
            "cash_add": gld_cash["Cash"],
        }

    return {
        "mode": "normal",
        "daily_amount": 60.0,
        "investments": {"QQQ": 20.0, "SMH": 30.0, "GLD": 5.0},
        "cash_add": 5.0,
    }


def split_gld_cash_for_target(
    state: PortfolioState,
    prices: pd.Series,
    amount: float,
    config: BacktestConfig,
) -> dict[str, float]:
    """Split the GLD/Cash sleeve to keep tactical cash around 10%-15% of assets."""

    total = portfolio_value(state, prices)
    cash_ratio = state.cash / total if total > 0 else 0.0
    if cash_ratio < config.tactical_min_ratio:
        return {"GLD": 0.0, "Cash": amount}
    if cash_ratio > config.tactical_max_ratio:
        return {"GLD": amount, "Cash": 0.0}
    return {"GLD": amount / 2, "Cash": amount / 2}


def invest_plan(
    state: PortfolioState,
    prices: pd.Series,
    investments: dict[str, float],
    cash_add: float,
    use_existing_cash: bool = False,
) -> None:
    """Apply investments and cash contributions."""

    total_investment = sum(investments.values())
    if use_existing_cash:
        state.cash -= total_investment
    else:
        state.invested += total_investment + cash_add
        state.cash += cash_add

    for symbol, amount in investments.items():
        if amount > 0:
            state.units[symbol] += amount / float(prices[symbol])


def build_tactical_trade(
    date: pd.Timestamp,
    prices: pd.Series,
    indicators: dict[str, pd.DataFrame],
    state: PortfolioState,
    config: BacktestConfig,
    quarter_usage: dict[str, float],
    quarter_cash_basis: dict[str, float],
) -> tuple[float, int, str]:
    """Determine tactical cash use for Clayton strategy."""

    level, reason = classify_tactical_level(date, prices, indicators)
    if level < 2:
        return 0.0, level, reason
    if state.cash <= 0 or state.cooldown_remaining > 0:
        return 0.0, level, reason
    if is_rsi_hot(date, indicators) or both_below_ma(date, prices, indicators) or is_market_risk_off(date, prices, indicators):
        return 0.0, level, reason

    total = portfolio_value(state, prices)
    cash_ratio = state.cash / total if total > 0 else 0.0
    if cash_ratio < config.tactical_min_ratio:
        return 0.0, level, reason

    level_pct = {2: 0.10, 3: 0.20, 4: 0.30}[level]
    reserve_floor = state.cash * config.tactical_reserve_floor
    usable_cash = max(0.0, state.cash - reserve_floor)
    quarter = quarter_key(date)
    quarter_cap = quarter_cash_basis.get(quarter, state.cash) * config.quarterly_use_cap
    quarter_remaining = max(0.0, quarter_cap - quarter_usage.get(quarter, 0.0))
    amount = min(state.cash * level_pct, usable_cash, quarter_remaining)
    if amount <= 0:
        return 0.0, level, reason
    return amount, level, reason


def classify_tactical_level(
    date: pd.Timestamp,
    prices: pd.Series,
    indicators: dict[str, pd.DataFrame],
) -> tuple[int, str]:
    """Classify pullback severity for tactical cash."""

    candidates = []
    for symbol in ["QQQ", "SMH"]:
        rsi = indicators["rsi"].at[date, symbol]
        ma60 = indicators["ma60"].at[date, symbol]
        drawdown = indicators["drawdown"].at[date, symbol]
        if pd.isna(rsi) or pd.isna(ma60) or pd.isna(drawdown):
            continue
        price = float(prices[symbol])
        candidates.append(
            {
                "symbol": symbol,
                "rsi": float(rsi),
                "drawdown": float(drawdown),
                "above_ma": price >= float(ma60),
                "near_ma": price >= float(ma60) * 0.97,
            }
        )

    level4 = [item for item in candidates if -0.25 <= item["drawdown"] <= -0.15 and 25 <= item["rsi"] <= 45]
    if level4:
        return 4, format_reason(level4, "15%-25% drawdown with RSI 25-45")

    level3 = [
        item for item in candidates
        if -0.15 <= item["drawdown"] <= -0.10 and 35 <= item["rsi"] <= 50 and item["near_ma"]
    ]
    if level3:
        return 3, format_reason(level3, "10%-15% drawdown, RSI 35-50, not clearly below 60-day MA")

    level2 = [
        item for item in candidates
        if -0.10 <= item["drawdown"] <= -0.05 and 45 <= item["rsi"] <= 60 and item["above_ma"]
    ]
    if level2:
        return 2, format_reason(level2, "5%-10% drawdown, RSI 45-60, above 60-day MA")

    return 0, "No tactical pullback level was triggered."


def format_reason(items: list[dict[str, Any]], label: str) -> str:
    """Build a compact tactical trigger reason."""

    symbols = ", ".join(item["symbol"] for item in items)
    details = "; ".join(f"{item['symbol']} drawdown {item['drawdown']:.2%}, RSI {item['rsi']:.1f}" for item in items)
    return f"{symbols} met {label}. {details}."


def is_healthy_pullback(date: pd.Timestamp, prices: pd.Series, indicators: dict[str, pd.DataFrame]) -> bool:
    """Healthy pullback for daily attack mode."""

    for symbol in ["QQQ", "SMH"]:
        rsi = indicators["rsi"].at[date, symbol]
        ma60 = indicators["ma60"].at[date, symbol]
        drawdown = indicators["drawdown"].at[date, symbol]
        if pd.isna(rsi) or pd.isna(ma60) or pd.isna(drawdown):
            continue
        if -0.12 <= drawdown <= -0.02 and 40 <= rsi <= 60 and prices[symbol] >= ma60 * 0.97:
            return True
    return False


def is_rsi_hot(date: pd.Timestamp, indicators: dict[str, pd.DataFrame]) -> bool:
    """Block tactical cash when QQQ or SMH RSI is overheated."""

    return any(
        not pd.isna(indicators["rsi"].at[date, symbol]) and indicators["rsi"].at[date, symbol] > 70
        for symbol in ["QQQ", "SMH"]
    )


def both_below_ma(date: pd.Timestamp, prices: pd.Series, indicators: dict[str, pd.DataFrame]) -> bool:
    """Check whether QQQ and SMH are both below 60-day moving average."""

    below = []
    for symbol in ["QQQ", "SMH"]:
        ma60 = indicators["ma60"].at[date, symbol]
        below.append(not pd.isna(ma60) and prices[symbol] < ma60)
    return all(below)


def is_market_risk_off(date: pd.Timestamp, prices: pd.Series, indicators: dict[str, pd.DataFrame]) -> bool:
    """Define market risk-off for this model."""

    qqq_dd = indicators["drawdown"].at[date, "QQQ"]
    smh_dd = indicators["drawdown"].at[date, "SMH"]
    severe_growth_drawdown = (
        not pd.isna(qqq_dd)
        and not pd.isna(smh_dd)
        and qqq_dd <= -0.20
        and smh_dd <= -0.20
    )
    return both_below_ma(date, prices, indicators) or severe_growth_drawdown


def portfolio_value(state: PortfolioState, prices: pd.Series) -> float:
    """Mark portfolio to market, including tactical cash."""

    return float(state.cash + sum(state.units[symbol] * float(prices[symbol]) for symbol in state.units))


def quarter_key(date: pd.Timestamp) -> str:
    """Return a stable quarter key."""

    quarter = ((date.month - 1) // 3) + 1
    return f"{date.year}Q{quarter}"


def build_period_results(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    config: BacktestConfig,
) -> pd.DataFrame:
    """Calculate strategy metrics for each requested period as an independent backtest."""

    rows = []
    for period_name, (start, end) in PERIODS.items():
        period_prices = prices.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        period_indicators = {
            name: table.loc[period_prices.index]
            for name, table in indicators.items()
        }
        period_runs = {
            strategy: run_strategy(period_prices, period_indicators, config, strategy)
            for strategy in ["qqq_pure_dca", "tech_plus_dca", "clayton_nasdaq_plus_aggressive"]
        }
        qqq_metrics = calculate_standalone_metrics(
            period_runs["qqq_pure_dca"]["daily"],
            "qqq_pure_dca",
            period_name,
            tactical_count=0,
            tactical_depleted=False,
        )
        for strategy, result in period_runs.items():
            tactical_count = len(result["tactical_log"])
            tactical_depleted = tactical_cash_depleted_early(result["tactical_log"], start, end) if strategy == "clayton_nasdaq_plus_aggressive" else False
            metrics = calculate_standalone_metrics(
                result["daily"],
                strategy,
                period_name,
                tactical_count=tactical_count,
                tactical_depleted=tactical_depleted,
            )
            metrics["beats_qqq_pure_dca"] = metrics["annualized_return"] > qqq_metrics["annualized_return"]
            metrics["max_drawdown_below_qqq"] = metrics["max_drawdown"] >= qqq_metrics["max_drawdown"]
            metrics["drawdown_not_much_worse_than_qqq"] = metrics["max_drawdown"] >= qqq_metrics["max_drawdown"] - 0.03
            rows.append(metrics)

    frame = pd.DataFrame(rows)
    clayton_full = row_for(frame, "full_2006_2025", "clayton_nasdaq_plus_aggressive")
    qqq_full = row_for(frame, "full_2006_2025", "qqq_pure_dca")
    clayton_oos = row_for(frame, "out_of_sample_2016_2025", "clayton_nasdaq_plus_aggressive")
    qqq_oos = row_for(frame, "out_of_sample_2016_2025", "qqq_pure_dca")
    strategy_effective = (
        clayton_full["annualized_return"] > qqq_full["annualized_return"]
        and clayton_full["drawdown_not_much_worse_than_qqq"]
        and clayton_full["sharpe_ratio"] > qqq_full["sharpe_ratio"]
        and clayton_oos["annualized_return"] > qqq_oos["annualized_return"]
        and clayton_oos["sharpe_ratio"] > qqq_oos["sharpe_ratio"]
        and not bool(clayton_full["tactical_cash_depleted_early"])
    )
    frame["out_of_sample_2016_2025_effective"] = frame.apply(
        lambda row: bool(
            row["period"] == "out_of_sample_2016_2025"
            and row["strategy"] == "clayton_nasdaq_plus_aggressive"
            and row["annualized_return"] > qqq_oos["annualized_return"]
            and row["drawdown_not_much_worse_than_qqq"]
            and row["sharpe_ratio"] > qqq_oos["sharpe_ratio"]
        ),
        axis=1,
    )
    frame["clayton_strategy_effective"] = frame.apply(
        lambda row: bool(row["strategy"] == "clayton_nasdaq_plus_aggressive" and strategy_effective),
        axis=1,
    )
    return frame


def calculate_standalone_metrics(
    daily: pd.DataFrame,
    strategy: str,
    period_name: str,
    tactical_count: int,
    tactical_depleted: bool,
) -> dict[str, Any]:
    """Calculate metrics from an independent backtest equity curve."""

    if daily.empty:
        return {
            "period": period_name,
            "strategy": strategy,
            "start_date": "",
            "end_date": "",
            "total_invested": 0.0,
            "ending_value": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "calmar_ratio": 0.0,
            "tactical_cash_uses": tactical_count,
            "tactical_cash_depleted_early": tactical_depleted,
        }

    total_invested = float(daily["invested"].iloc[-1])
    ending_value = float(daily["portfolio_value"].iloc[-1])
    annualized = annualized_return_from_invested(daily)
    drawdown = daily["portfolio_value"] / daily["portfolio_value"].cummax() - 1
    max_drawdown = float(drawdown.min())
    returns = daily["market_return"].iloc[1:].dropna()
    sharpe = 0.0
    if not returns.empty and returns.std() != 0:
        sharpe = float((returns.mean() / returns.std()) * (252 ** 0.5))
    calmar = annualized / abs(max_drawdown) if max_drawdown < 0 else 0.0
    return {
        "period": period_name,
        "strategy": strategy,
        "start_date": daily.index[0].date().isoformat(),
        "end_date": daily.index[-1].date().isoformat(),
        "total_invested": round(total_invested, 2),
        "ending_value": round(ending_value, 2),
        "annualized_return": round(annualized, 6),
        "max_drawdown": round(max_drawdown, 6),
        "sharpe_ratio": round(sharpe, 6),
        "calmar_ratio": round(calmar, 6),
        "tactical_cash_uses": tactical_count,
        "tactical_cash_depleted_early": tactical_depleted,
    }


def annualized_return_from_invested(daily: pd.DataFrame) -> float:
    """Approximate annualized return on total contributions."""

    ending_value = float(daily["portfolio_value"].iloc[-1])
    invested = float(daily["invested"].iloc[-1])
    if invested <= 0:
        return 0.0
    years = max((daily.index[-1] - daily.index[0]).days / 365.25, 1 / 365.25)
    return (ending_value / invested) ** (1 / years) - 1


def build_yearly_results(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    config: BacktestConfig,
) -> pd.DataFrame:
    """Build yearly return and drawdown comparison as independent one-year backtests."""

    rows = []
    for year in sorted(prices.index.year.unique()):
        year_prices = prices[prices.index.year == year]
        if year_prices.empty:
            continue
        year_indicators = {
            name: table.loc[year_prices.index]
            for name, table in indicators.items()
        }
        for strategy in ["qqq_pure_dca", "tech_plus_dca", "clayton_nasdaq_plus_aggressive"]:
            daily = run_strategy(year_prices, year_indicators, config, strategy)["daily"]
            yearly_return = float(daily["portfolio_value"].iloc[-1] / daily["invested"].iloc[-1] - 1)
            drawdown = daily["portfolio_value"] / daily["portfolio_value"].cummax() - 1
            rows.append(
                {
                    "year": int(year),
                    "strategy": strategy,
                    "yearly_invested": round(float(daily["invested"].iloc[-1]), 2),
                    "year_end_net_value": round(float(daily["portfolio_value"].iloc[-1]), 2),
                    "yearly_return": round(yearly_return, 6),
                    "yearly_max_drawdown": round(float(drawdown.min()), 6),
                }
            )
    frame = pd.DataFrame(rows)
    qqq = frame[frame["strategy"] == "qqq_pure_dca"][["year", "yearly_return", "yearly_max_drawdown"]].rename(
        columns={
            "yearly_return": "qqq_yearly_return",
            "yearly_max_drawdown": "qqq_yearly_max_drawdown",
        }
    )
    frame = frame.merge(qqq, on="year", how="left")
    frame["beats_qqq_yearly"] = frame["yearly_return"] > frame["qqq_yearly_return"]
    frame["drawdown_below_qqq_yearly"] = frame["yearly_max_drawdown"] >= frame["qqq_yearly_max_drawdown"]
    return frame


def count_tactical_uses(tactical_log: list[dict[str, Any]], start: str, end: str) -> int:
    """Count tactical uses in a period."""

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return sum(start_ts <= pd.Timestamp(item["date"]) <= end_ts for item in tactical_log)


def tactical_cash_depleted_early(tactical_log: list[dict[str, Any]], start: str, end: str) -> bool:
    """Flag early cash depletion as using down to the reserve floor in the first half of a period."""

    if not tactical_log:
        return False
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    midpoint = start_ts + (end_ts - start_ts) / 2
    for item in tactical_log:
        date = pd.Timestamp(item["date"])
        if start_ts <= date <= midpoint and float(item.get("cash_after", 0.0)) <= 0:
            return True
    return False


def row_for(frame: pd.DataFrame, period: str, strategy: str) -> pd.Series:
    """Return one metrics row."""

    return frame[(frame["period"] == period) & (frame["strategy"] == strategy)].iloc[0]


def write_summary(
    prices: pd.DataFrame,
    data_note: str,
    period_results: pd.DataFrame,
    yearly_results: pd.DataFrame,
    tactical_log: pd.DataFrame,
    strategy_runs: dict[str, dict[str, Any]],
    config: BacktestConfig,
) -> None:
    """Write Markdown summary report."""

    full = period_results[period_results["period"] == "full_2006_2025"].copy()
    oos = period_results[period_results["period"] == "out_of_sample_2016_2025"].copy()
    clayton_full = row_for(period_results, "full_2006_2025", "clayton_nasdaq_plus_aggressive")
    qqq_full = row_for(period_results, "full_2006_2025", "qqq_pure_dca")
    clayton_oos = row_for(period_results, "out_of_sample_2016_2025", "clayton_nasdaq_plus_aggressive")
    effective = bool(clayton_full["clayton_strategy_effective"])
    verdict = "有效" if effective else "无效"
    tactical_early = "是" if bool(clayton_full["tactical_cash_depleted_early"]) else "否"

    display_full = format_metric_table(full)
    display_oos = format_metric_table(oos)
    yearly_pivot = build_yearly_summary_table(yearly_results)
    tactical_section = "本次回测没有触发机动资金使用。" if tactical_log.empty else dataframe_to_markdown(tactical_log)

    content = f"""# Clayton Nasdaq-Plus Aggressive Model Backtest

## 回测目标

本回测比较三种策略：QQQ 纯定投、QQQ/SMH 科技增强定投、Clayton Nasdaq-Plus Aggressive Model。目标不是跑赢标普500，而是检验 Clayton 策略是否能跑赢 QQQ 纯定投，同时最大回撤不能明显高于 QQQ。

## 数据与口径

- 数据区间：{prices.index[0].date().isoformat()} 至 {prices.index[-1].date().isoformat()}
- 数据说明：{data_note}
- 资产：QQQ、SMH、GLD，使用复权后收盘价；若 yfinance 失败，则自动切换到 Yahoo Chart API 备用数据源。
- 资金口径：以人民币投入金额购买美元计价 ETF 代理份额，未建模汇率、税费、滑点、QDII 溢价和交易限制。
- 指标口径：RSI、60日均线、近期高点回撤均只使用当日及历史数据，不使用未来数据。

## 策略定义摘要

- 策略A `qqq_pure_dca`：每个交易日 ¥60，100% QQQ。
- 策略B `tech_plus_dca`：每个交易日 ¥60，QQQ 60%、SMH 40%。
- 策略C `clayton_nasdaq_plus_aggressive`：正常模式每日 ¥60，QQQ ¥20、SMH ¥30、GLD ¥5、Cash ¥5；健康回踩时每日 ¥100，SMH ¥60、QQQ ¥30、GLD/Cash ¥10。
- 机动资金：Level 2/3/4 分别使用当前现金的 10%/20%/30%，20个交易日冷却，每季度最多使用该季度初机动资金的40%，每次使用后至少保留当前机动资金40%，且 RSI 过热、QQQ和SMH同时跌破60日均线、market risk-off 时禁用。

## 全区间结果

{dataframe_to_markdown(display_full)}

## 样本外 2016-2025

{dataframe_to_markdown(display_oos)}

## 判定

- Clayton 策略最终判定：{verdict}
- 年化收益是否高于 QQQ：{"是" if clayton_full["annualized_return"] > qqq_full["annualized_return"] else "否"}
- 最大回撤是否不明显高于 QQQ：{"是" if clayton_full["drawdown_not_much_worse_than_qqq"] else "否"}
- 夏普比率是否高于 QQQ：{"是" if clayton_full["sharpe_ratio"] > qqq_full["sharpe_ratio"] else "否"}
- 样本外 2016-2025 是否仍然有效：{"是" if clayton_oos["out_of_sample_2016_2025_effective"] else "否"}
- 机动资金是否过早打光：{tactical_early}

## 每年收益与最大回撤对比

{dataframe_to_markdown(yearly_pivot)}

## 机动资金使用记录

{tactical_section}

## 风险提示

历史回测不代表未来收益。本报告仅用于研究和策略复盘，不构成投资建议，也不代表任何基金或 ETF 的未来表现。
"""
    SUMMARY_PATH.write_text(content, encoding="utf-8")


def format_metric_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Format headline metrics for Markdown only."""

    columns = [
        "strategy",
        "total_invested",
        "ending_value",
        "annualized_return",
        "max_drawdown",
        "sharpe_ratio",
        "calmar_ratio",
        "beats_qqq_pure_dca",
        "drawdown_not_much_worse_than_qqq",
        "tactical_cash_uses",
        "tactical_cash_depleted_early",
    ]
    display = frame[columns].copy()
    for column in ["annualized_return", "max_drawdown"]:
        display[column] = display[column].map(lambda value: f"{value:.2%}")
    for column in ["total_invested", "ending_value"]:
        display[column] = display[column].map(lambda value: f"{value:,.2f}")
    for column in ["sharpe_ratio", "calmar_ratio"]:
        display[column] = display[column].map(lambda value: f"{value:.2f}")
    return display


def build_yearly_summary_table(yearly_results: pd.DataFrame) -> pd.DataFrame:
    """Compact yearly table focused on returns and drawdowns."""

    clayton = yearly_results[yearly_results["strategy"] == "clayton_nasdaq_plus_aggressive"]
    qqq = yearly_results[yearly_results["strategy"] == "qqq_pure_dca"]
    tech = yearly_results[yearly_results["strategy"] == "tech_plus_dca"]
    table = qqq[["year", "yearly_return", "yearly_max_drawdown"]].rename(
        columns={
            "yearly_return": "qqq_return",
            "yearly_max_drawdown": "qqq_max_drawdown",
        }
    )
    table = table.merge(
        tech[["year", "yearly_return", "yearly_max_drawdown"]].rename(
            columns={
                "yearly_return": "tech_plus_return",
                "yearly_max_drawdown": "tech_plus_max_drawdown",
            }
        ),
        on="year",
        how="left",
    )
    table = table.merge(
        clayton[["year", "yearly_return", "yearly_max_drawdown", "beats_qqq_yearly", "drawdown_below_qqq_yearly"]].rename(
            columns={
                "yearly_return": "clayton_return",
                "yearly_max_drawdown": "clayton_max_drawdown",
            }
        ),
        on="year",
        how="left",
    )
    for column in [column for column in table.columns if column.endswith("return") or column.endswith("drawdown")]:
        table[column] = table[column].map(lambda value: f"{value:.2%}")
    return table


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    """Render DataFrame as Markdown without optional dependencies."""

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
    """Write error files without crashing."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"error": message}]).to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=["year", "strategy", "yearly_return", "yearly_max_drawdown"]).to_csv(
        YEARLY_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(
        columns=[
            "date",
            "level",
            "amount",
            "allocation",
            "trigger_reason",
            "cash_before",
            "cash_after",
            "quarter_used_ratio",
            "cooldown_days",
        ]
    ).to_csv(TACTICAL_LOG_PATH, index=False, encoding="utf-8-sig")
    SUMMARY_PATH.write_text(
        f"""# Clayton Nasdaq-Plus Aggressive Model Backtest Failed

数据下载或处理失败，程序已停止且未崩溃。

错误原因：{message}

历史回测不代表未来收益。
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
