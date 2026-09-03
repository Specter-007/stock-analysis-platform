import { AlertTriangle, ShieldAlert, ShieldCheck, Shield } from "lucide-react";
import { clsx } from "clsx";
import type { Risk } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";

const RISK_STYLE: Record<string, { text: string; bg: string; border: string; icon: typeof Shield }> = {
  LOW: { text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/30", icon: ShieldCheck },
  MODERATE: { text: "text-warning", bg: "bg-warning-dim", border: "border-warning/30", icon: Shield },
  HIGH: { text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/30", icon: ShieldAlert },
  SEVERE: { text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/40", icon: AlertTriangle },
};

export function RiskPanel({ risk }: { risk: Risk }) {
  const style = RISK_STYLE[risk.risk_level] ?? RISK_STYLE.MODERATE;
  const Icon = style.icon;

  return (
    <Card>
      <CardHeader title="Risk Analysis" subtitle="Model-based, present-tense context — not a prediction of future risk." />

      <div className="flex flex-col sm:flex-row gap-5">
        <div className={clsx("flex items-center gap-3 px-4 py-3 rounded-md border shrink-0 self-start", style.bg, style.border)}>
          <Icon size={22} className={style.text} aria-hidden="true" />
          <div>
            <p className={clsx("text-sm font-semibold", style.text)}>{risk.risk_level}</p>
            <p className="text-[11px] text-text-muted">Risk level</p>
          </div>
        </div>

        <div className="flex-1">
          <ul className="flex flex-col gap-1.5">
            {risk.risk_factors.map((factor, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="w-1 h-1 rounded-full bg-text-faint mt-1.5 shrink-0" aria-hidden="true" />
                {factor}
              </li>
            ))}
          </ul>

          <div className="flex gap-6 mt-4 pt-3 border-t border-border text-xs">
            <div>
              <p className="text-text-faint uppercase text-[10px] tracking-wide mb-0.5">Max Drawdown</p>
              <p className="text-text-primary font-medium tabular">{formatPercent(risk.max_drawdown_percent)}</p>
            </div>
            <div>
              <p className="text-text-faint uppercase text-[10px] tracking-wide mb-0.5">ATR % of Price</p>
              <p className="text-text-primary font-medium tabular">
                {risk.atr_percent_of_price === null ? "N/A" : `${risk.atr_percent_of_price.toFixed(1)}%`}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
