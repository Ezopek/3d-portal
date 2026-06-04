import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

type Material = "PLA" | "PETG" | "PCTG" | "TPU";
type Tier = "aesthetic" | "standard" | "strong";
type Status = "offerable" | "not_imported" | "not_resolvable" | "incompatible";

interface Slot {
  material_class: Material;
  quality_tier: Tier;
  imported: boolean;
  resolvable: boolean;
  compatible: boolean;
  offerable: boolean;
  status: Status;
  reason: string | null;
  portal_label: string | null;
  provenance: {
    source_system_tree_hash: string | null;
    orca_version: string | null;
  };
}

const MATERIALS: Material[] = ["PLA", "PETG", "PCTG", "TPU"];
const TIERS: Tier[] = ["aesthetic", "standard", "strong"];

function slot(
  material_class: Material,
  quality_tier: Tier,
  overrides: Partial<Slot> = {},
): Slot {
  const compatible =
    material_class !== "TPU" || quality_tier === "standard";
  const imported = compatible;
  const resolvable = compatible;
  const offerable = compatible && imported && resolvable;
  return {
    material_class,
    quality_tier,
    imported,
    resolvable,
    compatible,
    offerable,
    status: offerable ? "offerable" : "incompatible",
    reason: offerable ? null : "incompatible_for_material",
    portal_label: null,
    provenance: offerable
      ? {
          source_system_tree_hash:
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
          orca_version: "2.3.0",
        }
      : { source_system_tree_hash: null, orca_version: null },
    ...overrides,
  };
}

const SLOTS: Slot[] = MATERIALS.flatMap((material) =>
  TIERS.map((tier) => slot(material, tier)),
);

// Exercise all four status presentations in one stable grid:
// - PLA/aesthetic: offerable
// - PETG/standard: not_imported
// - PCTG/strong: not_resolvable
// - TPU/aesthetic + TPU/strong: incompatible (Q5: TPU standard-only)
const mixedSlots = SLOTS.map((s) => {
  if (s.material_class === "PETG" && s.quality_tier === "standard") {
    return slot("PETG", "standard", {
      imported: false,
      resolvable: false,
      compatible: true,
      offerable: false,
      status: "not_imported",
      reason: "profile_not_imported",
      provenance: { source_system_tree_hash: null, orca_version: null },
    });
  }
  if (s.material_class === "PCTG" && s.quality_tier === "strong") {
    return slot("PCTG", "strong", {
      imported: true,
      resolvable: false,
      compatible: true,
      offerable: false,
      status: "not_resolvable",
      reason: "not_resolvable",
      provenance: { source_system_tree_hash: null, orca_version: null },
    });
  }
  return s;
});

async function stubAdminProfilesPage(page: Page, slots: Slot[] = mixedSlots) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000001",
        email: "admin@localhost.localdomain",
        display_name: "Admin",
        role: "admin",
      }),
    }),
  );

  await page.route("**/api/admin/profiles**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        printer_ref: "creality-k1-max-microswiss-hf",
        material_classes: MATERIALS,
        quality_tiers: TIERS,
        slots,
      }),
    }),
  );
}

test.describe("/admin/profiles baselines", () => {
  test("mixed status grid matches baseline", async ({ page }) => {
    await stubAdminProfilesPage(page);
    await page.goto("/admin/profiles");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await expect(page.locator("body")).toContainText("PLA");
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-profiles-mixed-status.png", {
      fullPage: true,
    });
  });
});
