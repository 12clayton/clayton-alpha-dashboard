"""Live market confirmation metrics for selected industry themes."""

from __future__ import annotations

import contextlib
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from typing import Any

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover - runtime fallback when optional market package is absent
    yf = None


DEBUG_MARKET_DATA = False
DOWNLOAD_FAILURE_DEBUG: dict[str, str] = {}

for logger_name in ("yfinance", "peewee"):
    market_logger = logging.getLogger(logger_name)
    market_logger.setLevel(logging.CRITICAL)
    market_logger.propagate = False


INDUSTRY_MARKET_TICKERS = {
    "semiconductor": {
        "etfs": ["SMH", "SOXX"],
        "leaders": ["NVDA", "AMD", "TSM", "AVGO", "ASML"],
        "benchmark": "QQQ",
    },
    "memory": {
        "etfs": ["SOXX", "SMH"],
        "leaders": ["MU", "WDC", "STX", "SSNLF", "005930.KS", "000660.KS"],
        "benchmark": "QQQ",
        "no_dedicated_etf": True,
        "proxy_note_key": "memory_proxy_note",
        "unstable_tickers": ["SSNLF"],
    },
    "cpo_optical_module": {
        "etfs": [],
        "leaders": ["ANET", "AVGO", "MRVL", "COHR", "LITE"],
        "benchmark": "QQQ",
    },
    "gold": {
        "etfs": ["GLD", "IAU", "GDX"],
        "leaders": ["NEM", "GOLD", "AEM"],
        "benchmark": "SPY",
    },
    "banking": {
        "etfs": ["XLF", "KBE"],
        "leaders": ["JPM", "BAC", "WFC", "GS", "MS"],
        "benchmark": "SPY",
    },
    "ai_compute": {
        "etfs": ["BOTZ", "AIQ"],
        "leaders": ["NVDA", "AMD", "AVGO", "ANET", "SMCI", "DELL", "VRT"],
        "benchmark": "QQQ",
    },
    "cpu": {
        "etfs": [],
        "leaders": ["AMD", "INTC", "ARM", "QCOM", "TSM"],
        "benchmark": "QQQ",
        "no_dedicated_etf": True,
    },
    "cloud_computing": {
        "etfs": ["SKYY", "CLOU", "WCLD"],
        "leaders": ["MSFT", "AMZN", "GOOGL", "ORCL", "CRM", "NOW"],
        "benchmark": "QQQ",
    },
    "data_center": {
        "etfs": ["VPN", "SRVR"],
        "leaders": ["VRT", "ETN", "DELL", "SMCI", "ANET", "NVDA", "AVGO"],
        "benchmark": "QQQ",
    },
    "sic": {
        "etfs": [],
        "leaders": ["ON", "STM", "WOLF", "ROHM", "IFNNY"],
        "benchmark": "QQQ",
        "no_dedicated_etf": True,
        "proxy_note_key": "sic_proxy_note",
        "unstable_tickers": ["ROHM"],
    },
    "ev": {
        "etfs": ["DRIV", "IDRV", "KARS"],
        "leaders": ["TSLA", "BYDDY", "LI", "NIO", "XPEV", "RIVN"],
        "benchmark": "QQQ",
    },
    "solar": {
        "etfs": ["TAN", "RAYS"],
        "leaders": ["FSLR", "ENPH", "SEDG", "JKS", "CSIQ"],
        "benchmark": "SPY",
    },
    "energy_storage": {
        "etfs": ["LIT", "BATT"],
        "leaders": ["ALB", "SQM", "TSLA", "BYDDY", "QS", "FLNC"],
        "benchmark": "SPY",
    },
    "battery": {
        "etfs": ["LIT", "BATT"],
        "leaders": ["ALB", "SQM", "TSLA", "BYDDY", "QS", "FLNC"],
        "benchmark": "SPY",
    },
    "robotics": {
        "etfs": ["BOTZ", "ROBO"],
        "leaders": ["ISRG", "ABBNY", "FANUY", "TER", "SYM", "NVDA"],
        "benchmark": "QQQ",
    },
    "copper": {
        "etfs": ["CPER", "COPX"],
        "leaders": ["FCX", "SCCO", "TECK", "BHP", "RIO"],
        "benchmark": "SPY",
    },
    "oil": {
        "etfs": ["USO", "XLE", "XOP"],
        "leaders": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "benchmark": "SPY",
    },
    "defense": {
        "etfs": ["ITA", "XAR"],
        "leaders": ["LMT", "RTX", "NOC", "GD", "LHX", "BA"],
        "benchmark": "SPY",
    },
    "healthcare": {
        "etfs": ["XLV", "IBB", "XBI"],
        "leaders": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO"],
        "benchmark": "SPY",
    },
    "innovative_drugs": {
        "etfs": ["XLV", "IBB", "XBI"],
        "leaders": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO"],
        "benchmark": "SPY",
    },
    "biotechnology": {
        "etfs": ["XLV", "IBB", "XBI"],
        "leaders": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO"],
        "benchmark": "SPY",
    },
    "medical_devices": {
        "etfs": ["XLV", "IBB", "XBI"],
        "leaders": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO"],
        "benchmark": "SPY",
    },
    "brokerage": {
        "etfs": ["IAI"],
        "leaders": ["SCHW", "IBKR", "HOOD", "MS", "GS"],
        "benchmark": "SPY",
    },
    "real_estate": {
        "etfs": ["XLRE", "VNQ", "IYR"],
        "leaders": ["AMT", "PLD", "EQIX", "SPG", "O"],
        "benchmark": "SPY",
    },
    "cxo": {
        "etfs": ["IBB", "XBI"],
        "leaders": ["TMO", "IQV", "ICLR", "CRL", "WUXAY"],
        "benchmark": "SPY",
        "no_dedicated_etf": True,
        "proxy_note_key": "cxo_proxy_note",
    },
    "shipping": {
        "etfs": ["SEA"],
        "leaders": ["ZIM", "MATX", "DAC", "SBLK", "GNK"],
        "benchmark": "SPY",
    },
    "insurance": {
        "etfs": ["KIE"],
        "leaders": ["BRK-B", "CB", "PGR", "TRV", "AIG", "MET", "PRU"],
        "benchmark": "SPY",
    },
    "reits": {
        "etfs": ["VNQ", "SCHH", "IYR"],
        "leaders": ["O", "PLD", "AMT", "EQIX", "SPG"],
        "benchmark": "SPY",
    },
    "coal": {
        "etfs": [],
        "leaders": ["BTU", "ARCH", "CEIX", "HCC"],
        "benchmark": "SPY",
        "no_dedicated_etf": True,
        "unstable_tickers": ["ARCH", "CEIX"],
    },
    "natural_gas": {
        "etfs": ["UNG", "FCG"],
        "leaders": ["EQT", "LNG", "CTRA", "RRC", "AR"],
        "benchmark": "SPY",
    },
    "lithium": {
        "etfs": ["LIT"],
        "leaders": ["ALB", "SQM", "LAC", "PLL", "SGML"],
        "benchmark": "SPY",
        "unstable_tickers": ["PLL"],
    },
    "rare_earth": {
        "etfs": ["REMX"],
        "leaders": ["MP", "LYSDY"],
        "benchmark": "SPY",
    },
    "gaming": {
        "etfs": ["HERO", "ESPO"],
        "leaders": ["NTES", "TCEHY", "EA", "TTWO", "RBLX", "SONY"],
        "benchmark": "QQQ",
    },
    "e_commerce": {
        "etfs": ["IBUY", "ONLN"],
        "leaders": ["AMZN", "BABA", "JD", "PDD", "MELI", "SHOP", "EBAY"],
        "benchmark": "QQQ",
    },
    "consumer_electronics": {
        "etfs": [],
        "leaders": ["AAPL", "SONY", "SSNLF", "PCRFY", "GRMN"],
        "benchmark": "QQQ",
        "no_dedicated_etf": True,
        "unstable_tickers": ["PCRFY"],
    },
    "cybersecurity": {
        "etfs": ["CIBR", "HACK", "BUG"],
        "leaders": ["CRWD", "PANW", "ZS", "FTNT", "OKTA", "S"],
        "benchmark": "QQQ",
    },
    "wind_power": {
        "etfs": ["FAN"],
        "leaders": ["NEE", "GE", "VWSYF", "VWDRY", "TPIC"],
        "benchmark": "SPY",
        "proxy_note_key": "wind_power_proxy_note",
    },
    "industrial_automation": {
        "etfs": ["ROBO", "BOTZ"],
        "leaders": ["ABBNY", "FANUY", "ROK", "EMR", "HON", "TER"],
        "benchmark": "SPY",
    },
    "aluminum": {
        "etfs": ["JJU", "DBB"],
        "leaders": ["AA", "CENX", "RIO", "BHP", "ACH"],
        "benchmark": "SPY",
    },
    "aviation": {
        "etfs": ["JETS"],
        "leaders": ["DAL", "UAL", "AAL", "LUV", "CPA"],
        "benchmark": "SPY",
    },
    "chemicals": {
        "etfs": ["XLB", "IYM"],
        "leaders": ["DOW", "DD", "LYB", "APD", "LIN", "CE"],
        "benchmark": "SPY",
    },
    "logistics": {
        "etfs": ["IYT"],
        "leaders": ["UPS", "FDX", "CHRW", "EXPD", "JBHT", "XPO"],
        "benchmark": "SPY",
    },
}

EXPLICIT_NO_MARKET_MAPPING = {
    "liquor",
    "food_beverage",
    "tourism",
    "hotel",
    "ai_healthcare",
    "cement",
    "ports",
    "power_equipment",
}


@dataclass(frozen=True)
class MarketDataResult:
    """Container for live market confirmation output."""

    available: bool
    message: str
    tickers: list[str]
    benchmark: str | None
    benchmark_ticker: str | None = None
    data_source: str = "Yahoo Finance via yfinance"
    last_updated: str | None = None
    valid_ticker_count: int = 0
    failed_tickers: list[str] | None = None
    failed_ticker_details: list[dict[str, str]] | None = None
    has_etf_sample: bool = False
    no_dedicated_etf: bool = False
    proxy_note_key: str | None = None
    score: float | None = None
    above_ma20_ratio: float | None = None
    above_ma20_count: int = 0
    above_ma20_total: int = 0
    above_ma50_ratio: float | None = None
    above_ma50_count: int = 0
    above_ma50_total: int = 0
    above_ma200_ratio: float | None = None
    above_ma200_count: int = 0
    above_ma200_total: int = 0
    average_1m_return: float | None = None
    average_3m_return: float | None = None
    average_6m_return: float | None = None
    median_3m_return: float | None = None
    benchmark_3m_return: float | None = None
    relative_strength: float | None = None
    details: list[dict[str, Any]] | None = None
    reason_code: str | None = None


def has_market_mapping(industry_id: str) -> bool:
    """Return whether an industry has a live ticker mapping."""

    return industry_id in INDUSTRY_MARKET_TICKERS


@st.cache_data(ttl=3600, show_spinner=False)
def get_market_confirmation_data(industry_id: str) -> dict[str, Any]:
    """Fetch prices and compute market confirmation metrics for one industry."""

    try:
        mapping = INDUSTRY_MARKET_TICKERS.get(industry_id)
        if not mapping:
            return _result(
                available=False,
                message="No live market ticker mapping for this industry.",
                reason_code="no_market_mapping",
                tickers=[],
                benchmark=None,
            )

        tickers = [*mapping["etfs"], *mapping["leaders"]]
        benchmark = mapping["benchmark"]
        all_tickers = sorted(set([*tickers, benchmark]))
        close_prices = download_close_prices(all_tickers)
        close_prices = retry_missing_close_prices(close_prices, all_tickers)
        base_meta = {
            "tickers": tickers,
            "benchmark": benchmark,
            "benchmark_ticker": benchmark,
            "last_updated": _timestamp(),
            "has_etf_sample": bool(mapping["etfs"]),
            "no_dedicated_etf": bool(mapping.get("no_dedicated_etf", not mapping["etfs"])),
            "proxy_note_key": mapping.get("proxy_note_key"),
        }
        unstable_tickers = set(mapping.get("unstable_tickers", []))
        if close_prices.empty:
            return _result(
                available=False,
                message="No price data returned.",
                reason_code="market_data_failed",
                failed_tickers=tickers,
                failed_ticker_details=[
                    {
                        "ticker": ticker,
                        "reason": normalize_failure_reason("empty data"),
                        "debug": DOWNLOAD_FAILURE_DEBUG.get(ticker, "empty data"),
                        "unstable": ticker in unstable_tickers,
                    }
                    for ticker in tickers
                ],
                **base_meta,
            )

        details = []
        failed_ticker_details = []
        for ticker in tickers:
            metrics = build_ticker_metrics(ticker, close_prices.get(ticker), sample_type=_sample_type(ticker, mapping))
            if metrics:
                details.append(metrics)
            else:
                raw_reason = diagnose_ticker_failure(close_prices.get(ticker))
                failed_ticker_details.append(
                    {
                        "ticker": ticker,
                        "reason": normalize_failure_reason(raw_reason),
                        "debug": DOWNLOAD_FAILURE_DEBUG.get(ticker, raw_reason),
                        "unstable": ticker in unstable_tickers,
                    }
                )
        valid_tickers = {row["ticker"] for row in details}
        failed_tickers = [ticker for ticker in tickers if ticker not in valid_tickers]
        benchmark_metrics = build_ticker_metrics(benchmark, close_prices.get(benchmark), sample_type="Benchmark")
        if not details or not benchmark_metrics:
            if not benchmark_metrics:
                raw_reason = diagnose_ticker_failure(close_prices.get(benchmark))
                failed_ticker_details.append(
                    {
                        "ticker": benchmark,
                        "reason": normalize_failure_reason(raw_reason),
                        "debug": DOWNLOAD_FAILURE_DEBUG.get(benchmark, raw_reason),
                        "unstable": benchmark in unstable_tickers,
                    }
                )
            return _result(
                available=False,
                message="Insufficient ticker or benchmark data.",
                reason_code="market_data_failed",
                valid_ticker_count=len(details),
                failed_tickers=failed_tickers,
                failed_ticker_details=failed_ticker_details,
                **base_meta,
            )

        summary = build_industry_market_summary(details, benchmark_metrics)
        return _result(
            available=True,
            message="ok",
            valid_ticker_count=len(details),
            failed_tickers=failed_tickers,
            failed_ticker_details=failed_ticker_details,
            details=details,
            **base_meta,
            **summary,
        )
    except Exception as exc:  # pragma: no cover - defensive runtime fallback for Streamlit
        return _result(
            available=False,
            message=f"Market data unavailable: {exc}",
            reason_code="market_data_failed",
            tickers=[],
            benchmark=None,
        )


def download_close_prices(tickers: list[str]) -> pd.DataFrame:
    """Download adjusted daily close prices for tickers."""

    if not tickers or yf is None:
        return pd.DataFrame()
    try:
        data = quiet_yfinance_download(
            tickers=tickers,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        for ticker in tickers:
            DOWNLOAD_FAILURE_DEBUG[ticker] = str(exc)
        return pd.DataFrame()
    if data.empty:
        for ticker in tickers:
            DOWNLOAD_FAILURE_DEBUG.setdefault(ticker, "Yahoo Finance returned no price data")
        return pd.DataFrame()
    close = extract_close_frame(data, tickers)
    return close.dropna(how="all")


@st.cache_data(ttl=3600, show_spinner=False)
def download_single_close_prices(ticker: str) -> pd.DataFrame:
    """Download one ticker through the same cached, quiet path."""

    return download_close_prices([ticker])


def quiet_yfinance_download(**kwargs: Any) -> pd.DataFrame:
    """Run yfinance download without leaking raw provider output to the terminal."""

    if yf is None:
        return pd.DataFrame()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            data = yf.download(**kwargs)
    finally:
        captured = "\n".join(
            value for value in [stdout_buffer.getvalue().strip(), stderr_buffer.getvalue().strip()] if value
        )
        if captured:
            tickers = kwargs.get("tickers", [])
            if isinstance(tickers, str):
                tickers = [tickers]
            for ticker in tickers:
                DOWNLOAD_FAILURE_DEBUG[str(ticker)] = captured
            if DEBUG_MARKET_DATA:
                print(captured)
    return data


def extract_close_frame(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Extract a ticker-column close-price frame from yfinance output."""

    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"].copy()
        elif "Close" in data.columns.get_level_values(1):
            close = data.xs("Close", axis=1, level=1).copy()
        else:
            return pd.DataFrame()
    else:
        close = data[["Close"]].rename(columns={"Close": tickers[0]}) if "Close" in data else pd.DataFrame()
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    return close.reindex(columns=tickers)


def retry_missing_close_prices(close_prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Retry individual downloads for tickers missing from the batch result."""

    if close_prices.empty:
        close_prices = pd.DataFrame()
    for ticker in tickers:
        if _series_has_data(close_prices.get(ticker)):
            continue
        retry = download_single_close_prices(ticker)
        if _series_has_data(retry.get(ticker)):
            close_prices[ticker] = retry[ticker]
            continue
        sleep(0.5)
        retry = download_single_close_prices(ticker)
        if _series_has_data(retry.get(ticker)):
            close_prices[ticker] = retry[ticker]
    return close_prices.dropna(how="all")


def build_ticker_metrics(
    ticker: str,
    prices: pd.Series | None,
    sample_type: str = "Leader",
) -> dict[str, Any] | None:
    """Compute moving-average and return metrics for one ticker."""

    if prices is None:
        return None
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty or len(clean) <= 21:
        return None
    latest_close = float(clean.iloc[-1])
    close_21d_ago = _past_close(clean, 21)
    close_63d_ago = _past_close(clean, 63)
    close_126d_ago = _past_close(clean, 126)
    ma20 = _latest_ma(clean, 20)
    ma50 = _latest_ma(clean, 50)
    ma200 = _latest_ma(clean, 200)
    return {
        "ticker": ticker,
        "sample_type": sample_type,
        "latest_close": latest_close,
        "close_21d_ago": close_21d_ago,
        "close_63d_ago": close_63d_ago,
        "close_126d_ago": close_126d_ago,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "above_ma20": _above(latest_close, ma20),
        "above_ma50": _above(latest_close, ma50),
        "above_ma200": _above(latest_close, ma200),
        "return_1m": _period_return(clean, 21),
        "return_3m": _period_return(clean, 63),
        "return_6m": _period_return(clean, 126),
    }


def build_industry_market_summary(
    details: list[dict[str, Any]],
    benchmark_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate ticker metrics into an industry-level confirmation score."""

    above_ma20_ratio, above_ma20_count, above_ma20_total = _ratio_stats(row["above_ma20"] for row in details)
    above_ma50_ratio, above_ma50_count, above_ma50_total = _ratio_stats(row["above_ma50"] for row in details)
    above_ma200_ratio, above_ma200_count, above_ma200_total = _ratio_stats(row["above_ma200"] for row in details)
    average_1m_return = _mean_metric(details, "return_1m")
    average_3m_return = _mean_metric(details, "return_3m")
    average_6m_return = _mean_metric(details, "return_6m")
    median_3m_return = _median_metric(details, "return_3m")
    benchmark_3m_return = benchmark_metrics.get("return_3m")
    relative_strength = None
    if median_3m_return is not None and benchmark_3m_return is not None:
        relative_strength = median_3m_return - benchmark_3m_return
    score = calculate_market_confirmation_score(
        above_ma20_ratio=above_ma20_ratio,
        above_ma50_ratio=above_ma50_ratio,
        above_ma200_ratio=above_ma200_ratio,
        relative_strength=relative_strength,
        median_3m_return=median_3m_return,
    )
    return {
        "score": score,
        "above_ma20_ratio": above_ma20_ratio,
        "above_ma20_count": above_ma20_count,
        "above_ma20_total": above_ma20_total,
        "above_ma50_ratio": above_ma50_ratio,
        "above_ma50_count": above_ma50_count,
        "above_ma50_total": above_ma50_total,
        "above_ma200_ratio": above_ma200_ratio,
        "above_ma200_count": above_ma200_count,
        "above_ma200_total": above_ma200_total,
        "average_1m_return": average_1m_return,
        "average_3m_return": average_3m_return,
        "average_6m_return": average_6m_return,
        "median_3m_return": median_3m_return,
        "benchmark_3m_return": benchmark_3m_return,
        "relative_strength": relative_strength,
    }


def calculate_market_confirmation_score(
    *,
    above_ma20_ratio: float | None,
    above_ma50_ratio: float | None,
    above_ma200_ratio: float | None,
    relative_strength: float | None,
    median_3m_return: float | None,
) -> float:
    """Calculate a simple 0-10 market confirmation score.

    Breadth carries most of the weight. Return inputs use median values and
    capped ranges so one extreme ticker cannot dominate the score.
    """

    ma20_component = (above_ma20_ratio or 0.0) * 2.0
    ma50_component = (above_ma50_ratio or 0.0) * 2.5
    ma200_component = (above_ma200_ratio or 0.0) * 2.5
    relative_component = _bounded_score(_cap(relative_strength, -0.15, 0.15), lower=-0.10, upper=0.10) * 2.0
    return_component = _bounded_score(_cap(median_3m_return, -0.20, 0.25), lower=-0.10, upper=0.15) * 1.0
    return round(
        max(0.0, min(9.5, ma20_component + ma50_component + ma200_component + relative_component + return_component)),
        1,
    )


def _result(**kwargs: Any) -> dict[str, Any]:
    """Return a serializable result dictionary."""

    return MarketDataResult(**kwargs).__dict__


def _latest_ma(prices: pd.Series, window: int) -> float | None:
    if len(prices) < window:
        return None
    value = prices.rolling(window).mean().iloc[-1]
    return None if pd.isna(value) else float(value)


def _period_return(prices: pd.Series, periods: int) -> float | None:
    past_close = _past_close(prices, periods)
    if past_close is None:
        return None
    end = float(prices.iloc[-1])
    if past_close == 0:
        return None
    return end / past_close - 1


def _past_close(prices: pd.Series, periods: int) -> float | None:
    if len(prices) <= periods:
        return None
    value = prices.iloc[-periods - 1]
    return None if pd.isna(value) else float(value)


def _above(latest_close: float, moving_average: float | None) -> bool | None:
    return None if moving_average is None else latest_close > moving_average


def _ratio_stats(values: Any) -> tuple[float | None, int, int]:
    valid = [value for value in values if value is not None]
    if not valid:
        return None, 0, 0
    count = sum(1 for value in valid if value)
    total = len(valid)
    return count / total, count, total


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None
    return float(sum(values) / len(values))


def _median_metric(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return None
    return float(pd.Series(values).median())


def _bounded_score(value: float | None, *, lower: float, upper: float) -> float:
    if value is None:
        return 0.0
    if upper <= lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))


def _cap(value: float | None, lower: float, upper: float) -> float | None:
    if value is None:
        return None
    return max(lower, min(upper, value))


def _sample_type(ticker: str, mapping: dict[str, Any]) -> str:
    if ticker in mapping.get("etfs", []):
        return "ETF"
    return "Leader"


def diagnose_ticker_failure(prices: pd.Series | None) -> str:
    """Return a human-readable reason for ticker metric failure."""

    if prices is None:
        return "missing close"
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    if clean.empty:
        return "empty data"
    if len(clean) <= 21:
        return "insufficient history"
    return "metric calculation failed"


def normalize_failure_reason(reason: object) -> str:
    """Normalize yfinance no-data messages without implying a confirmed delisting."""

    raw = str(reason or "")
    lowered = raw.lower()
    no_data_tokens = [
        "possibly delisted",
        "no price data found",
        "no data found",
        "empty data",
        "missing close",
    ]
    if any(token in lowered for token in no_data_tokens):
        return "yahoo_no_price_data"
    return raw


def _series_has_data(series: pd.Series | None) -> bool:
    if series is None:
        return False
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return not clean.empty


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
