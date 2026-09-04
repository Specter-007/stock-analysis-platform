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

export interface PaperEquitySnapshot {
  date: string;
  recorded_at: string;
  equity: number;
  cash: number;
  invested_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  cumulative_return_percent: number | null;
  benchmark_value: number | null;
  daily_pnl: number | null;
  previous_snapshot_date: string | null;
}

export interface PaperEquityHistoryResponse {
  portfolio_id: string;
  starting_capital: number;
  benchmark_ticker: string | null;
  snapshots: PaperEquitySnapshot[];
  methodology: string;
}

export interface ForwardValidationResponse {
  portfolio_id: string;
  model_version: string;
  model_version_is_mixed: boolean;
  start_date: string | null;
  current_date: string | null;
  trading_days_observed: number;
  initial_capital: number;
  current_equity: number;
  total_return_percent: number;
  benchmark_ticker: string | null;
  benchmark_return_percent: number | null;
  max_drawdown_percent: number | null;
  number_of_trades: number;
  open_positions_count: number;
  realized_pnl: number;
  unrealized_pnl: number;
  insufficient_sample: boolean;
  warnings: string[];
  methodology: string;
}

export type AllocationMethod = "EQUAL_WEIGHT" | "FIXED_WEIGHT" | "SIGNAL_WEIGHTED" | "RISK_WEIGHTED";
export type RebalanceFrequency = "DAILY" | "WEEKLY" | "MONTHLY";

export interface PortfolioConstraintsPayload {
  max_position_weight_percent?: number;
  min_position_weight_percent?: number;
  max_holdings?: number | null;
  cash_allocation_percent?: number;
  sector_cap_percent?: number | null;
}

export interface PortfolioBacktestRequestPayload {
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  allocation_method: AllocationMethod;
  rebalance_frequency: RebalanceFrequency;
  constraints?: PortfolioConstraintsPayload;
  fixed_weights?: Record<string, number> | null;
  benchmark_ticker?: string | null;
}

export interface PortfolioHoldingSnapshot {
  date: string;
  ticker: string;
  weight_percent: number;
  shares: number;
  price: number;
  market_value: number;
}

export interface PortfolioBacktestResponse {
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  allocation_method: AllocationMethod;
  rebalance_frequency: RebalanceFrequency;
  total_return_percent: number | null;
  equal_weight_buy_hold_return_percent: number | null;
  benchmark_ticker: string | null;
  benchmark_return_percent: number | null;
  max_drawdown_percent: number | null;
  sharpe_ratio: number | null;
  trading_days: number;
  number_of_rebalances: number;
  equity_curve: EquityPoint[];
  equal_weight_buy_hold_curve: EquityPoint[];
  benchmark_curve: EquityPoint[];
  drawdown_curve: EquityPoint[];
  holdings_history: PortfolioHoldingSnapshot[];
  advanced_metrics: Record<string, number | null>;
  risk_analytics: {
    exposure_percent: number;
    cash_percent: number;
    largest_position_percent: number;
    top_3_concentration_percent: number;
    sector_concentration_percent: Record<string, number>;
    correlation_matrix: Record<string, Record<string, number | null>> | null;
    number_of_holdings: number;
  };
  warnings: string[];
  excluded_tickers: Record<string, string>;
  methodology: Record<string, string>;
  meta: DataMeta;
}

export interface ComparisonRow {
  ticker: string;
  error: string | null;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  last_price: number | null;
  change_percent: number | null;
  market_cap: number | null;
  trend_classification: string | null;
  rsi_14: number | null;
  dist_sma_50_pct: number | null;
  dist_sma_200_pct: number | null;
  historical_volatility_percent: number | null;
  return_1m_percent: number | null;
  return_3m_percent: number | null;
  return_6m_percent: number | null;
  return_1y_percent: number | null;
  relative_strength_1y_classification: string | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  price_to_book: number | null;
  revenue_growth_percent: number | null;
  profit_margin_percent: number | null;
  return_on_equity_percent: number | null;
  signal: string | null;
  score: number | null;
  model_version: string | null;
}

export interface ComparisonResponse {
  tickers: string[];
  benchmark_ticker: string;
  rows: ComparisonRow[];
  methodology: string;
}

export interface ComparisonRequestPayload {
  tickers: string[];
  benchmark_ticker?: string;
}

export type ScorecardLabel = "STRONG" | "MODERATE" | "WEAK" | "INSUFFICIENT_DATA" | "NOT_PROVIDED";

export interface ScorecardDimension {
  name: string;
  label: ScorecardLabel;
  detail: string;
  supporting_metrics: Record<string, number | string | null>;
}

export interface ScorecardResponse {
  ticker: string;
  model_version: string;
  dimensions: ScorecardDimension[];
  composite_note: string;
  methodology: string;
  meta: DataMeta;
}

export interface ScorecardRequestPayload {
  ticker: string;
  benchmark?: string;
  initial_capital?: number;
  transaction_cost_bps?: number;
  slippage_bps?: number;
  forward_portfolio_id?: string | null;
}

export interface ModelVersionBacktestSummary {
  model_version: string;
  total_return_percent: number | null;
  cagr_percent: number | null;
  sharpe_ratio: number | null;
  max_drawdown_percent: number | null;
  number_of_trades: number;
  win_rate_percent: number | null;
}

export interface ModelVersionForwardSummary {
  model_version: string;
  portfolio_id: string;
  trading_days_observed: number;
  total_return_percent: number;
  insufficient_sample: boolean;
}

export interface ModelComparisonResponse {
  ticker: string;
  backtest_comparison: ModelVersionBacktestSummary[];
  forward_comparison: ModelVersionForwardSummary[];
  methodology: string;
  meta: DataMeta;
}

export interface ModelComparisonRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  transaction_cost_bps?: number;
  slippage_bps?: number;
  benchmark_ticker?: string;
  forward_portfolio_id_v1?: string | null;
  forward_portfolio_id_v2?: string | null;
}

export interface MonteCarloResponse {
  ticker: string;
  simulations: number;
  resampling_basis: "trade_returns" | "daily_returns" | "unavailable";
  resampling_method: "iid_bootstrap" | "block_bootstrap" | "unavailable";
  sample_size: number;
  seed: number | null;
  median_return_percent: number | null;
  percentile_5_return_percent: number | null;
  percentile_95_return_percent: number | null;
  median_max_drawdown_percent: number | null;
  worst_max_drawdown_percent: number | null;
  median_cagr_percent: number | null;
  percentile_5_cagr_percent: number | null;
  percentile_95_cagr_percent: number | null;
  median_final_equity: number | null;
  percentile_5_final_equity: number | null;
  percentile_95_final_equity: number | null;
  probability_of_loss_percent: number | null;
  drawdown_threshold_percent: number;
  probability_of_exceeding_drawdown_threshold_percent: number | null;
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
  drawdown_threshold_percent?: number;
}

// -------------------------------------------------------------------- V5

export interface CostStressScenario {
  label: string;
  commission_bps: number;
  slippage_bps: number;
  net_return_percent: number | null;
  total_cost_percent: number | null;
  cagr_percent: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown_percent: number | null;
  turnover_percent: number | null;
  number_of_trades: number;
}

export interface CostStressResponse {
  ticker: string;
  gross_return_percent: number | null;
  commission_scenarios: CostStressScenario[];
  slippage_scenarios: CostStressScenario[];
  methodology: string;
  meta: DataMeta;
}

export interface CostStressRequestPayload {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  base_commission_bps: number;
  base_slippage_bps: number;
}

export type DriftBucketLabel = string;

export interface DistributionComparison {
  dimension: string;
  historical_percent: Record<DriftBucketLabel, number>;
  recent_percent: Record<DriftBucketLabel, number>;
  shifted_buckets: string[];
  flagged: boolean;
}

export interface DriftResponse {
  ticker: string;
  model_version: string;
  historical_sessions: number;
  recent_sessions: number;
  insufficient_data: boolean;
  signal_distribution: DistributionComparison | null;
  factor_distribution: DistributionComparison | null;
  regime_distribution: DistributionComparison | null;
  methodology: string;
  meta: DataMeta;
}

export interface DriftRequestPayload {
  ticker: string;
  benchmark?: string;
}

// ------------------------------------------------------ Experiment Lab (V5)

export type ExperimentStatus =
  | "DRAFT" | "CONFIGURED" | "RUNNING" | "COMPLETED" | "VALIDATED" | "PAPER_FORWARD_TEST" | "FAILED";

export interface PortfolioConstraintsInput {
  max_position_weight_percent?: number;
  min_position_weight_percent?: number;
  max_holdings?: number | null;
  cash_allocation_percent?: number;
  sector_cap_percent?: number | null;
}

export interface ExperimentConfig {
  model_version: string;
  tickers: string[];
  benchmark: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_bps: number;
  slippage_bps: number;
  allocation_method: string | null;
  rebalance_frequency: string | null;
  portfolio_constraints: PortfolioConstraintsInput | null;
  run_out_of_sample: boolean;
  run_walk_forward: boolean;
  run_sensitivity: boolean;
  run_monte_carlo: boolean;
  run_regime_analysis: boolean;
  run_cost_stress: boolean;
  monte_carlo_simulations: number;
  monte_carlo_seed: number | null;
  sensitivity_parameters: string[];
  walk_forward_train_years: number;
  walk_forward_test_years: number;
  walk_forward_max_folds: number;
}

export interface CreateExperimentPayload {
  name: string;
  config: ExperimentConfig;
  notes?: string;
  tags?: string[];
}

export interface ValidationOutcome {
  requested: boolean;
  completed: boolean;
  error: string | null;
  result: Record<string, unknown> | null;
}

export interface ExperimentResults {
  backtest: ValidationOutcome;
  out_of_sample: ValidationOutcome;
  walk_forward: ValidationOutcome;
  sensitivity: ValidationOutcome;
  monte_carlo: ValidationOutcome;
  regime_performance: ValidationOutcome;
  cost_stress: ValidationOutcome;
}

export interface DataProvenance {
  data_source: string;
  retrieved_at: string;
  data_status: string;
  tickers_retrieved: string[];
  tickers_unavailable: Record<string, string>;
  latest_market_timestamp: string | null;
  timeframe: string;
}

export interface Experiment {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  status: ExperimentStatus;
  config: ExperimentConfig;
  fingerprint: string;
  notes: string;
  tags: string[];
  results: ExperimentResults | null;
  data_provenance: DataProvenance | null;
  error: string | null;
  forward_portfolio_id: string | null;
  reproduced_from: string | null;
  archived: boolean;
}

export interface ExperimentListRow {
  experiment: Experiment;
  group_count: number;
  data_mining_warning: boolean;
}

export interface ExperimentListResponse {
  experiments: ExperimentListRow[];
  methodology: string;
}

export interface CompareExperimentsResponse {
  experiments: Experiment[];
  warnings: string[];
}

export interface ForwardVsHistoricalMetrics {
  return_percent: number | null;
  sharpe_ratio: number | null;
  max_drawdown_percent: number | null;
  trading_days_observed: number | null;
}

export interface ForwardVsHistoricalResponse {
  available: boolean;
  reason: string | null;
  historical: ForwardVsHistoricalMetrics | null;
  historical_source: string | null;
  forward: ForwardVsHistoricalMetrics | null;
  forward_sample_developing: boolean;
  deviation_notes: string[];
}

export interface PaperPortfolioSummary {
  portfolio_id: string;
  starting_capital: number;
  current_value: number;
  total_return_percent: number;
  number_of_positions: number;
  number_of_trades: number;
  cash_percent: number;
}

export interface PaperPortfolioListResponse {
  portfolios: PaperPortfolioSummary[];
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
