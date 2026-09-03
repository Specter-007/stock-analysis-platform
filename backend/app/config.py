"""Central configuration constants for the signal engine, cache, and API."""

DATA_SOURCE_LABEL = "Yahoo Finance via yfinance"

DISCLAIMER = (
    "This is a research and educational analysis tool, not a financial adviser. "
    "It does not guarantee returns. BUY/HOLD/SELL is the output of a deterministic "
    "quantitative model, not personalized financial advice. Verify important "
    "financial information independently before making decisions."
)

# --- Cache ---
CACHE_TTL_QUOTE_SECONDS = 30
CACHE_TTL_HISTORY_SECONDS = 300
CACHE_TTL_INFO_SECONDS = 3600
CACHE_TTL_SEARCH_SECONDS = 3600

# --- Indicator windows ---
SMA_WINDOWS = (20, 50, 100, 200)
EMA_WINDOWS = (20, 50)
RSI_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ROC_WINDOW = 12
ATR_WINDOW = 14
BOLLINGER_WINDOW = 20
BOLLINGER_STD = 2
HIST_VOL_WINDOW = 20
HIST_VOL_ANNUALIZATION = 252
VOLUME_SMA_WINDOW = 20

# Minimum daily candles required to compute the full indicator suite reliably
# (200-day SMA is the longest window; require some cushion beyond it).
MIN_HISTORY_FOR_FULL_INDICATORS = 210
# Absolute minimum candles needed to attempt any indicator computation at all.
MIN_HISTORY_FOR_PARTIAL_INDICATORS = 20

# --- Signal score normalization thresholds (0-100) ---
SCORE_STRONG_BUY = 80
SCORE_BUY = 65
SCORE_HOLD_LOW = 45  # >= this and < SCORE_BUY => HOLD
SCORE_SELL_LOW = 30  # >= this and < SCORE_HOLD_LOW => SELL
# below SCORE_SELL_LOW => STRONG SELL

SIGNAL_TIMEFRAME_DAILY = "Daily"

# --- Backtesting defaults ---
DEFAULT_INITIAL_CAPITAL = 10_000.0
DEFAULT_TRANSACTION_COST_BPS = 5.0  # 0.05% per trade, in basis points
DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_BENCHMARK_TICKER = "SPY"
RISK_FREE_RATE_ANNUAL = 0.0  # used for Sharpe ratio; documented assumption

# --- Ticker validation ---
TICKER_REGEX = r"^[A-Za-z0-9\.\-\^=]{1,12}$"

POPULAR_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META"]
MOVERS_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META",
    "NFLX", "AMD", "INTC", "JPM", "V", "WMT", "DIS",
]
MAJOR_INDEXES = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones Industrial Average",
    "^IXIC": "NASDAQ Composite",
    "^RUT": "Russell 2000",
    "^VIX": "CBOE Volatility Index",
}
