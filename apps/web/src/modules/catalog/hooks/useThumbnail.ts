import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useSetThumbnail(modelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) =>
      api<void>(
        `/admin/models/${modelId}/thumbnail`,
        { method: "PUT", body: JSON.stringify({ path }) },
        { authenticated: true },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["catalog", "models"] });
      qc.invalidateQueries({ queryKey: ["catalog", "model", modelId] });
    },
  });
}

export function useClearThumbnail(modelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<void>(
        `/admin/models/${modelId}/thumbnail`,
        { method: "DELETE" },
        { authenticated: true },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["catalog", "models"] });
      qc.invalidateQueries({ queryKey: ["catalog", "model", modelId] });
    },
  });
}
