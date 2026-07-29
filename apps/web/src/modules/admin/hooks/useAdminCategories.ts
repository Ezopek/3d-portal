import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { BrowseCategoryAdminRead, BrowseCategorySummary } from "@/lib/api-types";

// Story 52.2 — the admin browse-category governance surface.
//
// The read is a SIBLING key of the shipped public `["sot", "categories"]`, not
// a child (D-12). A child would be swept by the public prefix invalidation —
// convenient here, but it would also make every member's browse-rail
// invalidation refetch an admin-only endpoint they cannot call. Every write
// below therefore invalidates BOTH keys explicitly.
const ADMIN_KEY = ["sot", "admin-categories"] as const;
const PUBLIC_KEY = ["sot", "categories"] as const;

export function useAdminCategories() {
  return useQuery<BrowseCategoryAdminRead[]>({
    queryKey: ADMIN_KEY,
    queryFn: () => api<BrowseCategoryAdminRead[]>("/admin/categories"),
    // Deliberately shorter than the public list's 5 min: this is the surface an
    // admin edits, so it must reflect their own writes and a concurrent admin's
    // writes promptly. Under the accepted last-writer-wins posture (Decision AY)
    // a fresher read is the only mitigation the contract actually offers.
    staleTime: 10 * 1000,
  });
}

function invalidateCategories(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ADMIN_KEY });
  void qc.invalidateQueries({ queryKey: PUBLIC_KEY });
}

export interface BrowseCategoryCreateBody {
  slug: string;
  name_en: string;
  name_pl: string | null;
  inclusion_criterion: string | null;
  position: number;
}

export function useCreateBrowseCategory() {
  const qc = useQueryClient();
  return useMutation<BrowseCategoryAdminRead, ApiError, BrowseCategoryCreateBody>({
    mutationFn: (body) =>
      api<BrowseCategoryAdminRead>("/admin/categories", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateCategories(qc),
  });
}

// PATCH is `extra="forbid"` server-side and only sends changed fields. An
// explicit null CLEARS `name_pl` / `inclusion_criterion`; `slug`, `name_en` and
// `position` are NOT NULL and an explicit null on them is a 422.
export interface BrowseCategoryPatchBody {
  slug?: string;
  name_en?: string;
  name_pl?: string | null;
  inclusion_criterion?: string | null;
  position?: number;
}

export function useUpdateBrowseCategory() {
  const qc = useQueryClient();
  return useMutation<
    BrowseCategoryAdminRead,
    ApiError,
    { id: string; body: BrowseCategoryPatchBody }
  >({
    mutationFn: ({ id, body }) =>
      api<BrowseCategoryAdminRead>(`/admin/categories/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      invalidateCategories(qc);
      // `ModelDetail.categories` embeds `name_en`/`name_pl`/`position` via
      // `BrowseCategorySummary`, and `useModel` holds them for 30s — so without
      // this a rename or a reorder leaves every mounted model view rendering the
      // old label. The delete hook below already does this; the divergence was
      // the bug, not the extra invalidation.
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}

// `detach` is NEVER implicit: the first delete attempt always omits it, so a
// category with assignments returns 409 and the admin makes a second, explicit
// decision. That is FR26-ADMIN-1's "never a silent cascade" at the client edge.
export function useDeleteBrowseCategory() {
  const qc = useQueryClient();
  return useMutation<void, ApiError, { id: string; detach?: boolean }>({
    mutationFn: ({ id, detach }) =>
      api<void>(`/admin/categories/${id}${detach ? "?detach=true" : ""}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      invalidateCategories(qc);
      // A detach changes model membership, so the queue and every model page
      // that could have carried this category are now stale.
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
    },
  });
}

// Whole-set replace, explicit last-writer-wins. There is no precondition to
// send — no `revision`, no `If-Match` — because the shipped contract has none
// (Decision AY). Do not invent one here.
export function useReplaceModelCategories(modelId: string) {
  const qc = useQueryClient();
  return useMutation<BrowseCategorySummary[], ApiError, string[]>({
    mutationFn: (categoryIds) =>
      api<BrowseCategorySummary[]>(`/admin/models/${modelId}/categories`, {
        method: "PUT",
        body: JSON.stringify({ category_ids: categoryIds }),
      }),
    onSuccess: () => {
      // Counts moved, so both category lists are stale.
      invalidateCategories(qc);
      void qc.invalidateQueries({ queryKey: ["sot", "models", modelId] });
      void qc.invalidateQueries({ queryKey: ["sot", "models"] });
      // The write just became the newest audited category change, so the
      // last-writer note must not keep showing the previous one.
      void qc.invalidateQueries({ queryKey: ["sot", "audit-log"] });
    },
  });
}
