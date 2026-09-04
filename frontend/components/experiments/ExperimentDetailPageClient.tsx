"use client";

import { useState } from "react";
import { clsx } from "clsx";
import {
  AlertTriangle, Archive, Copy, Download, FlaskConical, Loader2, PlayCircle, RotateCcw,
} from "lucide-react";
import {
  archiveExperiment, duplicateExperiment, getExperiment, getExperimentExportUrl,
  getForwardVsHistorical, runExperiment, startForwardSimulation, updateExperimentNotes, ApiError,
} from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonText } from "@/components/ui/Skeleton";
import { EquityChart } from "@/components/backtest/EquityChart";
import { DrawdownChart } from "@/components/backtest/DrawdownChart";
import { formatCurrency, formatDateTime, formatPercent } from "@/lib/format";
import type { EquityPoint, Experiment, ExperimentStatus, ForwardVsHistoricalResponse } from "@/types/api";

const TABS = ["Configuration", "Performance", "Validation", "Robustness", "Regime", "Forward", "Notes", "Audit"] as const;
type Tab = (typeof TABS)[number];

interface BacktestResultShape {
  total_return_percent: number | null;
  cagr_percent: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  max_drawdown_percent: number | null;
  max_drawdown_recovery_days: number | null;
  alpha_percent: number | null;
  beta: number | null;
  tracking_error_percent: number | null;
  information_ratio: number | null;
  number_of_trades: number | null;
  number_of_rebalances: number | null;
  win_rate_percent: number | null;
  profit_factor: number | null;
  expectancy: number | null;
  exposure_percent: number | null;
  turnover_percent: number | null;
  warnings: string[];
  strategy_curve?: EquityPoint[];
  buy_hold_curve?: EquityPoint[];
  equity_curve?: EquityPoint[];
  equal_weight_buy_hold_curve?: EquityPoint[];
  benchmark_curve?: EquityPoint[];
  drawdown_curve?: EquityPoint[];
}

interface OosPeriodShape {
  label: string;
  total_return_percent: number | null;
  sharpe_ratio: number | null;
  max_drawdown_percent: number | null;
  number_of_trades: number;
}

interface OosResultShape {
  periods: OosPeriodShape[];
}

interface WalkForwardFoldShape {
  fold_index: number;
  test_start: string;
  test_end: string;
  test_total_return_percent: number | null;
  test_sharpe_ratio: number | null;
}

interface WalkForwardResultShape {
  folds: WalkForwardFoldShape[];
  folds_with_positive_return: number;
  average_test_return_percent: number | null;
}

interface SensitivityParamShape {
  parameter: string;
  label: string;
  robustness: string;
}

interface SensitivityResultShape {
  parameters: SensitivityParamShape[];
}

interface MonteCarloResultShape {
  median_return_percent: number | null;
  percentile_5_return_percent: number | null;
  percentile_95_return_percent: number | null;
  median_cagr_percent: number | null;
  probability_of_loss_percent: number | null;
  drawdown_threshold_percent: number;
  probability_of_exceeding_drawdown_threshold_percent: number | null;
  resampling_method: string;
  seed: number | null;
}

interface CostScenarioShape {
  label: string;
  net_return_percent: number | null;
  total_cost_percent: number | null;
}

interface CostStressResultShape {
  commission_scenarios: CostScenarioShape[];
}

interface RegimeBucketShape {
  regime: string;
  trading_days: number;
  frequency_percent: number;
  compounded_return_percent: number | null;
}

interface RegimeResultShape {
  buckets: RegimeBucketShape[];
}

const STATUS_STYLE: Record<ExperimentStatus, string> = {
  DRAFT: "text-text-faint bg-bg-elevated border-border",
  CONFIGURED: "text-text-faint bg-bg-elevated border-border",
  RUNNING: "text-accent bg-accent/10 border-accent/25",
  COMPLETED: "text-text-secondary bg-bg-elevated border-border-strong",
  VALIDATED: "text-bullish bg-bullish/10 border-bullish/25",
  PAPER_FORWARD_TEST: "text-accent bg-accent/10 border-accent/25",
  FAILED: "text-bearish bg-bearish/10 border-bearish/25",
};

export default function ExperimentDetailPageClient({ id }: { id: string }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [tab, setTab] = useState<Tab>("Configuration");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: exp, loading, error } = useApiResource((signal) => getExperiment(id, signal), [id, refreshKey]);

  async function withBusy(fn: () => Promise<void>) {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-8"><ErrorState error={error} onRetry={() => setRefreshKey((k) => k + 1)} /></div>;
  if (loading || !exp) return <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-8"><Card><SkeletonText lines={8} /></Card></div>;

  return (
    <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary mb-1 flex items-center gap-2">
            <FlaskConical size={18} className="text-accent" aria-hidden="true" />
            {exp.name}
          </h1>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx("text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border", STATUS_STYLE[exp.status])}>
              {exp.status.replace(/_/g, " ")}
            </span>
            <span className="text-xs text-text-faint font-mono">{exp.fingerprint}</span>
            {exp.tags.map((t) => (
              <span key={t} className="text-[10px] px-2 py-0.5 rounded bg-bg-elevated border border-border text-text-secondary">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {exp.status === "DRAFT" && (
            <ActionButton icon={<PlayCircle size={13} />} label="Run" busy={busy} onClick={() => withBusy(() => runExperiment(id).then(() => {}))} />
          )}
          <ActionButton icon={<Copy size={13} />} label="Duplicate" busy={busy} onClick={() => withBusy(() => duplicateExperiment(id).then(() => {}))} />
          <ActionButton
            icon={<Archive size={13} />}
            label={exp.archived ? "Unarchive" : "Archive"}
            busy={busy}
            onClick={() => withBusy(() => archiveExperiment(id, !exp.archived).then(() => {}))}
          />
          <a
            href={getExperimentExportUrl(id)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
          >
            <Download size={13} /> Export
          </a>
        </div>
      </div>

      {actionError && <p className="text-xs text-bearish">{actionError}</p>}

      {exp.error && (
        <p className="flex items-start gap-2 text-xs text-bearish bg-bearish/10 border border-bearish/25 rounded px-3 py-2">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
          {exp.error}
        </p>
      )}

      <div className="flex flex-wrap gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              "px-3 py-2 text-xs font-medium border-b-2 -mb-px cursor-pointer transition-colors",
              tab === t ? "border-accent text-text-primary" : "border-transparent text-text-muted hover:text-text-secondary"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Configuration" && <ConfigurationTab exp={exp} />}
      {tab === "Performance" && <PerformanceTab exp={exp} />}
      {tab === "Validation" && <ValidationTab exp={exp} />}
      {tab === "Robustness" && <RobustnessTab exp={exp} />}
      {tab === "Regime" && <RegimeTab exp={exp} />}
      {tab === "Forward" && <ForwardTab exp={exp} busy={busy} onStartForward={() => withBusy(() => startForwardSimulation(id).then(() => {}))} refreshKey={refreshKey} />}
      {tab === "Notes" && <NotesTab exp={exp} onSaved={() => setRefreshKey((k) => k + 1)} />}
      {tab === "Audit" && <AuditTab exp={exp} />}
    </div>
  );
}

function ActionButton({ icon, label, busy, onClick }: { icon: React.ReactNode; label: string; busy: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors cursor-pointer disabled:opacity-50"
    >
      {busy ? <Loader2 size={13} className="animate-spin" /> : icon} {label}
    </button>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "bullish" | "bearish" }) {
  return (
    <div className="border border-border rounded p-3 bg-bg-elevated">
      <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{label}</p>
      <p className={clsx("text-sm font-semibold tabular", tone === "bullish" && "text-bullish", tone === "bearish" && "text-bearish", !tone && "text-text-primary")}>
        {value}
      </p>
    </div>
  );
}

function ConfigurationTab({ exp }: { exp: Experiment }) {
  const c = exp.config;
  return (
    <Card>
      <CardHeader title="Immutable Configuration" subtitle="This is exactly what produced this experiment's result - it never changes, even if global model defaults do." />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <Metric label="Model Version" value={`v${c.model_version}`} />
        <Metric label="Tickers" value={c.tickers.join(", ")} />
        <Metric label="Benchmark" value={c.benchmark} />
        <Metric label="Period" value={`${c.start_date} → ${c.end_date}`} />
        <Metric label="Initial Capital" value={formatCurrency(c.initial_capital)} />
        <Metric label="Commission" value={`${c.commission_bps} bps`} />
        <Metric label="Slippage" value={`${c.slippage_bps} bps`} />
        {c.allocation_method && <Metric label="Allocation" value={c.allocation_method} />}
        {c.rebalance_frequency && <Metric label="Rebalance" value={c.rebalance_frequency} />}
      </div>
      <p className="text-xs text-text-muted font-medium mt-4 mb-2">Requested Validation Procedures</p>
      <div className="flex flex-wrap gap-2">
        {[
          ["Out-of-Sample", c.run_out_of_sample], ["Walk-Forward", c.run_walk_forward], ["Sensitivity", c.run_sensitivity],
          ["Monte Carlo", c.run_monte_carlo], ["Regime Analysis", c.run_regime_analysis], ["Cost Stress", c.run_cost_stress],
        ].map(([label, on]) => (
          <span key={label as string} className={clsx("text-[10px] px-2 py-1 rounded border", on ? "border-accent/40 text-accent bg-accent/10" : "border-border text-text-faint")}>
            {label as string}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 mt-4 text-xs text-text-faint">
        <span>Created: {formatDateTime(exp.created_at)}</span>
        <span>Updated: {formatDateTime(exp.updated_at)}</span>
        {exp.reproduced_from && <span>Reproduced from: {exp.reproduced_from}</span>}
      </div>
    </Card>
  );
}

function ValidationOutcomeNote({ label, outcome }: { label: string; outcome: { requested: boolean; completed: boolean; error: string | null } }) {
  if (!outcome.requested) return null;
  if (outcome.completed) return null;
  return (
    <p className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2">
      <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
      {label}: {outcome.error ?? "Did not complete."}
    </p>
  );
}

function PerformanceTab({ exp }: { exp: Experiment }) {
  const outcome = exp.results?.backtest;
  if (!outcome || !outcome.result) {
    return <Card><p className="text-sm text-text-muted">No backtest result yet - run this experiment first.</p></Card>;
  }
  const r = outcome.result as unknown as BacktestResultShape;
  const isPortfolio = exp.config.tickers.length > 1;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Performance" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Metric label="Total Return" value={formatPercent(r.total_return_percent)} tone={(r.total_return_percent ?? 0) >= 0 ? "bullish" : "bearish"} />
          <Metric label="CAGR" value={formatPercent(r.cagr_percent)} />
          <Metric label="Sharpe" value={r.sharpe_ratio == null ? "N/A" : Number(r.sharpe_ratio).toFixed(2)} />
          <Metric label="Sortino" value={r.sortino_ratio == null ? "N/A" : Number(r.sortino_ratio).toFixed(2)} />
          <Metric label="Calmar" value={r.calmar_ratio == null ? "N/A" : Number(r.calmar_ratio).toFixed(2)} />
          <Metric label="Max Drawdown" value={formatPercent(r.max_drawdown_percent)} tone="bearish" />
          <Metric label="Recovery Days" value={r.max_drawdown_recovery_days == null ? "N/A" : String(r.max_drawdown_recovery_days)} />
          <Metric label="Alpha" value={formatPercent(r.alpha_percent)} />
          <Metric label="Beta" value={r.beta == null ? "N/A" : Number(r.beta).toFixed(2)} />
          <Metric label="Tracking Error" value={formatPercent(r.tracking_error_percent)} />
          <Metric label="Information Ratio" value={r.information_ratio == null ? "N/A" : Number(r.information_ratio).toFixed(2)} />
          <Metric label="Trades" value={String(r.number_of_trades ?? r.number_of_rebalances ?? "N/A")} />
          <Metric label="Win Rate" value={formatPercent(r.win_rate_percent)} />
          <Metric label="Profit Factor" value={r.profit_factor == null ? "N/A" : Number(r.profit_factor).toFixed(2)} />
          <Metric label="Expectancy" value={r.expectancy == null ? "N/A" : formatCurrency(r.expectancy)} />
          <Metric label="Exposure" value={formatPercent(r.exposure_percent)} />
          <Metric label="Turnover" value={formatPercent(r.turnover_percent)} />
        </div>
      </Card>

      {r.warnings?.length > 0 && (
        <Card>
          {r.warnings.map((w: string, i: number) => (
            <p key={i} className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2 mb-1.5 last:mb-0">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              {w}
            </p>
          ))}
        </Card>
      )}

      <Card>
        <CardHeader title="Equity Curve" />
        <EquityChart
          strategy={(isPortfolio ? r.equity_curve : r.strategy_curve) ?? []}
          buyHold={(isPortfolio ? r.equal_weight_buy_hold_curve : r.buy_hold_curve) ?? []}
          benchmark={r.benchmark_curve ?? []}
          benchmarkTicker={exp.config.benchmark}
        />
      </Card>

      <Card>
        <CardHeader title="Drawdown" />
        <DrawdownChart drawdown={r.drawdown_curve ?? []} />
      </Card>
    </div>
  );
}

function ValidationTab({ exp }: { exp: Experiment }) {
  const oos = exp.results?.out_of_sample;
  const wf = exp.results?.walk_forward;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Out-of-Sample Validation" />
        {oos && <ValidationOutcomeNote label="Out-of-Sample" outcome={oos} />}
        {oos?.completed && oos.result && (
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-xs min-w-[500px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Period</th><th className="pb-2 text-right">Return</th>
                  <th className="pb-2 text-right">Sharpe</th><th className="pb-2 text-right">Max DD</th><th className="pb-2 text-right">Trades</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(oos.result as unknown as OosResultShape).periods.map((p: OosPeriodShape) => (
                  <tr key={p.label}>
                    <td className="py-2 text-text-primary">{p.label}</td>
                    <td className={clsx("py-2 text-right tabular", (p.total_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish")}>{formatPercent(p.total_return_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{p.sharpe_ratio == null ? "N/A" : p.sharpe_ratio.toFixed(2)}</td>
                    <td className="py-2 text-right tabular text-bearish">{formatPercent(p.max_drawdown_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{p.number_of_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!oos?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
      </Card>

      <Card>
        <CardHeader title="Walk-Forward Analysis" />
        {wf && <ValidationOutcomeNote label="Walk-Forward" outcome={wf} />}
        {wf?.completed && wf.result && (
          <>
            <div className="flex gap-6 mb-3 text-xs mt-2">
              <span>Positive Folds: <span className="text-text-primary tabular">{(wf.result as unknown as WalkForwardResultShape).folds_with_positive_return} / {(wf.result as unknown as WalkForwardResultShape).folds.length}</span></span>
              <span>Avg Return: <span className="text-text-primary tabular">{formatPercent((wf.result as unknown as WalkForwardResultShape).average_test_return_percent)}</span></span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs min-w-[500px]">
                <thead>
                  <tr className="text-left text-text-faint uppercase tracking-wide">
                    <th className="pb-2">Fold</th><th className="pb-2">Test Period</th><th className="pb-2 text-right">Return</th><th className="pb-2 text-right">Sharpe</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(wf.result as unknown as WalkForwardResultShape).folds.map((f: WalkForwardFoldShape) => (
                    <tr key={f.fold_index}>
                      <td className="py-2 text-text-secondary">#{f.fold_index}</td>
                      <td className="py-2 text-text-secondary tabular">{f.test_start} → {f.test_end}</td>
                      <td className={clsx("py-2 text-right tabular", (f.test_total_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish")}>{formatPercent(f.test_total_return_percent)}</td>
                      <td className="py-2 text-right tabular text-text-secondary">{f.test_sharpe_ratio == null ? "N/A" : f.test_sharpe_ratio.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {!wf?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
      </Card>
    </div>
  );
}

function RobustnessTab({ exp }: { exp: Experiment }) {
  const sens = exp.results?.sensitivity;
  const mc = exp.results?.monte_carlo;
  const cost = exp.results?.cost_stress;
  const mcResult = mc?.result ? (mc.result as unknown as MonteCarloResultShape) : null;
  const costResult = cost?.result ? (cost.result as unknown as CostStressResultShape) : null;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Parameter Sensitivity" />
        {sens && <ValidationOutcomeNote label="Sensitivity" outcome={sens} />}
        {sens?.completed && sens.result && (
          <div className="flex flex-col gap-3 mt-2">
            {(sens.result as unknown as SensitivityResultShape).parameters.map((p: SensitivityParamShape) => (
              <div key={p.parameter} className="border border-border rounded p-2.5 flex items-center justify-between text-xs">
                <span className="text-text-primary">{p.label}</span>
                <span className="text-text-faint">{p.robustness.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        )}
        {!sens?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
      </Card>

      <Card>
        <CardHeader title="Monte Carlo" />
        {mc && <ValidationOutcomeNote label="Monte Carlo" outcome={mc} />}
        {mc?.completed && mc.result && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
            <Metric label="Median Return" value={formatPercent(mcResult?.median_return_percent ?? null)} />
            <Metric label="5th %ile Return" value={formatPercent(mcResult?.percentile_5_return_percent ?? null)} />
            <Metric label="95th %ile Return" value={formatPercent(mcResult?.percentile_95_return_percent ?? null)} />
            <Metric label="Median CAGR" value={formatPercent(mcResult?.median_cagr_percent ?? null)} />
            <Metric label="Probability of Loss" value={formatPercent(mcResult?.probability_of_loss_percent ?? null)} tone="bearish" />
            <Metric label={`P(DD > ${Math.abs(mcResult?.drawdown_threshold_percent ?? 0)}%)`} value={formatPercent(mcResult?.probability_of_exceeding_drawdown_threshold_percent ?? null)} tone="bearish" />
            <Metric label="Resampling" value={mcResult?.resampling_method?.replace(/_/g, " ") ?? "N/A"} />
            <Metric label="Seed" value={mcResult?.seed == null ? "Random" : String(mcResult.seed)} />
          </div>
        )}
        {!mc?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
      </Card>

      <Card>
        <CardHeader title="Cost Stress" />
        {cost && <ValidationOutcomeNote label="Cost Stress" outcome={cost} />}
        {cost?.completed && cost.result && (
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-xs min-w-[400px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Scenario</th><th className="pb-2 text-right">Net Return</th><th className="pb-2 text-right">Total Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(costResult?.commission_scenarios ?? []).map((s: CostScenarioShape) => (
                  <tr key={s.label}>
                    <td className="py-2 text-text-primary">{s.label}</td>
                    <td className={clsx("py-2 text-right tabular", (s.net_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish")}>{formatPercent(s.net_return_percent)}</td>
                    <td className="py-2 text-right tabular text-text-secondary">{formatPercent(s.total_cost_percent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!cost?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
      </Card>
    </div>
  );
}

function RegimeTab({ exp }: { exp: Experiment }) {
  const regime = exp.results?.regime_performance;
  const regimeResult = regime?.result ? (regime.result as unknown as RegimeResultShape) : null;
  return (
    <Card>
      <CardHeader title="Regime-Conditioned Performance" />
      {regime && <ValidationOutcomeNote label="Regime Analysis" outcome={regime} />}
      {regime?.completed && regime.result && (
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs min-w-[500px]">
            <thead>
              <tr className="text-left text-text-faint uppercase tracking-wide">
                <th className="pb-2">Regime</th><th className="pb-2 text-right">Days</th><th className="pb-2 text-right">Frequency</th><th className="pb-2 text-right">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(regimeResult?.buckets ?? []).map((b: RegimeBucketShape) => (
                <tr key={b.regime}>
                  <td className="py-2 text-text-primary">{b.regime}</td>
                  <td className="py-2 text-right tabular text-text-secondary">{b.trading_days}</td>
                  <td className="py-2 text-right tabular text-text-secondary">{formatPercent(b.frequency_percent)}</td>
                  <td className={clsx("py-2 text-right tabular", (b.compounded_return_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish")}>{formatPercent(b.compounded_return_percent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!regime?.requested && <p className="text-xs text-text-faint mt-2">Not requested for this experiment.</p>}
    </Card>
  );
}

function ForwardTab({ exp, busy, onStartForward, refreshKey }: { exp: Experiment; busy: boolean; onStartForward: () => void; refreshKey: number }) {
  const isPortfolio = exp.config.tickers.length > 1;
  const { data: fvh } = useApiResource<ForwardVsHistoricalResponse>(
    (signal) => getForwardVsHistorical(exp.id, signal),
    [exp.id, refreshKey],
    !!exp.forward_portfolio_id
  );

  if (!exp.forward_portfolio_id) {
    return (
      <Card>
        <CardHeader title="Forward Paper Simulation" />
        {isPortfolio ? (
          <p className="text-xs text-warning">
            Forward paper simulation is not yet supported for multi-ticker portfolio experiments - the paper-trading
            engine trades one ticker per order and has no portfolio-level forward engine yet.
          </p>
        ) : (
          <>
            <p className="text-xs text-text-muted mb-3">
              Starting a forward simulation creates a fresh paper portfolio inheriting this experiment&apos;s ticker,
              capital, and model version. Trades must still be placed manually via the Paper Trading page - there is
              no automatic order-placement engine.
            </p>
            <button
              onClick={onStartForward}
              disabled={busy}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              {busy ? <Loader2 size={15} className="animate-spin" /> : <PlayCircle size={15} />}
              Start Forward Simulation
            </button>
          </>
        )}
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Forward vs. Historical Expectation"
        subtitle={`Forward portfolio: ${exp.forward_portfolio_id} - manage trades on the Paper Trading page.`}
      />
      {!fvh ? (
        <SkeletonText lines={4} />
      ) : !fvh.available ? (
        <p className="text-xs text-text-muted">{fvh.reason}</p>
      ) : (
        <>
          {fvh.forward_sample_developing && (
            <p className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2 mb-3">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              Forward sample is still developing - too early to compare meaningfully.
            </p>
          )}
          <div className="overflow-x-auto mb-3">
            <table className="w-full text-xs min-w-[400px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Metric</th>
                  <th className="pb-2 text-right">Historical ({fvh.historical_source ?? "N/A"})</th>
                  <th className="pb-2 text-right">Forward</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr>
                  <td className="py-2 text-text-secondary">Return</td>
                  <td className="py-2 text-right tabular text-text-primary">{formatPercent(fvh.historical?.return_percent ?? null)}</td>
                  <td className="py-2 text-right tabular text-text-primary">{formatPercent(fvh.forward?.return_percent ?? null)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-text-secondary">Sharpe</td>
                  <td className="py-2 text-right tabular text-text-primary">{fvh.historical?.sharpe_ratio?.toFixed(2) ?? "N/A"}</td>
                  <td className="py-2 text-right tabular text-text-primary">{fvh.forward?.sharpe_ratio?.toFixed(2) ?? "N/A"}</td>
                </tr>
                <tr>
                  <td className="py-2 text-text-secondary">Max Drawdown</td>
                  <td className="py-2 text-right tabular text-bearish">{formatPercent(fvh.historical?.max_drawdown_percent ?? null)}</td>
                  <td className="py-2 text-right tabular text-bearish">{formatPercent(fvh.forward?.max_drawdown_percent ?? null)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          {fvh.deviation_notes.map((n, i) => (
            <p key={i} className="text-xs text-text-muted mb-1.5 last:mb-0">{n}</p>
          ))}
        </>
      )}
    </Card>
  );
}

function NotesTab({ exp, onSaved }: { exp: Experiment; onSaved: () => void }) {
  const [notes, setNotes] = useState(exp.notes);
  const [tagsInput, setTagsInput] = useState(exp.tags.join(", "));
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await updateExperimentNotes(exp.id, notes, tagsInput.split(",").map((t) => t.trim()).filter(Boolean));
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader title="Research Notes" subtitle="Free-form research metadata - never fed into the trading algorithm." />
      <div className="flex flex-col gap-3">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={6}
          className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary resize-y"
        />
        <label className="flex flex-col gap-1.5 text-xs">
          <span className="text-text-muted font-medium">Tags</span>
          <input
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
          />
        </label>
        <button
          onClick={save}
          disabled={saving}
          className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {saving ? <Loader2 size={15} className="animate-spin" /> : <RotateCcw size={15} />}
          Save
        </button>
      </div>
    </Card>
  );
}

function AuditTab({ exp }: { exp: Experiment }) {
  const prov = exp.data_provenance;
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader title="Data Provenance" />
        {prov ? (
          <div className="grid grid-cols-2 gap-3 text-xs">
            <Metric label="Data Source" value={prov.data_source} />
            <Metric label="Data Status" value={prov.data_status} />
            <Metric label="Retrieved At" value={formatDateTime(prov.retrieved_at)} />
            <Metric label="Latest Market Timestamp" value={prov.latest_market_timestamp ?? "N/A"} />
            <Metric label="Tickers Retrieved" value={prov.tickers_retrieved.join(", ") || "None"} />
            <Metric label="Tickers Unavailable" value={Object.keys(prov.tickers_unavailable).join(", ") || "None"} />
          </div>
        ) : (
          <p className="text-xs text-text-muted">No provenance recorded yet - run this experiment first.</p>
        )}
      </Card>

      <Card>
        <CardHeader title="Execution & Reproducibility" />
        <dl className="flex flex-col gap-2 text-xs">
          <div><dt className="text-text-secondary font-medium inline">Execution: </dt><dd className="text-text-muted inline">Signal calculated at candle close; execution at the next bar&apos;s open.</dd></div>
          <div><dt className="text-text-secondary font-medium inline">Costs: </dt><dd className="text-text-muted inline">{exp.config.commission_bps} bps commission + {exp.config.slippage_bps} bps slippage, charged on both entry and exit legs.</dd></div>
          <div><dt className="text-text-secondary font-medium inline">Look-ahead: </dt><dd className="text-text-muted inline">Tested - every indicator is causal, and execution timing is next-bar-only (unit tested directly).</dd></div>
          <div><dt className="text-text-secondary font-medium inline">Reproducibility Fingerprint: </dt><dd className="text-text-muted inline font-mono">{exp.fingerprint}</dd></div>
        </dl>
      </Card>
    </div>
  );
}
