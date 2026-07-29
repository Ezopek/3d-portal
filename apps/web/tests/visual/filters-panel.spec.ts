import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotList } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";

// Story 52.1 AC-27 — the consolidated `Filters (n)` surface. Four states, each
// captured on all four Playwright projects, which is what gives the required
// light + dark × desktop + mobile matrix (playwright.config.ts also forces
// `pl-PL`, so every matcher below is the literal pl.json string):
//
//   1. the panel open as a RIGHT panel at `lg`+            (desktop projects)
//   2. the panel open as a BOTTOM sheet below `lg`          (mobile projects)
//   3. the trigger WITHOUT a badge (n === 0)                (all projects)
//   4. the trigger WITH a badge (n > 0)                     (all projects)
//
// Per the Epic 45/46 test-authoring rule, every `toHaveScreenshot` is preceded
// by an explicit `toBeVisible()` on the concrete state being captured.

const GROUP_THEME_ID = "55555555-5555-5555-5555-555555555501";
const GROUP_MATERIAL_ID = "55555555-5555-5555-5555-555555555502";

const TAG_DRAGON_ID = "55555555-5555-5555-5555-555555555541";
const TAG_CASTLE_ID = "55555555-5555-5555-5555-555555555542";
const TAG_PLA_ID = "55555555-5555-5555-5555-555555555543";
const TAG_MISC_ID = "55555555-5555-5555-5555-555555555544";

const FIXTURE: TagGroupsResponse = {
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

// Derived from `FIXTURE`, never hand-duplicated, so the flat tag list
// `FilterRibbon`'s chip labels use and the grouped tree the panel renders
// cannot drift apart.
const TAGS: TagListItem[] = [
  ...FIXTURE.groups.flatMap((g) => g.tags),
  ...FIXTURE.groupless,
];

async function setup(page: Page, url = "/catalog") {
  await stubSotList(page, { tagGroups: FIXTURE, tags: TAGS });
  await page.goto(url);
  await waitForReady(page);
}

function skipOnMobile(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("mobile-"),
    "Right-panel presentation is the `lg`+ regime only (EXPERIENCE.md:328-331).",
  );
}

function skipOnDesktop(testInfo: { project: { name: string } }) {
  test.skip(
    testInfo.project.name.startsWith("desktop-"),
    "Bottom-sheet presentation is the below-`lg` regime only (EXPERIENCE.md:328-331).",
  );
}

test.describe("FiltersPanel — open-surface baselines (Story 52.1)", () => {
  test("opens as a right panel at lg and above", async ({ page }, testInfo) => {
    skipOnMobile(testInfo);
    await setup(page);

    // catalog.filters.openFilters = "Filtry"; at n === 0 that IS the whole
    // accessible name, which is itself the no-badge proof.
    await page.getByRole("button", { name: "Filtry", exact: true }).click();

    const sheet = page.locator("[data-slot='sheet-content']");
    await expect(sheet).toBeVisible();
    await expect(sheet).toHaveAttribute("data-side", "right");
    // The panel is exhaustive: the facet surface AND the three Selects.
    await expect(sheet.getByRole("button", { name: "Zwiń Motyw" })).toBeVisible();
    await expect(sheet.getByText("Smok", { exact: true })).toBeVisible();
    await expect(
      sheet.getByRole("checkbox", { name: "Modele bez tagów" }),
    ).toBeVisible();
    await expect(sheet.getByRole("combobox", { name: "Status" })).toBeVisible();
    await expect(sheet.getByRole("combobox", { name: "Źródło" })).toBeVisible();
    await expect(sheet.getByRole("combobox", { name: "Sortowanie" })).toBeVisible();

    await expect(sheet).toHaveScreenshot("filters-panel-right-open.png");
  });

  test("opens as a bottom sheet below lg", async ({ page }, testInfo) => {
    skipOnDesktop(testInfo);
    await setup(page);

    await page.getByRole("button", { name: "Filtry", exact: true }).click();

    const sheet = page.locator("[data-slot='sheet-content']");
    await expect(sheet).toBeVisible();
    await expect(sheet).toHaveAttribute("data-side", "bottom");
    await expect(sheet.getByRole("button", { name: "Zwiń Motyw" })).toBeVisible();
    await expect(
      sheet.getByRole("checkbox", { name: "Modele bez tagów" }),
    ).toBeVisible();
    await expect(sheet.getByRole("combobox", { name: "Sortowanie" })).toBeVisible();

    await expect(sheet).toHaveScreenshot("filters-panel-bottom-open.png");
  });
});

test.describe("FiltersPanel — trigger badge baselines (Story 52.1)", () => {
  test("trigger renders without a badge at n = 0", async ({ page }) => {
    await setup(page);

    const trigger = page.getByRole("button", { name: "Filtry", exact: true });
    await expect(trigger).toBeVisible();
    // AC-9 — the badge node is absent entirely, never a rendered "0".
    await expect(trigger.getByTestId("filters-trigger-badge")).toHaveCount(0);

    await expect(trigger).toHaveScreenshot("filters-trigger-no-badge.png");
  });

  test("trigger renders the count badge at n > 0", async ({ page }) => {
    // status + source = 2. `sort` is deliberately non-default here as well and
    // must NOT push the count to 3 (AC-7).
    await setup(page, "/catalog?status=printed&source=own&sort=name_asc");

    const trigger = page.getByRole("button", { name: "Filtry (2)", exact: true });
    await expect(trigger).toBeVisible();
    const badge = trigger.getByTestId("filters-trigger-badge");
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText("2");

    await expect(trigger).toHaveScreenshot("filters-trigger-badge.png");
  });
});
