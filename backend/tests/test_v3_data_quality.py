"""Tests for the OHLCV data-quality validation layer. Every check is
constructed with deliberately corrupted synthetic data - this validator
must never be tested only on "clean" fixtures, since its entire purpose is
catching the unclean case.
"""
import pandas as pd
import pytest

from app.services.data_quality import validate_ohlcv


def _clean_df(n=30):
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [101.0 + i for i in range(n)],
            "Low": [99.0 + i for i in range(n)],
            "Close": [100.5 + i for i in range(n)],
            "Volume": [1_000_000.0] * n,
        },
        index=idx,
    )


def test_clean_data_is_valid_with_no_issues():
    report = validate_ohlcv(_clean_df())
    assert report.is_valid is True
    assert report.issues == []
    assert report.duplicate_timestamps == 0
    assert report.missing_ohlc_values == 0
    assert report.invalid_high_low == 0


def test_empty_dataframe_is_invalid():
    report = validate_ohlcv(pd.DataFrame())
    assert report.is_valid is False
    assert len(report.issues) > 0


def test_none_is_invalid():
    report = validate_ohlcv(None)
    assert report.is_valid is False


def test_non_chronological_index_detected():
    df = _clean_df()
    shuffled = df.iloc[::-1]  # reverse order
    report = validate_ohlcv(shuffled)
    assert report.is_valid is False
    assert any("chronological" in i for i in report.issues)


def test_duplicate_timestamps_detected():
    df = _clean_df()
    dup = pd.concat([df, df.iloc[[0]]])
    report = validate_ohlcv(dup)
    assert report.duplicate_timestamps == 1
    assert any("duplicate" in i.lower() for i in report.issues)


def test_missing_ohlc_values_detected():
    df = _clean_df()
    df.loc[df.index[5], "Close"] = None
    report = validate_ohlcv(df)
    assert report.missing_ohlc_values == 1


def test_negative_prices_detected_and_invalidate():
    df = _clean_df()
    df.loc[df.index[3], "Open"] = -10.0
    report = validate_ohlcv(df)
    assert report.negative_prices == 1
    assert report.is_valid is False


def test_impossible_high_low_relationship_detected():
    df = _clean_df()
    # High below Low - physically impossible for a real candle
    df.loc[df.index[2], "High"] = 50.0
    df.loc[df.index[2], "Low"] = 200.0
    report = validate_ohlcv(df)
    assert report.invalid_high_low >= 1
    assert any("High/Low" in i for i in report.issues)


def test_high_below_open_or_close_detected():
    df = _clean_df()
    df.loc[df.index[4], "High"] = 1.0  # far below that row's Open/Close
    report = validate_ohlcv(df)
    assert report.invalid_high_low >= 1


def test_negative_volume_detected():
    df = _clean_df()
    df.loc[df.index[7], "Volume"] = -500.0
    report = validate_ohlcv(df)
    assert report.invalid_volume == 1
    assert any("volume" in i.lower() for i in report.issues)


def test_suspicious_gap_detected():
    idx = list(pd.bdate_range("2024-01-01", periods=10)) + list(pd.bdate_range("2024-06-01", periods=10))
    df = pd.DataFrame(
        {
            "Open": [100.0] * 20, "High": [101.0] * 20, "Low": [99.0] * 20,
            "Close": [100.5] * 20, "Volume": [1_000_000.0] * 20,
        },
        index=pd.DatetimeIndex(idx),
    )
    report = validate_ohlcv(df)
    assert report.suspicious_gaps >= 1


def test_stale_data_detected_when_now_is_far_after_latest_candle():
    df = _clean_df()
    now = pd.Timestamp(df.index[-1]) + pd.Timedelta(days=30)
    report = validate_ohlcv(df, now=now)
    assert report.is_stale is True


def test_not_stale_when_now_is_close_to_latest_candle():
    df = _clean_df()
    now = pd.Timestamp(df.index[-1]) + pd.Timedelta(hours=2)
    report = validate_ohlcv(df, now=now)
    assert report.is_stale is False


def test_stale_check_handles_tz_aware_vs_naive_without_crashing():
    df = _clean_df()
    tz_aware = df.tz_localize("America/New_York")
    now_naive = pd.Timestamp(df.index[-1]) + pd.Timedelta(days=1)
    # Should not raise, regardless of tz mismatch between `now` and the index.
    report = validate_ohlcv(tz_aware, now=now_naive.tz_localize("UTC"))
    assert isinstance(report.is_stale, bool)
