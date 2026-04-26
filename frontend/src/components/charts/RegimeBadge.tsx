import type { Regime } from "@/api/useAdaptive";

const STYLES: Record<Regime, { label: string; cls: string; emoji: string }> = {
  trend: {
    label: "Тренд",
    cls: "bg-hermes-laurel/15 text-hermes-laurel border-hermes-laurel/40",
    emoji: "📈",
  },
  flat: {
    label: "Флэт",
    cls: "bg-hermes-parchment/60 text-hermes-bronze border-hermes-bronze/40",
    emoji: "⚖",
  },
  high_vol: {
    label: "Волатильность",
    cls: "bg-hermes-wine/10 text-hermes-wine border-hermes-wine/40",
    emoji: "⚡",
  },
};

interface Props {
  regime: Regime;
  small?: boolean;
  symbol?: string;
}

export function RegimeBadge({ regime, small, symbol }: Props) {
  const s = STYLES[regime];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${s.cls} ${
        small ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs"
      } font-medium`}
      title={symbol ? `${symbol}: ${s.label}` : s.label}
    >
      <span aria-hidden>{s.emoji}</span>
      {symbol ? <span className="font-mono">{symbol}</span> : null}
      <span>{s.label}</span>
    </span>
  );
}
