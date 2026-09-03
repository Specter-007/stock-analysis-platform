"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { getModelScorecard, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import type { ScorecardResponse, ScorecardLabel } from "@/types/api";

const LABEL_STYLE: Record<ScorecardLabel, string> = {
  STRONG: "text-bullish bg-bullish/10 border-bullish/25",
  MODERATE: "text-warning bg-warning-dim border-warning/25",
  WEAK: "text-bearish bg-bearish/10 border-bearish/25",
  INSUFFICIENT_DATA: "text-text-faint bg-bg-elevated border-border",
  NOT_PROVIDED: "text-text-faint bg-bg-elevated border-border",
};

const DIMENSION_LABELS: Record<string, string> = {
  OUT_OF_SAMPLE_STRENGTH: "Out-of-Sample Strength",
  ROBUSTNESS: "Robustness",
  WALK_FORWARD_STABILITY: "Walk-Forward Stability",
  REGIME_DEPENDENCY: "Regime Dependency",
  FORWARD_PAPER_DATA: "Forward Paper Data",
};

export function ModelScorecardPanel() {
  const [ticker, setTicker] = useState("AAPL");
  const [forwardPortfolioId, setForwardPortfolioId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScorecardResponse | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await getModelScorecard({
        ticker: ticker.trim().toUpperCase(),
        forward_portfolio_id: forwardPortfolioId.trim() || null,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Scorecard generation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Model Scorecard"
        subtitle="Five independent dimensions - never blended into one number. Runs several backtests, so this may take up to 15-20 seconds."
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
          <span className="text-text-muted font-medium">Forward Paper Portfolio ID (optional)</span>
          <input
            value={forwardPortfolioId}
            onChange={(e) => setForwardPortfolioId(e.target.value)}
            placeholder="e.g. default"
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-48"
          />
        </label>
        <button
          onClick={run}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          Generate
        </button>
      </div>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result && (
        <div className="flex flex-col gap-3">
          {result.dimensions.map((d) => (
            <div key={d.name} className="border border-border rounded-lg p-3">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <p className="text-sm font-medium text-text-primary">{DIMENSION_LABELS[d.name] ?? d.name}</p>
                <span className={clsx("text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border", LABEL_STYLE[d.label])}>
                  {d.label.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-xs text-text-muted leading-relaxed mb-2">{d.detail}</p>
              {Object.keys(d.supporting_metrics).length > 0 && (
                <div className="flex flex-wrap gap-3 text-[11px] text-text-faint">
                  {Object.entries(d.supporting_metrics).map(([k, v]) => (
                    <span key={k}>
                      {k.replace(/_/g, " ")}: <span className="text-text-secondary tabular">{v === null ? "N/A" : String(v)}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}

          <p className="text-[11px] text-text-faint leading-relaxed mt-1">{result.composite_note}</p>
          <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology}</p>
        </div>
      )}
    </Card>
  );
}
