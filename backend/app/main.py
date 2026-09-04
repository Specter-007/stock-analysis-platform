import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes_auth import router as auth_router
from app.api.routes_backtest import router as backtest_router
from app.api.routes_comparison import router as comparison_router
from app.api.routes_experiments import router as experiments_router
from app.api.routes_market import router as market_router
from app.api.routes_model import router as model_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_paper_trading import router as paper_trading_router
from app.api.routes_settings import router as settings_router
from app.api.routes_stock import router as stock_router
from app.api.routes_support import router as support_router
from app.api.routes_watchlist import router as watchlist_router
from app.config import EXPERIMENTS_DATA_DIR, MODEL_VERSION_CURRENT, PAPER_TRADING_DATA_DIR
from app.rate_limit import limiter
from app.security_headers import SecurityHeadersMiddleware
from app.settings import CORS_ALLOWED_ORIGINS
from app.utils.logging_config import configure_logging

configure_logging(logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stock Analyst API",
    description=(
        "Deterministic, rules-based stock research and technical-analysis API. "
        "Real market data via Yahoo Finance (yfinance). Not a financial adviser."
    ),
    version=f"2.0.0 (quant model v{MODEL_VERSION_CURRENT})",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS_ALLOWED_ORIGINS is validated at import time (app.settings) to never be
# "*" when APP_ENV=production and credentials are allowed - a wildcard origin
# combined with allow_credentials=True would let any site read a signed-in
# user's cookies via a cross-origin fetch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(stock_router)
app.include_router(backtest_router)
app.include_router(market_router)
app.include_router(model_router)
app.include_router(paper_trading_router)
app.include_router(watchlist_router)
app.include_router(comparison_router)
app.include_router(experiments_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(support_router)


@app.get("/api/health", tags=["meta"])
def health_check():
    """Deliberately cheap: checks that each JSON data directory is
    writable (a real, near-instant filesystem check), never a live Yahoo
    Finance call - a health check that depends on an external network
    call would make an unrelated outage look like this service is down.
    """
    persistence: dict[str, str] = {}
    for name, data_dir in (
        ("paper_trading", PAPER_TRADING_DATA_DIR),
        ("watchlists", "data/watchlists"),
        ("experiments", EXPERIMENTS_DATA_DIR),
    ):
        try:
            path = Path(data_dir)
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".health_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            persistence[name] = "ok"
        except OSError as exc:
            persistence[name] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in persistence.values()) else "degraded"
    return {
        "status": overall,
        "model_version": MODEL_VERSION_CURRENT,
        "persistence": persistence,
        "data_service": "not checked (health checks never call Yahoo Finance - see DATA_UNAVAILABLE handling on data endpoints instead)",
    }
