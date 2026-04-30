import type { Page } from "@playwright/test";

export async function waitForReady(page: Page) {
  await page.waitForLoadState("networkidle");
  // Disable animations for stable snapshots.
  await page.addStyleTag({
    content:
      "*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }",
  });
}

export async function loginAsAdmin(page: Page) {
  // Build a JWT-shaped token whose payload decodes to {role: "admin"} so the
  // frontend's isAdmin() check (which decodes the payload) returns true.
  // Header/signature are placeholders — the SPA never verifies the signature.
  await page.addInitScript(() => {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
      .replace(/=+$/, "");
    const payload = btoa(
      JSON.stringify({ sub: "1", role: "admin", exp: 9999999999 }),
    ).replace(/=+$/, "");
    const token = `${header}.${payload}.sig`;
    localStorage.setItem("portal.token", token);
    localStorage.setItem(
      "portal.token.exp",
      String(Date.now() + 60 * 60 * 1000),
    );
  });
}
