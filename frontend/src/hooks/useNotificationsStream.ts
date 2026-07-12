import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export type StreamStatus = "connecting" | "open" | "unavailable";

// Contract only defines GET /notifications/stream (SSE) — there is no /events route.
// Native EventSource cannot send an Authorization header, so the token is passed as a
// query param; the backend does not currently document support for that either.
export function useNotificationsStream(onEvent: (payload: unknown) => void) {
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const failureCount = useRef(0);

  useEffect(() => {
    const token = localStorage.getItem("ecosphere_token");
    const url = `${API_BASE}/notifications/stream${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    const source = new EventSource(url);

    source.addEventListener("notification", (e) => {
      failureCount.current = 0;
      setStatus("open");
      try {
        onEvent(JSON.parse((e as MessageEvent).data));
      } catch {
        onEvent((e as MessageEvent).data);
      }
    });

    source.onopen = () => setStatus("open");

    source.onerror = () => {
      failureCount.current += 1;
      // EventSource retries indefinitely on its own; after a few failures assume the
      // endpoint isn't implemented rather than flashing "connecting" forever.
      if (failureCount.current >= 2) setStatus("unavailable");
    };

    return () => source.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return status;
}
