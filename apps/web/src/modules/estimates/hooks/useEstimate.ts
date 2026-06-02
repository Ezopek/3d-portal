import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { EstimateView } from "@/lib/api-types";
import {
  presetKey,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

// because "the FR20-CACHE-1 estimate freshness cadence — match the estimate cache/recompute
// cadence so the UI doesn't refetch faster than the server can change state. The estimate
// cache only changes when a (re)slice completes on the worker, which is no faster than the
// Init 19 Spoolman poll cadence, so 60s is a safe lower bound on how often a new value can
// appear; this mirrors the useSpoolsSummary 60s/5min Decision-AD pattern rather than copying
// it blindly — both point to the same upstream refresh budget." (AC-11)
const ESTIMATE_STALE_TIME_MS = 60_000;
// because "keep the snapshot in memory across selector toggles / route transitions so a
// re-key back to a prior preset is instant — Decision AD gcTime convention."
const ESTIMATE_GC_TIME_MS = 5 * 60_000;

/**
 * Story 32.6 (AC-3) — the typed estimate read hook.
 *
 * Re-keyed on `stlHash` + the full preset (via `presetKey`) + `printerRef`: any selector
 * change resolves to a different bundle, hence a different estimate, hence a new cache key
 * (a stale key would show another preset's numbers). Read-only — the hook never enqueues or
 * recomputes (AC-1b is deferred); it reflects the server cache/recompute state as it is.
 *
 * The `status` the UI branches on lives in the response body (`fresh`/`stale`/`queued`/
 * `failed`/`absent`); `isPending`/`isError` are the query/transport states the FE owns.
 */
export function useEstimate(
  stlHash: string,
  preset: PrintIntentPresetInput,
  printerRef: string,
) {
  return useQuery<EstimateView>({
    queryKey: ["estimates", stlHash, presetKey(preset), printerRef],
    queryFn: () => {
      const params = new URLSearchParams({
        stl_hash: stlHash,
        material_class: preset.material_class,
        quality_tier: preset.quality_tier,
        printer_ref: printerRef,
      });
      if (preset.spoolman_filament_ref !== null) {
        params.set("spoolman_filament_ref", preset.spoolman_filament_ref);
      }
      return api<EstimateView>(`/estimates?${params.toString()}`);
    },
    staleTime: ESTIMATE_STALE_TIME_MS,
    gcTime: ESTIMATE_GC_TIME_MS,
    // No stl_hash ⇒ nothing to resolve; do not fire a request that would 422.
    enabled: stlHash.length > 0 && printerRef.length > 0,
  });
}
