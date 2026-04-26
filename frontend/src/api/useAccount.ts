import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { api } from "@/lib/api";
import { subscribe } from "@/lib/ws";
import type { AccountInfo, EquityPoint, TradingStatus } from "./types";

export function useAccount() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["account"],
    queryFn: () => api.get<AccountInfo | null>("/api/account/info"),
    refetchInterval: 30_000,
  });

  // Real-time equity stream patches the account cache.
  useEffect(() => {
    return subscribe<{ equity: number; balance: number; margin: number }>(
      "equity",
      (msg) => {
        qc.setQueryData<AccountInfo | null>(["account"], (prev) =>
          prev
            ? { ...prev, equity: msg.equity, balance: msg.balance, margin: msg.margin }
            : prev,
        );
      },
    );
  }, [qc]);

  return q;
}

export function useEquityHistory(brokerAccountId: number | null, days = 30) {
  return useQuery({
    queryKey: ["equity-history", brokerAccountId, days],
    queryFn: () =>
      api.get<EquityPoint[]>(
        `/api/account/equity-history?broker_account_id=${brokerAccountId}&days=${days}`,
      ),
    enabled: brokerAccountId != null,
  });
}

export function useTradingStatus() {
  return useQuery({
    queryKey: ["trading-status"],
    queryFn: () => api.get<TradingStatus>("/api/trading/status"),
    refetchInterval: 5_000,
  });
}
