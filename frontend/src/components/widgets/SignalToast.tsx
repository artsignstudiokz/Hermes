import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Bell, X } from "lucide-react";

import { subscribe } from "@/lib/ws";

interface SignalEvent {
  type: string;
  symbol?: string;
  direction?: string;
  level?: number;
  lots?: number;
  lot_size?: number;
  price?: number;
  pnl?: number;
  reason?: string;
  ts?: string;
  message?: string;
  closed_count?: number;
  mode?: string;
  confidence?: number;
  trades_today?: number;
}

interface ToastEntry extends SignalEvent {
  id: number;
}

let nextId = 1;

/** Top-right stack of live signal toasts pushed via /ws/signals. */
export function SignalToasts() {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  useEffect(() => {
    // v1.0.41: only surface user-visible events. The legacy grid
    // strategy still runs in dry_run mode every tick (it powers the
    // indicator panel) and emits internal "open" / "close_basket"
    // actions over /ws/signals. Those were misleading the user into
    // thinking sales/buys at 0.1 lot were happening on real money -
    // they weren't. Real broker fills come in as type="trade_opened".
    const VISIBLE = new Set([
      "trade_opened",
      "kill_switch",
      "broker_down",
      "risk_block",
      "error",
    ]);
    return subscribe<SignalEvent>("signals", (event) => {
      if (!VISIBLE.has(event.type)) return;
      const id = nextId++;
      setToasts((prev) => [...prev.slice(-3), { ...event, id }]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 6000);
    });
  }, []);

  return (
    <div className="pointer-events-none fixed right-4 top-14 z-40 flex w-80 flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto marble-card flex items-start gap-3 p-3 shadow-marble"
          >
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-hermes-gold/15 text-hermes-gold-deep">
              {t.type === "open" ? (
                t.direction === "long" ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />
              ) : t.type === "kill_switch" || t.type === "error" ? (
                <X size={14} />
              ) : (
                <Bell size={14} />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <div className="display text-sm font-semibold">
                {labelFor(t)}
              </div>
              <div className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                {detailFor(t)}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function labelFor(t: SignalEvent): string {
  if (t.type === "trade_opened") return `Сделка открыта · ${t.symbol}`;
  if (t.type === "kill_switch") return "Аварийная остановка";
  if (t.type === "broker_down") return "Брокер недоступен";
  if (t.type === "risk_block") return "Риск-фильтр заблокировал вход";
  if (t.type === "error") return "Ошибка стратегии";
  return t.type;
}

function detailFor(t: SignalEvent): string {
  if (t.type === "trade_opened") {
    const dir = t.direction === "long" ? "Покупка" : "Продажа";
    const conf = t.confidence != null ? ` · уверенность ${t.confidence.toFixed(2)}` : "";
    return `${dir}${conf} · режим ${t.mode ?? "-"}`;
  }
  if (t.type === "kill_switch") return `Закрыто позиций: ${t.closed_count ?? 0}`;
  if (t.type === "broker_down") return t.reason ?? "MT5 не отвечает на health-probe.";
  if (t.type === "risk_block") return `${t.symbol ?? ""}: ${t.reason ?? "блокировка риска"}`;
  if (t.type === "error") return t.message ?? "-";
  return "";
}
