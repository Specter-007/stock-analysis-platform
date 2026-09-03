"use client";

import { Area, AreaChart, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import type { EquityPoint } from "@/types/api";
import { formatDate } from "@/lib/format";

export function DrawdownChart({ drawdown }: { drawdown: EquityPoint[] }) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={drawdown} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef5350" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#ef5350" stopOpacity={0.02} />
            </linearGradient>
          </defs>
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
            tickFormatter={(v) => `${v.toFixed(0)}%`}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip
            formatter={(value) => [`${Number(value).toFixed(2)}%`, "Drawdown"]}
            labelFormatter={(l) => formatDate(l as string)}
            contentStyle={{ background: "#0a0d15", border: "1px solid #2a3441", borderRadius: 6, fontSize: 12 }}
          />
          <Area type="monotone" dataKey="equity" stroke="#ef5350" fill="url(#ddFill)" strokeWidth={1.25} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
