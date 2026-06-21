import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  OfferEstimateRecomputeRequest,
  OfferEstimateRecomputeResponse,
} from "@/lib/api-types";

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
