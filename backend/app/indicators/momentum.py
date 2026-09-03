"""Momentum indicators: RSI, MACD, Rate of Change."""
import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's RSI. Uses Wilder smoothing (equivalent to an EWM with
    alpha = 1/window) rather than a simple rolling mean, matching the
    original 1978 formulation used by most charting platforms.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    result = 100 - (100 / (1 + rs))
    # Where avg_loss is exactly 0 (no down days in the window) RSI is 100.
    result = result.where(avg_loss != 0, 100.0)
    return result


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def roc(close: pd.Series, window: int = 12) -> pd.Series:
    """Rate of change, as a percentage."""
    return (close / close.shift(window) - 1.0) * 100.0
