import { Card, CardHeader } from "@/components/ui/Card";
import { clsx } from "clsx";
import type { BacktestResponse } from "@/types/api";
import { formatCurrency, formatPercent } from "@/lib/format";

export function ModelEvaluationPanel({ result }: { result: BacktestResponse }) {
  const m = result.advanced_metrics;

  const metrics: { label: string; value: string; tone?: "bullish" | "bearish" }[] = [
    { label: "CAGR", value: formatPercent(m.cagr_percent), tone: toneOf(m.cagr_percent) },
    { label: "Annualized Volatility", value: formatPercent(m.annualized_volatility_percent) },
    { label: "Sortino Ratio", value: fmt2(m.sortino_ratio), tone: toneOf(m.sortino_ratio) },
    { label: "Calmar Ratio", value: fmt2(m.calmar_ratio), tone: toneOf(m.calmar_ratio) },
    { label: "Average Drawdown", value: formatPercent(m.average_drawdown_percent), tone: "bearish" },
    { label: "Downside Deviation", value: formatPercent(m.downside_deviation_percent) },
    {
      label: "Drawdown Recovery",
      value: m.max_drawdown_recovery_days === null ? "N/A (still underwater)" : `${m.max_drawdown_recovery_days} days`,
    },
    { label: "Expectancy / Trade", value: formatCurrency(m.expectancy), tone: toneOf(m.expectancy) },
    { label: "Exposure", value: formatPercent(m.exposure_percent) },
    { label: "Turnover", value: formatPercent(m.turnover_percent) },
    { label: "Beta (vs. benchmark)", value: fmt2(m.beta) },
    { label: "Alpha (annualized)", value: formatPercent(m.alpha_percent), tone: toneOf(m.alpha_percent) },
    { label: "Tracking Error", value: formatPercent(m.tracking_error_percent) },
    { label: "Information Ratio", value: fmt2(m.information_ratio), tone: toneOf(m.information_ratio) },
    { label: "Average Win", value: formatCurrency(m.average_win), tone: "bullish" },
    { label: "Average Loss", value: formatCurrency(m.average_loss), tone: "bearish" },
    { label: "Median Trade", value: formatPercent(m.median_trade_percent), tone: toneOf(m.median_trade_percent) },
  ];

  return (
    <Card>
      <CardHeader
        title="Model Evaluation"
        subtitle="Is this actually useful, or does it only look good in this one backtest? Metrics not computable from available data show N/A, never a fabricated value."
      />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {metrics.map((s) => (
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
      {m.beta === null && (
        <p className="text-[11px] text-text-faint mt-3">
          Beta/alpha/tracking-error/information-ratio require a benchmark - set one in the configuration above.
        </p>
      )}
    </Card>
  );
}

function fmt2(v: number | null): string {
  return v === null ? "N/A" : v.toFixed(2);
}

function toneOf(v: number | null): "bullish" | "bearish" | undefined {
  if (v === null) return undefined;
  return v >= 0 ? "bullish" : "bearish";
}
