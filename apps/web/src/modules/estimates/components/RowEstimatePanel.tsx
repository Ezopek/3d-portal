import { FileQuestion } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/lib/api";

import { EstimateDisplay } from "@/modules/estimates/components/EstimateDisplay";
import { useEstimate } from "@/modules/estimates/hooks/useEstimate";
import { useOfferEstimate } from "@/modules/estimates/hooks/useOfferEstimate";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { EmptyState } from "@/ui/custom/EmptyState";

interface Props {
  /** `ModelFileRead.sha256` of the STL. Empty ⇒ no read, honest no-hash empty state. */
  stlHash: string;
  preset: PrintIntentPresetInput;
  printerRef: string;
  enabled?: boolean;
  /** Story 36.3 (AC-5) — when provided, switches the panel to offer mode. */
  offerId?: string | null;
}

/**
 * EST-DISPLAY-1 (UX §C) + Story 36.3 (AC-5) — the expanded-row estimate breakdown.
 *
 * When `offerId` is provided, switches to offer mode: uses `useOfferEstimate` instead of
 * `useEstimate`. The two modes share the same `EstimateDisplay` render path; the cache key
 * differs so switching "None" ↔ offer never serves stale cross-mode values.
 */
export function RowEstimatePanel({
  stlHash,
  preset,
  printerRef,
  enabled = true,
  offerId,
}: Props) {
  const { t } = useTranslation();
  // Story 36.3 (AC-5): always call both hooks; disabled by their own enabled gates.
  const presetQuery = useEstimate(stlHash, preset, printerRef, {
    enabled: enabled && !offerId,
  });
  const offerQuery = useOfferEstimate(stlHash, offerId ?? "");
  const query = offerId ? offerQuery : presetQuery;

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

  // §E.7 — offer 404: the selected offer was unpublished since selection.
  if (
    offerId &&
    query.isError &&
    query.error instanceof ApiError &&
    query.error.status === 404
  ) {
    return (
      <div role="status" className="rounded-lg border p-4">
        <p className="font-medium">
          {t("modules.member.offers.estimate.offer_unavailable_title")}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("modules.member.offers.estimate.offer_unavailable_detail")}
        </p>
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
