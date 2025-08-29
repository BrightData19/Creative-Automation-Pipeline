export type GatewayEvent = {
  topic: string;
  event_id?: string;
  ts?: string;
  [key: string]: unknown;
};

export type EventUnsubscribe = () => void;

export function connectEvents(
  onMessage: (event: GatewayEvent) => void,
  onError?: (err: Error | Event) => void,
  onOpen?: () => void
): EventUnsubscribe {
  const base = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:3001";
  const es = new EventSource(`${base}/events`);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onMessage(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to parse SSE data");
      onError?.(error);
    }
  };
  es.onopen = () => {
    try {
      onOpen?.();
    } catch {}
  };
  es.onerror = (ev) => {
    // Normalize browser Event into a meaningful Error message without noisy [object Event]
    const ready = (es as any).readyState; // 0=CONNECTING, 1=OPEN, 2=CLOSED
    const msg = `SSE error (readyState=${ready})`;
    onError?.(new Error(msg));
  };

  return () => {
    es.close();
  };
}
