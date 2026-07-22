import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// TAG-GROUPS-1 (Story 46.1) — read-only admin tag-groups screen (/admin/tag-groups).
//
// Each state is driven by a MOCKED `GET /api/tag-groups` response so the four
// projects (desktop-light/dark, mobile-light/dark) are pixel-stable. The payload
// carries no rendered timestamp and the query never re-fetches (5-min staleTime),
// so screenshots are deterministic.
//
// Per the Epic 45 retro action ("every UI story that adds a rendered state owes a
// pre-screenshot toBeVisible() assertion for that specific state"), each test asserts
// the concrete rendered content is visible *immediately before* toHaveScreenshot — so a
// silently-degraded/empty render fails the assertion loudly rather than rubber-stamping a
// pixel diff. The visual harness forces `pl-PL` (playwright.config.ts), so text matchers
// below are Polish; structure matchers use locale-independent data-testids.
//
// NOTE (loading state): the loading skeleton (`data-testid="tag-groups-skeleton"`) is
// transient and `aria-hidden` — capturing it deterministically requires holding the
// `/api/tag-groups` request open, which also stalls the harness's `networkidle` wait.
// Consistent with the admin-queues / admin-users specs, the loading skeleton is not
// baselined; populated / empty / error are the load-bearing rendered states.

// Populated fixture exercises: position ordering (Motyw → Materiał → Kolekcja), multi-tag
// groups, singular vs plural CLDR counts (1 → "model"), name_pl-null fallback to name_en
// (PLA), an empty group's inline empty-state, and the groupless ("Bez grupy") section.
//
// Story 46.3 — "Bracket"/"Brackets" is an intentional near-duplicate pair (Levenshtein
// distance 1, normalized length 8) added to the groupless tags so the populated fixture
// also exercises the duplicates-detection panel.
const POPULATED = {
  groups: [
    {
      id: "tg-theme",
      slug: "theme",
      name_en: "Theme",
      name_pl: "Motyw",
      position: 0,
      tags: [
        {
          id: "t-dragon",
          slug: "dragon",
          name_en: "Dragon",
          name_pl: "Smok",
          group_id: "tg-theme",
          group_position: 0,
          model_count: 12,
        },
        {
          id: "t-castle",
          slug: "castle",
          name_en: "Castle",
          name_pl: "Zamek",
          group_id: "tg-theme",
          group_position: 1,
          model_count: 3,
        },
      ],
    },
    {
      id: "tg-material",
      slug: "material",
      name_en: "Material",
      name_pl: "Materiał",
      position: 1,
      tags: [
        {
          id: "t-pla",
          slug: "pla",
          name_en: "PLA",
          name_pl: null,
          group_id: "tg-material",
          group_position: 0,
          model_count: 1,
        },
      ],
    },
    {
      id: "tg-collection",
      slug: "collection",
      name_en: "Collection",
      name_pl: "Kolekcja",
      position: 2,
      tags: [],
    },
  ],
  groupless: [
    {
      id: "t-misc",
      slug: "misc",
      name_en: "Miscellaneous",
      name_pl: "Różne",
      group_id: null,
      group_position: 0,
      model_count: 5,
    },
    {
      id: "t-bracket",
      slug: "bracket",
      name_en: "Bracket",
      name_pl: null,
      group_id: null,
      group_position: 1,
      model_count: 8,
    },
    {
      id: "t-brackets",
      slug: "brackets",
      name_en: "Brackets",
      name_pl: null,
      group_id: null,
      group_position: 2,
      model_count: 2,
    },
  ],
};

const EMPTY = { groups: [], groupless: [] };

async function stubTagGroups(
  page: Page,
  opts: { snapshot?: unknown; error?: boolean } = {},
) {
  await page.route("**/api/tag-groups**", (route) => {
    if (opts.error) {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(opts.snapshot ?? {}),
    });
  });
}

test.describe("/admin/tag-groups baselines", () => {
  test("populated — groups in order, counts, empty group, ungrouped section", async ({
    page,
  }) => {
    await stubTagGroups(page, { snapshot: POPULATED });
    await page.goto("/admin/tag-groups");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // Assert the specific populated state is rendered (not an empty shell) before capturing.
    await expect(page.getByTestId("tag-group-theme")).toBeVisible();
    await expect(page.getByTestId("tag-group-material")).toBeVisible();
    await expect(page.getByTestId("tag-group-collection")).toBeVisible();
    await expect(page.getByTestId("tag-group-ungrouped")).toBeVisible();
    await expect(page.getByText("1 model", { exact: true })).toBeVisible();
    await expect(page.getByText("Brak tagów w tej grupie.")).toBeVisible();
    // Story 46.2 — the page now carries write affordances (per-row menus + Create group).
    await expect(page.getByRole("button", { name: "Utwórz grupę" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Akcje dla grupy Motyw" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-populated.png", { fullPage: true });
  });

  test("populated — possible duplicates panel for a near-duplicate tag pair", async ({
    page,
  }) => {
    await stubTagGroups(page, { snapshot: POPULATED });
    await page.goto("/admin/tag-groups");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // Story 46.3 — the duplicates panel renders above the group list, listing the
    // Bracket/Brackets cluster with its similar-count badge and merge action.
    await expect(page.getByText("Możliwe duplikaty")).toBeVisible();
    await expect(page.getByText("2 podobne")).toBeVisible();
    await expect(page.getByRole("button", { name: "Scal w jeden" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-duplicates-panel.png", { fullPage: true });
  });

  test("empty — no groups and no groupless tags", async ({ page }) => {
    await stubTagGroups(page, { snapshot: EMPTY });
    await page.goto("/admin/tag-groups");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // Assert the distinct empty-state copy is rendered (not a blank/broken load) before capturing.
    await expect(page.getByText("Brak grup tagów.")).toBeVisible();
    await expect(page.getByTestId("tag-group-ungrouped")).toHaveCount(0);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-empty.png", { fullPage: true });
  });

  test("error — fails-closed error banner + retry", async ({ page }) => {
    await stubTagGroups(page, { error: true });
    await page.goto("/admin/tag-groups");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // Assert the error banner + retry affordance is rendered before capturing.
    await expect(page.getByText("Nie udało się wczytać grup tagów")).toBeVisible();
    await expect(page.getByRole("button", { name: "Ponów" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-error.png", { fullPage: true });
  });
});

// Story 46.2 — the four write dialogs, each opened over the populated page. The
// harness forces pl-PL, so triggers/menu items/titles are matched in Polish.
// POPULATED's first theme tag localizes to "Smok" (Dragon → name_pl) and the
// first group to "Motyw" (Theme).
test.describe("/admin/tag-groups write dialogs", () => {
  async function gotoPopulated(page: Page) {
    await stubTagGroups(page, { snapshot: POPULATED });
    await page.goto("/admin/tag-groups");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
  }

  test("create-group dialog", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Utwórz grupę" }).click();
    // Concrete rendered content of THIS dialog (slug field is create-only) before capturing.
    await expect(page.getByRole("heading", { name: "Utwórz grupę" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Identyfikator" })).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-dialog-create.png", { fullPage: true });
  });

  test("rename dialog", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Akcje dla tagu Smok" }).click();
    await page.getByRole("menuitem", { name: "Zmień nazwę" }).click();
    await expect(page.getByRole("heading", { name: "Zmień nazwę tagu" })).toBeVisible();
    await expect(page.getByText("Nazwa angielska")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-dialog-rename.png", { fullPage: true });
  });

  test("move dialog", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Akcje dla tagu Smok" }).click();
    await page.getByRole("menuitem", { name: "Przenieś do grupy" }).click();
    await expect(page.getByRole("heading", { name: "Przenieś tag" })).toBeVisible();
    await expect(page.getByText("Grupa docelowa")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-dialog-move.png", { fullPage: true });
  });

  test("merge dialog", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Akcje dla tagu Smok" }).click();
    await page.getByRole("menuitem", { name: "Scal z…" }).click();
    await expect(page.getByRole("heading", { name: "Scal tag" })).toBeVisible();
    await expect(page.getByText("Tag docelowy")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-dialog-merge.png", { fullPage: true });
  });

  test("merge-duplicates dialog", async ({ page }) => {
    await gotoPopulated(page);
    await page.getByRole("button", { name: "Scal w jeden" }).click();
    await expect(page.getByRole("heading", { name: "Scal duplikaty tagów" })).toBeVisible();
    await expect(page.getByText("Tag, który pozostanie")).toBeVisible();
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("tag-groups-dialog-merge-duplicates.png", {
      fullPage: true,
    });
  });
});
