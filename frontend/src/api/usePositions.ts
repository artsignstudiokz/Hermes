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
    // 60 s safety net - the WS subscription below pushes the full
    // positions array on every worker tick, so polling is just for
    // recovery after a transient WS drop. Was 15 s before v1.0.27.
    refetchInterval: 60_000,
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
