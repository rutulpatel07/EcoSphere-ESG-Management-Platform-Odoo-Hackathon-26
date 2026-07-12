import { useEffect, useState } from "react";
import { AxiosError } from "axios";

export type ApiState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };

export function describeApiError(err: unknown): string {
  if (err instanceof AxiosError) {
    if (err.response) {
      if (err.response.status === 404) {
        return `Endpoint not implemented yet on the backend (${err.config?.method?.toUpperCase()} ${err.config?.url} → 404).`;
      }
      return `Request failed: ${err.response.status} ${err.response.statusText}`;
    }
    return "Could not reach the backend. Is it running?";
  }
  return err instanceof Error ? err.message : "Unknown error";
}

// Refetches whenever `deps` changes; pass a stable empty array for "fetch once on mount".
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): ApiState<T> & { refetch: () => void } {
  const [state, setState] = useState<ApiState<T>>({ status: "loading" });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "success", data });
      })
      .catch((err) => {
        if (!cancelled) setState({ status: "error", error: describeApiError(err) });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  return { ...state, refetch: () => setTick((t) => t + 1) };
}
