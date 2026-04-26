import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type Regime = "trend" | "flat" | "high_vol";

export interface PairRegime {
  symbol: string;
  regime: Regime;
  adx: number;
  atr_pct: number;
  ema_aligned: boolean;
  hurst: number | null;
  confidence: number;
}

export interface GlobalRegime {
  regime: Regime;
  counts: Record<string, number>;
  per_pair: PairRegime[];
}

export interface CalibrationRun {
  id: number;
  ts: string;
  regime: string;
  challenger_won: boolean;
  applied: boolean;
  walk_forward_score: number;
  before_params: Record<string, unknown>;
  after_params: Record<string, unknown>;
}

export function useRegime() {
  return useQuery({
    queryKey: ["regime"],
    queryFn: () => api.get<GlobalRegime>("/api/adaptive/regime"),
    refetchInterval: 5 * 60_000,
    retry: false,
  });
}

export function useCalibrationRuns(limit = 20) {
  return useQuery({
    queryKey: ["calibration-runs", limit],
    queryFn: () => api.get<CalibrationRun[]>(`/api/adaptive/calibration/runs?limit=${limit}`),
  });
}

export function useRunCalibrationNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ started: boolean }>("/api/adaptive/calibration/run-now"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calibration-runs"] }),
  });
}

export function useRollbackCalibration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>("/api/adaptive/calibration/rollback"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calibration-runs"] });
      qc.invalidateQueries({ queryKey: ["strategy-config"] });
    },
  });
}
