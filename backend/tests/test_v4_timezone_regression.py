"""V4 timezone regression coverage for the new P0/P1/P2 surfaces.

The project has hit this exact bug class three times before (signal
performance, regime performance, backtest beta/alpha - see test_backtesting.
py::test_beta_alpha_present_with_tz_aware_equity_index and
test_v3_regime_performance.py): real yfinance data has a timezone-AWARE
DatetimeIndex, while constructed date strings/objects are naive. Comparing
or slicing one against the other with `.loc[:timestamp]` or a naive-keyed
reindex silently matches nothing rather than raising - so every new V4
module that aligns dates across tickers or across a benchmark is exercised
here specifically with tz-localized synthetic fixtures, which a tz-naive
fixture would never catch.
"""
import numpy as np
import pandas as pd
import pytest

from app.backtesting.portfolio import run_portfolio_backtest
from app.comparison.service import compare_stocks
from app.model_evaluation.scorecard import build_model_scorecard
from app.paper_trading import service as paper_trading_service


def _tz_localize_all(dfs: dict, tz: str = "America/New_York") -> dict:
    return {t: df.tz_localize(tz) for t, df in dfs.items()}


def _make_long_ohlcv(n: int, seed: int) -> pd.DataFrame:
    """Same generator shape as conftest's _make_ohlcv, duplicated locally
    (as test_v4_portfolio_backtesting.py already does for its own multi-
    ticker generator) so this module needs a longer history than the
    shared ohlcv_long fixture provides - walk-forward's 2+1 year defaults
    need 3+ years, and ohlcv_long is only ~1.6 years.
    """
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=0.0005, scale=0.015, size=n)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    open_ = np.empty(n)
    open_[0] = 100.0
    open_[1:] = close[:-1]
    noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + noise)
    low = np.minimum(open_, close) * (1 - noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


def test_portfolio_backtest_handles_tz_aware_multi_ticker_data(ohlcv_long, ohlcv_uptrend, ohlcv_downtrend, monkeypatch):
    from app.backtesting import portfolio as portfolio_module

    monkeypatch.setattr(portfolio_module, "_sector_for", lambda ticker: "Technology")

    price_data = _tz_localize_all({"AAA": ohlcv_long, "BBB": ohlcv_uptrend, "CCC": ohlcv_downtrend})
    start = price_data["AAA"].index[220].date()
    end = price_data["AAA"].index[-1].date()

    result = run_portfolio_backtest(
        tickers=["AAA", "BBB", "CCC"], price_data=price_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert result.final_capital > 0
    assert len(result.equity_curve) > 100
    # If tz handling silently matched nothing, holdings/rebalances would be empty.
    assert len(result.holdings_history) > 0
    assert result.number_of_rebalances > 0


def test_portfolio_backtest_benchmark_comparison_with_tz_aware_benchmark(ohlcv_long, ohlcv_uptrend, monkeypatch):
    from app.backtesting import portfolio as portfolio_module

    monkeypatch.setattr(portfolio_module, "_sector_for", lambda ticker: "Technology")

    price_data = _tz_localize_all({"AAA": ohlcv_long, "BBB": ohlcv_uptrend})
    benchmark_df = ohlcv_uptrend.tz_localize("America/New_York")
    start = price_data["AAA"].index[220].date()
    end = price_data["AAA"].index[-1].date()

    result = run_portfolio_backtest(
        tickers=["AAA", "BBB"], price_data=price_data,
        start_date=start, end_date=end,
        initial_capital=20_000.0, transaction_cost_bps=5, slippage_bps=5,
        benchmark_ticker="SPY", benchmark_price_df=benchmark_df,
    )
    # A naive/aware mismatch in the benchmark slice would silently produce an
    # empty curve and a None return instead of raising.
    assert result.benchmark_return_percent is not None
    assert len(result.benchmark_curve) > 100


def test_comparison_service_handles_tz_aware_history(monkeypatch, ohlcv_long):
    from app.comparison import service as comparison_module

    tz_df = ohlcv_long.tz_localize("America/New_York")

    def fake_get_overview(ticker):
        return {"company_name": f"{ticker} Inc", "sector": "Technology", "industry": "Software",
                "last_price": 100.0, "change_percent": 1.0, "market_cap": 1_000_000_000.0}, None

    monkeypatch.setattr(comparison_module.market_data, "get_overview", fake_get_overview)
    monkeypatch.setattr(comparison_module.market_data, "get_full_daily_history", lambda ticker: (tz_df, None))
    monkeypatch.setattr(comparison_module.market_data, "fetch_info_raw", lambda ticker: {})

    result = compare_stocks(["AAA", "BBB"], benchmark_ticker="AAA")
    for row in result.rows:
        assert row.error is None
        # Relative-strength periods use positional (.iloc) lookups, not
        # date-based ones, so tz-awareness must never prevent this from
        # populating - but assert it explicitly as a regression guard.
        assert row.return_1y_percent is not None


def test_model_scorecard_handles_tz_aware_history(monkeypatch):
    # Walk-forward's defaults need 2 (train) + 1 (test) = 3+ years of history
    # to produce even one fold - ohlcv_long (400 days, ~1.6 years) is too
    # short for that regardless of timezone, so this needs its own longer
    # fixture rather than reusing the shared one.
    long_history = _make_long_ohlcv(2200, seed=42)
    tz_ticker = long_history.tz_localize("America/New_York")
    tz_benchmark = long_history.tz_localize("America/New_York")

    result = build_model_scorecard(
        ticker="TEST", full_price_df=tz_ticker, benchmark="SPY", benchmark_full_price_df=tz_benchmark,
    )
    oos_dim = next(d for d in result.dimensions if d.name == "OUT_OF_SAMPLE_STRENGTH")
    walk_forward_dim = next(d for d in result.dimensions if d.name == "WALK_FORWARD_STABILITY")
    regime_dim = next(d for d in result.dimensions if d.name == "REGIME_DEPENDENCY")
    # A tz mismatch inside any of the reused engines would show up as an
    # INSUFFICIENT_DATA verdict from an empty/broken slice rather than a
    # real computation - assert these actually ran.
    assert oos_dim.label != "INSUFFICIENT_DATA" or "trade(s)" in oos_dim.detail
    assert walk_forward_dim.label in ("STRONG", "MODERATE", "WEAK")
    assert regime_dim.label in ("STRONG", "MODERATE", "WEAK")


def test_paper_trading_snapshot_trading_day_from_tz_aware_benchmark(monkeypatch, db_session, ohlcv_long):
    """_latest_real_trading_day extracts a plain date() from the benchmark's
    (tz-aware, in production) index - confirm that plain-date extraction
    survives a real tz-aware index rather than only ever being exercised
    against the tz-naive synthetic fixtures used elsewhere.
    """
    from app.models_db.user import User

    user = User(email="tz-regression-test@example.com", password_hash="x", display_name="Test")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    tz_df = ohlcv_long.tz_localize("America/New_York")
    expected_day = tz_df.index[-1].date()

    monkeypatch.setattr(paper_trading_service.market_data, "get_full_daily_history", lambda ticker: (tz_df, None))
    monkeypatch.setattr(paper_trading_service, "_current_price", lambda ticker: 100.0)
    monkeypatch.setattr(paper_trading_service, "_current_signal_snapshot", lambda ticker: (None, None))
    monkeypatch.setattr(paper_trading_service, "_current_market_regime", lambda: None)

    paper_trading_service.execute_trade(db_session, user.id, "tz_test_portfolio", "AAPL", "BUY", 1)
    history = paper_trading_service.get_equity_history(db_session, user.id, "tz_test_portfolio")

    assert len(history.snapshots) == 1
    assert history.snapshots[0].date == expected_day.isoformat()
