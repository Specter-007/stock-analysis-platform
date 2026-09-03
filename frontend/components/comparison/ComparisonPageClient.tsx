"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { compareStocks, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { formatCompactNumber, formatCurrency, formatPercent } from "@/lib/format";
import type { ComparisonResponse, ComparisonRow } from "@/types/api";

type MetricRow = {
  section: string;
  label: string;
  render: (row: ComparisonRow) => { text: string; tone?: "bullish" | "bearish" };
};

function FragmentRow({
  metric,
  rows,
  colSpan,
}: {
  metric: MetricRow & { showSection: boolean };
  rows: ComparisonRow[];
  colSpan: number;
}) {
  return (
    <>
      {metric.showSection && (
        <tr>
          <td colSpan={colSpan} className="pt-4 pb-1 text-[10px] uppercase tracking-wide text-accent font-semibold">
            {metric.section}
          </td>
        </tr>
      )}
      <tr>
        <td className="py-1.5 pr-4 text-text-muted">{metric.label}</td>
        {rows.map((r) => {
          const { text, tone } = r.error ? { text: "N/A", tone: undefined } : metric.render(r);
          return (
            <td
              key={r.ticker}
              className={clsx(
                "py-1.5 px-3 text-right tabular",
                tone === "bullish" && "text-bullish",
                tone === "bearish" && "text-bearish",
                !tone && "text-text-secondary"
              )}
            >
              {text}
            </td>
          );
        })}
      </tr>
    </>
  );
}

const METRICS: MetricRow[] = [
  { section: "Market", label: "Company", render: (r) => ({ text: r.company_name ?? "N/A" }) },
  { section: "Market", label: "Sector", render: (r) => ({ text: r.sector ?? "N/A" }) },
  { section: "Market", label: "Industry", render: (r) => ({ text: r.industry ?? "N/A" }) },
  { section: "Market", label: "Last Price", render: (r) => ({ text: formatCurrency(r.last_price) }) },
  {
    section: "Market",
    label: "Change",
    render: (r) => ({ text: formatPercent(r.change_percent), tone: (r.change_percent ?? 0) >= 0 ? "bullish" : "bearish" }),
  },
  { section: "Market", label: "Market Cap", render: (r) => ({ text: r.market_cap === null ? "N/A" : formatCompactNumber(r.market_cap) }) },

  { section: "Technical", label: "Trend", render: (r) => ({ text: r.trend_classification ?? "N/A" }) },
  { section: "Technical", label: "RSI (14)", render: (r) => ({ text: r.rsi_14 === null ? "N/A" : r.rsi_14.toFixed(1) }) },
  { section: "Technical", label: "Dist. from 50D SMA", render: (r) => ({ text: formatPercent(r.dist_sma_50_pct) }) },
  { section: "Technical", label: "Dist. from 200D SMA", render: (r) => ({ text: formatPercent(r.dist_sma_200_pct) }) },
  { section: "Technical", label: "Ann. Volatility", render: (r) => ({ text: formatPercent(r.historical_volatility_percent) }) },

  { section: "Performance", label: "1M Return", render: (r) => ({ text: formatPercent(r.return_1m_percent), tone: (r.return_1m_percent ?? 0) >= 0 ? "bullish" : "bearish" }) },
  { section: "Performance", label: "3M Return", render: (r) => ({ text: formatPercent(r.return_3m_percent), tone: (r.return_3m_percent ?? 0) >= 0 ? "bullish" : "bearish" }) },
  { section: "Performance", label: "6M Return", render: (r) => ({ text: formatPercent(r.return_6m_percent), tone: (r.return_6m_percent ?? 0) >= 0 ? "bullish" : "bearish" }) },
  { section: "Performance", label: "1Y Return", render: (r) => ({ text: formatPercent(r.return_1y_percent), tone: (r.return_1y_percent ?? 0) >= 0 ? "bullish" : "bearish" }) },
  { section: "Performance", label: "1Y Relative Strength", render: (r) => ({ text: r.relative_strength_1y_classification ?? "N/A" }) },

  { section: "Fundamentals", label: "Trailing P/E", render: (r) => ({ text: r.trailing_pe === null ? "N/A" : `${r.trailing_pe.toFixed(1)}x` }) },
  { section: "Fundamentals", label: "Forward P/E", render: (r) => ({ text: r.forward_pe === null ? "N/A" : `${r.forward_pe.toFixed(1)}x` }) },
  { section: "Fundamentals", label: "Price / Book", render: (r) => ({ text: r.price_to_book === null ? "N/A" : `${r.price_to_book.toFixed(1)}x` }) },
  { section: "Fundamentals", label: "Revenue Growth (YoY)", render: (r) => ({ text: formatPercent(r.revenue_growth_percent) }) },
  { section: "Fundamentals", label: "Profit Margin", render: (r) => ({ text: formatPercent(r.profit_margin_percent) }) },
  { section: "Fundamentals", label: "Return on Equity", render: (r) => ({ text: formatPercent(r.return_on_equity_percent) }) },

  { section: "Model", label: "Signal", render: (r) => ({ text: r.signal ?? "N/A" }) },
  { section: "Model", label: "Score", render: (r) => ({ text: r.score === null ? "N/A" : r.score.toFixed(1) }) },
  { section: "Model", label: "Model Version", render: (r) => ({ text: r.model_version ?? "N/A" }) },
];

export default function ComparisonPageClient() {
  const [tickersInput, setTickersInput] = useState("AAPL, MSFT, NVDA");
  const [benchmark, setBenchmark] = useState("SPY");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<ComparisonResponse | null>(null);

  async function handleSubmit() {
    const tickers = tickersInput
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);

    setLoading(true);
    setError(null);
    try {
      const res = await compareStocks({ tickers, benchmark_ticker: benchmark || undefined });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "UNKNOWN_ERROR", "Something went wrong."));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const metricsWithSectionFlag = METRICS.map((m, i) => ({
    ...m,
    showSection: i === 0 || METRICS[i - 1].section !== m.section,
  }));

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1">Stock Comparison</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          2-8 tickers side by side - market, technical, performance, fundamental, and model data. Every field is
          retrieved independently per ticker; unavailable data shows N/A, never a fabricated 0.
        </p>
      </div>

      <Card>
        <CardHeader title="Configuration" />
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1.5 text-xs flex-1 min-w-[240px]">
            <span className="text-text-muted font-medium">Tickers (comma-separated, 2-8)</span>
            <input
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Benchmark (for relative strength)</span>
            <input
              value={benchmark}
              onChange={(e) => setBenchmark(e.target.value.toUpperCase())}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-28"
            />
          </label>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            Compare
          </button>
        </div>
      </Card>

      {error && <ErrorState error={error} onRetry={handleSubmit} />}

      {loading && (
        <Card>
          <p className="text-sm text-text-muted">Fetching data for every ticker…</p>
        </Card>
      )}

      {result && !loading && (
        <Card>
          <CardHeader title="Comparison" subtitle={`Benchmark: ${result.benchmark_ticker}`} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[700px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2 pr-4">Metric</th>
                  {result.rows.map((r) => (
                    <th key={r.ticker} className="pb-2 px-3 text-right font-mono text-text-secondary">
                      {r.ticker}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {result.rows.some((r) => r.error) && (
                  <tr>
                    <td className="py-2 pr-4 text-text-faint">Status</td>
                    {result.rows.map((r) => (
                      <td key={r.ticker} className="py-2 px-3 text-right text-bearish">
                        {r.error ? "Error" : "OK"}
                      </td>
                    ))}
                  </tr>
                )}
                {metricsWithSectionFlag.map((m) => (
                  <FragmentRow key={m.label} metric={m} rows={result.rows} colSpan={result.rows.length + 1} />
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-text-faint leading-relaxed mt-4">{result.methodology}</p>
        </Card>
      )}
    </div>
  );
}
