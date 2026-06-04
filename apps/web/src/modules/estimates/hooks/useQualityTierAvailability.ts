import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { MaterialClass, QualityTier } from "@/lib/api-types";

export interface QualityTierAvailability {
  quality_tier: QualityTier;
  available: boolean;
  reason: "profile_not_imported" | string | null;
}

interface QualityTierAvailabilityResponse {
  printer_ref: string;
  material_class: MaterialClass;
  tiers: QualityTierAvailability[];
}

const AVAILABILITY_STALE_TIME_MS = 5 * 60_000;

/**
 * EST-TIERS-1 — backend-derived process-profile availability for the compact
 * Catalog Files/STL selector. The selector must not probe unavailable tiers by
 * firing estimate reads; it asks this read contract first and disables missing
 * profiles in-place.
 */
export function useQualityTierAvailability(
  materialClass: MaterialClass,
  printerRef: string,
) {
  return useQuery<QualityTierAvailabilityResponse>({
    queryKey: ["estimates", "quality-tiers", materialClass, printerRef],
    queryFn: () => {
      const params = new URLSearchParams({
        material_class: materialClass,
        printer_ref: printerRef,
      });
      return api<QualityTierAvailabilityResponse>(`/estimates/quality-tiers?${params}`);
    },
    enabled: materialClass.length > 0 && printerRef.length > 0,
    staleTime: AVAILABILITY_STALE_TIME_MS,
  });
}
