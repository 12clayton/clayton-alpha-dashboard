"""Research-only, forward-looking-signal multi-alpha strategy lab.

Inspired by *A Regime-Aware Multi-Alpha Trading Framework* (Math 585 team report).
Does NOT implement or price options contracts, and MUST NOT be described as a
reproduction of the source QuantConnect strategy's performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Optional
import warnings

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, norm

SYMBOLS = ("SPY", "QQQ", "SHV", "GDX", "GLD")


@dataclass(frozen=True)
class StrategyConfig:
    copula_window: int = 252
    entry_low: float = 0.05
    entry_high: float = 0.95
    exit_low: float = 0.40
    exit_high: float = 0.60
    break_tau: float = 0.20
    pair_leg_weight: float = 0.50  # Source report: +/-0.5 for each pair leg
    momentum_weight: float = 0.75  # Source report: up to 75% in QQQ or SHV
    gross_cap: float = 1.0  # safer-than-paper default; 1.75 is report's uncapped combination
    charge_bps: float = 10.0  # commission + slippage per unit of traded notional
    short_borrow_bps_annual: float = 50.0  # illustrative financing assumption
    hmm_training_days: int = 756
    hmm_refit_days: int = 63
    hmm_confirm_days: int = 2
    regime_method: str = "hmm"  # or "volatility"


def validate_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept long-form Date,Symbol,Open,High,Low,Close; one row per date/symbol.

    No forward filling of trading prices. All five symbols must be present.
    Same-day rows are aligned by intersection only.
    """
    f = frame.copy()
    f.columns = [str(c).strip().lower() for c in f.columns]
    needed = {"date", "symbol", "high", "low", "close"}
    missing = needed - set(f.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    f["date"] = pd.to_datetime(f["date"], errors="coerce").dt.tz_localize(None)
    f["symbol"] = f["symbol"].astype(str).str.upper().str.strip()
    for col in ("high", "low", "close"):
        f[col] = pd.to_numeric(f[col], errors="coerce")
    f = f.dropna(subset=["date", "high", "low", "close"])
    f = f[f.symbol.isin(SYMBOLS)]
    if not set(SYMBOLS).issubset(set(f.symbol)):
        raise ValueError(f"CSV requires {', '.join(SYMBOLS)}. Found: {sorted(f.symbol.unique())}")
    if f.duplicated(["date", "symbol"]).any():
        raise ValueError("Duplicate (date, symbol) rows in price CSV")
    if not np.isfinite(f[["high", "low", "close"]].to_numpy()).all():
        raise ValueError("Prices must be finite")
    tolerance = f.close.abs() * 1e-8  # adjusted OHLC can differ by floating-point roundoff
    if ((f.high + tolerance < f.close) | (f.low - tolerance > f.close) | (f.high + tolerance < f.low)).any():
        raise ValueError("Invalid OHLC ordering")
    if (f[["high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be > 0")
    wide = f.set_index(["date", "symbol"])[["high", "low", "close"]].unstack("symbol")
    columns = pd.MultiIndex.from_product([["high", "low", "close"], SYMBOLS])
    wide = wide.reindex(columns=columns).dropna().sort_index()
    if len(wide) < 300:
        raise ValueError("At least 300 common trading days are required (800+ recommended)")
    if not wide.index.is_unique or not wide.index.is_monotonic_increasing:
        raise ValueError("Price index must be ordered and unique")
    return wide


def yahoo_download(start: str, end: str) -> pd.DataFrame:
    """Fetch adjusted OHLC for the research lab; requires network and yfinance."""
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError("Install yfinance or upload an OHLC CSV") from e
    prices = yf.download(
        list(SYMBOLS), start=start, end=end, group_by="ticker",
        auto_adjust=True, progress=False, threads=False,
    )
    if prices.empty:
        raise ValueError("Yahoo Finance returned no data. Upload the source CSV instead.")
    frames = []
    for sym in SYMBOLS:
        try:
            sub = prices[sym]
            block = sub[["High", "Low", "Close"]].copy()
        except (KeyError, TypeError) as e:
            raise ValueError(f"Yahoo response missing {sym}") from e
        block.columns = ["high", "low", "close"]
        block["symbol"] = sym
        block["date"] = block.index
        frames.append(block.reset_index(drop=True))
    return validate_ohlc(pd.concat(frames, ignore_index=True))


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's ADX; daily price information only."""
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.), index=high.index)
    tr = pd.concat([(high-low), (high-close.shift(1)).abs(), (low-close.shift(1)).abs()], axis=1).max(axis=1)
    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    denom = plus_di + minus_di
    dx = 100 * (plus_di-minus_di).abs() / denom.replace(0, np.nan)
    return dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean().fillna(0)


def copula_mispricing(closes: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """Estimate Clayton copula MI using *past* window for tau, current bar for MI.

    Returns MI = conditional CDF P(GDX return <= observed | GLD return).
    Signals must be traded on the FOLLOWING session; no same-bar fills.
    """
    returns = np.log(closes[["GDX", "GLD"]] / closes[["GDX", "GLD"]].shift(1))
    out = pd.DataFrame(index=closes.index, columns=["mi", "kendall_tau", "theta"], dtype=float)
    for i in range(window + 1, len(returns)):
        past = returns.iloc[i-window:i].dropna()
        if len(past) < window:
            continue
        tau = kendalltau(past["GDX"], past["GLD"]).statistic
        if not np.isfinite(tau) or tau <= 0 or tau >= 0.995:
            continue
        x, y = returns.iloc[i]["GDX"], returns.iloc[i]["GLD"]
        if not np.isfinite(x) or not np.isfinite(y):
            continue
        # Empirical distributions fitted on historical data only.
        u = (float((past["GDX"] <= x).sum()) + .5) / (window + 1)
        v = (float((past["GLD"] <= y).sum()) + .5) / (window + 1)
        u, v = np.clip([u, v], 1e-5, 1 - 1e-5)
        theta = 2.0 * tau / (1.0 - tau)
        inside = u**(-theta) + v**(-theta) - 1
        mi = v**(-theta-1) * inside**(-1.0/theta-1.0)
        out.iloc[i] = [float(np.clip(mi, 0, 1)), float(tau), float(theta)]
    return out


def _fit_hmm(training_returns: pd.Series) -> Optional[Dict]:
    """Fit two-state Markov-switching Gaussian on historical SPY daily returns.

    Filtering afterward is causal. Does not use full-backtest smoothed probabilities.
    """
    try:
        from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
        y = training_returns.dropna().astype(float) * 100.0
        if len(y) < 250 or y.std() < 0.01:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = MarkovRegression(y, k_regimes=2, trend="c", switching_variance=True).fit(
                maxiter=120, disp=False, em_iter=10, search_reps=0,
            )
        p = res.params
        var = np.array([float(p["sigma2[0]"]), float(p["sigma2[1]"])])
        means = np.array([float(p["const[0]"]), float(p["const[1]"])])
        if not np.all(np.isfinite(var)) or min(var) <= 0:
            return None
        p00 = float(p["p[0->0]"])
        p10 = float(p["p[1->0]"])
        transition = np.array([[p00, 1-p00], [p10, 1-p10]])
        if not np.isfinite(transition).all():
            return None
        posterior = res.filtered_marginal_probabilities.iloc[-1].to_numpy(dtype=float)
        posterior = np.clip(posterior, 1e-12, 1)
        posterior /= posterior.sum()
        return {"mean": means, "sd": np.sqrt(var), "transition": transition,
                "posterior": posterior, "high": int(np.argmax(var))}
    except Exception:
        return None


def regime_probabilities(spy_returns: pd.Series, cfg: StrategyConfig) -> pd.DataFrame:
    """Rolling HMM with causal forward filter, 2-day confirmation; volatility fallback labelled.

    Model is recalibrated each cfg.hmm_refit_days using only data before day t.
    A per-day posterior update incorporates t's close and can only act t+1.
    """
    n = len(spy_returns)
    ans = pd.DataFrame(index=spy_returns.index, columns=["crisis_probability", "high_vol", "regime_source"])
    ret = spy_returns.astype(float)
    realized = ret.rolling(21, min_periods=15).std() * np.sqrt(252)
    threshold = realized.shift(1).rolling(252, min_periods=126).quantile(.95)
    fallback = (realized > threshold).fillna(False)
    model = None
    last_fit = -10**9
    active = False
    hi_streak = low_streak = 0
    for i in range(n):
        t = ret.iloc[i]
        prob = np.nan
        source = "volatility_baseline"
        if cfg.regime_method == "hmm" and i >= cfg.hmm_training_days:
            if i - last_fit >= cfg.hmm_refit_days:
                history = ret.iloc[i-cfg.hmm_training_days:i]
                model = _fit_hmm(history)
                last_fit = i
            if model is not None and np.isfinite(t):
                prior = model["posterior"] @ model["transition"]
                likelihood = norm.pdf(t * 100, loc=model["mean"], scale=model["sd"])
                posterior = np.maximum(prior * likelihood, 1e-250)
                posterior /= posterior.sum()
                model["posterior"] = posterior
                prob = float(posterior[model["high"]])
                source = "hmm_filtered"
        if not np.isfinite(prob):
            prob = float(fallback.iloc[i])
        new_high = prob > .5
        if new_high:
            hi_streak += 1
            low_streak = 0
        else:
            low_streak += 1
            hi_streak = 0
        if not active and hi_streak >= cfg.hmm_confirm_days:
            active = True
        elif active and low_streak >= cfg.hmm_confirm_days:
            active = False
        ans.iloc[i] = [prob, active, source]
    ans["crisis_probability"] = pd.to_numeric(ans["crisis_probability"])
    ans["high_vol"] = ans["high_vol"].astype(bool)
    return ans


def calculate_risk(returns: pd.Series, window: int = 252) -> pd.DataFrame:
    """Historical 1-day VaR/CVaR of strategy return distribution (loss-positive)."""
    v = pd.DataFrame(index=returns.index)
    minobs = max(60, window // 2)
    for confidence in (.95, .99):
        tail_q = 1 - confidence
        var = returns.rolling(window, min_periods=minobs).quantile(tail_q)
        v[f"var{int(confidence * 100)}"] = (-var).clip(lower=0)
        cvar = []
        for i in range(len(returns)):
            x = returns.iloc[max(0, i-window+1):i+1].dropna()
            if len(x) < minobs:
                cvar.append(np.nan)
            else:
                q = x.quantile(tail_q)
                cvar.append(max(0.0, -float(x[x <= q].mean())))
        v[f"cvar{int(confidence * 100)}"] = cvar
    return v


def _summarize(net: pd.Series, equity: pd.Series, position: pd.DataFrame, cfg: StrategyConfig) -> Dict:
    n = len(net.dropna())
    if n < 2:
        return {"days": n}
    vol = float(net.std(ddof=1) * np.sqrt(252))
    cagr = float((equity.iloc[-1] / 100000.0)**(252/max(n, 1)) - 1)
    dd = equity/equity.cummax().clip(lower=100000.0)-1
    turn = position.diff().fillna(position).abs().sum(axis=1)
    return {
        "days": n,
        "cagr": cagr,
        "sharpe": float(net.mean()*252/vol) if vol > 0 else np.nan,
        "volatility": vol,
        "max_drawdown": float(dd.min()),
        "ending_equity": float(equity.iloc[-1]),
        "roundtrip_cost_bps": cfg.charge_bps,
        "annualized_turnover": float(turn.sum() * 252/max(n, 1)),
        "pair_entry_events": int((position["GDX"].abs().diff().fillna(0) > 1e-6).sum()),
    }


def backtest(ohlc: pd.DataFrame, cfg: StrategyConfig, start: Optional[str] = None) -> Dict:
    """Stocks/ETF-only backtest. Options overlay displayed as event flags ONLY.

    Signals computed using close at t; positions implemented at t+1. Execution
    costs are charged with one-day lag. No fabricated option prices or P&L.
    """
    close = ohlc["close"].copy()
    rets = close.pct_change(fill_method=None).fillna(0)
    mi = copula_mispricing(close, cfg.copula_window)
    regimes = regime_probabilities(rets["SPY"], cfg)
    qqq = close["QQQ"]
    sma = qqq.rolling(200, min_periods=200).mean()
    roc = qqq.pct_change(120, fill_method=None)
    adx = _adx(ohlc["high"]["QQQ"], ohlc["low"]["QQQ"], qqq)
    momentum = (qqq > sma) & (roc > 0) & (adx > 20)

    ws = pd.DataFrame(0.0, index=close.index, columns=["GDX", "GLD", "QQQ", "SHV"])
    pair_signal = []
    pair = 0
    for i, dt in enumerate(close.index):
        m, tau = mi.loc[dt, ["mi", "kendall_tau"]]
        crisis = bool(regimes.loc[dt, "high_vol"])
        if not np.isfinite(m) or not np.isfinite(tau):
            pair = 0
        elif crisis and tau < cfg.break_tau:
            pair = 0
        elif pair != 0 and cfg.exit_low <= m <= cfg.exit_high:
            pair = 0
        elif pair == 0 and tau >= cfg.break_tau:
            if m < cfg.entry_low:
                pair = +1   # long GDX / short GLD
            elif m > cfg.entry_high:
                pair = -1   # short GDX / long GLD
        pair_signal.append(pair)
        ws.at[dt, "GDX"] = pair * cfg.pair_leg_weight
        ws.at[dt, "GLD"] = -pair * cfg.pair_leg_weight
        if bool(momentum.loc[dt]):
            ws.at[dt, "QQQ"] = cfg.momentum_weight
        else:
            ws.at[dt, "SHV"] = cfg.momentum_weight
        gross = ws.loc[dt].abs().sum()
        if gross > cfg.gross_cap:
            ws.loc[dt] *= cfg.gross_cap / gross

    # Today's signal -> next day's holding. No same-day signal execution.
    realized_w = ws.shift(1).fillna(0)
    turn = ws.diff().fillna(ws).abs().sum(axis=1).shift(1).fillna(0)
    gross_ret = (realized_w * rets[realized_w.columns]).sum(axis=1)
    costs = turn * cfg.charge_bps / 10000
    borrow = realized_w.clip(upper=0).abs().sum(axis=1) * cfg.short_borrow_bps_annual/10000/252
    net = gross_ret - costs - borrow
    df = pd.DataFrame(index=close.index)
    df["gross_return"] = gross_ret
    df["transaction_cost"] = costs
    df["borrow_cost"] = borrow
    df["net_return"] = net
    df["portfolio_equity"] = 100000*(1+net).cumprod()
    df["qqq_buyhold"] = 100000*(1+rets["QQQ"]).cumprod()
    df["pair_direction"] = pair_signal
    df["mi"] = mi["mi"]
    df["kendall_tau"] = mi["kendall_tau"]
    df["crisis_probability"] = regimes["crisis_probability"]
    df["high_vol"] = regimes["high_vol"]
    df["regime_source"] = regimes["regime_source"]
    df["momentum_on"] = momentum
    df["sma200"] = sma
    df["roc120"] = roc
    df["adx14"] = adx
    df["collar_trigger_only"] = regimes["high_vol"] & (ws["GDX"] > 0) | regimes["high_vol"] & (ws["GLD"] > 0)
    for symbol in ws.columns:
        df[f"weight_{symbol}"] = ws[symbol]
    risk = calculate_risk(net)
    df = pd.concat([df, risk], axis=1)
    if start is not None:
        df = df.loc[pd.Timestamp(start):].copy()
        if len(df) < 10:
            raise ValueError("The chosen backtest start has fewer than 10 observations")
        # Rebase with no hindsight or prior-profit contamination at displayed start.
        df["portfolio_equity"] = 100000 * (1 + df["net_return"]).cumprod()
        df["qqq_buyhold"] = 100000 * (1 + rets.loc[df.index, "QQQ"]).cumprod()
    summary = _summarize(df["net_return"], df["portfolio_equity"], ws.loc[df.index], cfg)
    summary["collar_trigger_days"] = int(df["collar_trigger_only"].sum())
    summary["hmm_fraction"] = float((df["regime_source"] == "hmm_filtered").mean())
    return {"daily": df, "metrics": summary, "signals": ws.loc[df.index]}
