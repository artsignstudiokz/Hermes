import { motion } from "framer-motion";
import { TrendingDown, TrendingUp } from "lucide-react";

import { MiniSparkline } from "@/components/charts/MiniSparkline";
import { formatMoney, formatPct } from "@/lib/format";
import type { AccountInfo, EquityPoint } from "@/api/types";

interface Props {
  account: AccountInfo | null | undefined;
  loading?: boolean;
  history?: EquityPoint[];
}

/** Premium hero card — equity, profit, mini sparkline, breakdown. */
export function BalanceCard({ account, loading, history }: Props) {
  const profit = account?.profit ?? 0;
  const equity = account?.equity ?? 0;
  const ratio = account && account.balance ? profit / account.balance : 0;
  const isUp = profit >= 0;

  const sparklineData = (history ?? []).slice(-30).map((p) => p.equity);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.2, 0.65, 0.3, 1] }}
      className="marble-card relative overflow-hidden p-6 col-span-1 md:col-span-2"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full opacity-50"
        style={{
          background: "radial-gradient(closest-side, rgba(201,169,110,0.35), transparent)",
          filter: "blur(40px)",
        }}
      />

      <div className="relative flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-medium uppercase tracking-[0.28em] text-muted-foreground">
              Equity
            </span>
            <span className="rounded-full border border-hermes-gold/30 bg-hermes-alabaster/70 px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider text-hermes-gold-deep">
              {account?.currency ?? "—"} · 1:{account?.leverage ?? "—"}
            </span>
          </div>
          <div className="mt-3 number text-4xl md:text-5xl font-semibold tracking-tight text-hermes-navy">
            {loading ? "…" : formatMoney(equity, account?.currency ?? "USD")}
          </div>
          <div
            className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              isUp ? "bg-hermes-laurel/15 text-hermes-laurel" : "bg-hermes-wine/15 text-hermes-wine"
            }`}
          >
            {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            <span className="number">{formatMoney(profit)}</span>
            <span className="opacity-60">·</span>
            <span className="number">{formatPct(ratio)}</span>
          </div>
        </div>

        {sparklineData.length > 1 && (
          <div className="hidden md:block">
            <MiniSparkline
              values={sparklineData}
              width={170}
              height={62}
              stroke="#A8884F"
              fillFrom="rgba(201,169,110,0.35)"
              fillTo="rgba(201,169,110,0)"
            />
            <div className="mt-1 text-right text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
              30 дней
            </div>
          </div>
        )}
      </div>

      <div className="relative mt-5 grid grid-cols-3 gap-3 border-t border-hermes-gold/15 pt-4">
        <Sub label="Баланс" value={formatMoney(account?.balance ?? 0)} />
        <Sub label="Свободно" value={formatMoney(account?.free_margin ?? 0)} />
        <Sub label="Маржа" value={formatMoney(account?.margin ?? 0)} muted />
      </div>
    </motion.div>
  );
}

function Sub({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</div>
      <div
        className={`number mt-1 text-sm font-semibold ${
          muted ? "text-foreground/70" : "text-hermes-navy"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
