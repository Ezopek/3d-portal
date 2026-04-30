import type { Page } from "@playwright/test";

export async function waitForReady(page: Page) {
  await page.waitForLoadState("networkidle");
  // Disable animations for stable snapshots.
  await page.addStyleTag({
    content:
      "*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }",
  });
}
