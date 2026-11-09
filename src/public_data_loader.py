"""Public-mode market data loader for Streamlit Cloud deployments."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import re
import json

import pandas as pd
import requests
import yfinance as yf


PUBLIC_TICKERS = ["QQQ", "SMH", "SOXX", "GLD", "SPY", "ACWI", "UUP", "TLT", "GC=F", "DFII10"]


def load_public_market_snapshot(tickers: list[str] | None = None, period: str = "1y") -> pd.DataFrame:
    """Load a public market snapshot without relying on local reports/data files."""

    symbols = tickers or PUBLIC_TICKERS
    frames = load_public_ohlc_data(symbols, period)
    rows = []
    for symbol in symbols:
        frame = frames.get(symbol, pd.DataFrame())
        if frame is None or frame.empty or "Close" not in frame.columns:
            rows.append(missing_snapshot_row(symbol))
            continue
        enriched = add_public_indicators(frame)
        rows.append(build_snapshot_row(symbol, enriched))
    return pd.DataFrame(rows)


def load_public_ohlc_data(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Load OHLC data from yfinance, then Yahoo Chart API fallback."""

    data = {symbol: pd.DataFrame() for symbol in symbols}
    yahoo_symbols = [symbol for symbol in symbols if symbol != "DFII10"]
    try:
        raw = yf.download(
            tickers=yahoo_symbols,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=True,
            timeout=6,
        )
    except Exception:
        raw = pd.DataFrame()

    if raw is not None and not raw.empty:
        for symbol in yahoo_symbols:
            try:
                frame = raw[symbol].copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
                normalized = normalize_ohlc_frame(frame)
                if not normalized.empty:
                    normalized.attrs["data_source"] = "yfinance"
                    data[symbol] = normalized
            except Exception:
                data[symbol] = pd.DataFrame()

    if "DFII10" in data:
        data["DFII10"] = download_fred_real_yield()
    missing = [symbol for symbol, frame in data.items() if frame.empty and symbol != "DFII10"]
    if missing:
        for symbol, frame in download_yahoo_chart_api(missing, period).items():
            if not frame.empty:
                data[symbol] = frame
    cache_dir = Path(__file__).resolve().parents[1] / "data" / "public_prices"
    for symbol in symbols:
        cache = cache_dir / (re.sub(r"[^A-Za-z0-9_-]", "_", symbol) + "_" + re.sub(r"[^A-Za-z0-9]", "", period) + ".json")
        frame = data[symbol]
        if not frame.empty:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                payload = {"source": frame.attrs.get("data_source"), "data": frame.to_json(orient="split", date_format="iso")}
                temp = cache.with_suffix(".tmp")
                temp.write_text(json.dumps(payload), encoding="utf-8")
                temp.replace(cache)
            except OSError:
                pass
        elif cache.exists():
            try:
                from io import StringIO
                payload = json.loads(cache.read_text(encoding="utf-8"))
                frame = normalize_ohlc_frame(pd.read_json(StringIO(payload["data"]), orient="split"))
                frame.attrs["data_source"] = "cache"
                data[symbol] = frame
            except (ValueError, KeyError, OSError):
                pass

    return data


def build_public_asset_table(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Convert public snapshot to the app's asset-risk table schema."""

    if snapshot.empty:
        return pd.DataFrame()
    table = snapshot.copy()
    table["资产"] = table["代码"].map(PUBLIC_ASSET_NAMES).fillna(table["代码"])
    table["最新价格"] = table["latest_price"].map(lambda value: f"{value:.2f}" if pd.notna(value) else "N/A")
    table["今日涨跌幅"] = table["today_return"].map(format_percent)
    table["RSI"] = table["RSI数值"].map(lambda value: f"{value:.1f}" if pd.notna(value) else "N/A")
    table["当前回撤"] = table["当前回撤数值"].map(format_percent)
    return table[
        [
            "资产",
            "代码",
            "最新价格",
            "今日涨跌幅",
            "RSI",
            "当前回撤",
            "风险状态",
            "RSI数值",
            "当前回撤数值",
            "今日涨跌幅数值",
            "data_quality",
            "price_date",
            "data_source",
        ]
    ]


def infer_public_market_status(snapshot: pd.DataFrame) -> str:
    """Infer a conservative public market status from QQQ/SMH."""

    if snapshot.empty:
        return "neutral"
    focus = snapshot.loc[snapshot["代码"].isin(["QQQ", "SMH"])]
    if focus.empty:
        return "neutral"
    if (pd.to_numeric(focus["RSI数值"], errors="coerce") > 70).any():
        return "do_not_chase"
    if (focus["风险状态"] == "risk-off").all():
        return "risk-off"
    if (focus["风险状态"] == "risk-on").any():
        return "risk-on"
    return "neutral"


def add_public_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Add MA, RSI, drawdown and period return helpers."""

    enriched = normalize_ohlc_frame(frame)
    if enriched.empty:
        return enriched
    close = pd.to_numeric(enriched["Close"], errors="coerce")
    enriched["MA20"] = close.rolling(20).mean()
    enriched["MA60"] = close.rolling(60).mean()
    enriched["RSI14"] = calculate_rsi(close, 14)
    rolling_high = close.cummax()
    enriched["drawdown"] = close / rolling_high - 1
    enriched["today_return"] = close.pct_change()
    return enriched


def build_snapshot_row(symbol: str, frame: pd.DataFrame) -> dict:
    """Build one public snapshot row."""

    clean = frame.dropna(subset=["Close"])
    if clean.empty:
        return missing_snapshot_row(symbol)
    latest = clean.iloc[-1]
    close = pd.to_numeric(clean["Close"], errors="coerce").dropna()
    rsi = safe_float(latest.get("RSI14"))
    drawdown = safe_float(latest.get("drawdown"))
    latest_price = safe_float(latest.get("Close"))
    today_return = safe_float(latest.get("today_return"))
    risk_status = classify_public_risk_status(latest)
    row = {
        "代码": symbol,
        "latest_price": latest_price,
        "today_return": today_return,
        "今日涨跌幅数值": today_return,
        "RSI数值": rsi,
        "drawdown_from_high": drawdown,
        "当前回撤数值": drawdown,
        "风险状态": risk_status,
        "1月收益": period_return(close, 21),
        "3月收益": period_return(close, 63),
        "6月收益": period_return(close, 126),
        "YTD收益": ytd_return(close),
        "1年收益": period_return(close, 252),
        "data_quality": snapshot_quality(frame, clean.index[-1]),
        "price_date": str(clean.index[-1].date()),
        "data_source": frame.attrs.get("data_source", "public_market"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return row


def missing_snapshot_row(symbol: str) -> dict:
    """Return a stable missing ticker row."""

    return {
        "代码": symbol,
        "latest_price": pd.NA,
        "today_return": pd.NA,
        "今日涨跌幅数值": pd.NA,
        "RSI数值": pd.NA,
        "drawdown_from_high": pd.NA,
        "当前回撤数值": pd.NA,
        "风险状态": "data_unavailable",
        "1月收益": pd.NA,
        "3月收益": pd.NA,
        "6月收益": pd.NA,
        "YTD收益": pd.NA,
        "1年收益": pd.NA,
        "data_quality": "missing",
        "price_date": "",
        "data_source": "missing",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def download_yahoo_chart_api(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Fetch bounded, parallel requests; retain only valid OHLC observations."""
    def fetch(symbol):
        for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
            try:
                response = requests.get(
                    f"https://{host}/v8/finance/chart/{symbol}",
                    params={"range": period, "interval": "1d", "events": "history"},
                    headers={"User-Agent": "Mozilla/5.0"}, timeout=(3, 6),
                )
                response.raise_for_status()
                payload = response.json()["chart"]["result"][0]
                timestamps = pd.to_datetime(payload.get("timestamp", []), unit="s", utc=True).tz_convert(None)
                quote = payload.get("indicators", {}).get("quote", [{}])[0]
                frame = pd.DataFrame({k.title(): quote.get(k, []) for k in ("open", "high", "low", "close")}, index=timestamps)
                frame = normalize_ohlc_frame(frame)
                if not frame.empty:
                    frame.attrs["data_source"] = "yahoo_chart_api"
                    return symbol, frame
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
                continue
        return symbol, pd.DataFrame()
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(symbols)))) as pool:
        return dict(pool.map(fetch, symbols))


def normalize_ohlc_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLC columns."""

    if frame is None or frame.empty:
        return pd.DataFrame()
    normalized = frame.copy()
    normalized.index = pd.to_datetime(normalized.index)
    normalized = normalized.rename(columns={column: str(column).title() for column in normalized.columns})
    if "Close" not in normalized.columns:
        return pd.DataFrame()
    columns = [column for column in ["Open", "High", "Low", "Close"] if column in normalized.columns]
    return normalized[columns].dropna(how="all").sort_index()


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI."""

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def classify_public_risk_status(latest: pd.Series) -> str:
    """Classify risk state from public technical data."""

    rsi = safe_float(latest.get("RSI14"))
    close = safe_float(latest.get("Close"))
    ma60 = safe_float(latest.get("MA60"))
    if rsi is not None and rsi > 70:
        return "risk-on"
    if close is not None and ma60 is not None and close < ma60:
        return "risk-off"
    return "neutral"


def period_return(close: pd.Series, periods: int):
    """Calculate period return using trading-day offset."""

    if close is None or len(close) <= periods:
        return pd.NA
    start = close.iloc[-periods]
    end = close.iloc[-1]
    if pd.isna(start) or not start:
        return pd.NA
    return float(end / start - 1)


def ytd_return(close: pd.Series):
    """Calculate year-to-date return."""

    if close is None or close.empty:
        return pd.NA
    current_year = close.index[-1].year
    year_data = close.loc[close.index.year == current_year]
    if year_data.empty:
        return pd.NA
    start = year_data.iloc[0]
    end = year_data.iloc[-1]
    return float(end / start - 1) if start else pd.NA


def safe_float(value):
    """Normalize numeric values."""

    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_percent(value) -> str:
    """Format decimal percent."""

    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.2%}"


PUBLIC_ASSET_NAMES = {
    "QQQ": "纳指100",
    "SMH": "半导体",
    "SOXX": "半导体辅助",
    "GLD": "黄金ETF",
    "SPY": "标普500",
    "ACWI": "全球股票",
    "UUP": "美元",
    "TLT": "长期美债",
    "GC=F": "COMEX黄金",
    "DFII10": "美国10年期实际利率",
}


def snapshot_quality(frame, latest_date):
    if frame.attrs.get("data_source") == "cache":
        return "cache"
    latest = pd.Timestamp(latest_date)
    if latest.tzinfo is not None:
        latest = latest.tz_convert(None)
    return "stale" if (pd.Timestamp.now(tz="UTC").tz_localize(None) - latest).days > 5 else "fresh"


def download_fred_real_yield():
    """Load the actual FRED series; never substitute a Treasury ETF."""
    from io import StringIO
    try:
        response = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": "DFII10", "cosd": (pd.Timestamp.now() - pd.Timedelta(days=400)).strftime("%Y-%m-%d")}, timeout=(3, 6))
        response.raise_for_status()
        raw = pd.read_csv(StringIO(response.text))
        date_col = "observation_date" if "observation_date" in raw else "DATE"
        values = pd.to_numeric(raw["DFII10"], errors="coerce")
        frame = pd.DataFrame({"Close": values.to_numpy()}, index=pd.to_datetime(raw[date_col], errors="coerce")).dropna()
        frame.attrs["data_source"] = "fred"
        return frame
    except (requests.RequestException, ValueError, KeyError):
        return pd.DataFrame()
