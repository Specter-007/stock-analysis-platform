import type { FundamentalMetric, FundamentalsResponse } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";

const SECTIONS: { key: keyof FundamentalsResponse; title: string }[] = [
  { key: "valuation", title: "Valuation" },
  { key: "growth", title: "Growth" },
  { key: "profitability", title: "Profitability" },
  { key: "balance_sheet", title: "Balance Sheet" },
];

function formatMetric(m: FundamentalMetric): string {
  if (m.value === null) return "N/A";
  const formatted = m.unit === "$" ? m.value.toLocaleString("en-US", { notation: "compact" }) : m.value.toFixed(2);
  if (m.unit === "$") return `$${formatted}`;
  if (m.unit === "x") return `${formatted}x`;
  if (m.unit === "%") return `${formatted}%`;
  return formatted;
}

export function FundamentalsPanel({ fundamentals }: { fundamentals: FundamentalsResponse }) {
  if (!fundamentals.has_any_data) {
    return (
      <Card>
        <CardHeader title="Fundamental Analysis" />
        <p className="text-xs text-text-muted">
          Yahoo Finance did not report fundamental data for this ticker (common for ETFs, indexes, and some
          international listings).
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Fundamental Analysis" subtitle="Latest figures reported by Yahoo Finance" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-5">
        {SECTIONS.map(({ key, title }) => {
          const metrics = fundamentals[key] as FundamentalMetric[];
          return (
            <div key={key}>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">{title}</h3>
              <ul className="flex flex-col gap-1.5">
                {metrics.map((m) => (
                  <li key={m.key} className="flex items-center justify-between text-xs">
                    <span className="text-text-muted">{m.label}</span>
                    <span className="text-text-primary font-mono tabular">{formatMetric(m)}</span>
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
