import { motion } from "framer-motion";

interface Props {
  /** Current drawdown as a fraction 0..1 */
  drawdown: number;
  /** Stop level (e.g. 0.10 for 10%) */
  stop: number;
  /** Hard portfolio cap (e.g. 0.20 for 20%) */
  hardStop: number;
}

/** Half-moon gauge showing current drawdown vs stop & hard-stop levels. */
export function RiskGauge({ drawdown, stop, hardStop }: Props) {
  const ratio = Math.min(1, Math.max(0, drawdown / hardStop));
  // Map 0..1 to angle [-90°, 90°] for the needle.
  const angle = -90 + ratio * 180;
  const tone =
    drawdown >= hardStop * 0.9
      ? "text-hermes-wine"
      : drawdown >= stop
      ? "text-hermes-bronze"
      : "text-hermes-laurel";

  return (
    <div className="marble-card flex flex-col items-center p-5">
      <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
        Просадка
      </span>
      <div className="relative mt-3 h-24 w-44">
        <svg viewBox="0 0 200 110" className="absolute inset-0">
          {/* Track */}
          <path
            d="M10 100 A90 90 0 0 1 190 100"
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="14"
            strokeLinecap="round"
          />
          {/* Olive zone (safe) */}
          <path
            d="M10 100 A90 90 0 0 1 100 10"
            fill="none"
            stroke="#7E8B5A"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${(stop / hardStop) * 283} 283`}
          />
          {/* Bronze zone (warning) */}
          <path
            d="M10 100 A90 90 0 0 1 190 100"
            fill="none"
            stroke="#8B6F3E"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${283} 283`}
            opacity="0.18"
          />
          {/* Needle */}
          <motion.line
            x1="100"
            y1="100"
            x2="100"
            y2="22"
            stroke="#2A2520"
            strokeWidth="2.5"
            strokeLinecap="round"
            initial={{ rotate: -90 }}
            animate={{ rotate: angle }}
            transition={{ type: "spring", stiffness: 90, damping: 16 }}
            style={{ transformOrigin: "100px 100px" }}
          />
          <circle cx="100" cy="100" r="6" fill="#A8884F" />
        </svg>
      </div>
      <div className={`mt-1 number text-2xl font-semibold ${tone}`}>
        {(drawdown * 100).toFixed(2)}%
      </div>
      <div className="mt-1 flex items-center gap-3 text-[10px] uppercase tracking-wider text-muted-foreground">
        <span>Stop {(stop * 100).toFixed(0)}%</span>
        <span>·</span>
        <span>Max {(hardStop * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}
