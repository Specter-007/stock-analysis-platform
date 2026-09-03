import type { IndicatorValue, TechnicalResponse } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import { formatNumber } from "@/lib/format";

const SECTIONS: { key: keyof TechnicalResponse; title: string }[] = [
  { key: "trend", title: "Trend" },
  { key: "momentum", title: "Momentum" },
  { key: "volatility", title: "Volatility" },
  { key: "volume", title: "Volume" },
  { key: "price_relationships", title: "Price Relationships" },
];

export function IndicatorPanel({ technical }: { technical: TechnicalResponse }) {
  return (
    <Card>
      <CardHeader
        title="Technical Indicators"
        subtitle={`Latest completed daily candle: ${technical.latest_candle_date}`}
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-6">
        {SECTIONS.map(({ key, title }) => {
          const values = technical[key] as IndicatorValue[];
          return (
            <div key={key}>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2.5">
                {title}
              </h3>
              <ul className="flex flex-col divide-y divide-border">
                {values.map((iv) => (
                  <li key={iv.key} className="flex items-center justify-between gap-3 py-2">
                    <div className="min-w-0">
                      <p className="text-sm text-text-primary font-medium">{iv.label}</p>
                      <p className="text-[11px] text-text-muted truncate">{iv.interpretation}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-sm font-mono tabular text-text-secondary">
                        {formatIndicatorValue(iv)}
                      </span>
                      <StatusPill status={iv.status} label={statusLabel(iv.status)} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function formatIndicatorValue(iv: IndicatorValue): string {
  if (iv.value === null) return "N/A";
  const digits = iv.unit === "shares" ? 0 : iv.value < 10 ? 2 : iv.unit === "$" ? 2 : 1;
  const formatted = formatNumber(iv.value, digits);
  if (iv.unit === "$") return `$${formatted}`;
  if (iv.unit === "shares" || iv.unit === "") return formatted;
  return `${formatted}${iv.unit}`;
}

function statusLabel(status: IndicatorValue["status"]): string {
  switch (status) {
    case "bullish":
      return "Bullish";
    case "bearish":
      return "Bearish";
    case "warning":
      return "Caution";
    case "unavailable":
      return "N/A";
    default:
      return "Neutral";
  }
}
