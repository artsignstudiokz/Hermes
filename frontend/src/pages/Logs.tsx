import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

interface LogsResponse {
  lines: string[];
}

export function Logs() {
  const [lines, setLines] = useState<string[]>([]);
  const [paused, setPaused] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      if (paused) return;
      try {
        const r = await api.get<LogsResponse>("/api/system/logs?tail=400");
        if (active) setLines(r.lines);
      } catch {
        // ignore — backend may be reloading in dev
      }
    };
    tick();
    const handle = setInterval(tick, 3000);
    return () => {
      active = false;
      clearInterval(handle);
    };
  }, [paused]);

  useEffect(() => {
    if (!paused) ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [lines, paused]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-6"
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-muted-foreground">Журнал</p>
          <h1 className="display mt-2 text-4xl font-semibold tracking-tight">Логи системы</h1>
        </div>
        <button
          onClick={() => setPaused((v) => !v)}
          className="rounded-xl border border-hermes-gold/40 bg-hermes-alabaster px-4 py-2 text-sm font-medium hover:bg-hermes-parchment"
        >
          {paused ? "Возобновить" : "Пауза"}
        </button>
      </header>

      <div
        ref={ref}
        className="marble-card h-[60vh] overflow-y-auto p-4 font-mono text-xs leading-relaxed"
      >
        {lines.length === 0 ? (
          <span className="text-muted-foreground">Пусто. Логи появятся когда стартуете бота.</span>
        ) : (
          lines.map((ln, i) => (
            <div key={i} className={lineClass(ln)}>
              {ln}
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}

function lineClass(ln: string): string {
  if (ln.includes("[ERROR]")) return "text-hermes-wine";
  if (ln.includes("[WARN")) return "text-hermes-bronze";
  if (ln.includes("[INFO]")) return "text-foreground/80";
  return "text-muted-foreground";
}
