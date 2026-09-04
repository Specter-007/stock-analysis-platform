"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FlaskConical, Loader2, Play } from "lucide-react";
import { createExperiment, runExperiment, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import type { AllocationMethod, ExperimentConfig, RebalanceFrequency } from "@/types/api";

const MODEL_VERSIONS = ["1.1", "1.0"];
const ALLOCATION_OPTIONS: { value: AllocationMethod; label: string }[] = [
  { value: "EQUAL_WEIGHT", label: "Equal Weight" },
  { value: "SIGNAL_WEIGHTED", label: "Signal Weighted" },
  { value: "RISK_WEIGHTED", label: "Risk Weighted" },
  { value: "FIXED_WEIGHT", label: "Fixed Weight" },
];
const REBALANCE_OPTIONS: { value: RebalanceFrequency; label: string }[] = [
  { value: "DAILY", label: "Daily" },
  { value: "WEEKLY", label: "Weekly" },
  { value: "MONTHLY", label: "Monthly" },
];

const VALIDATION_FLAGS: { key: keyof ExperimentConfig; label: string; description: string }[] = [
  { key: "run_out_of_sample", label: "Out-of-Sample", description: "Splits history into in-sample/validation/out-of-sample thirds" },
  { key: "run_walk_forward", label: "Walk-Forward", description: "Sequential train/test windows across history" },
  { key: "run_sensitivity", label: "Sensitivity", description: "Parameter robustness sweep (thresholds by default)" },
  { key: "run_monte_carlo", label: "Monte Carlo", description: "Bootstrap resampling stress test" },
  { key: "run_regime_analysis", label: "Regime Analysis", description: "Performance grouped by market regime" },
  { key: "run_cost_stress", label: "Cost Stress", description: "Commission/slippage friction sensitivity" },
];

export default function ExperimentLabPageClient() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [tickersInput, setTickersInput] = useState("AAPL");
  const [benchmark, setBenchmark] = useState("SPY");
  const [modelVersion, setModelVersion] = useState("1.1");
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commissionBps, setCommissionBps] = useState(5);
  const [slippageBps, setSlippageBps] = useState(5);
  const [allocationMethod, setAllocationMethod] = useState<AllocationMethod>("EQUAL_WEIGHT");
  const [rebalanceFrequency, setRebalanceFrequency] = useState<RebalanceFrequency>("MONTHLY");
  const [flags, setFlags] = useState<Record<string, boolean>>({
    run_out_of_sample: true,
    run_walk_forward: false,
    run_sensitivity: true,
    run_monte_carlo: true,
    run_regime_analysis: false,
    run_cost_stress: false,
  });
  const [monteCarloSimulations, setMonteCarloSimulations] = useState(1000);
  const [notes, setNotes] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tickers = tickersInput.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
  const isPortfolio = tickers.length > 1;

  async function handleCreateAndRun() {
    setBusy(true);
    setError(null);
    try {
      const config: ExperimentConfig = {
        model_version: modelVersion,
        tickers,
        benchmark: benchmark.trim().toUpperCase(),
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        commission_bps: commissionBps,
        slippage_bps: slippageBps,
        allocation_method: isPortfolio ? allocationMethod : null,
        rebalance_frequency: isPortfolio ? rebalanceFrequency : null,
        portfolio_constraints: null,
        run_out_of_sample: flags.run_out_of_sample,
        run_walk_forward: flags.run_walk_forward,
        run_sensitivity: flags.run_sensitivity,
        run_monte_carlo: flags.run_monte_carlo,
        run_regime_analysis: flags.run_regime_analysis,
        run_cost_stress: flags.run_cost_stress,
        monte_carlo_simulations: monteCarloSimulations,
        monte_carlo_seed: null,
        sensitivity_parameters: ["buy_threshold", "sell_threshold"],
        walk_forward_train_years: 2,
        walk_forward_test_years: 1,
        walk_forward_max_folds: 5,
      };

      const created = await createExperiment({
        name: name.trim() || `${tickers.join("/")} ${modelVersion}`,
        config,
        notes,
        tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean),
      });
      await runExperiment(created.id);
      router.push(`/experiments/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create experiment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1000px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1 flex items-center gap-2">
          <FlaskConical size={20} className="text-accent" aria-hidden="true" />
          Experiment Lab
        </h1>
        <p className="text-sm text-text-muted max-w-2xl">
          An experiment stores the CONFIGURATION that produced a result, not just the numbers - so it can be
          reopened, reproduced, or compared long after today&apos;s defaults have changed. Every run reuses the
          same backtest, out-of-sample, walk-forward, sensitivity, Monte Carlo, regime, and cost-stress engines
          used elsewhere in this app.
        </p>
      </div>

      <Card>
        <CardHeader title="Configuration" />
        <div className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="text-text-muted font-medium">Experiment Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. AAPL Momentum Baseline"
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>

          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1.5 text-xs flex-1 min-w-[200px]">
              <span className="text-text-muted font-medium">Tickers (comma-separated, 1-20)</span>
              <input
                value={tickersInput}
                onChange={(e) => setTickersInput(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Benchmark</span>
              <input
                value={benchmark}
                onChange={(e) => setBenchmark(e.target.value.toUpperCase())}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-24"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Model</span>
              <select
                value={modelVersion}
                onChange={(e) => setModelVersion(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              >
                {MODEL_VERSIONS.map((v) => (
                  <option key={v} value={v}>
                    v{v}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Start Date</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">End Date</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Initial Capital</span>
              <input
                type="number"
                value={initialCapital}
                step={1000}
                min={100}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-32"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Commission (bps)</span>
              <input
                type="number"
                value={commissionBps}
                step={1}
                min={0}
                onChange={(e) => setCommissionBps(Number(e.target.value))}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-24"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Slippage (bps)</span>
              <input
                type="number"
                value={slippageBps}
                step={1}
                min={0}
                onChange={(e) => setSlippageBps(Number(e.target.value))}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-24"
              />
            </label>
          </div>

          {isPortfolio && (
            <div className="flex flex-wrap items-end gap-3 border-t border-border pt-3">
              <p className="text-xs text-text-muted w-full">Portfolio settings (2+ tickers detected)</p>
              <label className="flex flex-col gap-1.5 text-xs">
                <span className="text-text-muted font-medium">Allocation Method</span>
                <select
                  value={allocationMethod}
                  onChange={(e) => setAllocationMethod(e.target.value as AllocationMethod)}
                  className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
                >
                  {ALLOCATION_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1.5 text-xs">
                <span className="text-text-muted font-medium">Rebalance Frequency</span>
                <select
                  value={rebalanceFrequency}
                  onChange={(e) => setRebalanceFrequency(e.target.value as RebalanceFrequency)}
                  className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
                >
                  {REBALANCE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-[11px] text-text-faint w-full">
                Out-of-sample/walk-forward/sensitivity/Monte Carlo/regime/cost-stress validation is not yet
                available for multi-ticker portfolio experiments - requesting one will be recorded as
                &quot;not yet implemented for portfolios&quot; rather than silently skipped.
              </p>
            </div>
          )}

          <div className="border-t border-border pt-3">
            <p className="text-xs text-text-muted font-medium mb-2">Validation Procedures</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {VALIDATION_FLAGS.map((f) => (
                <label
                  key={f.key}
                  className="flex items-start gap-2 text-xs border border-border rounded-md p-2.5 bg-bg-elevated cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={!!flags[f.key as string]}
                    onChange={(e) => setFlags((prev) => ({ ...prev, [f.key as string]: e.target.checked }))}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="text-text-primary font-medium block">{f.label}</span>
                    <span className="text-text-faint">{f.description}</span>
                  </span>
                </label>
              ))}
            </div>
            {flags.run_monte_carlo && (
              <label className="flex flex-col gap-1.5 text-xs mt-3 w-40">
                <span className="text-text-muted font-medium">Monte Carlo Simulations</span>
                <input
                  type="number"
                  value={monteCarloSimulations}
                  step={100}
                  min={100}
                  max={5000}
                  onChange={(e) => setMonteCarloSimulations(Number(e.target.value))}
                  className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
                />
              </label>
            )}
          </div>

          <div className="border-t border-border pt-3 flex flex-col gap-3">
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Research Notes (optional)</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Hypothesis: trend + momentum holds up better in high-volatility regimes."
                rows={2}
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary resize-y"
              />
            </label>
            <label className="flex flex-col gap-1.5 text-xs">
              <span className="text-text-muted font-medium">Tags (comma-separated, optional)</span>
              <input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="baseline, momentum, candidate"
                className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
              />
            </label>
          </div>

          {error && <p className="text-xs text-bearish">{error}</p>}

          <button
            onClick={handleCreateAndRun}
            disabled={busy || tickers.length === 0}
            className="self-start inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            Create &amp; Run Experiment
          </button>
        </div>
      </Card>
    </div>
  );
}
