# Stock Analyst

A quantitative stock research, **validation**, and paper-trading platform. It retrieves real
market data from Yahoo Finance (via `yfinance`) and runs it through a transparent, deterministic,
versioned rules-based scoring engine to classify each ticker as **Strong Buy / Buy / Hold / Sell /
Strong Sell** — with every contributing factor, its category weight, its historical track record,
and what would invalidate it all shown, not hidden behind a black box.

Beyond the core signal, the platform adds: signal history and stability tracking, market-regime
detection (and regime-conditioned performance), relative-strength and sector comparison, optional
fundamental scoring, a full quantitative Model Evaluation suite (CAGR, Sortino, Calmar, beta/alpha,
exposure, turnover, and more), out-of-sample validation, parameter sensitivity/robustness analysis
(including indicator-period sweeps and a 2D heatmap), walk-forward and Monte Carlo backtesting
checks, multi-ticker portfolio backtesting with configurable allocation/rebalancing/constraints,
side-by-side stock comparison, a five-dimension Model Scorecard, a watchlist, and an advanced
simulation-only paper-trading engine with position sizing, stop-loss/take-profit/trailing-stop
controls, persistent equity-curve history, and a dedicated **Forward Validation** engine that tracks
how the model actually performs as real market data arrives — conceptually and technically distinct
from backtesting, which replays the past.

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
17. [Regime-Conditioned Performance](#regime-conditioned-performance)
18. [Fundamental Analysis & Optional Fundamental Score](#fundamental-analysis--optional-fundamental-score)
19. [Backtesting Methodology](#backtesting-methodology)
20. [Model Evaluation Metrics](#model-evaluation-metrics)
21. [Out-of-Sample Validation](#out-of-sample-validation)
22. [Parameter Sensitivity & Robustness](#parameter-sensitivity--robustness)
23. [Walk-Forward Analysis](#walk-forward-analysis)
24. [Monte Carlo Robustness](#monte-carlo-robustness)
25. [Data Quality Layer](#data-quality-layer)
26. [Watchlist](#watchlist)
27. [Paper Trading](#paper-trading)
28. [Forward Validation (Paper Trading ≠ Backtesting)](#forward-validation-paper-trading--backtesting)
29. [Portfolio Backtesting](#portfolio-backtesting)
30. [Stock Comparison](#stock-comparison)
31. [Model Scorecard & Model-vs-Model Comparison](#model-scorecard--model-vs-model-comparison)
32. [No-Look-Ahead-Bias Guarantee](#no-look-ahead-bias-guarantee)
33. [Data Freshness & Status Labels](#data-freshness--status-labels)
34. [yfinance / Yahoo Finance Limitations](#yfinance--yahoo-finance-limitations)
35. [Financial Disclaimer](#financial-disclaimer)
36. [Testing](#testing)
37. [Deployment Considerations](#deployment-considerations)
38. [GitHub Setup](#github-setup)
39. [Known Limitations & Remaining Work](#known-limitations--remaining-work)

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
      services/                yfinance wrapper, in-memory TTL cache, typed exceptions, data-quality validation
      indicators/              Pure indicator math (trend/momentum/volatility/volume) + interpretation
      signals/                 Scoring engine (versioned, configurable thresholds), confidence, risk,
                                 history/stability/change-detection, invalidation conditions, performance analytics
      market/                  Market regime (+ regime-conditioned performance), relative strength, sector comparison
      fundamentals/            Fundamental data extraction + optional fundamental/overall score
      backtesting/             Backtest engine + extended metrics, walk-forward, Monte Carlo,
                                 parameter sensitivity, in-sample/out-of-sample validation
      paper_trading/           JSON-file-backed virtual portfolio: position sizing, stop-loss/
                                 take-profit/trailing-stop, cost breakdown, risk dashboard (simulation only)
      watchlist/               JSON-file-backed watchlist, enriched with live quotes + fresh signals
      models/                  Pydantic request/response schemas
      utils/                   Ticker validation, time/market-hours helpers, shared finance math
    tests/                    pytest suite (unit + API + real-network integration)

  frontend/                 Next.js (App Router) + TypeScript + Tailwind CSS
    app/                      Routes: /, /markets, /analysis, /backtest, /paper-trading, /model, /watchlist
    components/               UI, by domain: nav, search, stock, backtest, markets, paper-trading, model, watchlist
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
| POST | `/api/backtest` | Runs the backtest engine (see request body below); response includes `advanced_metrics` (see [Model Evaluation Metrics](#model-evaluation-metrics)) |
| POST | `/api/backtest/walk-forward` | Sequential train/test-window robustness analysis |
| POST | `/api/backtest/monte-carlo` | Bootstrap-resampling robustness simulation over a backtest |
| POST | `/api/backtest/sensitivity` | Threshold + indicator-period perturbation and robustness classification (see [Parameter Sensitivity & Robustness](#parameter-sensitivity--robustness)) |
| POST | `/api/backtest/sensitivity/heatmap` | 2D grid over two sensitivity parameters at once |
| POST | `/api/backtest/out-of-sample` | In-sample / validation / out-of-sample three-period split |
| POST | `/api/backtest/portfolio` | Multi-ticker (2-20) allocation backtest (see [Portfolio Backtesting](#portfolio-backtesting)) |
| POST | `/api/compare` | Side-by-side 2-8 ticker comparison (see [Stock Comparison](#stock-comparison)) |
| GET | `/api/market/status` | Major indexes + gainers/losers from a fixed watchlist |
| GET | `/api/market/regime?benchmark=SPY` | Deterministic Bull/Bear/Sideways/High-Volatility classification |
| GET | `/api/search?q=` | Ticker/company search (via Yahoo Finance search) |
| GET | `/api/model` | Full model methodology reference (versions, weights, thresholds) |
| GET | `/api/model/performance?ticker=` | Signal counts, stability, performance analytics, and a reference backtest for one ticker |
| POST | `/api/model/regime-performance` | Regroups a backtest's realized returns by benchmark regime (see [Regime-Conditioned Performance](#regime-conditioned-performance)) |
| POST | `/api/model/scorecard` | Five-dimension model scorecard (see [Model Scorecard & Model-vs-Model Comparison](#model-scorecard--model-vs-model-comparison)) |
| POST | `/api/model/compare-versions` | v1.0 vs v1.1 backtest + forward comparison |
| GET | `/api/watchlist?watchlist_id=default` | Enriched watchlist (real quote + fresh signal per ticker) |
| POST | `/api/watchlist` | Add a ticker (`watchlist_id`, `ticker`) |
| DELETE | `/api/watchlist/{ticker}?watchlist_id=default` | Remove a ticker |
| GET | `/api/paper-portfolio?portfolio_id=default` | Current paper-trading portfolio (positions, P&L, live valuation); auto-applies any triggered stop-loss/take-profit/trailing-stop first |
| POST | `/api/paper-trade` | Execute a virtual BUY/SELL, with optional position sizing and risk controls (see [Paper Trading](#paper-trading)) |
| GET | `/api/paper-trades?portfolio_id=default` | Trade journal for a portfolio |
| POST | `/api/paper-portfolio/reset?portfolio_id=default&starting_capital=10000` | Reset a paper-trading portfolio |
| POST | `/api/paper-portfolio/close-all?portfolio_id=default` | Liquidate every open position (`exit_reason=END_OF_TEST`) |
| GET | `/api/paper-portfolio/risk?portfolio_id=default` | Exposure/concentration/sector risk dashboard |
| GET | `/api/paper-portfolio/history?portfolio_id=default` | Persistent, append-only daily equity snapshot history (see [Paper Trading](#paper-trading)) |
| GET | `/api/paper-portfolio/forward-validation?portfolio_id=default` | Forward paper-trading observation summary (see [Forward Validation](#forward-validation-paper-trading--backtesting)) |
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

## Regime-Conditioned Performance

`POST /api/model/regime-performance` answers "how did this strategy actually perform on days the
market was classified Bull / Bear / Sideways / High-Volatility?" It runs one ordinary backtest,
classifies the benchmark's regime for every day in that period causally (using only data through
that day), and then **regroups the strategy's own already-realized daily returns** by which regime
was active — it is not a separate simulation per regime. Trades are bucketed by the regime active
on their entry date. Each bucket reports trading days, % of the period, compounded return,
annualized volatility, Sharpe, trade count, and win rate — all `null` rather than fabricated if a
regime bucket has too little data.

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

## Model Evaluation Metrics

Every `/api/backtest` response includes an `advanced_metrics` block answering "is this actually
useful, or does it only look good in this one backtest?":

| Metric | Notes |
|---|---|
| CAGR | Compound annual growth rate (same formula as `annualized_return`) |
| Annualized volatility | Standard deviation of daily returns, annualized |
| Sortino ratio | Like Sharpe, but penalizes only downside deviation |
| Calmar ratio | CAGR ÷ \|max drawdown\| |
| Average drawdown | Mean depth of every distinct drawdown episode, not just the single worst one |
| Max drawdown recovery (days) | `null` if the equity curve never made a new high before the period ended |
| Expectancy | Average P&L per trade, in currency |
| Average win / loss, median trade | |
| Exposure % | Share of trading days the strategy actually held a position |
| Turnover % | Total traded notional ÷ starting capital |
| Beta, alpha, tracking error, information ratio | Computed against the supplied benchmark's daily returns; `null` if no benchmark was supplied or there's too little overlapping data |

Every field is individually `null` (never a fabricated number) when it can't be computed from the
available data — e.g. a strategy with zero closed trades has no expectancy or average win/loss.

## Out-of-Sample Validation

`POST /api/backtest/out-of-sample` runs three explicit, chronologically ordered, non-overlapping
periods — `IN_SAMPLE`, `VALIDATION`, `OUT_OF_SAMPLE` — through the **same** `run_backtest()` engine
used everywhere else. There is no separate "training" step (the signal engine has no fitted
parameters); the value of the split is procedural: it forces a pre-committed boundary so the
out-of-sample number was never visible while forming an opinion of the strategy. The request is
rejected (422) if the six boundary dates aren't strictly increasing. Each period reports its own
return, CAGR, Sharpe, Sortino, max drawdown, trade count, and win rate — a degrading result from
in-sample to out-of-sample is a real, common, and important finding this feature is designed to
surface, not a bug.

## Parameter Sensitivity & Robustness

`POST /api/backtest/sensitivity` is the primary overfitting-detection tool. By default it perturbs
the BUY and SELL score thresholds independently around their defaults (`[55, 60, 65, 70, 75]` and
`[20, 25, 30, 35, 40]`); passing an explicit `parameters` list additionally sweeps **indicator
periods** — `rsi_period`, `sma_short`, `sma_long`, `macd_fast`, `macd_slow` — around their own
defaults, using a bounded, sensible range per parameter (never an arbitrary caller-supplied grid).
Each swept variant re-runs the backtest engine and is classified by the coefficient of variation
(std/\|mean\|) of total return across all tested values: `HIGHER_ROBUSTNESS` (CV < 0.5),
`LOW_ROBUSTNESS` (CV ≥ 0.5), **`PARAMETER_INERT`** when every tested value produced an identical
result, or **`INSUFFICIENT_SAMPLE`** when the default configuration itself produced too few trades
(< 5) to trust a robustness verdict from. The `PARAMETER_INERT` case is not a hypothetical: the
current long/flat engine's entry/exit rule only checks whether the signal is BUY-class, so the
SELL/STRONG_SELL boundary (`sell_threshold`) cannot change a single trade at any value — reporting
that as "robust" would misrepresent "has no effect" as "stable performance," so it's called out
explicitly instead (see
`backend/tests/test_v3_sensitivity_and_oos.py::test_sensitivity_detects_inert_parameter`). Each
parameter also reports `best_value`/`median_value`/`worst_value` (by total return) and a
`robust_region` — the longest contiguous run of tested values (including the default) that keep the
same return sign as the default.

**Indicator-period sensitivity is computed by a fully isolated code path**
(`app/backtesting/parametrized_indicators.py`) that never touches the production indicator
computation (`app.indicators.compute.compute_indicator_frame`) used by every live signal, backtest,
walk-forward, Monte Carlo, and out-of-sample run. It is proven bit-for-bit equivalent to the
production path *at default parameters* by a dedicated test
(`test_default_params_match_standard_indicator_frame`) — the safety property the whole feature
depends on.

`POST /api/backtest/sensitivity/heatmap` runs a 2D grid over two parameters at once (e.g.
`buy_threshold` × `rsi_period`) for the chosen metric, flagging any cell with fewer than 5 trades
as `insufficient_sample` rather than coloring it as if it were reliable.

**Scope limit:** Bollinger Band period/stddev, ATR period, ROC period, volume-SMA period, and
signal-category weights are not (yet) perturbable — the bounded-range design above could be
extended to them, but wasn't in this pass. Documented here rather than silently omitted.

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

## Data Quality Layer

`app/services/data_quality.py` validates every OHLCV fetch before indicators are computed -
chronological ordering, duplicate timestamps, missing OHLC values, negative prices, impossible
High/Low relationships (e.g. High < Low), negative volume, suspicious gaps (>10 calendar days
between daily candles), and staleness (latest candle >5 days old). It never repairs or substitutes
values: fundamentally unusable data (non-chronological, negative prices) raises
`DataUnavailableError` rather than proceeding; survivable issues are attached as a `data_quality`
object inside every response's `meta` block, and `data_status` becomes `STALE` when appropriate
(joining the existing `LIVE` / `DELAYED` / `MARKET_CLOSED` / `HISTORICAL` / `UNAVAILABLE` set - see
[Data Freshness & Status Labels](#data-freshness--status-labels)).

## Watchlist

`GET/POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`. A small JSON-file-backed list of
tickers (`backend/data/watchlists/`, gitignored) enriched, on every read, with each ticker's real
current quote and a freshly computed signal from the same deterministic engine used everywhere
else - never a cached or precomputed summary. A ticker that fails to refresh shows an explicit
per-row error rather than stale or fabricated data; the rest of the list still loads normally.

## Paper Trading

A **simulation-only** virtual portfolio: no real money, no brokerage connection, no real orders,
long-only, no leverage. State is persisted per `portfolio_id` in a small JSON file
(`backend/data/paper_trading/`, gitignored) rather than a database — durable across backend
restarts without new infrastructure.

- **Execution & valuation:** every buy/sell uses a real, live-retrieved quote (`fast_info.lastPrice`).
- **Realistic costs:** commission + slippage (`PAPER_TRADING_COMMISSION_BPS`/`SLIPPAGE_BPS`, 5 bps
  each by default) are charged as a price haircut on both the entry and exit leg of every trade.
  Every closed trade reports **gross P&L, fees, slippage, and net P&L separately** - never one
  opaque number.
- **Position sizing** (`sizing_mode` on `POST /api/paper-trade`): `FIXED_SHARES` (caller specifies
  the share count), `FIXED_CAPITAL_PERCENT` (allocate X% of current portfolio equity), or
  `RISK_PERCENT` (size so that a stop-loss hit loses exactly X% of equity — requires
  `stop_loss_percent`). All three are hard-capped by `max_position_percent` (default 20%) and by
  available cash; it is mathematically impossible for a paper trade to create negative cash.
- **Stop-loss / take-profit / trailing-stop:** optional, attached per-position at entry. Checked
  against the current live price every time the portfolio is loaded (`GET /api/paper-portfolio`
  runs this check first) and auto-closed with an explicit `exit_reason`: `MODEL_SELL`,
  `STOP_LOSS`, `TAKE_PROFIT`, `TRAILING_STOP`, `END_OF_TEST` (via `POST
  /api/paper-portfolio/close-all`), or `MANUAL_PAPER_EXIT`.
- **Trade journal:** every closed trade records the signal and score at entry and at exit, the
  market regime at entry, the model version, and the full gross/fees/slippage/net cost breakdown -
  fully auditable, not just a running P&L number.
- **Portfolio risk dashboard** (`GET /api/paper-portfolio/risk`): exposure %, cash %, largest
  position %, and sector concentration (via each held ticker's real, live-fetched sector), with
  threshold-based warnings (`HIGH_CONCENTRATION`, `LOW_CASH`, `HIGH_DRAWDOWN`).
- **Persistent equity snapshot history** (`GET /api/paper-portfolio/history`): one **immutable**
  observation per real trading day the portfolio was actually queried on, appended opportunistically
  whenever the portfolio is loaded (there is no background scheduler). The trading day is keyed off
  the benchmark's (SPY's) own daily bars, never wall-clock date, so a weekend, holiday, or a day the
  portfolio was never viewed produces no entry — never a fabricated one. Each snapshot records
  equity, cash, invested value, realized/unrealized/daily P&L, cumulative return, and a benchmark
  value (SPY scaled proportionally from the portfolio's first recorded day). `daily_pnl` is
  documented as the change since the previous *recorded* observation, which may span more than one
  calendar day if the portfolio wasn't queried every day — never presented as a guaranteed
  day-over-day figure it can't back up. This history is what makes portfolio-level volatility,
  Sharpe, drawdown, and the Forward Validation page below possible; a resurgent-portfolio's
  history is separated from the version of it before an explicit reset.

Every API response and the UI both prominently label this feature as simulated.

## Forward Validation (Paper Trading ≠ Backtesting)

`GET /api/paper-portfolio/forward-validation` answers a **conceptually different question** from
every backtest/out-of-sample/walk-forward page in this app:

| | Backtest / Out-of-Sample / Walk-Forward | Forward Validation |
|---|---|---|
| Question | "How would this model have behaved on **past** data?" | "How does this model behave as **real, live** data arrives from now on?" |
| Data | Replayed history | Only data that has actually occurred since the portfolio started |
| Engine | `run_backtest()` | The paper-trading engine's own persisted equity snapshots |

It reports start date, current date, trading days observed, model version (flagged `MIXED` if the
portfolio's trades span more than one), current equity, total return, benchmark return, max
drawdown (computed from the portfolio's *own* recorded equity curve, same peak-to-trough definition
backtesting uses), trade count, and realized/unrealized P&L — and flags `insufficient_sample: true`
under 20 observed trading days rather than presenting an early number as conclusive. The frontend
page shows an explicit **"NO NEW MARKET DATA to chart yet"** state instead of any simulated or
interpolated ticking when there aren't yet enough real observations to draw a line.

## Portfolio Backtesting

`POST /api/backtest/portfolio` extends backtesting from one ticker to a **basket of 2-20 tickers**,
adding an allocation layer on top of the exact same per-ticker signals every other backtest uses
(`app.signals.engine.evaluate` over `app.indicators.compute.compute_indicator_frame`) — this module
never re-implements or duplicates that decision logic, only the choice of *which* signaling tickers
to hold, at what weight, rebalanced how often.

- **Allocation methods:** `EQUAL_WEIGHT` (default — investable capital split equally across every
  BUY/STRONG_BUY-signaling ticker), `FIXED_WEIGHT` (caller-supplied target weights, renormalized
  across only the currently-eligible tickers), `SIGNAL_WEIGHTED` (proportional to each ticker's own
  0-100 score), `RISK_WEIGHTED` (inverse-historical-volatility — a standard, well-defined heuristic,
  not a full risk-parity optimization).
- **Rebalancing:** `DAILY`, `WEEKLY`, or `MONTHLY` (first trading day of the week/month). Target
  weights are always decided from data through a day's **close** and executed at the **next**
  trading day's **open**, with the same transaction-cost/slippage haircut single-ticker backtests
  use — the same no-look-ahead contract, extended to a basket.
- **Constraints:** `max_position_weight`/`min_position_weight` (a name that can't be funded at least
  its minimum is dropped, not forced up), `max_holdings` (kept by highest score), `cash_allocation`
  (a minimum cash buffer no rebalance may invest below), `sector_cap` (an over-cap sector is scaled
  down proportionally; freed capital becomes cash, not redistributed to other sectors — a
  conservative simplification, documented rather than silently assumed). Long-only, no leverage.
- **Comparisons & risk analytics:** full metrics suite (CAGR, Sharpe, Sortino, Calmar, drawdown)
  against an equal-weight buy-and-hold of the same basket and a benchmark; risk analytics include
  exposure, cash %, largest position, top-3 concentration, sector concentration, and a **pairwise
  correlation matrix computed from each holding's real historical daily RETURNS** (never price
  levels, which are non-stationary and produce spurious correlation).

**A real bug was found and fixed via live verification against AAPL/MSFT/NVDA** during this
feature's development: target dollar amounts were originally sized off the rebalance *decision*
day's stale close-based equity snapshot, then compared against *execution*-day open prices — so a
holding already sitting exactly at its unchanged target weight could look artificially underfunded
purely from the overnight price gap, producing a phantom "insufficient cash" warning (observed
live: 16 of 36 monthly rebalances, one scaled to 0%, with no real allocation change needed). Fixed
by sizing target dollars off the portfolio's actual value **at the execution moment** instead of a
stale snapshot; see `test_unchanged_target_weight_produces_no_spurious_insufficient_cash_warning`.

## Stock Comparison

`POST /api/compare` (2-8 tickers) fans the exact same already-tested functions used everywhere else
in the app — `market_data.get_overview`/`get_full_daily_history`, `compute_indicator_frame`,
`signal_engine.evaluate`, `extract_fundamentals`, `compute_relative_strength` — out across tickers
concurrently, and assembles one row per ticker covering market, technical, performance,
fundamental, and model data. No new fetching or scoring logic, and **no cross-ticker normalization
or ranking**: values are shown exactly as retrieved per ticker, documented explicitly rather than
silently implying a methodology that doesn't exist. A field genuinely unavailable for a given
ticker is `null` ("N/A" in the UI) — **never** defaulted to `0`, since `0` is itself a real,
meaningful value (a genuine 0% margin) that must never be confused with missing data. One bad
ticker reports its own `error` field without failing the rest of the comparison.

A real unit-scaling bug was found and fixed via live verification: `HIST_VOL_20` is already computed
as a percentage (see `app.indicators.volatility.historical_volatility`), but the comparison row
multiplied it by 100 again, producing values like "1858%" annualized volatility for AAPL instead of
the real ~18.6%. See `test_historical_volatility_is_not_double_scaled`.

## Model Scorecard & Model-vs-Model Comparison

`POST /api/model/scorecard` reports **five independent dimensions** — `OUT_OF_SAMPLE_STRENGTH`,
`ROBUSTNESS`, `WALK_FORWARD_STABILITY`, `REGIME_DEPENDENCY`, `FORWARD_PAPER_DATA` — each labeled
`STRONG`/`MODERATE`/`WEAK`/`INSUFFICIENT_DATA` (or `NOT_PROVIDED` for the forward-data dimension
when no paper portfolio is supplied) directly from an already-tested engine's own output
(out-of-sample validation, sensitivity analysis, walk-forward, regime-performance, and forward
validation, respectively). **There is deliberately no default single composite score**: blending
five dimensions that don't share a common unit into one number would hide exactly the kind of
cross-dimension disagreement (e.g. strong in-sample results with unstable walk-forward folds) a
scorecard exists to surface — the response includes a `composite_note` explaining this rather than
a fabricated blended figure.

`POST /api/model/compare-versions` runs the same backtest engine for both supported model versions
(`1.0`, `1.1`) over an identical period, and — if forward paper-trading portfolio IDs are supplied
for each — reports their real observed sample sizes and returns too. The methodology string
explicitly disclaims any claim of statistical superiority: forward sample sizes are typically small
enough that a few points of return difference between versions is ordinary noise, not evidence of a
better model.

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
- **`STALE`** — the [data quality layer](#data-quality-layer) found the latest candle to be more
  than 5 days old; shown instead of `HISTORICAL` so the UI never implies fresher data than it has.
- **`UNAVAILABLE`** — Yahoo Finance could not be reached or returned no usable data.

Every response's `meta` also carries a `data_quality` object (duplicate timestamps, missing OHLC
values, negative prices, invalid High/Low relationships, invalid volume, suspicious gaps, and the
staleness flag) - see [Data Quality Layer](#data-quality-layer).

The signal endpoint additionally reports `signal_timeframe` (always `"Daily"` today),
`signal_generated_at`, `latest_candle_date`, and `is_latest_candle_complete` (false when the
market is open and the latest daily candle is still forming) so the UI never implies a daily
model is a tick-by-tick real-time signal. `retrieved_at` (when this server fetched the data),
`latest_market_timestamp` (the data's own timestamp), and `signal_generated_at` (when the signal
was computed) are three distinct fields precisely so freshness, data age, and signal age are never
conflated into one ambiguous "updated" label.

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

**349 tests** in `backend/tests/` (313 unit/component + 36 real-network integration) cover: ticker
validation, every indicator calculation (SMA, EMA,
RSI, MACD, Bollinger Bands, ATR, ROC, historical volatility, relative volume) plus the interpretation
layer that turns them into UI text (regression-tested after a real bug where the Bollinger lower-band
description was accidentally copied from the upper band), signal scoring and threshold mapping under
**both model versions** with configurable thresholds, confidence methodology, risk assessment,
signal history/stability/change-detection/invalidation-conditions/performance analytics, market
regime/relative-strength/sector comparison, regime-conditioned performance, fundamental data
extraction and scoring, the extended Model Evaluation metrics suite (CAGR, Sortino, Calmar,
drawdown recovery, expectancy, exposure, turnover, beta/alpha/tracking-error/information-ratio),
backtesting (transaction costs, slippage, drawdown, Sharpe, trade stats), out-of-sample validation,
parameter sensitivity (including the `PARAMETER_INERT` detection above), walk-forward analysis
(including a regression test that recent folds are preferred over the oldest ones), Monte Carlo
robustness (including reproducibility with a fixed seed), the data-quality validation layer
(constructed with deliberately corrupted synthetic OHLCV data - duplicates, negative prices,
impossible High/Low relationships, negative volume, gaps, staleness), advanced paper trading
(position sizing, stop-loss/take-profit/trailing-stop auto-exits, cost breakdown, portfolio risk
warnings, all with an isolated temp-directory store and mocked quotes), watchlist CRUD, and
API-level tests (response shape, error mapping, disclaimer content) with `yfinance` calls
monkeypatched for speed and determinism.

**V4 additions:** indicator-period sensitivity (including the equivalence proof that the isolated
parametrized-indicator path matches production output bit-for-bit at defaults) and its 2D heatmap;
persistent paper-trading equity snapshots (append-only/no-duplicate/no-shrink invariants, benchmark
proportionality, daily-P&L-since-last-recorded-observation semantics); the Forward Validation engine
(insufficient-sample thresholds, mixed-model-version detection, drawdown from a real recorded
curve); portfolio backtesting (no-look-ahead across a basket, cash/equity invariants under forced
funding-shortfall stress, every allocation method, every constraint, and the funding-basis
regression described in [Portfolio Backtesting](#portfolio-backtesting)); stock comparison
(including the historical-volatility double-scaling regression); the Model Scorecard and
model-vs-model comparison (dimension-labeling logic against each underlying engine's real output
shape); and a dedicated timezone-regression file (`test_v4_timezone_regression.py`) that
tz-localizes synthetic fixtures for every new V4 module that aligns dates across tickers or against
a benchmark — a tz-naive fixture would not have caught any of the three prior real timezone bugs
this project has hit, so it can't be trusted to catch a fourth.

**The most important test file is `tests/test_v3_no_look_ahead.py`**: rather than only proving
indicators are unaffected by *truncating* future data (the older, weaker test), it directly proves
that *mutating* future prices to a completely different, independently-generated path never changes
a signal, an indicator value, a signal-history entry, or a backtest trade decided before that point -
for the signal engine, the full signal history, and the backtest engine.

`tests/test_integration_real_data.py` is a **separate, real-network** suite that hits live Yahoo
Finance data for `AAPL`, `MSFT`, `NVDA`, and an invalid ticker — covering the overview, technical,
signal (incl. model version/score breakdown/stability), signal-history, fundamentals,
relative-strength, market-regime, regime-performance, model-info, out-of-sample, sensitivity,
walk-forward, Monte Carlo, watchlist, paper-trade, and backtest (incl. `advanced_metrics`)
endpoints — and inspects the actual returned structure (not just HTTP 200). It auto-skips if no
network access is available.

Two real bugs were found and fixed via real-data testing during this pass (both timezone-naive vs.
timezone-aware datetime mismatches - real yfinance data is tz-aware, synthetic test fixtures were
not, so unit tests alone did not catch them): `beta`/`alpha`/`tracking_error`/`information_ratio`
silently returning `null` even with a valid benchmark supplied, and a crash in regime-conditioned
performance. Both now have dedicated regression tests using a tz-localized fixture.

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

## Known Limitations & Remaining Work

Documented honestly rather than silently omitted:

- **Parameter sensitivity** covers score thresholds and RSI/SMA/MACD periods, but not Bollinger
  period/stddev, ATR period, ROC period, volume-SMA period, or signal-category weights - see
  [Parameter Sensitivity & Robustness](#parameter-sensitivity--robustness).
- **Portfolio-level paper-trading risk metrics** (volatility, Sharpe, drawdown) now have the
  persisted daily equity-curve history they need (see [Paper Trading](#paper-trading) and
  [Forward Validation](#forward-validation-paper-trading--backtesting)), but are surfaced there and
  in the Model Scorecard rather than added to the original lightweight `GET /api/paper-portfolio/risk`
  dashboard, which still reports exposure/cash/concentration only.
- **Multiple concurrent forward-paper simulations** per model/strategy variant are supported only
  through the existing `portfolio_id` mechanism (distinct IDs = distinct, independently-tracked
  simulations with their own equity history) - there is no dedicated UI for creating/naming/listing
  many simulations side by side yet.
- **Portfolio backtesting constraint interactions** (e.g. a sector cap combined with a tight cash
  allocation) are resolved by sequential waterfall passes documented in
  [Portfolio Backtesting](#portfolio-backtesting), not a joint optimizer - correct and tested, but
  not the global-optimum allocation a full solver would produce.
- **Stock comparison** shows retrieved values side by side with no cross-ticker normalization or
  ranking by design (see [Stock Comparison](#stock-comparison)) - there is no "which of these is
  better" score, intentionally.
- **The Model Scorecard** does not compute a default composite score across its five dimensions,
  by design - see [Model Scorecard & Model-vs-Model Comparison](#model-scorecard--model-vs-model-comparison).
- **Custom strategy parameters** (a UI for overriding thresholds/weights outside of the sensitivity
  endpoint, with an explicit "CUSTOM MODEL" label) are not exposed beyond the `model_version` and
  sensitivity-analysis paths already described above.
- The watchlist and paper-trading stores are single-user JSON files with no authentication - fine
  for local/personal use, not suitable for multi-tenant deployment without adding a real user
  system first.
- Sector peer comparison covers a curated set of ~11 GICS-style sectors
  (`app.config.SECTOR_PEER_MAP`) - a ticker outside that map shows an explicit "unavailable" state.
