import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface OnboardingStatus {
  first_run: boolean;
  vault_initialised: boolean;
  has_broker: boolean;
  has_strategy: boolean;
  is_running: boolean;
  next_step: "master_password" | "broker" | "strategy" | "start" | "done";
}

export interface MT5Server {
  name: string;
  broker: string | null;
  terminal_path: string | null;
}

export function useOnboardingStatus() {
  return useQuery({
    queryKey: ["onboarding-status"],
    queryFn: () => api.get<OnboardingStatus>("/api/onboarding/status"),
  });
}

export function useMt5Servers() {
  return useQuery({
    queryKey: ["mt5-servers"],
    queryFn: () => api.get<MT5Server[]>("/api/onboarding/mt5/servers"),
    staleTime: 60_000,
  });
}
