import numpy as np
import pandas as pd
from src.multi_alpha_strategy import validate_ohlc, backtest, StrategyConfig, copula_mispricing


def make_prices(n=360):
    rng = np.random.default_rng(123)
    dates = pd.bdate_range("2023-01-02", periods=n)
    q = rng.normal(.0004, .009, n)
    g = rng.normal(.0002, .012, n)
    series = {}
    for symbol, r in {"SPY": q*.65, "QQQ": q, "SHV": np.full(n,.00009),
                      "GDX": g, "GLD": .5*g + rng.normal(0,.006,n)}.items():
        c = 100*np.exp(np.cumsum(r))
        series[symbol] = c
    rows=[]
    for symbol, c in series.items():
        for i, day in enumerate(dates):
            rows.append((day,symbol,c[i]*1.01,c[i]*.99,c[i]))
    return pd.DataFrame(rows,columns=["date","symbol","high","low","close"])


def test_validate_and_signals():
    prices=validate_ohlc(make_prices())
    assert prices.shape[0]==360
    cfg=StrategyConfig(regime_method="volatility",copula_window=60)
    r=backtest(prices,cfg)
    assert len(r['daily'])==360
    assert np.isfinite(r['metrics']['ending_equity'])
    assert r['signals'].abs().sum(axis=1).max() <= 1.0000001
    assert r['daily']['collar_trigger_only'].dtype==bool


def test_causal_mi_no_future_leakage():
    prices=validate_ohlc(make_prices())
    close=prices['close'].copy()
    mi1=copula_mispricing(close,window=60)
    altered=close.copy()
    altered.iloc[-1,altered.columns.get_loc('GDX')]*=1.9
    mi2=copula_mispricing(altered,window=60)
    # Altering future final price cannot affect any earlier signal.
    pd.testing.assert_frame_equal(mi1.iloc[:-1],mi2.iloc[:-1])


def test_next_day_trade_cost_lag():
    prices=validate_ohlc(make_prices())
    cfg=StrategyConfig(regime_method="volatility",copula_window=60,charge_bps=25)
    r=backtest(prices,cfg)
    # Trade cost is proportional to PREVIOUS day's signal weight changes.
    expect=r['signals'].diff().fillna(r['signals']).abs().sum(axis=1).shift(1).fillna(0)*cfg.charge_bps/10000
    pd.testing.assert_series_equal(r['daily']['transaction_cost'],expect,check_names=False)


def test_backtest_prefix_invariance():
    prices = validate_ohlc(make_prices(420))
    cfg = StrategyConfig(regime_method="hmm", hmm_training_days=300, copula_window=60)
    full = backtest(prices, cfg)["daily"]
    prefix = backtest(prices.iloc[:380], cfg)["daily"]
    pd.testing.assert_frame_equal(full.iloc[:380], prefix)


def test_initial_position_cost():
    result = backtest(validate_ohlc(make_prices()), StrategyConfig(regime_method="volatility"))
    assert result["daily"]["transaction_cost"].iloc[1] > 0











def test_ohlc_roundoff_tolerance():
    raw = make_prices()
    raw.loc[0, "high"] = raw.loc[0, "close"] - 1e-12
    validate_ohlc(raw)
    raw.loc[0, "high"] = raw.loc[0, "close"] - 1
    import pytest
    with pytest.raises(ValueError, match="OHLC"):
        validate_ohlc(raw)
