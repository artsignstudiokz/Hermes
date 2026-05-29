import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ManualOrderInput, ManualOrderResult, TradingStatus } from "./types";

// Re-export legacy hook names so other call sites compile while we
// migrate to startProven/startAutonomous below.

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

export function useEnableTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TradingStatus>("/api/trading/enable-trading"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useStartProven() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (broker_account_id: number) =>
      api.post<TradingStatus, { broker_account_id: number }>(
        "/api/trading/start-proven", { broker_account_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useStartAutonomous() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (broker_account_id: number) =>
      api.post<TradingStatus, { broker_account_id: number }>(
        "/api/trading/start-autonomous", { broker_account_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useDisableTrading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TradingStatus>("/api/trading/disable-trading"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trading-status"] }),
  });
}

export function useTestOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ManualOrderInput) =>
      api.post<ManualOrderResult, ManualOrderInput>("/api/trading/test-order", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["account"] });
    },
  });
}

export interface AnalyzeReport {
  symbol: string;
  ts: string;
  direction: "long" | "short" | "flat";
  confidence: number;
  reason: string;
  contributing: Array<{
    strategy: string;
    direction: string;
    confidence: number;
    reason: string;
  }>;
  indicators: Record<string, number>;
}

export interface AnalyzeResult {
  opened: boolean;
  reason: string;
  ticket: string | null;
  best: AnalyzeReport | null;
  reports: AnalyzeReport[];
}

export function useAnalyze() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { lot_size?: number; dry_run?: boolean }) =>
      api.post<AnalyzeResult, { lot_size: number; dry_run: boolean }>(
        "/api/trading/analyze",
        { lot_size: input.lot_size ?? 0.01, dry_run: input.dry_run ?? false },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["account"] });
    },
  });
}
