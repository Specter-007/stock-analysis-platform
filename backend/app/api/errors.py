"""Central mapping from internal exceptions to clean HTTP responses. No raw
Python tracebacks are ever exposed to API clients.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.dependencies import CsrfError
from app.auth.exceptions import (
    AccountNotActiveError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    NotAuthenticatedError,
    ResourceNotFoundError,
)
from app.paper_trading.service import PaperTradingError
from app.services.exceptions import DataUnavailableError, InsufficientHistoryError, TickerNotFoundError
from app.utils.validation import InvalidTickerError
from app.watchlist.service import WatchlistError

logger = logging.getLogger(__name__)


def _error_body(error_type: str, detail: str) -> dict:
    return {"error_type": error_type, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PaperTradingError)
    async def paper_trading_error_handler(request: Request, exc: PaperTradingError):
        return JSONResponse(status_code=400, content=_error_body("PAPER_TRADING_ERROR", str(exc)))

    @app.exception_handler(WatchlistError)
    async def watchlist_error_handler(request: Request, exc: WatchlistError):
        return JSONResponse(status_code=400, content=_error_body("WATCHLIST_ERROR", str(exc)))

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

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
        return JSONResponse(status_code=401, content=_error_body("INVALID_CREDENTIALS", str(exc)))

    @app.exception_handler(AccountNotActiveError)
    async def account_not_active_handler(request: Request, exc: AccountNotActiveError):
        return JSONResponse(status_code=401, content=_error_body("INVALID_CREDENTIALS", str(exc)))

    @app.exception_handler(EmailAlreadyRegisteredError)
    async def email_already_registered_handler(request: Request, exc: EmailAlreadyRegisteredError):
        return JSONResponse(status_code=409, content=_error_body("EMAIL_ALREADY_REGISTERED", str(exc)))

    @app.exception_handler(InvalidOrExpiredTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidOrExpiredTokenError):
        return JSONResponse(status_code=400, content=_error_body("INVALID_OR_EXPIRED_TOKEN", str(exc)))

    @app.exception_handler(NotAuthenticatedError)
    async def not_authenticated_handler(request: Request, exc: NotAuthenticatedError):
        return JSONResponse(status_code=401, content=_error_body("NOT_AUTHENTICATED", str(exc)))

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(status_code=404, content=_error_body("NOT_FOUND", str(exc) or "Not found."))

    @app.exception_handler(CsrfError)
    async def csrf_error_handler(request: Request, exc: CsrfError):
        return JSONResponse(status_code=403, content=_error_body("CSRF_ERROR", str(exc)))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred. Please try again."),
        )
