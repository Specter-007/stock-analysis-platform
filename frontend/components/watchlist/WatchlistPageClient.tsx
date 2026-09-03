"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2, Plus } from "lucide-react";
import { clsx } from "clsx";
import { addToWatchlist, removeFromWatchlist, getWatchlist, ApiError } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonText } from "@/components/ui/Skeleton";
import { StatusPill, signalToStatus } from "@/components/ui/StatusPill";
import { formatPercent, formatPrice, DATA_STATUS_LABEL } from "@/lib/format";
import { SIGNAL_LABELS } from "@/lib/constants";

const WATCHLIST_ID = "default";

export default function WatchlistPageClient() {
  const [refreshKey, setRefreshKey] = useState(0);
  const { data, loading, error } = useApiResource((signal) => getWatchlist(WATCHLIST_ID, signal), [refreshKey]);
  const [newTicker, setNewTicker] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleAdd() {
    if (!newTicker.trim()) return;
    setBusy(true);
    setActionError(null);
    try {
      await addToWatchlist(newTicker.trim().toUpperCase(), WATCHLIST_ID);
      setNewTicker("");
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not add ticker.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(ticker: string) {
    setBusy(true);
    try {
      await removeFromWatchlist(ticker, WATCHLIST_ID);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not remove ticker.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1">Watchlist</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          Real quotes and the same deterministic signal engine used everywhere else in the app - computed
          fresh for every ticker on this list, not a cached summary.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1.5 text-xs flex-1 min-w-[160px]">
            <span className="text-text-muted font-medium">Add ticker</span>
            <input
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              placeholder="e.g. NVDA"
              className="bg-bg-elevated border border-border-strong rounded-md px-3 py-2 text-sm text-text-primary"
            />
          </label>
          <button
            onClick={handleAdd}
            disabled={busy}
            className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 cursor-pointer"
          >
            <Plus size={15} /> Add
          </button>
        </div>
        {actionError && <p className="text-xs text-bearish mt-3">{actionError}</p>}
      </Card>

      {error ? (
        <ErrorState error={error as ApiError} onRetry={() => setRefreshKey((k) => k + 1)} />
      ) : loading || !data ? (
        <Card>
          <SkeletonText lines={6} />
        </Card>
      ) : data.entries.length === 0 ? (
        <Card>
          <p className="text-sm text-text-muted">No tickers yet. Add one above to get started.</p>
        </Card>
      ) : (
        <Card>
          <CardHeader title="Tickers" subtitle={`${data.entries.length} ticker(s)`} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[820px]">
              <thead>
                <tr className="text-left text-text-faint uppercase tracking-wide">
                  <th className="pb-2">Ticker</th>
                  <th className="pb-2 text-right">Price</th>
                  <th className="pb-2 text-right">Change</th>
                  <th className="pb-2">Signal</th>
                  <th className="pb-2 text-right">Score</th>
                  <th className="pb-2">Trend</th>
                  <th className="pb-2">Regime</th>
                  <th className="pb-2">Data</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.entries.map((e) => (
                  <tr key={e.ticker}>
                    <td className="py-2">
                      <Link href={`/analysis?ticker=${e.ticker}`} className="font-mono text-accent hover:underline">
                        {e.ticker}
                      </Link>
                      {e.signal_changed_today && (
                        <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-warning" title="Signal changed" />
                      )}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {e.error ? "—" : formatPrice(e.price)}
                    </td>
                    <td
                      className={clsx(
                        "py-2 text-right tabular font-medium",
                        (e.change_percent ?? 0) >= 0 ? "text-bullish" : "text-bearish"
                      )}
                    >
                      {e.error ? "—" : formatPercent(e.change_percent)}
                    </td>
                    <td className="py-2">
                      {e.signal ? (
                        <StatusPill status={signalToStatus(e.signal)} label={SIGNAL_LABELS[e.signal] ?? e.signal} />
                      ) : (
                        <span className="text-text-faint">N/A</span>
                      )}
                    </td>
                    <td className="py-2 text-right tabular text-text-secondary">
                      {e.score !== null ? e.score.toFixed(0) : "N/A"}
                    </td>
                    <td className="py-2 text-text-secondary">{e.trend_classification ?? "N/A"}</td>
                    <td className="py-2 text-text-secondary">{e.market_regime ?? "N/A"}</td>
                    <td className="py-2 text-text-faint">{DATA_STATUS_LABEL[e.data_status] ?? e.data_status}</td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => handleRemove(e.ticker)}
                        disabled={busy}
                        aria-label={`Remove ${e.ticker}`}
                        className="text-text-faint hover:text-bearish cursor-pointer disabled:opacity-50"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.entries.some((e) => e.error) && (
            <p className="text-[11px] text-text-faint mt-3">
              Some tickers could not be refreshed right now and show N/A - this is never filled with a fabricated value.
            </p>
          )}
        </Card>
      )}
    </div>
  );
}
