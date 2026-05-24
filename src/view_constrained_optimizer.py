"""Three-stage view-constrained optimizer for offensive QQQ/SMH portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import json

import numpy as np
import pandas as pd


START_DATE = "2006-01-01"
END_DATE = "2025-12-31"
REPORT_DIR = Path("reports")
SUMMARY_PATH = REPORT_DIR / "view_constrained_optimizer_summary.md"
TOP20_PATH = REPORT_DIR / "view_constrained_optimizer_top10.csv"
BUCKET_PATH = REPORT_DIR / "view_constrained_optimizer_by_smh_bucket.csv"
SCENARIO_PATH = REPORT_DIR / "view_constrained_optimizer_scenarios.csv"

PERIODS = {
    "train_2006_2015": ("2006-01-01", "2015-12-31"),
    "validation_2016_2020": ("2016-01-01", "2020-12-31"),
    "out_of_sample_2021_2025": ("2021-01-01", "2025-12-31"),
    "full_2006_2025": ("2006-01-01", "2025-12-31"),
}
SMH_BUCKETS = [
    ("SMH_35_40", 0.35, 0.40),
    ("SMH_40_50", 0.40, 0.50),
    ("SMH_50_60", 0.50, 0.60),
    ("SMH_60_65", 0.60, 0.65),
]
TACTICAL_OPTIONS = [
    {"option": "QQQ50_SMH40_GLD10", "QQQ": 0.50, "SMH": 0.40, "GLD": 0.10},
    {"option": "QQQ40_SMH50_GLD10", "QQQ": 0.40, "SMH": 0.50, "GLD": 0.10},
    {"option": "QQQ30_SMH60_GLD10", "QQQ": 0.30, "SMH": 0.60, "GLD": 0.10},
    {"option": "QQQ20_SMH75_GLD05", "QQQ": 0.20, "SMH": 0.75, "GLD": 0.05},
    {"option": "QQQ00_SMH100_GLD00", "QQQ": 0.00, "SMH": 1.00, "GLD": 0.00},
]


@dataclass(frozen=True)
class BaseWeights:
    qqq: float
    smh: float
    gld: float
    cash: float


@dataclass
class State:
    qqq_units: float = 0.0
    smh_units: float = 0.0
    gld_units: float = 0.0
    cash: float = 0.0
    invested: float = 0.0
    cooldown: int = 0


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    prices, error = download_prices()
    if error:
        write_error(error)
        print(f"Optimizer failed: {error}")
        return

    prices = prices.loc[pd.Timestamp(START_DATE) : pd.Timestamp(END_DATE)].dropna()
    indicators = build_indicators(prices)
    qqq_ref = {period: qqq_metrics(prices.loc[start:end], period) for period, (start, end) in PERIODS.items()}

    stage1 = run_stage1(prices, indicators, qqq_ref["full_2006_2025"])
    top20 = stage1.head(20).copy()
    buckets = bucket_summary(stage1)

    stage2 = run_stage2(prices, indicators, qqq_ref["full_2006_2025"], top20.head(5))
    final_top3 = stage2.head(3).copy()
    validation = run_final_validation(prices, indicators, qqq_ref, final_top3)
    scenarios = run_scenarios(final_top3, prices)

    top20.to_csv(TOP20_PATH, index=False, encoding="utf-8-sig")
    buckets.to_csv(BUCKET_PATH, index=False, encoding="utf-8-sig")
    scenarios.to_csv(SCENARIO_PATH, index=False, encoding="utf-8-sig")
    write_summary(prices, top20, buckets, stage2, final_top3, validation, scenarios, qqq_ref)

    print(f"Optimizer completed. Summary: {SUMMARY_PATH}")
    print(f"Top 20 base combinations: {TOP20_PATH}")
    print(f"SMH buckets: {BUCKET_PATH}")
    print(f"Scenarios: {SCENARIO_PATH}")


def download_prices() -> tuple[pd.DataFrame, str | None]:
    period1 = int(datetime(2006, 1, 1, tzinfo=timezone.utc).timestamp())
    period2 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    series = {}
    for symbol in ["QQQ", "SMH", "GLD"]:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
        )
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            result = payload["chart"]["result"][0]
            timestamps = result["timestamp"]
            adjclose = result["indicators"]["adjclose"][0]["adjclose"]
            index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
            series[symbol] = pd.Series(adjclose, index=index, name=symbol, dtype="float64")
        except Exception as exc:
            return pd.DataFrame(), f"{symbol} download failed: {exc}"
    return pd.concat(series.values(), axis=1).sort_index()[["QQQ", "SMH", "GLD"]], None


def build_indicators(prices: pd.DataFrame) -> dict[str, pd.DataFrame]:
    rsi = prices.apply(calc_rsi)
    ma60 = prices.rolling(60, min_periods=60).mean()
    drawdown = prices / prices.rolling(252, min_periods=1).max() - 1
    return {"rsi": rsi, "ma60": ma60, "drawdown": drawdown}


def calc_rsi(price: pd.Series, window: int = 14) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window, min_periods=window).mean()
    avg_loss = loss.rolling(window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - 100 / (1 + rs)


def generate_base_weights() -> list[BaseWeights]:
    out = []
    grid = [value / 100 for value in range(0, 101, 5)]
    for qqq in grid:
        for smh in grid:
            for gld in grid:
                cash = round(1 - qqq - smh - gld, 10)
                if 0.25 <= qqq <= 0.50 and 0.35 <= smh <= 0.65 and 0 <= gld <= 0.10 and 0.05 <= cash <= 0.20:
                    if qqq + smh >= 0.80 and gld + cash <= 0.25:
                        out.append(BaseWeights(qqq, smh, gld, cash))
    return out


def run_stage1(prices: pd.DataFrame, indicators: dict[str, pd.DataFrame], qqq_full: dict) -> pd.DataFrame:
    rows = []
    for idx, weights in enumerate(generate_base_weights(), start=1):
        daily = simulate(prices, indicators, weights, tactical=None)
        row = metrics(daily, "full_2006_2025")
        row.update(weight_row(idx, weights))
        add_relative(row, qqq_full)
        rows.append(row)
    return score(pd.DataFrame(rows)).sort_values(["balanced_score", "annualized_return"], ascending=False)


def run_stage2(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    qqq_full: dict,
    top5: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, base in top5.iterrows():
        weights = BaseWeights(base.qqq_weight, base.smh_weight, base.gld_weight, base.cash_weight)
        for option in TACTICAL_OPTIONS:
            daily = simulate(prices, indicators, weights, tactical=option)
            row = metrics(daily, "full_2006_2025")
            row.update(weight_row(int(base.candidate_id), weights))
            row.update(
                {
                    "tactical_option": option["option"],
                    "tactical_qqq_weight": option["QQQ"],
                    "tactical_smh_weight": option["SMH"],
                    "tactical_gld_weight": option["GLD"],
                }
            )
            add_relative(row, qqq_full)
            rows.append(row)
    return score(pd.DataFrame(rows)).sort_values(["balanced_score", "annualized_return"], ascending=False)


def run_final_validation(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    qqq_ref: dict[str, dict],
    top3: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for rank, candidate in enumerate(top3.itertuples(index=False), start=1):
        weights = BaseWeights(candidate.qqq_weight, candidate.smh_weight, candidate.gld_weight, candidate.cash_weight)
        option = {
            "option": candidate.tactical_option,
            "QQQ": candidate.tactical_qqq_weight,
            "SMH": candidate.tactical_smh_weight,
            "GLD": candidate.tactical_gld_weight,
        }
        for period, (start, end) in PERIODS.items():
            period_prices = prices.loc[start:end]
            period_indicators = {name: table.loc[period_prices.index] for name, table in indicators.items()}
            daily = simulate(period_prices, period_indicators, weights, tactical=option)
            row = metrics(daily, period)
            row.update(weight_row(candidate.candidate_id, weights))
            row["final_rank"] = rank
            row["tactical_option"] = candidate.tactical_option
            add_relative(row, qqq_ref[period])
            rows.append(row)
    return pd.DataFrame(rows)


def simulate(
    prices: pd.DataFrame,
    indicators: dict[str, pd.DataFrame],
    weights: BaseWeights,
    tactical: dict[str, float] | None,
) -> pd.DataFrame:
    state = State()
    rows = []
    quarter_usage: dict[str, float] = {}
    quarter_basis: dict[str, float] = {}
    tactical_uses = 0
    for date, price in prices.iterrows():
        before = value(state, price)
        prev = rows[-1]["portfolio_value"] if rows else 0.0
        market_return = before / prev - 1 if prev > 0 else 0.0
        if state.cooldown > 0:
            state.cooldown -= 1

        state.invested += 60
        state.qqq_units += 60 * weights.qqq / price.QQQ
        state.smh_units += 60 * weights.smh / price.SMH
        state.gld_units += 60 * weights.gld / price.GLD
        state.cash += 60 * weights.cash

        level = 0
        tactical_amount = 0.0
        if tactical is not None:
            quarter = quarter_key(date)
            quarter_basis.setdefault(quarter, state.cash)
            tactical_amount, level = tactical_amount_for(date, price, indicators, state, quarter_usage, quarter_basis)
            if tactical_amount > 0:
                state.qqq_units += tactical_amount * tactical["QQQ"] / price.QQQ
                state.smh_units += tactical_amount * tactical["SMH"] / price.SMH
                state.gld_units += tactical_amount * tactical["GLD"] / price.GLD
                state.cash -= tactical_amount
                state.cooldown = 20
                quarter_usage[quarter] = quarter_usage.get(quarter, 0.0) + tactical_amount
                tactical_uses += 1

        rows.append(
            {
                "date": date,
                "portfolio_value": value(state, price),
                "invested": state.invested,
                "market_return": market_return,
                "tactical_uses": tactical_uses,
                "tactical_level": level,
            }
        )
    return pd.DataFrame(rows).set_index("date")


def tactical_amount_for(
    date: pd.Timestamp,
    price: pd.Series,
    indicators: dict[str, pd.DataFrame],
    state: State,
    quarter_usage: dict[str, float],
    quarter_basis: dict[str, float],
) -> tuple[float, int]:
    level = opportunity_level(date, price, indicators)
    if level < 2 or state.cash <= 0 or state.cooldown > 0:
        return 0.0, level
    if rsi_hot(date, indicators) or risk_off(date, price, indicators):
        return 0.0, level
    quarter = quarter_key(date)
    level_pct = {2: 0.10, 3: 0.20, 4: 0.30}[level]
    usable = max(0.0, state.cash * 0.60)
    quarter_left = max(0.0, quarter_basis.get(quarter, state.cash) * 0.40 - quarter_usage.get(quarter, 0.0))
    return min(state.cash * level_pct, usable, quarter_left), level


def opportunity_level(date: pd.Timestamp, price: pd.Series, indicators: dict[str, pd.DataFrame]) -> int:
    checks = []
    for symbol in ["QQQ", "SMH"]:
        rsi = indicators["rsi"].at[date, symbol]
        ma = indicators["ma60"].at[date, symbol]
        dd = indicators["drawdown"].at[date, symbol]
        if pd.isna(rsi) or pd.isna(ma) or pd.isna(dd):
            continue
        checks.append((float(rsi), float(dd), float(price[symbol]) >= float(ma), float(price[symbol]) >= float(ma) * 0.97))
    if any(-0.25 <= dd <= -0.15 and 25 <= rsi <= 45 for rsi, dd, _, _ in checks):
        return 4
    if any(-0.15 <= dd <= -0.10 and 35 <= rsi <= 50 and near for rsi, dd, _, near in checks):
        return 3
    if any(-0.10 <= dd <= -0.05 and 45 <= rsi <= 60 and above for rsi, dd, above, _ in checks):
        return 2
    return 0


def rsi_hot(date: pd.Timestamp, indicators: dict[str, pd.DataFrame]) -> bool:
    return any(not pd.isna(indicators["rsi"].at[date, symbol]) and indicators["rsi"].at[date, symbol] > 70 for symbol in ["QQQ", "SMH"])


def risk_off(date: pd.Timestamp, price: pd.Series, indicators: dict[str, pd.DataFrame]) -> bool:
    below = []
    for symbol in ["QQQ", "SMH"]:
        ma = indicators["ma60"].at[date, symbol]
        below.append(not pd.isna(ma) and float(price[symbol]) < float(ma))
    qqq_dd = indicators["drawdown"].at[date, "QQQ"]
    smh_dd = indicators["drawdown"].at[date, "SMH"]
    severe = not pd.isna(qqq_dd) and not pd.isna(smh_dd) and qqq_dd <= -0.20 and smh_dd <= -0.20
    return all(below) or severe


def qqq_metrics(prices: pd.DataFrame, period: str) -> dict:
    state = State()
    rows = []
    for date, price in prices.iterrows():
        before = state.qqq_units * price.QQQ
        prev = rows[-1]["portfolio_value"] if rows else 0.0
        market_return = before / prev - 1 if prev > 0 else 0.0
        state.invested += 60
        state.qqq_units += 60 / price.QQQ
        rows.append({"date": date, "portfolio_value": state.qqq_units * price.QQQ, "invested": state.invested, "market_return": market_return, "tactical_uses": 0})
    return metrics(pd.DataFrame(rows).set_index("date"), period)


def metrics(daily: pd.DataFrame, period: str) -> dict:
    invested = float(daily.invested.iloc[-1])
    ending = float(daily.portfolio_value.iloc[-1])
    years = max((daily.index[-1] - daily.index[0]).days / 365.25, 1 / 365.25)
    annualized = (ending / invested) ** (1 / years) - 1
    drawdown = daily.portfolio_value / daily.portfolio_value.cummax() - 1
    max_dd = float(drawdown.min())
    returns = daily.market_return.iloc[1:].dropna()
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if len(returns) and returns.std() != 0 else 0.0
    return {"period": period, "total_invested": round(invested, 2), "ending_value": round(ending, 2), "annualized_return": round(annualized, 6), "max_drawdown": round(max_dd, 6), "sharpe_ratio": round(sharpe, 6), "calmar_ratio": round(annualized / abs(max_dd), 6) if max_dd < 0 else 0.0, "tactical_uses": int(daily.tactical_uses.iloc[-1])}


def score(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["return_rank"] = out.annualized_return.rank(pct=True)
    out["sharpe_rank"] = out.sharpe_ratio.rank(pct=True)
    out["calmar_rank"] = out.calmar_ratio.rank(pct=True)
    out["drawdown_rank"] = (-out.drawdown_worsening_vs_qqq).rank(pct=True)
    out["balanced_score"] = 0.30 * out.return_rank + 0.25 * out.sharpe_rank + 0.20 * out.calmar_rank + 0.25 * out.drawdown_rank - 0.35 * out.drawdown_worsening_vs_qqq.clip(lower=0)
    out["worth_extra_risk"] = (out.excess_annualized_return_vs_qqq > 0.01) & (out.drawdown_worsening_vs_qqq <= 0.03) & (out.sharpe_excess_vs_qqq >= -0.03)
    return out


def add_relative(row: dict, qqq: dict) -> None:
    row["excess_annualized_return_vs_qqq"] = round(row["annualized_return"] - qqq["annualized_return"], 6)
    row["drawdown_worsening_vs_qqq"] = round(abs(row["max_drawdown"]) - abs(qqq["max_drawdown"]), 6)
    row["sharpe_excess_vs_qqq"] = round(row["sharpe_ratio"] - qqq["sharpe_ratio"], 6)


def weight_row(candidate_id: int, weights: BaseWeights) -> dict:
    return {"candidate_id": int(candidate_id), "qqq_weight": weights.qqq, "smh_weight": weights.smh, "gld_weight": weights.gld, "cash_weight": weights.cash, "smh_bucket": smh_bucket(weights.smh)}


def bucket_summary(stage1: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, _, _ in SMH_BUCKETS:
        bucket = stage1[stage1.smh_bucket == name]
        if bucket.empty:
            continue
        best = bucket.sort_values(["balanced_score", "annualized_return"], ascending=False).iloc[0]
        rows.append({key: best[key] for key in ["smh_bucket", "candidate_id", "qqq_weight", "smh_weight", "gld_weight", "cash_weight", "annualized_return", "max_drawdown", "sharpe_ratio", "calmar_ratio", "excess_annualized_return_vs_qqq", "drawdown_worsening_vs_qqq", "worth_extra_risk", "balanced_score"]})
    return pd.DataFrame(rows)


def run_scenarios(final_top3: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change().dropna()
    hist_mu = returns.mean() * 252
    cov = returns.cov() * 252
    rows = []
    for _, row in final_top3.iterrows():
        w = np.array([row.qqq_weight, row.smh_weight, row.gld_weight], dtype=float)
        cash = float(row.cash_weight)
        for scenario, mu, shock in scenarios(hist_mu):
            expected = float(w @ np.array([mu["QQQ"], mu["SMH"], mu["GLD"]]) + cash * mu["Cash"])
            vol = float(np.sqrt(w @ cov.loc[["QQQ", "SMH", "GLD"], ["QQQ", "SMH", "GLD"]].values @ w))
            stress = float(row.qqq_weight * shock["QQQ"] + row.smh_weight * shock["SMH"] + row.gld_weight * shock["GLD"] + cash * shock["Cash"])
            rows.append({"scenario": scenario, "candidate_id": int(row.candidate_id), "qqq_weight": row.qqq_weight, "smh_weight": row.smh_weight, "gld_weight": row.gld_weight, "cash_weight": cash, "tactical_option": row.tactical_option, "expected_annual_return": round(expected, 6), "estimated_volatility": round(vol, 6), "stress_drawdown_estimate": round(stress, 6), "scenario_sharpe_proxy": round(expected / vol, 6) if vol else 0.0})
    return pd.DataFrame(rows)


def scenarios(hist_mu: pd.Series) -> list[tuple[str, dict, dict]]:
    qqq = max(float(hist_mu.QQQ) * 0.75, 0.06)
    gld = max(float(hist_mu.GLD) * 0.60, 0.02)
    return [
        ("Scenario A: AI mainline remains strong", {"QQQ": qqq, "SMH": qqq + 0.075, "GLD": gld, "Cash": 0.02}, {"QQQ": -0.18, "SMH": -0.24, "GLD": 0.03, "Cash": 0.0}),
        ("Scenario B: AI mainline cools", {"QQQ": qqq, "SMH": qqq - 0.05, "GLD": gld, "Cash": 0.02}, {"QQQ": -0.20, "SMH": -0.32, "GLD": 0.04, "Cash": 0.0}),
        ("Scenario C: high-rate valuation compression", {"QQQ": -0.02, "SMH": -0.06, "GLD": 0.06, "Cash": 0.025}, {"QQQ": -0.30, "SMH": -0.42, "GLD": 0.08, "Cash": 0.0}),
    ]


def write_summary(prices: pd.DataFrame, top20: pd.DataFrame, buckets: pd.DataFrame, stage2: pd.DataFrame, final_top3: pd.DataFrame, validation: pd.DataFrame, scenario_df: pd.DataFrame, qqq_ref: dict) -> None:
    best = final_top3.iloc[0]
    control = final_top3.sort_values(["drawdown_worsening_vs_qqq", "balanced_score"], ascending=[True, False]).iloc[0]
    semi = final_top3[final_top3.smh_weight >= 0.50]
    semi_pick = semi.iloc[0] if not semi.empty else best
    valid_oos = validation[(validation.final_rank == 1) & (validation.period == "out_of_sample_2021_2025")].iloc[0]
    verdict = "值得复杂化" if bool(best.worth_extra_risk) and valid_oos.excess_annualized_return_vs_qqq > 0 and valid_oos.drawdown_worsening_vs_qqq <= 0.05 else "不建议为了复杂度本身复杂化"
    content = f"""# View-Constrained Optimizer

## 三阶段流程

- 第一阶段：只搜索 QQQ / SMH / GLD / Cash 基础权重，步长 5%，共 {len(generate_base_weights())} 个候选。
- 第二阶段：只拿第一阶段 Top 5，测试 5 种固定机动资金分配。
- 第三阶段：只对最终 Top 3 做 2006-2015、2016-2020、2021-2025、2006-2025 分段验证。
- 数据区间：{prices.index[0].date().isoformat()} 至 {prices.index[-1].date().isoformat()}；数据源为 Yahoo Chart API 复权后收盘价。
- 历史数据只用于压力测试和风险校准，不用于证明未来一定有效。

## QQQ 基准

{markdown(format_reference(qqq_ref))}

## 第一阶段 Top 20 基础组合

{markdown(format_table(top20.head(20)))}

## 按 SMH 权重分组

{markdown(format_table(buckets))}

## 第二阶段 Top 5 基础组合 x 机动资金分配

{markdown(format_table(stage2.head(10)))}

## 第三阶段最终 Top 3 分段验证

{markdown(format_table(validation))}

## 前瞻情景测试

{markdown(format_table(scenario_df))}

## 最终建议

- 如果坚持看好半导体：建议 QQQ {semi_pick.qqq_weight:.0%} / SMH {semi_pick.smh_weight:.0%} / GLD {semi_pick.gld_weight:.0%} / Cash {semi_pick.cash_weight:.0%}，机动资金使用 `{semi_pick.tactical_option}`。
- 如果想控制回撤：建议 QQQ {control.qqq_weight:.0%} / SMH {control.smh_weight:.0%} / GLD {control.gld_weight:.0%} / Cash {control.cash_weight:.0%}，机动资金使用 `{control.tactical_option}`。
- 是否值得复杂化：{verdict}。如果执行纪律、数据稳定性或再平衡成本不可控，直接定投 QQQ 或简化为 QQQ+SMH 会更稳。

历史回测不代表未来收益。本报告仅用于观点约束下的风险收益校准，不构成投资建议。
"""
    SUMMARY_PATH.write_text(content, encoding="utf-8")


def format_reference(qqq_ref: dict) -> pd.DataFrame:
    return pd.DataFrame([{"period": p, "annualized_return": m["annualized_return"], "max_drawdown": m["max_drawdown"], "sharpe_ratio": m["sharpe_ratio"], "calmar_ratio": m["calmar_ratio"]} for p, m in qqq_ref.items()])


def format_table(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in frame.columns if not c.endswith("_rank")]
    out = frame[keep].copy()
    pct_cols = [c for c in out.columns if c.endswith("_weight") or c in {"annualized_return", "max_drawdown", "excess_annualized_return_vs_qqq", "drawdown_worsening_vs_qqq", "expected_annual_return", "estimated_volatility", "stress_drawdown_estimate"}]
    for col in pct_cols:
        out[col] = out[col].map(lambda v: f"{float(v):.2%}" if pd.notna(v) else "")
    for col in ["sharpe_ratio", "calmar_ratio", "balanced_score", "scenario_sharpe_proxy"]:
        if col in out.columns:
            out[col] = out[col].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
    return out


def markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    lines = ["| " + " | ".join(map(str, frame.columns)) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("\n", " ") for c in frame.columns) + " |")
    return "\n".join(lines)


def value(state: State, price: pd.Series) -> float:
    return float(state.qqq_units * price.QQQ + state.smh_units * price.SMH + state.gld_units * price.GLD + state.cash)


def smh_bucket(weight: float) -> str:
    for name, lo, hi in SMH_BUCKETS:
        if lo <= weight <= hi:
            return name
    return "outside"


def quarter_key(date: pd.Timestamp) -> str:
    return f"{date.year}Q{((date.month - 1) // 3) + 1}"


def write_error(message: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"error": message}]).to_csv(TOP20_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame([{"error": message}]).to_csv(BUCKET_PATH, index=False, encoding="utf-8-sig")
    pd.DataFrame([{"error": message}]).to_csv(SCENARIO_PATH, index=False, encoding="utf-8-sig")
    SUMMARY_PATH.write_text(f"# View-Constrained Optimizer Failed\n\n错误原因：{message}\n\n历史回测不代表未来收益。\n", encoding="utf-8")


if __name__ == "__main__":
    main()
