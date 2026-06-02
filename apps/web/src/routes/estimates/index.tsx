import { createFileRoute } from "@tanstack/react-router";

import { EstimatesPanel } from "@/modules/estimates/components/EstimatesPanel";

// because "the Init 20 single-printer MVP printer identity (a resolve input). The portal has
// one printer today; the mount surface supplies a stable default while still allowing the
// search param to override it for multi-printer follow-ups. NOT a tunable threshold." (AC-11)
const DEFAULT_PRINTER_REF = "p1s";

interface EstimatesSearch {
  stl_hash?: string;
  printer_ref?: string;
}

/**
 * Story 32.6 — the self-contained estimates surface. The catalog↔STL ingestion that would
 * auto-derive an `stl_hash` per catalog part is OUT OF SCOPE (AC-9); this route renders the
 * selector + display against a supplied `?stl_hash=` (and an optional `?printer_ref=`),
 * which the visual specs drive with a known hash + mocked API.
 */
export const Route = createFileRoute("/estimates/")({
  validateSearch: (raw: Record<string, unknown>): EstimatesSearch => {
    const out: EstimatesSearch = {};
    if (typeof raw.stl_hash === "string" && raw.stl_hash.length > 0) {
      out.stl_hash = raw.stl_hash;
    }
    if (typeof raw.printer_ref === "string" && raw.printer_ref.length > 0) {
      out.printer_ref = raw.printer_ref;
    }
    return out;
  },
  component: EstimatesRoute,
});

function EstimatesRoute() {
  const { stl_hash, printer_ref } = Route.useSearch();
  return (
    <EstimatesPanel
      stlHash={stl_hash ?? ""}
      printerRef={printer_ref ?? DEFAULT_PRINTER_REF}
    />
  );
}
