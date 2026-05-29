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
    // 60 s safety net - equity/balance/margin are patched on every
    // /ws/equity tick (see subscription below). Was 30 s before
    // v1.0.27; doubled since the WS now drives the live values.
    refetchInterval: 60_000,
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
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["equity-history", brokerAccountId, days],
    queryFn: () =>
      api.get<EquityPoint[]>(
        `/api/account/equity-history?broker_account_id=${brokerAccountId}&days=${days}`,
      ),
    enabled: brokerAccountId != null,
  });

  // Live append on every /ws/equity tick - keeps the sparkline + chart
  // history growing in real time without a refetch. We drop the leading
  // point only when we'd exceed `days × 24` bars so the array doesn't
  // grow unbounded over a long session.
  useEffect(() => {
    if (brokerAccountId == null) return;
    return subscribe<{ ts: string; equity: number; balance: number; margin: number }>(
      "equity",
      (msg) => {
        qc.setQueryData<EquityPoint[]>(
          ["equity-history", brokerAccountId, days],
          (prev) => {
            if (!prev) return prev;
            const next: EquityPoint = {
              ts: msg.ts,
              equity: msg.equity,
              balance: msg.balance,
              drawdown_pct: 0,
            };
            const maxLen = days * 24;
            const merged = [...prev, next];
            return merged.length > maxLen ? merged.slice(-maxLen) : merged;
          },
        );
      },
    );
  }, [qc, brokerAccountId, days]);

  return q;
}

export function useTradingStatus() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["trading-status"],
    queryFn: () => api.get<TradingStatus>("/api/trading/status"),
    // 30 s fallback instead of 5 s - the WS subscription below pushes
    // mode/pause/trade-count/risk changes the moment they happen, so
    // we don't need to hammer REST. Polling stays as a safety net for
    // missed events (transient WS drops within the linger window).
    refetchInterval: 30_000,
  });

  useEffect(() => {
    return subscribe<{ type: string; [k: string]: unknown }>("signals", (msg) => {
      // Several event types push us toward a status change. Cheapest
      // way to stay accurate is to mark the query stale so it refetches
      // ONCE on the next render, instead of mirroring each field.
      const interesting = [
        "trade_opened", "kill_switch", "broker_down", "risk_block", "error",
      ];
      if (interesting.includes(msg.type)) {
        qc.invalidateQueries({ queryKey: ["trading-status"] });
      }
    });
  }, [qc]);

  return q;
}
