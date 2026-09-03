"""OHLCV data-quality validation, run on every history fetch before
indicators are computed. This never repairs or substitutes values - it only
detects and reports. A caller decides whether an issue is survivable
(logged/flagged) or fatal (raise `DataUnavailableError`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# A gap wider than this many calendar days between consecutive daily candles
# is flagged as suspicious (covers long weekends/holidays without false
# positives; a genuine multi-week trading halt or thin/illiquid ticker would
# exceed it).
SUSPICIOUS_GAP_DAYS = 10

# If the single most-recent candle is older than this many calendar days
# while being served as "current" data, it's flagged stale rather than
# silently treated as fresh.
STALE_DATA_DAYS = 5


@dataclass
class DataQualityReport:
    is_valid: bool  # False only when the data is fundamentally unusable
    issues: list[str] = field(default_factory=list)
    duplicate_timestamps: int = 0
    missing_ohlc_values: int = 0
    negative_prices: int = 0
    invalid_high_low: int = 0
    invalid_volume: int = 0
    suspicious_gaps: int = 0
    is_stale: bool = False

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "duplicate_timestamps": self.duplicate_timestamps,
            "missing_ohlc_values": self.missing_ohlc_values,
            "negative_prices": self.negative_prices,
            "invalid_high_low": self.invalid_high_low,
            "invalid_volume": self.invalid_volume,
            "suspicious_gaps": self.suspicious_gaps,
            "is_stale": self.is_stale,
        }


def validate_ohlcv(df: pd.DataFrame, now: pd.Timestamp | None = None) -> DataQualityReport:
    """Validates a raw OHLCV DataFrame (columns: Open, High, Low, Close,
    Volume; DatetimeIndex). Does not mutate `df`.
    """
    issues: list[str] = []

    if df is None or df.empty:
        return DataQualityReport(is_valid=False, issues=["No data to validate."])

    is_valid = True

    if not df.index.is_monotonic_increasing:
        issues.append("Timestamps are not in chronological order.")
        is_valid = False

    duplicate_count = int(df.index.duplicated().sum())
    if duplicate_count > 0:
        issues.append(f"{duplicate_count} duplicate timestamp(s) found.")

    ohlc_cols = [c for c in ("Open", "High", "Low", "Close") if c in df.columns]
    missing_count = int(df[ohlc_cols].isna().sum().sum()) if ohlc_cols else 0
    if missing_count > 0:
        issues.append(f"{missing_count} missing OHLC value(s).")

    negative_count = 0
    if ohlc_cols:
        negative_count = int((df[ohlc_cols] < 0).sum().sum())
    if negative_count > 0:
        issues.append(f"{negative_count} negative price value(s) found.")
        is_valid = False

    invalid_high_low = 0
    if {"High", "Low", "Open", "Close"} <= set(df.columns):
        clean = df.dropna(subset=["High", "Low", "Open", "Close"])
        invalid_high_low = int(
            (
                (clean["High"] < clean["Low"])
                | (clean["High"] < clean["Open"])
                | (clean["High"] < clean["Close"])
                | (clean["Low"] > clean["Open"])
                | (clean["Low"] > clean["Close"])
            ).sum()
        )
    if invalid_high_low > 0:
        issues.append(f"{invalid_high_low} row(s) with an impossible High/Low relationship.")

    invalid_volume = 0
    if "Volume" in df.columns:
        invalid_volume = int((df["Volume"] < 0).sum())
    if invalid_volume > 0:
        issues.append(f"{invalid_volume} row(s) with negative volume.")

    suspicious_gaps = 0
    if len(df.index) > 1:
        gaps = df.index.to_series().diff().dt.days.dropna()
        suspicious_gaps = int((gaps > SUSPICIOUS_GAP_DAYS).sum())
    if suspicious_gaps > 0:
        issues.append(f"{suspicious_gaps} gap(s) wider than {SUSPICIOUS_GAP_DAYS} calendar days between candles.")

    is_stale = False
    if now is not None and len(df.index) > 0:
        latest = df.index[-1]
        now_cmp = now.tz_convert(latest.tz) if (latest.tzinfo is not None and now.tzinfo is not None) else now
        try:
            age_days = (now_cmp - latest).days
            is_stale = age_days > STALE_DATA_DAYS
        except TypeError:
            is_stale = False
        if is_stale:
            issues.append(f"Latest candle is {age_days} day(s) old - data may be stale.")

    return DataQualityReport(
        is_valid=is_valid,
        issues=issues,
        duplicate_timestamps=duplicate_count,
        missing_ohlc_values=missing_count,
        negative_prices=negative_count,
        invalid_high_low=invalid_high_low,
        invalid_volume=invalid_volume,
        suspicious_gaps=suspicious_gaps,
        is_stale=is_stale,
    )
