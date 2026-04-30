import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { ThemeProvider } from "./theme/ThemeProvider";
import "./styles/index.css";

// Forward any JS error / unhandled rejection to the backend log so it
// shows up in hermes.log — --windowed builds have no devtools.
function reportClientError(message: string, stack: string) {
  try {
    fetch("/api/system/log-client-error", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, stack, component_stack: "" }),
    }).catch(() => {});
  } catch {
    /* swallow */
  }
}
window.addEventListener("error", (e) => {
  reportClientError(e.message ?? "error", e.error?.stack ?? "");
});
window.addEventListener("unhandledrejection", (e) => {
  const reason = e.reason as { message?: string; stack?: string } | string;
  if (typeof reason === "string") reportClientError(reason, "");
  else reportClientError(reason?.message ?? "unhandled rejection", reason?.stack ?? "");
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
