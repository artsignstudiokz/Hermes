import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, Loader2, X, XCircle } from "lucide-react";

import { dismiss, useToasts, type ToastVariant } from "@/lib/toast";
import { cn } from "@/lib/utils";

const ICONS: Record<ToastVariant, typeof CheckCircle2> = {
  default: Info,
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  loading: Loader2,
};

const TONES: Record<ToastVariant, string> = {
  default: "border-hermes-gold/35 bg-hermes-alabaster text-hermes-navy",
  success: "border-hermes-laurel/40 bg-hermes-laurel/10 text-hermes-laurel",
  error: "border-hermes-wine/40 bg-hermes-wine/10 text-hermes-wine",
  warning: "border-hermes-bronze/40 bg-hermes-bronze/10 text-hermes-bronze",
  loading: "border-hermes-gold/40 bg-hermes-gold/10 text-hermes-gold-deep",
};

/** Mount once at app root. Reads toasts from the global store. */
export function Toaster() {
  const toasts = useToasts();
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-full max-w-sm flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = ICONS[t.variant];
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 32, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 32, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
              className={cn(
                "pointer-events-auto relative flex items-start gap-3 rounded-xl border p-3.5 pr-9 shadow-marble backdrop-blur-md",
                TONES[t.variant],
              )}
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-card/80 ring-1 ring-current/20">
                <Icon
                  size={14}
                  className={t.variant === "loading" ? "animate-spin" : ""}
                />
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold leading-tight text-foreground">
                  {t.title}
                </div>
                {t.description && (
                  <div className="mt-1 text-xs text-muted-foreground line-clamp-3">
                    {t.description}
                  </div>
                )}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                aria-label="Закрыть"
                className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-md text-current/60 hover:bg-current/10 hover:text-current transition"
              >
                <X size={12} />
              </button>
              {/* Auto-dismiss progress bar */}
              {t.durationMs > 0 && (
                <motion.div
                  initial={{ scaleX: 1 }}
                  animate={{ scaleX: 0 }}
                  transition={{ duration: t.durationMs / 1000, ease: "linear" }}
                  className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-current/40"
                />
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
