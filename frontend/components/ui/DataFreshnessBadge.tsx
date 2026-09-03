import { Radio, Clock, Archive, WifiOff } from "lucide-react";
import { clsx } from "clsx";
import type { DataMeta } from "@/types/api";
import { DATA_STATUS_LABEL, formatDateTime } from "@/lib/format";

const STATUS_STYLE: Record<string, { icon: typeof Radio; text: string; bg: string; border: string }> = {
  LIVE: { icon: Radio, text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/30" },
  DELAYED: { icon: Clock, text: "text-warning", bg: "bg-warning-dim", border: "border-warning/30" },
  MARKET_CLOSED: { icon: Archive, text: "text-text-secondary", bg: "bg-card-hover", border: "border-border-strong" },
  HISTORICAL: { icon: Archive, text: "text-text-secondary", bg: "bg-card-hover", border: "border-border-strong" },
  UNAVAILABLE: { icon: WifiOff, text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/30" },
};

export function DataFreshnessBadge({ meta, compact = false }: { meta: DataMeta; compact?: boolean }) {
  const style = STATUS_STYLE[meta.data_status] ?? STATUS_STYLE.HISTORICAL;
  const Icon = style.icon;

  if (compact) {
    return (
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
          style.text,
          style.bg,
          style.border
        )}
        title={`Source: ${meta.data_source}. Last updated ${formatDateTime(meta.retrieved_at)}.`}
      >
        <Icon size={12} aria-hidden="true" />
        {DATA_STATUS_LABEL[meta.data_status] ?? meta.data_status}
      </span>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-text-muted">
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium",
          style.text,
          style.bg,
          style.border
        )}
      >
        <Icon size={12} aria-hidden="true" />
        {DATA_STATUS_LABEL[meta.data_status] ?? meta.data_status}
      </span>
      <span>
        Source: <span className="text-text-secondary">{meta.data_source}</span>
      </span>
      <span>
        Updated: <span className="text-text-secondary tabular">{formatDateTime(meta.retrieved_at)}</span>
      </span>
      {meta.latest_market_timestamp && (
        <span>
          Latest candle:{" "}
          <span className="text-text-secondary tabular">{formatDateTime(meta.latest_market_timestamp)}</span>
        </span>
      )}
      <span>
        Timeframe: <span className="text-text-secondary">{meta.timeframe}</span>
      </span>
    </div>
  );
}
