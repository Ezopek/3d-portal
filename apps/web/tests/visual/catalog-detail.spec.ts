import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog detail matches baseline", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto("/catalog/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail.png", { fullPage: true });
});

// Story 22.3 (TB-037 viewer + TB-022 consumer) — symmetric fullscreen image
// viewer. Click the gallery main frame, wait for the lazy chunk to mount,
// then snapshot the open viewer overlay. Light + dark + 4 viewports
// resolve via the Playwright project matrix (desktop-light/dark +
// mobile-light/dark — 4 baselines total). Operator does manual verify for
// /share/<token> since no share visual spec exists yet.
test("catalog detail fullscreen image viewer matches baseline", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto("/catalog/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  // Wait for the lazy ImageFullscreenViewer chunk to resolve + the Dialog
  // to render its root element.
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-detail-image-viewer-open.png", {
    fullPage: true,
  });
});
