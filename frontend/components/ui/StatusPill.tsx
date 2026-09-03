import { clsx } from "clsx";
import { TrendingUp, TrendingDown, Minus, AlertTriangle, HelpCircle } from "lucide-react";
import type { IndicatorStatus } from "@/types/api";

const STATUS_CONFIG: Record<
  IndicatorStatus,
  { icon: typeof TrendingUp; text: string; bg: string; border: string }
> = {
  bullish: { icon: TrendingUp, text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/30" },
  bearish: { icon: TrendingDown, text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/30" },
  neutral: { icon: Minus, text: "text-neutral", bg: "bg-card-hover", border: "border-border-strong" },
  warning: { icon: AlertTriangle, text: "text-warning", bg: "bg-warning-dim", border: "border-warning/30" },
  unavailable: { icon: HelpCircle, text: "text-text-faint", bg: "bg-card-hover", border: "border-border" },
};

export function StatusPill({ status, label }: { status: IndicatorStatus; label: string }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        cfg.text,
        cfg.bg,
        cfg.border
      )}
    >
      <Icon size={12} aria-hidden="true" />
      {label}
    </span>
  );
}

const SIGNAL_STATUS: Record<string, IndicatorStatus> = {
  STRONG_BUY: "bullish",
  BUY: "bullish",
  HOLD: "neutral",
  SELL: "bearish",
  STRONG_SELL: "bearish",
};

export function signalToStatus(signal: string): IndicatorStatus {
  return SIGNAL_STATUS[signal] ?? "neutral";
}
