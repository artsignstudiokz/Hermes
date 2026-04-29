import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Play, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useApplyOptimize, useStartOptimize } from "@/api/useOptimize";
import { useStrategyConfig } from "@/api/useStrategy";
import { subscribe } from "@/lib/ws";

interface TrialEvent {
  type: string;
  trial?: number;
  value?: number | null;
  params?: Record<string, number>;
  best_value?: number;
  best_params?: Record<string, number>;
  message?: string;
}

interface Trial {
  trial: number;
  value: number;
  params: Record<string, number>;
}

export function Optimize() {
  const config = useStrategyConfig();
  const start = useStartOptimize();
  const apply = useApplyOptimize();
  const [trials, setTrials] = useState<Trial[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [bestValue, setBestValue] = useState<number | null>(null);
  const [bestParams, setBestParams] = useState<Record<string, number> | null>(null);
  const [n, setN] = useState(60);
  const [days, setDays] = useState(90);
  const [done, setDone] = useState(false);
  const [applied, setApplied] = useState(false);

  useEffect(() => {
    if (activeRunId === null) return;
    setTrials([]);
    setDone(false);
    setApplied(false);
    setBestValue(null);
    setBestParams(null);
    const unsub = subscribe<TrialEvent>(`optimize_${activeRunId}` as never, (e) => {
      if (e.type === "trial" && typeof e.trial === "number" && typeof e.value === "number") {
        setTrials((prev) => [
          ...prev,
          { trial: e.trial!, value: e.value as number, params: e.params ?? {} },
        ]);
      }
      if (e.type === "complete") {
        setDone(true);
        setBestValue(e.best_value ?? null);
        setBestParams((e.best_params as Record<string, number>) ?? null);
      }
    });
    return unsub;
  }, [activeRunId]);

  const sorted = useMemo(
    () => [...trials].sort((a, b) => b.value - a.value).slice(0, 25),
    [trials],
  );
  const currentBest = bestValue ?? (trials.length ? Math.max(...trials.map((t) => t.value)) : null);

  const onRun = async () => {
    if (!config.data) return;
    const { run_id } = await start.mutateAsync({
      base_params: config.data.payload as unknown as Record<string, unknown>,
      symbols: config.data.payload.symbols,
      n_trials: n,
      days,
    });
    setActiveRunId(run_id);
  };

  const onApply = async () => {
    if (activeRunId === null) return;
    await apply.mutateAsync(activeRunId);
    setApplied(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Оптимизация</p>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
            Поиск <span className="gold-text">лучших параметров</span>
          </h1>
          <p className="mt-1 max-w-2xl font-serif italic text-muted-foreground">
            Optuna перебирает параметры стратегии. После завершения можно одной кнопкой
            применить лучший набор.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="form-input">
            <option value={60}>60 дней</option>
            <option value={90}>90 дней</option>
            <option value={180}>180 дней</option>
          </select>
          <select value={n} onChange={(e) => setN(Number(e.target.value))} className="form-input">
            <option value={30}>30 trials</option>
            <option value={60}>60 trials</option>
            <option value={100}>100 trials</option>
            <option value={200}>200 trials</option>
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

      {activeRunId !== null && (
        <section className="grid gap-6 lg:grid-cols-[1fr_2fr]">
          <div className="marble-card p-5">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">Прогресс</div>
            <div className="number mt-2 text-3xl font-semibold">
              {trials.length}/{n}
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-hermes-parchment/60">
              <motion.div
                className="h-full bg-gradient-to-r from-hermes-gold-light via-hermes-gold to-hermes-gold-deep"
                animate={{ width: `${Math.round((trials.length / n) * 100)}%` }}
                transition={{ duration: 0.25 }}
              />
            </div>
            <div className="mt-5 grid gap-2">
              <div className="flex items-baseline justify-between text-xs">
                <span className="uppercase tracking-wider text-muted-foreground">Лучший Sharpe</span>
                <span className="number text-lg font-semibold gold-text">
                  {currentBest !== null ? currentBest.toFixed(2) : "—"}
                </span>
              </div>
            </div>
            {done && (
              <button
                onClick={onApply}
                disabled={apply.isPending || applied}
                className="gold-button mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
              >
                {apply.isPending && <Loader2 size={14} className="animate-spin" />}
                {applied ? <CheckCircle2 size={14} /> : <Sparkles size={14} />}
                {applied ? "Применено" : "Применить лучшие параметры"}
              </button>
            )}
          </div>

          <div className="marble-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-hermes-gold/20 px-5 py-3">
              <h2 className="display text-lg font-semibold">Лучшие пробы</h2>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                top 25 / {trials.length}
              </span>
            </div>
            <div className="max-h-[460px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-hermes-alabaster/95">
                  <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    <th className="px-4 py-2 text-left">#</th>
                    <th className="px-3 py-2 text-right">Sharpe</th>
                    <th className="px-3 py-2 text-right">grid pips</th>
                    <th className="px-3 py-2 text-right">lot mult</th>
                    <th className="px-3 py-2 text-right">levels</th>
                    <th className="px-3 py-2 text-right">TP %</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((t) => (
                    <tr key={t.trial} className="border-t border-hermes-gold/15">
                      <td className="px-4 py-2 font-mono text-xs">{t.trial}</td>
                      <td className="px-3 py-2 text-right number font-semibold gold-text">
                        {t.value.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-right number">
                        {t.params.base_grid_distance_pips?.toFixed(1) ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right number">
                        {t.params.lot_multiplier?.toFixed(2) ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right number">
                        {t.params.max_grid_levels ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right number">
                        {t.params.fix_take_profit_pct?.toFixed(1) ?? "—"}
                      </td>
                    </tr>
                  ))}
                  {sorted.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center font-serif italic text-muted-foreground">
                        Ожидание первых результатов…
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {activeRunId !== null && bestParams && done && (
        <section className="marble-card p-5">
          <h2 className="display text-lg font-semibold">Лучший набор параметров</h2>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-hermes-alabaster/60 p-4 font-mono text-xs">
            {JSON.stringify(bestParams, null, 2)}
          </pre>
        </section>
      )}
    </motion.div>
  );
}
