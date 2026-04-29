import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

import type { Model } from "../types";

export function useModel(id: string) {
  return useQuery<Model>({
    queryKey: ["catalog", "models", id],
    queryFn: () => api<Model>(`/catalog/models/${id}`),
  });
}
