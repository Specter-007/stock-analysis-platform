"use client";

import { useCallback, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { getStockHistory, getStockOverview, getStockSignal, getStockTechnical } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { PriceHeader } from "@/components/stock/PriceHeader";
import { PriceChart } from "@/components/stock/PriceChart";
import { SignalCard } from "@/components/stock/SignalCard";
import { FactorsList } from "@/components/stock/FactorsList";
import { IndicatorPanel } from "@/components/stock/IndicatorPanel";
import { RiskPanel } from "@/components/stock/RiskPanel";
import { CompanyInfo } from "@/components/stock/CompanyInfo";
import { TickerSearch } from "@/components/search/TickerSearch";
import { Skeleton, SkeletonText } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Card } from "@/components/ui/Card";
import { POPULAR_TICKERS, type ChartRange } from "@/lib/constants";
import type { ApiError } from "@/lib/api";

export default function AnalysisPageClient() {
  const searchParams = useSearchParams();
  const rawTicker = searchParams.get("ticker");
  const ticker = rawTicker ? rawTicker.trim().toUpperCase() : null;
  const [range, setRange] = useState<ChartRange>("1Y");

  const overview = useApiResource(
    (signal) => getStockOverview(ticker!, signal),
    [ticker],
    !!ticker
  );
  const history = useApiResource(
    (signal) => getStockHistory(ticker!, range, signal),
    [ticker, range],
    !!ticker
  );
  const technical = useApiResource(
    (signal) => getStockTechnical(ticker!, signal),
    [ticker],
    !!ticker
  );
  const signalResource = useApiResource(
    (signal) => getStockSignal(ticker!, signal),
    [ticker],
    !!ticker
  );

  const retryAll = useCallback(() => {
    // Re-triggering is handled naturally by React Router's key-based effect
    // deps; simplest reliable retry is a full reload of this ticker's data.
    window.location.reload();
  }, []);

  if (!ticker) {
    return <EmptyAnalysisState />;
  }

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      {overview.error ? (
        <ErrorState error={overview.error as ApiError} onRetry={retryAll} />
      ) : overview.loading || !overview.data ? (
        <HeaderSkeleton />
      ) : (
        <PriceHeader ticker={ticker} data={overview.data.data} meta={overview.data.meta} />
      )}

      <Card>
        {history.error ? (
          <ErrorState error={history.error as ApiError} onRetry={retryAll} />
        ) : (
          <PriceChart
            candles={history.data?.candles ?? []}
            isDaily={history.data?.is_daily ?? true}
            range={range}
            onRangeChange={setRange}
            loading={history.loading}
          />
        )}
      </Card>

      {signalResource.error ? (
        <ErrorState error={signalResource.error as ApiError} onRetry={retryAll} />
      ) : signalResource.loading || !signalResource.data ? (
        <Card>
          <SkeletonText lines={4} />
        </Card>
      ) : (
        <>
          <SignalCard signal={signalResource.data} />
          <FactorsList
            positive={signalResource.data.positive_factors}
            negative={signalResource.data.negative_factors}
            neutral={signalResource.data.neutral_factors}
            confidence={signalResource.data.confidence}
          />
          <RiskPanel risk={signalResource.data.risk} />
        </>
      )}

      {technical.error ? (
        <ErrorState error={technical.error as ApiError} onRetry={retryAll} />
      ) : technical.loading || !technical.data ? (
        <Card>
          <SkeletonText lines={6} />
        </Card>
      ) : (
        <IndicatorPanel technical={technical.data} />
      )}

      {overview.data && <CompanyInfo data={overview.data.data} />}
    </div>
  );
}

function HeaderSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-8 w-32" />
      </div>
      <Skeleton className="h-6 w-64" />
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-14" />
        ))}
      </div>
    </div>
  );
}

function EmptyAnalysisState() {
  return (
    <div className="mx-auto max-w-2xl px-4 sm:px-6 py-24 flex flex-col items-center text-center gap-5">
      <Search size={28} className="text-text-muted" aria-hidden="true" />
      <h1 className="text-xl font-semibold text-text-primary">Search for a stock to analyze</h1>
      <p className="text-sm text-text-muted max-w-md">
        Enter a ticker symbol to see real-time market data, technical indicators, and the deterministic
        BUY/HOLD/SELL signal for that stock.
      </p>
      <div className="w-full max-w-md">
        <TickerSearch autoFocus />
      </div>
      <div className="flex flex-wrap justify-center gap-2 pt-1">
        {POPULAR_TICKERS.map((t) => (
          <a
            key={t}
            href={`/analysis?ticker=${t}`}
            className="font-mono text-xs px-2.5 py-1 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors"
          >
            {t}
          </a>
        ))}
      </div>
    </div>
  );
}
