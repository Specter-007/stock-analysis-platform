"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { runCostStress, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";
import type { CostStressResponse } from "@/types/api";

export function CostStressPanel({
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CostStressResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await runCostStress({
        ticker,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        base_commission_bps: transactionCostBps,
        base_slippage_bps: slippageBps,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cost stress test failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Transaction-Cost Stress Test"
        subtitle="Same trades, higher friction - does the edge survive, or is it razor-thin relative to trading costs?"
      />
      <button
        onClick={run}
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer mb-4"
      >
        {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
        Run
      </button>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <p className="text-xs text-text-muted">
            Gross return (zero commission, zero slippage): <span className="text-text-primary tabular font-medium">{formatPercent(result.gross_return_percent)}</span>
          </p>

          <div>
            <p className="text-xs text-text-muted font-medium mb-2">Commission Scaling (slippage held at base)</p>
            <ScenarioTable scenarios={result.commission_scenarios} />
          </div>

          <div>
            <p className="text-xs text-text-muted font-medium mb-2">Slippage Sweep (commission held at base)</p>
            <ScenarioTable scenarios={result.slippage_scenarios} />
          </div>

          <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology}</p>
        </div>
      )}
    </Card>
  );
}

function ScenarioTable({ scenarios }: { scenarios: CostStressResponse["commission_scenarios"] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs min-w-[500px]">
        <thead>
          <tr className="text-left text-text-faint uppercase tracking-wide">
            <th className="pb-2">Scenario</th>
            <th className="pb-2 text-right">Commission</th>
            <th className="pb-2 text-right">Slippage</th>
            <th className="pb-2 text-right">Net Return</th>
            <th className="pb-2 text-right">Total Cost</th>
            <th className="pb-2 text-right">Sharpe</th>
            <th className="pb-2 text-right">Max DD</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {scenarios.map((s) => (
            <tr key={s.label}>
              <td className="py-2 text-text-primary font-medium">{s.label}</td>
              <td className="py-2 text-right tabular text-text-secondary">{s.commission_bps} bps</td>
              <td className="py-2 text-right tabular text-text-secondary">{s.slippage_bps} bps</td>
              <td className={clsx("py-2 text-right tabular font-medium", (s.net_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish")}>
                {formatPercent(s.net_return_percent)}
              </td>
              <td className="py-2 text-right tabular text-text-secondary">{formatPercent(s.total_cost_percent)}</td>
              <td className="py-2 text-right tabular text-text-secondary">{s.sharpe_ratio === null ? "N/A" : s.sharpe_ratio.toFixed(2)}</td>
              <td className="py-2 text-right tabular text-bearish">{formatPercent(s.max_drawdown_percent)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
