import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// EST-DISPLAY-1 (UX §B/§C, NFR20-VISUAL-VERIFICATION-1) — the FilesTab inline estimate chip
// states on the catalog detail surface. Each state is driven by a MOCKED `/api/estimates`
// response with a pinned `computed_at` + pinned wall clock, so the chip grams and the expanded
// `EstimateDisplay` soft-fail label are pixel-stable across the 4 visual projects
// (desktop/mobile × light/dark). No real slice/Orca/worker runs.
//
// NOTE (baseline status): authored under EST-DISPLAY-1. If the authoring environment has no
// dev-server/browser budget, the `__snapshots__` baselines are generated in the controller-owned
// visual pass (the Story 32.6 deferred-baseline precedent). Regen command + caveat are in the
// story spec Verification section.

const MODEL_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee";
const STL_HASH = "a".repeat(64);
const FIXED_NOW_ISO = "2026-06-02T10:05:00Z";
const COMPUTED_AT = "2026-06-02T10:00:00Z"; // 5 minutes before FIXED_NOW

const CONTEXT = {
  material_class: "PLA",
  quality_tier: "standard",
  pinned_filament_name: null,
  custom_overrides_applied: false,
  purchase_url: null,
};

function estimate(overrides: Record<string, unknown> = {}) {
  return {
    status: "fresh",
    time_seconds: 12947,
    filament_g: 76.76,
    filament_mm: 25735.79,
    filament_cm3: 61.9,
    filament_cost: 4.6,
    currency: "PLN",
    computed_at: COMPUTED_AT,
    warnings: [],
    failure_reason: null,
    override_context: CONTEXT,
    ...overrides,
  };
}

async function stubModelDetail(page: Page) {
  await page.route(`**/api/models/${MODEL_ID}`, (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: MODEL_ID,
        slug: "bracket",
        name_en: "Bracket",
        name_pl: "Wspornik",
        category_id: "c1",
        source: "printables",
        status: "printed",
        rating: null,
        thumbnail_file_id: null,
        date_added: "2026-04-12",
        deleted_at: null,
        created_at: "2026-04-12T00:00:00Z",
        updated_at: "2026-04-12T00:00:00Z",
        tags: [],
        category: {
          id: "c1",
          parent_id: null,
          slug: "parts",
          name_en: "Parts",
          name_pl: "Części",
        },
        files: [
          {
            id: "f1",
            model_id: MODEL_ID,
            kind: "stl",
            original_name: "bracket_left_v3.stl",
            storage_path: "",
            sha256: STL_HASH,
            size_bytes: 12400000,
            mime_type: "model/stl",
            position: 0,
            selected_for_render: false,
            created_at: "",
          },
        ],
        prints: [],
        notes: [],
        external_links: [],
      }),
    }),
  );
}

async function stubEstimate(page: Page, body: Record<string, unknown>) {
  // Deterministic empty spools so the preset selector's pin list has no entries.
  await page.route("**/api/spools/summary**", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        spools: [],
        filaments: [],
        vendors: [],
        fetched_at: null,
        last_success_ts: null,
      }),
    }),
  );
  await page.route("**/api/estimates**", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  );
}

const STATES: Array<{ name: string; body: Record<string, unknown> }> = [
  { name: "fresh", body: estimate({ status: "fresh" }) },
  { name: "stale", body: estimate({ status: "stale" }) },
  {
    name: "absent",
    body: estimate({
      status: "absent",
      time_seconds: null,
      filament_g: null,
      filament_mm: null,
      filament_cm3: null,
      filament_cost: null,
      computed_at: null,
    }),
  },
];

for (const state of STATES) {
  test(`FilesTab estimate chip — ${state.name} (collapsed list)`, async ({ page }) => {
    await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
    await stubModelDetail(page);
    await stubEstimate(page, state.body);
    await page.goto(`/catalog/${MODEL_ID}`);
    await waitForReady(page);
    // SecondaryTabs defaults to the Files tab; assert the preset bar is present before snapshot.
    await page.getByRole("tabpanel").first().waitFor({ state: "visible" });
    await expect(page.getByRole("tabpanel").first()).toHaveScreenshot(
      `filestab-estimate-${state.name}.png`,
    );
  });
}

test("FilesTab estimate chip — expanded panel reuses EstimateDisplay", async ({
  page,
}) => {
  await page.clock.install({ time: new Date(FIXED_NOW_ISO) });
  await stubModelDetail(page);
  await stubEstimate(page, estimate({ status: "fresh" }));
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page
    .getByRole("button", { name: /toggle 3d preview for bracket_left_v3\.stl/i })
    .click();
  await page.waitForTimeout(500);
  await expect(page.getByRole("tabpanel").first()).toHaveScreenshot(
    "filestab-estimate-expanded.png",
  );
});
