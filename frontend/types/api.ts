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
  current_value: number | null;
  threshold_label: string;
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

export interface SignalChange {
  date: string;
  previous_signal: SignalLabel;
  current_signal: SignalLabel;
  previous_score: number;
  current_score: number;
  contributing_changes: string[];
}

export interface SignalStability {
  stability_percent: number;
  window_sessions: number;
  recent_signals: SignalLabel[];
  methodology: string;
}

export interface FundamentalScoreFactor {
  key: string;
  label: string;
  value: number | null;
  healthy: boolean | null;
  points: number;
  max_points: number;
}

export interface OverallScore {
  technical_score: number;
  fundamental_score: number | null;
  overall_score: number | null;
  technical_weight: number;
  fundamental_weight: number;
  fundamental_factors: FundamentalScoreFactor[];
  methodology: string;
}

export interface SignalResponse {
  ticker: string;
  model_version: string;
  signal: SignalLabel;
  score: number;
  score_breakdown: Record<string, number>;
  confidence: Confidence;
  positive_factors: ScoreFactor[];
  negative_factors: ScoreFactor[];
  neutral_factors: ScoreFactor[];
  trend_classification: string;
  volatility_regime: string;
  risk: Risk;
  signal_change: SignalChange | null;
  stability: SignalStability;
  invalidation_conditions: string[];
  overall_score: OverallScore | null;
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
  model_version: string;
  advanced_metrics: {
    cagr_percent: number | null;
    annualized_volatility_percent: number | null;
    sortino_ratio: number | null;
    calmar_ratio: number | null;
    average_drawdown_percent: number | null;
    downside_deviation_percent: number | null;
    max_drawdown_recovery_days: number | null;
    expectancy: number | null;
    exposure_percent: number | null;
    turnover_percent: number | null;
    beta: number | null;
    alpha_percent: number | null;
    tracking_error_percent: number | null;
    information_ratio: number | null;
    average_win: number | null;
    average_loss: number | null;
    average_win_percent: number | null;
    average_loss_percent: number | null;
    median_trade_percent: number | null;
  };
  meta: DataMeta;
}

export interface WalkForwardFold {
  fold_index: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  test_total_return_percent: number | null;
  test_buy_hold_return_percent: number | null;
  test_max_drawdown_percent: number | null;
  test_sharpe_ratio: number | null;
  test_number_of_trades: number;
  test_win_rate_percent: number | null;
}

export interface WalkForwardResponse {
  ticker: string;
  train_years: number;
  test_years: number;
  folds: WalkForwardFold[];
  folds_with_positive_return: number;
  average_test_return_percent: number | null;
  methodology: string;
  meta: DataMeta;
}

export interface WalkForwardRequestPayload {
  ticker: string;
  train_years: number;
  test_years: number;
  max_folds: number;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
}

export interface SensitivityPoint {
  parameter: string;
  value: number;
  is_default: boolean;
  total_return_percent: number | null;
  cagr_percent: number | null;
  sharpe_ratio: number | null;
  max_drawdown_percent: number | null;
  number_of_trades: number;
}

export type SensitivityRobustness =
  | "HIGHER_ROBUSTNESS"
  | "LOW_ROBUSTNESS"
  | "INSUFFICIENT_DATA"
  | "PARAMETER_INERT"
  | "INSUFFICIENT_SAMPLE";

export interface SensitivityResult {
  parameter: string;
  label: string;
  default_value: number;
  points: SensitivityPoint[];
  robustness: SensitivityRobustness;
  robust_region_min: number | null;
  robust_region_max: number | null;
  best_value: number | null;
  median_value: number | null;
  worst_value: number | null;
  note: string | null;
}

export interface SensitivityResponse {
  ticker: string;
  model_version: string;
  parameters: SensitivityResult[];
  methodology: string;
  meta: DataMeta;
}

export interface SensitivityRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  parameters?: string[];
}

export interface SensitivityHeatmapCell {
  x_value: number;
  y_value: number;
  metric_value: number | null;
  number_of_trades: number;
  insufficient_sample: boolean;
}

export interface SensitivityHeatmapResponse {
  ticker: string;
  param_x: string;
  param_y: string;
  metric: string;
  cells: SensitivityHeatmapCell[];
  methodology: string;
  meta: DataMeta;
}

export interface SensitivityHeatmapRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  param_x: string;
  param_y: string;
  metric: string;
}

export interface MonteCarloResponse {
  ticker: string;
  simulations: number;
  resampling_basis: "trade_returns" | "daily_returns" | "unavailable";
  sample_size: number;
  median_return_percent: number | null;
  percentile_5_return_percent: number | null;
  percentile_95_return_percent: number | null;
  median_max_drawdown_percent: number | null;
  worst_max_drawdown_percent: number | null;
  methodology: string;
  meta: DataMeta;
}

export interface MonteCarloRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  simulations: number;
  seed?: number | null;
}

export interface SignalHistoryPoint {
  date: string;
  signal: SignalLabel;
  score: number;
  model_version: string;
}

export interface SignalHistoryResponse {
  ticker: string;
  model_version: string;
  lookback_sessions: number;
  history: SignalHistoryPoint[];
  meta: DataMeta;
}

export interface SignalPerformanceHorizon {
  horizon_sessions: number;
  sample_size: number;
  positive_rate_percent: number | null;
  average_return_percent: number | null;
  median_return_percent: number | null;
}

export interface SignalPerformanceGroup {
  signal_group: string;
  total_signals: number;
  horizons: SignalPerformanceHorizon[];
}

export interface SignalPerformanceResponse {
  ticker: string;
  model_version: string;
  lookback_sessions: number;
  groups: SignalPerformanceGroup[];
  disclaimer: string;
  meta: DataMeta;
}

export interface FundamentalMetric {
  key: string;
  label: string;
  value: number | null;
  unit: string;
}

export interface FundamentalsResponse {
  ticker: string;
  valuation: FundamentalMetric[];
  growth: FundamentalMetric[];
  profitability: FundamentalMetric[];
  balance_sheet: FundamentalMetric[];
  has_any_data: boolean;
  meta: DataMeta;
}

export interface MarketRegimeResponse {
  benchmark: string;
  regime: "BULL" | "BEAR" | "SIDEWAYS" | "HIGH_VOLATILITY" | "UNAVAILABLE";
  trend_classification: string;
  momentum: "Positive" | "Negative" | "Neutral";
  volatility_regime: string;
  regime_confidence_percent: number;
  methodology: string;
  meta: DataMeta;
}

export interface RelativeStrengthPeriod {
  period: string;
  ticker_return_percent: number | null;
  benchmark_return_percent: number | null;
  relative_return_pp: number | null;
  classification: "STRONG" | "IN_LINE" | "WEAK" | "UNAVAILABLE";
}

export interface RelativeStrengthResponse {
  ticker: string;
  benchmark: string;
  periods: RelativeStrengthPeriod[];
  meta: DataMeta;
}

export interface SectorPeerReturn {
  symbol: string;
  return_percent: number | null;
}

export interface SectorComparisonResponse {
  ticker: string;
  sector: string | null;
  period: string;
  peers: SectorPeerReturn[];
  available: boolean;
  meta: DataMeta;
}

export interface ModelInfoResponse {
  current_version: string;
  supported_versions: string[];
  version_notes: Record<string, string>;
  factor_weights: { category: string; factor: string; min: number; max: number }[];
  score_thresholds: Record<string, number>;
  confidence_methodology: string;
  risk_methodology: string;
  backtest_methodology: Record<string, string>;
  no_look_ahead_methodology: string;
  data_limitations: string[];
  disclaimer: string;
}

export interface ModelPerformanceResponse {
  ticker: string;
  model_version: string;
  lookback_sessions: number;
  signal_counts: Record<string, number>;
  stability: SignalStability;
  performance: SignalPerformanceGroup[];
  backtest_summary: Record<string, number | string | null>;
  meta: DataMeta;
}

export type PaperExitReason =
  | "MODEL_SELL"
  | "STOP_LOSS"
  | "TAKE_PROFIT"
  | "TRAILING_STOP"
  | "END_OF_TEST"
  | "MANUAL_PAPER_EXIT";

export interface PaperPosition {
  ticker: string;
  shares: number;
  avg_entry_price: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_percent: number | null;
  stop_loss_percent: number | null;
  take_profit_percent: number | null;
  trailing_stop_percent: number | null;
  entry_signal: string | null;
  entry_score: number | null;
  entry_date: string | null;
}

export interface PaperTrade {
  date: string;
  ticker: string;
  action: "BUY" | "SELL";
  shares: number;
  price: number;
  realized_pnl: number | null;
  gross_pnl: number | null;
  fees: number | null;
  slippage: number | null;
  net_pnl: number | null;
  exit_reason: PaperExitReason | null;
  entry_signal: string | null;
  entry_score: number | null;
  exit_signal: string | null;
  exit_score: number | null;
  model_version: string | null;
  market_regime: string | null;
}

export interface PaperPortfolioResponse {
  portfolio_id: string;
  simulation_only: boolean;
  starting_capital: number;
  cash: number;
  invested_capital: number;
  current_value: number;
  total_return_percent: number;
  realized_pnl: number;
  unrealized_pnl: number;
  number_of_positions: number;
  exposure_percent: number;
  largest_position_percent: number;
  cash_percent: number;
  positions: PaperPosition[];
  trades: PaperTrade[];
  disclaimer: string;
}

export type PositionSizingMode = "FIXED_SHARES" | "FIXED_CAPITAL_PERCENT" | "RISK_PERCENT";

export interface PaperTradeRequestPayload {
  portfolio_id: string;
  ticker: string;
  action: "BUY" | "SELL";
  shares?: number | null;
  sizing_mode?: PositionSizingMode | null;
  capital_percent?: number | null;
  risk_percent?: number | null;
  max_position_percent?: number;
  stop_loss_percent?: number | null;
  take_profit_percent?: number | null;
  trailing_stop_percent?: number | null;
}

export interface PaperRiskResponse {
  total_exposure_percent: number;
  cash_percent: number;
  largest_position_percent: number;
  number_of_positions: number;
  sector_concentration: Record<string, number>;
  warnings: string[];
  methodology: string;
}

export interface WatchlistEntry {
  ticker: string;
  company_name: string | null;
  price: number | null;
  change_percent: number | null;
  signal: SignalLabel | null;
  score: number | null;
  trend_classification: string | null;
  market_regime: string | null;
  data_status: string;
  signal_changed_today: boolean;
  error: string | null;
}

export interface WatchlistResponse {
  watchlist_id: string;
  tickers: string[];
  entries: WatchlistEntry[];
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
