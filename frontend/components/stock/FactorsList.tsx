import { Plus, Minus, Equal } from "lucide-react";
import { clsx } from "clsx";
import type { ScoreFactor, Confidence } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";

export function FactorsList({
  positive,
  negative,
  neutral,
  confidence,
}: {
  positive: ScoreFactor[];
  negative: ScoreFactor[];
  neutral: ScoreFactor[];
  confidence: Confidence;
}) {
  return (
    <Card>
      <CardHeader title="Why this signal?" subtitle="Every factor below is computed from this stock's actual current indicator values." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <FactorGroup title="Positive factors" icon={Plus} tone="bullish" factors={positive} />
        <FactorGroup title="Negative factors" icon={Minus} tone="bearish" factors={negative} />
        <FactorGroup title="Neutral factors" icon={Equal} tone="neutral" factors={neutral} />
      </div>

      <div className="mt-5 pt-4 border-t border-border">
        <p className="text-xs text-text-secondary mb-2">
          Confidence breakdown:{" "}
          <span className="text-text-primary font-medium">{confidence.confidence_percent.toFixed(0)}%</span>
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
          <ConfidenceBar label="Data completeness" value={confidence.completeness} />
          <ConfidenceBar label="Factor agreement" value={confidence.agreement} />
          <ConfidenceBar label="Score stability" value={confidence.stability_margin} />
          <ConfidenceBar label="Volatility clarity" value={confidence.volatility_clarity} />
        </div>
        <p className="text-[11px] text-text-faint mt-3 leading-relaxed">{confidence.methodology}</p>
      </div>
    </Card>
  );
}

const TONE_CLASSES: Record<string, string> = {
  bullish: "text-bullish bg-bullish-dim border-bullish/25",
  bearish: "text-bearish bg-bearish-dim border-bearish/25",
  neutral: "text-neutral bg-card-hover border-border-strong",
};

function FactorGroup({
  title,
  icon: Icon,
  tone,
  factors,
}: {
  title: string;
  icon: typeof Plus;
  tone: "bullish" | "bearish" | "neutral";
  factors: ScoreFactor[];
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2.5">{title}</h3>
      {factors.length === 0 ? (
        <p className="text-xs text-text-faint italic">None identified.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {factors.map((f) => (
            <li
              key={f.name}
              className={clsx("flex items-start gap-2 rounded-md border px-2.5 py-2 text-xs", TONE_CLASSES[tone])}
            >
              <Icon size={13} className="mt-0.5 shrink-0" aria-hidden="true" />
              <span className="leading-snug">
                <span className="font-medium">{f.name}:</span> {f.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ConfidenceBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between text-text-muted mb-1">
        <span>{label}</span>
        <span className="tabular">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-card-hover overflow-hidden">
        <div className="h-full bg-accent rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
