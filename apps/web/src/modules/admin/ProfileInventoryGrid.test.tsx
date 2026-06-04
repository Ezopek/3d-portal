import "@/locales/i18n";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import type { AdminProfileSlot, AdminProfileStatus } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { ProfileInventoryGrid } from "@/modules/admin/ProfileInventoryGrid";

afterEach(cleanup);

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

function slot(
  material: AdminProfileSlot["material_class"],
  tier: AdminProfileSlot["quality_tier"],
  status: AdminProfileStatus,
  overrides: Partial<AdminProfileSlot> = {},
): AdminProfileSlot {
  const base: AdminProfileSlot = {
    material_class: material,
    quality_tier: tier,
    imported: status !== "not_imported",
    resolvable: status === "offerable",
    compatible: status !== "incompatible",
    offerable: status === "offerable",
    status,
    reason:
      status === "offerable"
        ? null
        : status === "incompatible"
          ? "incompatible_for_material"
          : status === "not_imported"
            ? "profile_not_imported"
            : "not_resolvable",
    portal_label: null,
    provenance:
      status === "offerable"
        ? { source_system_tree_hash: "abcdef0123456789", orca_version: "2.3.2" }
        : { source_system_tree_hash: null, orca_version: null },
    ...overrides,
  };
  return base;
}

const MIXED_SLOTS: AdminProfileSlot[] = [
  slot("PLA", "aesthetic", "offerable"),
  slot("PLA", "standard", "offerable"),
  slot("PLA", "strong", "not_resolvable"),
  slot("PETG", "aesthetic", "not_imported"),
  slot("PETG", "standard", "offerable"),
  slot("PETG", "strong", "not_imported"),
  slot("PCTG", "aesthetic", "not_resolvable"),
  slot("PCTG", "standard", "offerable"),
  slot("PCTG", "strong", "not_imported"),
  slot("TPU", "aesthetic", "incompatible"),
  slot("TPU", "standard", "incompatible"),
  slot("TPU", "strong", "not_imported"),
];

describe("ProfileInventoryGrid (Story 33.1 — AC-12..AC-16)", () => {
  it("renders every one of the four statuses with an icon+text label (AC-13)", () => {
    render(<ProfileInventoryGrid slots={MIXED_SLOTS} />);
    // Desktop matrix + mobile cards both render, so each label appears multiple times.
    for (const label of ["Offerable", "Not imported", "Not resolvable", "Incompatible"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("shows a human-readable reason on a non-offerable cell, never on offerable (AC-12)", () => {
    render(<ProfileInventoryGrid slots={MIXED_SLOTS} />);
    // Incompatible TPU rows interpolate the material name.
    expect(
      screen.getAllByText("Not a valid process for TPU").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Installed profile fails to resolve").length,
    ).toBeGreaterThan(0);
  });

  it("exposes a provenance affordance only on offerable cells (AC-14)", () => {
    render(<ProfileInventoryGrid slots={MIXED_SLOTS} />);
    const provenanceTriggers = screen.getAllByRole("button", {
      name: /show provenance/i,
    });
    // One per offerable slot (PLA aesthetic+standard, PETG standard, PCTG standard = 4),
    // doubled across desktop+mobile renders.
    const offerableCount = MIXED_SLOTS.filter((s) => s.offerable).length;
    expect(provenanceTriggers.length).toBe(offerableCount * 2);
  });

  it("shows an inert disabled Import placeholder on compatible not-imported cells (AC-16)", () => {
    render(<ProfileInventoryGrid slots={MIXED_SLOTS} />);
    const importButtons = screen.getAllByRole("button", { name: "Import" });
    expect(importButtons.length).toBeGreaterThan(0);
    for (const btn of importButtons) {
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    }
  });

  it("never renders an Orca-internal key / path / g-code in the grid (AC-14 fence)", () => {
    const { container } = render(<ProfileInventoryGrid slots={MIXED_SLOTS} />);
    const html = container.innerHTML;
    for (const forbidden of [
      "filament_max_volumetric_speed",
      "nozzle_temperature",
      "/intents/",
      ".json",
      "gcode",
      "settings_id",
      "bundle_hash",
    ]) {
      expect(html).not.toContain(forbidden);
    }
  });
});
