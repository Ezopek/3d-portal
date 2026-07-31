/*
 * Story 54.2 / AC-1 + T2 (Decision D-1) — WCAG 2.2 SC 2.5.8 Target Size
 * (Minimum) measured across the whole Initiative 26 journey, in real Chromium,
 * on all four Playwright projects.
 *
 * D-1: "The audit unit for target size is the rendered border box, not the
 * class. A class-level audit is a guess." Every number below therefore comes
 * from `getBoundingClientRect()` on the live element — never from a Tailwind
 * class. The class-level seed list in the story (§ 2 V-10) was a candidate
 * generator only.
 *
 * ⚠️ SCOPE OF THE CLAIM (story § 0.1). Headless-Chromium evidence only. The
 * `mobile-*` projects are a desktop Chromium with an emulated Pixel 5 viewport,
 * DPR and touch flag — EMULATION, never "Android". No physical device was used;
 * no screen reader was run.
 *
 * D-7 (controller-ruled): the "viewer" on this journey is the PHOTO LIGHTBOX.
 * `viewer3d/*` chrome is measured only where the probe reaches it naturally on
 * the model-detail route, and is never remediated here. This spec does not
 * mount a single `viewer3d` surface on purpose.
 *
 * WHAT COUNTS AS A TARGET
 * -----------------------
 * Every rendered, enabled, non-`aria-hidden` interactive element, keyed by its
 * accessible name / testid. Zero-size and `display:none` elements are skipped
 * (they are not on screen). Elements revealed only on hover (`sm:opacity-0
 * sm:group-hover:opacity-100`) ARE measured: they are keyboard-reachable via
 * `focus-visible:opacity-100`, so they are real targets.
 *
 * THE KNOWN LIST
 * --------------
 * `SC_2_5_8_KNOWN` is the only escape hatch, and it does NOT mean "waived".
 * Each entry is one of exactly two things, and says which:
 *
 *   `exception:` — a genuine WCAG 2.5.8 exception (Inline / User agent control
 *                  / Essential / Equivalent), named. This is a PASS.
 *   `routed:`    — a real, measured failure that this story deliberately does
 *                  not remediate, with the story that shipped the surface and
 *                  the `deferred-work.md` owner. This is a FAIL that is
 *                  tracked, not hidden.
 *
 * The gate is therefore a REGRESSION gate: any NEW undersized control fails the
 * suite, and removing a `routed:` entry is how a future story proves it closed
 * one. An entry with neither field is a bug, not a waiver.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail, stubSotList } from "./api-stubs";
import { loginAsAdmin, waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

/** `{spacing.target-min}` — EXPERIENCE.md:302, WCAG 2.2 SC 2.5.8. */
const TARGET_MIN_PX = 24;
/** Sub-pixel tolerance for the Pixel 5 projects' device-scale-factor rounding. */
const EPSILON_PX = 0.5;

interface Target {
  key: string;
  tag: string;
  width: number;
  height: number;
  className: string;
}

/**
 * Controls measured BELOW the floor that this story does not resize. Keyed by
 * the probe's stable `key` (or a prefix of it, for keys that carry fixture
 * data such as a filename or a URL).
 */
// Matched by REGEX, not by prefix, and every pattern is anchored. A prefix
// match silently over-waived once already during this story's own dev pass:
// `button:Usuń ` was written for FilesTab's `Usuń dragon.stl` and quietly
// swallowed FilterRibbon's `Usuń tag dragon`, hiding a real journey finding.
const SC_2_5_8_KNOWN: { match: RegExp; exception?: string; routed?: string }[] = [
  {
    match: /^a:https?:\/\//,
    exception:
      'WCAG 2.5.8 "Inline" — `ExternalLinksPanel` renders the raw URL as flowing' +
      " text inside a paragraph, so the target height is the line box and is not" +
      " independently author-controlled. Measured 20 px tall; PASSES by exception.",
  },
  // ---- Routed, not waived. All four are `tabs/FilesTab.tsx` (shipped by
  // `06ece7b`, 2026-05-05 — Initiative-13 era, two initiatives before this
  // audit). They sit on the model-detail ROUTE but not on the § 1 journey
  // (browse -> detail -> photo lightbox); FilesTab is the admin file-management
  // sibling tab. Same treatment D-7 rules for `viewer3d`: measured here, routed
  // out of remediation. Ledgered in `deferred-work.md` under Story 54.2.
  {
    match: /^input:include .+ in renders$/,
    routed:
      "FilesTab render-selection checkbox, measured 13x13 with no associated" +
      " <label> to enlarge the target. Owner: deferred-work.md (Story 54.2 audit).",
  },
  {
    match: /^button:Toggle 3D preview for .+$/,
    routed: "FilesTab row action, measured 48x22. Owner: deferred-work.md (Story 54.2 audit).",
  },
  {
    match: /^a:Pobierz$/,
    routed: "FilesTab download link, measured 30x22. Owner: deferred-work.md (Story 54.2 audit).",
  },
  {
    match: /^button:Usuń \S+\.\w+$/,
    routed: "FilesTab delete action, measured 30x22. Owner: deferred-work.md (Story 54.2 audit).",
  },
];

function knownEntry(key: string) {
  return SC_2_5_8_KNOWN.find((entry) => entry.match.test(key));
}

/**
 * Collect every rendered interactive target with its measured border box.
 * Runs entirely in the page so the numbers are Chromium's, not a heuristic.
 */
async function measureTargets(page: Page): Promise<Target[]> {
  return page.evaluate(() => {
    const SELECTOR = [
      "a[href]",
      "button",
      "input:not([type=hidden])",
      "select",
      "textarea",
      "summary",
      '[role="button"]',
      '[role="link"]',
      '[role="checkbox"]',
      '[role="radio"]',
      '[role="switch"]',
      '[role="tab"]',
      '[role="menuitem"]',
      '[role="menuitemcheckbox"]',
      '[role="option"]',
      '[role="combobox"]',
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");

    const out: Target[] = [];
    const seen = new Set<Element>();
    for (const el of Array.from(document.querySelectorAll(SELECTOR))) {
      if (seen.has(el)) continue;
      seen.add(el);
      if (el.closest('[aria-hidden="true"]') !== null) continue;
      if (el.hasAttribute("inert") || el.closest("[inert]") !== null) continue;
      if ((el as HTMLButtonElement).disabled) continue;
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") continue;
      // The target is the region that ACCEPTS THE POINTER ACTION, not the
      // painted glyph. For a form control that means its associated `<label>`
      // as well: clicking anywhere on `<label class="min-h-9">…<input
      // class="size-4">…</label>` activates the control, so the target is 36 px
      // tall even though the checkbox paints at 16. Measuring the `<input>`
      // alone reports a failure the user cannot experience.
      let r = el.getBoundingClientRect();
      const id = el.getAttribute("id");
      const label =
        el.closest("label") ??
        (id !== null ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null);
      if (label !== null) {
        const lr = label.getBoundingClientRect();
        if (lr.width > 0 && lr.height > 0) {
          const left = Math.min(r.left, lr.left);
          const top = Math.min(r.top, lr.top);
          r = new DOMRect(
            left,
            top,
            Math.max(r.right, lr.right) - left,
            Math.max(r.bottom, lr.bottom) - top,
          );
        }
      }
      // A zero box is not on screen at all — nothing to measure.
      if (r.width === 0 || r.height === 0) continue;
      // `sr-only` controls are not visual targets; they exist for AT only.
      if (r.width <= 1 && r.height <= 1) continue;
      const name =
        el.getAttribute("data-testid") ??
        el.getAttribute("aria-label") ??
        (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 40) ??
        "";
      out.push({
        key: `${el.tagName.toLowerCase()}:${name || "<unnamed>"}`,
        tag: el.tagName.toLowerCase(),
        width: Math.round(r.width * 100) / 100,
        height: Math.round(r.height * 100) / 100,
        className: el.className.toString().slice(0, 80),
      });
    }
    return out;
  });
}

/** Assert every measured target clears the 24x24 floor, minus documented exemptions. */
async function expectTargetsMeetFloor(page: Page, surface: string) {
  const targets = await measureTargets(page);
  expect(targets.length, `${surface}: probe found no targets to measure`).toBeGreaterThan(0);

  const undersized = targets.filter(
    (t) =>
      t.width < TARGET_MIN_PX - EPSILON_PX || t.height < TARGET_MIN_PX - EPSILON_PX,
  );
  const unknown = undersized.filter((t) => knownEntry(t.key) === undefined);

  expect(
    unknown.map((t) => `${t.key} = ${t.width}x${t.height}`).sort(),
    `${surface}: control(s) under the ${TARGET_MIN_PX}x${TARGET_MIN_PX} CSS px floor` +
      ` (EXPERIENCE.md:302, WCAG 2.2 SC 2.5.8). Full class: ` +
      JSON.stringify(unknown.map((t) => ({ key: t.key, cls: t.className }))),
  ).toEqual([]);

}

// ---------------------------------------------------------------------------
// Browse — /catalog, default state. Desktop renders BrowseRail, mobile renders
// the BrowseSheet trigger; both regimes are covered by the project matrix.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog default (browse rail / browse trigger + filter ribbon)", async ({
  page,
}) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
  await expect(page.getByRole("button", { name: "Filtry", exact: true })).toBeVisible();
  await expectTargetsMeetFloor(page, "/catalog default");
});

// ---------------------------------------------------------------------------
// Browse — /catalog with two tag constraints active, which is the ONLY state
// that renders FilterRibbon's remove-chip buttons and the match-mode toggle.
// A probe of the default state cannot see either.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog with active tag chips (remove + match-mode)", async ({ page }) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);

  // Selected through the panel's facet checkboxes, the way a user gets here.
  await page.getByRole("button", { name: "Filtry", exact: true }).click();
  const sheet = page.locator('[data-slot="sheet-content"]');
  await expect(sheet).toBeVisible();
  // `stubSotList`'s default group carries exactly these two tags; `name_pl` is
  // null on the second, so it falls back to `name_en` (`FacetSidebar.tsx:80`).
  await sheet.getByRole("checkbox", { name: /^Smok/ }).check();
  await sheet.getByRole("checkbox", { name: /^Articulated/ }).check();
  await page.keyboard.press("Escape");
  await expect(sheet).not.toBeVisible();

  const ribbonChips = page
    .getByTestId("tag-chip")
    .filter({ has: page.getByRole("button", { name: /^Usuń tag /i }) });
  await expect(ribbonChips).toHaveCount(2);
  await expect(page.getByRole("group", { name: "Dopasowanie tagów" })).toBeVisible();

  await expectTargetsMeetFloor(page, "/catalog with tag chips");
});

// ---------------------------------------------------------------------------
// Filters — the open panel (right panel at lg+, bottom sheet below).
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog with the Filters panel open", async ({ page }) => {
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
  await page.getByRole("button", { name: "Filtry", exact: true }).click();
  await expect(page.locator('[data-slot="sheet-content"]')).toBeVisible();
  await expectTargetsMeetFloor(page, "/catalog Filters panel open");
});

// ---------------------------------------------------------------------------
// Browse sheet — the mobile browse surface (lg:hidden trigger).
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog with the Browse sheet open", async ({ page }, testInfo) => {
  test.skip(
    !testInfo.project.name.startsWith("mobile-"),
    "BrowseSheet's trigger is lg:hidden; the desktop browse surface is the rail.",
  );
  await stubSotList(page);
  await page.goto("/catalog");
  await waitForReady(page);
  await page.getByRole("button", { name: "Przeglądaj" }).click();
  await expect(page.locator('[data-slot="sheet-content"]')).toBeVisible();
  await expectTargetsMeetFloor(page, "/catalog Browse sheet open");
});

// ---------------------------------------------------------------------------
// Category scope — /categories/$slug, which is where ScopeChip renders.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /categories/$slug with the scope chip", async ({ page }) => {
  await stubSotList(page);
  await page.goto("/categories/uchwyty");
  await waitForReady(page);
  await expect(page.getByRole("group", { name: /Uchwyty i mocowania/ })).toBeVisible();
  await expectTargetsMeetFloor(page, "/categories/$slug");
});

// ---------------------------------------------------------------------------
// Model detail — the hero, the secondary tabs and the gallery triggers.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog/$id model detail", async ({ page }) => {
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await expect(page.getByTestId("gallery-fullscreen-trigger")).toBeVisible();
  await expectTargetsMeetFloor(page, "/catalog/$id detail");
});

// ---------------------------------------------------------------------------
// Model detail — the PHOTOS tab. This is AC-2 / V-1's surface: the drag handle
// whose border box WAS the 16x16 icon, and the move-up/move-down pair that is
// the SC 2.5.7 single-pointer alternative to the drag.
//
// It needs its own entry because the probe cannot reach it from the default
// detail state: the tab is `isAdmin`-gated (`SecondaryTabs.tsx:49`) and its
// panel is unmounted until selected, so the "model detail" test above measures
// zero PhotosTab controls. Without this, `PhotosTab.tsx`'s own comment —
// "the RENDERED box is measured in Chromium by tests/visual/a11y-target-size.
// spec.ts (D-1)" — would be a citation of coverage that does not exist, which
// is precisely the defect class D-1 and D-2 were written to prevent.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog/$id Photos tab (drag handle + move-up/move-down)", async ({ page }) => {
  await loginAsAdmin(page);
  await stubSotDetail(page, { imageCount: 2 });
  // `usePhotos` reads the LIST endpoint (`/models/:id/files`), which is a
  // different call from the model-detail payload `stubSotDetail` serves and is
  // not stubbed by it — `_test.ts`'s catch-all 404s it, leaving the tab empty.
  // Two photos, because move-up/move-down only render meaningfully with a
  // neighbour to move past.
  await page.route(`**/api/models/${MODEL_ID}/files`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "f2",
            model_id: MODEL_ID,
            kind: "image",
            original_name: "iso.png",
            storage_path: "",
            sha256: "",
            size_bytes: 1024,
            mime_type: "image/png",
            position: 1,
            created_at: "",
          },
          {
            id: "f3",
            model_id: MODEL_ID,
            kind: "image",
            original_name: "side.png",
            storage_path: "",
            sha256: "",
            size_bytes: 1024,
            mime_type: "image/png",
            position: 2,
            created_at: "",
          },
        ],
        total: 2,
        page: 1,
        page_size: 50,
      }),
    }),
  );
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // catalog.tabs.photos = "Zdjęcia"; the trigger carries a count suffix.
  await page.getByRole("tab", { name: /^Zdjęcia\b/ }).click();

  // Non-vacuity: the assertion below is worthless if the rows never rendered.
  await expect(page.getByTestId("photo-drag-handle").first()).toBeVisible();
  await expect(page.getByTestId("photo-move-down").first()).toBeVisible();

  await expectTargetsMeetFloor(page, "/catalog/$id Photos tab");
});

// ---------------------------------------------------------------------------
// The photo lightbox — the "viewer" D-7 scopes this story to.
// ---------------------------------------------------------------------------
test("SC 2.5.8 — /catalog/$id with the photo lightbox open", async ({ page }) => {
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();
  await expect(page.getByTestId("image-viewer-zoom-in")).toBeEnabled();
  await expectTargetsMeetFloor(page, "/catalog/$id lightbox open");
});
