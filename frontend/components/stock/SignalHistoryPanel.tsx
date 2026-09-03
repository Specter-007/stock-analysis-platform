"use client";

import { Line, LineChart, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import type { SignalHistoryPoint } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatDate } from "@/lib/format";

export function SignalHistoryPanel({ history }: { history: SignalHistoryPoint[] }) {
  if (history.length === 0) {
    return (
      <Card>
        <CardHeader title="Signal History" />
        <p className="text-xs text-text-muted">Not enough historical data to compute a signal history yet.</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Signal History" subtitle={`Model score over the last ${history.length} sessions`} />
      <div className="h-[180px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="date"
              tickFormatter={(v) => formatDate(v)}
              stroke="#545e6e"
              tick={{ fontSize: 10, fill: "#7c8798" }}
              minTickGap={40}
              axisLine={{ stroke: "#1f2937" }}
              tickLine={false}
            />
            <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#7c8798" }} axisLine={false} tickLine={false} width={28} />
            <ReferenceLine y={65} stroke="#26a69a" strokeDasharray="2 3" strokeOpacity={0.4} />
            <ReferenceLine y={45} stroke="#8b96a5" strokeDasharray="2 3" strokeOpacity={0.4} />
            <ReferenceLine y={30} stroke="#ef5350" strokeDasharray="2 3" strokeOpacity={0.4} />
            <Tooltip
              labelFormatter={(l) => formatDate(l as string)}
              formatter={(value, name, item) => [`${value} (${item.payload.signal})`, "Score"]}
              contentStyle={{ background: "#0a0d15", border: "1px solid #2a3441", borderRadius: 6, fontSize: 12 }}
            />
            <Line type="stepAfter" dataKey="score" stroke="#4c8eff" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11px] text-text-faint mt-2">
        Each point is computed causally from data available through that date only - identical to what the live
        signal would have shown that day.
      </p>
    </Card>
  );
}
