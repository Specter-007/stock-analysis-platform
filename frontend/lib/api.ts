import type {
  BacktestRequestPayload,
  BacktestResponse,
  HistoryResponse,
  MarketOverviewResponse,
  SearchResponse,
  SignalResponse,
  StockOverviewResponse,
  TechnicalResponse,
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

export function getStockSignal(ticker: string, signal?: AbortSignal) {
  return apiFetch<SignalResponse>(`/api/stock/${encodeURIComponent(ticker)}/signal`, { signal });
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
