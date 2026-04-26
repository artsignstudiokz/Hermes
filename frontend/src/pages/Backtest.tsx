import { motion } from "framer-motion";
import { Loader2, Play, TestTube } from "lucide-react";
import { useEffect, useState } from "react";

import {
  useBacktestRun,
  useBacktestRuns,
  useStartBacktest,
} from "@/api/useBacktest";
import { useStrategyConfig } from "@/api/useStrategy";
import { subscribe } from "@/lib/ws";
import { formatDateTime } from "@/lib/format";

interface ProgressEvent {
  type: string;
  stage?: string;
  pct?: number;
  symbol?: string;
  metrics?: Record<string, unknown>;
  message?: string;
}

export function Backtest() {
  const config = useStrategyConfig();
  const runs = useBacktestRuns();
  const start = useStartBacktest();
  const [days, setDays] = useState(90);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const detail = useBacktestRun(activeRunId);

  useEffect(() => {
    if (activeRunId === null) return;
    const unsub = subscribe<ProgressEvent>(`backtest_${activeRunId}` as never, (e) => {
      setProgress(e);
    });
    return unsub;
  }, [activeRunId]);

  const onRun = async () => {
    if (!config.data) return;
    setProgress(null);
    const { run_id } = await start.mutateAsync({
      params: config.data.payload,
      symbols: config.data.payload.symbols,
      days,
    });
    setActiveRunId(run_id);
  };

  const metrics = (detail.data?.metrics ?? {}) as Record<string, unknown>;
  const isRunning = progress && progress.type !== "complete" && progress.type !== "error";
  const pct = Math.round(progress?.pct ?? 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Бэктест</p>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
            Проверка <span className="gold-text">на истории</span>
          </h1>
          <p className="mt-1 max-w-2xl font-serif italic text-muted-foreground">
            Прогон стратегии на свежих данных биржи. Запускается через активного брокера.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="form-input"
          >
            <option value={30}>30 дней</option>
            <option value={60}>60 дней</option>
            <option value={90}>90 дней</option>
            <option value={180}>180 дней</option>
            <option value={365}>1 год</option>
          </select>
          <button
            onClick={onRun}
            disabled={start.isPending || !config.data}
            className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
          >
            {start.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Запустить
          </button>
        </div>
      </header>

      {/* Active run */}
      {activeRunId !== null && (
        <section className="marble-card p-6">
          <div className="flex items-center justify-between">
            <h2 className="display text-xl font-semibold">Запуск #{activeRunId}</h2>
            <span className="text-xs uppercase tracking-wider text-muted-foreground">
              {progress?.stage ?? detail.data?.status ?? "—"}
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-hermes-parchment/60">
            <motion.div
              className="h-full bg-gradient-to-r from-hermes-gold-light via-hermes-gold to-hermes-gold-deep"
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            {isRunning && (
              <>
                {progress?.stage === "fetching" && progress?.symbol
                  ? `Загрузка данных: ${progress.symbol}`
                  : `Прогресс: ${pct}%`}
              </>
            )}
            {progress?.type === "complete" && "Завершено"}
            {progress?.type === "error" && (progress.message ?? "Ошибка")}
          </div>

          {detail.data?.status === "done" && detail.data.metrics && (
            <div className="mt-6 grid gap-3 md:grid-cols-3 lg:grid-cols-5">
              <Metric label="Доходность" value={fmtPct(metrics.total_return)} />
              <Metric label="Sharpe" value={fmtNum(metrics.sharpe_ratio, 2)} />
              <Metric label="Max DD" value={fmtPct(metrics.max_drawdown)} />
              <Metric label="Profit factor" value={fmtNum(metrics.profit_factor, 2)} />
              <Metric label="Сделок" value={fmtNum(metrics.trade_count, 0)} />
            </div>
          )}
        </section>
      )}

      {/* History */}
      <section className="marble-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-hermes-gold/20 px-5 py-3">
          <h2 className="display text-lg font-semibold">История прогонов</h2>
          <TestTube size={14} className="text-muted-foreground" />
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              <th className="px-5 py-2 text-left">ID</th>
              <th className="px-3 py-2 text-left">Статус</th>
              <th className="px-3 py-2 text-right">Sharpe</th>
              <th className="px-3 py-2 text-right">Доходность</th>
              <th className="px-3 py-2 text-right">Max DD</th>
              <th className="px-3 py-2 text-left">Запущен</th>
            </tr>
          </thead>
          <tbody>
            {(runs.data ?? []).map((r) => {
              const m = (r.metrics ?? {}) as Record<string, unknown>;
              return (
                <tr
                  key={r.id}
                  onClick={() => setActiveRunId(r.id)}
                  className="cursor-pointer border-t border-hermes-gold/15 hover:bg-hermes-parchment/30"
                >
                  <td className="px-5 py-2 font-mono text-xs">#{r.id}</td>
                  <td className="px-3 py-2">
                    <StatusPill status={r.status} />
                  </td>
                  <td className="px-3 py-2 text-right number">{fmtNum(m.sharpe_ratio, 2)}</td>
                  <td className="px-3 py-2 text-right number">{fmtPct(m.total_return)}</td>
                  <td className="px-3 py-2 text-right number">{fmtPct(m.max_drawdown)}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {r.started_at ? formatDateTime(r.started_at) : "—"}
                  </td>
                </tr>
              );
            })}
            {(runs.data ?? []).length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center font-serif italic text-muted-foreground">
                  Прогонов ещё не было.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </motion.div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-hermes-gold/30 bg-hermes-alabaster/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="number mt-1 text-base font-semibold">{value}</div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-hermes-parchment/60 text-muted-foreground",
    running: "bg-hermes-gold/15 text-hermes-gold-deep",
    done: "bg-hermes-laurel/15 text-hermes-laurel",
    error: "bg-hermes-wine/10 text-hermes-wine",
  };
  const labels: Record<string, string> = {
    pending: "ожидание",
    running: "идёт",
    done: "готово",
    error: "ошибка",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider ${map[status] ?? ""}`}>
      {labels[status] ?? status}
    </span>
  );
}

function fmtNum(v: unknown, decimals: number): string {
  const n = typeof v === "number" ? v : v != null ? Number(v) : NaN;
  return Number.isFinite(n) ? n.toFixed(decimals) : "—";
}

function fmtPct(v: unknown): string {
  const n = typeof v === "number" ? v : v != null ? Number(v) : NaN;
  if (!Number.isFinite(n)) return "—";
  // Heuristic: values > 5 are already in % units; <= 5 are fractions.
  return Math.abs(n) > 5 ? `${n.toFixed(1)}%` : `${(n * 100).toFixed(2)}%`;
}
