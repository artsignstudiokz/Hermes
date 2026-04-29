import { cn } from "@/lib/utils";

interface Props {
  className?: string;
  rounded?: "sm" | "md" | "lg" | "full";
}

/** Marble-tinted skeleton with subtle shimmer — for loading states. */
export function Skeleton({ className, rounded = "md" }: Props) {
  const r = {
    sm: "rounded-md",
    md: "rounded-lg",
    lg: "rounded-xl",
    full: "rounded-full",
  }[rounded];
  return (
    <span
      className={cn(
        "block animate-skel bg-gradient-to-r from-hermes-parchment/40 via-hermes-gold/10 to-hermes-parchment/40",
        "bg-[length:200%_100%]",
        r,
        className,
      )}
      aria-hidden
    />
  );
}

export function SkeletonText({ lines = 1, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-3", i === lines - 1 ? "w-2/3" : "w-full")}
          rounded="sm"
        />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="marble-card p-5">
      <Skeleton className="h-3 w-1/3" rounded="sm" />
      <Skeleton className="mt-3 h-8 w-2/3" />
      <Skeleton className="mt-2 h-3 w-1/2" rounded="sm" />
    </div>
  );
}
