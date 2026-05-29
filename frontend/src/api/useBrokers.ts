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

export interface BrokerHealth {
  connected: boolean;
  balance?: number;
  equity?: number;
  currency?: string;
  server?: string;
  reason?: string;
}

export function useBrokerHealth(id: number | null) {
  return useQuery({
    queryKey: ["broker-health", id],
    queryFn: () => api.get<BrokerHealth>(`/api/brokers/${id}/health`),
    enabled: id != null,
    refetchInterval: 15_000,    // poll every 15s so silent drops surface fast
    retry: 0,
  });
}

export function useReconnectBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<BrokerHealth>(`/api/brokers/${id}/reconnect`),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["broker-health", id] });
      qc.invalidateQueries({ queryKey: ["account"] });
      qc.invalidateQueries({ queryKey: ["positions"] });
    },
  });
}
