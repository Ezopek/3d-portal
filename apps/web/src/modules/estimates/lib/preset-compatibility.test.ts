import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import type { MaterialClass } from "@/lib/api-types";
import { MATERIAL_TIER_COMPATIBILITY } from "./preset";

// Story 33.1 (AC-21) — FE↔BE compatibility-map parity. The backend
// `apps/api/app/modules/slicer/compatibility.py MATERIAL_TIER_COMPATIBILITY` is the SoT; the
// FE mirror (preset.ts) must agree byte-for-byte (same proven QUALITY_TIER_ORDER ↔
// QUALITY_TIERS mirroring discipline). This reads the backend file and asserts equality so
// the two CANNOT drift — including the operator-confirmed Q5 TPU row.
const BACKEND_COMPAT_PATH = resolve(
  process.cwd(),
  "../api/app/modules/slicer/compatibility.py",
);

function parseBackendMap(source: string): Record<string, Set<string>> {
  const out: Record<string, Set<string>> = {};
  // Match e.g.  "PLA": frozenset({"aesthetic", "standard", "strong"}),
  const rowRe = /"(PLA|PETG|PCTG|TPU)":\s*frozenset\(\{([^}]*)\}\)/g;
  let m: RegExpExecArray | null;
  while ((m = rowRe.exec(source)) !== null) {
    const material = m[1] as string;
    const tiers = [...(m[2] as string).matchAll(/"([a-z]+)"/g)].map((x) => x[1] as string);
    out[material] = new Set(tiers);
  }
  return out;
}

describe("FE↔BE compatibility-map parity (AC-21)", () => {
  const backend = parseBackendMap(readFileSync(BACKEND_COMPAT_PATH, "utf8"));

  it("parsed all four material rows from the backend SoT", () => {
    expect(Object.keys(backend).sort()).toEqual(["PCTG", "PETG", "PLA", "TPU"]);
  });

  it("the FE mirror agrees with the backend map for every material", () => {
    for (const material of Object.keys(MATERIAL_TIER_COMPATIBILITY) as MaterialClass[]) {
      const fe = new Set(MATERIAL_TIER_COMPATIBILITY[material]);
      expect(
        { material, tiers: [...fe].sort() },
        `FE/BE compatibility drift on ${material}`,
      ).toEqual({ material, tiers: [...(backend[material] ?? new Set())].sort() });
    }
  });
});
