import { clsx } from "clsx";
import { Card, CardHeader } from "@/components/ui/Card";

const CATEGORY_ORDER = ["Trend", "Momentum", "Volume", "Volatility", "Other"];
const CATEGORY_MAX = 40; // used only to scale the bar width visually

export function ScoreBreakdown({ breakdown, score }: { breakdown: Record<string, number>; score: number }) {
  const entries = CATEGORY_ORDER.filter((c) => c in breakdown).map((c) => [c, breakdown[c]] as const);

  return (
    <Card>
      <CardHeader title="Score Breakdown" subtitle={`Category contributions summing to the raw score behind ${score.toFixed(0)}/100`} />
      <div className="flex flex-col gap-3">
        {entries.map(([category, points]) => {
          const isPositive = points >= 0;
          const widthPct = Math.min(100, (Math.abs(points) / CATEGORY_MAX) * 100);
          return (
            <div key={category} className="flex items-center gap-3">
              <span className="w-24 text-xs text-text-secondary shrink-0">{category}</span>
              <div className="flex-1 h-5 bg-card-hover rounded-sm relative overflow-hidden">
                <div className="absolute inset-y-0 left-1/2 w-px bg-border-strong" aria-hidden="true" />
                <div
                  className={clsx(
                    "absolute inset-y-0 rounded-sm",
                    isPositive ? "bg-bullish/70 left-1/2" : "bg-bearish/70 right-1/2"
                  )}
                  style={{ width: `${widthPct / 2}%` }}
                />
              </div>
              <span
                className={clsx(
                  "w-14 text-right text-xs font-mono tabular font-medium",
                  isPositive ? "text-bullish" : "text-bearish"
                )}
              >
                {isPositive ? "+" : ""}
                {points.toFixed(0)}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
