"""Price data loading utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


def fetch_price_data(
    assets: list[dict],
    period: str = "1y",
    cache_path: str | Path = "data/price_cache.csv",
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Fetch historical close prices and return a data-quality map."""

    # 确保缓存目录存在，避免首次运行时写入失败。
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # 从资产配置中取出 symbol，作为下载和后续拼表的唯一标识。
    symbols = [asset["symbol"] for asset in assets]
    fred_symbols = [asset["symbol"] for asset in assets if str(asset.get("source", "")).upper() == "FRED"]
    yahoo_symbols = [symbol for symbol in symbols if symbol not in fred_symbols]
    quality = {symbol: "missing" for symbol in symbols}

    # 先尝试在线获取数据；失败时不会中断流程，而是进入缓存兜底。
    online_prices = _download_from_yahoo(symbols=yahoo_symbols, period=period)
    fred_prices = _download_from_fred(symbols=fred_symbols)
    if not fred_prices.empty:
        online_prices = pd.concat([online_prices, fred_prices], axis=1).sort_index()
    if not online_prices.empty:
        for symbol in symbols:
            if symbol not in online_prices.columns:
                online_prices[symbol] = pd.NA
        online_prices = online_prices.reindex(columns=symbols)

    # 如果线上数据成功返回，就更新每个资产的数据质量标记。
    for symbol in online_prices.columns:
        if online_prices[symbol].dropna().empty:
            quality[symbol] = "missing"
        else:
            quality[symbol] = "fresh"

    # 如果拿到了任意线上数据，就写入本地缓存，方便下次断网时使用。
    if not online_prices.empty:
        online_prices.to_csv(cache_path, encoding="utf-8-sig")
        return online_prices, quality

    # 如果线上数据完全不可用，就尝试读取缓存，报告中会标记为 stale。
    cached_prices = _load_cached_prices(cache_path=cache_path, symbols=symbols)
    for symbol in cached_prices.columns:
        if not cached_prices[symbol].dropna().empty:
            quality[symbol] = "stale"

    return cached_prices, quality


def _download_from_yahoo(symbols: list[str], period: str) -> pd.DataFrame:
    """Download adjusted close prices from Yahoo Finance."""

    try:
        # yfinance 支持一次下载多个 symbol，速度比逐个下载更快。
        raw_data = yf.download(
            tickers=symbols,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        # 数据源异常时返回空表，让主流程使用缓存兜底。
        return pd.DataFrame()

    if raw_data.empty:
        return pd.DataFrame()

    # 多资产下载时 yfinance 会返回多层列索引；这里统一抽取 Close。
    if isinstance(raw_data.columns, pd.MultiIndex):
        if "Close" not in raw_data.columns.get_level_values(0):
            return pd.DataFrame()
        prices = raw_data["Close"].copy()
    else:
        prices = raw_data[["Close"]].copy()
        prices.columns = symbols[:1]

    # 清理全空行，并保证日期索引按时间升序排列。
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index().dropna(how="all")

    # 即使某些资产没有返回数据，也保留对应列，避免下游页面少显示资产。
    for symbol in symbols:
        if symbol not in prices.columns:
            prices[symbol] = pd.NA

    prices = prices.reindex(columns=symbols)
    return prices


def _download_from_fred(symbols: list[str]) -> pd.DataFrame:
    """Download FRED series and fail softly when unavailable."""

    if not symbols:
        return pd.DataFrame()

    frames = []
    for symbol in symbols:
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={symbol}"
            series = pd.read_csv(url)
            if "observation_date" not in series.columns or symbol not in series.columns:
                continue
            series["observation_date"] = pd.to_datetime(series["observation_date"], errors="coerce")
            values = pd.to_numeric(series[symbol], errors="coerce")
            frame = pd.DataFrame({symbol: values.values}, index=series["observation_date"])
            frame = frame.dropna().sort_index().last("370D")
            frames.append(frame)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame(columns=symbols)
    result = pd.concat(frames, axis=1).sort_index()
    for symbol in symbols:
        if symbol not in result.columns:
            result[symbol] = pd.NA
    return result.reindex(columns=symbols)


def _load_cached_prices(cache_path: Path, symbols: list[str]) -> pd.DataFrame:
    """Load cached prices when online data is unavailable."""

    if not cache_path.exists():
        return pd.DataFrame(columns=symbols)

    # 缓存第一列是日期索引，读取后恢复为 DatetimeIndex。
    cached_prices = pd.read_csv(cache_path, index_col=0, parse_dates=True)

    # 只保留当前配置中需要的资产，避免旧缓存污染本次报告。
    existing_symbols = [symbol for symbol in symbols if symbol in cached_prices.columns]
    return cached_prices[existing_symbols].sort_index()
