"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { runWalkForward, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";
import type { WalkForwardResponse } from "@/types/api";

export function WalkForwardPanel({
  ticker,
  initialCapital,
  transactionCostBps,
  slippageBps,
}: {
  ticker: string;
  initialCapital: number;
  transactionCostBps: number;
  slippageBps: number;
}) {
  const [trainYears, setTrainYears] = useState(2);
  const [testYears, setTestYears] = useState(1);
  const [maxFolds, setMaxFolds] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<WalkForwardResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await runWalkForward({
        ticker,
        train_years: trainYears,
        test_years: testYears,
        max_folds: maxFolds,
        initial_capital: initialCapital,
        transaction_cost_bps: transactionCostBps,
        slippage_bps: slippageBps,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Walk-forward analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Walk-Forward Analysis"
        subtitle="Same fixed model re-run on several sequential, non-overlapping periods"
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <NumberField label="Train Years" value={trainYears} onChange={setTrainYears} step={0.5} min={0.5} max={10} />
        <NumberField label="Test Years" value={testYears} onChange={setTestYears} step={0.5} min={0.5} max={5} />
        <NumberField label="Max Folds" value={maxFolds} onChange={setMaxFolds} step={1} min={1} max={8} />
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

      {result && (
        <>
          <div className="flex gap-6 mb-4 text-xs">
            <div>
              <p className="text-text-faint uppercase text-[10px] tracking-wide mb-0.5">Avg. Test Return</p>
              <p className="text-text-primary font-medium tabular">{formatPercent(result.average_test_return_percent)}</p>
            </div>
            <div>
              <p className="text-text-faint uppercase text-[10px] tracking-wide mb-0.5">Positive Folds</p>
              <p className="text-text-primary font-medium tabular">
                {result.folds_with_positive_return} / {result.folds.length}
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[600px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Fold</th>
                  <th className="pb-2">Test Period</th>
                  <th className="pb-2 text-right">Return</th>
                  <th className="pb-2 text-right">Buy &amp; Hold</th>
                  <th className="pb-2 text-right">Max DD</th>
                  <th className="pb-2 text-right">Sharpe</th>
                  <th className="pb-2 text-right">Trades</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.folds.map((f) => (
                  <tr key={f.fold_index}>
                    <td className="py-2 text-text-secondary">#{f.fold_index}</td>
                    <td className="py-2 text-text-secondary tabular">
                      {f.test_start} → {f.test_end}
                    </td>
                    <td
                      className={clsx(
                        "py-2 text-right tabular font-medium",
                        (f.test_total_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                      )}
                    >
                      {formatPercent(f.test_total_return_percent)}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {formatPercent(f.test_buy_hold_return_percent)}
                    </td>
                    <td className="py-2 text-right tabular text-bearish">{formatPercent(f.test_max_drawdown_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {f.test_sharpe_ratio === null ? "N/A" : f.test_sharpe_ratio.toFixed(2)}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">{f.test_number_of_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-[11px] text-text-faint leading-relaxed mt-3">{result.methodology}</p>
        </>
      )}
    </Card>
  );
}

function NumberField({
  label,
  value,
  onChange,
  step,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step: number;
  min: number;
  max: number;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-24"
      />
    </label>
  );
}
