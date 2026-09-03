"use client";

import { useMemo } from "react";
import { Line, LineChart, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import type { EquityPoint } from "@/types/api";
import { formatCurrency, formatDate } from "@/lib/format";

export function EquityChart({
  strategy,
  buyHold,
  benchmark,
  benchmarkTicker,
}: {
  strategy: EquityPoint[];
  buyHold: EquityPoint[];
  benchmark: EquityPoint[];
  benchmarkTicker: string | null;
}) {
  const merged = useMemo(() => {
    const map = new Map<string, { date: string; strategy?: number; buyHold?: number; benchmark?: number }>();
    for (const p of strategy) map.set(p.date, { date: p.date, strategy: p.equity });
    for (const p of buyHold) {
      const existing = map.get(p.date) ?? { date: p.date };
      existing.buyHold = p.equity;
      map.set(p.date, existing);
    }
    for (const p of benchmark) {
      const existing = map.get(p.date) ?? { date: p.date };
      existing.benchmark = p.equity;
      map.set(p.date, existing);
    }
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [strategy, buyHold, benchmark]);

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={merged} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(v) => formatDate(v)}
            stroke="#545e6e"
            tick={{ fontSize: 11, fill: "#7c8798" }}
            minTickGap={50}
            axisLine={{ stroke: "#1f2937" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#7c8798" }}
            tickFormatter={(v) => formatCurrency(v)}
            axisLine={false}
            tickLine={false}
            width={80}
          />
          <Tooltip
            formatter={(value, name) => [formatCurrency(Number(value)), String(name)]}
            labelFormatter={(l) => formatDate(l as string)}
            contentStyle={{
              background: "#0a0d15",
              border: "1px solid #2a3441",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="strategy" name="Strategy" stroke="#4c8eff" dot={false} strokeWidth={1.75} isAnimationActive={false} />
          <Line type="monotone" dataKey="buyHold" name="Buy & Hold" stroke="#e7ecf3" dot={false} strokeWidth={1.5} strokeDasharray="4 3" isAnimationActive={false} />
          {benchmark.length > 0 && (
            <Line
              type="monotone"
              dataKey="benchmark"
              name={benchmarkTicker ?? "Benchmark"}
              stroke="#f5a623"
              dot={false}
              strokeWidth={1.5}
              strokeDasharray="2 3"
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
