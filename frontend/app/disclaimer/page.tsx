import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata = { title: "Financial Disclaimer — Stock Analyst" };

export default function DisclaimerPage() {
  return (
    <LegalPageShell title="Financial Disclaimer" lastUpdated="2026-09-04">
      <p>
        Stock Analyst is a <strong>research and educational tool</strong>. Nothing in this application
        constitutes personalized investment advice, a recommendation to buy or sell any security, or a
        solicitation of any kind.
      </p>

      <h2>What this application actually does</h2>
      <p>
        Every signal, score, and backtest result is the output of a fixed, deterministic, rules-based
        quantitative model applied to historical or current market data retrieved from Yahoo Finance. There is
        no artificial intelligence, machine learning, or language model in the signal-generation or
        quant-analysis logic - the same inputs always produce the same outputs, and every calculation can be
        traced back to a documented formula.
      </p>

      <h2>Not personalized advice</h2>
      <p>
        This tool has no knowledge of your financial situation, risk tolerance, time horizon, tax situation, or
        goals. A BUY, SELL, or HOLD label is a description of what a generic rules-based model concluded from
        historical price/volume data - never a suggestion tailored to you.
      </p>

      <h2>Past performance is not indicative of future results</h2>
      <p>
        Backtests, walk-forward analyses, Monte Carlo simulations, and paper-trading results describe how a
        strategy would have performed on historical data, or how it is performing in a simulated forward test.
        None of this guarantees, predicts, or implies similar performance in the future. Markets change; a
        model that performed well historically can perform poorly going forward, and vice versa.
      </p>

      <h2>Paper trading is not real trading</h2>
      <p>
        The paper-trading feature simulates trades using real, live-retrieved market quotes, but no real money
        is ever involved, no broker is ever contacted, and no real order is ever placed. It exists to let you
        observe how a strategy behaves against real, forward-arriving data without financial risk.
      </p>

      <h2>Data may be delayed, incomplete, or unavailable</h2>
      <p>
        Market data is sourced from Yahoo Finance via the yfinance library and may be delayed, incomplete, or
        temporarily unavailable. This application labels data honestly (LIVE, DELAYED, MARKET_CLOSED,
        HISTORICAL, STALE, or UNAVAILABLE) rather than presenting stale or missing data as current. You are
        responsible for independently verifying any information before acting on it.
      </p>

      <h2>No guarantees</h2>
      <ul>
        <li>This application does not guarantee profits, and does not eliminate the risk of loss.</li>
        <li>This application is not a licensed investment adviser, broker-dealer, or financial institution.</li>
        <li>No output of this application should be construed as superior to advice from a qualified, licensed financial professional.</li>
      </ul>

      <h2>Your responsibility</h2>
      <p>
        You are solely responsible for any investment or trading decisions you make, whether or not informed by
        this application. Consult a qualified, licensed financial adviser before making investment decisions.
      </p>
    </LegalPageShell>
  );
}
