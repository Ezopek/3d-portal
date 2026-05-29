import type { FilamentView, SpoolView } from "@/lib/api-types";

// because "operator UX preference at MVP-A — ≤200g treated as 'low' on a
// standard 1 kg spool; Story 31.5 documents the value in operations.md
// addendum (no env override in MVP-A by design; promote to env if operator
// wants runtime tuning)"
export const LOW_STOCK_THRESHOLD_G = 200;

// because "operator UX preference — keep the card compact; a 5-spool list
// fits the dashboard hero without a scroll bar at the desktop breakpoint"
export const LOW_STOCK_LIST_CAP = 5;

export interface LowStockRow {
  spool: SpoolView;
  filament: FilamentView | undefined;
}

export function selectLowStockRows(
  spools: SpoolView[],
  filaments: FilamentView[],
): LowStockRow[] {
  const filamentById = new Map(filaments.map((f) => [f.id, f]));
  // The threshold is intentionally strict (`<`, not `<=`) — a spool at
  // exactly 200g is on the boundary, not yet "below"; operator UX
  // preference per Story 31.4 review round 1. If the operator later
  // changes the boundary semantic, flip the comparator AND update the
  // boundary test case in LowStockCard.test.tsx.
  const filtered = spools.filter(
    (s) =>
      !s.archived && s.remaining_weight !== null && s.remaining_weight < LOW_STOCK_THRESHOLD_G,
  );
  filtered.sort((a, b) => (a.remaining_weight ?? 0) - (b.remaining_weight ?? 0));
  return filtered.map((spool) => ({ spool, filament: filamentById.get(spool.filament_id) }));
}
