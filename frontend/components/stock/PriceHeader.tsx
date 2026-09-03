import { TrendingUp, TrendingDown } from "lucide-react";
import { clsx } from "clsx";
import type { OverviewData, DataMeta } from "@/types/api";
import { formatPrice, formatPercent, formatCompactNumber } from "@/lib/format";
import { DataFreshnessBadge } from "@/components/ui/DataFreshnessBadge";

export function PriceHeader({
  ticker,
  data,
  meta,
}: {
  ticker: string;
  data: OverviewData;
  meta: DataMeta;
}) {
  const isUp = (data.change ?? 0) >= 0;
  const hasChange = data.change !== null && data.change_percent !== null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold text-text-primary font-mono">{ticker}</h1>
            <span className="text-text-muted text-sm">{data.company_name}</span>
          </div>
          <p className="text-xs text-text-faint mt-0.5">
            {data.exchange} &middot; {data.currency} &middot; {data.sector !== "N/A" ? data.sector : "Sector N/A"}
          </p>
        </div>

        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <span className="text-3xl font-semibold text-text-primary tabular">
              {data.last_price !== null ? formatPrice(data.last_price) : "N/A"}
            </span>
            {data.currency && data.last_price !== null && (
              <span className="text-sm text-text-muted">{data.currency}</span>
            )}
          </div>
          {hasChange && (
            <div
              className={clsx(
                "flex items-center gap-1.5 justify-end text-sm font-medium mt-1",
                isUp ? "text-bullish" : "text-bearish"
              )}
            >
              {isUp ? <TrendingUp size={14} aria-hidden="true" /> : <TrendingDown size={14} aria-hidden="true" />}
              <span className="tabular">
                {isUp ? "+" : ""}
                {formatPrice(data.change)} ({formatPercent(data.change_percent)})
              </span>
            </div>
          )}
        </div>
      </div>

      <DataFreshnessBadge meta={meta} />

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 text-xs">
        <Stat label="Prev. Close" value={formatPrice(data.previous_close)} />
        <Stat label="Day Range" value={`${formatPrice(data.day_low)} – ${formatPrice(data.day_high)}`} />
        <Stat
          label="52W Range"
          value={`${formatPrice(data.fifty_two_week_low)} – ${formatPrice(data.fifty_two_week_high)}`}
        />
        <Stat label="Volume" value={formatCompactNumber(data.volume)} />
        <Stat label="Avg. Volume" value={formatCompactNumber(data.average_volume)} />
        <Stat label="Market Cap" value={formatCompactNumber(data.market_cap)} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border rounded p-2.5 bg-bg-elevated">
      <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{label}</p>
      <p className="text-text-primary font-medium tabular">{value}</p>
    </div>
  );
}
