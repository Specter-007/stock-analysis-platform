"""Trend indicators: simple and exponential moving averages.

All functions are pure and deterministic: same input Series -> same output
Series, every time. No randomness, no external state.
"""
import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False, min_periods=window).mean()
