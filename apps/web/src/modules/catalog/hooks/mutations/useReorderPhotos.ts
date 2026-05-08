import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useReorderPhotos(modelId: string) {
  const qc = useQueryClient();
  return useMutation<{ ok: true }, Error, string[]>({
    mutationFn: (orderedIds) =>
      api<{ ok: true }>(
        `/admin/models/${modelId}/photos/reorder`,
        { method: "POST", body: JSON.stringify({ ordered_ids: orderedIds }) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "photos", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
    },
  });
}
