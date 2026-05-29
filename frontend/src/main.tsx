import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { ThemeProvider } from "./theme/ThemeProvider";
import "./styles/index.css";

// Forward any JS error / unhandled rejection to the backend log so it
// shows up in hermes.log - --windowed builds have no devtools.
//
// v1.0.34: switched the transport to navigator.sendBeacon. fetch() is
// async + cancellable, so when WebView2 dies mid-render (which is what
// we're chasing here), the request never reaches uvicorn and the log
// line is lost forever. sendBeacon is kernel-queued by the browser
// before any JS continuation runs - guaranteed delivery even if the
// renderer is torn down a millisecond later.
function reportClientError(message: string, stack: string) {
  const payload = JSON.stringify({ message, stack, component_stack: "" });
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: "application/json" });
      const ok = navigator.sendBeacon("/api/system/log-client-error", blob);
      if (ok) return;
    }
  } catch {
    /* fall through to fetch */
  }
  try {
    fetch("/api/system/log-client-error", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* swallow */
  }
}

// Boot-time progress beacons. If WebView2 tears down between any two
// of these, hermes.log will show exactly which step was the last one
// alive. Without this, the log just stops at "WS open" with no clue
// what crashed in the renderer.
export function trace(stage: string): void {
  try {
    const blob = new Blob([JSON.stringify({ stage })], { type: "application/json" });
    navigator.sendBeacon?.("/api/system/trace", blob);
  } catch {
    /* never let a trace failure cascade */
  }
}

trace("main.tsx:boot");

window.addEventListener("error", (e) => {
  // Swallow at window level so a single async hiccup doesn't poison
  // the rest of the app. Real React render errors still hit
  // ErrorBoundary; this guard catches the "fire and forget" rejects
  // and stray setTimeout throws that WebView2 otherwise propagates.
  reportClientError(e.message ?? "error", e.error?.stack ?? "");
  e.preventDefault();
});
window.addEventListener("unhandledrejection", (e) => {
  const reason = e.reason as { message?: string; stack?: string } | string;
  if (typeof reason === "string") reportClientError(reason, "");
  else reportClientError(reason?.message ?? "unhandled rejection", reason?.stack ?? "");
  e.preventDefault();
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5_000,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
