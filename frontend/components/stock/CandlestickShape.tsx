import type { Candle } from "@/types/api";

interface ShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Candle;
}

const BULLISH = "#26a69a";
const BEARISH = "#ef5350";

/**
 * Custom Recharts <Bar> shape rendering a real OHLC candlestick.
 *
 * The bar itself is drawn with dataKey=[low, high] so Recharts already gives
 * us `y` (pixel for `high`) and `height` (pixel span for high-low). We
 * derive the open/close body position from that same linear pixel-per-unit
 * scale, so the body is always correctly proportioned relative to the wick.
 */
export function CandlestickShape(props: ShapeProps) {
  const { x, y, width, height, payload } = props;
  if (x === undefined || y === undefined || width === undefined || height === undefined || !payload) return null;

  const { open, close, high, low } = payload;
  if (open === null || close === null || high === null || low === null) return null;

  const isBullish = close >= open;
  const color = isBullish ? BULLISH : BEARISH;

  const range = high - low;
  const pxPerUnit = range > 0 ? height / range : 0;

  const bodyTopPrice = Math.max(open, close);
  const bodyBottomPrice = Math.min(open, close);
  const bodyTop = y + (high - bodyTopPrice) * pxPerUnit;
  const bodyBottomY = y + (high - bodyBottomPrice) * pxPerUnit;
  const bodyHeight = Math.max(1, bodyBottomY - bodyTop);

  const centerX = x + width / 2;
  const bodyWidth = Math.max(2, width * 0.6);
  const bodyX = centerX - bodyWidth / 2;

  return (
    <g>
      <line x1={centerX} x2={centerX} y1={y} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={bodyX} y={bodyTop} width={bodyWidth} height={bodyHeight} fill={color} />
    </g>
  );
}
