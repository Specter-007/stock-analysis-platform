import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes_backtest import router as backtest_router
from app.api.routes_market import router as market_router
from app.api.routes_model import router as model_router
from app.api.routes_paper_trading import router as paper_trading_router
from app.api.routes_stock import router as stock_router
from app.config import MODEL_VERSION_CURRENT
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

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(stock_router)
app.include_router(backtest_router)
app.include_router(market_router)
app.include_router(model_router)
app.include_router(paper_trading_router)


@app.get("/api/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
