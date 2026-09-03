import { AlertCircle, WifiOff, SearchX, Database } from "lucide-react";
import type { ApiError } from "@/lib/api";

const ERROR_ICON: Record<string, typeof AlertCircle> = {
  TICKER_NOT_FOUND: SearchX,
  DATA_UNAVAILABLE: Database,
  NETWORK_ERROR: WifiOff,
};

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const Icon = ERROR_ICON[error.errorType] ?? AlertCircle;

  return (
    <div className="flex flex-col items-center justify-center text-center gap-3 py-14 px-6 border border-border rounded-md bg-card">
      <Icon size={28} className="text-bearish" aria-hidden="true" />
      <p className="text-sm text-text-primary font-medium max-w-md">{error.message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-xs px-3 py-1.5 rounded border border-border-strong text-text-secondary hover:text-text-primary hover:border-accent transition-colors cursor-pointer"
        >
          Try again
        </button>
      )}
    </div>
  );
}
