import { motion } from "framer-motion";
import { useTradingStatus } from "@/api/useAccount";

export function BotStatusBadge() {
  const { data } = useTradingStatus();
  const running = !!data?.worker?.running;
  const paused = !!data?.worker?.paused;

  const label = running ? (paused ? "Приостановлен" : "Торгует") : "Остановлен";
  const tone = running ? (paused ? "warning" : "success") : "neutral";
  const tones = {
    success: "bg-hermes-laurel/15 text-hermes-laurel border-hermes-laurel/40",
    warning: "bg-hermes-bronze/15 text-hermes-bronze border-hermes-bronze/40",
    neutral: "bg-hermes-parchment/60 text-hermes-ink/60 border-hermes-gold/30",
  } as const;

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium tracking-wide ${tones[tone]}`}>
      <motion.span
        className="h-1.5 w-1.5 rounded-full bg-current"
        animate={running && !paused ? { opacity: [0.4, 1, 0.4] } : { opacity: 1 }}
        transition={{ duration: 1.6, repeat: Infinity }}
      />
      {label}
      {data?.worker?.tick_count ? (
        <span className="ml-1 font-mono text-[10px] opacity-70">·{data.worker.tick_count}</span>
      ) : null}
    </div>
  );
}
