"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { runSensitivity, runSensitivityHeatmap, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";
import type { SensitivityResponse, SensitivityHeatmapResponse, SensitivityRobustness } from "@/types/api";

const ALL_PARAMETERS = [
  "buy_threshold",
  "sell_threshold",
  "rsi_period",
  "sma_short",
  "sma_long",
  "macd_fast",
  "macd_slow",
] as const;

const PARAMETER_LABELS: Record<string, string> = {
  buy_threshold: "BUY Threshold",
  sell_threshold: "SELL Threshold",
  rsi_period: "RSI Period",
  sma_short: "Short SMA",
  sma_long: "Long SMA",
  macd_fast: "MACD Fast",
  macd_slow: "MACD Slow",
};

const ROBUSTNESS_STYLE: Record<SensitivityRobustness, { label: string; className: string }> = {
  HIGHER_ROBUSTNESS: { label: "Higher Robustness", className: "text-bullish bg-bullish/10 border-bullish/25" },
  LOW_ROBUSTNESS: { label: "Low Robustness", className: "text-warning bg-warning-dim border-warning/25" },
  PARAMETER_INERT: { label: "Parameter Inert", className: "text-text-faint bg-bg-elevated border-border" },
  INSUFFICIENT_DATA: { label: "Insufficient Data", className: "text-text-faint bg-bg-elevated border-border" },
  INSUFFICIENT_SAMPLE: { label: "Insufficient Sample", className: "text-warning bg-warning-dim border-warning/25" },
};

export function SensitivityPanel({
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
  const [selected, setSelected] = useState<string[]>([...ALL_PARAMETERS]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SensitivityResponse | null>(null);

  const [heatmapX, setHeatmapX] = useState<string>("buy_threshold");
  const [heatmapY, setHeatmapY] = useState<string>("rsi_period");
  const [heatmapMetric, setHeatmapMetric] = useState<string>("cagr_percent");
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [heatmap, setHeatmap] = useState<SensitivityHeatmapResponse | null>(null);

  function toggleParameter(p: string) {
    setSelected((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await runSensitivity({
        ticker,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        transaction_cost_bps: transactionCostBps,
        slippage_bps: slippageBps,
        parameters: selected.length > 0 ? selected : undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sensitivity analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function runHeatmap() {
    setHeatmapLoading(true);
    setHeatmapError(null);
    try {
      const res = await runSensitivityHeatmap({
        ticker,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        transaction_cost_bps: transactionCostBps,
        slippage_bps: slippageBps,
        param_x: heatmapX,
        param_y: heatmapY,
        metric: heatmapMetric,
      });
      setHeatmap(res);
    } catch (err) {
      setHeatmapError(err instanceof ApiError ? err.message : "Heatmap generation failed.");
    } finally {
      setHeatmapLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Parameter Sensitivity"
        subtitle="Does performance hold up near the chosen parameter values, or only at one exact point? A parameter that only 'works' at a single value is an overfitting warning sign, not a discovery."
      />

      <div className="flex flex-wrap gap-2 mb-4">
        {ALL_PARAMETERS.map((p) => (
          <button
            key={p}
            onClick={() => toggleParameter(p)}
            className={clsx(
              "text-xs px-3 py-1.5 rounded-md border cursor-pointer transition-colors",
              selected.includes(p)
                ? "bg-accent/15 border-accent/40 text-accent"
                : "bg-bg-elevated border-border text-text-muted hover:border-border-strong"
            )}
          >
            {PARAMETER_LABELS[p]}
          </button>
        ))}
      </div>

      <button
        onClick={run}
        disabled={loading || selected.length === 0}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer mb-4"
      >
        {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
        Run Sensitivity Sweep
      </button>

      {error && <p className="text-xs text-bearish mb-3">{error}</p>}

      {result && (
        <div className="flex flex-col gap-4 mb-6">
          {result.parameters.map((p) => {
            const style = ROBUSTNESS_STYLE[p.robustness];
            return (
              <div key={p.parameter} className="border border-border rounded-lg p-3">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <p className="text-sm font-medium text-text-primary">{p.label}</p>
                  <span className={clsx("text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border", style.className)}>
                    {style.label}
                  </span>
                </div>

                <div className="overflow-x-auto mb-2">
                  <table className="w-full text-xs min-w-[500px]">
                    <thead>
                      <tr className="text-left text-text-faint uppercase tracking-wide">
                        <th className="pb-1.5">Value</th>
                        <th className="pb-1.5 text-right">Total Return</th>
                        <th className="pb-1.5 text-right">CAGR</th>
                        <th className="pb-1.5 text-right">Sharpe</th>
                        <th className="pb-1.5 text-right">Max DD</th>
                        <th className="pb-1.5 text-right">Trades</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {p.points.map((pt) => (
                        <tr key={pt.value} className={pt.is_default ? "bg-accent/5" : undefined}>
                          <td className="py-1.5 text-text-secondary tabular">
                            {pt.value}
                            {pt.is_default && <span className="text-accent ml-1 text-[10px]">(default)</span>}
                          </td>
                          <td
                            className={clsx(
                              "py-1.5 text-right tabular font-medium",
                              (pt.total_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                            )}
                          >
                            {formatPercent(pt.total_return_percent)}
                          </td>
                          <td className="py-1.5 text-right tabular text-text-secondary">{formatPercent(pt.cagr_percent)}</td>
                          <td className="py-1.5 text-right tabular text-text-secondary">
                            {pt.sharpe_ratio === null ? "N/A" : pt.sharpe_ratio.toFixed(2)}
                          </td>
                          <td className="py-1.5 text-right tabular text-bearish">{formatPercent(pt.max_drawdown_percent)}</td>
                          <td className="py-1.5 text-right tabular text-text-secondary">{pt.number_of_trades}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="flex flex-wrap gap-4 text-[11px] text-text-muted">
                  <span>
                    Best: <span className="text-text-secondary tabular">{p.best_value ?? "N/A"}</span>
                  </span>
                  <span>
                    Median: <span className="text-text-secondary tabular">{p.median_value ?? "N/A"}</span>
                  </span>
                  <span>
                    Worst: <span className="text-text-secondary tabular">{p.worst_value ?? "N/A"}</span>
                  </span>
                  {p.robust_region_min !== null && p.robust_region_max !== null && (
                    <span>
                      Robust Region:{" "}
                      <span className="text-text-secondary tabular">
                        [{p.robust_region_min}, {p.robust_region_max}]
                      </span>
                    </span>
                  )}
                </div>

                {p.note && <p className="text-[11px] text-text-faint mt-2 leading-relaxed">{p.note}</p>}
              </div>
            );
          })}

          <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology}</p>
        </div>
      )}

      <div className="border-t border-border pt-4">
        <p className="text-sm font-medium text-text-primary mb-1">2D Heatmap</p>
        <p className="text-xs text-text-muted mb-3">
          Re-runs the full backtest for every combination of two parameters. Cells with fewer than 5 trades are
          flagged as an insufficient sample rather than colored as if reliable.
        </p>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <SelectField label="X Axis" value={heatmapX} onChange={setHeatmapX} options={ALL_PARAMETERS} labels={PARAMETER_LABELS} />
          <SelectField label="Y Axis" value={heatmapY} onChange={setHeatmapY} options={ALL_PARAMETERS} labels={PARAMETER_LABELS} />
          <SelectField
            label="Metric"
            value={heatmapMetric}
            onChange={setHeatmapMetric}
            options={["cagr_percent", "total_return_percent", "sharpe_ratio", "max_drawdown_percent"]}
            labels={{
              cagr_percent: "CAGR",
              total_return_percent: "Total Return",
              sharpe_ratio: "Sharpe Ratio",
              max_drawdown_percent: "Max Drawdown",
            }}
          />
          <button
            onClick={runHeatmap}
            disabled={heatmapLoading || heatmapX === heatmapY}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {heatmapLoading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            Generate
          </button>
        </div>

        {heatmapX === heatmapY && <p className="text-xs text-warning mb-3">X and Y axes must be different parameters.</p>}
        {heatmapError && <p className="text-xs text-bearish mb-3">{heatmapError}</p>}

        {heatmap && <HeatmapGrid heatmap={heatmap} />}
      </div>
    </Card>
  );
}

function HeatmapGrid({ heatmap }: { heatmap: SensitivityHeatmapResponse }) {
  const xValues = Array.from(new Set(heatmap.cells.map((c) => c.x_value))).sort((a, b) => a - b);
  const yValues = Array.from(new Set(heatmap.cells.map((c) => c.y_value))).sort((a, b) => a - b);
  const cellByKey = new Map(heatmap.cells.map((c) => [`${c.x_value}_${c.y_value}`, c]));

  const validValues = heatmap.cells.map((c) => c.metric_value).filter((v): v is number => v !== null);
  const min = validValues.length > 0 ? Math.min(...validValues) : 0;
  const max = validValues.length > 0 ? Math.max(...validValues) : 0;
  const range = max - min || 1;

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="p-1.5 text-text-faint text-right">
              {PARAMETER_LABELS[heatmap.param_y] ?? heatmap.param_y} \ {PARAMETER_LABELS[heatmap.param_x] ?? heatmap.param_x}
            </th>
            {xValues.map((x) => (
              <th key={x} className="p-1.5 text-text-faint tabular text-center min-w-[64px]">
                {x}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...yValues].reverse().map((y) => (
            <tr key={y}>
              <th className="p-1.5 text-text-faint tabular text-right">{y}</th>
              {xValues.map((x) => {
                const cell = cellByKey.get(`${x}_${y}`);
                const v = cell?.metric_value ?? null;
                const intensity = v === null ? 0 : (v - min) / range;
                const bg = v === null ? "transparent" : `color-mix(in srgb, var(--color-accent) ${Math.round(intensity * 70)}%, var(--color-bg-elevated))`;
                return (
                  <td
                    key={x}
                    className={clsx(
                      "p-1.5 text-center tabular border border-border",
                      cell?.insufficient_sample && "opacity-40"
                    )}
                    style={{ backgroundColor: bg }}
                    title={cell ? `${cell.number_of_trades} trade(s)${cell.insufficient_sample ? " - insufficient sample" : ""}` : undefined}
                  >
                    {v === null ? "N/A" : v.toFixed(1)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[11px] text-text-faint leading-relaxed mt-3">{heatmap.methodology}</p>
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  labels,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
  labels: Record<string, string>;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {labels[o] ?? o}
          </option>
        ))}
      </select>
    </label>
  );
}
