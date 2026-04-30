/**
 * WebSocket client with auto-reconnect (exponential backoff, capped).
 * Used for /ws/positions, /ws/equity, /ws/signals, /ws/logs.
 *
 * Subscriptions are reference-counted with a linger window: when the
 * last consumer unsubscribes we wait LINGER_MS before actually closing
 * the socket. If a new subscriber arrives in that window we cancel the
 * close and keep the same socket — this prevents an open/close/open
 * storm when React quickly remounts components (Strict Mode in dev,
 * Suspense boundaries, route transitions).
 */

const LINGER_MS = 1500;

export type WsTopic = "positions" | "equity" | "signals" | "logs" | "prices";

type Listener<T> = (payload: T) => void;

interface Subscription {
  topic: WsTopic;
  listeners: Set<Listener<unknown>>;
  socket: WebSocket | null;
  reconnectAttempts: number;
  reconnectTimer: number | null;
  lingerTimer: number | null;
  closing: boolean;
}

const subs: Map<WsTopic, Subscription> = new Map();

function wsUrl(topic: WsTopic): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/${topic}`;
}

function connect(sub: Subscription): void {
  if (sub.socket && sub.socket.readyState <= WebSocket.OPEN) return;
  const ws = new WebSocket(wsUrl(sub.topic));
  sub.socket = ws;

  ws.addEventListener("open", () => {
    sub.reconnectAttempts = 0;
  });

  ws.addEventListener("message", (e) => {
    let data: unknown = e.data;
    try {
      data = JSON.parse(e.data);
    } catch {
      // keep raw string
    }
    sub.listeners.forEach((fn) => fn(data));
  });

  ws.addEventListener("close", () => {
    sub.socket = null;
    if (sub.closing || sub.listeners.size === 0) return;
    const delay = Math.min(15_000, 500 * 2 ** sub.reconnectAttempts);
    sub.reconnectAttempts += 1;
    sub.reconnectTimer = window.setTimeout(() => connect(sub), delay);
  });

  ws.addEventListener("error", () => {
    ws.close();
  });
}

export function subscribe<T = unknown>(topic: WsTopic, listener: Listener<T>): () => void {
  let sub = subs.get(topic);
  if (!sub) {
    sub = {
      topic,
      listeners: new Set(),
      socket: null,
      reconnectAttempts: 0,
      reconnectTimer: null,
      lingerTimer: null,
      closing: false,
    };
    subs.set(topic, sub);
  }
  // A new subscriber cancels any pending linger-close from a previous
  // unsubscribe, so transient remounts don't tear down the socket.
  if (sub.lingerTimer != null) {
    window.clearTimeout(sub.lingerTimer);
    sub.lingerTimer = null;
  }
  sub.closing = false;
  sub.listeners.add(listener as Listener<unknown>);
  if (!sub.socket) connect(sub);

  return () => {
    sub!.listeners.delete(listener as Listener<unknown>);
    if (sub!.listeners.size === 0 && sub!.lingerTimer == null) {
      sub!.lingerTimer = window.setTimeout(() => {
        sub!.lingerTimer = null;
        if (sub!.listeners.size > 0) return;   // resubscribed in time
        sub!.closing = true;
        if (sub!.reconnectTimer != null) window.clearTimeout(sub!.reconnectTimer);
        sub!.socket?.close();
        subs.delete(topic);
      }, LINGER_MS);
    }
  };
}
