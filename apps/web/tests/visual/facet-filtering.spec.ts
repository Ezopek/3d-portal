import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";

// E47 47.2 — facet-surface visual specs: FacetSidebar's default-expanded/
// collapsed/groupless/untagged states, the UI-driven (not URL-preset) 2-tag
// match-mode reveal, and the AND-too-narrow EmptyState. Story 52.1 re-pointed
// every entry here at the consolidated `Filters (n)` panel: the "Tagi" trigger
// and the `+ tag` TagPicker it used to drive are both deleted, and the same
// FacetSidebar surface (verbatim, zero-line diff) is now reached by opening
// "Filtry". Per Epic 45/46's test-authoring rule, every `toHaveScreenshot`
// below is preceded by a `toBeVisible()`/visible-text assertion on the
// concrete state being captured. The harness forces `pl-PL`
// (playwright.config.ts), so text matchers are the actual pl.json strings.
//
// This fixture is deliberately richer than `stubSotList`'s own
// `DEFAULT_TAGS`/`DEFAULT_TAG_GROUPS` (3 groups + a non-empty `groupless`,
// real UUID-shaped ids) so it exercises `FacetSidebar`'s
// `DEFAULT_EXPANDED_GROUP_COUNT = 2` default-collapse rule (group 3 starts
// collapsed) and survives `routes/catalog/index.tsx`'s `UUID_RE` when used
// in a URL `tag_ids` param. `RICH_TAGS` is the flat equivalent of the same
// tags (same ids/slugs) so `FilterRibbon`'s chip labels resolve to real
// slugs instead of a truncated id.

const GROUP_THEME_ID = "44444444-4444-4444-4444-444444444401";
const GROUP_MATERIAL_ID = "44444444-4444-4444-4444-444444444402";
const GROUP_COLLECTION_ID = "44444444-4444-4444-4444-444444444403";

const TAG_DRAGON_ID = "44444444-4444-4444-4444-444444444441";
const TAG_CASTLE_ID = "44444444-4444-4444-4444-444444444442";
const TAG_PLA_ID = "44444444-4444-4444-4444-444444444443";
const TAG_VEHICLES_ID = "44444444-4444-4444-4444-444444444444";
const TAG_MISC_ID = "44444444-4444-4444-4444-444444444445";

const RICH_FIXTURE: TagGroupsResponse = {
  groups: [
    {
      id: GROUP_THEME_ID,
      slug: "theme",
      name_en: "Theme",
      name_pl: "Motyw",
      position: 0,
      tags: [
        {
          id: TAG_DRAGON_ID,
          slug: "dragon",
          name_en: "Dragon",
          name_pl: "Smok",
          group_id: GROUP_THEME_ID,
          group_position: 0,
          model_count: 3,
        },
        {
          id: TAG_CASTLE_ID,
          slug: "castle",
          name_en: "Castle",
          name_pl: "Zamek",
          group_id: GROUP_THEME_ID,
          group_position: 1,
          model_count: 2,
        },
      ],
    },
    {
      id: GROUP_MATERIAL_ID,
      slug: "material",
      name_en: "Material",
      name_pl: "Materiał",
      position: 1,
      tags: [
        {
          id: TAG_PLA_ID,
          slug: "pla",
          name_en: "PLA",
          name_pl: null,
          group_id: GROUP_MATERIAL_ID,
          group_position: 0,
          model_count: 5,
        },
      ],
    },
    // Third group by `position` — collapsed by default per
    // `FacetSidebar`'s `DEFAULT_EXPANDED_GROUP_COUNT = 2`.
    {
      id: GROUP_COLLECTION_ID,
      slug: "collection",
      name_en: "Collection",
      name_pl: "Kolekcja",
      position: 2,
      tags: [
        {
          id: TAG_VEHICLES_ID,
          slug: "vehicles",
          name_en: "Vehicles",
          name_pl: "Pojazdy",
          group_id: GROUP_COLLECTION_ID,
          group_position: 0,
          model_count: 1,
        },
      ],
    },
  ],
  groupless: [
    {
      id: TAG_MISC_ID,
      slug: "misc",
      name_en: "Miscellaneous",
      name_pl: "Różne",
      group_id: null,
      group_position: 0,
      model_count: 4,
    },
  ],
};

// Derived from `RICH_FIXTURE` (not hand-duplicated) so the flat tag list
// FilterRibbon's `tagsById` lookup uses and the grouped tree FacetSidebar/
// the Filters panel renders can never drift apart — review finding: two independently
// hand-authored literals for the same 5 tags would silently disagree on a
// future edit to one and not the other.
const RICH_TAGS: TagListItem[] = [
  ...RICH_FIXTURE.groups.flatMap((g) => g.tags),
  ...RICH_FIXTURE.groupless,
];

// Story 51.1 moved browse navigation into the desktop left column and Story
// 52.1 consolidated the remaining refinement controls into one panel — the
// Sheet-mounted FacetSidebar is the ONLY facet mount, on every viewport. These
// tests therefore run on all four projects (no desktop-only skip) and reach
// the facet surface the way a user does: one click on the toolbar trigger,
// which is now "Filtry" (catalog.filters.openFilters) rather than the retired
// "Tagi" trigger.
// The trigger's accessible name CARRIES the count (D-10), so it is "Filtry" at
// n === 0 and "Filtry (n)" above it. Tests that arrive with a constraint
// already in the URL (e.g. `?untagged=true`) would miss an exact "Filtry".
const FILTERS_TRIGGER = /^Filtry(\s\(\d+\))?$/;

async function openFiltersPanel(page: Page) {
  await page.getByRole("button", { name: FILTERS_TRIGGER }).click();
  const sidebar = page.getByRole("complementary");
  await expect(sidebar).toBeVisible();
  return sidebar;
}

async function closeFiltersPanel(page: Page) {
  // The chips and the match-mode toggle live OUTSIDE the panel (D-1), behind
  // the modal backdrop while it is open, so the panel is dismissed before they
  // are asserted or captured.
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-slot='sheet-content']")).toHaveCount(0);
}

test.describe("FacetSidebar — default/collapsed/untagged baselines", () => {
  // Relies on `FacetSidebar`'s `localStorage["catalog:facet-collapse"]`
  // starting unset so `computeDefaultExpanded`'s position-based default (first
  // `DEFAULT_EXPANDED_GROUP_COUNT` groups) applies — true today because
  // Playwright gives every test a fresh, isolated browser context. If this
  // suite is ever reconfigured toward a shared/serial context, this
  // assumption would need re-verifying (review finding).
  test("default state: groups 1-2 expanded, group 3 collapsed", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    // Scoped to the sidebar `<aside>` (implicit role "complementary"): the
    // catalog grid's `ModelCard` also renders `Smok`/tag-slug text (the
    // fixture "dragon" model card), so an unscoped page-wide text match is
    // ambiguous.
    const sidebar = await openFiltersPanel(page);

    // Groups 1-2 (by `position`) expanded: their tag rows render.
    await expect(sidebar.getByRole("button", { name: "Zwiń Motyw" })).toBeVisible();
    await expect(sidebar.getByText("Smok", { exact: true })).toBeVisible();
    await expect(sidebar.getByText("Zamek", { exact: true })).toBeVisible();
    await expect(sidebar.getByRole("button", { name: "Zwiń Materiał" })).toBeVisible();
    await expect(sidebar.getByText("PLA", { exact: true })).toBeVisible();

    // Group 3 collapsed: header shows the "expand" aria-label, its tag row
    // is not rendered at all.
    await expect(sidebar.getByRole("button", { name: "Rozwiń Kolekcja" })).toBeVisible();
    await expect(sidebar.getByText("Pojazdy", { exact: true })).toHaveCount(0);

    // Groupless section also collapsed by default (review finding: the
    // fixture's 3rd claimed state — groupless section render — was
    // previously asserted nowhere before the screenshot).
    await expect(sidebar.getByRole("button", { name: "Rozwiń Bez grupy" })).toBeVisible();
    await expect(sidebar.getByText("Różne", { exact: true })).toHaveCount(0);

    await expect(page).toHaveScreenshot("facet-sidebar-default.png", { fullPage: true });
  });

  test("group-expand: clicking the collapsed group reveals its tag row", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    const sidebar = await openFiltersPanel(page);
    await sidebar.getByRole("button", { name: "Rozwiń Kolekcja" }).click();

    await expect(sidebar.getByRole("button", { name: "Zwiń Kolekcja" })).toBeVisible();
    await expect(sidebar.getByText("Pojazdy", { exact: true })).toBeVisible();

    await expect(page).toHaveScreenshot("facet-sidebar-group-expanded.png", { fullPage: true });
  });

  test("untagged checkbox renders checked from ?untagged=true", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog?untagged=true");
    await waitForReady(page);

    await openFiltersPanel(page);
    const untaggedCheckbox = page.getByRole("checkbox", { name: "Modele bez tagów" });
    await expect(untaggedCheckbox).toBeVisible();
    await expect(untaggedCheckbox).toBeChecked();

    await expect(page).toHaveScreenshot("facet-sidebar-untagged.png", { fullPage: true });
  });
});

// Story 52.1 replaced the `+ tag` TagPicker with in-panel tag selection: every
// tag the picker could reach is reachable inside the Filters panel, grouped and
// with per-tag counts (AC-14). The selected-tag chips and the ≥2-tag match-mode
// toggle stay OUTSIDE the panel, in `FilterRibbon`, because active constraints
// must remain visible regardless of where they were selected
// (EXPERIENCE.md:347) — so the panel is dismissed before they are captured.
test.describe("Filters panel — in-panel tag selection + UI-driven match-mode reveal", () => {
  test("panel lists every fixture tag, grouped, with per-tag counts", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    const sidebar = await openFiltersPanel(page);

    // Groups 1-2 are expanded by the shipped default rule, so their tags show
    // directly; groups 3 and the groupless section are one click away, and the
    // in-panel search reaches all of them without any expanding at all.
    await expect(sidebar.getByRole("checkbox", { name: /^Smok/ })).toBeVisible();
    await expect(sidebar.getByRole("checkbox", { name: /^Zamek/ })).toBeVisible();
    await expect(sidebar.getByRole("checkbox", { name: /^PLA/ })).toBeVisible();
    await sidebar.getByRole("button", { name: "Rozwiń Kolekcja" }).click();
    await expect(sidebar.getByRole("checkbox", { name: /^Pojazdy/ })).toBeVisible();
    await sidebar.getByRole("button", { name: "Rozwiń Bez grupy" }).click();
    await expect(sidebar.getByRole("checkbox", { name: /^Różne/ })).toBeVisible();

    await expect(page).toHaveScreenshot("filters-panel-all-tags-open.png", {
      fullPage: true,
    });
  });

  // Deliberately UI-driven (not a `?tag_ids=...` URL preset): closes
  // deferred-work.md's "story 44.2 dev repair review" STILL-OPEN item — the
  // `>=2` gate that reveals the match-mode toggle, previously only reasoned
  // about at the `validateSearch`/`useModels.buildParams` layers. Since Story
  // 52.1 the two tags are selected through the panel's facet checkboxes, which
  // route through `toggleTag` (D-11), not through `setFilters`.
  test("selecting 2 tags one-by-one in the panel reveals the match-mode toggle", async ({
    page,
  }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    // `ModelCard` in the catalog grid also renders `data-testid="tag-chip"`
    // badges for a model's own tags (unaffected by this test's fixture
    // override, since `stubSotList`'s `/api/models*` default carries a
    // "dragon" tag on its fixture model) — scope to FilterRibbon's chips
    // specifically via their unique nested "remove" button, which
    // `ModelCard`'s read-only chips don't have.
    const ribbonChips = page
      .getByTestId("tag-chip")
      .filter({ has: page.getByRole("button", { name: /^Usuń tag /i }) });

    const sidebar = await openFiltersPanel(page);
    await sidebar.getByRole("checkbox", { name: /^Smok/ }).check();
    await expect(sidebar.getByRole("checkbox", { name: /^Smok/ })).toBeChecked();
    await sidebar.getByRole("checkbox", { name: /^Zamek/ }).check();
    await expect(sidebar.getByRole("checkbox", { name: /^Zamek/ })).toBeChecked();

    // AC-6/AC-8 — each selected tag counts as one, so the trigger's badge and
    // accessible name now read 2.
    await expect(page.getByTestId("filters-trigger-badge")).toHaveText("2");

    await closeFiltersPanel(page);

    await expect(ribbonChips).toHaveCount(2);
    await expect(ribbonChips.filter({ hasText: "dragon" })).toBeVisible();
    await expect(ribbonChips.filter({ hasText: "castle" })).toBeVisible();
    const matchModeGroup = page.getByRole("group", { name: "Dopasowanie tagów" });
    await expect(matchModeGroup).toBeVisible();
    await expect(matchModeGroup.getByRole("button", { name: "Wszystkie" })).toBeVisible();
    await expect(matchModeGroup.getByRole("button", { name: "Dowolne" })).toBeVisible();

    await expect(page).toHaveScreenshot("filter-ribbon-match-mode-toggle.png", {
      fullPage: true,
    });
  });
});

test.describe("AND-too-narrow EmptyState", () => {
  test("2 tag_ids + total:0 renders both recovery actions", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    // Registered AFTER stubSotList — Playwright resolves matching routes in
    // reverse registration order, so this override wins over stubSotList's
    // own `/api/models*` handler.
    await page.route("**/api/models*", (route: Route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, offset: 0, limit: 48, items: [] }),
      }),
    );

    await page.goto(`/catalog?tag_ids=${TAG_DRAGON_ID}&tag_ids=${TAG_CASTLE_ID}`);
    await waitForReady(page);

    await expect(page.getByTestId("tag-chip")).toHaveCount(2);
    const switchToOr = page.getByRole("button", { name: "Przełącz na dowolne" });
    const clearFilters = page.getByRole("button", { name: "Wyczyść filtry" });
    await expect(switchToOr).toBeVisible();
    await expect(clearFilters).toBeVisible();

    await expect(page).toHaveScreenshot("catalog-and-too-narrow-empty.png", { fullPage: true });
  });
});
