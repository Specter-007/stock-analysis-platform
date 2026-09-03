import { TrendingUp, TrendingDown, Minus, Clock, CalendarClock } from "lucide-react";
import { clsx } from "clsx";
import type { SignalResponse } from "@/types/api";
import { SIGNAL_LABELS } from "@/lib/constants";
import { formatDate, formatDateTime } from "@/lib/format";
import { Card } from "@/components/ui/Card";

const SIGNAL_STYLE: Record<string, { text: string; bg: string; border: string; icon: typeof TrendingUp }> = {
  STRONG_BUY: { text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/40", icon: TrendingUp },
  BUY: { text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/30", icon: TrendingUp },
  HOLD: { text: "text-neutral", bg: "bg-card-hover", border: "border-border-strong", icon: Minus },
  SELL: { text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/30", icon: TrendingDown },
  STRONG_SELL: { text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/40", icon: TrendingDown },
};

export function SignalCard({ signal }: { signal: SignalResponse }) {
  const style = SIGNAL_STYLE[signal.signal] ?? SIGNAL_STYLE.HOLD;
  const Icon = style.icon;

  return (
    <Card className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-5 sm:gap-8">
        <div
          className={clsx(
            "flex items-center gap-3 px-5 py-4 rounded-md border shrink-0",
            style.bg,
            style.border
          )}
        >
          <Icon size={28} className={style.text} aria-hidden="true" />
          <div>
            <p className={clsx("text-xl font-semibold leading-none", style.text)}>
              {SIGNAL_LABELS[signal.signal] ?? signal.signal}
            </p>
            <p className="text-xs text-text-muted mt-1">Model classification</p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:flex sm:items-center gap-x-8 gap-y-4 flex-1">
          <Metric label="Score" value={`${signal.score.toFixed(0)} / 100`} />
          <Metric label="Model Confidence" value={`${signal.confidence.confidence_percent.toFixed(0)}%`} />
          <Metric label="Trend" value={signal.trend_classification} />
          <Metric label="Volatility Regime" value={signal.volatility_regime} />
        </div>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-text-muted border-t border-border pt-4">
        <span className="flex items-center gap-1.5">
          <Clock size={13} aria-hidden="true" /> Signal timeframe:{" "}
          <span className="text-text-secondary">{signal.signal_timeframe}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <CalendarClock size={13} aria-hidden="true" /> Latest candle:{" "}
          <span className="text-text-secondary tabular">
            {formatDate(signal.latest_candle_date)}
            {!signal.is_latest_candle_complete && " (forming, market open)"}
          </span>
        </span>
        <span>
          Generated: <span className="text-text-secondary tabular">{formatDateTime(signal.signal_generated_at)}</span>
        </span>
      </div>

      <p className="text-[11px] text-text-faint leading-relaxed border-t border-border pt-3">
        {signal.disclaimer}
      </p>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-text-faint mb-0.5">{label}</p>
      <p className="text-sm font-medium text-text-primary tabular">{value}</p>
    </div>
  );
}
