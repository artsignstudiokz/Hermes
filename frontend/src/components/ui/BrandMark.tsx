import { cn } from "@/lib/utils";

interface BrandMarkProps {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  className?: string;
  /** Use the full horizontal logo (with HERMES wordmark baked in) instead of the favicon emblem. */
  full?: boolean;
}

const SIZES = {
  sm: { svg: 26, text: "text-base" },
  md: { svg: 36, text: "text-xl" },
  lg: { svg: 56, text: "text-3xl" },
  xl: { svg: 88, text: "text-5xl" },
} as const;

/** Hermes wordmark + caduceus emblem. */
export function BrandMark({ size = "md", showText = true, className, full }: BrandMarkProps) {
  const s = SIZES[size];

  if (full) {
    // Use the wordmark logo end-to-end, no extra text.
    return (
      <div className={cn("flex items-center", className)}>
        <img
          src="/hermes-logo.png"
          alt="Hermes — Trading Bot"
          height={s.svg}
          style={{ height: s.svg, width: "auto" }}
          className="select-none"
          draggable={false}
        />
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <img
        src="/hermes-favicon.png"
        alt="Hermes"
        width={s.svg}
        height={s.svg}
        className="animate-wing-flutter select-none drop-shadow-sm"
        style={{ width: s.svg, height: s.svg }}
        draggable={false}
      />
      {showText && (
        <div className="flex flex-col leading-none">
          <span className={cn("display font-semibold tracking-tight text-hermes-navy", s.text)}>
            HERMES
          </span>
          <span className="text-[10px] uppercase tracking-[0.28em] text-hermes-gold-deep mt-0.5">
            Trading Bot · BAI Core
          </span>
        </div>
      )}
    </div>
  );
}
