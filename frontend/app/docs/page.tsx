import Link from "next/link";

export const metadata = { title: "Documentation — Stock Analyst" };

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "methodology", label: "Methodology & Signals" },
  { id: "backtesting", label: "Backtesting" },
  { id: "walk-forward", label: "Walk-Forward Analysis" },
  { id: "monte-carlo", label: "Monte Carlo" },
  { id: "sensitivity", label: "Parameter Sensitivity" },
  { id: "cost-stress", label: "Cost Stress Testing" },
  { id: "paper-trading", label: "Paper Trading & Forward Validation" },
  { id: "model-drift", label: "Model Drift Monitoring" },
  { id: "data-quality", label: "Data Quality & Freshness" },
  { id: "limitations", label: "Known Limitations" },
];

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-8 flex gap-8">
      <nav className="hidden lg:block w-56 shrink-0 sticky top-20 self-start" aria-label="Documentation sections">
        <p className="text-xs uppercase tracking-wide text-text-faint mb-2">On this page</p>
        <ul className="flex flex-col gap-1">
          {SECTIONS.map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`} className="block text-xs text-text-muted hover:text-text-primary py-1">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="min-w-0 flex-1 flex flex-col gap-10 text-sm text-text-secondary leading-relaxed [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-text-primary [&_h2]:mb-3 [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:flex [&_ul]:flex-col [&_ul]:gap-1.5 [&_ul]:mb-3 [&_strong]:text-text-primary [&_code]:font-mono [&_code]:text-xs [&_code]:bg-bg-elevated [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded">
        <header id="overview">
          <h1 className="text-2xl font-semibold text-text-primary mb-2">Documentation</h1>
          <p>
            Stock Analyst is a quantitative research terminal: a deterministic, rules-based signal engine, a
            historical backtesting suite, statistical robustness tools, and a paper-trading forward-validation
            environment - all built on real Yahoo Finance market data. There is no AI or language model
            anywhere in the signal-generation or quant-analysis logic. See the{" "}
            <Link href="/disclaimer" className="text-accent hover:underline">Financial Disclaimer</Link> before
            interpreting anything below as investment advice (it is not).
          </p>
        </header>

        <section id="methodology">
          <h2>Methodology & Signals</h2>
          <p>
            Every signal is computed from the latest available <strong>daily</strong> candle using a fixed
            point-scoring model across four categories - Trend (price vs. 20/50/200-day SMA), Momentum (RSI,
            MACD, Rate of Change), Volume (price move confirmed or contradicted by relative volume), and
            Volatility (the stock&apos;s own trailing volatility regime). A factor is included only when there
            is enough history to compute it honestly - never approximated.
          </p>
          <p>
            The raw score is normalized (model version <strong>1.1</strong>, the default) against the fixed
            theoretical min/max across all eight possible factors, so the same factor condition always
            contributes the same amount regardless of ticker. An older normalization (<strong>1.0</strong>)
            remains available for reference but is not the default. A signal means: &quot;this fixed model,
            applied to the latest available data, classifies current conditions as BUY&quot; - not &quot;buy
            this stock.&quot;
          </p>
        </section>

        <section id="backtesting">
          <h2>Backtesting</h2>
          <p>
            Backtests execute next-bar (the signal on day N can only affect the trade filled on day N+1&apos;s
            open) to avoid look-ahead bias, and charge configurable commission and slippage on every fill. An
            optional Out-of-Sample split partitions history into in-sample/validation/out-of-sample thirds and
            re-runs the same fixed model (there is no parameter-fitting step to overfit) on the held-out third.
          </p>
        </section>

        <section id="walk-forward">
          <h2>Walk-Forward Analysis</h2>
          <p>
            Because this signal engine has no trainable parameters, walk-forward here does not mean
            re-fitting a model on a rolling training window - it means partitioning history into sequential
            train/test windows and re-running the identical fixed model on each test window, to check whether
            performance is consistent across different market regimes rather than an artifact of one period.
          </p>
        </section>

        <section id="monte-carlo">
          <h2>Monte Carlo</h2>
          <p>
            One backtest is run, then its own historical trade returns (or daily returns, as a fallback) are
            bootstrap-resampled to build many simulated equity paths - reporting percentile outcomes, the
            probability of ending below initial capital, and the probability of exceeding a chosen drawdown
            threshold. Trade-level returns use an independent (IID) bootstrap; the daily-returns fallback uses
            a <strong>block bootstrap</strong> (contiguous chunks) specifically because daily returns from a
            persistent position are autocorrelated - an IID bootstrap would understate real path risk. This is
            a stress/robustness check on the sample actually observed, explicitly <strong>not</strong> a
            forecast, and is fully reproducible given the same seed.
          </p>
        </section>

        <section id="sensitivity">
          <h2>Parameter Sensitivity</h2>
          <p>
            Sweeps individual thresholds/indicator periods one at a time and reports whether performance is
            stable across nearby values (a &quot;robust region&quot;) or highly sensitive to the exact value
            chosen. This is a disclosure tool, not an optimizer - the application never automatically selects
            or applies the &quot;best&quot; parameter value it finds; that would risk overfitting to one
            historical sample and is explicitly out of scope by design.
          </p>
        </section>

        <section id="cost-stress">
          <h2>Cost Stress Testing</h2>
          <p>
            Answers a narrower question than Monte Carlo: does an edge survive higher trading friction, or is
            it razor-thin? Commission is scaled independently from slippage (they are economically different
            frictions), and the zero-cost baseline is computed once and reused so every scenario reflects an
            identical sequence of trades with only the cost model differing.
          </p>
        </section>

        <section id="paper-trading">
          <h2>Paper Trading & Forward Validation</h2>
          <p>
            Paper trading simulates trades using real, live-retrieved quotes - no real money, no broker, no
            real order. It is fundamentally different from a backtest: a backtest replays history, while
            paper-trading forward validation records one real, append-only observation per real trading day as
            it actually arrives. Metrics from a small number of observed days are explicitly flagged as an
            insufficient sample rather than presented as if they were statistically meaningful.
          </p>
        </section>

        <section id="model-drift">
          <h2>Model Drift Monitoring</h2>
          <p>
            Compares the distribution of recent signals/factors/market regimes against a longer historical
            baseline using a disclosed percentage-point threshold. This is a transparent heuristic, explicitly{" "}
            <strong>not</strong> a formal statistical hypothesis test (daily signals are highly autocorrelated,
            so the independence assumption a classical test requires would not hold), and it never
            automatically retrains or modifies the model.
          </p>
        </section>

        <section id="data-quality">
          <h2>Data Quality & Freshness</h2>
          <p>
            Every market-data response is labeled honestly: <code>LIVE</code>, <code>DELAYED</code>,{" "}
            <code>MARKET_CLOSED</code>, <code>HISTORICAL</code>, or <code>UNAVAILABLE</code>. OHLCV data is
            validated for chronological ordering, duplicate timestamps, missing values, and impossible prices
            before any indicator is computed on it. The application never claims data is real-time unless the
            source actually guarantees that, and never fabricates a data point that was not actually retrieved.
          </p>
        </section>

        <section id="limitations">
          <h2>Known Limitations</h2>
          <ul>
            <li>Forward paper-trading simulation currently supports single-ticker experiments only, not multi-ticker portfolio experiments.</li>
            <li>Model drift and sensitivity results are heuristic disclosures, not formal statistical guarantees.</li>
            <li>Market data depends on Yahoo Finance&apos;s availability and accuracy - this application does not control or guarantee it.</li>
            <li>The command palette&apos;s search currently covers page navigation and ticker lookup; full-text search across your own experiment/watchlist names is not yet implemented.</li>
            <li>This documentation summarizes the methodology at a high level - see the project README for the complete technical detail.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
