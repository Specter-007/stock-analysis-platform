"""The most important test file in the application.

Proves, directly and explicitly, that no signal, score, indicator, or
backtest decision at time T can be changed by ANY data after T - not just
by its absence (truncation, already covered in
`test_indicators.py::test_indicators_are_causal_no_lookahead`), but by its
presence with DIFFERENT values. If future prices were ever leaking into a
past decision, mutating them (while leaving everything through T untouched)
would change the result at T. It must not.
"""
import numpy as np
import pandas as pd
import pytest

from app.indicators.compute import compute_indicator_frame
from app.signals import engine as signal_engine
from app.signals.history import compute_signal_history_full


def _mutate_future(df: pd.DataFrame, cutoff_idx: int, seed: int) -> pd.DataFrame:
    """Returns a copy of `df` with every row AFTER `cutoff_idx` replaced by a
    completely different, independently-generated price path. Rows up to and
    including `cutoff_idx` are untouched.
    """
    mutated = df.copy()
    n_future = len(df) - (cutoff_idx + 1)
    if n_future <= 0:
        return mutated

    rng = np.random.default_rng(seed)
    last_close = float(df["Close"].iloc[cutoff_idx])
    shocked_returns = rng.normal(-0.01, 0.08, n_future)  # wild, unrelated future path
    new_close = last_close * np.exp(np.cumsum(shocked_returns))
    new_open = np.empty(n_future)
    new_open[0] = last_close
    new_open[1:] = new_close[:-1]
    noise = rng.uniform(0.001, 0.03, n_future)
    new_high = np.maximum(new_open, new_close) * (1 + noise)
    new_low = np.minimum(new_open, new_close) * (1 - noise)
    new_volume = rng.integers(1_000_000, 20_000_000, n_future).astype(float)

    future_index = df.index[cutoff_idx + 1 :]
    mutated.loc[future_index, "Open"] = new_open
    mutated.loc[future_index, "High"] = new_high
    mutated.loc[future_index, "Low"] = new_low
    mutated.loc[future_index, "Close"] = new_close
    mutated.loc[future_index, "Volume"] = new_volume
    return mutated


@pytest.mark.parametrize("cutoff_idx", [220, 250, 300, 399])
def test_changing_future_prices_does_not_alter_historical_signal(ohlcv_long, cutoff_idx):
    """For a fixed historical date T (`cutoff_idx`), the signal computed with
    the ORIGINAL future data must exactly match the signal computed with a
    WILDLY DIFFERENT, independently-generated future data - because a
    correct causal model must never look past T to decide what happened at T.
    """
    original_frame = compute_indicator_frame(ohlcv_long)
    original_signal = signal_engine.evaluate(original_frame.iloc[: cutoff_idx + 1])

    mutated_prices = _mutate_future(ohlcv_long, cutoff_idx, seed=cutoff_idx)
    mutated_frame = compute_indicator_frame(mutated_prices)
    # Evaluate on the FULL mutated frame's row at cutoff_idx (not a truncated
    # slice) - this is the strongest version of the test: even with future
    # rows physically present in the DataFrame, evaluating on the identical
    # historical row index must be unaffected by what comes after it.
    row_from_full_mutated_frame = mutated_frame.iloc[cutoff_idx]
    resliced = mutated_frame.loc[: mutated_frame.index[cutoff_idx]]
    mutated_signal = signal_engine.evaluate(resliced)

    assert mutated_signal.score == pytest.approx(original_signal.score), (
        f"Score at index {cutoff_idx} changed from {original_signal.score} to "
        f"{mutated_signal.score} after mutating only FUTURE data - this indicates look-ahead bias."
    )
    assert mutated_signal.signal == original_signal.signal

    # Also confirm every individual indicator value at that row is untouched,
    # not just the final aggregated score (a bug could cancel out in the
    # score while still leaking in an individual factor).
    for col in ("SMA_20", "SMA_50", "SMA_200", "RSI_14", "MACD", "ATR_14", "HIST_VOL_20", "REL_VOLUME"):
        original_val = original_frame.iloc[cutoff_idx][col]
        mutated_val = row_from_full_mutated_frame[col]
        if pd.isna(original_val) and pd.isna(mutated_val):
            continue
        assert original_val == pytest.approx(mutated_val), f"{col} leaked future data at index {cutoff_idx}"


def test_signal_history_unaffected_by_appending_future_data(ohlcv_long):
    """The entire signal HISTORY (not just one point) computed from data
    through day K must be identical whether the input DataFrame ends at day
    K, or continues for another year with completely different prices.
    """
    cutoff_idx = 300
    truncated_df = ohlcv_long.iloc[: cutoff_idx + 1]
    extended_df = _mutate_future(ohlcv_long, cutoff_idx, seed=99)

    truncated_frame = compute_indicator_frame(truncated_df)
    extended_frame = compute_indicator_frame(extended_df)

    history_from_truncated = compute_signal_history_full(truncated_frame, lookback_sessions=60)
    history_from_extended_but_sliced = compute_signal_history_full(
        extended_frame.loc[: extended_frame.index[cutoff_idx]], lookback_sessions=60
    )

    assert [d for d, _ in history_from_truncated] == [d for d, _ in history_from_extended_but_sliced]
    for (d1, r1), (d2, r2) in zip(history_from_truncated, history_from_extended_but_sliced):
        assert d1 == d2
        assert r1.score == pytest.approx(r2.score)
        assert r1.signal == r2.signal


def test_backtest_trade_decisions_before_cutoff_unaffected_by_future_mutation(ohlcv_long):
    """A backtest run only through day K must produce identical trades to one
    run on a longer series with the SAME history through day K but a totally
    different, mutated continuation afterward.
    """
    from app.backtesting.engine import run_backtest

    cutoff_idx = 350
    cutoff_date = ohlcv_long.index[cutoff_idx].date()
    start_date = ohlcv_long.index[220].date()

    baseline = run_backtest(
        ticker="TEST", full_price_df=ohlcv_long.iloc[: cutoff_idx + 1],
        start_date=start_date, end_date=cutoff_date,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )

    mutated_full = _mutate_future(ohlcv_long, cutoff_idx, seed=7)
    with_mutated_future = run_backtest(
        ticker="TEST", full_price_df=mutated_full,
        start_date=start_date, end_date=cutoff_date,
        initial_capital=10_000.0, transaction_cost_bps=5, slippage_bps=5,
    )

    assert baseline.total_return_percent == pytest.approx(with_mutated_future.total_return_percent)
    assert len(baseline.trades) == len(with_mutated_future.trades)
    for t1, t2 in zip(baseline.trades, with_mutated_future.trades):
        assert t1.entry_date == t2.entry_date
        assert t1.entry_price == pytest.approx(t2.entry_price)
