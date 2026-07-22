import { expect, test } from "./_test";
import { waitForReady } from "./helpers";

// Story 47.5 (T-V2) — the admin Add Model form (/admin/models/new) after the
// terminal taxonomy cutover: the form carries name/source/status/rating/
// description fields only — no classification selector of any kind (tagging
// happens post-create via EditTagsSheet/TagGroupsSection on the detail page).
//
// The default `_test.ts` fixture authenticates as admin and 404-stubs every
// unlisted `/api/*` route, so the page renders deterministically with no extra
// stubs: the form issues no read requests at mount time.
//
// Per the E45/E46 test-authoring rule, the specific rendered state is asserted
// visible immediately before the screenshot. The visual harness forces pl-PL
// (playwright.config.ts), so text matchers are Polish.

test.describe("/admin/models/new baselines", () => {
  test("add-model form — no classification selector", async ({ page }) => {
    await page.goto("/admin/models/new");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    await expect(page.getByRole("heading", { name: "Dodaj model" })).toBeVisible();
    await expect(page.getByText("Nazwa (angielska)")).toBeVisible();
    await expect(page.getByText("Nazwa (polska)")).toBeVisible();
    await expect(page.getByText("Źródło")).toBeVisible();
    await expect(page.getByText("Ocena (1.0–5.0)")).toBeVisible();
    await expect(page.getByRole("button", { name: "Utwórz model" })).toBeVisible();
    // Exactly the two enum selects (source, status) — the retired taxonomy
    // selector must not resurface as a third combobox.
    await expect(page.getByRole("combobox")).toHaveCount(2);

    await expect(page).toHaveScreenshot("add-model-form.png", { fullPage: true });
  });
});
