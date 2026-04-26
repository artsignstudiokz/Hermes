import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  usePresets,
  useSaveStrategy,
  useStrategyConfig,
  useValidateStrategy,
} from "@/api/useStrategy";
import type { StrategyParams } from "@/api/types";

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

export function Strategy() {
  const presets = usePresets();
  const config = useStrategyConfig();
  const save = useSaveStrategy();
  const validate = useValidateStrategy();
  const [params, setParams] = useState<StrategyParams>(DEFAULTS);
  const [chosenPreset, setChosenPreset] = useState<string | null>(null);
  const [name, setName] = useState("Custom");

  // Hydrate from existing active config.
  useEffect(() => {
    if (config.data?.payload) {
      setParams({ ...DEFAULTS, ...config.data.payload });
      setName(config.data.name);
    }
  }, [config.data]);

  // Validate on every change (debounced).
  useEffect(() => {
    const t = setTimeout(() => {
      validate.mutate(params);
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const issues = validate.data?.issues ?? [];
  const hasErrors = validate.data?.has_errors ?? false;

  const choosePreset = (presetId: string) => {
    const p = presets.data?.find((pp) => pp.id === presetId);
    if (!p) return;
    setChosenPreset(presetId);
    setParams({ ...params, ...p.payload } as StrategyParams);
    setName(p.name);
  };

  const onSave = async () => {
    await save.mutateAsync(params);
  };

  const issueByField = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const i of issues) {
      (map[i.field] ??= []).push(i.message);
    }
    return map;
  }, [issues]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header>
        <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Стратегия</p>
        <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
          Настройки <span className="gold-text">сетки</span>
        </h1>
        <p className="mt-2 max-w-2xl font-serif italic text-muted-foreground">
          Выберите пресет или настройте под себя. Hermes проверит безопасность параметров перед
          сохранением.
        </p>
      </header>

      {/* Presets */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {(presets.data ?? []).map((p) => (
          <button
            key={p.id}
            onClick={() => choosePreset(p.id)}
            className={`marble-card p-5 text-left transition ${
              chosenPreset === p.id || name === p.name
                ? "ring-2 ring-hermes-gold-deep shadow-gold"
                : "hover:-translate-y-0.5 hover:shadow-marble"
            }`}
          >
            <div className="text-2xl">{p.risk_emoji}</div>
            <div className="display mt-2 text-lg font-semibold">{p.name}</div>
            <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
          </button>
        ))}
      </section>

      {/* Parameters */}
      <section className="marble-card p-6">
        <h2 className="display text-xl font-semibold">Параметры</h2>

        <div className="mt-4 grid gap-5 md:grid-cols-2">
          <Slider
            label="Расстояние между ордерами (пипс)"
            value={params.base_grid_distance_pips}
            min={5}
            max={100}
            step={1}
            onChange={(v) => setParams({ ...params, base_grid_distance_pips: v })}
            issues={issueByField.base_grid_distance_pips}
          />
          <Slider
            label="Множитель лота"
            value={params.lot_multiplier}
            min={1}
            max={2.5}
            step={0.05}
            onChange={(v) => setParams({ ...params, lot_multiplier: v })}
            issues={issueByField.lot_multiplier}
          />
          <Slider
            label="Базовый лот"
            value={params.base_lot_size}
            min={0.01}
            max={1}
            step={0.01}
            onChange={(v) => setParams({ ...params, base_lot_size: v })}
            issues={issueByField.base_lot_size}
            decimals={2}
          />
          <Slider
            label="Уровней сетки"
            value={params.max_grid_levels}
            min={1}
            max={12}
            step={1}
            onChange={(v) => setParams({ ...params, max_grid_levels: Math.round(v) })}
            issues={issueByField.max_grid_levels}
          />
          <Slider
            label="Take Profit (%)"
            value={params.fix_take_profit_pct}
            min={0.5}
            max={10}
            step={0.1}
            onChange={(v) => setParams({ ...params, fix_take_profit_pct: v })}
            issues={issueByField.fix_take_profit_pct}
            decimals={1}
          />
          <Slider
            label="Stop drawdown (%)"
            value={params.stop_drawdown_pct}
            min={1}
            max={30}
            step={0.5}
            onChange={(v) => setParams({ ...params, stop_drawdown_pct: v })}
            issues={issueByField.stop_drawdown_pct}
            decimals={1}
          />
          <Slider
            label="Max просадка портфеля (%)"
            value={params.max_portfolio_drawdown_pct}
            min={5}
            max={50}
            step={1}
            onChange={(v) => setParams({ ...params, max_portfolio_drawdown_pct: v })}
            issues={issueByField.max_portfolio_drawdown_pct}
          />
          <Slider
            label="Риск на сделку (%)"
            value={params.risk_per_trade_pct}
            min={0.1}
            max={5}
            step={0.1}
            onChange={(v) => setParams({ ...params, risk_per_trade_pct: v })}
            issues={issueByField.risk_per_trade_pct}
            decimals={1}
          />
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={onSave}
            disabled={hasErrors || save.isPending}
            className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider disabled:opacity-50"
          >
            {save.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            Сохранить и активировать
          </button>
          {save.isSuccess && (
            <span className="inline-flex items-center gap-1 text-xs text-hermes-laurel">
              <CheckCircle2 size={12} /> Сохранено
            </span>
          )}
        </div>

        {issues.length > 0 && (
          <div className="mt-5 space-y-2">
            {issues.map((i, idx) => (
              <div
                key={idx}
                className={`rounded-xl border px-4 py-2 text-sm ${
                  i.severity === "error"
                    ? "border-hermes-wine/40 bg-hermes-wine/10 text-hermes-wine"
                    : "border-hermes-bronze/40 bg-hermes-bronze/10 text-hermes-bronze"
                }`}
              >
                <span className="font-semibold mr-2">{i.field}:</span>
                {i.message}
              </div>
            ))}
          </div>
        )}
      </section>
    </motion.div>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  decimals = 0,
  onChange,
  issues,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  decimals?: number;
  onChange: (v: number) => void;
  issues?: string[];
}) {
  const hasError = issues && issues.length > 0;
  return (
    <label className="block">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="number text-sm font-semibold">
          {value.toFixed(decimals)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={`w-full accent-hermes-gold-deep ${hasError ? "outline outline-hermes-wine/40" : ""}`}
      />
    </label>
  );
}
