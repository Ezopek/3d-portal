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
      // Prefix-invalidate covers both ["catalog","models"] (list) and
      // ["catalog","models",id] (single) since useModel uses the same prefix.
      qc.invalidateQueries({ queryKey: ["catalog", "models"] });
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
    },
  });
}
