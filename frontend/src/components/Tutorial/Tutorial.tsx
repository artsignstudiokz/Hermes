/**
 * Action-driven tutorial.
 *
 * Each step has an action the operator must perform:
 *   - manual       -> operator clicks "Далее"
 *   - navigate     -> wait for the URL to match a path
 *   - click        -> wait for click on [data-tour="<id>"]
 *
 * The tutorial card lives bottom-right of the screen, compact,
 * non-blocking. It does NOT cover the UI - operators can interact
 * with the app while the card is open. The anchored element (if
 * any) gets a gold spotlight ring so it's obvious where to click.
 *
 * Crash defenses (from v1.0.29):
 *   - step is clamped into [0, length-1] so out-of-range never
 *     dereferences undefined
 *   - all DOM measurements wrapped in try/catch
 *   - listeners cleaned up on unmount
 *   - markTutorialDone is fire-and-forget (UI doesn't wait for
 *     backend write)
 */

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChevronRight, MinusCircle, X } from "lucide-react";

import { api } from "@/lib/api";
import { TUTORIAL_STEPS, type TutorialStep } from "./steps";

const CURRENT_TOUR_VERSION = "v1.0.30";

interface UiPrefs {
  tutorial_done: boolean;
  tutorial_version: string;
}

/* Backend-persisted preferences (data_dir/ui-prefs.json). localStorage
   was unusable because the ephemeral 127.0.0.1 port flips on every
   restart, scoping the flag to nothing. See v1.0.29 commit notes. */

export async function shouldShowTutorial(): Promise<boolean> {
  try {
    const p = await api.get<UiPrefs>("/api/system/ui-prefs");
    return !p.tutorial_done || p.tutorial_version !== CURRENT_TOUR_VERSION;
  } catch {
    return true;
  }
}

export async function markTutorialDone(): Promise<void> {
  try {
    await api.post<UiPrefs, UiPrefs>("/api/system/ui-prefs", {
      tutorial_done: true,
      tutorial_version: CURRENT_TOUR_VERSION,
    });
  } catch {
    /* swallow - tour is over visually even if persistence fails */
  }
}

export async function resetTutorial(): Promise<void> {
  try {
    await api.post<UiPrefs, UiPrefs>("/api/system/ui-prefs", {
      tutorial_done: false,
      tutorial_version: "",
    });
  } catch {
    /* swallow */
  }
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export function Tutorial({ open, onClose }: Props) {
  const total = TUTORIAL_STEPS.length;
  const [rawStep, setStep] = useState(0);
  const [minimized, setMinimized] = useState(false);

  // Clamp into the valid index range. Defensive: if total ever
  // becomes 0 or step drifts out of range, we serve step 0 instead
  // of crashing on `current.anchor`.
  const step = Math.max(0, Math.min(rawStep, total - 1));
  const current: TutorialStep = TUTORIAL_STEPS[step] ?? TUTORIAL_STEPS[0];
  const isFirst = step === 0;
  const isLast = step === total - 1;

  const goNext = useCallback(() => {
    if (isLast) {
      void markTutorialDone();
      onClose();
    } else {
      setStep((s) => s + 1);
    }
  }, [isLast, onClose]);

  const goPrev = useCallback(() => {
    if (!isFirst) setStep((s) => s - 1);
  }, [isFirst]);

  // ── Action detectors ──────────────────────────────────────────

  const location = useLocation();
  const lastNavStepRef = useRef(-1);

  // Navigate detector: when the URL matches the expected path AND we
  // haven't already advanced for this step, move forward.
  useEffect(() => {
    if (!open) return;
    if (current?.action.type !== "navigate") return;
    if (lastNavStepRef.current === step) return;
    if (location.pathname === current.action.path) {
      lastNavStepRef.current = step;
      // Small delay so the new page mounts before we reposition.
      const t = window.setTimeout(() => goNext(), 350);
      return () => window.clearTimeout(t);
    }
  }, [open, current, step, location.pathname, goNext]);

  // Click detector: document-level listener for [data-tour="<id>"]
  // clicks. Event delegation means the target component doesn't need
  // to know about the tutorial.
  useEffect(() => {
    if (!open) return;
    if (current?.action.type !== "click") return;
    const expected = current.action.tour;
    const handler = (e: MouseEvent) => {
      try {
        const target = e.target as HTMLElement | null;
        const match = target?.closest(`[data-tour="${expected}"]`);
        if (match) {
          window.setTimeout(() => goNext(), 250);
        }
      } catch {
        /* never let our listener throw */
      }
    };
    document.addEventListener("click", handler, true);
    return () => document.removeEventListener("click", handler, true);
  }, [open, current, goNext]);

  // ── Anchor spotlight ─────────────────────────────────────────

  const spotlight = useAnchorRect(open ? (current?.anchor ?? null) : null);

  // ── Keyboard ─────────────────────────────────────────────────

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        void markTutorialDone();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) setMinimized(false);
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Spotlight ring on anchored element. pointer-events: none lets
          clicks pass through to the actual button underneath. */}
      <AnimatePresence>
        {spotlight && !minimized && (
          <motion.div
            key={current.id}
            initial={{ opacity: 0, scale: 1.3 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.35 }}
            className="pointer-events-none fixed rounded-2xl z-[9998]"
            style={{
              left: spotlight.left - 10,
              top: spotlight.top - 10,
              width: spotlight.width + 20,
              height: spotlight.height + 20,
              boxShadow: `
                0 0 0 3px rgba(244, 215, 131, 0.9),
                0 0 24px 6px rgba(212, 175, 55, 0.55),
                0 0 80px 24px rgba(212, 175, 55, 0.18)
              `,
            }}
          />
        )}
      </AnimatePresence>

      {/* Floating card, bottom-right. Does NOT block the UI. */}
      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.35, ease: [0.2, 0.65, 0.3, 1] }}
        className="fixed bottom-6 right-6 z-[9999] w-[min(440px,calc(100vw-3rem))]"
      >
        <AnimatePresence mode="wait">
          {minimized ? (
            <motion.button
              key="mini"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              onClick={() => setMinimized(false)}
              className="ml-auto flex items-center gap-2 rounded-full border border-hermes-gold-deep/60 bg-hermes-gold/15 px-4 py-2.5 text-sm font-semibold text-hermes-gold-deep shadow-lg backdrop-blur transition hover:bg-hermes-gold/25"
            >
              <CoinDot />
              Шаг {step + 1} / {total}
            </motion.button>
          ) : (
            <motion.div
              key="full"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="relative overflow-hidden rounded-2xl border border-hermes-gold-deep/45 bg-hermes-alabaster shadow-2xl"
              style={{
                boxShadow:
                  "0 30px 80px -20px rgba(155,123,45,0.55), 0 0 0 1px rgba(244,215,131,0.4)",
              }}
            >
              <div className="flex items-center justify-between px-5 pt-4">
                <div className="flex items-center gap-2.5">
                  <CoinDot />
                  <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-hermes-gold-deep">
                    Hermes · шаг {step + 1} / {total}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setMinimized(true)}
                    className="grid h-6 w-6 place-items-center rounded text-hermes-gold-deep/70 hover:bg-hermes-gold/15 hover:text-hermes-gold-deep"
                    title="Свернуть"
                  >
                    <MinusCircle size={13} />
                  </button>
                  <button
                    onClick={() => {
                      void markTutorialDone();
                      onClose();
                    }}
                    className="grid h-6 w-6 place-items-center rounded text-hermes-gold-deep/70 hover:bg-hermes-gold/15 hover:text-hermes-gold-deep"
                    title="Закрыть"
                  >
                    <X size={13} />
                  </button>
                </div>
              </div>

              <div className="mt-2 flex items-center gap-1 px-5">
                {TUTORIAL_STEPS.map((_, i) => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-all ${
                      i <= step ? "bg-hermes-gold-deep" : "bg-hermes-gold/25"
                    }`}
                  />
                ))}
              </div>

              <div className="px-5 pb-5 pt-4">
                <h3 className="display gold-text text-xl font-semibold leading-tight">
                  {current.title}
                </h3>
                <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-foreground/85">
                  {current.body}
                </p>
                {current.hint && (
                  <div className="mt-3 rounded-lg border border-hermes-gold/30 bg-hermes-gold/10 px-3 py-2 text-xs font-medium text-hermes-gold-deep">
                    👉 {current.hint}
                  </div>
                )}

                <div className="mt-4 flex items-center justify-between">
                  <button
                    onClick={goPrev}
                    disabled={isFirst}
                    className="text-xs text-muted-foreground hover:text-foreground disabled:opacity-30"
                  >
                    Назад
                  </button>
                  <div className="flex items-center gap-2">
                    {current.action.type === "manual" ? (
                      <button
                        onClick={goNext}
                        className="gold-button inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold uppercase tracking-wider"
                      >
                        {isLast ? "Завершить" : isFirst ? "Поехали" : "Понятно"}
                        {!isLast && <ChevronRight size={12} />}
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={goNext}
                          className="text-xs text-muted-foreground hover:text-foreground"
                          title="Если не получается, можно пропустить"
                        >
                          Пропустить
                        </button>
                        <div className="inline-flex items-center gap-1.5 rounded-lg border border-hermes-laurel/50 bg-hermes-laurel/10 px-3 py-2 text-xs font-medium text-hermes-laurel">
                          <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-hermes-laurel/40"></span>
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-hermes-laurel"></span>
                          </span>
                          Жду действия
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </>
  );
}

// ── Helpers ──────────────────────────────────────────────────────


function useAnchorRect(selector: string | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);
  useEffect(() => {
    if (!selector) {
      setRect(null);
      return;
    }
    const measure = () => {
      try {
        const el = document.querySelector(selector);
        if (el) setRect(el.getBoundingClientRect());
        else setRect(null);
      } catch {
        setRect(null);
      }
    };
    measure();
    const t = window.setTimeout(measure, 250);
    const onResize = () => measure();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    let mo: MutationObserver | null = null;
    try {
      mo = new MutationObserver(measure);
      mo.observe(document.body, { childList: true, subtree: true, attributes: true });
    } catch {
      /* MutationObserver unsupported - degrade gracefully */
    }
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
      mo?.disconnect();
    };
  }, [selector]);
  return rect;
}

function CoinDot() {
  return (
    <div
      className="grid h-5 w-5 place-items-center rounded-full"
      style={{
        background:
          "radial-gradient(circle at 30% 25%, #FFEFC5 0%, #F4D783 25%, #D4AF37 60%, #7A5A1E 100%)",
        boxShadow:
          "inset 0 1px 2px rgba(255,255,255,0.6), inset 0 -2px 3px rgba(60,44,18,0.45), 0 2px 6px -1px rgba(155,123,45,0.5)",
      }}
    >
      <span
        className="display text-[10px] font-semibold"
        style={{ color: "#5A3F12" }}
      >
        Ἑ
      </span>
    </div>
  );
}
