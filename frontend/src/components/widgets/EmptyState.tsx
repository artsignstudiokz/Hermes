import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface Props {
  icon?: LucideIcon;
  glyph?: string;            // Greek glyph fallback
  title: string;
  description?: string;
  action?: React.ReactNode;
  compact?: boolean;
}

/** Empty state with marble background, soft gold radial, Greek glyph. */
export function EmptyState({ icon: Icon, glyph, title, description, action, compact }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`relative flex flex-col items-center justify-center text-center ${
        compact ? "px-6 py-10" : "px-6 py-16"
      }`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(circle at 50% 30%, rgba(201,169,110,0.18), transparent 60%)",
        }}
      />
      <div className="grid h-16 w-16 place-items-center rounded-full border border-hermes-gold/30 bg-hermes-alabaster/70 text-hermes-gold-deep">
        {Icon ? <Icon size={26} /> : (
          <span className="font-serif text-3xl">{glyph ?? "Ω"}</span>
        )}
      </div>
      <h3 className="display mt-5 text-2xl font-semibold gold-text">{title}</h3>
      {description && (
        <p className="mt-2 max-w-md font-serif italic text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </motion.div>
  );
}
