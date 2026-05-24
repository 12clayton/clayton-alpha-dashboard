"""Technical indicators used by the risk monitor."""

from __future__ import annotations

import pandas as pd


def moving_average(price: pd.Series, window: int) -> pd.Series:
    """Calculate a simple moving average."""

    # 使用 min_periods=window，避免样本不足时给出误导性均线。
    return price.rolling(window=window, min_periods=window).mean()


def rsi(price: pd.Series, window: int = 14) -> pd.Series:
    """Calculate the Relative Strength Index."""

    # 先计算每日价格变化，正数代表上涨，负数代表下跌。
    delta = price.diff()

    # 上涨幅度和下跌幅度分开统计，便于计算 RSI 的相对强弱。
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # 使用滚动均值计算平均上涨和平均下跌。
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    # 当平均下跌为 0 时，RSI 理论上接近 100；这里用替换避免除零。
    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + relative_strength))


def max_drawdown(price: pd.Series) -> float:
    """Calculate the maximum drawdown over the available price history."""

    # rolling_high 记录历史最高价，drawdown 记录相对历史高点的跌幅。
    rolling_high = price.cummax()
    drawdown = price / rolling_high - 1

    # 如果数据为空，返回 0，避免报告生成阶段报错。
    if drawdown.dropna().empty:
        return 0.0

    return float(drawdown.min())


def latest_drawdown(price: pd.Series) -> float:
    """Calculate the latest drawdown from the historical high."""

    # 最新回撤用于判断当前是否仍处在压力区。
    clean_price = price.dropna()
    if clean_price.empty:
        return 0.0

    return float(clean_price.iloc[-1] / clean_price.cummax().iloc[-1] - 1)


def build_indicator_table(
    prices: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 60,
    rsi_window: int = 14,
) -> pd.DataFrame:
    """Build a one-row-per-asset indicator table."""

    rows = []

    # 对每个资产单独计算指标，保证缺失数据不会影响其他资产。
    for symbol in prices.columns:
        price = prices[symbol].dropna()
        if price.empty:
            rows.append(_empty_indicator_row(symbol))
            continue

        short_ma = moving_average(price, short_window)
        long_ma = moving_average(price, long_window)
        rsi_series = rsi(price, rsi_window)

        # 汇总最后一个交易日的核心指标，供风险模型和报告使用。
        rows.append(
            {
                "symbol": symbol,
                "last_date": price.index[-1].date().isoformat(),
                "last_price": float(price.iloc[-1]),
                "short_ma": _last_valid_value(short_ma),
                "long_ma": _last_valid_value(long_ma),
                "rsi": _last_valid_value(rsi_series),
                "latest_drawdown": latest_drawdown(price),
                "max_drawdown": max_drawdown(price),
                "daily_return": _latest_return(price),
            }
        )

    return pd.DataFrame(rows)


def _empty_indicator_row(symbol: str) -> dict:
    """Return a placeholder row when an asset has no usable price data."""

    return {
        "symbol": symbol,
        "last_date": "",
        "last_price": pd.NA,
        "short_ma": pd.NA,
        "long_ma": pd.NA,
        "rsi": pd.NA,
        "latest_drawdown": pd.NA,
        "max_drawdown": pd.NA,
        "daily_return": pd.NA,
    }


def _last_valid_value(series: pd.Series) -> float | pd.NA:
    """Return the latest valid numeric value from a Series."""

    clean_series = series.dropna()
    if clean_series.empty:
        return pd.NA

    return float(clean_series.iloc[-1])


def _latest_return(price: pd.Series) -> float | pd.NA:
    """Return the latest one-day percentage return."""

    if len(price) < 2:
        return pd.NA

    return float(price.iloc[-1] / price.iloc[-2] - 1)
