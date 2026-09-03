import { AlertOctagon } from "lucide-react";
import { clsx } from "clsx";
import type { SignalLabel, SignalStability } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";

const DOT_COLOR: Record<SignalLabel, string> = {
  STRONG_BUY: "bg-bullish",
  BUY: "bg-bullish/70",
  HOLD: "bg-neutral",
  SELL: "bg-bearish/70",
  STRONG_SELL: "bg-bearish",
};

export function StabilityPanel({ stability }: { stability: SignalStability }) {
  return (
    <Card>
      <CardHeader title="Signal Stability" subtitle="Consistency of the model's own output over recent sessions" />
      <div className="flex items-center gap-4 mb-3">
        <span className="text-2xl font-semibold text-text-primary tabular">{stability.stability_percent.toFixed(0)}%</span>
        <div className="flex gap-1" aria-label="Recent signal history, most recent first">
          {stability.recent_signals.map((s, i) => (
            <span
              key={i}
              title={s}
              className={clsx("w-4 h-4 rounded-sm", DOT_COLOR[s] ?? "bg-neutral")}
            />
          ))}
        </div>
      </div>
      <p className="text-[11px] text-text-faint leading-relaxed">{stability.methodology}</p>
    </Card>
  );
}

export function InvalidationPanel({ conditions }: { conditions: string[] }) {
  return (
    <Card>
      <CardHeader title="What could invalidate this signal?" subtitle="Derived from the factors currently supporting the signal's direction" />
      <ul className="flex flex-col gap-2">
        {conditions.map((c, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
            <AlertOctagon size={13} className="mt-0.5 text-warning shrink-0" aria-hidden="true" />
            {c}
          </li>
        ))}
      </ul>
    </Card>
  );
}
