import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { TagRead } from "@/lib/api-types";

// PATCH /admin/tags/{id} — partial body (Story 46.2). Only changed fields are
// sent; `name_pl: null` clears the Polish name and `group_id: null` makes the
// tag groupless. `slug`/`name_en`/`group_position` must never be explicit null
// (the backend 422s on those). When moving into a container, callers set
// `group_position` explicitly to the target's current tag count (append at end).
export interface TagPatchBody {
  slug?: string;
  name_en?: string;
  name_pl?: string | null;
  group_id?: string | null;
  group_position?: number;
}

export function useUpdateTag() {
  const qc = useQueryClient();
  return useMutation<TagRead, ApiError, { id: string; body: TagPatchBody }>({
    mutationFn: ({ id, body }) =>
      api<TagRead>(`/admin/tags/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tag-groups"] });
      void qc.invalidateQueries({ queryKey: ["sot", "tags"] });
    },
  });
}
