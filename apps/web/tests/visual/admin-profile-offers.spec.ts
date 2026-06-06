import { expect, test } from "./_test";
import { stubProfileOffers } from "./api-stubs";
import { waitForReady } from "./helpers";

// PROFILE-OFFER-1 (AC-20, NFR21-VISUAL-VERIFICATION-1) — admin profile-offer visual states.
//
// Each state is driven by MOCKED `/api/admin/profiles/offers` (+ `/library` for the compose
// pickers) responses (curated DTOs only, no raw Orca JSON), so the four projects
// (desktop-light/dark, mobile-light/dark) are pixel-stable. No real validate/disk runs.
//
// NOTE (baseline status): the `__snapshots__` PNGs are generated + `baseline-reviewed:` signed
// off in the controller-owned visual pass. Each screenshot call below carries the sign-off
// marker for that review. See the story Dev Agent Record for any deferred-baseline note.

const MACHINE_ID = "3".repeat(32);
const PROCESS_ID = "1".repeat(32);
const FILAMENT_ID = "2".repeat(32);

const MACHINE_BLOCK = {
  block_id: MACHINE_ID,
  profile_type: "machine",
  name: "Creality K1 Max (0.4 nozzle)",
  source: "system",
  is_system: true,
  inherit: "fdm_creality_common",
  inherit_chain: ["fdm_creality_common"],
  settings_id: "GM001",
  material_type: null,
  compatible_printers: [],
  validation_state: "usable",
  reasons: [],
  portal_label: null,
  imported_at: "2026-06-06T00:00:00+00:00",
  imported_by: "11111111-1111-1111-1111-111111111111",
};

const PROCESS_BLOCK = {
  ...MACHINE_BLOCK,
  block_id: PROCESS_ID,
  profile_type: "process",
  name: "0.20mm Standard MicroSwiss",
  source: "user",
  is_system: false,
  settings_id: "0.20mm Standard MicroSwiss",
};

const FILAMENT_BLOCK = {
  ...MACHINE_BLOCK,
  block_id: FILAMENT_ID,
  profile_type: "filament",
  name: "Rosa3D PLA Black",
  source: "user",
  is_system: false,
  inherit: "Generic PLA @System",
  inherit_chain: ["Generic PLA @System"],
  settings_id: "Rosa3D PLA Black",
  material_type: "PLA",
  compatible_printers: ["Creality K1 Max (0.4 nozzle)"],
};

const LIBRARY = [MACHINE_BLOCK, PROCESS_BLOCK, FILAMENT_BLOCK];

const OFFER_USABLE = {
  offer_id: "a".repeat(32),
  label: "Rosa PLA — standard",
  description: "Everyday PLA preset",
  chain: {
    machine_block_id: MACHINE_ID,
    process_block_id: PROCESS_ID,
    filament_block_id: FILAMENT_ID,
  },
  visibility: "visible",
  is_default: true,
  compatible_material_categories: ["PLA"],
  validation_state: "usable",
  reasons: [],
  chain_blocks: [MACHINE_BLOCK, PROCESS_BLOCK, FILAMENT_BLOCK],
  created_at: "2026-06-06T00:00:00+00:00",
  created_by: "11111111-1111-1111-1111-111111111111",
  updated_at: "2026-06-06T00:00:00+00:00",
};

const OFFER_ATTENTION = {
  ...OFFER_USABLE,
  offer_id: "b".repeat(32),
  label: "Flex draft",
  description: null,
  visibility: "hidden",
  is_default: false,
  compatible_material_categories: ["TPU"],
  validation_state: "requires_attention",
  reasons: ["filament_machine_incompatible"],
};

const OFFER_INVALID = {
  ...OFFER_USABLE,
  offer_id: "c".repeat(32),
  label: "Old PETG offer",
  description: null,
  visibility: "visible",
  is_default: false,
  compatible_material_categories: ["PETG"],
  validation_state: "invalid",
  reasons: ["unknown_block"],
  // A deleted referenced machine block ⇒ omitted from the echo (surfaced via unknown_block).
  chain_blocks: [PROCESS_BLOCK, FILAMENT_BLOCK],
};

const MIXED = [OFFER_USABLE, OFFER_ATTENTION, OFFER_INVALID];

test.describe("/admin/profile-offers baselines", () => {
  test("offer list — usable + requires_attention + invalid", async ({ page }) => {
    await stubProfileOffers(page, { offers: MIXED, library: LIBRARY });
    await page.goto("/admin/profile-offers");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("offers-list-mixed.png", { fullPage: true });
  });

  test("compose panel open — three slot pickers + toggles", async ({ page }) => {
    await stubProfileOffers(page, { offers: [], library: LIBRARY });
    await page.goto("/admin/profile-offers");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    // Locale-agnostic: the compose action is the only primary button; open the panel and wait
    // for the first slot <select> to appear (the visual suite runs in pl-PL).
    await page.getByRole("button", { name: "Utwórz ofertę" }).click();
    await page.locator("select").first().waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("offers-compose-open.png", { fullPage: true });
  });

  test("create rejection surfaced inline", async ({ page }) => {
    await stubProfileOffers(page, {
      offers: [],
      library: LIBRARY,
      postRejection: { status: 422, reason_category: "invalid_chain" },
    });
    await page.goto("/admin/profile-offers");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await page.getByRole("button", { name: "Utwórz ofertę" }).click();
    const selects = page.locator("select");
    await selects.nth(0).selectOption(MACHINE_ID);
    await selects.nth(1).selectOption(PROCESS_ID);
    await selects.nth(2).selectOption(FILAMENT_ID);
    await page.locator('input[type="text"]').first().fill("Bad chain");
    // force: the Save button is the last flow child of a tall non-positioned form card; on the
    // 411px Pixel-5 viewport its center sits at the scroll edge so the actionability hit-test
    // resolves to the (ancestor) card. Playwright already reports the button visible+enabled+
    // stable — the card cannot overlay its own last flow child, so this is a hit-test artifact.
    await page.getByRole("button", { name: "Zapisz ofertę" }).click({ force: true });
    await page.getByRole("alert").waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("offers-create-rejected.png", { fullPage: true });
  });

  test("offer detail — curated chain blocks + requires_attention reason", async ({ page }) => {
    await stubProfileOffers(page, { offers: [OFFER_ATTENTION], library: LIBRARY });
    await page.goto("/admin/profile-offers");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    // Target the row's detail expander by its accessible name (pl visual locale) — NOT a bare
    // aria-expanded selector, which would match the TopBar account-menu trigger first.
    await page.getByRole("button", { name: "Pokaż szczegóły" }).first().click();
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("offers-detail-expanded.png", { fullPage: true });
  });
});
