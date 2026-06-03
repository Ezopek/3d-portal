import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RecomputeResponse } from "@/lib/api-types";
import {
  presetKey,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";

/**
 * EST-RECOMPUTE-1 — the guarded recompute-enqueue mutation hook.
 *
 * POSTs the SAME preset-resolution inputs `useEstimate` reads with to
 * `POST /api/estimates/recompute`, which resolves the preset to its bundle and enqueues an
 * idempotent by-hash re-slice (a record already `queued` is a server-side no-op — the R1
 * self-DoS guard, surfaced as `enqueued=false`). On success it invalidates the EXACT estimate
 * query key (`useEstimate`'s `["estimates", stlHash, presetKey, printerRef]`) so the display
 * refetches and reflects the new server state (`stale`→`queued`, an `absent`/`failed` key
 * stays honest until the worker fills it). It NEVER promises automatic live propagation.
 */
export function useRecomputeEstimate(
  stlHash: string,
  preset: PrintIntentPresetInput,
  printerRef: string,
) {
  const qc = useQueryClient();
  return useMutation<RecomputeResponse, Error, void>({
    mutationFn: () => {
      const body: Record<string, string> = {
        stl_hash: stlHash,
        material_class: preset.material_class,
        quality_tier: preset.quality_tier,
        printer_ref: printerRef,
      };
      if (preset.spoolman_filament_ref !== null) {
        body.spoolman_filament_ref = preset.spoolman_filament_ref;
      }
      return api<RecomputeResponse>("/estimates/recompute", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ["estimates", stlHash, presetKey(preset), printerRef],
      });
    },
  });
}
