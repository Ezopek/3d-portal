import { FileQuestion } from "lucide-react";

import { EstimateDisplay } from "@/modules/estimates/components/EstimateDisplay";
import { useEstimate } from "@/modules/estimates/hooks/useEstimate";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { EmptyState } from "@/ui/custom/EmptyState";

interface Props {
  /** `ModelFileRead.sha256` of the STL. Empty ⇒ no read, honest no-hash empty state. */
  stlHash: string;
  preset: PrintIntentPresetInput;
  printerRef: string;
}

/**
 * EST-DISPLAY-1 (UX §C) — the expanded-row estimate breakdown.
 *
 * A thin wrapper that binds the FilesTab GLOBAL preset to the shipped Story 32.6
 * `EstimateDisplay`. It shares the `useEstimate` query key with the row's `EstimateChip`
 * (same `stlHash + preset + printerRef`), so the panel reuses the chip's already-cached read —
 * one network request per `(hash, preset)`, not two. Read-only: it renders the server
 * cache/recompute state as-is; there is no recompute affordance.
 */
export function RowEstimatePanel({ stlHash, preset, printerRef }: Props) {
  const query = useEstimate(stlHash, preset, printerRef);

  // No hash ⇒ the read seam was never engaged; show the honest no-hash state rather than a
  // perpetual spinner (a disabled query stays `isPending`).
  if (stlHash.length === 0) {
    return (
      <div role="status" className="rounded-lg border p-2">
        <EmptyState
          messageKey="modules.estimates.chip.no_hash"
          tone="muted"
          icon={<FileQuestion className="size-8" />}
        />
      </div>
    );
  }

  return (
    <EstimateDisplay
      isPending={query.isPending}
      isError={query.isError}
      data={query.data}
      onRetry={() => void query.refetch()}
    />
  );
}
