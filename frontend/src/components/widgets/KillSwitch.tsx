import { useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

import { useKillSwitch } from "@/api/useTrading";

/** Big red button that closes everything immediately. Two-step confirmation. */
export function KillSwitch() {
  const [armed, setArmed] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const mut = useKillSwitch();

  const onClick = async () => {
    if (!armed) {
      setArmed(true);
      setTimeout(() => setArmed(false), 4000);
      return;
    }
    try {
      const r = await mut.mutateAsync();
      setFeedback(`Закрыто позиций: ${r.closed_count}`);
    } catch (e) {
      setFeedback(e instanceof Error ? e.message : "Не удалось");
    } finally {
      setArmed(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  return (
    <div className="marble-card overflow-hidden p-5">
      <div className="flex items-center gap-3">
        <AlertTriangle size={18} className="text-hermes-wine" />
        <h3 className="display text-lg font-semibold">Аварийная остановка</h3>
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        Мгновенно закроет все открытые позиции у активного брокера. Подтвердите действие двойным
        нажатием.
      </p>
      <motion.button
        onClick={onClick}
        whileTap={{ scale: 0.98 }}
        disabled={mut.isPending}
        className={`mt-4 w-full rounded-xl px-5 py-3 text-sm font-bold uppercase tracking-[0.18em] transition
          ${armed
            ? "bg-hermes-wine text-white shadow-[0_8px_24px_-8px_rgba(122,27,39,0.5)]"
            : "border border-hermes-wine/40 bg-hermes-wine/10 text-hermes-wine hover:bg-hermes-wine/15"}
          disabled:opacity-50`}
      >
        {mut.isPending ? "Закрываю…" : armed ? "Подтвердите — закрыть всё" : "Закрыть все позиции"}
      </motion.button>
      {feedback && (
        <p className="mt-3 text-xs text-muted-foreground">{feedback}</p>
      )}
    </div>
  );
}
