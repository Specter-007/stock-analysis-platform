import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.errors import register_exception_handlers
from app.api.routes_admin import router as admin_router
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
from app.body_size_limit import BodySizeLimitMiddleware
from app.config import MODEL_VERSION_CURRENT
from app.db.base import get_db
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
app.add_middleware(BodySizeLimitMiddleware)

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
app.include_router(admin_router)


@app.get("/api/health", tags=["meta"])
def health_check():
    """Pure liveness: confirms the process itself is up and responding.
    Deliberately makes no database or network call - a health check that
    depends on a dependency's availability would make an unrelated
    Postgres or Yahoo Finance outage look like this service itself is
    down. See /api/health/ready for a check that includes the database.
    """
    return {
        "status": "ok",
        "model_version": MODEL_VERSION_CURRENT,
        "data_service": "not checked (health checks never call Yahoo Finance - see DATA_UNAVAILABLE handling on data endpoints instead)",
    }


@app.get("/api/health/ready", tags=["meta"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness: additionally confirms the database is actually reachable
    (a real `SELECT 1`, not an assumption) - suitable for a deployment
    orchestrator deciding whether to route traffic to this instance.
    """
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as exc:  # noqa: BLE001 - report any DB failure, never crash the readiness probe itself
        database_status = f"error: {exc}"

    overall = "ok" if database_status == "ok" else "not_ready"
    return {
        "status": overall,
        "model_version": MODEL_VERSION_CURRENT,
        "database": database_status,
    }
