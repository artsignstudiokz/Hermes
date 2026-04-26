import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface OptimizeStartInput {
  base_params: Record<string, unknown>;
  symbols: string[];
  n_trials?: number;
  days?: number;
}

export function useStartOptimize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: OptimizeStartInput) =>
      api.post<{ run_id: number }, OptimizeStartInput>("/api/optimize/run", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backtest-runs"] }),
  });
}

export function useApplyOptimize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) =>
      api.post<{ id: number; name: string; payload: Record<string, unknown> }>(
        `/api/optimize/${runId}/apply`,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["strategy-config"] });
      qc.invalidateQueries({ queryKey: ["backtest-runs"] });
    },
  });
}
