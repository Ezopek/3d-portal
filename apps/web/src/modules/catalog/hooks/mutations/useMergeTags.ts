import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { TagRead } from "@/lib/api-types";

// POST /admin/tags/merge (Story 46.2) — `from` is the source (deleted), `to` is
// the survivor. Invalidates both tag-groups and tags so the merged-away source
// disappears from the list on refresh.
export interface MergeTagsInput {
  from_id: string;
  to_id: string;
}

export function useMergeTags() {
  const qc = useQueryClient();
  return useMutation<TagRead, ApiError, MergeTagsInput>({
    mutationFn: (input) =>
      api<TagRead>("/admin/tags/merge", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tag-groups"] });
      void qc.invalidateQueries({ queryKey: ["sot", "tags"] });
    },
  });
}
