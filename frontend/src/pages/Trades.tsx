import { motion } from "framer-motion";
import { Download } from "lucide-react";
import { useMemo, useState } from "react";

import { useTradeStats, useTrades } from "@/api/useTrades";
import { formatDateTime, formatMoney } from "@/lib/format";

export function Trades() {
  const [days, setDays] = useState<number>(30);
  const [symbol, setSymbol] = useState<string>("");
  const trades = useTrades({ days, symbol: symbol || undefined, limit: 500 });
  const stats = useTradeStats(days);

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
      ...rows.map((t) => head.map((k) => JSON.stringify((t as Record<string, unknown>)[k] ?? "")).join(",")),
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
        <button
          onClick={exportCsv}
          className="inline-flex items-center gap-2 rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2.5 text-sm font-medium hover:bg-hermes-parchment"
        >
          <Download size={14} /> Скачать CSV
        </button>
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
          </div>
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            {trades.data?.length ?? 0} строк
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <th className="px-4 py-2 text-left">Тикет</th>
                <th className="px-3 py-2 text-left">Символ</th>
                <th className="px-3 py-2 text-left">Напр.</th>
                <th className="px-3 py-2 text-right">Лот</th>
                <th className="px-3 py-2 text-right">Вход</th>
                <th className="px-3 py-2 text-right">Выход</th>
                <th className="px-3 py-2 text-right">P&amp;L</th>
                <th className="px-3 py-2 text-left">Открыта</th>
                <th className="px-3 py-2 text-left">Причина</th>
              </tr>
            </thead>
            <tbody>
              {(trades.data ?? []).map((t) => (
                <tr
                  key={t.id}
                  className="border-t border-hermes-gold/15 hover:bg-hermes-parchment/30"
                >
                  <td className="px-4 py-2 font-mono text-xs">{t.ticket}</td>
                  <td className="px-3 py-2 font-medium">{t.symbol}</td>
                  <td className="px-3 py-2 text-xs">
                    <span className={t.direction === "long" ? "text-hermes-laurel" : "text-hermes-wine"}>
                      {t.direction === "long" ? "Long" : "Short"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right number">{t.lots.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right number">{t.entry_price.toFixed(5)}</td>
                  <td className="px-3 py-2 text-right number">
                    {t.exit_price ? t.exit_price.toFixed(5) : "—"}
                  </td>
                  <td
                    className={`px-3 py-2 text-right number ${
                      t.pnl >= 0 ? "text-hermes-laurel" : "text-hermes-wine"
                    }`}
                  >
                    {formatMoney(t.pnl)}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {formatDateTime(t.opened_at)}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{t.reason || "—"}</td>
                </tr>
              ))}
              {(trades.data ?? []).length === 0 && !trades.isLoading && (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center font-serif italic text-muted-foreground">
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
