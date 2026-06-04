import { AlertTriangle, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { SpoolIcon } from "@/modules/estimates/components/SpoolIcon";
import { useEstimate } from "@/modules/estimates/hooks/useEstimate";
import { EM_DASH, formatMass } from "@/modules/estimates/lib/format";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";

interface Props {
  /**
   * The STL content hash (`ModelFileRead.sha256`) — the `stl_hash` the estimate is read by
   * (EST-INGEST-1 proved `sha256 == compute_stl_hash` for `kind=stl`). When empty, NO
   * `GET /api/estimates` request fires (the hook self-disables) and the chip shows the honest
   * no-hash state — never a spurious request that would 422.
   */
  stlHash: string;
  preset: PrintIntentPresetInput;
  printerRef: string;
  enabled?: boolean;
}

/**
 * EST-DISPLAY-1 (UX §B) — the inline, grams-only, collapsed-row estimate chip.
 *
 * Reuses the Story 32.6 `useEstimate` read seam and `formatMass` formatter 1:1. Renders every
 * state HONESTLY and mutually-exclusively (UX state table): no-hash / loading / absent / fresh /
 * stale / queued / failed / network-error. Grams ONLY (cost/time/length/volume live in the
 * expanded panel) and never silent-zero (`formatMass` em-dashes a missing/non-finite value).
 *
 * It is NON-INTERACTIVE (a `<span>`, never focusable) — the chip never triggers a recompute
 * (EST-RECOMPUTE-1 is deferred). State is signalled by glyph + text + color, never color alone.
 */
export function EstimateChip({ stlHash, preset, printerRef, enabled = true }: Props) {
  const { t } = useTranslation();
  // Always called (rules of hooks); self-disables when `stlHash` is empty or the parent
  // availability gate has not confirmed the selected slot is offerable.
  const query = useEstimate(stlHash, preset, printerRef, { enabled });

  const base =
    "inline-flex shrink-0 items-center justify-end gap-1 tabular-nums text-xs";

  // 1) no-hash — nothing to read; no request was fired. Honest, distinct from a store miss.
  if (stlHash.length === 0) {
    return (
      <ChipShell title={t("modules.estimates.chip.no_hash")} className={base}>
        <SpoolIcon className="size-3.5 text-muted-foreground/60" />
        <span className="text-muted-foreground">{EM_DASH}</span>
      </ChipShell>
    );
  }

  // 2) transport error — retryable upstream; the chip stays quiet, the panel owns Retry.
  if (query.isError) {
    return (
      <ChipShell title={t("modules.estimates.chip.error")} className={base}>
        <AlertTriangle className="size-3.5 text-destructive" aria-hidden />
        <span className="text-destructive">{EM_DASH}</span>
      </ChipShell>
    );
  }

  // 3) loading — skeleton in the chip slot; never flash absent/failed (aria-busy).
  if (query.isPending) {
    return (
      <span
        role="status"
        aria-busy="true"
        aria-label={t("modules.estimates.chip.loading")}
        className={cn(base, "text-muted-foreground")}
      >
        <SpoolIcon className="size-3.5 text-muted-foreground/40" />
        <span className="h-3 w-8 animate-pulse rounded bg-muted" />
      </span>
    );
  }

  const data = query.data;

  // 4) absent — explicit "no estimate yet" store miss, distinct from failed/error.
  if (data.status === "absent") {
    return (
      <ChipShell title={t("modules.estimates.chip.absent")} className={base}>
        <SpoolIcon className="size-3.5 text-muted-foreground/60" />
        <span className="text-muted-foreground">{EM_DASH}</span>
      </ChipShell>
    );
  }

  // 5) failed — "couldn't estimate"; numeric is em-dash, paired with an alert glyph.
  if (data.status === "failed") {
    return (
      <ChipShell title={t("modules.estimates.chip.failed")} className={base}>
        <AlertTriangle className="size-3.5 text-destructive" aria-hidden />
        <span className="text-destructive">{EM_DASH}</span>
      </ChipShell>
    );
  }

  // 6) fresh / stale / queued — last-known grams + an honest accent/glyph.
  const mass = formatMass(data.filament_g);

  if (data.status === "stale") {
    return (
      <ChipShell
        title={t("modules.estimates.chip.stale", { mass })}
        className={base}
      >
        <SpoolIcon className="size-3.5 text-warning" />
        <span className="text-warning">{mass}</span>
        {/* Non-color stale signal so color-blind users aren't reliant on hue. */}
        <span
          className="size-1.5 shrink-0 rounded-full bg-warning"
          aria-hidden
        />
      </ChipShell>
    );
  }

  if (data.status === "queued") {
    const hasValue = mass !== EM_DASH;
    return (
      <ChipShell
        title={
          hasValue
            ? t("modules.estimates.chip.queued", { mass })
            : t("modules.estimates.chip.queued_no_value")
        }
        className={cn(base, "text-muted-foreground")}
      >
        <SpoolIcon className="size-3.5 text-muted-foreground" />
        <span>{mass}</span>
        <Loader2 className="size-3 shrink-0 animate-spin" aria-hidden />
      </ChipShell>
    );
  }

  // fresh
  return (
    <ChipShell
      title={t("modules.estimates.chip.fresh", { mass })}
      className={base}
    >
      <SpoolIcon className="size-3.5 text-muted-foreground" />
      <span className="font-medium text-foreground">{mass}</span>
    </ChipShell>
  );
}

/**
 * The non-interactive chip wrapper. A `<span>` with an accessible label equal to the visible
 * `title`, so the state is conveyed without making a non-actionable element focusable.
 */
function ChipShell({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span title={title} aria-label={title} className={className}>
      {children}
    </span>
  );
}
