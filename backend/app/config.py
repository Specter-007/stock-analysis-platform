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

# --- Model versioning ---
# v1.0 (legacy): raw score normalized against the min/max of ONLY the factors
#   available for a given stock. Mathematically valid but means an identical
#   factor condition (e.g. "price above 200-day SMA") can contribute a
#   different normalized amount depending on how many other factors that
#   ticker happened to have data for - an unintuitive property when comparing
#   scores across tickers.
# v1.1 (current/default): raw score normalized against the FIXED theoretical
#   min/max achievable across all 8 possible factors, so the same factor
#   condition always contributes the same normalized amount for every
#   ticker. Preferred for cross-ticker comparison; v1.0 is kept only for
#   backward-compatible reference, never silently swapped into v1.0 results.
MODEL_VERSION_LEGACY = "1.0"
MODEL_VERSION_CURRENT = "1.1"
SUPPORTED_MODEL_VERSIONS = (MODEL_VERSION_LEGACY, MODEL_VERSION_CURRENT)

MODEL_VERSION_NOTES = {
    MODEL_VERSION_LEGACY: (
        "Per-ticker dynamic normalization: the raw score is normalized against the "
        "min/max of only the factors available for that specific stock."
    ),
    MODEL_VERSION_CURRENT: (
        "Fixed normalization: the raw score is normalized against the theoretical "
        "min/max across all 8 possible factors, so the same factor condition always "
        "contributes the same normalized amount regardless of ticker."
    ),
}

# Theoretical min/max of the sum of every factor's own min/max points
# (3 trend: +-15,+-15,+-10; momentum: RSI -10..+10, MACD +-15, ROC +-5;
# volume +-10; volatility -10..+5). Used only by model v1.1.
RAW_SCORE_FIXED_MIN = -90.0
RAW_SCORE_FIXED_MAX = 85.0

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

# --- Signal history / stability ---
SIGNAL_HISTORY_LOOKBACK_SESSIONS = 60
SIGNAL_STABILITY_WINDOW = 10

# --- Market regime (deterministic, benchmark-based) ---
MARKET_REGIME_BENCHMARK = "SPY"

# --- Relative strength ---
RELATIVE_STRENGTH_PERIODS = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252}
RELATIVE_STRENGTH_STRONG_THRESHOLD_PP = 5.0   # percentage points above benchmark
RELATIVE_STRENGTH_WEAK_THRESHOLD_PP = -5.0    # percentage points below benchmark

# --- Sector comparison ---
# A curated list of large, liquid representative peers per Yahoo Finance
# GICS-style sector label. This is only a lookup of WHICH tickers to compare
# against - every price/return shown for them is fetched live, never faked.
SECTOR_PEER_MAP: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "AVGO"],
    "Communication Services": ["META", "GOOGL", "NFLX", "DIS", "VZ"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Financial Services": ["JPM", "V", "MA", "BAC", "WFC"],
    "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "ABBV"],
    "Industrials": ["CAT", "BA", "HON", "UPS", "GE"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Basic Materials": ["LIN", "SHW", "APD", "FCX", "NEM"],
}
SECTOR_PEER_DISPLAY_COUNT = 5

# --- Fundamental score (optional, off unless explicitly requested) ---
FUNDAMENTAL_SCORE_METHODOLOGY = (
    "Deterministic point-scoring over valuation, growth, profitability, and balance-sheet "
    "fields actually returned by Yahoo Finance for this ticker; fields that are unavailable "
    "are excluded from both the score and its normalization range, never estimated."
)
DEFAULT_TECHNICAL_WEIGHT = 0.6
DEFAULT_FUNDAMENTAL_WEIGHT = 0.4

# --- Walk-forward analysis ---
WALK_FORWARD_DEFAULT_TRAIN_YEARS = 2
WALK_FORWARD_DEFAULT_TEST_YEARS = 1
WALK_FORWARD_MAX_FOLDS = 8
WALK_FORWARD_METHODOLOGY = (
    "This signal engine has no trainable/fitted parameters - it is a fixed rules-based "
    "model, so there is no parameter-fitting step on the 'train' window. Walk-forward here "
    "instead partitions history into sequential periods and re-runs the SAME fixed model "
    "only on each 'test' window, to check whether performance is consistent across "
    "different, non-overlapping market regimes rather than an artifact of one lucky period."
)

# --- Monte Carlo robustness ---
MONTE_CARLO_DEFAULT_SIMULATIONS = 1000
MONTE_CARLO_MAX_SIMULATIONS = 5000
MONTE_CARLO_MIN_TRADES_FOR_TRADE_RESAMPLING = 10
MONTE_CARLO_METHODOLOGY = (
    "Bootstrap resampling (with replacement) of this specific backtest's own historical "
    "per-trade returns (or daily returns, if there were too few trades) to build simulated "
    "equity paths. This is a stress/robustness check on the historical sample actually "
    "observed - it assumes the future resembles that sample's distribution and is NOT a "
    "forecast of future performance."
)

# --- Paper trading (simulation only - no real money, no brokerage) ---
PAPER_TRADING_DEFAULT_CAPITAL = 10_000.0
PAPER_TRADING_DATA_DIR = "data/paper_trading"
PAPER_TRADING_DEFAULT_PORTFOLIO_ID = "default"

# --- Signal performance analytics ---
SIGNAL_PERFORMANCE_HORIZONS_SESSIONS = (5, 20)
SIGNAL_PERFORMANCE_LOOKBACK_SESSIONS = 500
