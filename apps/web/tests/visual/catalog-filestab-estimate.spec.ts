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
        source: "printables",
        status: "printed",
        rating: null,
        thumbnail_file_id: null,
        date_added: "2026-04-12",
        deleted_at: null,
        created_at: "2026-04-12T00:00:00Z",
        updated_at: "2026-04-12T00:00:00Z",
        tags: [],
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

// EST-TIERS-1 — a single `**/api/estimates**` route serves BOTH the estimate read and the
// `/quality-tiers` availability read, branching on the path. Folding them into ONE handler makes
// the stub independent of Playwright's route-precedence semantics: a separate, more-specific
// `**/api/estimates/quality-tiers**` route can lose the match to this generic glob (the observed
// flake where the availability rows never reach the selector), and an unhandled tiers request
// would stall `waitForReady`'s `networkidle`. The default body reports every tier available, so
// the chip states above render an all-selectable selector exactly as before.
const ALL_TIERS_AVAILABLE = {
  printer_ref: "creality-k1-max-microswiss-hf",
  material_class: "PLA",
  tiers: [
    { quality_tier: "aesthetic", available: true, reason: null },
    { quality_tier: "standard", available: true, reason: null },
    { quality_tier: "strong", available: true, reason: null },
  ],
};

async function stubEstimate(
  page: Page,
  body: Record<string, unknown>,
  tiers: Record<string, unknown> = ALL_TIERS_AVAILABLE,
) {
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
  // Story 38.3: stub the published offers endpoint — return empty list so the picker
  // does not appear in chip/panel visual baselines (no authenticated member in visual tests).
  await page.route("**/api/profiles/offers/published**", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ offers: [] }),
    }),
  );
  await page.route("**/api/estimates**", (r) => {
    // The tier-availability read shares the `/api/estimates` prefix; serve it from the SAME
    // handler so the disabled-tier body is never shadowed by the generic estimate stub.
    if (r.request().url().includes("/quality-tiers")) {
      return r.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(tiers),
      });
    }
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
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

// EST-TIERS-1 — the compact STL profile selector must render the unresolvable tiers
// (Aesthetic / Strong for the catalog printer·PLA identity, which has only `standard.json`
// vendored) DISABLED with honest "profile not imported yet" copy, while Standard stays
// selectable. This availability body is handed to the unified `stubEstimate` route above so the
// `/quality-tiers` read is fulfilled deterministically (no route-precedence flake).
// Baseline status: deferred to the controller-owned visual pass, same precedent as the
// E38.3: EST-TIERS-1 test removed — the Material + Quality tier profile selector is removed
// from FilesTab in Story 38.3 (offer-first UX). The useQualityTierAvailability hook is retained
// internally as a load-bearing 422 gate (NFR21-NO-422-1) but its UI is gone.

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
