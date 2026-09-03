"use client";

import { useState } from "react";
import { Play, Loader2, ShieldQuestion } from "lucide-react";
import { runMonteCarlo, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";
import type { MonteCarloResponse } from "@/types/api";

export function MonteCarloPanel({
  ticker,
  startDate,
  endDate,
  initialCapital,
  transactionCostBps,
  slippageBps,
}: {
  ticker: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  transactionCostBps: number;
  slippageBps: number;
}) {
  const [simulations, setSimulations] = useState(1000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MonteCarloResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await runMonteCarlo({
        ticker,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        transaction_cost_bps: transactionCostBps,
        slippage_bps: slippageBps,
        simulations,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Monte Carlo simulation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Monte Carlo Robustness"
        subtitle="Bootstrap resampling of this backtest's own historical returns - a stress test, not a forecast"
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Simulations</span>
          <input
            type="number"
            value={simulations}
            step={100}
            min={100}
            max={5000}
            onChange={(e) => setSimulations(Number(e.target.value))}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-28"
          />
        </label>
        <button
          onClick={run}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Run
        </button>
      </div>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result &&
        (result.resampling_basis === "unavailable" ? (
          <p className="text-xs text-text-muted flex items-center gap-2">
            <ShieldQuestion size={14} /> Not enough trade or return history to run a simulation for this period.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-3">
              <Stat label="5th Percentile" value={formatPercent(result.percentile_5_return_percent)} tone="bearish" />
              <Stat label="Median Return" value={formatPercent(result.median_return_percent)} />
              <Stat label="95th Percentile" value={formatPercent(result.percentile_95_return_percent)} tone="bullish" />
              <Stat label="Median Max DD" value={formatPercent(result.median_max_drawdown_percent)} tone="bearish" />
              <Stat label="Worst Max DD" value={formatPercent(result.worst_max_drawdown_percent)} tone="bearish" />
            </div>
            <p className="text-[11px] text-text-faint">
              Based on {result.sample_size} historical {result.resampling_basis === "trade_returns" ? "trades" : "daily returns"} ·{" "}
              {result.simulations} simulations
            </p>
            <p className="text-[11px] text-text-faint leading-relaxed mt-2">{result.methodology}</p>
          </>
        ))}
    </Card>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "bullish" | "bearish" }) {
  return (
    <div className="border border-border rounded p-2.5 bg-bg-elevated">
      <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{label}</p>
      <p className={`text-sm font-medium tabular ${tone === "bullish" ? "text-bullish" : tone === "bearish" ? "text-bearish" : "text-text-primary"}`}>
        {value}
      </p>
    </div>
  );
}
