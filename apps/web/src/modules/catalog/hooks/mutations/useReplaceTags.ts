import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { TagRead } from "@/lib/api-types";

export function useReplaceTags(modelId: string) {
  const qc = useQueryClient();
  return useMutation<TagRead[], Error, string[]>({
    mutationFn: (tagIds) =>
      api<TagRead[]>(
        `/admin/models/${modelId}/tags`,
        { method: "PUT", body: JSON.stringify({ tag_ids: tagIds }) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}
