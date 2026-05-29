import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SpoolsSummaryResponse } from "@/lib/api-types";

export function useSpoolsSummary() {
  return useQuery<SpoolsSummaryResponse>({
    queryKey: ["spools", "summary"],
    queryFn: () => api<SpoolsSummaryResponse>("/spools/summary"),
    // because "FR19-CACHE-1 freshness budget is 60s; matches arq poll cadence — Decision AD"
    staleTime: 60_000,
    // because "keep snapshot in memory across /spools <-> landing card transitions — Decision AD"
    gcTime: 5 * 60_000,
  });
}
