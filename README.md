# Stock Analyst

A quantitative stock research **and paper-trading** platform. It retrieves real market data from
Yahoo Finance (via `yfinance`) and runs it through a transparent, deterministic, versioned
rules-based scoring engine to classify each ticker as **Strong Buy / Buy / Hold / Sell / Strong
Sell** — with every contributing factor, its category weight, its historical track record, and
what would invalidate it all shown, not hidden behind a black box.

Beyond the core signal, the platform adds: signal history and stability tracking, market-regime
detection, relative-strength and sector comparison, optional fundamental scoring, walk-forward and
Monte Carlo backtesting robustness checks, and a simulation-only paper-trading portfolio.

> **Not financial advice.** This is a research and educational tool. It does not guarantee returns,
> does not predict the future, and is not a substitute for professional financial advice. See
> [Financial Disclaimer](#financial-disclaimer).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Tech Stack](#tech-stack)
5. [Installation](#installation)
6. [Running the Backend](#running-the-backend)
7. [Running the Frontend](#running-the-frontend)
8. [Environment Variables](#environment-variables)
9. [API Reference](#api-reference)
10. [Signal Methodology](#signal-methodology)
11. [Model Versioning](#model-versioning)
12. [Indicator Definitions](#indicator-definitions)
13. [Confidence Methodology](#confidence-methodology)
14. [Signal History, Stability & Change Detection](#signal-history-stability--change-detection)
15. [Signal Performance Analytics](#signal-performance-analytics)
16. [Market Regime, Relative Strength & Sector Comparison](#market-regime-relative-strength--sector-comparison)
17. [Fundamental Analysis & Optional Fundamental Score](#fundamental-analysis--optional-fundamental-score)
18. [Backtesting Methodology](#backtesting-methodology)
19. [Walk-Forward Analysis](#walk-forward-analysis)
20. [Monte Carlo Robustness](#monte-carlo-robustness)
21. [Paper Trading](#paper-trading)
22. [No-Look-Ahead-Bias Guarantee](#no-look-ahead-bias-guarantee)
23. [Data Freshness & Status Labels](#data-freshness--status-labels)
24. [yfinance / Yahoo Finance Limitations](#yfinance--yahoo-finance-limitations)
25. [Financial Disclaimer](#financial-disclaimer)
26. [Testing](#testing)
27. [Deployment Considerations](#deployment-considerations)
28. [GitHub Setup](#github-setup)

---

## Project Overview

Stock Analyst has six sections:

- **Overview** — what the platform does, a ticker search, and the methodology summary.
- **Markets** — major index quotes and gainers/losers from a fixed watchlist, all real data.
- **Analysis** — the core page: real-time-delayed quote, an interactive OHLC/candlestick chart
  with SMA overlays, the deterministic BUY/HOLD/SELL signal (model version, score breakdown,
  signal-change banner), its full factor explanation, signal stability and "what could invalidate
  this" panels, a signal-history chart, technical indicators, fundamental analysis, relative
  strength vs. a benchmark, market regime, sector comparison, a risk panel, and company information.
- **Backtesting** — runs the exact same signal engine against historical data to simulate a
  long/flat trading strategy, compared against buy-and-hold and a benchmark (default `SPY`), plus
  on-demand walk-forward analysis and Monte Carlo robustness simulation.
- **Paper Trading** — a simulation-only virtual portfolio (no real money, no brokerage) valued
  with real, live-retrieved quotes.
- **Model** — the full methodology reference: current/legacy model version notes, factor weights,
  score thresholds, confidence/risk/backtest methodology, and documented data limitations.

**The recommendation engine contains no machine learning and no LLM call.** It is a fixed,
documented, versioned point-scoring system over technical indicators. Given the same input data
and model version, it always produces the same output.

## Features

- Real OHLCV and fundamental data from Yahoo Finance via `yfinance` — no fabricated or hardcoded
  production data anywhere.
- Explicit data-freshness labeling on every response: `LIVE` / `DELAYED` / `MARKET_CLOSED` /
  `HISTORICAL` / `UNAVAILABLE`, plus `retrieved_at`, `latest_market_timestamp`, `market_status`,
  and `timeframe`.
- Trend, momentum, volatility, and volume indicators (SMA/EMA, RSI, MACD, ROC, ATR, Bollinger
  Bands, historical volatility, relative volume).
- **Explicit model versioning** (`1.0` legacy, `1.1` current) — a documented methodology change is
  never applied silently to historical comparisons.
- A 0–100 normalized deterministic score, mapped to five signal buckets, with every contributing
  factor shown as a plain-language explanation **and** a category-level score breakdown
  (Trend/Momentum/Volume/Volatility).
- **Signal history, stability, and change detection** — the same deterministic model re-evaluated
  causally at each of the last N sessions, with automatic detection of when and why the signal
  flipped, and a stability percentage over the trailing window.
- **"What could invalidate this signal?"** — derived directly from the specific factors currently
  supporting the signal's direction, using their actual current values.
- **Signal performance analytics** — retrospective (never predictive) outcome statistics for past
  BUY/SELL signals on a ticker: positive-rate and average/median forward return at fixed horizons.
- **Market regime detection** (Bull/Bear/Sideways/High-Volatility) from a benchmark's own trend and
  volatility indicators, plus **relative strength** vs. a benchmark and **sector peer comparison**.
- Optional **fundamental data and fundamental score** (valuation/growth/profitability/balance
  sheet) from Yahoo Finance, with an explicit, documented, and configurable technical/fundamental
  weighting for an "overall score" — never a silent average.
- A confidence score that reflects data completeness and internal factor agreement — explicitly
  **not** a probability of future price movement.
- A risk panel built from the ticker's own actual current indicator readings (never generic text).
- A backtesting engine with realistic transaction costs, slippage, next-bar execution, a documented
  no-look-ahead-bias contract, **walk-forward analysis** across sequential market periods, and
  **Monte Carlo** bootstrap robustness simulation.
- A **simulation-only paper-trading portfolio** (buy/sell, average-entry tracking, realized/
  unrealized P&L) valued with real live quotes — clearly labeled, never connected to a real broker.
- Graceful error handling for invalid tickers, insufficient history, and Yahoo Finance outages —
  never a fake fallback number.
- Dark-mode-first, information-dense UI designed to feel like a research terminal, not a generic
  AI SaaS dashboard.

## Architecture

```
stock-analyst/
  backend/                  FastAPI application
    app/
      main.py                App entrypoint, CORS, router wiring
      config.py               All tunable constants (thresholds, windows, cache TTLs, model versions)
      api/                    HTTP route handlers + exception -> HTTP mapping
      services/                yfinance wrapper, in-memory TTL cache, typed exceptions
      indicators/              Pure indicator math (trend/momentum/volatility/volume) + interpretation
      signals/                 Scoring engine (versioned), confidence, risk, history/stability/
                                 change-detection, invalidation conditions, performance analytics
      market/                  Market regime, relative strength, sector peer comparison
      fundamentals/            Fundamental data extraction + optional fundamental/overall score
      backtesting/             Backtest engine, metrics, walk-forward analysis, Monte Carlo
      paper_trading/           JSON-file-backed virtual portfolio (simulation only)
      models/                  Pydantic request/response schemas
      utils/                   Ticker validation, time/market-hours helpers, shared finance math
    tests/                    pytest suite (unit + API + real-network integration)

  frontend/                 Next.js (App Router) + TypeScript + Tailwind CSS
    app/                      Routes: /, /markets, /analysis, /backtest, /paper-trading, /model
    components/               UI, by domain: nav, search, stock, backtest, markets, paper-trading, model
    lib/                      API client, formatting helpers, constants
    hooks/                    Data-fetching hook with cancellation, debounce
    types/                    TypeScript types mirroring the backend's Pydantic schemas
```

The frontend is a pure client of the backend's HTTP API — there is no server-side data fetching
of Yahoo Finance data inside Next.js, keeping a single source of truth for market data and
indicator logic.

## Tech Stack

**Backend:** Python, FastAPI, yfinance, pandas, numpy, Pydantic, pytest.
**Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, Recharts, lucide-react icons.

No database. The application is stateless; a lightweight in-memory TTL cache reduces redundant
Yahoo Finance requests within a single backend process.

## Installation

Prerequisites: Python 3.12+, Node.js 20+, npm.

```bash
git clone <this-repo>
cd stock-analyst
```

### Backend setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # defaults already point at http://localhost:8000
```

## Running the Backend

```bash
cd backend
venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs (Swagger UI) at
`http://localhost:8000/docs`. Health check: `GET /api/health`.

## Running the Frontend

```bash
cd frontend
npm run dev
```

The app is now at `http://localhost:3000`. It expects the backend at the URL configured in
`NEXT_PUBLIC_API_BASE_URL` (see below).

## Environment Variables

**Backend** (`backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed CORS origins |

**Frontend** (`frontend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

## API Reference

All responses include a `meta` object: `data_source`, `data_status`, `retrieved_at`,
`latest_market_timestamp`, `market_status`, `timeframe`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/stock/{ticker}` | Company overview + latest quote |
| GET | `/api/stock/{ticker}/history?range=1Y` | OHLCV candles + SMA overlays for the given range (`1D,5D,1M,3M,6M,1Y,2Y,5Y,MAX`) |
| GET | `/api/stock/{ticker}/technical` | Full technical indicator breakdown, grouped by category |
| GET | `/api/stock/{ticker}/signal` | Signal, score, score breakdown, confidence, factors, signal change, stability, invalidation conditions, risk panel. Query: `model_version` (`1.0`\|`1.1`), `include_overall_score`, `technical_weight`, `fundamental_weight` |
| GET | `/api/stock/{ticker}/signal-history?lookback_sessions=60` | Causal signal/score history over the trailing N sessions |
| GET | `/api/stock/{ticker}/signal-performance` | Retrospective forward-return statistics for past BUY/SELL signals |
| GET | `/api/stock/{ticker}/fundamentals` | Valuation/growth/profitability/balance-sheet metrics (Yahoo Finance `.info`) |
| GET | `/api/stock/{ticker}/relative-strength?benchmark=SPY` | 1M/3M/6M/1Y return vs. a benchmark |
| GET | `/api/stock/{ticker}/sector` | Sector peer comparison (curated peer list, live-fetched returns) |
| POST | `/api/backtest` | Runs the backtest engine (see request body below) |
| POST | `/api/backtest/walk-forward` | Sequential train/test-window robustness analysis |
| POST | `/api/backtest/monte-carlo` | Bootstrap-resampling robustness simulation over a backtest |
| GET | `/api/market/status` | Major indexes + gainers/losers from a fixed watchlist |
| GET | `/api/market/regime?benchmark=SPY` | Deterministic Bull/Bear/Sideways/High-Volatility classification |
| GET | `/api/search?q=` | Ticker/company search (via Yahoo Finance search) |
| GET | `/api/model` | Full model methodology reference (versions, weights, thresholds) |
| GET | `/api/model/performance?ticker=` | Signal counts, stability, performance analytics, and a reference backtest for one ticker |
| GET | `/api/paper-portfolio?portfolio_id=default` | Current paper-trading portfolio (positions, P&L, live valuation) |
| POST | `/api/paper-trade` | Execute a virtual BUY/SELL (`portfolio_id`, `ticker`, `action`, `shares`) |
| GET | `/api/paper-trades?portfolio_id=default` | Trade history for a portfolio |
| POST | `/api/paper-portfolio/reset?portfolio_id=default&starting_capital=10000` | Reset a paper-trading portfolio |
| GET | `/api/health` | Liveness check |

**POST `/api/backtest` body:**

```json
{
  "ticker": "AAPL",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 10000,
  "transaction_cost_bps": 5,
  "slippage_bps": 5,
  "benchmark_ticker": "SPY",
  "timeframe": "Daily"
}
```

Errors are returned as `{ "error_type": "...", "detail": "..." }` with an appropriate HTTP status
(400 invalid input, 404 ticker not found, 422 insufficient history / validation, 503 data
unavailable). No raw Python tracebacks are ever returned to clients.

## Signal Methodology

The signal is computed once per request, from the latest available **daily** candle, using a
fixed point-scoring model. Each factor has a **symmetric** point range (e.g. price vs. 200-day SMA
contributes +15 if bullish, −15 if bearish) so the model rewards and penalizes evidence evenly
rather than being tuned to favor BUY outcomes:

| Category | Factor | Range |
|---|---|---|
| Trend | Price vs. 200-day SMA | ±15 |
| Trend | 50-day SMA vs. 200-day SMA | ±15 |
| Trend | 20-day SMA vs. 50-day SMA | ±10 |
| Momentum | RSI (14) bucket (oversold/weak/neutral/healthy/overbought) | −10 to +10 |
| Momentum | MACD vs. signal line, and vs. zero | −15 to +15 |
| Momentum | 12-period Rate of Change | ±5 |
| Volume | Price move confirmed (or contradicted) by relative volume > 1.2x | ±10 |
| Volatility | Volatility regime (Low/Normal/Elevated/Extreme, vs. the stock's own trailing history) | −10 to +5 |

A factor is only included when its underlying indicator has enough history to compute (e.g. the
200-day SMA factor is omitted for a stock with under ~200 days of price history — never
approximated or faked).

**Normalization (model v1.1, default):** the raw score is normalized against a **fixed** min/max
(−90 to +85 — the theoretical worst/best case across all 8 possible factors), so the same factor
condition (e.g. "price above the 200-day SMA") always contributes the same normalized amount for
every ticker, making scores meaningfully comparable across stocks. See
[Model Versioning](#model-versioning) for why this replaced the original per-ticker normalization
and how the two versions differ.

**Score Breakdown:** every signal response also reports `score_breakdown` — the raw points
contributed by each category (Trend/Momentum/Volume/Volatility) — so the 0–100 score is never a
single opaque number.

**Thresholds** (`backend/app/config.py`, all configurable in one place):

| Score | Signal |
|---|---|
| 80–100 | Strong Buy |
| 65–79 | Buy |
| 45–64 | Hold |
| 30–44 | Sell |
| 0–29 | Strong Sell |

**What a signal means:** "According to this predefined quantitative model and the Daily
timeframe, the current/latest available data satisfies conditions classified as `BUY`." It does
**not** mean "buy this stock."

## Model Versioning

The signal engine is explicitly versioned (`GET /api/model` exposes both versions' notes):

- **v1.0 (legacy):** the raw score is normalized against the min/max of *only the factors available
  for that specific stock*. Mathematically valid, but an identical factor condition can contribute
  a different normalized amount depending on how many other factors that ticker happened to have
  data for — an unintuitive property when comparing scores across tickers.
- **v1.1 (current, default):** the raw score is normalized against the *fixed* theoretical min/max
  across all 8 possible factors (−90 to +85), so the same factor condition always contributes the
  same normalized amount regardless of ticker. This is the recommended version for cross-ticker
  comparison.

Both versions remain fully implemented and selectable (`?model_version=1.0` on the signal, history,
and performance endpoints, or `model_version` in a backtest request) — a methodology change is
never applied silently to historical results. Every signal, backtest, and paper-trade-relevant
response reports which `model_version` produced it.

## Indicator Definitions

- **SMA(n) / EMA(n)** — simple / exponential moving average of closing price over `n` days.
- **RSI(14)** — Wilder's Relative Strength Index; >70 overbought, <30 oversold.
- **MACD** — EMA(12) − EMA(26); signal line is EMA(9) of MACD; histogram is MACD − signal.
- **ROC(12)** — percentage price change over the last 12 periods.
- **ATR(14)** — Wilder's Average True Range; also expressed as % of price for risk context.
- **Bollinger Bands(20, 2σ)** — SMA(20) ± 2 population standard deviations of closing price.
- **Historical Volatility(20)** — annualized standard deviation of daily log returns (×√252), as %.
- **Volume SMA(20) / Relative Volume** — 20-day average volume; current volume ÷ that average.
- **Trend Classification** — combines price/SMA20/SMA50/SMA200 comparisons into a five-bucket
  label (Strong Bearish → Strong Bullish).
- **Volatility Regime** — percentile rank of current historical volatility within its own trailing
  252-day distribution (Low / Normal / Elevated / Extreme) — relative to the stock's *own* history,
  not a universal cutoff.

All formulas are in `backend/app/indicators/`, unit-tested in `backend/tests/test_indicators.py`.

## Confidence Methodology

Confidence is **not** `score / 100`. It's a weighted blend of:

- **Completeness** (30%) — fraction of the 8 possible factors that had enough data to compute.
- **Agreement** (40%) — share of non-neutral factors pointing the same direction as the overall
  score.
- **Stability margin** (15%) — how far the score sits from the nearest signal-bucket boundary (a
  score of 82 is more "stable" than a score of 66, which is one point from becoming a Hold).
- **Volatility clarity** (15%) — extreme volatility regimes reduce confidence.

Result is clamped to `[5%, 97%]` — the model never claims absolute certainty in either direction.

> **Model confidence reflects internal indicator agreement and data completeness; it is NOT the
> probability of future returns.**

## Signal History, Stability & Change Detection

`GET /api/stock/{ticker}/signal-history` computes the signal at each of the last N sessions by
truncating the indicator frame to end at that day and calling the exact same `evaluate()` used
live — identical to what a live signal on that historical day would have shown (no future data
leaks in; this is the same causal-truncation contract the backtester relies on, and is directly
unit-tested: `test_v2_signal_analytics.py::test_signal_history_matches_direct_evaluate_at_each_point`).

- **Signal change detection** compares the two most recent history points; when they differ, the
  response includes the previous/current signal and score plus the *specific factors* whose
  polarity flipped (e.g. "MACD turned bullish") — derived from the actual factor diff, not a
  canned message.
- **Signal stability** is the share of the trailing 10 sessions whose signal matches the latest
  session's signal — a measure of the model's own output consistency, explicitly **not** a
  probability of any future return.

## Signal Performance Analytics

`GET /api/stock/{ticker}/signal-performance` answers, retrospectively, "historically, what
happened in the N sessions *after* this model produced a BUY (or SELL) signal for this ticker?" —
using only price data that has already occurred. For each historical BUY-class and SELL-class
signal in the lookback window, it measures the forward return at fixed horizons (5 and 20 sessions)
and reports sample size, positive-rate, and average/median return. Signals too close to the end of
the available history (no future data to measure yet) are excluded from the sample, never padded.
This is deliberately **not** framed as an "accuracy" percentage — it is descriptive statistics over
the past, not a forecast.

## Market Regime, Relative Strength & Sector Comparison

- **Market regime** (`GET /api/market/regime`) classifies a benchmark (default `SPY`) into
  `BULL` / `BEAR` / `SIDEWAYS` / `HIGH_VOLATILITY` by reusing the same causal trend and
  volatility-regime classifiers used for individual stocks, applied to the benchmark's own price
  history. An `Extreme` volatility regime overrides the trend label. A regime confidence score
  (internal agreement, not a forecast) is included.
- **Relative strength** (`GET /api/stock/{ticker}/relative-strength`) compares a ticker's actual
  1M/3M/6M/1Y return against a benchmark's, classifying each period `STRONG` / `IN_LINE` / `WEAK`
  by a fixed percentage-point threshold.
- **Sector comparison** (`GET /api/stock/{ticker}/sector`) ranks a ticker against a small, curated
  list of large, liquid peers for its Yahoo Finance-reported sector (`app.config.SECTOR_PEER_MAP`
  only decides *which* tickers to compare — every return shown is fetched live). Sectors outside
  the curated map return an explicit "unavailable" state rather than a guess.

## Fundamental Analysis & Optional Fundamental Score

`GET /api/stock/{ticker}/fundamentals` surfaces valuation (P/E, forward P/E, PEG, P/S, P/B),
growth (revenue/earnings growth), profitability (margins, ROE), and balance-sheet (debt/equity,
current ratio, free cash flow) fields exactly as Yahoo Finance reports them — a missing field is
`null` ("N/A"), never estimated. (Yahoo's `debtToEquity` field is already a percentage of equity,
e.g. `78.4` means a 0.784 ratio — this is *not* re-scaled, to avoid a double-scaling bug.)

An optional, fully documented **fundamental score** (0–100) awards fixed points per metric that
falls in a "healthy" range, normalized only against the metrics actually available for that
ticker. It is surfaced only when `include_overall_score=true` is passed to the signal endpoint,
alongside the technical score and an explicit, configurable weighted **overall score**
(`technical_weight` / `fundamental_weight`, default 60/40) — the three numbers are always shown
separately; the overall score is never presented as if it were the technical score alone.

## Backtesting Methodology

- **Same engine, not a second strategy.** The backtester calls the exact same
  `signals.engine.evaluate()` function used by the live Stock Analysis page.
- **Position model:** long-or-flat only. `BUY`/`STRONG_BUY` → hold a full position;
  `HOLD`/`SELL`/`STRONG_SELL` → fully in cash. No shorting.
- **Execution:** a signal computed from day T's close can only change the position starting at day
  T+1's **open** ("next-bar execution") — see [No-Look-Ahead-Bias Guarantee](#no-look-ahead-bias-guarantee).
- **Costs:** transaction cost + slippage (in basis points) are applied as a price haircut on every
  executed entry and exit.
- **Metrics:** total/annualized return, buy-and-hold return, benchmark return, max drawdown,
  Sharpe ratio (risk-free rate = 0, documented assumption), win rate, average/best/worst trade,
  profit factor. Any metric that can't be meaningfully computed (e.g. Sharpe with zero variance,
  profit factor with no losing trades) is returned as `null` (rendered "N/A") — never a fabricated
  number.
- **Limitations (also shown in the UI):** no taxes, no dividends, no borrowing costs, no partial
  fills, no execution latency modeling. Past performance does not guarantee future results.

## Walk-Forward Analysis

`POST /api/backtest/walk-forward` partitions a ticker's full available history into sequential,
non-overlapping `train_years` + `test_years` windows and re-runs the **same fixed model** — via the
same `run_backtest()` engine — only on each window's *test* period. Because the signal engine has
no trainable/fitted parameters, there is no parameter-fitting step on the "train" window; it is
shown for reference (what history existed before that test period) only. The purpose is to check
whether performance holds up across several distinct market regimes rather than being an artifact
of one favorable period.

When more windows exist than the requested fold count, the **most recent** folds are kept — an
earlier version of this logic kept the *oldest* folds instead, silently hiding recent performance
for any ticker with long history; this is covered by a regression test
(`test_walk_forward_prefers_most_recent_folds_for_long_history`).

## Monte Carlo Robustness

`POST /api/backtest/monte-carlo` runs one backtest, then bootstrap-resamples (with replacement)
its own historical per-trade returns (or daily returns, if there were fewer than 10 trades) to
build many simulated equity paths, reporting the 5th/median/95th-percentile final return and the
median/worst simulated maximum drawdown. This is a stress/robustness check on the historical sample
actually observed — it assumes the future resembles that sample's distribution and is explicitly
**not** a forecast. Pass a `seed` for reproducible output.

## Paper Trading

A **simulation-only** virtual portfolio: no real money, no brokerage connection, no real orders.
State is persisted per `portfolio_id` in a small JSON file (`backend/data/paper_trading/`, gitignored)
rather than a database — durable across backend restarts without new infrastructure. Buying and
selling use a real, live-retrieved quote (`fast_info.lastPrice`) for execution and for valuing
open positions; average entry price, realized P&L (on sell), and unrealized P&L (mark-to-market)
are all computed from that real price, never fabricated. Every API response and the UI both
prominently label this feature as simulated.

## No-Look-Ahead-Bias Guarantee

This is enforced two ways, and both are unit tested:

1. **Indicators are causal by construction.** Every rolling/EWM calculation in
   `backend/app/indicators/` only ever looks backward from a given row — pandas rolling/EWM
   operations cannot see future rows. `tests/test_indicators.py::test_indicators_are_causal_no_lookahead`
   proves a given day's indicator value is identical whether computed on the full series or on a
   series truncated to end at that day.
2. **Execution timing.** `tests/test_backtesting.py::test_no_look_ahead_prefix_invariance` proves
   the strategy's equity curve through day K is byte-identical whether the backtest is run with
   data ending at day K or with data extending months further into the future — i.e. future data
   provably cannot change a past decision. A companion test
   (`test_execution_happens_next_bar_not_same_bar`) proves every trade's entry price equals the
   *next* trading day's open, never the signal day's own close.

## Data Freshness & Status Labels

Every relevant response carries `data_status`, one of:

- **`LIVE`** — reserved for genuinely real-time-guaranteed data. This application never claims it,
  because `yfinance` cannot guarantee true real-time delivery.
- **`DELAYED`** — market is open; the quote reflects Yahoo Finance's own (typically ~15-minute)
  delayed feed.
- **`MARKET_CLOSED`** — market is not in its regular session; showing the latest available close.
- **`HISTORICAL`** — a range of past candles (charts, indicators, signal, backtest).
- **`UNAVAILABLE`** — Yahoo Finance could not be reached or returned no usable data.

The signal endpoint additionally reports `signal_timeframe` (always `"Daily"` today),
`signal_generated_at`, `latest_candle_date`, and `is_latest_candle_complete` (false when the
market is open and the latest daily candle is still forming) so the UI never implies a daily
model is a tick-by-tick real-time signal.

## yfinance / Yahoo Finance Limitations

- `yfinance` is an **unofficial**, community-maintained library that scrapes/accesses Yahoo
  Finance endpoints — it is not an official Yahoo API and carries no uptime or accuracy SLA.
- Data freshness and availability vary by ticker, exchange, and time of day; some fields
  (`.info`) are occasionally incomplete or slow.
- Intraday history depth is limited by Yahoo (e.g. 1-minute data only covers a recent window).
- Rate limiting and transient failures can occur; this app treats them as `DATA_UNAVAILABLE`
  rather than retrying indefinitely or fabricating a response.
- Review Yahoo Finance's and `yfinance`'s terms of use before any commercial deployment.
- Always verify important financial figures independently before acting on them.

## Financial Disclaimer

This application is a research and educational analysis tool. It is **not** a financial adviser.
It does **not** guarantee returns. BUY/HOLD/SELL is the output of a deterministic quantitative
model, not personalized financial advice. Nothing in this application should be construed as
"guaranteed profit," "100% accurate," "risk-free," or a "certain winner." Past performance
(including backtested, walk-forward, and Monte Carlo-simulated performance) does not guarantee
future results. Historical signal-performance statistics are retrospective descriptions of the
past, not predictions. Paper trading is a simulation only — it does not represent real money, a
real brokerage account, or real order execution.

## Testing

```bash
cd backend
venv\Scripts\python -m pytest -q
```

151+ tests in `backend/tests/` cover: ticker validation, every indicator calculation (SMA, EMA,
RSI, MACD, Bollinger Bands, ATR, ROC, historical volatility, relative volume) plus the interpretation
layer that turns them into UI text (regression-tested after a real bug where the Bollinger lower-band
description was accidentally copied from the upper band), signal scoring and threshold mapping under
**both model versions**, confidence methodology, risk assessment, signal history/stability/change
detection/invalidation-conditions/performance analytics, market regime/relative-strength/sector
comparison, fundamental data extraction and scoring, backtesting (transaction costs, slippage,
drawdown, Sharpe, trade stats, and the no-look-ahead-bias proofs above), walk-forward analysis
(including a regression test that recent folds are preferred over the oldest ones), Monte Carlo
robustness (including reproducibility with a fixed seed), paper trading (buy/sell/reset/P&L, with
an isolated temp-directory store and mocked quotes), and API-level tests (response shape, error
mapping, disclaimer content) with `yfinance` calls monkeypatched for speed and determinism.

`tests/test_integration_real_data.py` is a **separate, real-network** suite that hits live Yahoo
Finance data for `AAPL`, `MSFT`, `NVDA`, and an invalid ticker — covering the overview, technical,
signal (incl. model version/score breakdown/stability), signal-history, fundamentals,
relative-strength, market-regime, model-info, walk-forward, Monte Carlo, paper-trade, and backtest
endpoints — and inspects the actual returned structure (not just HTTP 200). It auto-skips if no
network access is available.

Frontend checks:

```bash
cd frontend
npx tsc --noEmit   # type check
npx eslint .       # lint
npm run build      # production build
```

## Deployment Considerations

GitHub hosts source code, not a running backend — deploy the two halves separately:

- **Backend (FastAPI):** any Python host that can run `uvicorn`/`gunicorn` (e.g. a container on
  Render, Fly.io, Railway, or your own VM). Set `CORS_ALLOWED_ORIGINS` to your deployed frontend's
  origin.
- **Frontend (Next.js):** any Next.js-capable host (e.g. Vercel, or a Node server anywhere). Set
  `NEXT_PUBLIC_API_BASE_URL` to your deployed backend's public URL.

No database is required. The in-memory cache is per-process — a multi-instance deployment behind
a load balancer will simply have independent caches per instance, which is fine given its purpose
(reducing duplicate Yahoo Finance calls) rather than shared state.

## GitHub Setup

```bash
cd stock-analyst
git init
git add .
git commit -m "Initial commit: Stock Analyst platform"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

`.gitignore` at the repo root excludes `node_modules/`, `.next/`, `__pycache__/`, `venv/`, and all
`.env*` files except the committed `.env.example` templates. No secrets are required for local
development — the backend needs no API keys at all.
