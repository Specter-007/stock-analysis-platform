"use client";

import { useState } from "react";
import { RotateCcw, ArrowDownCircle, ArrowUpCircle, FlaskConical, XCircle, ShieldAlert } from "lucide-react";
import { clsx } from "clsx";
import { getPaperPortfolio, getPaperRisk, postPaperTrade, resetPaperPortfolio, closeAllPaperPositions, ApiError } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonText } from "@/components/ui/Skeleton";
import { formatCurrency, formatPercent, formatPrice } from "@/lib/format";
import type { PaperPortfolioResponse, PositionSizingMode } from "@/types/api";
import { ForwardValidationPanel } from "./ForwardValidationPanel";

const PORTFOLIO_ID = "default";

export default function PaperTradingPageClient() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, loading, error } = useApiResource(
    (signal) => getPaperPortfolio(PORTFOLIO_ID, signal),
    [refreshKey]
  );
  const { data: risk } = useApiResource((signal) => getPaperRisk(PORTFOLIO_ID, signal), [refreshKey, data?.current_value]);

  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [ticker, setTicker] = useState("AAPL");
  const [sizingMode, setSizingMode] = useState<PositionSizingMode>("FIXED_SHARES");
  const [shares, setShares] = useState(1);
  const [capitalPercent, setCapitalPercent] = useState(10);
  const [riskPercent, setRiskPercent] = useState(1);
  const [stopLoss, setStopLoss] = useState<string>("");
  const [takeProfit, setTakeProfit] = useState<string>("");
  const [trailingStop, setTrailingStop] = useState<string>("");

  async function submitTrade(action: "BUY" | "SELL") {
    setBusy(true);
    setActionError(null);
    try {
      await postPaperTrade({
        portfolio_id: PORTFOLIO_ID,
        ticker: ticker.trim().toUpperCase(),
        action,
        shares: sizingMode === "FIXED_SHARES" ? shares : undefined,
        sizing_mode: action === "BUY" ? sizingMode : undefined,
        capital_percent: sizingMode === "FIXED_CAPITAL_PERCENT" ? capitalPercent : undefined,
        risk_percent: sizingMode === "RISK_PERCENT" ? riskPercent : undefined,
        stop_loss_percent: action === "BUY" && stopLoss ? Number(stopLoss) : undefined,
        take_profit_percent: action === "BUY" && takeProfit ? Number(takeProfit) : undefined,
        trailing_stop_percent: action === "BUY" && trailingStop ? Number(trailingStop) : undefined,
      });
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Trade failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    setBusy(true);
    setActionError(null);
    try {
      await resetPaperPortfolio(PORTFOLIO_ID, 10000);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCloseAll() {
    setBusy(true);
    setActionError(null);
    try {
      await closeAllPaperPositions(PORTFOLIO_ID);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Close-all failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary mb-1 flex items-center gap-2">
            Paper Trading
            <span className="inline-flex items-center gap-1 text-xs font-medium text-warning bg-warning-dim border border-warning/30 rounded-full px-2 py-0.5">
              <FlaskConical size={12} aria-hidden="true" /> Simulation Only
            </span>
          </h1>
          <p className="text-sm text-text-muted max-w-2xl">
            Virtual portfolio, real live-retrieved quotes. No real money, no brokerage execution, no real orders.
            Commission and slippage are modeled on every trade.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCloseAll}
            disabled={busy}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors cursor-pointer disabled:opacity-50"
          >
            <XCircle size={13} /> Close All
          </button>
          <button
            onClick={handleReset}
            disabled={busy}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors cursor-pointer disabled:opacity-50"
          >
            <RotateCcw size={13} /> Reset Portfolio
          </button>
        </div>
      </div>

      {error ? (
        <ErrorState error={error as ApiError} onRetry={() => setRefreshKey((k) => k + 1)} />
      ) : loading || !data ? (
        <Card>
          <SkeletonText lines={6} />
        </Card>
      ) : (
        <>
          <PortfolioOverview portfolio={data} />

          <ForwardValidationPanel portfolioId={PORTFOLIO_ID} refreshKey={refreshKey} />

          {risk && risk.warnings.length > 0 && (
            <Card>
              <CardHeader title="Portfolio Risk" subtitle="Computed from current real positions and live quotes" />
              <div className="flex flex-col gap-1.5 mb-3">
                {risk.warnings.map((w, i) => (
                  <p key={i} className="flex items-start gap-2 text-xs text-warning bg-warning-dim border border-warning/25 rounded px-3 py-2">
                    <ShieldAlert size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
                    {w}
                  </p>
                ))}
              </div>
              {Object.keys(risk.sector_concentration).length > 0 && (
                <div className="flex flex-wrap gap-2 text-xs">
                  {Object.entries(risk.sector_concentration).map(([sector, pct]) => (
                    <span key={sector} className="px-2 py-1 rounded bg-bg-elevated border border-border text-text-secondary">
                      {sector}: {pct.toFixed(1)}%
                    </span>
                  ))}
                </div>
              )}
            </Card>
          )}

          <Card>
            <CardHeader title="Place a Trade" />
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1.5 text-xs">
                  <span className="text-text-muted font-medium">Ticker</span>
                  <input
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-28"
                  />
                </label>
                <label className="flex flex-col gap-1.5 text-xs">
                  <span className="text-text-muted font-medium">Sizing (buy)</span>
                  <select
                    value={sizingMode}
                    onChange={(e) => setSizingMode(e.target.value as PositionSizingMode)}
                    className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
                  >
                    <option value="FIXED_SHARES">Fixed shares</option>
                    <option value="FIXED_CAPITAL_PERCENT">% of portfolio</option>
                    <option value="RISK_PERCENT">Risk % (needs stop-loss)</option>
                  </select>
                </label>

                {sizingMode === "FIXED_SHARES" && (
                  <NumberField label="Shares" value={shares} onChange={setShares} step={1} min={0.01} />
                )}
                {sizingMode === "FIXED_CAPITAL_PERCENT" && (
                  <NumberField label="% of Portfolio" value={capitalPercent} onChange={setCapitalPercent} step={1} min={1} max={100} />
                )}
                {sizingMode === "RISK_PERCENT" && (
                  <NumberField label="Risk % of Portfolio" value={riskPercent} onChange={setRiskPercent} step={0.5} min={0.1} max={100} />
                )}
              </div>

              <div className="flex flex-wrap items-end gap-3">
                <PercentField label="Stop-Loss %" value={stopLoss} onChange={setStopLoss} />
                <PercentField label="Take-Profit %" value={takeProfit} onChange={setTakeProfit} />
                <PercentField label="Trailing Stop %" value={trailingStop} onChange={setTrailingStop} />

                <button
                  onClick={() => submitTrade("BUY")}
                  disabled={busy}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-bullish text-bg text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer transition-opacity"
                >
                  <ArrowUpCircle size={15} /> Buy
                </button>
                <button
                  onClick={() => submitTrade("SELL")}
                  disabled={busy}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-bearish text-bg text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer transition-opacity"
                >
                  <ArrowDownCircle size={15} /> Sell All Held
                </button>
              </div>
            </div>
            {actionError && <p className="text-xs text-bearish mt-3">{actionError}</p>}
          </Card>

          <Card>
            <CardHeader title="Positions" />
            {data.positions.length === 0 ? (
              <p className="text-xs text-text-muted">No open positions.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs min-w-[720px]">
                  <thead>
                    <tr className="text-left text-text-faint uppercase tracking-wide">
                      <th className="pb-2">Ticker</th>
                      <th className="pb-2 text-right">Shares</th>
                      <th className="pb-2 text-right">Avg Entry</th>
                      <th className="pb-2 text-right">Current Price</th>
                      <th className="pb-2 text-right">Market Value</th>
                      <th className="pb-2 text-right">P&amp;L</th>
                      <th className="pb-2 text-right">P&amp;L %</th>
                      <th className="pb-2">Risk Controls</th>
                      <th className="pb-2">Entry Signal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.positions.map((p) => (
                      <tr key={p.ticker}>
                        <td className="py-2 font-mono text-text-primary">{p.ticker}</td>
                        <td className="py-2 text-right tabular text-text-secondary">{p.shares.toFixed(4)}</td>
                        <td className="py-2 text-right tabular text-text-secondary">{formatPrice(p.avg_entry_price)}</td>
                        <td className="py-2 text-right tabular text-text-secondary">{formatPrice(p.current_price)}</td>
                        <td className="py-2 text-right tabular text-text-secondary">{formatCurrency(p.market_value)}</td>
                        <td
                          className={clsx(
                            "py-2 text-right tabular font-medium",
                            (p.unrealized_pnl ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                          )}
                        >
                          {formatCurrency(p.unrealized_pnl)}
                        </td>
                        <td
                          className={clsx(
                            "py-2 text-right tabular font-medium",
                            (p.unrealized_pnl_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                          )}
                        >
                          {formatPercent(p.unrealized_pnl_percent)}
                        </td>
                        <td className="py-2 text-text-faint">
                          {[
                            p.stop_loss_percent ? `SL -${p.stop_loss_percent}%` : null,
                            p.take_profit_percent ? `TP +${p.take_profit_percent}%` : null,
                            p.trailing_stop_percent ? `Trail -${p.trailing_stop_percent}%` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "None"}
                        </td>
                        <td className="py-2 text-text-faint">
                          {p.entry_signal ? `${p.entry_signal} (${p.entry_score?.toFixed(0)})` : "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader title="Trade Journal" subtitle={`${data.trades.length} trade(s)`} />
            {data.trades.length === 0 ? (
              <p className="text-xs text-text-muted">No trades yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs min-w-[900px]">
                  <thead>
                    <tr className="text-left text-text-faint uppercase tracking-wide">
                      <th className="pb-2">Date</th>
                      <th className="pb-2">Ticker</th>
                      <th className="pb-2">Action</th>
                      <th className="pb-2 text-right">Shares</th>
                      <th className="pb-2 text-right">Price</th>
                      <th className="pb-2 text-right">Gross P&amp;L</th>
                      <th className="pb-2 text-right">Fees</th>
                      <th className="pb-2 text-right">Slippage</th>
                      <th className="pb-2 text-right">Net P&amp;L</th>
                      <th className="pb-2">Exit Reason</th>
                      <th className="pb-2">Regime</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {[...data.trades].reverse().map((t, i) => (
                      <tr key={i}>
                        <td className="py-2 text-text-secondary tabular">{new Date(t.date).toLocaleString()}</td>
                        <td className="py-2 font-mono text-text-primary">{t.ticker}</td>
                        <td className={clsx("py-2 font-medium", t.action === "BUY" ? "text-bullish" : "text-bearish")}>
                          {t.action}
                        </td>
                        <td className="py-2 text-right tabular text-text-secondary">{t.shares.toFixed(4)}</td>
                        <td className="py-2 text-right tabular text-text-secondary">{formatPrice(t.price)}</td>
                        <td className="py-2 text-right tabular text-text-secondary">
                          {t.gross_pnl === null ? "—" : formatCurrency(t.gross_pnl)}
                        </td>
                        <td className="py-2 text-right tabular text-bearish">{t.fees === null ? "—" : `-${formatCurrency(t.fees)}`}</td>
                        <td className="py-2 text-right tabular text-bearish">
                          {t.slippage === null ? "—" : `-${formatCurrency(t.slippage)}`}
                        </td>
                        <td
                          className={clsx(
                            "py-2 text-right tabular font-medium",
                            t.net_pnl === null ? "text-text-faint" : t.net_pnl >= 0 ? "text-bullish" : "text-bearish"
                          )}
                        >
                          {t.net_pnl === null ? "—" : formatCurrency(t.net_pnl)}
                        </td>
                        <td className="py-2 text-text-faint">{t.exit_reason ?? "—"}</td>
                        <td className="py-2 text-text-faint">{t.market_regime ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <p className="text-[11px] text-text-faint leading-relaxed">{data.disclaimer}</p>
        </>
      )}
    </div>
  );
}

function PortfolioOverview({ portfolio }: { portfolio: PaperPortfolioResponse }) {
  const stats: { label: string; value: string; tone?: "bullish" | "bearish" }[] = [
    { label: "Starting Capital", value: formatCurrency(portfolio.starting_capital) },
    { label: "Current Value", value: formatCurrency(portfolio.current_value) },
    {
      label: "Total Return",
      value: formatPercent(portfolio.total_return_percent),
      tone: portfolio.total_return_percent >= 0 ? "bullish" : "bearish",
    },
    { label: "Cash", value: formatCurrency(portfolio.cash) },
    { label: "Exposure", value: formatPercent(portfolio.exposure_percent) },
    { label: "Largest Position", value: formatPercent(portfolio.largest_position_percent) },
    {
      label: "Realized P&L",
      value: formatCurrency(portfolio.realized_pnl),
      tone: portfolio.realized_pnl >= 0 ? "bullish" : "bearish",
    },
    {
      label: "Unrealized P&L",
      value: formatCurrency(portfolio.unrealized_pnl),
      tone: portfolio.unrealized_pnl >= 0 ? "bullish" : "bearish",
    },
  ];

  return (
    <Card>
      <CardHeader title="Portfolio Overview" subtitle={`${portfolio.number_of_positions} position(s)`} />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
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

function PercentField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1.5 text-xs">
      <span className="text-text-muted font-medium">{label}</span>
      <input
        type="number"
        value={value}
        step={0.5}
        min={0}
        placeholder="Off"
        onChange={(e) => onChange(e.target.value)}
        className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary w-28"
      />
    </label>
  );
}
