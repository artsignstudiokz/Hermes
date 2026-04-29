import { motion } from "framer-motion";

interface Props {
  eyebrow?: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  status?: React.ReactNode;
}

/** Consistent page header: eyebrow + display title + subtitle + actions slot. */
export function PageHeader({ eyebrow, title, subtitle, actions, status }: Props) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col items-start justify-between gap-4 lg:flex-row lg:items-end"
    >
      <div className="min-w-0 flex-1">
        {(eyebrow || status) && (
          <div className="flex items-center gap-3">
            {eyebrow && (
              <p className="text-[10px] font-medium uppercase tracking-[0.32em] text-muted-foreground">
                {eyebrow}
              </p>
            )}
            {status}
          </div>
        )}
        <h1 className="display mt-2 text-3xl md:text-4xl font-semibold tracking-tight text-hermes-navy">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1.5 max-w-2xl font-serif text-base text-muted-foreground">
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </motion.header>
  );
}
