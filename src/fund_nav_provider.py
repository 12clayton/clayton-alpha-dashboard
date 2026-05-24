"""Real mutual fund NAV provider with multi-source fallback and local cache."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml


NAV_COLUMNS = [
    "fund_code",
    "fund_name",
    "nav_date",
    "nav",
    "daily_return",
    "purchase_status",
    "redemption_status",
    "data_source",
    "data_quality",
    "updated_at",
    "error_message",
]


def get_latest_fund_navs_for_funds(
    funds: pd.DataFrame,
    cache_path: Path,
    aliases_path: Path | None = None,
) -> pd.DataFrame:
    """Fetch latest real NAV rows for all configured funds."""

    aliases = load_fund_code_aliases(aliases_path) if aliases_path else {}
    rows = []
    for _, fund in funds.iterrows():
        fund_dict = fund.to_dict()
        code = resolve_fund_code(fund_dict, aliases)
        name = str(fund_dict.get("fund_name", ""))
        rows.append(get_latest_fund_nav(code, name, cache_path))
    return pd.DataFrame(rows, columns=NAV_COLUMNS)


def update_fund_nav_cache(
    portfolio_path: Path,
    cache_path: Path,
    aliases_path: Path | None = None,
) -> pd.DataFrame:
    """Update local NAV cache for all funds in portfolio.yaml."""

    portfolio = load_yaml(portfolio_path)
    funds = pd.DataFrame(portfolio.get("funds", []))
    if funds.empty:
        return pd.DataFrame(columns=NAV_COLUMNS)
    return get_latest_fund_navs_for_funds(funds, cache_path, aliases_path)


def get_latest_fund_nav(fund_code: str, fund_name: str, cache_path: Path) -> dict[str, Any]:
    """Get one latest NAV row from AKShare, Eastmoney, then local cache."""

    code = normalize_fund_code(fund_code)
    if not code:
        return missing_nav_row("", fund_name, "missing_code", "基金代码缺失")

    for fetcher in (fetch_nav_from_akshare, fetch_nav_from_eastmoney):
        row = fetcher(code, fund_name)
        if row.get("data_quality") == "fresh":
            upsert_nav_cache(cache_path, row)
            return row

    cached = find_cached_nav(cache_path, code)
    if cached is not None:
        return cached
    return missing_nav_row(code, fund_name, "missing_nav", "缓存缺失")


def fetch_nav_from_akshare(fund_code: str, fund_name: str) -> dict[str, Any]:
    """Fetch latest NAV via AKShare when it is installed."""

    try:
        import akshare as ak  # type: ignore
    except Exception:
        return missing_nav_row(fund_code, fund_name, "missing_nav", "akshare_unavailable")

    try:
        frame = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
    except Exception:
        return missing_nav_row(fund_code, fund_name, "missing_nav", "接口失败")

    if frame is None or frame.empty:
        return missing_nav_row(fund_code, fund_name, "missing_nav", "解析失败")

    latest = frame.iloc[-1].to_dict()
    return normalize_nav_record(
        record=latest,
        fund_code=fund_code,
        fund_name=fund_name,
        data_source="akshare",
    )


def fetch_nav_from_eastmoney(fund_code: str, fund_name: str) -> dict[str, Any]:
    """Fetch latest NAV from Eastmoney F10 historical NAV endpoint."""

    params = {"type": "lsjz", "code": fund_code, "page": 1, "per": 5}
    headers = {"User-Agent": "Mozilla/5.0"}
    last_error = "网络失败"
    for base_url in (
        "https://fund.eastmoney.com/f10/F10DataApi.aspx",
        "http://fund.eastmoney.com/f10/F10DataApi.aspx",
        "https://fundf10.eastmoney.com/F10DataApi.aspx",
    ):
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return parse_eastmoney_response(response.text, fund_code, fund_name)
        except requests.Timeout:
            last_error = "接口超时"
        except requests.RequestException:
            last_error = "网络失败"
        except ValueError:
            last_error = "解析失败"
    return missing_nav_row(fund_code, fund_name, "missing_nav", last_error)


def parse_eastmoney_response(text: str, fund_code: str, fund_name: str) -> dict[str, Any]:
    """Parse latest NAV from Eastmoney HTML response."""

    try:
        tables = pd.read_html(text)
    except Exception:
        tables = []

    for table in tables:
        if "净值日期" in table.columns:
            return normalize_nav_record(table.iloc[0].to_dict(), fund_code, fund_name, "eastmoney_f10")

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.I | re.S)
    for row_html in rows:
        cells = [clean_html(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.I | re.S)]
        if len(cells) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
            record = {
                "净值日期": cells[0],
                "单位净值": cells[1],
                "累计净值": cells[2] if len(cells) > 2 else "",
                "日增长率": cells[3] if len(cells) > 3 else "",
                "申购状态": cells[4] if len(cells) > 4 else "",
                "赎回状态": cells[5] if len(cells) > 5 else "",
            }
            return normalize_nav_record(record, fund_code, fund_name, "eastmoney_f10")

    raise ValueError("解析失败")


def normalize_nav_record(record: dict[str, Any], fund_code: str, fund_name: str, data_source: str) -> dict[str, Any]:
    """Normalize one NAV row from any provider."""

    nav_date = first_present(record, ["净值日期", "日期", "FSRQ", "nav_date"])
    nav = first_present(record, ["单位净值", "单位净值走势", "DWJZ", "nav"])
    daily_return = first_present(record, ["日增长率", "日涨幅", "JZZZL", "daily_return"])
    purchase_status = first_present(record, ["申购状态", "purchase_status"])
    redemption_status = first_present(record, ["赎回状态", "redemption_status"])
    return {
        "fund_code": normalize_fund_code(fund_code),
        "fund_name": fund_name,
        "nav_date": normalize_date_text(nav_date),
        "nav": parse_number(nav),
        "daily_return": parse_percent(daily_return),
        "purchase_status": safe_text(purchase_status) or "未知",
        "redemption_status": safe_text(redemption_status) or "未知",
        "data_source": data_source,
        "data_quality": "fresh",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_message": "",
    }


def load_fund_nav_cache(cache_path: Path) -> pd.DataFrame:
    """Load NAV cache safely."""

    if not cache_path.exists():
        return pd.DataFrame(columns=NAV_COLUMNS)
    try:
        frame = pd.read_csv(cache_path, dtype={"fund_code": str}, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame(columns=NAV_COLUMNS)
    for column in NAV_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["fund_code"] = frame["fund_code"].map(normalize_fund_code)
    return frame[NAV_COLUMNS]


def upsert_nav_cache(cache_path: Path, row: dict[str, Any]) -> None:
    """Write one successful NAV row into cache without duplicating fund_code + nav_date."""

    if row.get("data_quality") != "fresh":
        return
    cache = load_fund_nav_cache(cache_path)
    new_row = pd.DataFrame([row], columns=NAV_COLUMNS)
    if not cache.empty:
        same = (cache["fund_code"].astype(str) == str(row.get("fund_code", ""))) & (
            cache["nav_date"].astype(str) == str(row.get("nav_date", ""))
        )
        cache = cache.loc[~same].copy()
    cache = pd.concat([cache, new_row], ignore_index=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache.to_csv(cache_path, index=False, encoding="utf-8-sig")


def find_cached_nav(cache_path: Path, fund_code: str) -> dict[str, Any] | None:
    """Return latest cached NAV row for fund_code."""

    cache = load_fund_nav_cache(cache_path)
    if cache.empty:
        return None
    code = normalize_fund_code(fund_code)
    matched = cache.loc[cache["fund_code"].astype(str).map(normalize_fund_code) == code].copy()
    if matched.empty:
        return None
    matched["_sort_date"] = pd.to_datetime(matched["nav_date"], errors="coerce")
    matched = matched.sort_values("_sort_date", ascending=False)
    row = matched.iloc[0].drop(labels=["_sort_date"], errors="ignore").to_dict()
    nav_date = pd.to_datetime(row.get("nav_date", ""), errors="coerce")
    row["data_quality"] = "stale_cache" if pd.isna(nav_date) or nav_date.date() < datetime.now().date() - timedelta(days=7) else "cache"
    row["data_source"] = row.get("data_source") or "cache"
    row["error_message"] = "缓存可用"
    return ensure_nav_columns(row)


def missing_nav_row(fund_code: str, fund_name: str, data_quality: str, error_message: str) -> dict[str, Any]:
    """Build one stable missing NAV row with short user-facing error."""

    return {
        "fund_code": normalize_fund_code(fund_code),
        "fund_name": fund_name,
        "nav_date": "",
        "nav": pd.NA,
        "daily_return": pd.NA,
        "purchase_status": "基金代码缺失" if data_quality == "missing_code" else "未知",
        "redemption_status": "未知",
        "data_source": "missing_nav",
        "data_quality": data_quality,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_message": error_message,
    }


def ensure_nav_columns(row: dict[str, Any]) -> dict[str, Any]:
    """Ensure a NAV dict contains all standard columns."""

    return {column: row.get(column, "") for column in NAV_COLUMNS}


def load_fund_code_aliases(path: Path | None) -> dict[str, str]:
    """Load fund alias to fund code mapping."""

    if not path or not path.exists():
        return {}
    data = load_yaml(path)
    return {str(key): str(value or "") for key, value in data.get("fund_code_aliases", {}).items()}


def resolve_fund_code(fund: dict[str, Any], aliases: dict[str, str]) -> str:
    """Resolve fund code from portfolio first, then alias config."""

    direct = normalize_fund_code(fund.get("fund_code", ""))
    if direct:
        return direct
    name = normalize_fund_name(fund.get("fund_name", ""))
    for alias, code in aliases.items():
        if normalize_fund_name(alias) and normalize_fund_name(alias) in name:
            return normalize_fund_code(code)
    return ""


def normalize_fund_code(value: Any) -> str:
    """Normalize fund code; unknown or empty returns empty string."""

    text = str(value or "").strip()
    if not text or text.lower() in {"unknown", "nan", "none", "null"}:
        return ""
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits else ""


def normalize_fund_name(value: Any) -> str:
    """Normalize fund name for alias matching."""

    text = str(value or "").strip().lower()
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\((qdii|lof)\)", "", text)
    text = re.sub(r"[ac]类?$", "", text)
    return text


def parse_number(value: Any):
    """Parse numeric NAV value."""

    try:
        text = str(value).replace(",", "").strip()
        if not text or text.lower() in {"nan", "none", "--"}:
            return pd.NA
        return float(text)
    except (TypeError, ValueError):
        return pd.NA


def parse_percent(value: Any):
    """Parse percent into decimal, e.g. 0.52% -> 0.0052."""

    try:
        raw_text = str(value)
        text = raw_text.replace("%", "").strip()
        if not text or text.lower() in {"nan", "none", "--"}:
            return pd.NA
        number = float(text)
        if "%" in raw_text or abs(number) > 0.05:
            return number / 100
        return number
    except (TypeError, ValueError):
        return pd.NA


def first_present(record: dict[str, Any], keys: list[str]) -> Any:
    """Return first non-empty value from record."""

    for key in keys:
        if key in record and not is_blank(record[key]):
            return record[key]
    return ""


def is_blank(value: Any) -> bool:
    """Check blank-ish values."""

    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except TypeError:
        pass
    return str(value).strip() == ""


def safe_text(value: Any) -> str:
    """Convert display text safely."""

    if is_blank(value):
        return ""
    return str(value).strip()


def normalize_date_text(value: Any) -> str:
    """Normalize date value into YYYY-MM-DD text when possible."""

    if is_blank(value):
        return ""
    date_value = pd.to_datetime(value, errors="coerce")
    if pd.isna(date_value):
        return str(value).strip()
    return date_value.strftime("%Y-%m-%d")


def clean_html(value: str) -> str:
    """Remove tags from one HTML cell."""

    text = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", text).strip()


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML safely."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
