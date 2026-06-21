import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  DefaultMatrixBackfillRequest,
  DefaultMatrixBackfillResponse,
  MaterialDefaultUpsert,
  OfferEstimateRecomputeRequest,
  OfferEstimateRecomputeResponse,
  PolicyAdminView,
} from "@/lib/api-types";

const POLICY_QUERY_KEY = ["admin", "profile-policy"] as const;

export function useProfilePolicy(enabled = true) {
  return useQuery<PolicyAdminView>({
    queryKey: POLICY_QUERY_KEY,
    queryFn: () => api<PolicyAdminView>("/admin/policy"),
    staleTime: 0,
    refetchOnMount: "always",
    // The panel is collapsed by default; only fetch policy once the operator opens it
    // (saves an admin API call on every offers-page load and keeps the collapsed
    // panel a stable height — no loading→loaded layout shift).
    enabled,
  });
}

export function useUpsertMaterialDefault() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      material,
      body,
    }: {
      material: string;
      body: MaterialDefaultUpsert;
    }) =>
      api<PolicyAdminView>(
        `/admin/policy/material-defaults/${encodeURIComponent(material)}`,
        {
          method: "PUT",
          body: JSON.stringify(body),
        },
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(POLICY_QUERY_KEY, data);
      void queryClient.invalidateQueries({
        queryKey: ["admin", "profile-policy"],
      });
    },
  });
}

export function useDeleteMaterialDefault() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (material: string) =>
      api<void>(
        `/admin/policy/material-defaults/${encodeURIComponent(material)}`,
        {
          method: "DELETE",
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["admin", "profile-policy"],
      });
    },
  });
}

export function useDefaultMatrixBackfill() {
  return useMutation<
    DefaultMatrixBackfillResponse,
    Error,
    DefaultMatrixBackfillRequest
  >({
    mutationFn: (body) =>
      api<DefaultMatrixBackfillResponse>(
        "/admin/policy/default-matrix-backfill",
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
  });
}

export function useOfferEstimateRecompute() {
  return useMutation<
    OfferEstimateRecomputeResponse,
    Error,
    OfferEstimateRecomputeRequest
  >({
    mutationFn: (body) =>
      api<OfferEstimateRecomputeResponse>(
        "/admin/profiles/offers/recompute-estimates",
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
  });
}
