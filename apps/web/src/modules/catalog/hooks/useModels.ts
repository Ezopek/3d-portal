import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

import type { ModelListResponse } from "../types";

export function useModels() {
  return useQuery<ModelListResponse>({
    queryKey: ["catalog", "models"],
    queryFn: () => api<ModelListResponse>("/catalog/models"),
  });
}
