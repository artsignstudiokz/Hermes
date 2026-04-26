import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Broker, BrokerTestResult } from "./types";

export interface BrokerCreateInput {
  name: string;
  type: "mt5" | "binance" | "bybit" | "okx";
  server?: string;
  login?: number;
  password?: string;
  api_key?: string;
  api_secret?: string;
  api_passphrase?: string;
  testnet?: boolean;
}

export function useBrokers() {
  return useQuery({
    queryKey: ["brokers"],
    queryFn: () => api.get<Broker[]>("/api/brokers"),
  });
}

export function useTestBroker() {
  return useMutation({
    mutationFn: (input: Omit<BrokerCreateInput, "name">) =>
      api.post<BrokerTestResult, Omit<BrokerCreateInput, "name">>("/api/brokers/test", input),
  });
}

export function useCreateBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BrokerCreateInput) =>
      api.post<Broker, BrokerCreateInput>("/api/brokers", input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brokers"] }),
  });
}

export function useDeleteBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/brokers/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brokers"] }),
  });
}

export function useActivateBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<Broker>(`/api/brokers/${id}/activate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brokers"] }),
  });
}
