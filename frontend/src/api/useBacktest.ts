import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface BacktestRun {
  id: number;
  status: "pending" | "running" | "done" | "error";
  params: Record<string, unknown>;
  metrics: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface BacktestStartInput {
  params: Record<string, unknown>;
  symbols: string[];
  days?: number;
}

export function useBacktestRuns(limit = 20) {
  return useQuery({
    queryKey: ["backtest-runs", limit],
    queryFn: () => api.get<BacktestRun[]>(`/api/backtest/runs?limit=${limit}`),
    refetchInterval: 5_000,
  });
}

export function useBacktestRun(runId: number | null) {
  return useQuery({
    queryKey: ["backtest-run", runId],
    queryFn: () => api.get<BacktestRun>(`/api/backtest/${runId}`),
    enabled: runId !== null,
    refetchInterval: 2_000,
  });
}

export function useStartBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BacktestStartInput) =>
      api.post<{ run_id: number }, BacktestStartInput>("/api/backtest/run", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backtest-runs"] }),
  });
}
