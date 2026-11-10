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


def test_page_initial_render():
    from streamlit.testing.v1 import AppTest
    page = AppTest.from_file("../pages/10_Multi_Alpha_Strategy_Lab.py").run(timeout=30)
    assert not page.exception
    page.radio[0].set_value("Upload OHLC CSV").run()
    assert not page.exception


def test_page_fetch_error(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import src.multi_alpha_strategy as engine
    def fail(*args, **kwargs):
        raise ValueError("offline test")
    monkeypatch.setattr(engine, "yahoo_download", fail)
    page = AppTest.from_file("../pages/10_Multi_Alpha_Strategy_Lab.py").run(timeout=30)
    page.button[0].click().run(timeout=30)
    assert not page.exception
    assert any("offline test" in error.value for error in page.error)



def test_results_panel_and_csv():
    from streamlit.testing.v1 import AppTest
    result = backtest(validate_ohlc(make_prices()), StrategyConfig(regime_method="volatility"))
    page = AppTest.from_file("../pages/10_Multi_Alpha_Strategy_Lab.py")
    page.session_state["multi_alpha_result"] = result
    page.session_state["multi_alpha_source"] = "Synthetic test data"
    page.run(timeout=30)
    assert not page.exception
    assert len(page.metric) >= 7
    assert len(page.get("download_button")) == 1
    exported = pd.read_csv(__import__("io").StringIO(result["daily"].to_csv()))
    assert len(exported) == 360
    assert "cvar99" in exported


def test_csv_upload_end_date_and_error():
    from streamlit.testing.v1 import AppTest
    from datetime import date
    page = AppTest.from_file("../pages/10_Multi_Alpha_Strategy_Lab.py").run(timeout=30)
    page.radio[0].set_value("Upload OHLC CSV").run()
    page.selectbox[0].set_value("Volatility baseline")
    page.date_input[0].set_value(date(2023, 1, 2))
    page.date_input[1].set_value(date(2024, 3, 1))
    page.file_uploader[0].set_value(("prices.csv", make_prices().to_csv(index=False).encode(), "text/csv")).run()
    page.button[0].click().run(timeout=30)
    assert not page.exception
    assert not page.error
    assert page.session_state["multi_alpha_result"]["daily"].index.max() <= pd.Timestamp("2024-03-01")
    assert len(page.get("download_button")) == 1
    page.file_uploader[0].set_value(("bad.csv", b"bad\n1", "text/csv")).run()
    page.button[0].click().run(timeout=30)
    assert page.error
    assert "multi_alpha_result" not in page.session_state


def test_ohlc_roundoff_tolerance():
    raw = make_prices()
    raw.loc[0, "high"] = raw.loc[0, "close"] - 1e-12
    validate_ohlc(raw)
    raw.loc[0, "high"] = raw.loc[0, "close"] - 1
    import pytest
    with pytest.raises(ValueError, match="OHLC"):
        validate_ohlc(raw)
