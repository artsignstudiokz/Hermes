import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { api } from "@/lib/api";
import { subscribe } from "@/lib/ws";
import type { Position } from "./types";

export function usePositions() {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["positions"],
    queryFn: () => api.get<Position[]>("/api/positions"),
    refetchInterval: 15_000,
  });

  useEffect(() => {
    return subscribe<Position[]>("positions", (next) => {
      qc.setQueryData(["positions"], next);
    });
  }, [qc]);

  return q;
}

export async function closePosition(ticket: string): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>(`/api/positions/${encodeURIComponent(ticket)}/close`);
}
