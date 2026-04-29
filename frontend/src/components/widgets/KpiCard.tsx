import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";
import { type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { MiniSparkline } from "@/components/charts/MiniSparkline";

interface Props {
  label: string;
  value: string;
  hint?: string;
  delta?: { text: string; positive?: boolean };
  icon: LucideIcon;
  tone?: "gold" | "laurel" | "bronze" | "olive" | "aegean" | "wine";
  sparkline?: number[];
}

const TONES = {
  gold:    { ring: "ring-hermes-gold/40",    bar: "text-hermes-gold-deep",  glow: "rgba(201,169,110,0.45)" },
  laurel:  { ring: "ring-hermes-laurel/40",  bar: "text-hermes-laurel",     glow: "rgba(126,139,90,0.4)" },
  bronze:  { ring: "ring-hermes-bronze/40",  bar: "text-hermes-bronze",     glow: "rgba(139,111,62,0.4)" },
  olive:   { ring: "ring-hermes-olive/40",   bar: "text-hermes-olive",      glow: "rgba(107,124,79,0.4)" },
  aegean:  { ring: "ring-hermes-aegean/40",  bar: "text-hermes-aegean",     glow: "rgba(46,79,111,0.4)" },
  wine:    { ring: "ring-hermes-wine/40",    bar: "text-hermes-wine",       glow: "rgba(122,27,39,0.4)" },
};

/** Premium KPI card — floating glow + count-up + optional sparkline + delta chip. */
export function KpiCard({ label, value, hint, delta, icon: Icon, tone = "gold", sparkline }: Props) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const t = TONES[tone];

  // Subtle 3D tilt on cursor — adds depth without being distracting.
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotX = useSpring(useTransform(y, [-1, 1], [4, -4]), { stiffness: 200, damping: 25 });
  const rotY = useSpring(useTransform(x, [-1, 1], [-4, 4]), { stiffness: 200, damping: 25 });

  const handleMove = (e: React.PointerEvent) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    x.set(((e.clientX - rect.left) / rect.width - 0.5) * 2);
    y.set(((e.clientY - rect.top) / rect.height - 0.5) * 2);
  };
  const handleLeave = () => {
    x.set(0);
    y.set(0);
  };

  // Animate the value digit-by-digit on mount.
  const valueRef = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    if (!valueRef.current) return;
    const el = valueRef.current;
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    requestAnimationFrame(() => {
      el.style.transition = "opacity 0.5s ease, transform 0.5s cubic-bezier(0.2, 0.65, 0.3, 1)";
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
  }, [value]);

  return (
    <motion.div
      ref={cardRef}
      onPointerMove={handleMove}
      onPointerLeave={handleLeave}
      style={{ rotateX: rotX, rotateY: rotY, transformStyle: "preserve-3d" }}
      className="kpi-card-wrap relative"
    >
      {/* Soft glow */}
      <div
        aria-hidden
        className="absolute -inset-1 rounded-2xl opacity-0 transition-opacity group-hover:opacity-100 [.kpi-card-wrap:hover_&]:opacity-100"
        style={{
          background: `radial-gradient(60% 80% at 50% 50%, ${t.glow}, transparent)`,
          filter: "blur(20px)",
          zIndex: -1,
        }}
      />
      <div className={cn(
        "marble-card relative overflow-hidden p-5",
        "transition-shadow duration-300 hover:shadow-marble",
      )}>
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
            {label}
          </span>
          <span className={cn(
            "grid h-9 w-9 place-items-center rounded-full bg-card ring-1",
            t.ring, t.bar,
          )}>
            <Icon size={15} />
          </span>
        </div>

        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="min-w-0 flex-1">
            <span
              ref={valueRef}
              className="number block text-2xl md:text-[28px] font-semibold tracking-tight text-hermes-navy"
            >
              {value}
            </span>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
              {delta && (
                <span className={cn(
                  "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-mono font-semibold",
                  delta.positive
                    ? "bg-hermes-laurel/15 text-hermes-laurel"
                    : "bg-hermes-wine/15 text-hermes-wine",
                )}>
                  <span aria-hidden>{delta.positive ? "▲" : "▼"}</span>
                  {delta.text}
                </span>
              )}
              {hint && <span className="truncate">{hint}</span>}
            </div>
          </div>

          {sparkline && sparkline.length > 1 && (
            <MiniSparkline
              values={sparkline}
              width={72}
              height={32}
              className="opacity-90 shrink-0"
            />
          )}
        </div>
      </div>
    </motion.div>
  );
}
