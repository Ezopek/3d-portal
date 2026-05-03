import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface RenderSelectionResponse {
  paths: string[];
  available_stls: string[];
}

export function useRenderSelection(modelId: string, opts: { enabled: boolean }) {
  return useQuery<RenderSelectionResponse>({
    queryKey: ["renderSelection", modelId],
    queryFn: () =>
      api<RenderSelectionResponse>(
        `/admin/models/${modelId}/render-selection`,
        {},
        { authenticated: true },
      ),
    enabled: opts.enabled,
  });
}

export function useSetRenderSelection(modelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (paths: string[]) =>
      api<void>(
        `/admin/models/${modelId}/render-selection`,
        { method: "PUT", body: JSON.stringify({ paths }) },
        { authenticated: true },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renderSelection", modelId] });
      qc.invalidateQueries({ queryKey: ["catalog", "models", modelId] });
      qc.invalidateQueries({ queryKey: ["catalog", "models"] });
    },
  });
}
