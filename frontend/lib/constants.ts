export const POPULAR_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META"];

export const CHART_RANGES = ["1D", "5D", "1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"] as const;
export type ChartRange = (typeof CHART_RANGES)[number];

export const SIGNAL_LABELS: Record<string, string> = {
  STRONG_BUY: "Strong Buy",
  BUY: "Buy",
  HOLD: "Hold",
  SELL: "Sell",
  STRONG_SELL: "Strong Sell",
};

export const DISCLAIMER =
  "This is a research and educational analysis tool, not a financial adviser. It does not guarantee returns. BUY/HOLD/SELL is the output of a deterministic quantitative model, not personalized financial advice.";
