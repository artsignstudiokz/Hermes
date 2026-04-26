import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface TunnelStatus {
  active: boolean;
  url: string | null;
  qr: string | null;        // data:image/png;base64,...
  pin: string | null;
  pin_age_hours: number;
}

export function useTunnelStatus() {
  return useQuery({
    queryKey: ["tunnel-status"],
    queryFn: () => api.get<TunnelStatus>("/api/tunnel/status"),
    refetchInterval: 10_000,
  });
}

export function useStartTunnel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TunnelStatus>("/api/tunnel/start"),
    onSuccess: (data) => qc.setQueryData(["tunnel-status"], data),
  });
}

export function useStopTunnel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ ok: boolean }>("/api/tunnel/stop"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tunnel-status"] }),
  });
}

export function useRegenPin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<TunnelStatus>("/api/tunnel/regenerate-pin"),
    onSuccess: (data) => qc.setQueryData(["tunnel-status"], data),
  });
}
