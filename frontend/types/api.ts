// Mirrors backend/app/models/schemas.py exactly. Keep these in sync.

export interface DataMeta {
  data_source: string;
  data_status: "LIVE" | "DELAYED" | "MARKET_CLOSED" | "HISTORICAL" | "UNAVAILABLE";
  retrieved_at: string;
  latest_market_timestamp: string | null;
  market_status: "OPEN" | "CLOSED" | "PRE_MARKET" | "AFTER_HOURS" | "WEEKEND" | null;
  timeframe: string;
}

export interface OverviewData {
  company_name: string;
  exchange: string;
  currency: string;
  sector: string;
  industry: string;
  last_price: number | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  day_high: number | null;
  day_low: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  market_cap: number | null;
  volume: number | null;
  average_volume: number | null;
  website: string;
  description: string;
}

export interface StockOverviewResponse {
  ticker: string;
  data: OverviewData;
  meta: DataMeta;
}

export interface Candle {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  sma_20?: number | null;
  sma_50?: number | null;
  sma_100?: number | null;
  sma_200?: number | null;
}

export interface HistoryResponse {
  ticker: string;
  range: string;
  is_daily: boolean;
  candles: Candle[];
  meta: DataMeta;
}

export type IndicatorStatus = "bullish" | "bearish" | "neutral" | "warning" | "unavailable";

export interface IndicatorValue {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  interpretation: string;
  status: IndicatorStatus;
}

export interface TechnicalResponse {
  ticker: string;
  latest_candle_date: string;
  trend_classification: string;
  volatility_regime: string;
  trend: IndicatorValue[];
  momentum: IndicatorValue[];
  volatility: IndicatorValue[];
  volume: IndicatorValue[];
  price_relationships: IndicatorValue[];
  meta: DataMeta;
}

export type SignalLabel = "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";

export interface ScoreFactor {
  category: string;
  name: string;
  points: number;
  detail: string;
  polarity: "positive" | "negative" | "neutral";
}

export interface Confidence {
  confidence_percent: number;
  completeness: number;
  agreement: number;
  stability_margin: number;
  volatility_clarity: number;
  methodology: string;
}

export interface Risk {
  risk_level: "LOW" | "MODERATE" | "HIGH" | "SEVERE";
  risk_score: number;
  risk_factors: string[];
  max_drawdown_percent: number | null;
  atr_percent_of_price: number | null;
}

export interface SignalResponse {
  ticker: string;
  signal: SignalLabel;
  score: number;
  confidence: Confidence;
  positive_factors: ScoreFactor[];
  negative_factors: ScoreFactor[];
  neutral_factors: ScoreFactor[];
  trend_classification: string;
  volatility_regime: string;
  risk: Risk;
  signal_timeframe: string;
  signal_generated_at: string;
  latest_candle_date: string;
  is_latest_candle_complete: boolean;
  disclaimer: string;
  meta: DataMeta;
}

export interface BacktestRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  benchmark_ticker: string | null;
  timeframe?: "Daily";
}

export interface Trade {
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  shares: number;
  pnl: number | null;
  pnl_pct: number | null;
}

export interface EquityPoint {
  date: string;
  equity: number;
}

export interface BacktestResponse {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return_percent: number | null;
  annualized_return_percent: number | null;
  buy_hold_return_percent: number | null;
  benchmark_ticker: string | null;
  benchmark_return_percent: number | null;
  max_drawdown_percent: number | null;
  sharpe_ratio: number | null;
  trading_days: number;
  open_position_at_end: boolean;
  number_of_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_percent: number | null;
  average_trade_percent: number | null;
  best_trade_percent: number | null;
  worst_trade_percent: number | null;
  profit_factor: number | null;
  trades: Trade[];
  strategy_curve: EquityPoint[];
  buy_hold_curve: EquityPoint[];
  benchmark_curve: EquityPoint[];
  drawdown_curve: EquityPoint[];
  warnings: string[];
  methodology: Record<string, string>;
  meta: DataMeta;
}

export interface SearchResultItem {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  meta: DataMeta;
}

export interface IndexQuote {
  symbol: string;
  name: string;
  last_price: number | null;
  change: number | null;
  change_percent: number | null;
  status: "OK" | "UNAVAILABLE";
}

export interface MoverQuote {
  symbol: string;
  last_price: number;
  change: number;
  change_percent: number;
}

export interface MarketOverviewResponse {
  indexes: IndexQuote[];
  gainers: MoverQuote[];
  losers: MoverQuote[];
  meta: DataMeta;
}

export interface ApiErrorBody {
  error_type: string;
  detail: string;
}
