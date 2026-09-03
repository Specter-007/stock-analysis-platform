"""Central mapping from internal exceptions to clean HTTP responses. No raw
Python tracebacks are ever exposed to API clients.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.exceptions import DataUnavailableError, InsufficientHistoryError, TickerNotFoundError
from app.utils.validation import InvalidTickerError

logger = logging.getLogger(__name__)


def _error_body(error_type: str, detail: str) -> dict:
    return {"error_type": error_type, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidTickerError)
    async def invalid_ticker_handler(request: Request, exc: InvalidTickerError):
        return JSONResponse(status_code=400, content=_error_body("INVALID_TICKER", str(exc)))

    @app.exception_handler(TickerNotFoundError)
    async def ticker_not_found_handler(request: Request, exc: TickerNotFoundError):
        return JSONResponse(
            status_code=404,
            content=_error_body(
                "TICKER_NOT_FOUND",
                f"Yahoo Finance did not return usable data for '{exc.ticker}'. "
                "Double-check the symbol and try again.",
            ),
        )

    @app.exception_handler(InsufficientHistoryError)
    async def insufficient_history_handler(request: Request, exc: InsufficientHistoryError):
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "INSUFFICIENT_HISTORY",
                f"'{exc.ticker}' does not have enough historical data to calculate the "
                f"requested indicators ({exc.available} of {exc.required} required candles available).",
            ),
        )

    @app.exception_handler(DataUnavailableError)
    async def data_unavailable_handler(request: Request, exc: DataUnavailableError):
        logger.warning("Data unavailable for %s: %s", exc.ticker, exc.reason)
        return JSONResponse(
            status_code=503,
            content=_error_body(
                "DATA_UNAVAILABLE",
                "Market data could not be retrieved right now. Please try again shortly.",
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred. Please try again."),
        )
