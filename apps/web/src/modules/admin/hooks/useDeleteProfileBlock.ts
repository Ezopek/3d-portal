import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { ProfileImportRejection } from "@/lib/api-types";

/**
 * PROFILE-LIB-1 (AC-17) — the operator profile-block delete mutation.
 *
 * DELETEs `/admin/profiles/library/{block_id}` (204 on success). NO auto-retry on the write;
 * on success it invalidates the `["admin","profile-library"]` subtree so the list reconciles
 * from the server (no optimistic removal).
 */
export function useDeleteProfileBlock() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: (blockId) =>
      api<void>(`/admin/profiles/library/${blockId}`, { method: "DELETE" }),
    retry: false,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "profile-library"] });
    },
  });
}

/**
 * Extract the structured `reason_category` from a rejected library mutation, or `null`.
 *
 * Mirrors `importRejectionCategory` (33.2): the backend returns `{detail: {reason_category}}`
 * on a 4xx so the FE can localize *why* an op was rejected (admin fails closed/visible).
 */
export function libraryRejectionCategory(error: unknown): string | null {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: Partial<ProfileImportRejection> } | null)?.detail;
    if (detail && typeof detail.reason_category === "string") {
      return detail.reason_category;
    }
  }
  return null;
}
