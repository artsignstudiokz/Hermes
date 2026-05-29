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

  // v1.0.36: pure CSS pulse via tailwind's `animate-pulse` instead of a
  // framer-motion repeat:Infinity. Under --disable-gpu the JS-driven
  // animation was a per-frame setState that piled up on top of every
  // other animated component; the renderer eventually choked.
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium tracking-wide ${tones[tone]}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full bg-current ${running && !paused ? "animate-pulse" : ""}`}
      />
      {label}
      {data?.worker?.tick_count ? (
        <span className="ml-1 font-mono text-[10px] opacity-70">·{data.worker.tick_count}</span>
      ) : null}
    </div>
  );
}
