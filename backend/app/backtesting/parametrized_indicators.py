"""Indicator computation with CALLER-SUPPLIED periods, used exclusively by
parameter-sensitivity analysis. This is deliberately a separate code path
from `app.indicators.compute.compute_indicator_frame` (the one every live
signal, backtest, walk-forward, Monte Carlo, and out-of-sample run uses) so
that sensitivity experiments can never - even accidentally - alter Quant
v1.0/v1.1 behavior. The two are proven equivalent at default parameters by
`tests/test_v4_sensitivity_extended.py::test_default_params_match_standard_indicator_frame`.

Output columns are the same CANONICAL names the signal engine reads
(`SMA_20`, `SMA_50`, `SMA_200`, `RSI_14`, `MACD`, `MACD_SIGNAL`, `ROC_12`,
`REL_VOLUME`, `HIST_VOL_20`, ...) regardless of which period actually
produced them - e.g. requesting `sma_short=25` still stores it as `SMA_20`.
This keeps `signals.engine.evaluate()` completely unaware that a
non-default period was used, so no scoring logic has to be duplicated or
touched to support sensitivity testing.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.config import (
    ATR_WINDOW,
    BOLLINGER_STD,
    BOLLINGER_WINDOW,
    HIST_VOL_ANNUALIZATION,
    HIST_VOL_WINDOW,
    MACD_FAST,
    MACD_SIGNAL,
    MACD_SLOW,
    ROC_WINDOW,
    RSI_WINDOW,
    VOLUME_SMA_WINDOW,
)
from app.indicators import momentum, trend, volatility
from app.indicators import volume as volume_ind

# Defaults mirror app.config exactly, so calling with no overrides reproduces
# the standard indicator frame bit-for-bit on every column the engine reads.
DEFAULT_PARAMS = {
    "sma_short": 20,
    "sma_medium": 50,
    "sma_long": 200,
    "rsi_period": RSI_WINDOW,
    "macd_fast": MACD_FAST,
    "macd_slow": MACD_SLOW,
    "macd_signal": MACD_SIGNAL,
    "roc_period": ROC_WINDOW,
    "atr_period": ATR_WINDOW,
    "bb_period": BOLLINGER_WINDOW,
    "bb_std": BOLLINGER_STD,
    "volume_sma_period": VOLUME_SMA_WINDOW,
}

# Sensible perturbation ranges, centered on the default. Deliberately
# bounded (not "any integer a caller sends") so sensitivity runs stay a
# robustness check, not an invitation to overfit an arbitrary grid search.
SENSITIVITY_RANGES = {
    "buy_threshold": [55, 60, 65, 70, 75],
    "sell_threshold": [20, 25, 30, 35, 40],
    "rsi_period": [7, 10, 14, 18, 21],
    "sma_short": [10, 15, 20, 25, 30],
    "sma_long": [150, 175, 200, 225, 250],
    "macd_fast": [8, 10, 12, 14, 16],
    "macd_slow": [20, 23, 26, 29, 32],
}

PARAMETER_LABELS = {
    "buy_threshold": "BUY Score Threshold",
    "sell_threshold": "SELL Score Threshold",
    "rsi_period": "RSI Period",
    "sma_short": "Short SMA Period",
    "sma_long": "Long SMA Period",
    "macd_fast": "MACD Fast Period",
    "macd_slow": "MACD Slow Period",
}


@dataclass
class IndicatorParams:
    sma_short: int = DEFAULT_PARAMS["sma_short"]
    sma_medium: int = DEFAULT_PARAMS["sma_medium"]
    sma_long: int = DEFAULT_PARAMS["sma_long"]
    rsi_period: int = DEFAULT_PARAMS["rsi_period"]
    macd_fast: int = DEFAULT_PARAMS["macd_fast"]
    macd_slow: int = DEFAULT_PARAMS["macd_slow"]
    macd_signal: int = DEFAULT_PARAMS["macd_signal"]
    roc_period: int = DEFAULT_PARAMS["roc_period"]
    atr_period: int = DEFAULT_PARAMS["atr_period"]
    bb_period: int = DEFAULT_PARAMS["bb_period"]
    bb_std: float = DEFAULT_PARAMS["bb_std"]
    volume_sma_period: int = DEFAULT_PARAMS["volume_sma_period"]


def compute_custom_indicator_frame(df: pd.DataFrame, params: IndicatorParams) -> pd.DataFrame:
    """Same causal, non-mutating contract as `compute_indicator_frame` -
    every column at row T depends only on rows <= T."""
    out = df.copy()
    close = out["Close"]
    high = out["High"]
    low = out["Low"]
    vol = out["Volume"]

    out["SMA_20"] = trend.sma(close, params.sma_short)
    out["SMA_50"] = trend.sma(close, params.sma_medium)
    out["SMA_100"] = trend.sma(close, 100)
    out["SMA_200"] = trend.sma(close, params.sma_long)
    out["EMA_20"] = trend.ema(close, 20)
    out["EMA_50"] = trend.ema(close, 50)

    out["RSI_14"] = momentum.rsi(close, params.rsi_period)

    macd_line, signal_line, hist = momentum.macd(close, params.macd_fast, params.macd_slow, params.macd_signal)
    out["MACD"] = macd_line
    out["MACD_SIGNAL"] = signal_line
    out["MACD_HIST"] = hist

    out["ROC_12"] = momentum.roc(close, params.roc_period)
    out["ATR_14"] = volatility.atr(high, low, close, params.atr_period)

    bb_upper, bb_middle, bb_lower = volatility.bollinger_bands(close, params.bb_period, params.bb_std)
    out["BB_UPPER"] = bb_upper
    out["BB_MIDDLE"] = bb_middle
    out["BB_LOWER"] = bb_lower

    out["HIST_VOL_20"] = volatility.historical_volatility(close, HIST_VOL_WINDOW, HIST_VOL_ANNUALIZATION)

    out["VOLUME_SMA_20"] = volume_ind.volume_sma(vol, params.volume_sma_period)
    out["REL_VOLUME"] = volume_ind.relative_volume(vol, params.volume_sma_period)

    out["DIST_SMA_20_PCT"] = (close - out["SMA_20"]) / out["SMA_20"] * 100.0
    out["DIST_SMA_50_PCT"] = (close - out["SMA_50"]) / out["SMA_50"] * 100.0
    out["DIST_SMA_200_PCT"] = (close - out["SMA_200"]) / out["SMA_200"] * 100.0

    return out
