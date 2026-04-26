import { motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, X } from "lucide-react";
import { useState } from "react";

import { closePosition } from "@/api/usePositions";
import { formatDateTime, formatMoney } from "@/lib/format";
import type { Position } from "@/api/types";

interface Props {
  positions: Position[];
  loading?: boolean;
}

export function PositionsTable({ positions, loading }: Props) {
  const [closing, setClosing] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="grid h-32 place-items-center text-sm text-muted-foreground">
        Загружаю позиции…
      </div>
    );
  }
  if (!positions.length) {
    return (
      <div className="grid place-items-center px-6 py-12 text-center">
        <p className="font-serif italic text-muted-foreground">
          Hermes пока наблюдает. Ни одной открытой сделки.
        </p>
      </div>
    );
  }

  const handleClose = async (ticket: string) => {
    setClosing(ticket);
    try {
      await closePosition(ticket);
    } finally {
      setClosing(null);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            <th className="px-5 py-2 text-left">Символ</th>
            <th className="px-3 py-2 text-left">Направление</th>
            <th className="px-3 py-2 text-right">Лот</th>
            <th className="px-3 py-2 text-right">Цена входа</th>
            <th className="px-3 py-2 text-right">Сейчас</th>
            <th className="px-3 py-2 text-right">P&amp;L</th>
            <th className="px-3 py-2 text-left">Открыта</th>
            <th className="px-2 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <motion.tr
              key={p.ticket}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="border-t border-hermes-gold/15 hover:bg-hermes-parchment/30"
            >
              <td className="px-5 py-3 font-medium">{p.symbol}</td>
              <td className="px-3 py-3">
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                    p.direction === "long"
                      ? "bg-hermes-laurel/15 text-hermes-laurel"
                      : "bg-hermes-wine/15 text-hermes-wine"
                  }`}
                >
                  {p.direction === "long" ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                  {p.direction === "long" ? "Long" : "Short"}
                </span>
              </td>
              <td className="px-3 py-3 text-right number">{p.lot_size.toFixed(2)}</td>
              <td className="px-3 py-3 text-right number">{p.entry_price.toFixed(5)}</td>
              <td className="px-3 py-3 text-right number">{p.current_price.toFixed(5)}</td>
              <td
                className={`px-3 py-3 text-right number font-medium ${
                  p.unrealized_pnl >= 0 ? "text-hermes-laurel" : "text-hermes-wine"
                }`}
              >
                {formatMoney(p.unrealized_pnl)}
              </td>
              <td className="px-3 py-3 text-xs text-muted-foreground">
                {formatDateTime(p.opened_at)}
              </td>
              <td className="px-2 py-3">
                <button
                  onClick={() => handleClose(p.ticket)}
                  disabled={closing === p.ticket}
                  className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground hover:bg-hermes-wine/15 hover:text-hermes-wine disabled:opacity-50"
                  aria-label="Закрыть позицию"
                  title="Закрыть"
                >
                  <X size={14} />
                </button>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
