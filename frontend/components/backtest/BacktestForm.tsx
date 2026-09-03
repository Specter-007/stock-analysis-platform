"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import type { BacktestRequestPayload } from "@/types/api";

const todayIso = () => new Date().toISOString().slice(0, 10);
const yearsAgoIso = (years: number) => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  return d.toISOString().slice(0, 10);
};

export function BacktestForm({
  onSubmit,
  loading,
  initialTicker,
}: {
  onSubmit: (payload: BacktestRequestPayload) => void;
  loading: boolean;
  initialTicker?: string;
}) {
  const [ticker, setTicker] = useState(initialTicker ?? "AAPL");
  const [startDate, setStartDate] = useState(yearsAgoIso(3));
  const [endDate, setEndDate] = useState(todayIso());
  const [initialCapital, setInitialCapital] = useState(10000);
  const [transactionCostBps, setTransactionCostBps] = useState(5);
  const [slippageBps, setSlippageBps] = useState(5);
  const [benchmarkTicker, setBenchmarkTicker] = useState("SPY");
  const [formError, setFormError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!ticker.trim()) {
      setFormError("Enter a ticker symbol.");
      return;
    }
    if (new Date(startDate) >= new Date(endDate)) {
      setFormError("Start date must be before end date.");
      return;
    }
    if (initialCapital <= 0) {
      setFormError("Initial capital must be greater than zero.");
      return;
    }

    onSubmit({
      ticker: ticker.trim().toUpperCase(),
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      transaction_cost_bps: transactionCostBps,
      slippage_bps: slippageBps,
      benchmark_ticker: benchmarkTicker.trim() ? benchmarkTicker.trim().toUpperCase() : null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Field label="Ticker">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="input"
            placeholder="AAPL"
            required
          />
        </Field>
        <Field label="Benchmark (optional)">
          <input
            value={benchmarkTicker}
            onChange={(e) => setBenchmarkTicker(e.target.value)}
            className="input"
            placeholder="SPY"
          />
        </Field>
        <Field label="Start Date">
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="input" required />
        </Field>
        <Field label="End Date">
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="input" required />
        </Field>
        <Field label="Initial Capital ($)">
          <input
            type="number"
            min={1}
            step={1}
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            className="input"
            required
          />
        </Field>
        <Field label="Transaction Cost (bps)">
          <input
            type="number"
            min={0}
            max={1000}
            step={1}
            value={transactionCostBps}
            onChange={(e) => setTransactionCostBps(Number(e.target.value))}
            className="input"
          />
        </Field>
        <Field label="Slippage (bps)">
          <input
            type="number"
            min={0}
            max={1000}
            step={1}
            value={slippageBps}
            onChange={(e) => setSlippageBps(Number(e.target.value))}
            className="input"
          />
        </Field>
        <Field label="Signal Timeframe">
          <input value="Daily" disabled className="input opacity-60 cursor-not-allowed" />
        </Field>
      </div>

      {formError && <p className="text-xs text-bearish">{formError}</p>}

      <div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer transition-opacity"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {loading ? "Running backtest..." : "Run Backtest"}
        </button>
      </div>

      <style jsx>{`
        .input {
          background: var(--color-bg-elevated);
          border: 1px solid var(--color-border-strong);
          border-radius: 0.375rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          color: var(--color-text-primary);
          width: 100%;
        }
        .input:focus-visible {
          outline: 2px solid var(--color-accent);
          outline-offset: 1px;
        }
      `}</style>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      {children}
    </label>
  );
}
