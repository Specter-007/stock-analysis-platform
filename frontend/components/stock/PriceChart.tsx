"use client";

import { Fragment, useMemo, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { clsx } from "clsx";
import type { Candle } from "@/types/api";
import { CandlestickShape } from "./CandlestickShape";
import { CHART_RANGES, type ChartRange } from "@/lib/constants";
import { formatDate, formatPrice, formatCompactNumber } from "@/lib/format";

const SMA_COLORS: Record<string, string> = {
  sma_20: "#f5a623",
  sma_50: "#4c8eff",
  sma_100: "#b98bff",
  sma_200: "#e7ecf3",
};

const SMA_KEYS = ["sma_20", "sma_50", "sma_100", "sma_200"] as const;
const DENSE_THRESHOLD = 180;

export function PriceChart({
  candles,
  isDaily,
  range,
  onRangeChange,
  loading,
}: {
  candles: Candle[];
  isDaily: boolean;
  range: ChartRange;
  onRangeChange: (r: ChartRange) => void;
  loading: boolean;
}) {
  const [visibleSma, setVisibleSma] = useState<Record<string, boolean>>({
    sma_20: false,
    sma_50: true,
    sma_100: false,
    sma_200: true,
  });
  const [chartType, setChartType] = useState<"auto" | "candlestick" | "line">("auto");

  const data = useMemo(
    () =>
      candles.map((c) => ({
        ...c,
        ohlcRange: c.low !== null && c.high !== null ? [c.low, c.high] : null,
      })),
    [candles]
  );

  const maxVolume = useMemo(() => Math.max(1, ...candles.map((c) => c.volume ?? 0)), [candles]);
  const effectiveType = chartType === "auto" ? (candles.length > DENSE_THRESHOLD ? "line" : "candlestick") : chartType;
  const hasSmaData = isDaily && candles.some((c) => c.sma_20 !== null || c.sma_50 !== null);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1" role="group" aria-label="Chart time range">
          {CHART_RANGES.map((r) => (
            <button
              key={r}
              onClick={() => onRangeChange(r)}
              className={clsx(
                "px-2.5 py-1 text-xs font-medium rounded transition-colors cursor-pointer",
                r === range
                  ? "bg-accent-dim text-accent border border-accent/40"
                  : "text-text-muted hover:text-text-primary hover:bg-card-hover border border-transparent"
              )}
              aria-pressed={r === range}
            >
              {r}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          {hasSmaData && (
            <div className="flex flex-wrap gap-2" role="group" aria-label="Moving average overlays">
              {SMA_KEYS.map((key) => (
                <button
                  key={key}
                  onClick={() => setVisibleSma((v) => ({ ...v, [key]: !v[key] }))}
                  className={clsx(
                    "flex items-center gap-1.5 text-[11px] px-2 py-1 rounded border cursor-pointer transition-colors",
                    visibleSma[key]
                      ? "border-border-strong text-text-primary bg-card-hover"
                      : "border-border text-text-faint"
                  )}
                  aria-pressed={visibleSma[key]}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block"
                    style={{ background: visibleSma[key] ? SMA_COLORS[key] : "transparent", border: `1.5px solid ${SMA_COLORS[key]}` }}
                    aria-hidden="true"
                  />
                  SMA {key.split("_")[1]}
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-1 border border-border rounded p-0.5">
            {(["candlestick", "line"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setChartType(t)}
                className={clsx(
                  "px-2 py-0.5 text-[11px] rounded capitalize cursor-pointer",
                  effectiveType === t ? "bg-card-hover text-text-primary" : "text-text-faint hover:text-text-muted"
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="h-[420px] w-full" aria-label={`Price chart for the selected ${range} range`}>
        {loading ? (
          <div className="h-full w-full animate-pulse bg-card-hover rounded" />
        ) : data.length === 0 ? (
          <div className="h-full w-full flex items-center justify-center text-sm text-text-muted">
            No chart data available for this range.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v) => formatDate(v)}
                stroke="#545e6e"
                tick={{ fontSize: 11, fill: "#7c8798" }}
                minTickGap={40}
                axisLine={{ stroke: "#1f2937" }}
                tickLine={false}
              />
              <YAxis
                yAxisId="price"
                domain={["auto", "auto"]}
                tick={{ fontSize: 11, fill: "#7c8798" }}
                tickFormatter={(v) => formatPrice(v)}
                axisLine={false}
                tickLine={false}
                width={64}
              />
              <YAxis yAxisId="volume" domain={[0, maxVolume * 4]} hide />
              <Tooltip content={<ChartTooltip />} />

              <Bar yAxisId="volume" dataKey="volume" fill="#1f2937" isAnimationActive={false} />

              {effectiveType === "candlestick" ? (
                <Bar yAxisId="price" dataKey="ohlcRange" shape={CandlestickShape} isAnimationActive={false} />
              ) : (
                <Line
                  yAxisId="price"
                  dataKey="close"
                  stroke="#e7ecf3"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                  connectNulls={false}
                />
              )}

              {hasSmaData &&
                SMA_KEYS.filter((k) => visibleSma[k]).map((key) => (
                  <Line
                    key={key}
                    yAxisId="price"
                    dataKey={key}
                    stroke={SMA_COLORS[key]}
                    strokeWidth={1.25}
                    dot={false}
                    isAnimationActive={false}
                    connectNulls={false}
                  />
                ))}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
      <p className="text-[11px] text-text-faint">
        Volume shown as background bars, scaled independently from price. SMA lines only render where
        enough trailing history exists — gaps mean insufficient data, not zero.
      </p>
    </div>
  );
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: { payload?: Candle }[];
  label?: string | number;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const candle = payload[0]?.payload;
  if (!candle) return null;

  return (
    <div className="bg-bg-elevated border border-border-strong rounded-md p-3 text-xs shadow-xl min-w-[180px]">
      <p className="text-text-primary font-medium mb-1.5">{formatDate(label as string)}</p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 tabular text-text-secondary">
        <span>Open</span>
        <span className="text-right">{formatPrice(candle.open)}</span>
        <span>High</span>
        <span className="text-right">{formatPrice(candle.high)}</span>
        <span>Low</span>
        <span className="text-right">{formatPrice(candle.low)}</span>
        <span>Close</span>
        <span className="text-right text-text-primary font-medium">{formatPrice(candle.close)}</span>
        <span>Volume</span>
        <span className="text-right">{formatCompactNumber(candle.volume)}</span>
        {SMA_KEYS.map(
          (key) =>
            candle[key] != null && (
              <Fragment key={key}>
                <span style={{ color: SMA_COLORS[key] }}>SMA {key.split("_")[1]}</span>
                <span className="text-right">{formatPrice(candle[key] as number)}</span>
              </Fragment>
            )
        )}
      </div>
    </div>
  );
}
