"""Ticker input validation."""
import re

from app.config import TICKER_REGEX

_TICKER_RE = re.compile(TICKER_REGEX)


class InvalidTickerError(ValueError):
    """Raised when a ticker fails basic format validation."""


def normalize_and_validate_ticker(raw: str) -> str:
    """Normalize a user-supplied ticker string and validate its shape.

    This only checks *format* (empty, whitespace, disallowed characters,
    length). It does NOT confirm the ticker exists on Yahoo Finance -
    that is checked later against real retrieved data, never assumed here.
    """
    if raw is None:
        raise InvalidTickerError("Ticker must not be empty.")

    candidate = raw.strip().upper()

    if not candidate:
        raise InvalidTickerError("Ticker must not be empty.")

    if len(candidate) > 12:
        raise InvalidTickerError("Ticker is too long to be valid.")

    if not _TICKER_RE.match(candidate):
        raise InvalidTickerError(
            "Ticker contains invalid characters. Use letters, digits, '.', '-', '^' or '='."
        )

    return candidate
