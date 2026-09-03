"""Shared deterministic synthetic fixtures.

IMPORTANT: this synthetic data exists only to test calculation logic in
isolation. It must never be used as a fallback for real production market
data anywhere in the application - see app/services/market_data.py, which
only ever returns data actually retrieved from Yahoo Finance.
"""
import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(n: int, seed: int, start_price: float = 100.0, drift: float = 0.0005, vol: float = 0.015) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=drift, scale=vol, size=n)
    close = start_price * np.exp(np.cumsum(log_returns))

    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]

    intraday_noise = rng.uniform(0.001, 0.01, size=n)
    high = np.maximum(open_, close) * (1 + intraday_noise)
    low = np.minimum(open_, close) * (1 - intraday_noise)
    volume = rng.integers(1_000_000, 10_000_000, size=n).astype(float)

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


@pytest.fixture
def ohlcv_long():
    """400 business days - enough for every indicator window (SMA 200 included)."""
    return _make_ohlcv(400, seed=42)


@pytest.fixture
def ohlcv_short():
    """10 business days - not enough for most indicators."""
    return _make_ohlcv(10, seed=7)


@pytest.fixture
def ohlcv_uptrend():
    """Strong, low-noise uptrend so trend/momentum factors are unambiguous."""
    return _make_ohlcv(400, seed=1, drift=0.004, vol=0.006)


@pytest.fixture
def ohlcv_downtrend():
    """Strong, low-noise downtrend."""
    return _make_ohlcv(400, seed=2, drift=-0.004, vol=0.006)


@pytest.fixture
def ohlcv_high_volatility():
    return _make_ohlcv(400, seed=3, drift=0.0, vol=0.06)
