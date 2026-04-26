import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Preset, StrategyConfig, StrategyParams, ValidationResult } from "./types";

export function usePresets() {
  return useQuery({
    queryKey: ["presets"],
    queryFn: () => api.get<Preset[]>("/api/strategy/presets"),
    staleTime: Infinity,
  });
}

export function useStrategyConfig() {
  return useQuery({
    queryKey: ["strategy-config"],
    queryFn: () => api.get<StrategyConfig | null>("/api/strategy/config"),
  });
}

export function useSaveStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: StrategyParams) =>
      api.put<StrategyConfig, StrategyParams>("/api/strategy/config", params),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategy-config"] }),
  });
}

export function useValidateStrategy() {
  return useMutation({
    mutationFn: (params: StrategyParams) =>
      api.post<ValidationResult, StrategyParams>("/api/strategy/validate", params),
  });
}
