"use client";

import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { AlertTriangle, TrendingUp } from "lucide-react";
import { clsx } from "clsx";
import { getForwardValidation, getPaperEquityHistory } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { SkeletonText } from "@/components/ui/Skeleton";
import { formatCurrency, formatPercent, formatDate } from "@/lib/format";

export function ForwardValidationPanel({ portfolioId, refreshKey }: { portfolioId: string; refreshKey: number }) {
  const { data: fv, loading: fvLoading } = useApiResource(
    (signal) => getForwardValidation(portfolioId, signal),
    [portfolioId, refreshKey]
  );
  const { data: history, loading: historyLoading } = useApiResource(
    (signal) => getPaperEquityHistory(portfolioId, signal),
    [portfolioId, refreshKey]
  );

  const chartData = useMemo(
    () =>
      (history?.snapshots ?? []).map((s) => ({
        date: s.date,
        equity: s.equity,
        benchmark: s.benchmark_value ?? undefined,
      })),
    [history]
  );

  if (fvLoading || historyLoading || !fv) {
    return (
      <Card>
        <SkeletonText lines={6} />
      </Card>
    );
  }

  const stats: { label: string; value: string; tone?: "bullish" | "bearish" }[] = [
    { label: "Start Date", value: fv.start_date ?? "N/A" },
    { label: "Current Date", value: fv.current_date ?? "N/A" },
    { label: "Trading Days Observed", value: String(fv.trading_days_observed) },
    { label: "Model Version", value: fv.model_version_is_mixed ? "MIXED" : fv.model_version },
    { label: "Initial Capital", value: formatCurrency(fv.initial_capital) },
    { label: "Current Equity", value: formatCurrency(fv.current_equity) },
    {
      label: "Total Return",
      value: formatPercent(fv.total_return_percent),
      tone: fv.total_return_percent >= 0 ? "bullish" : "bearish",
    },
    {
      label: `Benchmark (${fv.benchmark_ticker ?? "N/A"}) Return`,
      value: formatPercent(fv.benchmark_return_percent),
      tone: fv.benchmark_return_percent === null ? undefined : fv.benchmark_return_percent >= 0 ? "bullish" : "bearish",
    },
    { label: "Max Drawdown", value: formatPercent(fv.max_drawdown_percent), tone: "bearish" },
    { label: "Trade Executions", value: String(fv.number_of_trades) },
    { label: "Open Positions", value: String(fv.open_positions_count) },
    { label: "Realized P&L", value: formatCurrency(fv.realized_pnl), tone: fv.realized_pnl >= 0 ? "bullish" : "bearish" },
    {
      label: "Unrealized P&L",
      value: formatCurrency(fv.unrealized_pnl),
      tone: fv.unrealized_pnl >= 0 ? "bullish" : "bearish",
    },
  ];

  return (
    <Card>
      <CardHeader
        title="Forward Validation"
        subtitle="How this model actually behaves as real market data arrives, going forward - NOT a backtest and not replayed history. Every point below was captured live, one per real trading day."
      />

      <div className="flex items-center gap-2 mb-4 text-xs text-accent bg-accent/10 border border-accent/25 rounded px-3 py-2">
        <TrendingUp size={13} className="shrink-0" aria-hidden="true" />
        Forward paper-trading observation record. Distinct from the Backtesting page&apos;s historical
        out-of-sample validation, which replays past data.
      </div>

      {fv.warnings.length > 0 && (
        <div className="mb-4 flex flex-col gap-1.5">
          {fv.warnings.map((w, i) => (
            <p
              key={i}
              className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2"
            >
              <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              {w}
            </p>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-5">
        {stats.map((s) => (
          <div key={s.label} className="border border-border rounded p-3 bg-bg-elevated">
            <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{s.label}</p>
            <p
              className={clsx(
                "text-sm font-semibold tabular",
                s.tone === "bullish" && "text-bullish",
                s.tone === "bearish" && "text-bearish",
                !s.tone && "text-text-primary"
              )}
            >
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {chartData.length < 2 ? (
        <p className="text-xs text-text-muted">
          NO NEW MARKET DATA to chart yet - {chartData.length === 0 ? "no" : "only one"} real trading day observation
          recorded so far. This will fill in as the portfolio is observed on further real trading days; it will
          never be filled with simulated points.
        </p>
      ) : (
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => formatDate(v)}
                stroke="#545e6e"
                tick={{ fontSize: 11, fill: "#7c8798" }}
                minTickGap={50}
                axisLine={{ stroke: "#1f2937" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#7c8798" }}
                tickFormatter={(v) => formatCurrency(v)}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip
                formatter={(value, name) => [formatCurrency(Number(value)), String(name)]}
                labelFormatter={(l) => formatDate(l as string)}
                contentStyle={{ background: "#0a0d15", border: "1px solid #2a3441", borderRadius: 6, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="equity" name="Paper Portfolio" stroke="#4c8eff" dot={false} strokeWidth={1.75} isAnimationActive={false} />
              <Line
                type="monotone"
                dataKey="benchmark"
                name={fv.benchmark_ticker ?? "Benchmark"}
                stroke="#f5a623"
                dot={false}
                strokeWidth={1.5}
                strokeDasharray="2 3"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="text-[11px] text-text-faint leading-relaxed mt-3">{fv.methodology}</p>
    </Card>
  );
}
