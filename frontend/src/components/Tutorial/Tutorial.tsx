/**
 * First-run tutorial - game-style walkthrough with cinematic intro.
 *
 * Stored in localStorage under HERMES_TOUR_VERSION so we can bump it
 * (e.g. when a major UI change lands) and re-show. Users who already
 * went through skip automatically; the Settings page exposes a
 * "Перепройти тур" button that clears the flag.
 */

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { api } from "@/lib/api";
import { TUTORIAL_STEPS, type TutorialStep } from "./steps";

const CURRENT_TOUR_VERSION = "v1.0.28";

interface UiPrefs {
  tutorial_done: boolean;
  tutorial_version: string;
}

/* Persisted on the backend (data_dir/ui-prefs.json), not localStorage.
   Reason: PyWebView opens the SPA on an ephemeral 127.0.0.1 port that
   changes every restart, so localStorage (scoped to host+port) lost
   the "done" flag and the tour replayed on every launch. */

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
    /* swallow */
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
  // Clamp step into the valid range. If TUTORIAL_STEPS ever changes
  // length while a stale flag points past the end (or a renderer
  // miscalculates), `current.anchor` would throw and crash the whole
  // app - that's the bug that produced the white screen after
  // restart. Clamping makes the component crash-proof.
  const total = TUTORIAL_STEPS.length;
  const [rawStep, setStep] = useState(0);
  const step = Math.max(0, Math.min(rawStep, total - 1));
  const current: TutorialStep = TUTORIAL_STEPS[step] ?? TUTORIAL_STEPS[0];
  const isFirst = step === 0;
  const isLast = step === total - 1;

  // Anchor highlight position, measured each step.
  const spotlight = useAnchorRect(current?.anchor ?? null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight" && !isLast) setStep((s) => s + 1);
      else if (e.key === "ArrowLeft" && !isFirst) setStep((s) => s - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, isFirst, isLast, onClose]);

  const finish = () => {
    // Fire and forget: close immediately so the UI is responsive,
    // let the backend persist in the background. Errors are swallowed
    // inside markTutorialDone itself.
    void markTutorialDone();
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="fixed inset-0 z-[10000]"
        >
          {/* Backdrop with vignette + ambient gold glow at edges */}
          <div
            className="absolute inset-0 backdrop-blur-md"
            style={{
              background: `
                radial-gradient(ellipse at top left, rgba(244,215,131,0.18) 0%, transparent 35%),
                radial-gradient(ellipse at bottom right, rgba(155,123,45,0.22) 0%, transparent 40%),
                rgba(26,21,15,0.65)
              `,
            }}
            onClick={isLast ? finish : undefined}
          />

          {/* Spotlight ring on anchored element */}
          {spotlight && (
            <motion.div
              key={current.id}
              initial={{ opacity: 0, scale: 1.4 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="pointer-events-none absolute rounded-2xl"
              style={{
                left: spotlight.left - 12,
                top: spotlight.top - 12,
                width: spotlight.width + 24,
                height: spotlight.height + 24,
                boxShadow: `
                  0 0 0 3px rgba(244, 215, 131, 0.85),
                  0 0 24px 8px rgba(212, 175, 55, 0.45),
                  0 0 80px 24px rgba(212, 175, 55, 0.25)
                `,
              }}
            />
          )}

          {/* Spinning Hermes coin in upper-right - passive aesthetic */}
          <CoinOrnament />

          {/* The step card */}
          <div className="absolute inset-0 flex items-center justify-center p-6 pointer-events-none">
            <AnimatePresence mode="wait">
              <motion.div
                key={current.id}
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -16, scale: 0.97 }}
                transition={{ duration: 0.45, ease: [0.2, 0.65, 0.3, 1] }}
                className="pointer-events-auto relative w-full max-w-xl"
                style={{
                  background: "linear-gradient(135deg, #FFFCF1 0%, #FFF8E1 100%)",
                  border: "1.5px solid rgba(212, 175, 55, 0.55)",
                  borderRadius: "20px",
                  padding: "2rem 2.25rem",
                  boxShadow: `
                    0 30px 90px -30px rgba(155, 123, 45, 0.55),
                    0 0 0 1px rgba(244, 215, 131, 0.4)
                  `,
                }}
              >
                {/* Close X */}
                <button
                  onClick={finish}
                  className="absolute right-4 top-4 grid h-7 w-7 place-items-center rounded-lg text-hermes-gold-deep/70 hover:bg-hermes-gold/15 hover:text-hermes-gold-deep transition"
                  aria-label="Закрыть тур"
                >
                  <X size={14} />
                </button>

                {/* Step indicator */}
                <div className="flex items-center gap-1.5 mb-3">
                  {TUTORIAL_STEPS.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setStep(i)}
                      className={`h-1 rounded-full transition-all ${
                        i === step
                          ? "w-7 bg-hermes-gold-deep"
                          : i < step
                          ? "w-3 bg-hermes-gold/60"
                          : "w-3 bg-hermes-gold/25"
                      }`}
                      aria-label={`Шаг ${i + 1}`}
                    />
                  ))}
                  <span className="ml-2 text-[10px] uppercase tracking-[0.18em] text-hermes-gold-deep/60 font-mono">
                    {step + 1} / {TUTORIAL_STEPS.length}
                  </span>
                </div>

                {/* Hermes avatar + title row */}
                <div className="flex items-start gap-4 mb-4">
                  <HermesAvatar />
                  <div className="flex-1 pt-1">
                    <h2
                      className="display text-2xl md:text-3xl font-semibold gold-text"
                      style={{ lineHeight: 1.15 }}
                    >
                      <RevealText text={current.title} key={current.id + "-title"} />
                    </h2>
                  </div>
                </div>

                {/* Body */}
                <motion.div
                  key={current.id + "-body"}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.2 }}
                  className="text-[15px] leading-relaxed text-foreground/85 whitespace-pre-line"
                >
                  {current.body}
                </motion.div>

                {/* Quote */}
                {current.quote && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.45 }}
                    className="mt-5 border-l-2 border-hermes-gold-deep/60 pl-3 italic font-serif text-[14px] text-hermes-gold-deep/80"
                  >
                    «{current.quote}»
                  </motion.div>
                )}

                {/* Footer */}
                <div className="mt-7 flex items-center justify-between gap-3">
                  <button
                    onClick={() => setStep((s) => Math.max(0, s - 1))}
                    disabled={isFirst}
                    className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft size={14} /> Назад
                  </button>
                  <button
                    onClick={() => (isLast ? finish() : setStep((s) => s + 1))}
                    className="gold-button inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold uppercase tracking-wider"
                  >
                    {isLast ? "Начать торговать" : "Далее"}
                    {!isLast && <ChevronRight size={14} />}
                  </button>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────


function useAnchorRect(selector: string | null): DOMRect | null {
  const [rect, setRect] = useState<DOMRect | null>(null);
  useEffect(() => {
    if (!selector) {
      setRect(null);
      return;
    }
    const measure = () => {
      const el = document.querySelector(selector);
      if (el) setRect(el.getBoundingClientRect());
      else setRect(null);
    };
    measure();
    window.addEventListener("resize", measure);
    const t = window.setTimeout(measure, 200);     // wait for layout to settle
    return () => {
      window.removeEventListener("resize", measure);
      window.clearTimeout(t);
    };
  }, [selector]);
  return rect;
}

/** Single character at a time - gives the title a cinematic feel. */
function RevealText({ text }: { text: string }) {
  const letters = useMemo(() => Array.from(text), [text]);
  return (
    <span>
      {letters.map((ch, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32, delay: i * 0.025 }}
          style={{ display: "inline-block", whiteSpace: ch === " " ? "pre" : "normal" }}
        >
          {ch}
        </motion.span>
      ))}
    </span>
  );
}

function HermesAvatar() {
  return (
    <div className="relative shrink-0">
      <div
        className="grid h-14 w-14 md:h-16 md:w-16 place-items-center rounded-full"
        style={{
          background: "radial-gradient(circle at 30% 25%, #FFEFC5 0%, #F4D783 25%, #D4AF37 60%, #7A5A1E 100%)",
          boxShadow: "inset 0 3px 8px rgba(255,255,255,0.6), inset 0 -6px 14px rgba(60,44,18,0.45), 0 6px 18px -4px rgba(155,123,45,0.5)",
        }}
      >
        <span
          className="display text-2xl md:text-3xl font-semibold"
          style={{ color: "#5A3F12", textShadow: "0 1px 0 rgba(255,255,255,0.35)" }}
        >
          Ἑ
        </span>
      </div>
      {/* Spinning halo */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
        className="absolute inset-[-6px] rounded-full pointer-events-none"
        style={{
          border: "1px dashed rgba(155,123,45,0.5)",
        }}
      />
    </div>
  );
}

function CoinOrnament() {
  return (
    <motion.div
      className="absolute right-8 top-8 pointer-events-none hidden md:block"
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
    >
      <motion.div
        animate={{ rotateY: [0, 360] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
        className="relative w-20 h-20 rounded-full"
        style={{
          background: "radial-gradient(circle at 30% 25%, #FFEFC5 0%, #F4D783 25%, #D4AF37 60%, #7A5A1E 100%)",
          boxShadow: `
            inset 0 4px 10px rgba(255,255,255,0.7),
            inset 0 -10px 22px rgba(60,44,18,0.55),
            0 18px 40px -10px rgba(155,123,45,0.6)
          `,
        }}
      >
        <span
          className="display absolute inset-0 grid place-items-center text-3xl font-semibold"
          style={{ color: "#5A3F12" }}
        >
          ⚡
        </span>
      </motion.div>
    </motion.div>
  );
}
