"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";
import { getMarketStatus } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { DataFreshnessBadge } from "@/components/ui/DataFreshnessBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { formatPercent, formatPrice } from "@/lib/format";
import type { ApiError } from "@/lib/api";
import type { IndexQuote, MoverQuote } from "@/types/api";

export default function MarketOverviewClient() {
  const { data, loading, error } = useApiResource((signal) => getMarketStatus(signal), []);

  if (error) {
    return (
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8">
        <ErrorState error={error as ApiError} onRetry={() => window.location.reload()} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-2">Markets</h1>
        {data && <DataFreshnessBadge meta={data.meta} />}
      </div>

      <Card>
        <CardHeader title="Major Indexes" />
        {loading || !data ? (
          <SkeletonGrid n={5} />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {data.indexes.map((idx) => (
              <IndexTile key={idx.symbol} index={idx} />
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Top Gainers" subtitle="From a fixed watchlist of large, liquid tickers" />
          {loading || !data ? (
            <SkeletonList />
          ) : data.gainers.length === 0 ? (
            <EmptyMovers label="gainers" />
          ) : (
            <MoversTable movers={data.gainers} />
          )}
        </Card>
        <Card>
          <CardHeader title="Top Losers" subtitle="From a fixed watchlist of large, liquid tickers" />
          {loading || !data ? (
            <SkeletonList />
          ) : data.losers.length === 0 ? (
            <EmptyMovers label="losers" />
          ) : (
            <MoversTable movers={data.losers} />
          )}
        </Card>
      </div>
    </div>
  );
}

function IndexTile({ index }: { index: IndexQuote }) {
  if (index.status === "UNAVAILABLE" || index.last_price === null) {
    return (
      <div className="border border-border rounded-md p-3 bg-bg-elevated">
        <p className="text-xs text-text-muted">{index.name}</p>
        <p className="text-sm text-text-faint mt-1">Data unavailable</p>
      </div>
    );
  }

  const isUp = (index.change ?? 0) >= 0;
  return (
    <div className="border border-border rounded-md p-3 bg-bg-elevated">
      <p className="text-xs text-text-muted truncate">{index.name}</p>
      <p className="text-sm font-mono tabular text-text-primary mt-1">{formatPrice(index.last_price)}</p>
      <p className={clsx("text-xs font-medium flex items-center gap-1 mt-0.5", isUp ? "text-bullish" : "text-bearish")}>
        {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
        {formatPercent(index.change_percent)}
      </p>
    </div>
  );
}

function MoversTable({ movers }: { movers: MoverQuote[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-text-faint text-[11px] uppercase tracking-wide">
          <th className="pb-2 font-medium">Symbol</th>
          <th className="pb-2 font-medium text-right">Price</th>
          <th className="pb-2 font-medium text-right">Change</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {movers.map((m) => {
          const isUp = m.change_percent >= 0;
          return (
            <tr key={m.symbol}>
              <td className="py-2">
                <Link href={`/analysis?ticker=${m.symbol}`} className="font-mono text-accent hover:underline">
                  {m.symbol}
                </Link>
              </td>
              <td className="py-2 text-right tabular text-text-primary">{formatPrice(m.last_price)}</td>
              <td className={clsx("py-2 text-right tabular font-medium", isUp ? "text-bullish" : "text-bearish")}>
                {formatPercent(m.change_percent)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function EmptyMovers({ label }: { label: string }) {
  return <p className="text-xs text-text-muted">No {label} found in the current watchlist right now.</p>;
}

function SkeletonGrid({ n }: { n: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {Array.from({ length: n }).map((_, i) => (
        <Skeleton key={i} className="h-16" />
      ))}
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}
