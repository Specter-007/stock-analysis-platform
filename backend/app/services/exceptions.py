class TickerNotFoundError(Exception):
    """Yahoo Finance returned no usable data for this ticker."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"No usable data returned for ticker '{ticker}'.")


class DataUnavailableError(Exception):
    """Yahoo Finance is unreachable, timed out, or returned malformed data."""

    def __init__(self, ticker: str, reason: str = ""):
        self.ticker = ticker
        self.reason = reason
        message = f"Market data could not be retrieved for '{ticker}'."
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class InsufficientHistoryError(Exception):
    """Not enough historical candles to compute the requested indicators."""

    def __init__(self, ticker: str, available: int, required: int):
        self.ticker = ticker
        self.available = available
        self.required = required
        super().__init__(
            f"'{ticker}' has only {available} historical candles; "
            f"{required} are required for this calculation."
        )
