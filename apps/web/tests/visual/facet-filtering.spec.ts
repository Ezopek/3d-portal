import type { Route } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";

// E47 47.2 — facet-surface visual specs: FacetSidebar's default-expanded/
// collapsed/groupless/untagged states, FilterRibbon's tag-picker + UI-driven
// (not URL-preset) 2-tag match-mode reveal, and the AND-too-narrow
// EmptyState. Per Epic 45/46's test-authoring rule, every `toHaveScreenshot`
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
// TagPicker render can never drift apart — review finding: two independently
// hand-authored literals for the same 5 tags would silently disagree on a
// future edit to one and not the other.
const RICH_TAGS: TagListItem[] = [
  ...RICH_FIXTURE.groups.flatMap((g) => g.tags),
  ...RICH_FIXTURE.groupless,
];

// FacetSidebar's desktop `<aside>` carries `hidden ... lg:flex` — real
// desktop-only chrome, distinct from the mobile Sheet-triggered instance.
// Copied from the established pattern in filter-ribbon-selects-open.spec.ts.
function skipOnMobile(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("mobile-"),
    "FacetSidebar's standalone <aside> renders desktop-only (hidden lg:flex); mobile uses the Sheet-triggered instance, out of this test's scope.",
  );
}

test.describe("FacetSidebar — default/collapsed/untagged baselines", () => {
  // Relies on `FacetSidebar`'s `localStorage["catalog:facet-collapse"]`
  // starting unset so `computeDefaultExpanded`'s position-based default (first
  // `DEFAULT_EXPANDED_GROUP_COUNT` groups) applies — true today because
  // Playwright gives every test a fresh, isolated browser context. If this
  // suite is ever reconfigured toward a shared/serial context, this
  // assumption would need re-verifying (review finding).
  test("default state: groups 1-2 expanded, group 3 collapsed", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    // Scoped to the sidebar `<aside>` (implicit role "complementary"): the
    // catalog grid's `ModelCard` also renders `Smok`/tag-slug text (the
    // fixture "dragon" model card), so an unscoped page-wide text match is
    // ambiguous.
    const sidebar = page.getByRole("complementary");

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

  test("group-expand: clicking the collapsed group reveals its tag row", async ({
    page,
  }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    const sidebar = page.getByRole("complementary");
    await sidebar.getByRole("button", { name: "Rozwiń Kolekcja" }).click();

    await expect(sidebar.getByRole("button", { name: "Zwiń Kolekcja" })).toBeVisible();
    await expect(sidebar.getByText("Pojazdy", { exact: true })).toBeVisible();

    await expect(page).toHaveScreenshot("facet-sidebar-group-expanded.png", { fullPage: true });
  });

  test("untagged checkbox renders checked from ?untagged=true", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog?untagged=true");
    await waitForReady(page);

    const untaggedCheckbox = page.getByRole("checkbox", { name: "Modele bez tagów" });
    await expect(untaggedCheckbox).toBeVisible();
    await expect(untaggedCheckbox).toBeChecked();

    await expect(page).toHaveScreenshot("facet-sidebar-untagged.png", { fullPage: true });
  });
});

// Unlike FacetSidebar's standalone `<aside>` (desktop-only, gated above via
// skipOnMobile), FilterRibbon's tag chips/picker/match-mode toggle render
// unconditionally on every viewport — they're not behind any `md:`/`lg:`
// responsive class in FilterRibbon.tsx — so these tests run on all 4
// projects without a skip.
test.describe("FilterRibbon — tag-picker + UI-driven match-mode reveal", () => {
  test("tag picker opens listing all fixture tags", async ({ page }) => {
    await stubSotList(page, { tagGroups: RICH_FIXTURE, tags: RICH_TAGS });
    await page.goto("/catalog");
    await waitForReady(page);

    await page.getByRole("button", { name: "+ tag", exact: true }).click();

    const picker = page.getByRole("dialog", { name: "Dodaj tagi" });
    await expect(picker).toBeVisible();
    await expect(picker.getByRole("option", { name: "dragon" })).toBeVisible();
    await expect(picker.getByRole("option", { name: "castle" })).toBeVisible();
    await expect(picker.getByRole("option", { name: "pla" })).toBeVisible();
    await expect(picker.getByRole("option", { name: "vehicles" })).toBeVisible();
    await expect(picker.getByRole("option", { name: "misc" })).toBeVisible();

    await expect(page).toHaveScreenshot("filter-ribbon-tag-picker-open.png", { fullPage: true });
  });

  // Deliberately UI-driven (not a `?tag_ids=...` URL preset): closes
  // deferred-work.md's "story 44.2 dev repair review" STILL-OPEN item — the
  // FilterRibbon-originated `setFilters` `>=2` gate that reveals the
  // match-mode toggle, previously only reasoned about at the
  // `validateSearch`/`useModels.buildParams` layers.
  test("selecting 2 tags one-by-one through the picker reveals the match-mode toggle", async ({
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

    await page.getByRole("button", { name: "+ tag", exact: true }).click();
    await page.getByRole("option", { name: "dragon" }).click();

    await expect(ribbonChips).toHaveCount(1);

    await page.getByRole("button", { name: "+ tag", exact: true }).click();
    await page.getByRole("option", { name: "castle" }).click();

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
