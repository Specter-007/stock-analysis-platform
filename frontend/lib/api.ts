import type {
  BacktestRequestPayload,
  BacktestResponse,
  ComparisonRequestPayload,
  ComparisonResponse,
  FundamentalsResponse,
  HistoryResponse,
  MarketOverviewResponse,
  MarketRegimeResponse,
  ModelInfoResponse,
  ModelPerformanceResponse,
  ForwardValidationResponse,
  MonteCarloRequestPayload,
  MonteCarloResponse,
  PaperEquityHistoryResponse,
  PaperPortfolioResponse,
  PortfolioBacktestRequestPayload,
  PortfolioBacktestResponse,
  SensitivityHeatmapRequestPayload,
  SensitivityHeatmapResponse,
  SensitivityRequestPayload,
  SensitivityResponse,
  PaperRiskResponse,
  PaperTradeRequestPayload,
  WatchlistResponse,
  RelativeStrengthResponse,
  SearchResponse,
  SectorComparisonResponse,
  SignalHistoryResponse,
  SignalPerformanceResponse,
  SignalResponse,
  StockOverviewResponse,
  TechnicalResponse,
  WalkForwardRequestPayload,
  WalkForwardResponse,
} from "@/types/api";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  errorType: string;

  constructor(status: number, errorType: string, message: string) {
    super(message);
    this.status = status;
    this.errorType = errorType;
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the analysis server. Is the backend running?");
  }

  if (!res.ok) {
    let errorType = "UNKNOWN_ERROR";
    let detail = `Request failed with status ${res.status}.`;
    try {
      const body = await res.json();
      errorType = body.error_type || errorType;
      detail = body.detail || detail;
    } catch {
      // Response wasn't JSON - keep generic message rather than leaking raw text.
    }
    throw new ApiError(res.status, errorType, detail);
  }

  return res.json() as Promise<T>;
}

export function getStockOverview(ticker: string, signal?: AbortSignal) {
  return apiFetch<StockOverviewResponse>(`/api/stock/${encodeURIComponent(ticker)}`, { signal });
}

export function getStockHistory(ticker: string, range: string, signal?: AbortSignal) {
  return apiFetch<HistoryResponse>(
    `/api/stock/${encodeURIComponent(ticker)}/history?range=${encodeURIComponent(range)}`,
    { signal }
  );
}

export function getStockTechnical(ticker: string, signal?: AbortSignal) {
  return apiFetch<TechnicalResponse>(`/api/stock/${encodeURIComponent(ticker)}/technical`, { signal });
}

export function getStockSignal(ticker: string, signal?: AbortSignal, includeOverallScore = false) {
  const query = includeOverallScore ? "?include_overall_score=true" : "";
  return apiFetch<SignalResponse>(`/api/stock/${encodeURIComponent(ticker)}/signal${query}`, { signal });
}

export function getSignalHistory(ticker: string, lookbackSessions = 60, signal?: AbortSignal) {
  return apiFetch<SignalHistoryResponse>(
    `/api/stock/${encodeURIComponent(ticker)}/signal-history?lookback_sessions=${lookbackSessions}`,
    { signal }
  );
}

export function getSignalPerformance(ticker: string, signal?: AbortSignal) {
  return apiFetch<SignalPerformanceResponse>(`/api/stock/${encodeURIComponent(ticker)}/signal-performance`, {
    signal,
  });
}

export function getFundamentals(ticker: string, signal?: AbortSignal) {
  return apiFetch<FundamentalsResponse>(`/api/stock/${encodeURIComponent(ticker)}/fundamentals`, { signal });
}

export function getRelativeStrength(ticker: string, benchmark = "SPY", signal?: AbortSignal) {
  return apiFetch<RelativeStrengthResponse>(
    `/api/stock/${encodeURIComponent(ticker)}/relative-strength?benchmark=${encodeURIComponent(benchmark)}`,
    { signal }
  );
}

export function getSectorComparison(ticker: string, signal?: AbortSignal) {
  return apiFetch<SectorComparisonResponse>(`/api/stock/${encodeURIComponent(ticker)}/sector`, { signal });
}

export function getMarketRegime(signal?: AbortSignal) {
  return apiFetch<MarketRegimeResponse>(`/api/market/regime`, { signal });
}

export function getModelInfo(signal?: AbortSignal) {
  return apiFetch<ModelInfoResponse>(`/api/model`, { signal });
}

export function getModelPerformance(ticker: string, signal?: AbortSignal) {
  return apiFetch<ModelPerformanceResponse>(`/api/model/performance?ticker=${encodeURIComponent(ticker)}`, {
    signal,
  });
}

export function runWalkForward(payload: WalkForwardRequestPayload, signal?: AbortSignal) {
  return apiFetch<WalkForwardResponse>(`/api/backtest/walk-forward`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function runMonteCarlo(payload: MonteCarloRequestPayload, signal?: AbortSignal) {
  return apiFetch<MonteCarloResponse>(`/api/backtest/monte-carlo`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function runSensitivity(payload: SensitivityRequestPayload, signal?: AbortSignal) {
  return apiFetch<SensitivityResponse>(`/api/backtest/sensitivity`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function runSensitivityHeatmap(payload: SensitivityHeatmapRequestPayload, signal?: AbortSignal) {
  return apiFetch<SensitivityHeatmapResponse>(`/api/backtest/sensitivity/heatmap`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function runPortfolioBacktest(payload: PortfolioBacktestRequestPayload, signal?: AbortSignal) {
  return apiFetch<PortfolioBacktestResponse>(`/api/backtest/portfolio`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function compareStocks(payload: ComparisonRequestPayload, signal?: AbortSignal) {
  return apiFetch<ComparisonResponse>(`/api/compare`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function getPaperPortfolio(portfolioId = "default", signal?: AbortSignal) {
  return apiFetch<PaperPortfolioResponse>(`/api/paper-portfolio?portfolio_id=${encodeURIComponent(portfolioId)}`, {
    signal,
  });
}

export function postPaperTrade(payload: PaperTradeRequestPayload, signal?: AbortSignal) {
  return apiFetch<PaperPortfolioResponse>(`/api/paper-trade`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function resetPaperPortfolio(portfolioId = "default", startingCapital?: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ portfolio_id: portfolioId });
  if (startingCapital) params.set("starting_capital", String(startingCapital));
  return apiFetch<PaperPortfolioResponse>(`/api/paper-portfolio/reset?${params.toString()}`, {
    method: "POST",
    signal,
  });
}

export function getPaperRisk(portfolioId = "default", signal?: AbortSignal) {
  return apiFetch<PaperRiskResponse>(`/api/paper-portfolio/risk?portfolio_id=${encodeURIComponent(portfolioId)}`, {
    signal,
  });
}

export function closeAllPaperPositions(portfolioId = "default", signal?: AbortSignal) {
  return apiFetch<PaperPortfolioResponse>(
    `/api/paper-portfolio/close-all?portfolio_id=${encodeURIComponent(portfolioId)}`,
    { method: "POST", signal }
  );
}

export function getPaperEquityHistory(portfolioId = "default", signal?: AbortSignal) {
  return apiFetch<PaperEquityHistoryResponse>(
    `/api/paper-portfolio/history?portfolio_id=${encodeURIComponent(portfolioId)}`,
    { signal }
  );
}

export function getForwardValidation(portfolioId = "default", signal?: AbortSignal) {
  return apiFetch<ForwardValidationResponse>(
    `/api/paper-portfolio/forward-validation?portfolio_id=${encodeURIComponent(portfolioId)}`,
    { signal }
  );
}

export function getWatchlist(watchlistId = "default", signal?: AbortSignal) {
  return apiFetch<WatchlistResponse>(`/api/watchlist?watchlist_id=${encodeURIComponent(watchlistId)}`, { signal });
}

export function addToWatchlist(ticker: string, watchlistId = "default", signal?: AbortSignal) {
  return apiFetch<WatchlistResponse>(`/api/watchlist`, {
    method: "POST",
    body: JSON.stringify({ watchlist_id: watchlistId, ticker }),
    signal,
  });
}

export function removeFromWatchlist(ticker: string, watchlistId = "default", signal?: AbortSignal) {
  return apiFetch<WatchlistResponse>(
    `/api/watchlist/${encodeURIComponent(ticker)}?watchlist_id=${encodeURIComponent(watchlistId)}`,
    { method: "DELETE", signal }
  );
}

export function searchTickers(query: string, signal?: AbortSignal) {
  return apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}`, { signal });
}

export function getMarketStatus(signal?: AbortSignal) {
  return apiFetch<MarketOverviewResponse>(`/api/market/status`, { signal });
}

export function runBacktest(payload: BacktestRequestPayload, signal?: AbortSignal) {
  return apiFetch<BacktestResponse>(`/api/backtest`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}
