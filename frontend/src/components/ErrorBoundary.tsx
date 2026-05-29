import React from "react";

interface Props {
  children: React.ReactNode;
  /** When true, render a compact inline error placeholder instead of a
   *  full-screen takeover. Used for per-section boundaries inside a
   *  page where one widget crashing shouldn't blow up the whole layout. */
  inline?: boolean;
  /** Identifier traced to the backend log so we know which boundary
   *  caught the error (useful when many small ones are nested). */
  name?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
    // v1.0.34: sendBeacon survives a renderer tear-down; fetch did not.
    const payload = JSON.stringify({
      message: `[${this.props.name ?? "root"}] ${error.message}`,
      stack: error.stack ?? "",
      component_stack: info.componentStack ?? "",
    });
    try {
      const blob = new Blob([payload], { type: "application/json" });
      if (navigator.sendBeacon?.("/api/system/log-client-error", blob)) return;
    } catch { /* fall through */ }
    try {
      fetch("/api/system/log-client-error", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      }).catch(() => {});
    } catch { /* swallow */ }
  }

  reset = () => {
    this.setState({ error: null });
    if (!this.props.inline) location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.inline) {
      return (
        <div className="rounded-lg border border-hermes-wine/40 bg-hermes-wine/5 p-3 text-xs text-muted-foreground">
          <div className="font-semibold text-hermes-wine">
            {this.props.name ? `Блок «${this.props.name}» недоступен` : "Виджет недоступен"}
          </div>
          <div className="mt-1 opacity-75">{this.state.error.message}</div>
          <button
            onClick={this.reset}
            className="mt-2 rounded border border-hermes-wine/30 px-2 py-1 text-[10px] hover:bg-hermes-wine/10"
          >
            Попробовать снова
          </button>
        </div>
      );
    }
    return (
      <div className="grid min-h-screen place-items-center bg-background px-6">
        <div className="marble-card max-w-xl p-8 text-center">
          <h1 className="display text-2xl font-semibold gold-text">
            Ой, Гермес споткнулся
          </h1>
          <p className="mt-2 font-serif italic text-muted-foreground">
            Что-то пошло не так в интерфейсе. Перезагрузка обычно помогает.
          </p>
          <pre className="mt-4 overflow-auto rounded-lg border border-hermes-gold/30 bg-hermes-alabaster/40 p-3 text-left text-xs text-muted-foreground">
            {this.state.error.name}: {this.state.error.message}
          </pre>
          <button
            onClick={this.reset}
            className="gold-button mt-6 rounded-xl px-6 py-3 text-sm font-semibold uppercase tracking-wider"
          >
            Перезагрузить
          </button>
        </div>
      </div>
    );
  }
}
