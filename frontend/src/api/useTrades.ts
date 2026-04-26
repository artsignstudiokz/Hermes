import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Trade, TradeStats } from "./types";

export function useTrades(opts: { days?: number; symbol?: string; limit?: number } = {}) {
  const { days = 30, symbol, limit = 200 } = opts;
  const q = new URLSearchParams({ days: String(days), limit: String(limit) });
  if (symbol) q.set("symbol", symbol);
  return useQuery({
    queryKey: ["trades", days, symbol, limit],
    queryFn: () => api.get<Trade[]>(`/api/trades?${q.toString()}`),
  });
}

export function useTradeStats(days = 30) {
  return useQuery({
    queryKey: ["trade-stats", days],
    queryFn: () => api.get<TradeStats>(`/api/trades/stats?days=${days}`),
  });
}
