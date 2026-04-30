import { ChevronLeft, ChevronRight, Loader2, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

import { useBrokers, useActivateBroker } from "@/api/useBrokers";
import { useStrategyConfig } from "@/api/useStrategy";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

interface Props {
  onPrev: () => void;
  onDone: () => void;
}

export function Step3Review({ onPrev, onDone }: Props) {
  const brokers = useBrokers();
  const config = useStrategyConfig();
  const activate = useActivateBroker();

  const broker = brokers.data?.[0];
  // We only activate the broker here — we do NOT auto-start trading.
  // User makes the explicit decision to begin live trading from the
  // Dashboard "Запустить" button after they've reviewed the state.
  const launch = async () => {
    if (!broker) {
      toast.error("Брокер не настроен", "Вернитесь на шаг 1 и подключите счёт.");
      return;
    }
    try {
      if (!broker.is_active) await activate.mutateAsync(broker.id);
      toast.success("Готов к запуску", "Откроется панель — нажмите «Запустить», когда будете готовы.");
      onDone();
    } catch (err) {
      const detail = err instanceof ApiError
        ? `${err.status}: ${err.message}`
        : err instanceof Error ? err.message : String(err);
      toast.error("Не удалось активировать", detail);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="display text-3xl font-semibold gold-text">Всё готово</h2>
        <p className="mt-2 font-serif italic text-muted-foreground">
          Брокер подключён, стратегия выбрана. На следующем шаге откроется панель — там
          вы сами решите, когда дать Гермесу начать торговать.
        </p>
      </div>

      <div className="space-y-3">
        <ReviewRow
          label="Брокер"
          value={broker ? `${broker.name} (${broker.type.toUpperCase()})` : "—"}
          extra={broker?.server ?? broker?.login ?? undefined}
        />
        <ReviewRow
          label="Стратегия"
          value={config.data?.name ?? "—"}
          extra={
            config.data
              ? `TP ${config.data.payload.fix_take_profit_pct}% · stop ${config.data.payload.stop_drawdown_pct}% · ${config.data.payload.max_grid_levels} уровней`
              : undefined
          }
        />
        <ReviewRow
          label="Пары"
          value={(config.data?.payload.symbols ?? []).join(", ") || "—"}
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="marble-card p-4 text-sm text-muted-foreground"
      >
        <div className="flex items-start gap-2">
          <Sparkles size={16} className="mt-0.5 text-hermes-gold-deep" />
          <p>
            Когда нажмёте «Запустить» на панели, Гермес начнёт постоянно анализировать рынок:
            сам открывает сделки, когда срабатывают сигналы стратегии, и сам закрывает их
            по тейк-профиту / стоп-лоссу / просадке. Все открытые позиции на брокере он
            подхватит сразу, история сделок ведётся непрерывно.
          </p>
        </div>
      </motion.div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button
          onClick={onPrev}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft size={14} /> Назад
        </button>
        <button
          onClick={launch}
          disabled={!broker || activate.isPending}
          className="gold-button inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
        >
          {activate.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ChevronRight size={14} />
          )}
          Открыть панель
        </button>
      </div>
    </div>
  );
}

function ReviewRow({
  label,
  value,
  extra,
}: {
  label: string;
  value: string;
  extra?: string;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-hermes-gold/15 py-2">
      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="text-right">
        <div className="font-medium">{value}</div>
        {extra && <div className="mt-0.5 text-xs text-muted-foreground">{extra}</div>}
      </div>
    </div>
  );
}
