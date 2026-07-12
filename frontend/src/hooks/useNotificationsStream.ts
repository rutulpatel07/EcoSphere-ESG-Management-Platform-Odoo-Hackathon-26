import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export type StreamStatus = "connecting" | "open" | "unavailable";

// GET /environmental/events (app/routers/carbon.py) is the live SSE stream —
// deliberately unauthenticated (native EventSource cannot send an Authorization
// header), fanning out two named events: "carbon.created" (a carbon transaction
// was just recorded) and "score.updated" (a department's E/S/G/total moved).
// Either one means the dashboard summary is stale — call onLiveEvent to refetch it.
export function useNotificationsStream(onLiveEvent: () => void) {
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const failureCount = useRef(0);

  useEffect(() => {
    const url = `${API_BASE}/environmental/events`;
    const source = new EventSource(url);

    function handleLiveEvent() {
      failureCount.current = 0;
      setStatus("open");
      onLiveEvent();
    }

    source.addEventListener("carbon.created", handleLiveEvent);
    source.addEventListener("score.updated", handleLiveEvent);
    // "ping" is a keepalive with no payload — just confirms the connection is alive.
    source.addEventListener("ping", () => setStatus("open"));

    source.onopen = () => setStatus("open");

    source.onerror = () => {
      failureCount.current += 1;
      // EventSource retries indefinitely on its own; after a few failures assume the
      // backend isn't reachable rather than flashing "connecting" forever.
      if (failureCount.current >= 2) setStatus("unavailable");
    };

    return () => source.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return status;
}
