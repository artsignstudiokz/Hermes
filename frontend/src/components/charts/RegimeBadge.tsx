import { motion } from "framer-motion";

import type { Regime } from "@/api/useAdaptive";

const STYLES: Record<Regime, { label: string; cls: string; emoji: string; barClass: string }> = {
  trend: {
    label: "Тренд",
    cls: "bg-hermes-laurel/15 text-hermes-laurel border-hermes-laurel/40",
    emoji: "📈",
    barClass: "bg-hermes-laurel",
  },
  flat: {
    label: "Флэт",
    cls: "bg-hermes-parchment/60 text-hermes-bronze border-hermes-bronze/40",
    emoji: "⚖",
    barClass: "bg-hermes-bronze",
  },
  high_vol: {
    label: "Волатильность",
    cls: "bg-hermes-wine/10 text-hermes-wine border-hermes-wine/40",
    emoji: "⚡",
    barClass: "bg-hermes-wine",
  },
};

interface Props {
  regime: Regime;
  small?: boolean;
  symbol?: string;
  confidence?: number;       // 0..1
}

export function RegimeBadge({ regime, small, symbol, confidence }: Props) {
  const s = STYLES[regime];
  const pct = Math.round((confidence ?? 0) * 100);
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border ${s.cls} ${
        small ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs"
      } font-medium`}
      title={symbol ? `${symbol}: ${s.label}` : s.label}
    >
      <span aria-hidden>{s.emoji}</span>
      {symbol ? <span className="font-mono">{symbol}</span> : null}
      <span>{s.label}</span>
      {confidence != null && (
        <span className="ml-1 inline-flex items-center gap-1">
          <span className={`relative h-1 ${small ? "w-7" : "w-10"} rounded-full bg-current/15 overflow-hidden`}>
            <motion.span
              className={`absolute inset-y-0 left-0 rounded-full ${s.barClass}`}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          </span>
          <span className="font-mono text-[9px] opacity-70">{pct}%</span>
        </span>
      )}
    </span>
  );
}
