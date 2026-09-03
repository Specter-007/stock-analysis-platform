import { clsx } from "clsx";
import type { Trade } from "@/types/api";
import { formatDate, formatPercent, formatPrice } from "@/lib/format";

export function TradesTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return <p className="text-xs text-text-muted">No trades were executed in this period.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs min-w-[560px]">
        <thead>
          <tr className="text-left text-text-faint uppercase tracking-wide">
            <th className="pb-2 font-medium">Entry</th>
            <th className="pb-2 font-medium text-right">Entry Price</th>
            <th className="pb-2 font-medium">Exit</th>
            <th className="pb-2 font-medium text-right">Exit Price</th>
            <th className="pb-2 font-medium text-right">P&amp;L</th>
            <th className="pb-2 font-medium text-right">P&amp;L %</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {trades.map((t, i) => (
            <tr key={i}>
              <td className="py-2 tabular text-text-secondary">{formatDate(t.entry_date)}</td>
              <td className="py-2 tabular text-right text-text-secondary">{formatPrice(t.entry_price)}</td>
              <td className="py-2 tabular text-text-secondary">
                {t.exit_date ? formatDate(t.exit_date) : <span className="text-text-faint italic">Open</span>}
              </td>
              <td className="py-2 tabular text-right text-text-secondary">
                {t.exit_price !== null ? formatPrice(t.exit_price) : "—"}
              </td>
              <td
                className={clsx(
                  "py-2 tabular text-right font-medium",
                  t.pnl === null ? "text-text-faint" : t.pnl >= 0 ? "text-bullish" : "text-bearish"
                )}
              >
                {t.pnl === null ? "N/A" : formatPrice(t.pnl)}
              </td>
              <td
                className={clsx(
                  "py-2 tabular text-right font-medium",
                  t.pnl_pct === null ? "text-text-faint" : t.pnl_pct >= 0 ? "text-bullish" : "text-bearish"
                )}
              >
                {t.pnl_pct === null ? "N/A" : formatPercent(t.pnl_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
