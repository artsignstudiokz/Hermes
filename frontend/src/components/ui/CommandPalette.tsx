import { AnimatePresence, motion } from "framer-motion";
import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { rankCommands, type Command } from "@/lib/commands";
import { cn } from "@/lib/utils";

/**
 * ⌘K / Ctrl+K command palette. Mount once at app root.
 *
 * Keyboard:
 *   ⌘K / Ctrl+K — open
 *   ↑ ↓        — navigate
 *   Enter      — execute
 *   Esc        — close
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();

  const results = useMemo(() => rankCommands(query), [query]);

  // Global hotkey.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Reset on open + focus input.
  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Clamp active index when results shrink.
  useEffect(() => {
    setActive((i) => Math.min(i, Math.max(0, results.length - 1)));
  }, [results.length]);

  const run = (cmd: Command) => {
    if (cmd.to) navigate(cmd.to);
    cmd.action?.();
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(results.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = results[active];
      if (cmd) run(cmd);
    }
  };

  // Group results by section while preserving rank order.
  const groups = useMemo(() => {
    const map = new Map<string, Command[]>();
    for (const cmd of results) {
      const arr = map.get(cmd.section) ?? [];
      arr.push(cmd);
      map.set(cmd.section, arr);
    }
    return Array.from(map.entries());
  }, [results]);

  // Find which absolute index each (group, item) corresponds to.
  let cursor = 0;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="palette"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-[80] flex items-start justify-center px-4 pt-[15vh]"
          onClick={() => setOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-hermes-ink/30 backdrop-blur-sm" />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -4 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-hermes-gold/40 bg-hermes-marble shadow-marble"
            role="dialog"
            aria-modal="true"
            aria-label="Командная палитра"
          >
            {/* Search */}
            <div className="flex items-center gap-3 border-b border-hermes-gold/20 px-4 py-3">
              <Search size={16} className="text-hermes-gold-deep" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Куда идём?  Стратегия, бэктест, брокеры…"
                className="flex-1 bg-transparent text-sm text-hermes-navy placeholder:text-muted-foreground/60 focus:outline-none"
              />
              <kbd className="hidden rounded border border-hermes-gold/30 bg-hermes-alabaster px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline">
                Esc
              </kbd>
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[60vh] overflow-y-auto p-1.5">
              {results.length === 0 ? (
                <div className="grid place-items-center py-12 text-center">
                  <p className="font-serif italic text-sm text-muted-foreground">
                    «Hermes ничего не нашёл по запросу <strong>"{query}"</strong>»
                  </p>
                </div>
              ) : (
                groups.map(([section, items]) => (
                  <div key={section} className="px-1.5 py-1">
                    <div className="px-2 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-muted-foreground/70">
                      {section}
                    </div>
                    {items.map((cmd) => {
                      const myIdx = cursor++;
                      const isActive = myIdx === active;
                      return (
                        <button
                          key={cmd.id}
                          onMouseEnter={() => setActive(myIdx)}
                          onClick={() => run(cmd)}
                          className={cn(
                            "flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm transition",
                            isActive
                              ? "bg-marble-grain text-hermes-navy shadow-card"
                              : "text-muted-foreground hover:bg-hermes-parchment/60",
                          )}
                        >
                          {cmd.icon && (
                            <span
                              className={cn(
                                "grid h-7 w-7 shrink-0 place-items-center rounded-md ring-1",
                                isActive
                                  ? "ring-hermes-gold/45 text-hermes-gold-deep bg-hermes-gold/10"
                                  : "ring-hermes-gold/20 text-muted-foreground",
                              )}
                            >
                              <cmd.icon size={14} />
                            </span>
                          )}
                          <span className="flex-1 truncate">{cmd.label}</span>
                          {isActive && (
                            <kbd className="rounded border border-hermes-gold/30 bg-hermes-alabaster px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground">
                              ↵
                            </kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-hermes-gold/15 bg-hermes-alabaster/50 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-muted-foreground/70">
              <span className="flex items-center gap-2">
                <Kbd>↑</Kbd>
                <Kbd>↓</Kbd>
                <span>навигация</span>
              </span>
              <span className="flex items-center gap-2">
                <Kbd>↵</Kbd>
                <span>открыть</span>
              </span>
              <span className="hidden sm:flex items-center gap-2">
                <span>BAI Core · Hermes</span>
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-grid h-4 min-w-[18px] place-items-center rounded border border-hermes-gold/30 bg-hermes-alabaster px-1 font-mono text-[9px] text-muted-foreground">
      {children}
    </kbd>
  );
}
