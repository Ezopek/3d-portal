// Initiative 18 Story 30.2 (FR18-INFO-BAR-1) — visual baseline for the B5
// enriched render with the info-bar pre-dismissed via sessionStorage. Same
// render shape as share-member-enriched.spec.ts but with the info-bar
// hidden (verifies Decision AC dismissal contract end-to-end).
//
// sessionStorage pre-seed via page.addInitScript runs BEFORE any document
// JS evaluates, so the first ShareMemberContextInfoBar mount reads the
// dismissed flag and renders null.

import { expect, test } from "./_test";

import { stubSotDetail } from "./api-stubs";

const TOKEN = "test-token-30-2-dismissed";
const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

test("share-member-enriched-dismissed: info-bar pre-dismissed via sessionStorage", async ({
  page,
}) => {
  await page.addInitScript((mid) => {
    sessionStorage.setItem("share-context-dismissed:" + mid, "1");
  }, MODEL_ID);

  await stubSotDetail(page);
  await page.route(`**/api/me/share-links/${TOKEN}/resolve`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ model_id: MODEL_ID, access: "granted" }),
    }),
  );

  await page.goto(`/share/${TOKEN}`);
  // Wait for the canonical catalog body (ModelHero title) — proves the
  // member render mounted, and absence of info-bar text proves dismissal.
  await page.getByText(/Smok|Dragon/i).first().waitFor();
  // Belt-and-suspenders: assert the info-bar text is NOT present.
  await expect(
    page.getByText(/Otworzyłeś ten model z linku udostępnionego|You opened this model from a shared link/i),
  ).toHaveCount(0);

  await expect(page).toHaveScreenshot("share-member-enriched-dismissed.png", {
    fullPage: true,
    animations: "disabled",
  });
});
