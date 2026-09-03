# Stock Analyst

A quantitative stock research and technical-analysis platform. It retrieves real market data
from Yahoo Finance (via `yfinance`) and runs it through a transparent, deterministic rules-based
scoring engine to classify each ticker as **Strong Buy / Buy / Hold / Sell / Strong Sell** — with
every contributing factor shown, not hidden behind a black box.

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
11. [Indicator Definitions](#indicator-definitions)
12. [Confidence Methodology](#confidence-methodology)
13. [Backtesting Methodology](#backtesting-methodology)
14. [No-Look-Ahead-Bias Guarantee](#no-look-ahead-bias-guarantee)
15. [Data Freshness & Status Labels](#data-freshness--status-labels)
16. [yfinance / Yahoo Finance Limitations](#yfinance--yahoo-finance-limitations)
17. [Financial Disclaimer](#financial-disclaimer)
18. [Testing](#testing)
19. [Deployment Considerations](#deployment-considerations)
20. [GitHub Setup](#github-setup)

---

## Project Overview

Stock Analyst has four sections:

- **Overview** — what the platform does, a ticker search, and the methodology summary.
- **Markets** — major index quotes and gainers/losers from a fixed watchlist, all real data.
- **Stock Analysis** — the core page: real-time-delayed quote, an interactive OHLC/candlestick
  chart with SMA overlays, the deterministic BUY/HOLD/SELL signal with its full factor breakdown,
  technical indicators grouped by category, a risk panel, and company information.
- **Backtesting** — runs the exact same signal engine against historical data to simulate a
  long/flat trading strategy, compared against buy-and-hold and a benchmark (default `SPY`).

**The recommendation engine contains no machine learning and no LLM call.** It is a fixed,
documented point-scoring system over technical indicators. Given the same input data, it always
produces the same output.

## Features

- Real OHLCV and fundamental data from Yahoo Finance via `yfinance` — no fabricated or hardcoded
  production data anywhere.
- Explicit data-freshness labeling on every response: `LIVE` / `DELAYED` / `MARKET_CLOSED` /
  `HISTORICAL` / `UNAVAILABLE`, plus `retrieved_at`, `latest_market_timestamp`, `market_status`,
  and `timeframe`.
- Trend, momentum, volatility, and volume indicators (SMA/EMA, RSI, MACD, ROC, ATR, Bollinger
  Bands, historical volatility, relative volume).
- A 0–100 normalized deterministic score, mapped to five signal buckets, with every contributing
  factor shown as a plain-language explanation.
- A confidence score that reflects data completeness and internal factor agreement — explicitly
  **not** a probability of future price movement.
- A risk panel built from the ticker's own actual current indicator readings (never generic text).
- A backtesting engine with realistic transaction costs, slippage, next-bar execution, and a
  documented no-look-ahead-bias contract.
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
      config.py               All tunable constants (thresholds, windows, cache TTLs)
      api/                    HTTP route handlers + exception -> HTTP mapping
      services/                yfinance wrapper, in-memory TTL cache, typed exceptions
      indicators/              Pure indicator math (trend/momentum/volatility/volume) + interpretation
      signals/                 Deterministic scoring engine, confidence, risk assessment
      backtesting/             Backtest engine + performance metrics
      models/                  Pydantic request/response schemas
      utils/                   Ticker validation, time/market-hours helpers, shared finance math
    tests/                    pytest suite (unit + API + real-network integration)

  frontend/                 Next.js (App Router) + TypeScript + Tailwind CSS
    app/                      Routes: /, /markets, /analysis, /backtest
    components/               UI, by domain: nav, search, stock, backtest, markets
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
| GET | `/api/stock/{ticker}/signal` | Deterministic signal, score, confidence, factor explanations, risk panel |
| POST | `/api/backtest` | Runs the backtest engine (see request body below) |
| GET | `/api/market/status` | Major indexes + gainers/losers from a fixed watchlist |
| GET | `/api/search?q=` | Ticker/company search (via Yahoo Finance search) |
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

**Normalization:** the raw score is normalized against the actual min/max achievable given
*only the factors available for that specific stock* — not a fixed constant — so a young stock
with fewer computable factors is still scored fairly on a proper 0–100 scale.

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
(including backtested performance) does not guarantee future results.

## Testing

```bash
cd backend
venv\Scripts\python -m pytest -q
```

The suite (`backend/tests/`) covers: ticker validation, every indicator calculation (SMA, EMA,
RSI, MACD, Bollinger Bands, ATR, ROC, historical volatility, relative volume), signal scoring and
threshold mapping, confidence methodology, risk assessment, backtesting (transaction costs,
slippage, drawdown, Sharpe, trade stats, and the no-look-ahead-bias proofs above), and API-level
tests (response shape, error mapping, disclaimer content) with `yfinance` calls monkeypatched for
speed and determinism.

`tests/test_integration_real_data.py` is a **separate, real-network** suite that hits live Yahoo
Finance data for `AAPL`, `MSFT`, `NVDA`, and an invalid ticker, and inspects the actual returned
structure (not just HTTP 200). It auto-skips if no network access is available.

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
