import type {
  BacktestRequestPayload,
  BacktestResponse,
  CompareExperimentsResponse,
  ComparisonRequestPayload,
  ComparisonResponse,
  CostStressRequestPayload,
  CostStressResponse,
  CreateExperimentPayload,
  DriftRequestPayload,
  DriftResponse,
  Experiment,
  ExperimentListResponse,
  ForwardVsHistoricalResponse,
  FundamentalsResponse,
  PaperPortfolioListResponse,
  ModelComparisonRequestPayload,
  ModelComparisonResponse,
  ScorecardRequestPayload,
  ScorecardResponse,
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
import type { Notification, NotificationListResponse, Preferences, SessionListResponse, User } from "@/types/auth";

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

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init?.headers as Record<string, string> || {}) };
  // Double-submit CSRF: the backend requires the signed csrf_token cookie's
  // value echoed back in this header on every state-changing request (see
  // backend/app/auth/dependencies.py:require_csrf). Safe methods never need it.
  if (!SAFE_METHODS.has(method)) {
    const csrfToken = readCookie("csrf_token");
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      method,
      headers,
      // Session/CSRF cookies are httpOnly (session) / same-site (csrf) and
      // must be sent on every request, including cross-origin ones between
      // the frontend and backend dev servers.
      credentials: "include",
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

  if (res.status === 204) return undefined as T;
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

export function getModelScorecard(payload: ScorecardRequestPayload, signal?: AbortSignal) {
  return apiFetch<ScorecardResponse>(`/api/model/scorecard`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function compareModelVersions(payload: ModelComparisonRequestPayload, signal?: AbortSignal) {
  return apiFetch<ModelComparisonResponse>(`/api/model/compare-versions`, {
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

// -------------------------------------------------------------------- V5

export function runCostStress(payload: CostStressRequestPayload, signal?: AbortSignal) {
  return apiFetch<CostStressResponse>(`/api/backtest/cost-stress`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function getModelDrift(payload: DriftRequestPayload, signal?: AbortSignal) {
  return apiFetch<DriftResponse>(`/api/model/drift`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function getPaperPortfolios(signal?: AbortSignal) {
  return apiFetch<PaperPortfolioListResponse>(`/api/paper-portfolios`, { signal });
}

// ------------------------------------------------------ Experiment Lab (V5)

export function createExperiment(payload: CreateExperimentPayload, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export function listExperiments(includeArchived = false, signal?: AbortSignal) {
  return apiFetch<ExperimentListResponse>(
    `/api/experiments?include_archived=${includeArchived}`,
    { signal }
  );
}

export function getExperiment(id: string, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}`, { signal });
}

export function deleteExperiment(id: string, signal?: AbortSignal) {
  return apiFetch<{ deleted: boolean; id: string }>(`/api/experiments/${encodeURIComponent(id)}`, {
    method: "DELETE",
    signal,
  });
}

export function runExperiment(id: string, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}/run`, {
    method: "POST",
    signal,
  });
}

export function updateExperimentNotes(id: string, notes?: string, tags?: string[], signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes: notes ?? null, tags: tags ?? null }),
    signal,
  });
}

export function duplicateExperiment(id: string, newName?: string, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}/duplicate`, {
    method: "POST",
    body: JSON.stringify({ new_name: newName ?? null }),
    signal,
  });
}

export function archiveExperiment(id: string, archived: boolean, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}/archive`, {
    method: "POST",
    body: JSON.stringify({ archived }),
    signal,
  });
}

export function startForwardSimulation(id: string, signal?: AbortSignal) {
  return apiFetch<Experiment>(`/api/experiments/${encodeURIComponent(id)}/forward-simulation`, {
    method: "POST",
    signal,
  });
}

export function compareExperiments(experimentIds: string[], signal?: AbortSignal) {
  return apiFetch<CompareExperimentsResponse>(`/api/experiments/compare`, {
    method: "POST",
    body: JSON.stringify({ experiment_ids: experimentIds }),
    signal,
  });
}

export function getForwardVsHistorical(id: string, signal?: AbortSignal) {
  return apiFetch<ForwardVsHistoricalResponse>(
    `/api/experiments/${encodeURIComponent(id)}/forward-vs-historical`,
    { signal }
  );
}

export function getExperimentExportUrl(id: string): string {
  return `${API_BASE_URL}/api/experiments/${encodeURIComponent(id)}/export`;
}

// --------------------------------------------------------------- Auth

export function registerAccount(payload: {
  email: string;
  password: string;
  display_name: string;
  accept_terms: boolean;
  marketing_consent?: boolean;
}) {
  return apiFetch<User>("/api/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export function login(email: string, password: string) {
  return apiFetch<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function logout() {
  return apiFetch<{ message: string }>("/api/auth/logout", { method: "POST" });
}

export function getCurrentUser(signal?: AbortSignal) {
  return apiFetch<User>("/api/auth/me", { signal });
}

export function requestPasswordReset(email: string) {
  return apiFetch<{ message: string }>("/api/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(token: string, new_password: string) {
  return apiFetch<{ message: string }>("/api/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ token, new_password }),
  });
}

export function requestEmailVerification() {
  return apiFetch<{ message: string }>("/api/auth/email-verification/request", { method: "POST" });
}

export function confirmEmailVerification(token: string) {
  return apiFetch<User>("/api/auth/email-verification/confirm", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function changePassword(current_password: string, new_password: string) {
  return apiFetch<{ message: string }>("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });
}

export function requestEmailChange(new_email: string, current_password: string) {
  return apiFetch<{ message: string }>("/api/auth/change-email/request", {
    method: "POST",
    body: JSON.stringify({ new_email, current_password }),
  });
}

export function confirmEmailChange(token: string) {
  return apiFetch<User>("/api/auth/change-email/confirm", { method: "POST", body: JSON.stringify({ token }) });
}

export function deleteAccount() {
  return apiFetch<{ message: string }>("/api/auth/account", { method: "DELETE" });
}

export function listSessions(signal?: AbortSignal) {
  return apiFetch<SessionListResponse>("/api/auth/sessions", { signal });
}

export function revokeSession(sessionId: string) {
  return apiFetch<{ message: string }>(`/api/auth/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}

export function revokeOtherSessions() {
  return apiFetch<{ message: string }>("/api/auth/sessions/revoke-others", { method: "POST" });
}

// ------------------------------------------------------------ Settings

export function getPreferences(signal?: AbortSignal) {
  return apiFetch<Preferences>("/api/settings/preferences", { signal });
}

export function updatePreferences(patch: Partial<Preferences>) {
  return apiFetch<Preferences>("/api/settings/preferences", { method: "PATCH", body: JSON.stringify(patch) });
}

export function completeOnboarding() {
  return apiFetch<Preferences>("/api/settings/onboarding/complete", { method: "POST" });
}

export function getAccountExportUrl(): string {
  return `${API_BASE_URL}/api/settings/export`;
}

// -------------------------------------------------------- Notifications

export function listNotifications(unreadOnly = false, signal?: AbortSignal) {
  return apiFetch<NotificationListResponse>(`/api/notifications?unread_only=${unreadOnly}`, { signal });
}

export function getUnreadNotificationCount(signal?: AbortSignal) {
  return apiFetch<{ unread_count: number }>("/api/notifications/unread-count", { signal });
}

export function markNotificationRead(id: string) {
  return apiFetch<{ marked: number }>(`/api/notifications/${encodeURIComponent(id)}/read`, { method: "POST" });
}

export function markAllNotificationsRead() {
  return apiFetch<{ marked: number }>("/api/notifications/read-all", { method: "POST" });
}

export type { Notification };

// -------------------------------------------------------------- Support

export function submitContactRequest(payload: {
  contact_email: string;
  category: string;
  subject: string;
  message: string;
}) {
  return apiFetch<{ id: string; created_at: string; message: string }>("/api/support", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
