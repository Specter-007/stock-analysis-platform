"use client";

import { useState } from "react";
import { Play, Loader2, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { getModelDrift, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import type { DistributionComparison, DriftResponse } from "@/types/api";

export function ModelDriftPanel() {
  const [ticker, setTicker] = useState("AAPL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DriftResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await getModelDrift({ ticker: ticker.trim().toUpperCase() });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Drift analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Model Drift"
        subtitle="Recent signal/factor/regime behavior vs. the historical baseline that precedes it - a documented threshold, not a hypothesis test."
      />
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Ticker</span>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-28"
          />
        </label>
        <button
          onClick={run}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Analyze
        </button>
      </div>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          {result.insufficient_data ? (
            <p className="text-xs text-text-muted">
              Not enough sessions to compare ({result.historical_sessions} historical, {result.recent_sessions} recent).
            </p>
          ) : (
            <>
              <p className="text-[11px] text-text-faint">
                Historical: {result.historical_sessions} sessions · Recent: {result.recent_sessions} sessions
              </p>
              {result.signal_distribution && <DistributionCard title="Signal Distribution" data={result.signal_distribution} />}
              {result.factor_distribution && <DistributionCard title="Factor Contribution Mix" data={result.factor_distribution} />}
              {result.regime_distribution && <DistributionCard title="Regime Distribution" data={result.regime_distribution} />}
            </>
          )}
          <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology}</p>
        </div>
      )}
    </Card>
  );
}

function DistributionCard({ title, data }: { title: string; data: DistributionComparison }) {
  const buckets = Array.from(new Set([...Object.keys(data.historical_percent), ...Object.keys(data.recent_percent)]));
  return (
    <div className="border border-border rounded-lg p-3">
      <div className="flex items-center justify-between gap-2 mb-2">
        <p className="text-sm font-medium text-text-primary">{title}</p>
        {data.flagged ? (
          <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border text-warning bg-warning-dim border-warning/25">
            <AlertTriangle size={10} /> Shifted
          </span>
        ) : (
          <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border text-text-faint bg-bg-elevated border-border">Stable</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[300px]">
          <thead>
            <tr className="text-left text-text-faint uppercase tracking-wide">
              <th className="pb-1.5">Bucket</th>
              <th className="pb-1.5 text-right">Historical</th>
              <th className="pb-1.5 text-right">Recent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {buckets.map((b) => (
              <tr key={b} className={clsx(data.shifted_buckets.includes(b) && "bg-warning-dim/40")}>
                <td className="py-1.5 text-text-secondary">{b}</td>
                <td className="py-1.5 text-right tabular text-text-primary">{(data.historical_percent[b] ?? 0).toFixed(1)}%</td>
                <td className="py-1.5 text-right tabular text-text-primary">{(data.recent_percent[b] ?? 0).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
