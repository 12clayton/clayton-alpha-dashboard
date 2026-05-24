from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen
import json

import pandas as pd

from report import write_daily_report
from risk_rules import build_advice, evaluate_data_quality


HOLDINGS_FILE = Path("holdings.csv")
AUTO_INVEST_PLAN_FILE = Path("auto_invest_plan.csv")
TARGET_ALLOCATION_FILE = Path("target_allocation.csv")
CACHE_FILE = Path("data_cache.csv")
OUTPUT_FILE = Path("daily_report.xlsx")

PROXY_ETFS = ["SPY", "QQQ", "GLD", "SOXX", "EWJ"]
MACRO_TICKERS = ["VIX", "DGS10"]
ALL_MARKET_KEYS = PROXY_ETFS + MACRO_TICKERS
CRITICAL_KEYS = ["SPY", "QQQ", "SOXX", "VIX", "DGS10"]

STOOQ_SYMBOLS = {
    "SPY": "spy.us",
    "QQQ": "qqq.us",
    "GLD": "gld.us",
    "SOXX": "soxx.us",
    "EWJ": "ewj.us",
}

FRED_IDS = {
    "VIX": "VIXCLS",
    "DGS10": "DGS10",
}

CBOE_VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"

CACHE_COLUMNS = [
    "proxy",
    "date",
    "previous_close",
    "latest_close",
    "return_pct",
    "drawdown_from_high",
    "value",
    "source",
    "updated_at",
]

WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


@dataclass(frozen=True)
class MarketSnapshot:
    proxy: str
    date: str | None
    previous_close: float | None
    latest_close: float | None
    return_pct: float | None
    drawdown_from_high: float | None
    value: float | None
    source: str
    data_quality: str
    status: str


def read_csv_smart(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"无法读取 {path}，请检查文件编码。最后错误：{last_error}")


def parse_date(value: object) -> date | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def count_weekly(start: date, end: date, day_name: str) -> int:
    weekday = WEEKDAY_MAP.get(str(day_name).strip().lower())
    if weekday is None:
        raise ValueError(f"weekly 定投的 day 无法识别：{day_name}")
    first = start
    while first.weekday() != weekday:
        first += timedelta(days=1)
    if first > end:
        return 0
    return ((end - first).days // 7) + 1


def count_biweekly(start: date, end: date) -> int:
    if start > end:
        return 0
    return ((end - start).days // 14) + 1


def count_monthly(start: date, end: date, day_value: object) -> int:
    try:
        target_day = int(day_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"monthly 定投的 day 需要填写日期数字，例如 1 或 15：{day_value}") from exc

    count = 0
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        next_month = date(cursor.year + int(cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        invest_day = date(cursor.year, cursor.month, min(target_day, last_day))
        if start <= invest_day <= end:
            count += 1
        cursor = next_month
    return count


def count_investments(row: pd.Series, today: date) -> int:
    start = parse_date(row["start_date"])
    if start is None or today < start:
        return 0
    end = parse_date(row.get("end_date"))
    effective_end = min(today, end) if end else today
    if effective_end < start:
        return 0

    frequency = str(row["frequency"]).strip().lower()
    if frequency == "weekly":
        return count_weekly(start, effective_end, row["day"])
    if frequency == "biweekly":
        return count_biweekly(start, effective_end)
    if frequency == "monthly":
        return count_monthly(start, effective_end, row["day"])
    raise ValueError(f"暂不支持的定投频率：{row['frequency']}")


def build_current_holdings(holdings: pd.DataFrame, plan: pd.DataFrame, today: date) -> pd.DataFrame:
    holdings = holdings.copy()
    holdings["amount"] = pd.to_numeric(holdings["amount"], errors="coerce").fillna(0)

    plan = plan.copy()
    plan["amount"] = pd.to_numeric(plan["amount"], errors="coerce").fillna(0)
    plan["invest_count"] = plan.apply(lambda row: count_investments(row, today), axis=1)
    plan["accumulated_auto_invest"] = plan["amount"] * plan["invest_count"]

    accumulated = plan.groupby("fund", as_index=False)["accumulated_auto_invest"].sum()
    current = holdings.merge(accumulated, on="fund", how="left")
    current["accumulated_auto_invest"] = current["accumulated_auto_invest"].fillna(0)
    current["initial_amount"] = current["amount"]
    current["current_amount"] = current["initial_amount"] + current["accumulated_auto_invest"]
    return current.drop(columns=["amount"])


def download_text(url: str, timeout: int = 20) -> str:
    headers = {"User-Agent": "Global-QDII-Risk-Monitor/3.0"}
    request_error: Exception | None = None
    try:
        import requests

        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.text
    except ModuleNotFoundError:
        pass
    except Exception as exc:
        request_error = exc

    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        if request_error is not None:
            raise RuntimeError("requests 和 urllib 都无法下载数据") from exc
        raise


def calculate_from_series(proxy: str, dates: list[str], closes: list[float], source: str) -> MarketSnapshot:
    valid = pd.DataFrame({"date": pd.to_datetime(dates, errors="coerce"), "close": pd.to_numeric(closes, errors="coerce")})
    valid = valid.dropna(subset=["date", "close"]).sort_values("date")
    if len(valid) < 2:
        raise ValueError("有效交易日少于2天")

    previous = valid.iloc[-2]
    latest = valid.iloc[-1]
    previous_close = float(previous["close"])
    latest_close = float(latest["close"])
    return_pct = latest_close / previous_close - 1
    drawdown = latest_close / float(valid["close"].max()) - 1

    return MarketSnapshot(
        proxy=proxy,
        date=latest["date"].strftime("%Y-%m-%d"),
        previous_close=previous_close,
        latest_close=latest_close,
        return_pct=return_pct,
        drawdown_from_high=drawdown,
        value=latest_close,
        source=source,
        data_quality="fresh",
        status="成功",
    )


def fetch_yahoo_etf(proxy: str) -> MarketSnapshot:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{proxy}?range=7d&interval=1d"
    payload = json.loads(download_text(url))
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise ValueError("Yahoo 返回空结果")

    chart = result[0]
    timestamps = chart.get("timestamp") or []
    quotes = chart.get("indicators", {}).get("quote") or []
    if not timestamps or not quotes:
        raise ValueError("Yahoo 返回数据缺少 timestamp 或 quote")

    closes = quotes[0].get("close") or []
    dates = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") for ts in timestamps]
    return calculate_from_series(proxy, dates, closes, "yahoo")


def fetch_stooq_etf(proxy: str) -> MarketSnapshot:
    symbol = STOOQ_SYMBOLS[proxy]
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    raw_text = download_text(url)
    first_line = next((line.strip() for line in raw_text.splitlines() if line.strip()), "")
    if "date" not in first_line.lower() or "close" not in first_line.lower():
        raise ValueError("Stooq 返回内容不是日线 CSV")

    data = pd.read_csv(StringIO(raw_text))
    normalized = {str(column).strip().lower(): column for column in data.columns}
    if "date" not in normalized or "close" not in normalized:
        raise ValueError(f"Stooq 返回数据缺少 Date 或 Close 列，实际列名：{list(data.columns)}")
    return calculate_from_series(proxy, data[normalized["date"]].astype(str).tolist(), data[normalized["close"]].tolist(), "stooq")


def fetch_fred_series(proxy: str, fred_id: str) -> MarketSnapshot:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"
    data = pd.read_csv(StringIO(download_text(url)))
    normalized = {str(column).strip().lower(): column for column in data.columns}
    if "observation_date" not in normalized or fred_id.lower() not in normalized:
        raise ValueError("FRED 返回数据列不完整")

    parsed = pd.DataFrame(
        {
            "date": pd.to_datetime(data[normalized["observation_date"]], errors="coerce"),
            "value": pd.to_numeric(data[normalized[fred_id.lower()]].replace(".", pd.NA), errors="coerce"),
        }
    )
    parsed = parsed.dropna(subset=["date", "value"]).sort_values("date")
    if len(parsed) < 2:
        raise ValueError("FRED 有效数据少于2天")

    previous = parsed.iloc[-2]
    latest = parsed.iloc[-1]
    previous_value = float(previous["value"])
    latest_value = float(latest["value"])
    return MarketSnapshot(
        proxy=proxy,
        date=latest["date"].strftime("%Y-%m-%d"),
        previous_close=previous_value,
        latest_close=latest_value,
        return_pct=latest_value / previous_value - 1 if previous_value else None,
        drawdown_from_high=None,
        value=latest_value,
        source="fred",
        data_quality="fresh",
        status="成功",
    )


def fetch_cboe_vix() -> MarketSnapshot:
    data = pd.read_csv(StringIO(download_text(CBOE_VIX_URL)))
    normalized = {str(column).strip().lower(): column for column in data.columns}
    date_col = normalized.get("date")
    close_col = normalized.get("close")
    if not date_col or not close_col:
        raise ValueError("Cboe 返回数据缺少 DATE 或 CLOSE")
    return calculate_from_series("VIX", data[date_col].astype(str).tolist(), data[close_col].tolist(), "cboe")


def empty_cache() -> pd.DataFrame:
    return pd.DataFrame(columns=CACHE_COLUMNS)


def load_cache() -> pd.DataFrame:
    if not CACHE_FILE.exists():
        return empty_cache()
    try:
        cache = read_csv_smart(CACHE_FILE)
    except Exception:
        return empty_cache()
    for column in CACHE_COLUMNS:
        if column not in cache.columns:
            cache[column] = pd.NA
    return cache[CACHE_COLUMNS]


def update_cache(cache: pd.DataFrame, snapshots: list[MarketSnapshot]) -> None:
    fresh_items = [item for item in snapshots if item.data_quality == "fresh"]
    if not fresh_items:
        if not CACHE_FILE.exists():
            empty_cache().to_csv(CACHE_FILE, index=False, encoding="utf-8-sig")
        return

    new_rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in fresh_items:
        new_rows.append(
            {
                "proxy": item.proxy,
                "date": item.date,
                "previous_close": item.previous_close,
                "latest_close": item.latest_close,
                "return_pct": item.return_pct,
                "drawdown_from_high": item.drawdown_from_high,
                "value": item.value,
                "source": item.source,
                "updated_at": now,
            }
        )

    combined = pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True)
    combined["updated_at_sort"] = pd.to_datetime(combined["updated_at"], errors="coerce")
    combined["date_sort"] = pd.to_datetime(combined["date"], errors="coerce")
    combined = combined.sort_values(["proxy", "date_sort", "updated_at_sort"])
    combined = combined.drop_duplicates(subset=["proxy"], keep="last")
    combined = combined.drop(columns=["updated_at_sort", "date_sort"])
    combined[CACHE_COLUMNS].to_csv(CACHE_FILE, index=False, encoding="utf-8-sig")


def fetch_from_cache(proxy: str, cache: pd.DataFrame, previous_status: str) -> MarketSnapshot:
    matched = cache.loc[cache["proxy"] == proxy].copy()
    if matched.empty:
        return MarketSnapshot(proxy, None, None, None, None, None, None, "none", "missing", f"{previous_status}；本地缓存缺失")

    matched["date_sort"] = pd.to_datetime(matched["date"], errors="coerce")
    matched["updated_at_sort"] = pd.to_datetime(matched["updated_at"], errors="coerce")
    matched = matched.sort_values(["date_sort", "updated_at_sort"])
    row = matched.iloc[-1]

    def number_or_none(value: object) -> float | None:
        number = pd.to_numeric(value, errors="coerce")
        if pd.isna(number):
            return None
        return float(number)

    return MarketSnapshot(
        proxy=proxy,
        date=None if pd.isna(row["date"]) else str(row["date"]),
        previous_close=number_or_none(row["previous_close"]),
        latest_close=number_or_none(row["latest_close"]),
        return_pct=number_or_none(row["return_pct"]),
        drawdown_from_high=number_or_none(row["drawdown_from_high"]),
        value=number_or_none(row["value"]),
        source="cache",
        data_quality="stale",
        status="在线数据失败，使用本地缓存",
    )


def fetch_etf_with_fallback(proxy: str, cache: pd.DataFrame) -> MarketSnapshot:
    print(f"正在抓取 {proxy}：Yahoo...")
    try:
        item = fetch_yahoo_etf(proxy)
        print(f"{proxy} Yahoo 成功，涨跌幅：{item.return_pct:.2%}")
        return item
    except Exception:
        print(f"{proxy} Yahoo 失败，切换 Stooq...")

    try:
        item = fetch_stooq_etf(proxy)
        print(f"{proxy} Stooq 成功，涨跌幅：{item.return_pct:.2%}")
        return item
    except Exception:
        print(f"{proxy} Stooq 失败，使用本地缓存...")

    item = fetch_from_cache(proxy, cache, "Yahoo 和 Stooq 均失败")
    if item.data_quality == "stale":
        pct_text = f"{item.return_pct:.2%}" if item.return_pct is not None else "暂无"
        print(f"{proxy} 使用本地缓存，日期：{item.date}，涨跌幅：{pct_text}")
    else:
        print(f"{proxy} 本地缓存也不可用")
    return item


def fetch_vix_with_fallback(cache: pd.DataFrame) -> MarketSnapshot:
    print("正在抓取 VIX：FRED...")
    try:
        item = fetch_fred_series("VIX", FRED_IDS["VIX"])
        print(f"VIX FRED 成功，最新值：{item.value:.2f}")
        return item
    except Exception:
        print("VIX FRED 失败，切换 Cboe...")

    try:
        item = fetch_cboe_vix()
        print(f"VIX Cboe 成功，最新值：{item.value:.2f}")
        return item
    except Exception:
        print("VIX Cboe 失败，使用本地缓存...")

    item = fetch_from_cache("VIX", cache, "FRED 和 Cboe 均失败")
    if item.data_quality == "stale":
        value_text = f"{item.value:.2f}" if item.value is not None else "暂无"
        print(f"VIX 使用本地缓存，日期：{item.date}，最新值：{value_text}")
    else:
        print("VIX 本地缓存也不可用")
    return item


def fetch_dgs10_with_fallback(cache: pd.DataFrame) -> MarketSnapshot:
    print("正在抓取 DGS10：FRED...")
    try:
        item = fetch_fred_series("DGS10", FRED_IDS["DGS10"])
        change = None if item.latest_close is None or item.previous_close is None else item.latest_close - item.previous_close
        print(f"DGS10 FRED 成功，最新值：{item.value:.2f}，变化：{change:.2f}")
        return item
    except Exception:
        print("DGS10 FRED 失败，使用本地缓存...")

    item = fetch_from_cache("DGS10", cache, "FRED 失败")
    if item.data_quality == "stale":
        change = None if item.latest_close is None or item.previous_close is None else item.latest_close - item.previous_close
        change_text = f"{change:.2f}" if change is not None else "暂无"
        print(f"DGS10 使用本地缓存，日期：{item.date}，变化：{change_text}")
    else:
        print("DGS10 本地缓存也不可用")
    return item


def fetch_market_data() -> pd.DataFrame:
    cache = load_cache()
    snapshots = [fetch_etf_with_fallback(proxy, cache) for proxy in PROXY_ETFS]
    snapshots.append(fetch_vix_with_fallback(cache))
    snapshots.append(fetch_dgs10_with_fallback(cache))
    update_cache(cache, snapshots)

    rows = []
    for item in snapshots:
        us10y_change = None
        if item.proxy == "DGS10" and item.latest_close is not None and item.previous_close is not None:
            us10y_change = item.latest_close - item.previous_close
        rows.append(
            {
                "proxy": item.proxy,
                "date": item.date,
                "previous_close": item.previous_close,
                "latest_close": item.latest_close,
                "return_pct": item.return_pct,
                "drawdown_from_high": item.drawdown_from_high,
                "value": item.value,
                "us10y_change": us10y_change,
                "source": item.source,
                "data_quality": item.data_quality,
                "status": item.status,
            }
        )
    return pd.DataFrame(rows)


def build_holdings_report(current: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    returns = market.set_index("proxy")["return_pct"].to_dict()
    report = current.copy()
    report["proxy_return_pct"] = report["proxy"].map(returns)
    report["estimated_daily_pnl"] = report["current_amount"] * report["proxy_return_pct"].fillna(0)

    total_amount = report["current_amount"].sum()
    report["current_weight"] = report["current_amount"] / total_amount if total_amount else 0
    return report[
        [
            "fund",
            "initial_amount",
            "accumulated_auto_invest",
            "current_amount",
            "proxy",
            "category",
            "current_weight",
            "proxy_return_pct",
            "estimated_daily_pnl",
        ]
    ]


def build_category_report(holdings_report: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target = target.copy()
    target["target_weight"] = pd.to_numeric(target["target_weight"], errors="coerce").fillna(0) / 100

    total_amount = holdings_report["current_amount"].sum()
    category = holdings_report.groupby("category", as_index=False)["current_amount"].sum()
    category["current_weight"] = category["current_amount"] / total_amount if total_amount else 0
    category = category.merge(target, on="category", how="outer")
    category["current_amount"] = category["current_amount"].fillna(0)
    category["current_weight"] = category["current_weight"].fillna(0)
    category["target_weight"] = category["target_weight"].fillna(0)
    category["deviation"] = category["current_weight"] - category["target_weight"]
    return category[["category", "current_amount", "current_weight", "target_weight", "deviation"]]


def build_data_quality_report(market: pd.DataFrame) -> pd.DataFrame:
    return market[["proxy", "source", "data_quality", "date", "status"]].copy()


def build_errors(market: pd.DataFrame, holdings_report: pd.DataFrame) -> pd.DataFrame:
    errors: list[str] = []
    for _, row in market.iterrows():
        if row["data_quality"] != "fresh":
            errors.append(f"{row['proxy']}：{row['status']}，data_quality={row['data_quality']}")

    missing = holdings_report[holdings_report["proxy_return_pct"].isna()]
    for proxy in missing["proxy"].drop_duplicates():
        errors.append(f"{proxy}：return_pct 为空，该 proxy 对应基金今日盈亏按 0 处理")

    if not errors:
        errors = ["无"]
    return pd.DataFrame({"error": errors})


def summarize_console(
    holdings_report: pd.DataFrame,
    category_report: pd.DataFrame,
    market: pd.DataFrame,
    advice: list[str],
    quality_summary: dict[str, object],
) -> None:
    total_amount = float(holdings_report["current_amount"].sum())
    total_pnl = float(holdings_report["estimated_daily_pnl"].sum())
    total_return = total_pnl / total_amount if total_amount else 0

    proxy_pnl = holdings_report.groupby("proxy")["estimated_daily_pnl"].sum()
    main_drag = proxy_pnl.idxmin() if not proxy_pnl.empty and proxy_pnl.min() < 0 else "暂无明显拖累"
    main_contribution = proxy_pnl.idxmax() if not proxy_pnl.empty and proxy_pnl.max() > 0 else "暂无明显贡献"

    category_weights = category_report.set_index("category")["current_weight"].to_dict()
    tech_weight = sum(category_weights.get(item, 0) for item in ["nasdaq100", "global_growth", "global_tech", "ai_semiconductor"])
    gold_weight = category_weights.get("gold", 0)

    core_advice = "原仓持有，定投继续执行，不额外追高科技成长。"
    for item in advice:
        if item.startswith("核心建议："):
            core_advice = item.replace("核心建议：", "", 1)
            break

    reason_text = "；".join(quality_summary["reasons"]) if quality_summary["reasons"] else "全部关键数据为 fresh"
    print()
    print(f"当前组合总金额：{total_amount:.2f} 元")
    print(f"今日组合估算涨跌：{total_pnl:.2f} 元，{total_return:.2%}")
    print(f"主要拖累：{main_drag}")
    print(f"主要贡献：{main_contribution}")
    print(f"科技成长合计仓位：{tech_weight:.2%}")
    print(f"黄金仓位：{gold_weight:.2%}")
    print(f"数据质量：{quality_summary['label']}")
    print(f"是否允许额外加仓：{'是' if quality_summary['allow_extra_add'] else '否'}")
    print(f"数据说明：{reason_text}")
    print(f"核心建议：{core_advice}")


def main() -> None:
    try:
        today = date.today()
        print("正在读取 holdings.csv...")
        holdings = read_csv_smart(HOLDINGS_FILE)

        print("正在读取 auto_invest_plan.csv...")
        plan = read_csv_smart(AUTO_INVEST_PLAN_FILE)

        print("正在计算自动定投...")
        current = build_current_holdings(holdings, plan, today)

        target = read_csv_smart(TARGET_ALLOCATION_FILE)
        market = fetch_market_data()
        holdings_report = build_holdings_report(current, market)
        category_report = build_category_report(holdings_report, target)
        quality_summary = evaluate_data_quality(market)
        advice = build_advice(market, category_report, quality_summary)
        data_quality = build_data_quality_report(market)
        errors = build_errors(market, holdings_report)

        print("正在生成 daily_report.xlsx...")
        write_daily_report(OUTPUT_FILE, holdings_report, category_report, market, data_quality, advice, errors)
        summarize_console(holdings_report, category_report, market, advice, quality_summary)
    except Exception as exc:
        print("程序运行失败。")
        print(f"原因：{exc}")


if __name__ == "__main__":
    main()
