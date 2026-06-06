import { expect, test } from "./_test";
import { stubProfileLibrary } from "./api-stubs";
import { waitForReady } from "./helpers";

// PROFILE-LIB-1 (AC-19, NFR21-VISUAL-VERIFICATION-1) — operator profile-library visual states.
//
// Each state is driven by MOCKED `/api/admin/profiles/library` responses (curated blocks only,
// no raw Orca JSON), so the four projects (desktop-light/dark, mobile-light/dark) are
// pixel-stable. No real import/classify/disk runs.
//
// NOTE (baseline status): the `__snapshots__` PNGs are generated + `baseline-reviewed:` signed
// off in the controller-owned visual pass. Each screenshot call below carries the sign-off
// marker for that review. See the story Dev Agent Record for any deferred-baseline note.

const PROCESS_USABLE = {
  block_id: "0".repeat(32),
  profile_type: "process",
  name: "AI 0.20mm TPU - FlowTech",
  source: "user",
  is_system: false,
  inherit: "0.20mm Standard @Creality K1Max (0.4 nozzle)",
  inherit_chain: ["0.20mm Standard @Creality K1Max (0.4 nozzle)"],
  settings_id: "AI 0.20mm TPU - FlowTech",
  material_type: null,
  compatible_printers: [],
  validation_state: "usable",
  reasons: [],
  portal_label: "TPU FlowTech",
  imported_at: "2026-06-06T00:00:00+00:00",
  imported_by: "11111111-1111-1111-1111-111111111111",
};

const PROCESS_FLAGGED = {
  ...PROCESS_USABLE,
  block_id: "1".repeat(32),
  name: "AI 0.20mm PCTG - MicroSwiss HF",
  inherit: "AI Custom Base - NotSystem",
  inherit_chain: ["AI Custom Base - NotSystem"],
  settings_id: "AI 0.20mm PCTG - MicroSwiss HF",
  validation_state: "requires_attention",
  reasons: ["user_process_invalid_inheritance"],
  portal_label: null,
};

const FILAMENT_USABLE = {
  ...PROCESS_USABLE,
  block_id: "2".repeat(32),
  profile_type: "filament",
  name: "AI Rosa3D Flex 96A Black",
  inherit: "Generic TPU @System",
  inherit_chain: ["Generic TPU @System"],
  settings_id: "AI Rosa3D Flex 96A Black",
  material_type: "TPU",
  compatible_printers: ["Creality K1 Max (0.4 nozzle)"],
  validation_state: "usable",
  reasons: [],
  portal_label: null,
};

const MACHINE_USABLE = {
  ...PROCESS_USABLE,
  block_id: "3".repeat(32),
  profile_type: "machine",
  name: "Creality K1 Max (0.4 nozzle)",
  inherit: "fdm_creality_common",
  inherit_chain: ["fdm_creality_common"],
  settings_id: "GM001",
  material_type: null,
  source: "system",
  is_system: true,
  validation_state: "usable",
  reasons: [],
  portal_label: null,
};

const MIXED = [PROCESS_USABLE, PROCESS_FLAGGED, FILAMENT_USABLE, MACHINE_USABLE];

test.describe("/admin/profile-library baselines", () => {
  test("inventory list — usable + requires_attention across types", async ({ page }) => {
    await stubProfileLibrary(page, { blocks: MIXED });
    await page.goto("/admin/profile-library");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("library-list-mixed.png", { fullPage: true });
  });

  test("empty inventory — upload affordance prominent", async ({ page }) => {
    await stubProfileLibrary(page, { blocks: [] });
    await page.goto("/admin/profile-library");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("library-empty-upload.png", { fullPage: true });
  });

  test("import rejection surfaced inline", async ({ page }) => {
    await stubProfileLibrary(page, {
      blocks: [],
      postRejection: { status: 422, reason_category: "unsupported_profile" },
    });
    await page.goto("/admin/profile-library");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    const file = {
      name: "weird.json",
      mimeType: "application/json",
      buffer: Buffer.from('{"a":1}'),
    };
    await page.locator('input[type="file"]').setInputFiles(file);
    await page.getByRole("alert").waitFor({ state: "visible" });
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("library-import-rejected.png", { fullPage: true });
  });

  test("block detail — inherit chain + requires_attention reason", async ({ page }) => {
    await stubProfileLibrary(page, { blocks: [PROCESS_FLAGGED, FILAMENT_USABLE] });
    await page.goto("/admin/profile-library");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    // Locale-agnostic: the detail toggle is the collapsed (aria-expanded=false) chevron
    // button — the visual suite runs in pl-PL, so an English-name selector would not match.
    await page.locator('button[aria-expanded="false"]').first().click();
    await waitForReady(page);
    // baseline-reviewed:
    await expect(page).toHaveScreenshot("library-detail-expanded.png", { fullPage: true });
  });
});
