import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

async function gotoDetail(page: Page) {
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
}

test("catalog detail matches baseline", async ({ page }) => {
  await gotoDetail(page);
  await expect(page).toHaveScreenshot("catalog-detail.png", { fullPage: true });
});

// Story 45.2 — the shared `_test.ts` fixture defaults `/api/auth/me` to admin,
// so the baseline above already covers the admin view (grouped tags + the
// empty-group dash/Add affordance). Override to a member role here to also
// capture the non-admin view, where an empty tag group is omitted entirely
// (no heading, no dash) instead of showing the dash + Add control.
test("catalog detail matches baseline for a non-admin (member) viewer", async ({ page }) => {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "22222222-2222-2222-2222-222222222222",
        email: "member@localhost.localdomain",
        display_name: "Member",
        role: "member",
      }),
    }),
  );
  await gotoDetail(page);
  await expect(page).toHaveScreenshot("catalog-detail-member.png", { fullPage: true });
});

// Story 22.3 (TB-037 viewer + TB-022 consumer) — symmetric fullscreen image
// viewer. Click the gallery main frame, wait for the lazy chunk to mount,
// then snapshot the open viewer overlay. Light + dark + 4 viewports
// resolve via the Playwright project matrix (desktop-light/dark +
// mobile-light/dark — 4 baselines total). Operator does manual verify for
// /share/<token> since no share visual spec exists yet.
test("catalog detail fullscreen image viewer matches baseline", async ({ page }) => {
  await gotoDetail(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  // Wait for the lazy ImageFullscreenViewer chunk to resolve + the Dialog
  // to render its root element.
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail-image-viewer-open.png", {
    fullPage: true,
  });
});
