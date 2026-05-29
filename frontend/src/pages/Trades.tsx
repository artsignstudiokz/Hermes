import { motion, AnimatePresence } from "framer-motion";
import { Brain, ChevronDown, Download, Pencil, ShieldAlert, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { useTradeStats, useTrades, useUpdateTradeNotes } from "@/api/useTrades";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import { toast } from "@/lib/toast";
import type { Trade } from "@/api/types";

export function Trades() {
  const [days, setDays] = useState<number>(30);
  const [symbol, setSymbol] = useState<string>("");
  const [modeFilter, setModeFilter] = useState<string>("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const trades = useTrades({ days, symbol: symbol || undefined, limit: 500 });
  const stats = useTradeStats(days);
  const updateNotes = useUpdateTradeNotes();

  const filtered = useMemo(() => {
    let list = trades.data ?? [];
    if (modeFilter) list = list.filter((t) => t.mode === modeFilter);
    return list;
  }, [trades.data, modeFilter]);

  const symbols = useMemo(() => {
    const set = new Set((trades.data ?? []).map((t) => t.symbol));
    return Array.from(set).sort();
  }, [trades.data]);

  const exportCsv = () => {
    const rows = trades.data ?? [];
    const head = [
      "ticket", "symbol", "direction", "level", "lots",
      "entry_price", "exit_price", "pnl", "commission", "swap",
      "opened_at", "closed_at", "reason",
    ];
    const csv = [
      head.join(","),
      ...rows.map((t) => head.map((k) => JSON.stringify((t as unknown as Record<string, unknown>)[k] ?? "")).join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `hermes-trades-${days}d.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-8"
    >
      <header className="flex flex-col items-start justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Сделки</p>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">
            История <span className="gold-text">сделок</span>
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={exportCsv}
            className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2.5 text-sm font-medium hover:bg-hermes-parchment"
            title="CSV всех сделок текущего фильтра"
          >
            <Download size={14} /> Текущий период
          </button>
          <a
            href={`/api/trades/export.csv?year=${new Date().getFullYear()}`}
            download
            className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold-deep/50 bg-hermes-gold/10 px-4 py-2.5 text-sm font-semibold hover:bg-hermes-gold/20"
            title="Налоговый отчёт за текущий год — все закрытые сделки с net P&L"
          >
            <Download size={14} /> Налоговый ({new Date().getFullYear()})
          </a>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Сделок" value={String(stats.data?.total ?? 0)} />
        <Stat label="Win-rate" value={`${((stats.data?.win_rate ?? 0) * 100).toFixed(1)}%`} />
        <Stat label="P&L" value={formatMoney(stats.data?.pnl_total ?? 0)} accent="laurel" />
        <Stat label="Комиссия" value={formatMoney(stats.data?.commission_total ?? 0)} accent="bronze" />
      </section>

      <section className="marble-card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hermes-gold/20 px-5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="form-input"
            >
              <option value={7}>7 дней</option>
              <option value={30}>30 дней</option>
              <option value={90}>90 дней</option>
              <option value={365}>1 год</option>
            </select>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="form-input"
            >
              <option value="">Все символы</option>
              {symbols.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="form-input"
              title="Фильтр по режиму, открывшему сделку"
            >
              <option value="">Все режимы</option>
              <option value="proven">🛡 Проверенный</option>
              <option value="autonomous">🧠 Автономный</option>
              <option value="manual">✏ Ручные</option>
            </select>
          </div>
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            {filtered.length} строк
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <th className="w-8"></th>
                <th className="px-3 py-2 text-left">Режим</th>
                <th className="px-4 py-2 text-left">Тикет</th>
                <th className="px-3 py-2 text-left">Символ</th>
                <th className="px-3 py-2 text-left">Напр.</th>
                <th className="px-3 py-2 text-right">Лот</th>
                <th className="px-3 py-2 text-right">Вход</th>
                <th className="px-3 py-2 text-right">Выход</th>
                <th className="px-3 py-2 text-right">P&amp;L</th>
                <th className="px-3 py-2 text-left">Открыта</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => {
                const isOpen = expandedId === t.id;
                return (
                  <>
                    <tr
                      key={t.id}
                      onClick={() => setExpandedId(isOpen ? null : t.id)}
                      className={`cursor-pointer border-t border-hermes-gold/15 transition ${
                        isOpen ? "bg-hermes-gold/10" : "hover:bg-hermes-parchment/30"
                      }`}
                    >
                      <td className="px-2 text-muted-foreground">
                        <ChevronDown
                          size={14}
                          className="transition-transform"
                          style={{ transform: isOpen ? "rotate(180deg)" : "none" }}
                        />
                      </td>
                      <td className="px-3 py-2 text-xs"><ModePill mode={t.mode} /></td>
                      <td className="px-4 py-2 font-mono text-xs">{t.ticket}</td>
                      <td className="px-3 py-2 font-medium">{t.symbol}</td>
                      <td className="px-3 py-2 text-xs">
                        <span className={t.direction === "long" ? "text-hermes-laurel" : "text-hermes-wine"}>
                          {t.direction === "long" ? "Long" : "Short"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right number">{(t.lots ?? 0).toFixed(2)}</td>
                      <td className="px-3 py-2 text-right number">{(t.entry_price ?? 0).toFixed(5)}</td>
                      <td className="px-3 py-2 text-right number">
                        {t.exit_price != null ? t.exit_price.toFixed(5) : "—"}
                      </td>
                      <td
                        className={`px-3 py-2 text-right number ${
                          (t.pnl ?? 0) >= 0 ? "text-hermes-laurel" : "text-hermes-wine"
                        }`}
                      >
                        {formatMoney(t.pnl)}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {formatDateTime(t.opened_at)}
                      </td>
                    </tr>
                    <AnimatePresence>
                      {isOpen && (
                        <tr>
                          <td colSpan={10} className="bg-hermes-alabaster/60 px-6 py-4">
                            <TradeJournalEntry
                              trade={t}
                              onSave={async (notes) => {
                                try {
                                  await updateNotes.mutateAsync({ id: t.id, notes });
                                  toast.success("Заметка сохранена");
                                } catch (e) {
                                  const m = e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e);
                                  toast.error("Не сохранилось", m);
                                }
                              }}
                            />
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </>
                );
              })}
              {filtered.length === 0 && !trades.isLoading && (
                <tr>
                  <td colSpan={10} className="px-6 py-12 text-center font-serif italic text-muted-foreground">
                    Пока ни одной сделки. После запуска торговли они появятся здесь.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </motion.div>
  );
}


// ── Mode pill ────────────────────────────────────────────────────


function ModePill({ mode }: { mode: Trade["mode"] }) {
  const styles = {
    proven: {
      icon: ShieldAlert,
      label: "Проверенный",
      cls: "border-hermes-laurel/50 bg-hermes-laurel/10 text-hermes-laurel",
    },
    autonomous: {
      icon: Brain,
      label: "Автономный",
      cls: "border-hermes-gold/45 bg-hermes-gold/10 text-hermes-gold-deep",
    },
    manual: {
      icon: Sparkles,
      label: "Ручная",
      cls: "border-hermes-gold/25 bg-hermes-alabaster/70 text-muted-foreground",
    },
  } as const;
  const s = styles[mode] ?? styles.manual;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${s.cls}`}>
      <Icon size={10} />
      {s.label}
    </span>
  );
}


// ── Trade journal entry (expanded row) ───────────────────────────


function TradeJournalEntry({
  trade,
  onSave,
}: {
  trade: Trade;
  onSave: (notes: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState(trade.notes ?? "");
  const [editing, setEditing] = useState(false);
  const dirty = (draft || "") !== (trade.notes ?? "");

  const handleSave = async () => {
    await onSave(draft);
    setEditing(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="grid gap-6 lg:grid-cols-[1fr_1fr]"
    >
      {/* Bot's reasoning */}
      <div>
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-hermes-gold-deep font-semibold">
          <Brain size={12} /> Почему бот вошёл
        </div>
        {trade.signal_reason ? (
          <div className="mt-2 rounded-xl border border-hermes-gold/30 bg-hermes-alabaster/80 p-3 text-sm whitespace-pre-line leading-relaxed text-foreground/85">
            {trade.signal_reason}
          </div>
        ) : (
          <div className="mt-2 rounded-xl border border-dashed border-hermes-gold/25 bg-hermes-alabaster/40 p-3 text-xs italic text-muted-foreground">
            {trade.mode === "manual"
              ? "Ручной вход — оператор открыл напрямую через «Тест-сделка» или «Анализ»."
              : "Обоснование сигнала недоступно (сделка из ранней версии бота)."}
          </div>
        )}

        {/* Meta line */}
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
          <span><strong className="text-foreground">Причина закрытия:</strong> {trade.reason || "—"}</span>
          {trade.closed_at && (
            <span><strong className="text-foreground">Закрыта:</strong> {formatDateTime(trade.closed_at)}</span>
          )}
          <span><strong className="text-foreground">Комиссия:</strong> {formatMoney(trade.commission)}</span>
          <span><strong className="text-foreground">Своп:</strong> {formatMoney(trade.swap)}</span>
        </div>
      </div>

      {/* Operator notes */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-hermes-gold-deep font-semibold">
            <Pencil size={12} /> Заметки оператора
          </div>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="text-[11px] text-hermes-gold-deep hover:underline"
            >
              {trade.notes ? "Изменить" : "Добавить"}
            </button>
          )}
        </div>
        {editing ? (
          <div className="mt-2 space-y-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={5}
              placeholder="Что заметили? Почему оставили / закрыли? Что улучшить в правилах?"
              className="form-input w-full font-sans text-sm leading-relaxed"
              maxLength={4000}
              autoFocus
            />
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">{draft.length}/4000</span>
              <div className="flex gap-2">
                <button
                  onClick={() => { setDraft(trade.notes ?? ""); setEditing(false); }}
                  className="rounded px-2 py-1 text-muted-foreground hover:text-foreground"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSave}
                  disabled={!dirty}
                  className="gold-button rounded-lg px-3 py-1 font-semibold disabled:opacity-50"
                >
                  Сохранить
                </button>
              </div>
            </div>
          </div>
        ) : trade.notes ? (
          <div className="mt-2 rounded-xl border border-hermes-gold/30 bg-hermes-alabaster/80 p-3 text-sm whitespace-pre-line leading-relaxed">
            {trade.notes}
          </div>
        ) : (
          <div className="mt-2 rounded-xl border border-dashed border-hermes-gold/25 bg-hermes-alabaster/40 p-3 text-xs italic text-muted-foreground">
            Заметок нет. Запишите свои наблюдения по этой сделке — они помогут оптимизировать
            стратегию.
          </div>
        )}
      </div>
    </motion.div>
  );
}


function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "laurel" | "bronze";
}) {
  const tone = accent === "laurel"
    ? "text-hermes-laurel"
    : accent === "bronze"
    ? "text-hermes-bronze"
    : "";
  return (
    <div className="marble-card p-5">
      <span className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <div className={`mt-2 number text-2xl font-semibold ${tone}`}>{value}</div>
    </div>
  );
}
