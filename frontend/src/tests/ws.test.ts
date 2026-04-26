import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { subscribe } from "@/lib/ws";

class MockSocket {
  static instances: MockSocket[] = [];
  url: string;
  readyState = 0;
  listeners: Record<string, ((e: Event | MessageEvent) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    MockSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = 1;
      this.emit("open", new Event("open"));
    });
  }

  addEventListener(type: string, fn: (e: Event | MessageEvent) => void) {
    (this.listeners[type] ??= []).push(fn);
  }

  emit(type: string, e: Event | MessageEvent) {
    (this.listeners[type] ?? []).forEach((fn) => fn(e));
  }

  close() {
    this.readyState = 3;
    this.emit("close", new Event("close"));
  }

  // Required by lib/ws's `WebSocket` type usage.
  static OPEN = 1;
  static CLOSED = 3;
  send() {}
}

describe("ws subscribe", () => {
  let realSocket: typeof globalThis.WebSocket;

  beforeEach(() => {
    realSocket = globalThis.WebSocket;
    // @ts-expect-error -- minimal stub
    globalThis.WebSocket = MockSocket;
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, host: "test:8080", protocol: "http:" },
    });
    MockSocket.instances = [];
  });

  afterEach(() => {
    globalThis.WebSocket = realSocket;
  });

  it("delivers parsed JSON to subscribers", async () => {
    const handler = vi.fn();
    const unsub = subscribe<{ x: number }>("equity", handler);

    // Wait for the queueMicrotask open.
    await new Promise((r) => setTimeout(r, 0));
    const sock = MockSocket.instances[0];
    sock.emit("message", { data: JSON.stringify({ x: 42 }) } as MessageEvent);
    expect(handler).toHaveBeenCalledWith({ x: 42 });

    unsub();
  });

  it("opens the URL with the right scheme", async () => {
    subscribe("positions", () => {});
    await new Promise((r) => setTimeout(r, 0));
    expect(MockSocket.instances[0].url).toContain("ws://test:8080/ws/positions");
  });
});
