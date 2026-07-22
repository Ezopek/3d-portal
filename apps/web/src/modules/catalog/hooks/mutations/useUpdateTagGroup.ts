import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { TagGroupSummary } from "@/lib/api-types";

// PATCH /admin/tag-groups/{id} (Story 46.2) — backs group rename (name_en/name_pl)
// and reorder (position adjacent-swap). Only changed fields are sent; `name_pl: null`
// clears the Polish name. `slug`/`name_en`/`position` must never be explicit null.
export interface TagGroupPatchBody {
  slug?: string;
  name_en?: string;
  name_pl?: string | null;
  position?: number;
}

export function useUpdateTagGroup() {
  const qc = useQueryClient();
  return useMutation<TagGroupSummary, ApiError, { id: string; body: TagGroupPatchBody }>({
    mutationFn: ({ id, body }) =>
      api<TagGroupSummary>(`/admin/tag-groups/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tag-groups"] });
    },
  });
}
