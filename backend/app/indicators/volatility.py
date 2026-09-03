"""Volatility indicators: ATR, Bollinger Bands, historical volatility."""
import numpy as np
import pandas as pd


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's Average True Range."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def bollinger_bands(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower). Population std (ddof=0), the
    conventional choice for Bollinger Bands.
    """
    middle = close.rolling(window=window, min_periods=window).mean()
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def historical_volatility(
    close: pd.Series, window: int = 20, annualization: int = 252
) -> pd.Series:
    """Annualized historical volatility from log returns, as a percentage."""
    log_returns = np.log(close / close.shift(1))
    return log_returns.rolling(window=window, min_periods=window).std(ddof=0) * np.sqrt(
        annualization
    ) * 100.0
