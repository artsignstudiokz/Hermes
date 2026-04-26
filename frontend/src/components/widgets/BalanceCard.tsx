import { TrendingDown, TrendingUp } from "lucide-react";

import { formatMoney, formatPct } from "@/lib/format";
import type { AccountInfo } from "@/api/types";

interface Props {
  account: AccountInfo | null | undefined;
  loading?: boolean;
}

export function BalanceCard({ account, loading }: Props) {
  const profit = account?.profit ?? 0;
  const equity = account?.equity ?? 0;
  const ratio = account && account.balance ? profit / account.balance : 0;
  const isUp = profit >= 0;

  return (
    <div className="marble-card p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Equity</span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          {account?.currency ?? "—"}
        </span>
      </div>
      <div className="mt-3 number text-3xl font-semibold tracking-tight">
        {loading ? "…" : formatMoney(equity, account?.currency ?? "USD")}
      </div>
      <div
        className={`mt-1 inline-flex items-center gap-1 text-xs ${isUp ? "text-hermes-laurel" : "text-hermes-wine"}`}
      >
        {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
        <span className="number">{formatMoney(profit)}</span>
        <span className="opacity-60">·</span>
        <span className="number">{formatPct(ratio)}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider">Баланс</span>
          <span className="number text-foreground">{formatMoney(account?.balance ?? 0)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider">Свободно</span>
          <span className="number text-foreground">{formatMoney(account?.free_margin ?? 0)}</span>
        </div>
      </div>
    </div>
  );
}
