/**
 * Adaptive - manual triggers + history for the walk-forward calibration
 * loop. Operator can:
 *   • see the live regime per pair
 *   • kick off an out-of-cycle calibration (the scheduler also runs
 *     this weekly on its own)
 *   • inspect every past run with champion vs challenger params and
 *     the walk-forward score
 *   • rollback to the previous strategy config if the latest applied
 *     calibration is making things worse
 */

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, ChevronRight, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { useState } from "react";

import {
  type CalibrationRun,
  useCalibrationRuns,
  useRegime,
  useRollbackCalibration,
  useRunCalibrationNow,
} from "@/api/useAdaptive";
import { RegimeBadge } from "@/components/charts/RegimeBadge";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

export function Adaptive() {
  const regime = useRegime();
  const runs = useCalibrationRuns(50);
  const runNow = useRunCalibrationNow();
  const rollback = useRollbackCalibration();
  const [selected, setSelected] = useState<CalibrationRun | null>(null);

  const onRunNow = async () => {
    try {
      await runNow.mutateAsync();
      toast.success("Калибровка запущена", "Это занимает 30-60 секунд. Результат появится в истории.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Не удалось запустить", msg);
    }
  };

  const onRollback = async () => {
    if (!window.confirm("Откатиться к предыдущей конфигурации? Это применит параметры, которые работали до последней калибровки.")) return;
    try {
      const r = await rollback.mutateAsync();
      if (r.ok) toast.success("Откат выполнен", "Активирована предыдущая конфигурация.");
      else toast.error("Откат не удался", "Нет предыдущей конфигурации для отката.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Ошибка отката", msg);
    }
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
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Адаптация</p>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
            Walk-forward <span className="gold-text">калибровка</span>
          </h1>
          <p className="mt-2 max-w-2xl font-serif italic text-muted-foreground">
            Каждое воскресенье Hermes автоматически переподбирает параметры стратегии на свежих данных
            (90 дней OHLCV, разделение 70/30, Optuna 100 trials). Применяет новые только если они
            обогнали текущие на out-of-sample.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onRunNow}
            disabled={runNow.isPending}
            className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
          >
            {runNow.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            Запустить сейчас
          </button>
          <button
            onClick={onRollback}
            disabled={rollback.isPending}
            className="inline-flex items-center gap-2 rounded-xl border border-hermes-wine/40 bg-hermes-wine/10 px-4 py-2.5 text-sm font-medium text-hermes-wine hover:bg-hermes-wine/20 transition disabled:opacity-50"
          >
            {rollback.isPending ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
            Откатить
          </button>
        </div>
      </header>

      {/* Current regime */}
      <section className="marble-card p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="display text-xl font-semibold">Текущий режим</h2>
          <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            обновляется каждые 5 мин
          </span>
        </div>
        {regime.data ? (
          <div className="mt-4 space-y-4">
            <div className="flex items-center gap-3">
              <RegimeBadge regime={regime.data.regime} />
              <span className="text-xs text-muted-foreground">
                {Object.entries(regime.data.counts ?? {})
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" · ")}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {regime.data.per_pair.map((p) => (
                <RegimeBadge
                  key={p.symbol}
                  regime={p.regime}
                  symbol={p.symbol}
                  confidence={p.confidence}
                />
              ))}
            </div>
          </div>
        ) : regime.isError ? (
          <p className="mt-4 text-sm text-muted-foreground">
            Брокер не активен - режим определяется по живым данным OHLCV. Подключи брокера на странице
            «Брокеры».
          </p>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">Загружаю…</p>
        )}
      </section>

      {/* Calibration history */}
      <section className="marble-card overflow-hidden">
        <div className="flex items-baseline justify-between border-b border-hermes-gold/20 px-5 py-3">
          <h2 className="display text-lg font-semibold">История калибровок</h2>
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {runs.data?.length ?? 0} записей
          </span>
        </div>
        {runs.isLoading && (
          <div className="grid h-32 place-items-center text-sm text-muted-foreground">Загружаю…</div>
        )}
        {runs.data && runs.data.length === 0 && (
          <div className="grid place-items-center px-6 py-12 text-center">
            <p className="font-serif italic text-muted-foreground">
              Калибровок ещё не было. Hermes запустит первую в ближайшее воскресенье,
              или нажми «Запустить сейчас».
            </p>
          </div>
        )}
        {runs.data && runs.data.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <th className="px-5 py-2 text-left">Дата</th>
                <th className="px-3 py-2 text-left">Режим</th>
                <th className="px-3 py-2 text-right">Score</th>
                <th className="px-3 py-2 text-center">Challenger</th>
                <th className="px-3 py-2 text-center">Применено</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {runs.data.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className={`cursor-pointer border-t border-hermes-gold/15 hover:bg-hermes-parchment/30 transition ${
                    selected?.id === r.id ? "bg-hermes-gold/10" : ""
                  }`}
                >
                  <td className="px-5 py-3 text-xs font-mono">{r.ts.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-3 py-3 text-xs">{r.regime}</td>
                  <td className="px-3 py-3 text-right number">{r.walk_forward_score.toFixed(3)}</td>
                  <td className="px-3 py-3 text-center">
                    {r.challenger_won ? (
                      <span className="inline-flex items-center gap-1 text-xs text-hermes-laurel">
                        <CheckCircle2 size={12} /> выиграл
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">не лучше</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-center">
                    {r.applied ? (
                      <span className="inline-flex items-center gap-1 text-xs text-hermes-laurel">
                        <CheckCircle2 size={12} /> да
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-hermes-bronze">
                        <AlertTriangle size={12} /> нет
                      </span>
                    )}
                  </td>
                  <td className="pr-3 text-muted-foreground">
                    <ChevronRight size={14} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Detail diff */}
      {selected && (
        <section className="marble-card p-6">
          <div className="flex items-baseline justify-between">
            <h2 className="display text-lg font-semibold">
              Run #{selected.id} ·{" "}
              <span className="font-mono text-sm font-normal text-muted-foreground">
                {selected.ts.slice(0, 19).replace("T", " ")}
              </span>
            </h2>
            <button
              onClick={() => setSelected(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              ×
            </button>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {selected.applied
              ? "Этот челленджер применён - параметры активной стратегии заменены."
              : selected.challenger_won
              ? "Челленджер показал лучший score, но не прошёл safety-проверку (min trades / max-DD). Не применён."
              : "Челленджер не обогнал текущие параметры. Применение пропущено."}
          </p>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <ParamColumn title="Было" data={selected.before_params} />
            <ParamColumn title="Стало" data={selected.after_params} diffWith={selected.before_params} />
          </div>
        </section>
      )}
    </motion.div>
  );
}

function ParamColumn({
  title,
  data,
  diffWith,
}: {
  title: string;
  data: Record<string, unknown>;
  diffWith?: Record<string, unknown>;
}) {
  const keys = Object.keys(data).sort();
  return (
    <div className="rounded-xl border border-hermes-gold/25 bg-hermes-alabaster/60 p-4">
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
      <div className="mt-3 space-y-1.5">
        {keys.map((k) => {
          const v = data[k];
          const changed = diffWith ? JSON.stringify(diffWith[k]) !== JSON.stringify(v) : false;
          return (
            <div
              key={k}
              className={`flex items-baseline justify-between gap-2 rounded px-2 py-1 text-xs ${
                changed ? "bg-hermes-gold/15" : ""
              }`}
            >
              <span className="font-mono text-muted-foreground">{k}</span>
              <span className={`font-mono ${changed ? "font-semibold text-hermes-gold-deep" : ""}`}>
                {formatValue(v)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") return v.toString();
  if (typeof v === "boolean") return v ? "true" : "false";
  if (Array.isArray(v)) return `[${v.length}]`;
  if (typeof v === "object") return "{…}";
  return String(v);
}
