import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useState } from "react";

import { usePresets, useSaveStrategy } from "@/api/useStrategy";
import type { Preset, StrategyParams } from "@/api/types";
import { ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

interface Props {
  onPrev: () => void;
  onNext: () => void;
}

const DEFAULTS: StrategyParams = {
  base_grid_distance_pips: 30,
  grid_distance_multiplier: 1.4,
  base_lot_size: 0.01,
  lot_multiplier: 1.3,
  max_grid_levels: 6,
  fix_take_profit_pct: 2.0,
  stop_drawdown_pct: 10,
  max_portfolio_drawdown_pct: 20,
  trend_filter_enabled: true,
  ema_fast: 50,
  ema_slow: 200,
  session_filter_enabled: true,
  risk_per_trade_pct: 1.0,
  max_simultaneous_pairs: 5,
  symbols: ["EURUSD", "GBPUSD", "EURCHF", "EURJPY", "USDCHF", "USDJPY"],
  timeframe: "1h",
};

export function Step2Strategy({ onPrev, onNext }: Props) {
  const presets = usePresets();
  const save = useSaveStrategy();
  const [chosen, setChosen] = useState<string>("balanced");

  const onPick = (preset: Preset) => {
    setChosen(preset.id);
  };

  const onContinue = async () => {
    const preset = presets.data?.find((p) => p.id === chosen);
    if (!preset) return;
    try {
      await save.mutateAsync({ ...DEFAULTS, ...(preset.payload as Partial<StrategyParams>) } as StrategyParams);
      onNext();
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : err instanceof Error ? err.message : String(err);
      toast.error("Не удалось сохранить стратегию", detail);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="display text-3xl font-semibold gold-text">Выберите стиль торговли</h2>
        <p className="mt-2 font-serif italic text-muted-foreground">
          Можно поменять позже на странице «Стратегия». Auto — Hermes сам подберёт под рынок.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {(presets.data ?? []).map((p) => (
          <button
            key={p.id}
            onClick={() => onPick(p)}
            className={`marble-card text-left p-5 transition ${
              chosen === p.id
                ? "ring-2 ring-hermes-gold-deep shadow-gold"
                : "hover:-translate-y-0.5 hover:shadow-marble"
            }`}
          >
            <div className="flex items-baseline justify-between">
              <span className="text-2xl">{p.risk_emoji}</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                {p.id}
              </span>
            </div>
            <div className="display mt-2 text-lg font-semibold">{p.name}</div>
            <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button
          onClick={onPrev}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft size={14} /> Назад
        </button>
        <button
          onClick={onContinue}
          disabled={save.isPending}
          className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
        >
          {save.isPending && <Loader2 size={14} className="animate-spin" />}
          Применить и далее <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
