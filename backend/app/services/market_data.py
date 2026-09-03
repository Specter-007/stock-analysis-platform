"""Thin, defensive wrapper around yfinance.

Every function here talks to Yahoo Finance (through yfinance) or to the
in-memory cache - never to hardcoded/fake data. Failures are translated into
the typed exceptions in `exceptions.py` so API routes can map them to clean
HTTP responses instead of leaking stack traces.
"""
from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

from app.config import (
    CACHE_TTL_HISTORY_SECONDS,
    CACHE_TTL_INFO_SECONDS,
    CACHE_TTL_QUOTE_SECONDS,
    CACHE_TTL_SEARCH_SECONDS,
    DATA_SOURCE_LABEL,
    MAJOR_INDEXES,
)
from app.services.cache import cache
from app.services.data_quality import validate_ohlcv
from app.services.exceptions import DataUnavailableError, TickerNotFoundError
from app.utils import timeutils

logger = logging.getLogger(__name__)

INTRADAY_PERIODS = {
    "1D": ("2d", "5m"),
    "5D": ("5d", "15m"),
}

# Calendar-day lookback applied when trimming the full daily series down to
# a requested chart range. Approximate (calendar, not trading) days is fine
# here since it only controls how much of the already-fetched series is shown.
DAILY_RANGE_LOOKBACK_DAYS = {
    "1M": 31,
    "3M": 93,
    "6M": 186,
    "1Y": 366,
    "2Y": 732,
    "5Y": 1827,
    "MAX": None,
}

# The single daily OHLCV series every indicator, signal, and backtest
# computation is derived from. Fetched at full length so long-window
# indicators (e.g. SMA 200) stay accurate even when the visible chart
# range is short.
FULL_HISTORY_PERIOD = "max"
FULL_HISTORY_INTERVAL = "1d"


def _clean_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


@dataclass
class DataMeta:
    data_source: str = DATA_SOURCE_LABEL
    data_status: str = "UNAVAILABLE"
    retrieved_at: str = field(default_factory=lambda: timeutils.to_iso(timeutils.utc_now()))
    latest_market_timestamp: str | None = None
    market_status: str | None = None
    timeframe: str = "Daily"
    data_quality: dict | None = None

    def to_dict(self) -> dict:
        return {
            "data_source": self.data_source,
            "data_status": self.data_status,
            "retrieved_at": self.retrieved_at,
            "latest_market_timestamp": self.latest_market_timestamp,
            "market_status": self.market_status,
            "timeframe": self.timeframe,
            "data_quality": self.data_quality,
        }


def _quote_data_status(market_stat: str) -> str:
    if market_stat == "OPEN":
        return "DELAYED"
    return "MARKET_CLOSED"


def _get_ticker(ticker: str) -> yf.Ticker:
    return yf.Ticker(ticker)


def fetch_history_raw(ticker: str, period: str, interval: str) -> pd.DataFrame:
    cache_key = f"history:{ticker}:{period}:{interval}"

    def _load() -> pd.DataFrame:
        try:
            df = _get_ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:  # yfinance raises a variety of network/parse errors
            logger.warning("yfinance history fetch failed for %s: %s", ticker, exc)
            raise DataUnavailableError(ticker, "network or parsing error") from exc
        return df

    return cache.get_or_set(cache_key, CACHE_TTL_HISTORY_SECONDS, _load)


def fetch_info_raw(ticker: str) -> dict:
    cache_key = f"info:{ticker}"

    def _load() -> dict:
        try:
            info = _get_ticker(ticker).info or {}
        except Exception as exc:
            logger.warning("yfinance info fetch failed for %s: %s", ticker, exc)
            info = {}
        return info

    return cache.get_or_set(cache_key, CACHE_TTL_INFO_SECONDS, _load)


def fetch_fast_info_raw(ticker: str) -> dict:
    cache_key = f"fastinfo:{ticker}"

    def _load() -> dict:
        try:
            fi = _get_ticker(ticker).fast_info
            return dict(fi) if fi else {}
        except Exception as exc:
            logger.warning("yfinance fast_info fetch failed for %s: %s", ticker, exc)
            return {}

    return cache.get_or_set(cache_key, CACHE_TTL_QUOTE_SECONDS, _load)


def get_full_daily_history(ticker: str) -> tuple[pd.DataFrame, DataMeta]:
    """The single full-length daily OHLCV series backing indicators, the
    signal engine, backtesting, and (sliced) the daily-interval chart ranges.
    """
    df = fetch_history_raw(ticker, FULL_HISTORY_PERIOD, FULL_HISTORY_INTERVAL)

    if df is None or df.empty:
        info = fetch_info_raw(ticker)
        if not info or not (info.get("shortName") or info.get("longName")):
            raise TickerNotFoundError(ticker)
        raise DataUnavailableError(ticker, "no historical candles returned")

    df = df.dropna(how="all")

    quality = validate_ohlcv(df, now=pd.Timestamp(timeutils.utc_now()))
    if not quality.is_valid:
        logger.warning("Data quality check failed for %s: %s", ticker, "; ".join(quality.issues))
        raise DataUnavailableError(ticker, "data failed quality validation: " + "; ".join(quality.issues))

    latest_ts = df.index[-1].to_pydatetime()
    m_status = timeutils.market_status()
    data_status = "STALE" if quality.is_stale else "HISTORICAL"

    meta = DataMeta(
        data_status=data_status,
        latest_market_timestamp=timeutils.to_iso(latest_ts),
        market_status=m_status,
        timeframe="Daily",
        data_quality=quality.to_dict(),
    )
    return df, meta


@dataclass
class ChartHistoryResult:
    full_df: pd.DataFrame  # complete daily series, used to seed long-window SMAs
    visible_df: pd.DataFrame  # the slice actually shown to the user for this range
    meta: DataMeta
    is_daily: bool  # whether SMA overlays are meaningful for this granularity


def get_chart_history(ticker: str, range_key: str) -> ChartHistoryResult:
    if range_key in INTRADAY_PERIODS:
        period, interval = INTRADAY_PERIODS[range_key]
        df = fetch_history_raw(ticker, period, interval)
        if df is None or df.empty:
            info = fetch_info_raw(ticker)
            if not info or not (info.get("shortName") or info.get("longName")):
                raise TickerNotFoundError(ticker)
            raise DataUnavailableError(ticker, "no intraday candles returned")
        df = df.dropna(how="all")
        latest_ts = df.index[-1].to_pydatetime()
        m_status = timeutils.market_status()
        meta = DataMeta(
            data_status=_quote_data_status(m_status),
            latest_market_timestamp=timeutils.to_iso(latest_ts),
            market_status=m_status,
            timeframe=interval,
        )
        return ChartHistoryResult(full_df=df, visible_df=df, meta=meta, is_daily=False)

    full_df, meta = get_full_daily_history(ticker)
    lookback_days = DAILY_RANGE_LOOKBACK_DAYS.get(range_key)
    if lookback_days is None:
        visible = full_df
    else:
        cutoff = full_df.index[-1] - pd.Timedelta(days=lookback_days)
        visible = full_df[full_df.index >= cutoff]
        if visible.empty:
            visible = full_df

    return ChartHistoryResult(full_df=full_df, visible_df=visible, meta=meta, is_daily=True)


def get_overview(ticker: str) -> tuple[dict, DataMeta]:
    info = fetch_info_raw(ticker)
    fast = fetch_fast_info_raw(ticker)

    has_identity = bool(info.get("shortName") or info.get("longName"))
    has_price = _clean_float(fast.get("lastPrice")) is not None or _clean_float(
        info.get("currentPrice")
    ) is not None

    if not has_identity and not has_price:
        raise TickerNotFoundError(ticker)

    last_price = _clean_float(fast.get("lastPrice")) or _clean_float(info.get("currentPrice"))
    prev_close = _clean_float(fast.get("previousClose")) or _clean_float(info.get("previousClose"))
    day_high = _clean_float(fast.get("dayHigh")) or _clean_float(info.get("dayHigh"))
    day_low = _clean_float(fast.get("dayLow")) or _clean_float(info.get("dayLow"))
    volume = fast.get("lastVolume") or info.get("volume")
    avg_volume = fast.get("threeMonthAverageVolume") or info.get("averageVolume")

    change = None
    change_pct = None
    if last_price is not None and prev_close:
        change = last_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else None

    overview = {
        "ticker": ticker,
        "company_name": info.get("longName") or info.get("shortName") or "N/A",
        "exchange": fast.get("exchange") or info.get("exchange") or "N/A",
        "currency": fast.get("currency") or info.get("currency") or "N/A",
        "sector": info.get("sector") or "N/A",
        "industry": info.get("industry") or "N/A",
        "last_price": last_price,
        "previous_close": prev_close,
        "change": change,
        "change_percent": change_pct,
        "day_high": day_high,
        "day_low": day_low,
        "fifty_two_week_high": _clean_float(fast.get("yearHigh")) or _clean_float(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": _clean_float(fast.get("yearLow")) or _clean_float(info.get("fiftyTwoWeekLow")),
        "market_cap": fast.get("marketCap") or info.get("marketCap"),
        "volume": volume,
        "average_volume": avg_volume,
        "website": info.get("website") or "N/A",
        "description": info.get("longBusinessSummary") or "N/A",
    }

    m_status = timeutils.market_status()
    meta = DataMeta(
        data_status=_quote_data_status(m_status),
        latest_market_timestamp=timeutils.to_iso(timeutils.utc_now()),
        market_status=m_status,
        timeframe="Real-time quote (delayed)" if m_status == "OPEN" else "Last session close",
    )
    return overview, meta


def search_symbols(query: str, max_results: int = 8) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    cache_key = f"search:{query.lower()}:{max_results}"

    def _load() -> list[dict]:
        try:
            results = yf.Search(query, max_results=max_results).quotes
        except Exception as exc:
            logger.warning("yfinance search failed for %r: %s", query, exc)
            return []
        cleaned = []
        for r in results or []:
            symbol = r.get("symbol")
            if not symbol:
                continue
            cleaned.append(
                {
                    "symbol": symbol,
                    "name": r.get("longname") or r.get("shortname") or symbol,
                    "exchange": r.get("exchDisp") or r.get("exchange") or "N/A",
                    "type": r.get("typeDisp") or r.get("quoteType") or "N/A",
                }
            )
        return cleaned

    return cache.get_or_set(cache_key, CACHE_TTL_SEARCH_SECONDS, _load)


def _fetch_quote_snapshot(symbol: str) -> dict | None:
    """One ticker's fast-info quote, or None if unavailable. Designed to be
    called concurrently across many symbols (see ThreadPoolExecutor usage
    below) since each call is a blocking network request.
    """
    try:
        fast = fetch_fast_info_raw(symbol)
        last_price = _clean_float(fast.get("lastPrice"))
        prev_close = _clean_float(fast.get("previousClose"))
        if last_price is None:
            return None
        change = last_price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
        return {"last_price": last_price, "change": change, "change_percent": change_pct}
    except Exception as exc:
        logger.warning("Failed to fetch quote for %s: %s", symbol, exc)
        return None


def get_market_indexes() -> tuple[list[dict], DataMeta]:
    m_status = timeutils.market_status()
    symbols = list(MAJOR_INDEXES.items())

    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as pool:
        snapshots = list(pool.map(lambda item: _fetch_quote_snapshot(item[0]), symbols))

    results = []
    any_success = False
    for (symbol, name), snap in zip(symbols, snapshots):
        if snap is None:
            results.append({"symbol": symbol, "name": name, "status": "UNAVAILABLE"})
        else:
            results.append({"symbol": symbol, "name": name, "status": "OK", **snap})
            any_success = True

    meta = DataMeta(
        data_status=_quote_data_status(m_status) if any_success else "UNAVAILABLE",
        latest_market_timestamp=timeutils.to_iso(timeutils.utc_now()),
        market_status=m_status,
        timeframe="Real-time quote (delayed)" if m_status == "OPEN" else "Last session close",
    )
    return results, meta


def get_movers(tickers: list[str]) -> tuple[list[dict], DataMeta]:
    """Fetch quote snapshots for a fixed watch-list of tickers (concurrently,
    since each is an independent blocking network call), ranked by daily
    percent change, so the Markets page can show real gainers/losers without
    a paid screener API.
    """
    m_status = timeutils.market_status()

    with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
        snapshots = list(pool.map(_fetch_quote_snapshot, tickers))

    rows = []
    for ticker, snap in zip(tickers, snapshots):
        if snap is None or snap.get("change") is None:
            continue
        rows.append({"symbol": ticker, **snap})

    meta = DataMeta(
        data_status=_quote_data_status(m_status) if rows else "UNAVAILABLE",
        latest_market_timestamp=timeutils.to_iso(timeutils.utc_now()),
        market_status=m_status,
        timeframe="Real-time quote (delayed)" if m_status == "OPEN" else "Last session close",
    )
    return rows, meta
