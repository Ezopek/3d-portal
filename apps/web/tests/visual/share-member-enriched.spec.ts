// Initiative 18 Story 30.2 (FR18-MEMBER-SHARE-VIEW-1) — visual baseline
// for the B5 enrich-in-place render: authenticated member opens
// /share/<token>, sees the canonical catalog detail UI plus a dismissible
// info-bar. URL stays /share/<token> (brainstorm rα-1 mitigation).
//
// Reuses the catalog-detail stub fixture (stubSotDetail) — same model_id
// the canonical /catalog/$id render uses — so the only visual diff vs the
// existing catalog-detail baseline is the info-bar at the top.

import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";

const TOKEN = "test-token-30-2-enriched";
const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

test("share-member-enriched: B5 sees canonical catalog body + info-bar", async ({
  page,
}) => {
  // Default api-stubs returns ADMIN for /auth/me — that's a valid
  // authenticated state for B5. No override needed.
  await stubSotDetail(page);
  await page.route(`**/api/me/share-links/${TOKEN}/resolve`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ model_id: MODEL_ID, access: "granted" }),
    }),
  );

  await page.goto(`/share/${TOKEN}`);
  // Wait for the info-bar (renders only on B5 enriched success).
  await page
    .getByText(/Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i)
    .first()
    .waitFor();

  await expect(page).toHaveScreenshot("share-member-enriched.png", {
    fullPage: true,
    animations: "disabled",
  });
});
