"""Volume indicators."""
import pandas as pd


def volume_sma(volume: pd.Series, window: int = 20) -> pd.Series:
    return volume.rolling(window=window, min_periods=window).mean()


def relative_volume(volume: pd.Series, window: int = 20) -> pd.Series:
    """Current volume divided by its rolling average. > 1 means above-average."""
    avg = volume_sma(volume, window)
    return volume / avg.replace(0, pd.NA)
