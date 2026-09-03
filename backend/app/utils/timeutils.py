"""Timestamp and market-hours helpers.

All timestamps returned to API consumers are timezone-aware ISO-8601 strings
in UTC unless documented otherwise, so the frontend never has to guess.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

# NYSE regular session, local (America/New_York) time.
MARKET_OPEN = dt.time(9, 30)
MARKET_CLOSE = dt.time(16, 0)

# A small fixed set of full-day NYSE holidays is intentionally NOT hardcoded
# here long-term (holiday calendars drift year to year). Weekday + session
# time is used as the primary signal; yfinance's own returned data freshness
# is the authoritative cross-check performed by the caller.


def utc_now() -> dt.datetime:
    return dt.datetime.now(tz=UTC)


def to_iso(timestamp: dt.datetime | None) -> str | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat()


def market_status(now: dt.datetime | None = None) -> str:
    """Return one of: 'OPEN', 'CLOSED', 'PRE_MARKET', 'AFTER_HOURS', 'WEEKEND'.

    This is a best-effort classification based on NYSE regular-session hours
    in America/New_York time. It does not account for market holidays.
    """
    now = now or utc_now()
    local = now.astimezone(NY_TZ)

    if local.weekday() >= 5:
        return "WEEKEND"

    if MARKET_OPEN <= local.time() <= MARKET_CLOSE:
        return "OPEN"
    if local.time() < MARKET_OPEN:
        return "PRE_MARKET"
    return "AFTER_HOURS"


def is_stale_daily_candle(latest_candle_date: dt.date, now: dt.datetime | None = None) -> bool:
    """A daily candle is considered stale if it's more than 4 calendar days old
    (covers a long weekend / single missed holiday) while markets are open now.
    """
    now = now or utc_now()
    today = now.astimezone(NY_TZ).date()
    return (today - latest_candle_date).days > 4
