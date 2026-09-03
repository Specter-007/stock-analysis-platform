"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import { runBacktest, ApiError } from "@/lib/api";
import { BacktestForm } from "./BacktestForm";
import { MetricsGrid } from "./MetricsGrid";
import { EquityChart } from "./EquityChart";
import { DrawdownChart } from "./DrawdownChart";
import { TradesTable } from "./TradesTable";
import { ModelEvaluationPanel } from "./ModelEvaluationPanel";
import { WalkForwardPanel } from "./WalkForwardPanel";
import { MonteCarloPanel } from "./MonteCarloPanel";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { DataFreshnessBadge } from "@/components/ui/DataFreshnessBadge";
import type { BacktestRequestPayload, BacktestResponse } from "@/types/api";

export default function BacktestPageClient() {
  const searchParams = useSearchParams();
  const initialTicker = searchParams.get("ticker") ?? undefined;

  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [lastPayload, setLastPayload] = useState<BacktestRequestPayload | null>(null);

  async function handleSubmit(payload: BacktestRequestPayload) {
    setLoading(true);
    setError(null);
    setLastPayload(payload);
    try {
      const res = await runBacktest(payload);
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
        <h1 className="text-xl font-semibold text-text-primary mb-1">Backtesting</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          Simulates the exact same deterministic signal engine used on the Stock Analysis page against
          historical data, trading long-or-flat with next-bar execution. Past performance does not
          guarantee future results.
        </p>
      </div>

      <Card>
        <CardHeader title="Configuration" />
        <BacktestForm onSubmit={handleSubmit} loading={loading} initialTicker={initialTicker} />
      </Card>

      {error && <ErrorState error={error} onRetry={() => lastPayload && handleSubmit(lastPayload)} />}

      {loading && (
        <Card>
          <p className="text-sm text-text-muted">Fetching historical data and running the simulation…</p>
        </Card>
      )}

      {result && !loading && (
        <>
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <CardHeader title={`Results: ${result.ticker}`} subtitle={`${result.start_date} → ${result.end_date} · ${result.trading_days} trading days`} />
              <DataFreshnessBadge meta={result.meta} compact />
            </div>

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

            <MetricsGrid result={result} />
          </Card>

          <ModelEvaluationPanel result={result} />

          <Card>
            <CardHeader title="Equity Curve" subtitle="Strategy vs. buy & hold vs. benchmark, mark-to-market daily" />
            <EquityChart
              strategy={result.strategy_curve}
              buyHold={result.buy_hold_curve}
              benchmark={result.benchmark_curve}
              benchmarkTicker={result.benchmark_ticker}
            />
          </Card>

          <Card>
            <CardHeader title="Drawdown" subtitle="Peak-to-trough decline of the strategy's equity curve" />
            <DrawdownChart drawdown={result.drawdown_curve} />
          </Card>

          <Card>
            <CardHeader title="Trade Log" subtitle={`${result.number_of_trades} completed trade(s)`} />
            <TradesTable trades={result.trades} />
          </Card>

          <Card>
            <CardHeader title="Methodology & Limitations" />
            <dl className="flex flex-col gap-3 text-xs">
              {Object.entries(result.methodology).map(([key, value]) => (
                <div key={key}>
                  <dt className="text-text-secondary font-medium capitalize mb-0.5">
                    {key.replace(/_/g, " ")}
                  </dt>
                  <dd className="text-text-muted leading-relaxed">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <WalkForwardPanel
            ticker={result.ticker}
            initialCapital={result.initial_capital}
            transactionCostBps={lastPayload?.transaction_cost_bps ?? 5}
            slippageBps={lastPayload?.slippage_bps ?? 5}
          />

          <MonteCarloPanel
            ticker={result.ticker}
            startDate={result.start_date}
            endDate={result.end_date}
            initialCapital={result.initial_capital}
            transactionCostBps={lastPayload?.transaction_cost_bps ?? 5}
            slippageBps={lastPayload?.slippage_bps ?? 5}
          />
        </>
      )}
    </div>
  );
}
