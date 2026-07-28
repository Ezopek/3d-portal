import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";

// Story 50.3 — inline structured suggestions. The populated fixture below
// exercises: a group suffix (Dragon · Motyw) and a matched-alias hint (the
// harness forces pl-PL, so the query "smok" matches Dragon's name_pl "Smok"
// while name_en "Dragon" does not contain it — D-4). Per the Epic 45 retro
// action ("every UI story that adds a rendered state owes a pre-screenshot
// toBeVisible() assertion for that specific state"), each test asserts the
// concrete populated rows are visible *immediately before* toHaveScreenshot.

const GROUP_THEME_ID = "55555555-5555-5555-5555-555555555501";
const TAG_DRAGON_ID = "55555555-5555-5555-5555-555555555541";
const TAG_DRAKE_ID = "55555555-5555-5555-5555-555555555542";

const TAG_GROUPS: TagGroupsResponse = {
  groups: [
    {
      id: GROUP_THEME_ID,
      slug: "theme",
      name_en: "Theme",
      name_pl: "Motyw",
      position: 0,
      tags: [],
    },
  ],
  groupless: [],
};

const SUGGESTION_TAGS: TagListItem[] = [
  {
    id: TAG_DRAGON_ID,
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    group_id: GROUP_THEME_ID,
    group_position: 0,
  },
  {
    id: TAG_DRAKE_ID,
    slug: "drake",
    name_en: "Drake",
    name_pl: null,
    group_id: null,
    group_position: 0,
  },
];

async function setup(page: Page) {
  // stubSotList's default /api/tags* route always wins the last-registered
  // match, so register a query-specific override AFTER it to serve the
  // richer suggestion fixture while the "drag" query is active — matching
  // this suite's own populated state, not stubSotList's 2-tag default.
  await stubSotList(page, { tagGroups: TAG_GROUPS });
  await page.route("**/api/tags?q=drag**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SUGGESTION_TAGS),
    }),
  );
  await page.goto("/catalog");
  await waitForReady(page);
}

test.describe("catalog search suggestions — pl-PL baselines (Story 50.3)", () => {
  test("populated panel: plain-query row, group suffix, and matched alias", async ({ page }) => {
    await setup(page);

    const input = page.getByRole("combobox", { name: "Szukaj" });
    // Under pl-PL (preferPl), Dragon's active label is its name_pl "Smok".
    // Querying "drag" matches only the non-active (en) name, so D-4's
    // matched-alias renders "Dragon" beneath the "Smok" pill.
    await input.fill("drag");

    const listbox = page.getByRole("listbox");
    await expect(listbox).toBeVisible();
    // Row 1 — plain-query option, Polish accessible name (catalog.suggestions.queryOption).
    await expect(page.getByRole("option", { name: "Szukaj: drag" })).toBeVisible();
    // Row 2 — Dragon tag, active pl label "Smok", group suffix "Motyw", en alias "Dragon".
    await expect(
      page.getByRole("option", { name: "Dodaj filtr: Smok, grupa Motyw" }),
    ).toBeVisible();
    await expect(listbox.getByText("Dragon")).toBeVisible();
    // Row 3 — Drake tag, groupless (no suffix), no alias (name_pl is null).
    await expect(page.getByRole("option", { name: "Dodaj filtr: Drake" })).toBeVisible();

    await expect(page).toHaveScreenshot("catalog-search-suggestions-populated.png");
  });
});
