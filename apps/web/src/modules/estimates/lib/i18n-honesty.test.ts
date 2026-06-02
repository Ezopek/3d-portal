import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

// Story 32.6 (AC-6) — the SPOOL-EVT-1 honesty guard. Because the live Spoolman-change event
// source + reverse index are DEFERRED, no estimate copy may promise that the estimate updates
// automatically when a Spoolman spool changes. The UI reflects the server cache/recompute
// state as it currently is — a stale state appears only when something actually marked it
// stale, never on a promise of live propagation.
const FORBIDDEN = [
  /automatically updates?/i,
  /updates? automatically/i,
  /auto-?update/i,
  /aktualizuje się automatycznie/i,
  /automatyczn\w* aktualiz/i,
];

function estimateValues(bundle: Record<string, string>): string[] {
  return Object.entries(bundle)
    .filter(([k]) => k.startsWith("modules.estimates"))
    .map(([, v]) => v);
}

describe("estimate copy makes no automatic-propagation claim (AC-6)", () => {
  it.each([
    ["en", en],
    ["pl", pl],
  ])(
    "%s estimate strings promise no live Spoolman auto-update",
    (_locale, bundle) => {
      for (const value of estimateValues(bundle as Record<string, string>)) {
        for (const pattern of FORBIDDEN) {
          expect(value).not.toMatch(pattern);
        }
      }
    },
  );
});
