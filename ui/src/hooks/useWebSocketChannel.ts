import { useEffect, useRef, useState } from 'react';

const RECONNECT_DELAY_MS = 2000;

/**
 * Subscribes to a JSON-message WebSocket channel with auto-reconnect.
 * Backend channels (ws/state, ws/telemetry) are fire-and-forget broadcasts —
 * the server never expects messages back, so this is read-only by design.
 */
export function useWebSocketChannel<T>(url: string, enabled = true) {
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
      socket.onerror = () => socket.close();
      socket.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data) as T);
        } catch {
          // ignore malformed frames
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      socketRef.current?.close();
    };
  }, [url, enabled]);

  return { lastMessage, connected };
}
