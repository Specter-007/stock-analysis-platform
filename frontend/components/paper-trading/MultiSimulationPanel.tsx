"use client";

import { clsx } from "clsx";
import { getPaperPortfolios } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatCurrency, formatPercent } from "@/lib/format";

export function MultiSimulationPanel({
  activePortfolioId,
  onSelect,
  refreshKey,
}: {
  activePortfolioId: string;
  onSelect: (id: string) => void;
  refreshKey: number;
}) {
  const { data } = useApiResource((signal) => getPaperPortfolios(signal), [refreshKey]);

  if (!data || data.portfolios.length <= 1) return null;

  return (
    <Card>
      <CardHeader title="Forward Simulations" subtitle="Every paper-trading portfolio that exists - switch between them or compare side by side." />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.portfolios.map((p) => (
          <button
            key={p.portfolio_id}
            onClick={() => onSelect(p.portfolio_id)}
            className={clsx(
              "text-left border rounded-lg p-3 transition-colors cursor-pointer",
              p.portfolio_id === activePortfolioId
                ? "border-accent bg-accent/10"
                : "border-border bg-bg-elevated hover:border-border-strong"
            )}
          >
            <p className="text-sm font-medium text-text-primary font-mono mb-1 truncate">{p.portfolio_id}</p>
            <p className="text-xs text-text-muted mb-1">
              {formatCurrency(p.starting_capital)} → {formatCurrency(p.current_value)}
            </p>
            <p className={clsx("text-sm font-semibold tabular", p.total_return_percent >= 0 ? "text-bullish" : "text-bearish")}>
              {formatPercent(p.total_return_percent)}
            </p>
            <p className="text-[10px] text-text-faint mt-1">
              {p.number_of_positions} position(s) · {p.number_of_trades} trade(s)
            </p>
          </button>
        ))}
      </div>
    </Card>
  );
}
