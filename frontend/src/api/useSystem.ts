import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface UpdateAsset {
  url: string;
  sha256: string;
  size: number;
}

export interface UpdateCheck {
  current_version: string;
  latest_version: string;
  has_update: boolean;
  released_at: string | null;
  notes: string | null;
  asset: UpdateAsset | null;
}

export interface VersionInfo {
  version: string;
  product: string;
  brand: string;
}

export function useVersion() {
  return useQuery({
    queryKey: ["system-version"],
    queryFn: () => api.get<VersionInfo>("/api/system/version"),
    staleTime: Infinity,
  });
}

export function useCheckUpdate() {
  return useMutation({
    mutationFn: () => api.post<UpdateCheck>("/api/system/check-update"),
  });
}
