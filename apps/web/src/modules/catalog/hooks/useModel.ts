import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ModelDetail } from "@/lib/api-types";

export function useModel(id: string) {
  return useQuery<ModelDetail>({
    queryKey: ["sot", "models", id],
    queryFn: () => api<ModelDetail>(`/models/${id}`),
    staleTime: 30 * 1000,
  });
}
