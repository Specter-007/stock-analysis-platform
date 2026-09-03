"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { compareModelVersions, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";
import type { ModelComparisonResponse } from "@/types/api";

export function ModelVersionComparisonPanel() {
  const [ticker, setTicker] = useState("AAPL");
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [portfolioV1, setPortfolioV1] = useState("");
  const [portfolioV2, setPortfolioV2] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ModelComparisonResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await compareModelVersions({
        ticker: ticker.trim().toUpperCase(),
        start_date: startDate,
        end_date: endDate,
        forward_portfolio_id_v1: portfolioV1.trim() || null,
        forward_portfolio_id_v2: portfolioV2.trim() || null,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Model comparison failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Model v1.0 vs v1.1"
        subtitle="Same backtest engine, same period, different scoring version - not a claim that one is statistically better."
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
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Start Date</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">End Date</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">v1.0 Forward Portfolio (optional)</span>
          <input
            value={portfolioV1}
            onChange={(e) => setPortfolioV1(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-40"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">v1.1 Forward Portfolio (optional)</span>
          <input
            value={portfolioV2}
            onChange={(e) => setPortfolioV2(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-40"
          />
        </label>
        <button
          onClick={run}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Compare
        </button>
      </div>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="overflow-x-auto">
            <p className="text-xs text-text-muted font-medium mb-2">Backtest Comparison</p>
            <table className="w-full text-xs min-w-[560px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Version</th>
                  <th className="pb-2 text-right">Total Return</th>
                  <th className="pb-2 text-right">CAGR</th>
                  <th className="pb-2 text-right">Sharpe</th>
                  <th className="pb-2 text-right">Max DD</th>
                  <th className="pb-2 text-right">Trades</th>
                  <th className="pb-2 text-right">Win Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.backtest_comparison.map((r) => (
                  <tr key={r.model_version}>
                    <td className="py-2 text-text-primary font-medium">v{r.model_version}</td>
                    <td
                      className={clsx(
                        "py-2 text-right tabular font-medium",
                        (r.total_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                      )}
                    >
                      {formatPercent(r.total_return_percent)}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatPercent(r.cagr_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {r.sharpe_ratio === null ? "N/A" : r.sharpe_ratio.toFixed(2)}
                    </td>
                    <td className="py-2 text-right tabular text-bearish">{formatPercent(r.max_drawdown_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{r.number_of_trades}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatPercent(r.win_rate_percent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.forward_comparison.length > 0 && (
            <div className="overflow-x-auto">
              <p className="text-xs text-text-muted font-medium mb-2">Forward Paper-Trading Comparison</p>
              <table className="w-full text-xs min-w-[480px]">
                <thead>
                  <tr className="text-left text-text-faint uppercase tracking-wide">
                    <th className="pb-2">Version</th>
                    <th className="pb-2">Portfolio</th>
                    <th className="pb-2 text-right">Days Observed</th>
                    <th className="pb-2 text-right">Return</th>
                    <th className="pb-2 text-right">Sample</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {result.forward_comparison.map((r) => (
                    <tr key={r.model_version}>
                      <td className="py-2 text-text-primary font-medium">v{r.model_version}</td>
                      <td className="py-2 text-text-secondary font-mono">{r.portfolio_id}</td>
                      <td className="py-2 text-right tabular text-text-secondary">{r.trading_days_observed}</td>
                      <td className="py-2 text-right tabular text-text-secondary">{formatPercent(r.total_return_percent)}</td>
                      <td className="py-2 text-right">
                        {r.insufficient_sample ? (
                          <span className="text-[10px] uppercase text-warning">Insufficient</span>
                        ) : (
                          <span className="text-[10px] uppercase text-bullish">OK</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology}</p>
        </div>
      )}
    </Card>
  );
}
