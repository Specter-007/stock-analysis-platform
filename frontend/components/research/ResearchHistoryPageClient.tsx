"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import { AlertTriangle, GitCompare } from "lucide-react";
import { compareExperiments, listExperiments, ApiError } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonText } from "@/components/ui/Skeleton";
import { formatPercent } from "@/lib/format";
import type { CompareExperimentsResponse, Experiment, ExperimentListRow, ExperimentStatus } from "@/types/api";

const STATUS_STYLE: Record<ExperimentStatus, string> = {
  DRAFT: "text-text-faint bg-bg-elevated border-border",
  CONFIGURED: "text-text-faint bg-bg-elevated border-border",
  RUNNING: "text-accent bg-accent/10 border-accent/25",
  COMPLETED: "text-text-secondary bg-bg-elevated border-border-strong",
  VALIDATED: "text-bullish bg-bullish/10 border-bullish/25",
  PAPER_FORWARD_TEST: "text-accent bg-accent/10 border-accent/25",
  FAILED: "text-bearish bg-bearish/10 border-bearish/25",
};

function metricFrom(row: ExperimentListRow, key: string): number | null {
  const result = row.experiment.results?.backtest.result as Record<string, unknown> | undefined;
  if (!result) return null;
  const v = result[key];
  return typeof v === "number" ? v : null;
}

export default function ResearchHistoryPageClient() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [modelFilter, setModelFilter] = useState<string>("ALL");
  const [selected, setSelected] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<CompareExperimentsResponse | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const { data, loading, error } = useApiResource(
    (signal) => listExperiments(includeArchived, signal),
    [includeArchived, refreshKey]
  );

  const rows = useMemo(() => {
    if (!data) return [];
    return data.experiments.filter((row) => modelFilter === "ALL" || row.experiment.config.model_version === modelFilter);
  }, [data, modelFilter]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 5) return prev;
      return [...prev, id];
    });
  }

  async function handleCompare() {
    setComparing(true);
    setCompareError(null);
    try {
      const res = await compareExperiments(selected);
      setCompareResult(res);
    } catch (err) {
      setCompareError(err instanceof ApiError ? err.message : "Comparison failed.");
    } finally {
      setComparing(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1">Research History</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          Every experiment ever run, with its own immutable configuration. Select 2-5 to compare side by side.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-text-muted">
            <input type="checkbox" checked={includeArchived} onChange={(e) => setIncludeArchived(e.target.checked)} />
            Show archived
          </label>
          <label className="flex items-center gap-2 text-xs">
            <span className="text-text-muted">Model</span>
            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-2 py-1 text-xs text-text-primary"
            >
              <option value="ALL">All</option>
              <option value="1.1">v1.1</option>
              <option value="1.0">v1.0</option>
            </select>
          </label>
          {selected.length >= 2 && (
            <button
              onClick={handleCompare}
              disabled={comparing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-white text-xs font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer ml-auto"
            >
              <GitCompare size={13} /> Compare Selected ({selected.length})
            </button>
          )}
        </div>
      </Card>

      {error ? (
        <ErrorState error={error} onRetry={() => setRefreshKey((k) => k + 1)} />
      ) : loading || !data ? (
        <Card><SkeletonText lines={6} /></Card>
      ) : (
        <Card>
          <CardHeader title="Experiments" subtitle={`${rows.length} experiment(s)`} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[900px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2 w-8"></th>
                  <th className="pb-2">Experiment</th>
                  <th className="pb-2">Model</th>
                  <th className="pb-2">Universe</th>
                  <th className="pb-2">Period</th>
                  <th className="pb-2 text-right">Return</th>
                  <th className="pb-2 text-right">Sharpe</th>
                  <th className="pb-2 text-right">Max DD</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.experiment.id}>
                    <td className="py-2">
                      <input
                        type="checkbox"
                        checked={selected.includes(row.experiment.id)}
                        onChange={() => toggleSelect(row.experiment.id)}
                      />
                    </td>
                    <td className="py-2">
                      <Link href={`/experiments/${row.experiment.id}`} className="text-accent hover:underline">
                        {row.experiment.name}
                      </Link>
                      <div className="flex gap-1 mt-0.5">
                        {row.experiment.tags.map((t) => (
                          <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-bg-elevated border border-border text-text-faint">
                            {t}
                          </span>
                        ))}
                        {row.data_mining_warning && (
                          <span className="flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-warning-dim border border-warning/25 text-warning">
                            <AlertTriangle size={9} /> {row.group_count} similar
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 text-text-secondary">v{row.experiment.config.model_version}</td>
                    <td className="py-2 text-text-secondary font-mono">{row.experiment.config.tickers.join(", ")}</td>
                    <td className="py-2 text-text-secondary tabular">
                      {row.experiment.config.start_date} → {row.experiment.config.end_date}
                    </td>
                    <td
                      className={clsx(
                        "py-2 text-right tabular font-medium",
                        (metricFrom(row, "total_return_percent") ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                      )}
                    >
                      {formatPercent(metricFrom(row, "total_return_percent"))}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {metricFrom(row, "sharpe_ratio") === null ? "N/A" : metricFrom(row, "sharpe_ratio")!.toFixed(2)}
                    </td>
                    <td className="py-2 text-right tabular text-bearish">{formatPercent(metricFrom(row, "max_drawdown_percent"))}</td>
                    <td className="py-2">
                      <span className={clsx("text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border", STATUS_STYLE[row.experiment.status])}>
                        {row.experiment.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={9} className="py-6 text-center text-text-muted">
                      No experiments yet - create one in the Experiment Lab.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-text-faint leading-relaxed mt-4">{data.methodology}</p>
        </Card>
      )}

      {compareError && <p className="text-xs text-bearish">{compareError}</p>}

      {compareResult && <ComparisonTable result={compareResult} />}
    </div>
  );
}

function ComparisonTable({ result }: { result: CompareExperimentsResponse }) {
  return (
    <Card>
      <CardHeader title="Comparison" />
      {result.warnings.length > 0 && (
        <div className="mb-4 flex flex-col gap-1.5">
          {result.warnings.map((w, i) => (
            <p key={i} className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              {w}
            </p>
          ))}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[700px]">
          <thead>
            <tr className="text-left text-text-faint uppercase tracking-wide">
              <th className="pb-2">Metric</th>
              {result.experiments.map((e) => (
                <th key={e.id} className="pb-2 px-3 text-right text-text-secondary">
                  {e.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            <ComparisonRow label="Model" experiments={result.experiments} render={(e) => `v${e.config.model_version}`} />
            <ComparisonRow label="Universe" experiments={result.experiments} render={(e) => e.config.tickers.join(", ")} />
            <ComparisonRow label="Period" experiments={result.experiments} render={(e) => `${e.config.start_date} → ${e.config.end_date}`} />
            <ComparisonRow
              label="Total Return"
              experiments={result.experiments}
              render={(e) => formatPercent(bt(e, "total_return_percent"))}
            />
            <ComparisonRow label="CAGR" experiments={result.experiments} render={(e) => formatPercent(bt(e, "cagr_percent"))} />
            <ComparisonRow
              label="Sharpe"
              experiments={result.experiments}
              render={(e) => {
                const v = bt(e, "sharpe_ratio");
                return v === null ? "N/A" : v.toFixed(2);
              }}
            />
            <ComparisonRow label="Max Drawdown" experiments={result.experiments} render={(e) => formatPercent(bt(e, "max_drawdown_percent"))} />
            <ComparisonRow label="Status" experiments={result.experiments} render={(e) => e.status.replace(/_/g, " ")} />
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function bt(e: Experiment, key: string): number | null {
  const result = e.results?.backtest.result as Record<string, unknown> | undefined;
  if (!result) return null;
  const v = result[key];
  return typeof v === "number" ? v : null;
}

function ComparisonRow({
  label,
  experiments,
  render,
}: {
  label: string;
  experiments: Experiment[];
  render: (e: Experiment) => string;
}) {
  return (
    <tr>
      <td className="py-2 text-text-muted">{label}</td>
      {experiments.map((e) => (
        <td key={e.id} className="py-2 px-3 text-right tabular text-text-secondary">
          {render(e)}
        </td>
      ))}
    </tr>
  );
}
