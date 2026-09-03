"use client";

import { useState } from "react";
import { Play, Loader2, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { runPortfolioBacktest, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { EquityChart } from "@/components/backtest/EquityChart";
import { DrawdownChart } from "@/components/backtest/DrawdownChart";
import { DataFreshnessBadge } from "@/components/ui/DataFreshnessBadge";
import { formatCurrency, formatPercent } from "@/lib/format";
import type {
  AllocationMethod,
  PortfolioBacktestRequestPayload,
  PortfolioBacktestResponse,
  RebalanceFrequency,
} from "@/types/api";

const ALLOCATION_OPTIONS: { value: AllocationMethod; label: string }[] = [
  { value: "EQUAL_WEIGHT", label: "Equal Weight" },
  { value: "SIGNAL_WEIGHTED", label: "Signal Weighted" },
  { value: "RISK_WEIGHTED", label: "Risk Weighted (inverse volatility)" },
  { value: "FIXED_WEIGHT", label: "Fixed Weight" },
];

const REBALANCE_OPTIONS: { value: RebalanceFrequency; label: string }[] = [
  { value: "DAILY", label: "Daily" },
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
];

export default function PortfolioBacktestPageClient() {
  const [tickersInput, setTickersInput] = useState("AAPL, MSFT, NVDA");
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 3);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [initialCapital, setInitialCapital] = useState(30000);
  const [allocationMethod, setAllocationMethod] = useState<AllocationMethod>("EQUAL_WEIGHT");
  const [rebalanceFrequency, setRebalanceFrequency] = useState<RebalanceFrequency>("MONTHLY");
  const [benchmarkTicker, setBenchmarkTicker] = useState("SPY");
  const [maxPositionWeight, setMaxPositionWeight] = useState(100);
  const [minPositionWeight, setMinPositionWeight] = useState(0);
  const [maxHoldings, setMaxHoldings] = useState<string>("");
  const [cashAllocation, setCashAllocation] = useState(0);
  const [sectorCap, setSectorCap] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<PortfolioBacktestResponse | null>(null);
  const [lastPayload, setLastPayload] = useState<PortfolioBacktestRequestPayload | null>(null);

  async function handleSubmit() {
    const tickers = tickersInput
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);

    const payload: PortfolioBacktestRequestPayload = {
      tickers,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      transaction_cost_bps: 5,
      slippage_bps: 5,
      allocation_method: allocationMethod,
      rebalance_frequency: rebalanceFrequency,
      benchmark_ticker: benchmarkTicker || null,
      constraints: {
        max_position_weight_percent: maxPositionWeight,
        min_position_weight_percent: minPositionWeight,
        max_holdings: maxHoldings ? Number(maxHoldings) : null,
        cash_allocation_percent: cashAllocation,
        sector_cap_percent: sectorCap ? Number(sectorCap) : null,
      },
    };

    setLoading(true);
    setError(null);
    setLastPayload(payload);
    try {
      const res = await runPortfolioBacktest(payload);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "UNKNOWN_ERROR", "Something went wrong."));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1">Portfolio Backtesting</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          Multi-ticker allocation on top of the same deterministic per-ticker signals used everywhere else -
          rebalanced on a schedule, constrained by position/sector limits, long-only with no leverage.
        </p>
      </div>

      <Card>
        <CardHeader title="Configuration" />
        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Tickers (comma-separated, 2-20)</span>
            <input
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          <div className="flex flex-wrap items-end gap-3">
            <DateField label="Start Date" value={startDate} onChange={setStartDate} />
            <DateField label="End Date" value={endDate} onChange={setEndDate} />
            <NumberField label="Initial Capital" value={initialCapital} onChange={setInitialCapital} step={1000} min={100} />
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Benchmark</span>
              <input
                value={benchmarkTicker}
                onChange={(e) => setBenchmarkTicker(e.target.value.toUpperCase())}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-24"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <SelectField label="Allocation Method" value={allocationMethod} onChange={(v) => setAllocationMethod(v as AllocationMethod)} options={ALLOCATION_OPTIONS} />
            <SelectField label="Rebalance Frequency" value={rebalanceFrequency} onChange={(v) => setRebalanceFrequency(v as RebalanceFrequency)} options={REBALANCE_OPTIONS} />
          </div>

          <p className="text-xs text-text-muted font-medium mt-1">Constraints</p>
          <div className="flex flex-wrap items-end gap-3">
            <NumberField label="Max Position Weight %" value={maxPositionWeight} onChange={setMaxPositionWeight} step={5} min={1} max={100} />
            <NumberField label="Min Position Weight %" value={minPositionWeight} onChange={setMinPositionWeight} step={1} min={0} max={100} />
            <TextNumberField label="Max Holdings (optional)" value={maxHoldings} onChange={setMaxHoldings} placeholder="No limit" />
            <NumberField label="Cash Allocation %" value={cashAllocation} onChange={setCashAllocation} step={5} min={0} max={99} />
            <TextNumberField label="Sector Cap % (optional)" value={sectorCap} onChange={setSectorCap} placeholder="No cap" />
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer mt-2"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            Run Portfolio Backtest
          </button>
        </div>
      </Card>

      {error && <ErrorState error={error} onRetry={() => lastPayload && handleSubmit()} />}

      {loading && (
        <Card>
          <p className="text-sm text-text-muted">Fetching historical data for every ticker and running the simulation…</p>
        </Card>
      )}

      {result && !loading && <PortfolioResults result={result} />}
    </div>
  );
}

function PortfolioResults({ result }: { result: PortfolioBacktestResponse }) {
  const m = result.advanced_metrics;
  const stats: { label: string; value: string; tone?: "bullish" | "bearish" }[] = [
    {
      label: "Total Return",
      value: formatPercent(result.total_return_percent),
      tone: (result.total_return_percent ?? 0) >= 0 ? "bullish" : "bearish",
    },
    { label: "Equal-Weight Buy & Hold", value: formatPercent(result.equal_weight_buy_hold_return_percent) },
    { label: `Benchmark (${result.benchmark_ticker ?? "N/A"})`, value: formatPercent(result.benchmark_return_percent) },
    { label: "CAGR", value: formatPercent(m.cagr_percent ?? null) },
    { label: "Sharpe Ratio", value: result.sharpe_ratio === null ? "N/A" : result.sharpe_ratio.toFixed(2) },
    { label: "Sortino Ratio", value: m.sortino_ratio === null || m.sortino_ratio === undefined ? "N/A" : m.sortino_ratio.toFixed(2) },
    { label: "Max Drawdown", value: formatPercent(result.max_drawdown_percent), tone: "bearish" },
    { label: "Annualized Volatility", value: formatPercent(m.annualized_volatility_percent ?? null) },
    { label: "Final Capital", value: formatCurrency(result.final_capital) },
    { label: "Rebalances", value: String(result.number_of_rebalances) },
    { label: "Trading Days", value: String(result.trading_days) },
    { label: "Holdings (final)", value: String(result.risk_analytics.number_of_holdings) },
  ];

  const finalDate = result.end_date;
  const finalHoldings = result.holdings_history
    .filter((h) => h.date === finalDate)
    .sort((a, b) => b.weight_percent - a.weight_percent);

  return (
    <>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <CardHeader
            title={`Results: ${result.tickers.join(", ")}`}
            subtitle={`${result.start_date} → ${result.end_date} · ${result.allocation_method} · ${result.rebalance_frequency} rebalance`}
          />
          <DataFreshnessBadge meta={result.meta} compact />
        </div>

        {Object.keys(result.excluded_tickers).length > 0 && (
          <div className="mb-4 flex flex-col gap-1.5">
            {Object.entries(result.excluded_tickers).map(([t, reason]) => (
              <p key={t} className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2">
                <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                {t} excluded: {reason}
              </p>
            ))}
          </div>
        )}

        {result.warnings.length > 0 && (
          <div className="mb-4 flex flex-col gap-1.5 max-h-40 overflow-y-auto">
            {result.warnings.map((w, i) => (
              <p key={i} className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2">
                <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                {w}
              </p>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
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
      </Card>

      <Card>
        <CardHeader title="Portfolio Equity Curve" subtitle="Strategy vs. equal-weight buy & hold vs. benchmark" />
        <EquityChart
          strategy={result.equity_curve}
          buyHold={result.equal_weight_buy_hold_curve}
          benchmark={result.benchmark_curve}
          benchmarkTicker={result.benchmark_ticker}
        />
      </Card>

      <Card>
        <CardHeader title="Drawdown" />
        <DrawdownChart drawdown={result.drawdown_curve} />
      </Card>

      <Card>
        <CardHeader title="Risk Analytics" subtitle="Computed from this backtest's final rebalance and its holdings' real historical daily returns" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <MiniStat label="Exposure" value={formatPercent(result.risk_analytics.exposure_percent)} />
          <MiniStat label="Cash" value={formatPercent(result.risk_analytics.cash_percent)} />
          <MiniStat label="Largest Position" value={formatPercent(result.risk_analytics.largest_position_percent)} />
          <MiniStat label="Top-3 Concentration" value={formatPercent(result.risk_analytics.top_3_concentration_percent)} />
        </div>

        {Object.keys(result.risk_analytics.sector_concentration_percent).length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs mb-5">
            {Object.entries(result.risk_analytics.sector_concentration_percent).map(([sector, pct]) => (
              <span key={sector} className="px-2 py-1 rounded bg-bg-elevated border border-border text-text-secondary">
                {sector}: {pct.toFixed(1)}%
              </span>
            ))}
          </div>
        )}

        {result.risk_analytics.correlation_matrix && (
          <div className="overflow-x-auto mb-3">
            <p className="text-xs text-text-muted font-medium mb-2">Correlation Matrix (daily returns)</p>
            <table className="border-collapse text-xs">
              <thead>
                <tr>
                  <th className="p-1.5" />
                  {result.tickers.map((t) => (
                    <th key={t} className="p-1.5 text-text-faint text-center">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.tickers.map((rowT) => (
                  <tr key={rowT}>
                    <th className="p-1.5 text-text-faint text-right">{rowT}</th>
                    {result.tickers.map((colT) => {
                      const v = result.risk_analytics.correlation_matrix?.[rowT]?.[colT] ?? null;
                      return (
                        <td key={colT} className="p-1.5 text-center tabular border border-border text-text-secondary">
                          {v === null ? "N/A" : v.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-[11px] text-text-faint leading-relaxed">{result.methodology.correlation}</p>
      </Card>

      <Card>
        <CardHeader title="Final Holdings" subtitle={`As of ${result.end_date}`} />
        {finalHoldings.length === 0 ? (
          <p className="text-xs text-text-muted">No open positions at the end of the backtest.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[500px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Ticker</th>
                  <th className="pb-2 text-right">Weight</th>
                  <th className="pb-2 text-right">Shares</th>
                  <th className="pb-2 text-right">Price</th>
                  <th className="pb-2 text-right">Market Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {finalHoldings.map((h) => (
                  <tr key={h.ticker}>
                    <td className="py-2 font-mono text-text-primary">{h.ticker}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatPercent(h.weight_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{h.shares.toFixed(4)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatCurrency(h.price)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatCurrency(h.market_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Methodology & Limitations" />
        <dl className="flex flex-col gap-3 text-xs">
          {Object.entries(result.methodology).map(([key, value]) => (
            <div key={key}>
              <dt className="text-text-secondary font-medium capitalize mb-0.5">{key.replace(/_/g, " ")}</dt>
              <dd className="text-text-muted leading-relaxed">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border rounded p-3 bg-bg-elevated">
      <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{label}</p>
      <p className="text-sm font-semibold tabular text-text-primary">{value}</p>
    </div>
  );
}

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
      />
    </label>
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
  max?: number;
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
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-32"
      />
    </label>
  );
}

function TextNumberField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      <input
        type="number"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-32"
      />
    </label>
  );
}

function SelectField<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (v: string) => void;
  options: { value: T; label: string }[];
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
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
