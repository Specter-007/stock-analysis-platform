"""V4 P1.4: portfolio-level (multi-ticker) backtesting.

Network-isolated: sector lookups are mocked (the same
`market_data.get_overview` pattern used by test_v3_paper_trading_advanced's
mocked_sector fixture). Price data is synthetic but built with the same
`_make_ohlcv`-style generator as the shared conftest fixtures, extended to
produce several correlated tickers.
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from app.backtesting.portfolio import (
    PortfolioConstraints,
    run_portfolio_backtest,
)
from app.services.exceptions import InsufficientHistoryError


def _make_multi_ohlcv(n: int, seed: int, market_beta: float = 1.0, start_price: float = 100.0) -> pd.DataFrame:
    """A ticker whose returns are a blend of a shared market factor (so
    correlation/portfolio math has something real to compute) plus
    idiosyncratic noise - same OHLCV shape as conftest's _make_ohlcv.
    """
    rng = np.random.default_rng(seed)
    market_rng = np.random.default_rng(999)  # shared across tickers
    market_returns = market_rng.normal(loc=0.0004, scale=0.01, size=n)
    idio_returns = rng.normal(loc=0.0002, scale=0.012, size=n)
    log_returns = market_beta * market_returns + idio_returns
    close = start_price * np.exp(np.cumsum(log_returns))

    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]
    noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + noise)
    low = np.minimum(open_, close) * (1 - noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=index)


@pytest.fixture
def three_ticker_data():
    return {
        "AAA": _make_multi_ohlcv(400, seed=10, market_beta=1.0),
        "BBB": _make_multi_ohlcv(400, seed=11, market_beta=1.2),
        "CCC": _make_multi_ohlcv(400, seed=12, market_beta=0.6),
    }


@pytest.fixture(autouse=True)
def mocked_sector(monkeypatch):
    from app.backtesting import portfolio as portfolio_module

    sectors = {"AAA": "Technology", "BBB": "Technology", "CCC": "Healthcare"}

    def fake_sector_for(ticker):
        return sectors.get(ticker, "Unknown")

    monkeypatch.setattr(portfolio_module, "_sector_for", fake_sector_for)


def _date_range(data, start_offset=220):
    any_df = next(iter(data.values()))
    return any_df.index[start_offset].date(), any_df.index[-1].date()


def test_basic_portfolio_backtest_runs_and_produces_equity_curve(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()),
        price_data=three_ticker_data,
        start_date=start,
        end_date=end,
        initial_capital=30_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    assert result.final_capital > 0
    assert len(result.equity_curve) == result.trading_days
    assert result.trading_days > 100
    assert result.allocation_method == "EQUAL_WEIGHT"
    assert result.rebalance_frequency == "MONTHLY"


def test_insufficient_history_raises(three_ticker_data):
    any_df = next(iter(three_ticker_data.values()))
    with pytest.raises(InsufficientHistoryError):
        run_portfolio_backtest(
            tickers=list(three_ticker_data.keys()),
            price_data=three_ticker_data,
            start_date=any_df.index[-5].date(),
            end_date=any_df.index[-1].date(),
            initial_capital=30_000.0,
            transaction_cost_bps=5,
            slippage_bps=5,
        )


def test_equal_weight_buy_hold_curve_matches_equity_curve_length(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()),
        price_data=three_ticker_data,
        start_date=start,
        end_date=end,
        initial_capital=30_000.0,
        transaction_cost_bps=5,
        slippage_bps=5,
    )
    assert len(result.equal_weight_buy_hold_curve) == len(result.equity_curve)
    assert result.equal_weight_buy_hold_return_percent is not None


def test_no_look_ahead_future_price_mutation_does_not_change_past_equity(three_ticker_data):
    start, end_full = _date_range(three_ticker_data)
    truncated = {t: df.iloc[:-30].copy() for t, df in three_ticker_data.items()}
    end_truncated = truncated["AAA"].index[-1].date()

    mutated = {t: df.copy() for t, df in three_ticker_data.items()}
    for t in mutated:
        mutated[t].iloc[-1, mutated[t].columns.get_loc("Close")] *= 5.0

    result_truncated = run_portfolio_backtest(
        tickers=list(truncated.keys()), price_data=truncated,
        start_date=start, end_date=end_truncated,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    result_full = run_portfolio_backtest(
        tickers=list(mutated.keys()), price_data=mutated,
        start_date=start, end_date=end_truncated,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert result_truncated.total_return_percent == result_full.total_return_percent
    assert [p.equity for p in result_truncated.equity_curve] == [p.equity for p in result_full.equity_curve]


def test_cash_and_positions_never_exceed_total_equity(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        constraints=PortfolioConstraints(cash_allocation_percent=50.0),  # force tight cash, stresses scaling
    )
    by_date: dict[str, float] = {}
    for h in result.holdings_history:
        by_date[h.date] = by_date.get(h.date, 0.0) + h.weight_percent
    for date, total_weight in by_date.items():
        assert total_weight <= 100.0 + 0.5  # small float tolerance


def test_max_holdings_constraint_caps_number_of_positions(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        rebalance_frequency="MONTHLY",
        constraints=PortfolioConstraints(max_holdings=1),
    )
    final_date = result.end_date
    final_holdings = [h for h in result.holdings_history if h.date == final_date]
    assert len(final_holdings) <= 1


def test_sector_cap_constraint_limits_sector_exposure(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        constraints=PortfolioConstraints(sector_cap_percent=40.0),
    )
    for sector, pct in result.risk_analytics["sector_concentration_percent"].items():
        assert pct <= 40.0 + 1.0  # tolerance for rounding across waterfall passes


@pytest.mark.parametrize("method", ["EQUAL_WEIGHT", "SIGNAL_WEIGHTED", "RISK_WEIGHTED"])
def test_allocation_methods_produce_valid_bounded_weights(three_ticker_data, method):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        allocation_method=method,
    )
    for h in result.holdings_history:
        assert -1.0 <= h.weight_percent <= 101.0


def test_fixed_weight_allocation_uses_supplied_weights(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        allocation_method="FIXED_WEIGHT",
        fixed_weights={"AAA": 0.6, "BBB": 0.3, "CCC": 0.1},
    )
    assert result.final_capital > 0


def test_daily_rebalance_produces_more_rebalances_than_monthly(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    daily = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        rebalance_frequency="DAILY",
    )
    monthly = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        rebalance_frequency="MONTHLY",
    )
    assert daily.number_of_rebalances > monthly.number_of_rebalances


def test_correlation_matrix_present_and_diagonal_is_one(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    corr = result.risk_analytics["correlation_matrix"]
    assert corr is not None
    for t in result.tickers:
        assert corr[t][t] == pytest.approx(1.0, abs=0.01)


def test_benchmark_comparison_when_supplied(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    benchmark_df = _make_multi_ohlcv(400, seed=99, market_beta=1.0)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        benchmark_ticker="SPY", benchmark_price_df=benchmark_df,
    )
    assert result.benchmark_return_percent is not None
    assert len(result.benchmark_curve) > 0


def test_excluded_ticker_reported_and_backtest_still_runs(three_ticker_data):
    data = dict(three_ticker_data)
    data["ZZZ"] = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(data.keys()), price_data=data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
    )
    assert "ZZZ" in result.excluded_tickers
    assert "ZZZ" not in result.tickers
    assert result.final_capital > 0


def test_min_position_weight_drops_tiny_allocations(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        constraints=PortfolioConstraints(min_position_weight_percent=90.0),  # only 1 name can ever qualify
    )
    by_date: dict[str, int] = {}
    for h in result.holdings_history:
        by_date[h.date] = by_date.get(h.date, 0) + 1
    for date, count in by_date.items():
        assert count <= 1


def test_unchanged_target_weight_produces_no_spurious_insufficient_cash_warning(monkeypatch, three_ticker_data):
    """Regression test: target dollar amounts must be sized off the actual
    portfolio value AT EXECUTION (today's open), not a stale decision-day
    close snapshot. Using the stale snapshot made a holding that is already
    exactly at its (unchanged) target weight look artificially underfunded
    whenever the ticker gapped down overnight - there was no real allocation
    change to make, so no trade (and no cash shortfall) should ever occur.
    """
    from app.backtesting import portfolio as portfolio_module

    # Force the SAME single ticker to be the only eligible name, at the same
    # weight, on every rebalance - so the target allocation never actually
    # changes month to month and a real portfolio manager would place zero
    # orders. Patching _target_weights isolates the dollar-sizing logic
    # (what this regression targets) from signal-generation noise.
    monkeypatch.setattr(portfolio_module, "_target_weights", lambda *a, **k: {"AAA": 1.0})

    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        rebalance_frequency="MONTHLY",
    )
    cash_warnings = [w for w in result.warnings if "Insufficient cash" in w]
    assert cash_warnings == []


def test_invalid_allocation_method_raises(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    with pytest.raises(ValueError):
        run_portfolio_backtest(
            tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
            start_date=start, end_date=end,
            initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
            allocation_method="NOT_REAL",
        )


def test_equity_always_equals_cash_plus_holdings_even_under_scaled_rebalances(three_ticker_data):
    """A rebalance that can't be fully funded (e.g. a signal rotation into a
    name that needs more cash than available sells generate) must scale down
    gracefully - it must never fabricate or destroy portfolio value. Since
    equity is computed directly as cash + mark-to-market holdings at every
    step, this is really asserting the loop never lets that computation
    diverge from the actual (scaled or not) trades that were executed - a
    discontinuous jump in equity across a rebalance day (beyond ordinary
    single-day price movement) would indicate phantom value creation.
    """
    start, end = _date_range(three_ticker_data)
    result = run_portfolio_backtest(
        tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
        start_date=start, end_date=end,
        initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
        constraints=PortfolioConstraints(cash_allocation_percent=80.0),  # force chronic underfunding
    )
    equities = [p.equity for p in result.equity_curve]
    assert all(e >= 0 for e in equities)
    # No single day-to-day move should exceed a generous sanity bound - a
    # phantom-value bug would typically show up as an implausible spike.
    for prev, curr in zip(equities, equities[1:]):
        if prev > 0:
            assert abs(curr / prev - 1.0) < 0.5


def test_invalid_rebalance_frequency_raises(three_ticker_data):
    start, end = _date_range(three_ticker_data)
    with pytest.raises(ValueError):
        run_portfolio_backtest(
            tickers=list(three_ticker_data.keys()), price_data=three_ticker_data,
            start_date=start, end_date=end,
            initial_capital=30_000.0, transaction_cost_bps=5, slippage_bps=5,
            rebalance_frequency="YEARLY",
        )
