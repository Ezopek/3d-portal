import { describe, expect, it } from "vitest";

import type { FilamentView } from "@/lib/api-types";
import {
  DEFAULT_MATERIAL_CLASS,
  DEFAULT_QUALITY_TIER,
  MATERIAL_CLASSES,
  QUALITY_TIERS,
  defaultPreset,
  filamentRef,
  presetKey,
} from "./preset";

const filament: FilamentView = {
  id: 10,
  name: "PLA Speed Matt White",
  vendor_id: 100,
  vendor_name: "Bambu Lab",
  material: "PLA",
  color_hex: "FFFFFF",
  price: 99.9,
  weight: 1000,
  spool_weight: 200,
};

describe("named contracts (AC-11)", () => {
  it("exposes exactly the FR20 material-class set, untranslated", () => {
    expect(MATERIAL_CLASSES).toEqual(["PLA", "PETG", "PCTG", "TPU"]);
  });

  it("exposes the portal quality-tier set", () => {
    expect(QUALITY_TIERS).toEqual(["aesthetic", "standard", "strong"]);
  });

  it("defaults to a material class + standard tier + no pin", () => {
    expect(defaultPreset()).toEqual({
      material_class: DEFAULT_MATERIAL_CLASS,
      quality_tier: DEFAULT_QUALITY_TIER,
      spoolman_filament_ref: null,
    });
    expect(defaultPreset().spoolman_filament_ref).toBeNull();
  });
});

describe("filamentRef", () => {
  it("derives the churn-stable vendor∥material∥name ref, NOT the integer id", () => {
    const ref = filamentRef(filament);
    expect(ref).toBe("Bambu Lab\x1fPLA\x1fPLA Speed Matt White");
    expect(ref).not.toContain("10");
  });

  it("tolerates missing vendor/material with empty segments", () => {
    expect(
      filamentRef({ ...filament, vendor_name: null, material: null }),
    ).toBe("\x1f\x1fPLA Speed Matt White");
  });
});

describe("presetKey", () => {
  it("re-keys on any field change so a stale key never shows another preset", () => {
    const base = defaultPreset();
    const k = presetKey(base);
    expect(presetKey({ ...base, material_class: "PETG" })).not.toBe(k);
    expect(presetKey({ ...base, quality_tier: "strong" })).not.toBe(k);
    expect(
      presetKey({ ...base, spoolman_filament_ref: filamentRef(filament) }),
    ).not.toBe(k);
  });
});
