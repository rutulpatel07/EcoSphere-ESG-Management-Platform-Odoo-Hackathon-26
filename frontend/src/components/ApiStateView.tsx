import { ReactNode } from "react";
import type { ApiState } from "../hooks/useApi";

// Consistent loading/error rendering for any useApi() result, inside a .card.
export default function ApiStateView<T>({
  state,
  children,
}: {
  state: ApiState<T> & { refetch: () => void };
  children: (data: T) => ReactNode;
}) {
  if (state.status === "loading") {
    return <p className="uncertainty-badge">Loading…</p>;
  }
  if (state.status === "error") {
    return (
      <div className="api-error">
        <span>⚠ {state.error}</span>
        <button type="button" className="chip-btn" onClick={state.refetch}>
          Retry
        </button>
      </div>
    );
  }
  return <>{children(state.data)}</>;
}
