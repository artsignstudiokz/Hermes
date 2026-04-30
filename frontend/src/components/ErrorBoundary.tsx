import React from "react";

interface Props {
  children: React.ReactNode;
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
    fetch("/api/system/log-client-error", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: error.message,
        stack: error.stack ?? "",
        component_stack: info.componentStack ?? "",
      }),
    }).catch(() => {});
  }

  reset = () => {
    this.setState({ error: null });
    location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;
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
