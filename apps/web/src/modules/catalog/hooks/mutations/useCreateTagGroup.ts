import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { TagGroupSummary } from "@/lib/api-types";

// POST /admin/tag-groups (Story 46.2) — create an empty facet group. `position`
// is sent explicitly (appended at the end of the current group list).
export interface CreateTagGroupInput {
  slug: string;
  name_en: string;
  name_pl?: string | null;
  position?: number;
}

export function useCreateTagGroup() {
  const qc = useQueryClient();
  return useMutation<TagGroupSummary, ApiError, CreateTagGroupInput>({
    mutationFn: (input) =>
      api<TagGroupSummary>("/admin/tag-groups", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sot", "tag-groups"] });
    },
  });
}
