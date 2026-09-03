import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";

export interface ApiResourceState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
}

interface ResultForKey<T> {
  key: string;
  data: T | null;
  error: ApiError | null;
}

const IDLE_STATE = { data: null, loading: false, error: null } as const;

/**
 * Fetches one resource whenever `deps` changes, cancelling any in-flight
 * request for the previous deps so a fast ticker switch never lets a stale
 * response overwrite a newer one.
 *
 * `loading` is deliberately DERIVED (whether the latest stored result's key
 * matches the current deps key) rather than its own piece of state set
 * synchronously inside the effect - the only setState calls here happen
 * inside the fetch's resolve/reject callbacks, which is what
 * react-hooks/set-state-in-effect wants: effects should subscribe to an
 * external system and update state from its callbacks, not assign state
 * imperatively in the effect body itself.
 */
export function useApiResource<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
  enabled: boolean = true
): ApiResourceState<T> {
  const key = JSON.stringify(deps);
  const [result, setResult] = useState<ResultForKey<T> | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const controller = new AbortController();

    fetcher(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data, error: null });
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        const apiErr = err instanceof ApiError ? err : new ApiError(0, "UNKNOWN_ERROR", "Something went wrong.");
        setResult({ key, data: null, error: apiErr });
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  if (!enabled) return IDLE_STATE;

  const loading = result === null || result.key !== key;
  if (loading) return { data: null, loading: true, error: null };

  return { data: result.data, loading: false, error: result.error };
}
