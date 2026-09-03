import { TrendingUp, TrendingDown, Waves, Activity } from "lucide-react";
import { clsx } from "clsx";
import type { MarketRegimeResponse, RelativeStrengthResponse, SectorComparisonResponse } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatPercent } from "@/lib/format";

const REGIME_STYLE: Record<string, { text: string; bg: string; border: string; icon: typeof TrendingUp }> = {
  BULL: { text: "text-bullish", bg: "bg-bullish-dim", border: "border-bullish/30", icon: TrendingUp },
  BEAR: { text: "text-bearish", bg: "bg-bearish-dim", border: "border-bearish/30", icon: TrendingDown },
  SIDEWAYS: { text: "text-neutral", bg: "bg-card-hover", border: "border-border-strong", icon: Waves },
  HIGH_VOLATILITY: { text: "text-warning", bg: "bg-warning-dim", border: "border-warning/30", icon: Activity },
  UNAVAILABLE: { text: "text-text-faint", bg: "bg-card-hover", border: "border-border", icon: Waves },
};

export function MarketRegimePanel({ regime }: { regime: MarketRegimeResponse }) {
  const style = REGIME_STYLE[regime.regime] ?? REGIME_STYLE.UNAVAILABLE;
  const Icon = style.icon;

  return (
    <Card>
      <CardHeader title="Market Context" subtitle={`Benchmark: ${regime.benchmark}`} />
      <div className="flex items-center gap-4">
        <div className={clsx("flex items-center gap-2 px-3 py-2 rounded-md border", style.bg, style.border)}>
          <Icon size={18} className={style.text} aria-hidden="true" />
          <span className={clsx("text-sm font-semibold", style.text)}>{regime.regime.replace("_", " ")}</span>
        </div>
        <div className="flex gap-6 text-xs">
          <div>
            <p className="text-text-faint uppercase text-[10px] tracking-wide">Trend</p>
            <p className="text-text-secondary">{regime.trend_classification}</p>
          </div>
          <div>
            <p className="text-text-faint uppercase text-[10px] tracking-wide">Momentum</p>
            <p className="text-text-secondary">{regime.momentum}</p>
          </div>
          <div>
            <p className="text-text-faint uppercase text-[10px] tracking-wide">Volatility</p>
            <p className="text-text-secondary">{regime.volatility_regime}</p>
          </div>
          <div>
            <p className="text-text-faint uppercase text-[10px] tracking-wide">Regime Confidence</p>
            <p className="text-text-secondary tabular">{regime.regime_confidence_percent.toFixed(0)}%</p>
          </div>
        </div>
      </div>
    </Card>
  );
}

const CLASSIFICATION_STYLE: Record<string, string> = {
  STRONG: "text-bullish",
  IN_LINE: "text-neutral",
  WEAK: "text-bearish",
  UNAVAILABLE: "text-text-faint",
};

export function RelativeStrengthPanel({ data }: { data: RelativeStrengthResponse }) {
  return (
    <Card>
      <CardHeader title="Relative Strength" subtitle={`${data.ticker} vs. ${data.benchmark}`} />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {data.periods.map((p) => (
          <div key={p.period} className="border border-border rounded p-2.5 bg-bg-elevated">
            <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{p.period}</p>
            <p className="text-text-primary font-medium tabular text-sm">{formatPercent(p.ticker_return_percent)}</p>
            <p className="text-text-faint text-[11px]">vs {formatPercent(p.benchmark_return_percent)}</p>
            <p className={clsx("text-[11px] font-medium mt-0.5", CLASSIFICATION_STYLE[p.classification])}>
              {p.classification.replace("_", " ")}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function SectorComparisonPanel({ data }: { data: SectorComparisonResponse }) {
  return (
    <Card>
      <CardHeader
        title="Sector Comparison"
        subtitle={data.sector ? `${data.sector} · ${data.period} return` : "Sector unavailable for this ticker"}
      />
      {!data.available ? (
        <p className="text-xs text-text-muted">Sector peer data is not available for this ticker.</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {data.peers.map((p) => (
            <div
              key={p.symbol}
              className={clsx(
                "flex items-center justify-between px-3 py-2 rounded text-sm",
                p.symbol === data.ticker ? "bg-accent-dim border border-accent/30" : "bg-bg-elevated"
              )}
            >
              <span className="font-mono text-text-primary">{p.symbol}</span>
              <span
                className={clsx(
                  "tabular font-medium",
                  p.return_percent === null ? "text-text-faint" : p.return_percent >= 0 ? "text-bullish" : "text-bearish"
                )}
              >
                {formatPercent(p.return_percent)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
