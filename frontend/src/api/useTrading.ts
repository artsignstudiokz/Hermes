import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TradingStatus } from "./types";

export function useStartTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (broker_account_id: number) =>
      api.post<TradingStatus, { broker_account_id: number }>("/api/trading/start", {
        broker_account_id,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useStopTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TradingStatus>("/api/trading/stop"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function usePauseTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TradingStatus>("/api/trading/pause"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useResumeTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TradingStatus>("/api/trading/resume"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ closed_count: number }>("/api/trading/kill-switch"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["trading-status"] });
    },
  });
}
