import { clsx } from "clsx";
import type { BacktestResponse } from "@/types/api";
import { formatCurrency, formatPercent } from "@/lib/format";

export function MetricsGrid({ result }: { result: BacktestResponse }) {
  const metrics: { label: string; value: string; tone?: "bullish" | "bearish" | "neutral" }[] = [
    { label: "Initial Capital", value: formatCurrency(result.initial_capital) },
    { label: "Final Capital", value: formatCurrency(result.final_capital) },
    {
      label: "Strategy Return",
      value: formatPercent(result.total_return_percent),
      tone: toneOf(result.total_return_percent),
    },
    {
      label: "Annualized Return",
      value: formatPercent(result.annualized_return_percent),
      tone: toneOf(result.annualized_return_percent),
    },
    {
      label: "Buy & Hold Return",
      value: formatPercent(result.buy_hold_return_percent),
      tone: toneOf(result.buy_hold_return_percent),
    },
    {
      label: result.benchmark_ticker ? `Benchmark (${result.benchmark_ticker})` : "Benchmark",
      value: result.benchmark_return_percent === null ? "N/A" : formatPercent(result.benchmark_return_percent),
      tone: toneOf(result.benchmark_return_percent),
    },
    { label: "Max Drawdown", value: formatPercent(result.max_drawdown_percent), tone: "bearish" },
    { label: "Sharpe Ratio", value: result.sharpe_ratio === null ? "N/A" : result.sharpe_ratio.toFixed(2) },
    { label: "Trades", value: String(result.number_of_trades) },
    {
      label: "Win Rate",
      value: result.win_rate_percent === null ? "N/A" : `${result.win_rate_percent.toFixed(1)}%`,
    },
    {
      label: "Avg. Trade",
      value: result.average_trade_percent === null ? "N/A" : formatPercent(result.average_trade_percent),
      tone: toneOf(result.average_trade_percent),
    },
    {
      label: "Best / Worst Trade",
      value: `${result.best_trade_percent === null ? "N/A" : formatPercent(result.best_trade_percent)} / ${
        result.worst_trade_percent === null ? "N/A" : formatPercent(result.worst_trade_percent)
      }`,
    },
    {
      label: "Profit Factor",
      value: result.profit_factor === null ? "N/A" : result.profit_factor.toFixed(2),
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {metrics.map((m) => (
        <div key={m.label} className="border border-border rounded-md p-3 bg-bg-elevated">
          <p className="text-[10px] uppercase tracking-wide text-text-faint mb-1">{m.label}</p>
          <p
            className={clsx(
              "text-sm font-semibold tabular",
              m.tone === "bullish" && "text-bullish",
              m.tone === "bearish" && "text-bearish",
              !m.tone && "text-text-primary"
            )}
          >
            {m.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function toneOf(value: number | null): "bullish" | "bearish" | undefined {
  if (value === null) return undefined;
  return value >= 0 ? "bullish" : "bearish";
}
