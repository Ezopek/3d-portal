// Story 53.2 (E53 / FR26-VIEW-1, NFR26-A11Y-1, NFR26-VISUAL-1) — TARGETED
// coverage of the mature viewer's always-mounted zoom toolbar.
//
// Deliberately narrow (story D-10). This spec owns exactly two captured states
// plus the assertions jsdom cannot make honestly:
//
//   1. the viewer open AT REST (scale 1.0) with the toolbar mounted
//   2. the viewer ZOOMED with the tap-to-hide chrome HIDDEN — mockup
//      `key-viewer-chrome.html` state C, "the load-bearing state"
//
// The FULL contract — Pixel 5 portrait AND landscape, panorama 4:1 and 8:1,
// portrait 1:4, small source, rotation refit, repeated open-close, error and
// slow-load, and the PHYSICAL Android Chrome smoke — belongs to Story 53.3
// (`epics.md:4579`) and is NOT pre-empted here.
//
// `tests/visual/image-viewer-containment.spec.ts` is a STANDING suite
// (`architecture.md:3376`) and is not touched by this story; it must stay green
// unmodified.
//
// playwright.config.ts forces `pl-PL`, so every matcher below is the literal
// pl.json string (`Powiększ` / `Pomniejsz` / `Dopasuj`). Per the Epic 45/46
// test-authoring rule, every `toHaveScreenshot` is preceded by an explicit
// `toBeVisible()` on the concrete state being captured.

import type { Page, Route } from "@playwright/test";

import { expect, test } from "./_test";
import { stubSotDetail } from "./api-stubs";
import { waitForReady } from "./helpers";

const MODEL_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

// `{spacing.target-fullscreen-close}` — DESIGN.md:180, :287; EXPERIENCE.md:302;
// WCAG 2.2 SC 2.5.8.
const CLOSE_TARGET_MIN_PX = 44;
// `{components.lightbox-zoom-control}` — DESIGN.md:176.
const ZOOM_CONTROL_MIN_PX = 40;
// Sub-pixel tolerance for device-scale-factor rounding on the Pixel 5 projects.
const EPSILON_PX = 0.5;

async function openViewer(page: Page) {
  // Two images, so the capture exercises the toolbar coexisting with the FULL
  // chrome layer (counter + chevrons) and the thumb strip — the three-layer
  // structure this story introduced. With the single-image default there would
  // be no strip and no counter to layer against.
  await stubSotDetail(page, { imageCount: 2 });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  // Layout only reflects the real intrinsic size once the source is decoded,
  // and the toolbar stays DISABLED until it resolves (D-6) — so waiting here is
  // what makes both the screenshots and the geometry assertions meaningful
  // rather than capturing a 0x0 placeholder behind a dimmed toolbar.
  await expect
    .poll(() =>
      page
        .getByTestId("image-viewer-frame")
        .locator("img")
        .evaluate((el: HTMLImageElement) => el.naturalWidth),
    )
    .toBeGreaterThan(0);
  await expect(zoomIn(page)).toBeEnabled();
  await waitForReady(page);
}

// The toolbar is scoped explicitly on every lookup. `catalog.image_viewer
// .zoom_in` is "Powiększ" in Polish and so is the SHIPPED
// `catalog.image_viewer.trigger_label` on the gallery trigger (story D-8's
// recorded terminology collision). 53.2 keeps the UX spine's viewer labels
// verbatim and does NOT rename the shipped trigger — that is raised for Story
// 54.1's cross-surface terminology audit. Scoping here is how this spec stays
// unambiguous in the meantime.
const toolbar = (page: Page) => page.getByTestId("image-viewer-toolbar");
const zoomIn = (page: Page) => toolbar(page).getByRole("button", { name: "Powiększ" });
const zoomOut = (page: Page) => toolbar(page).getByRole("button", { name: "Pomniejsz" });
const zoomReset = (page: Page) => toolbar(page).getByRole("button", { name: "Dopasuj" });

test("image viewer toolbar at rest matches baseline", async ({ page }) => {
  await openViewer(page);
  await expect(toolbar(page)).toBeVisible();
  await expect(zoomIn(page)).toBeVisible();
  await expect(zoomOut(page)).toBeVisible();
  await expect(zoomReset(page)).toBeVisible();
  // Mockup state A: at 1.0 the Zoom Out and Reset controls are
  // disabled-and-announced, not hidden.
  await expect(zoomOut(page)).toBeDisabled();
  await expect(zoomReset(page)).toBeDisabled();
  await expect(page).toHaveScreenshot("image-viewer-toolbar-rest.png");
});

test("image viewer toolbar stays visible when zoomed with chrome hidden", async ({ page }) => {
  await openViewer(page);
  await zoomIn(page).click();
  await zoomIn(page).click();

  // Tap the image to hide the chrome layer. This is the shipped
  // tap-to-toggle-chrome gesture; dispatching real touch events keeps it on
  // the same code path a phone takes.
  const frame = page.getByTestId("image-viewer-frame");
  const box = await frame.boundingBox();
  expect(box).not.toBeNull();
  const cx = (box?.x ?? 0) + (box?.width ?? 0) / 2;
  const cy = (box?.y ?? 0) + (box?.height ?? 0) / 2;
  // `TouchEvent`'s `touches` / `changedTouches` accept ONLY real `Touch`
  // instances — Chromium rejects plain object literals outright ("Failed to
  // convert value to 'Touch'"). `new Touch({...})` additionally requires
  // `identifier` and `target`. Constructing them properly is what keeps this on
  // the same code path a phone takes, instead of reaching past the shipped
  // gesture handler and calling React state directly.
  await page.evaluate(
    ([x, y]) => {
      const root = document.querySelector('[data-testid="image-viewer-root"]');
      if (root === null) return;
      const touch = new Touch({
        identifier: 1,
        target: root,
        clientX: x as number,
        clientY: y as number,
      });
      root.dispatchEvent(
        new TouchEvent("touchstart", {
          bubbles: true,
          touches: [touch],
          targetTouches: [touch],
          changedTouches: [touch],
        }),
      );
      root.dispatchEvent(
        new TouchEvent("touchend", {
          bubbles: true,
          touches: [],
          targetTouches: [],
          changedTouches: [touch],
        }),
      );
    },
    [cx, cy],
  );

  // Mockup state C — chrome hidden AND still zoomed, zoom controls still there.
  await expect(page.getByTestId("image-viewer-strip")).toHaveAttribute("aria-hidden", "true");
  await expect(toolbar(page)).toBeVisible();
  await expect(zoomOut(page)).toBeEnabled();
  await expect(zoomReset(page)).toBeEnabled();
  // The toolbar is never inside an aria-hidden subtree.
  expect(
    await toolbar(page).evaluate((el) => el.closest('[aria-hidden="true"]') !== null),
  ).toBe(false);
  await expect(page).toHaveScreenshot("image-viewer-toolbar-zoomed-chrome-hidden.png");
});

test("focus stays inside the toolbar when a control disables itself", async ({ page }) => {
  await openViewer(page);
  await zoomIn(page).focus();
  // Drive Zoom In to the ceiling from the keyboard. Chromium blurs a control
  // the instant it becomes `disabled`, and Base UI's focus manager does NOT
  // recover it (measured: `document.activeElement` became `<body>`), which
  // strands a keyboard / switch user outside the toolbar inside a focus-trapped
  // dialog. jsdom does not model that blur at all, so this is the only place the
  // repair can be honestly asserted.
  for (let i = 0; i < 20; i += 1) {
    if (await zoomIn(page).isDisabled()) break;
    await zoomIn(page).press("Enter");
  }
  await expect(zoomIn(page)).toBeDisabled();

  const active = await page.evaluate(
    () => document.activeElement?.getAttribute("data-testid") ?? "body",
  );
  expect(active).toBe("image-viewer-zoom-out");
});

test("close and zoom controls meet their target-size floors", async ({ page }) => {
  await openViewer(page);
  // jsdom has no layout, so this is the only place the 44x44 floor (AC-4) and
  // the 40px zoom-control size can actually be MEASURED.
  const close = await page.getByTestId("image-viewer-close").boundingBox();
  expect(close).not.toBeNull();
  expect(close?.width ?? 0).toBeGreaterThanOrEqual(CLOSE_TARGET_MIN_PX - EPSILON_PX);
  expect(close?.height ?? 0).toBeGreaterThanOrEqual(CLOSE_TARGET_MIN_PX - EPSILON_PX);

  for (const control of [zoomIn(page), zoomOut(page), zoomReset(page)]) {
    const box = await control.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(ZOOM_CONTROL_MIN_PX - EPSILON_PX);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(ZOOM_CONTROL_MIN_PX - EPSILON_PX);
  }
});

test("toolbar geometry is invariant across zoom levels (outside the transform layer)", async ({
  page,
}) => {
  await openViewer(page);
  const before = await toolbar(page).boundingBox();
  const closeBefore = await page.getByTestId("image-viewer-close").boundingBox();

  await zoomIn(page).click();
  await zoomIn(page).click();
  // The image really did scale...
  expect(
    await page
      .getByTestId("image-viewer-transform")
      .evaluate((el) => getComputedStyle(el).transform),
  ).not.toBe("none");

  // ...and the toolbar and close button did not move or resize by a pixel,
  // because they live outside the transform layer (AC-1, DESIGN.md § Elevation).
  const after = await toolbar(page).boundingBox();
  const closeAfter = await page.getByTestId("image-viewer-close").boundingBox();
  expect(after?.width).toBeCloseTo(before?.width ?? -1, 1);
  expect(after?.height).toBeCloseTo(before?.height ?? -1, 1);
  expect(after?.x).toBeCloseTo(before?.x ?? -1, 1);
  expect(after?.y).toBeCloseTo(before?.y ?? -1, 1);
  expect(closeAfter?.x).toBeCloseTo(closeBefore?.x ?? -1, 1);
  expect(closeAfter?.y).toBeCloseTo(closeBefore?.y ?? -1, 1);
});

// AC-6. Deliberately ELEMENT-AGNOSTIC. Story V-2 warns that Base UI's
// `useScrollLock` targets `<html>` OR `<body>` depending on which is the
// overflow element and on whether the platform uses overlay scrollbars — and
// measurement confirms it: in this Chromium it locks `<body>` (`overflow:
// hidden`) and leaves `<html>` untouched. Asserting one specific element would
// encode a platform detail and would make this test lie the moment the
// scrollbar mode changes. What is asserted instead is the contract
// `EXPERIENCE.md:234` actually states: scrolling is prevented while open, and
// the document is exactly as it was afterwards.
//
// `window.scrollTo` is NOT a valid probe here: `overflow: hidden` suppresses
// USER scrolling but still permits PROGRAMMATIC scrolling (only `overflow:
// clip` forbids it). A real wheel gesture is the honest test, so that is what
// runs below.

/** The overflow the viewport actually gets: `<html>` wins unless it is
 *  `visible`, in which case `<body>`'s value propagates to the viewport. */
async function effectiveViewportOverflow(page: Page): Promise<string> {
  return page.evaluate(() => {
    const html = getComputedStyle(document.documentElement).overflowY;
    return html === "visible" ? getComputedStyle(document.body).overflowY : html;
  });
}

/** Inline overflow overrides on both candidate elements, both axes. */
async function inlineOverflowState(page: Page) {
  return page.evaluate(() => ({
    htmlOverflow: document.documentElement.style.overflow,
    htmlOverflowY: document.documentElement.style.overflowY,
    bodyOverflow: document.body.style.overflow,
    bodyOverflowY: document.body.style.overflowY,
  }));
}

/** Scroll with a REAL wheel gesture and report where the page ended up. */
async function wheelAndReadScrollY(page: Page): Promise<number> {
  await page.mouse.move(200, 400);
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(200);
  return page.evaluate(() => window.scrollY);
}

test("body scroll is locked on open and fully restored on close", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // AC-6's stated pre-check: Base UI's `ScrollLocker.lock` bails out with a
  // NO-OP restore when the document is ALREADY overflow hidden/clip, which
  // would make every assertion below vacuously true. Prove that is not our
  // state.
  const overflowBefore = await effectiveViewportOverflow(page);
  expect(["hidden", "clip"]).not.toContain(overflowBefore);

  const inlineBefore = await inlineOverflowState(page);

  // Second no-op guard: prove the page is genuinely scrollable to begin with,
  // otherwise "scrolling was prevented" would prove nothing.
  expect(await wheelAndReadScrollY(page)).toBeGreaterThan(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });

  // Locked while open. This is Base UI's `Dialog.Root modal` default (V-2) —
  // Story 53.2 adds NO second lock; this test proves the SHIPPED one actually
  // engages on this surface, rather than covering a reimplementation.
  await expect.poll(() => effectiveViewportOverflow(page)).toBe("hidden");
  // ...and it is real prevention, not just a style: the same wheel gesture that
  // moved the page a moment ago now moves nothing.
  expect(await wheelAndReadScrollY(page)).toBe(0);

  await page.getByTestId("image-viewer-close").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "detached" });

  // Restored. The inline overflow overrides are byte-identical to the pre-open
  // state on BOTH candidate elements. The lock leaves an empty `style=""`
  // attribute behind on <body>; that is cosmetic residue and not an overflow
  // override, so comparing the overflow VALUES is simultaneously stricter about
  // what matters and immune to that.
  await expect.poll(() => inlineOverflowState(page)).toEqual(inlineBefore);
  expect(await effectiveViewportOverflow(page)).toBe(overflowBefore);
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  // ...and scrolling works again.
  expect(await wheelAndReadScrollY(page)).toBeGreaterThan(0);
});

// ══ Story 53.3 — AC-6, AC-7, AC-8 ═════════════════════════════════════════
// Everything below is NEW. The six tests above keep their bodies unchanged
// (AC-9); AC-7 extends the shipped scroll-lock test by REUSING its helpers
// rather than editing it, and the geometry half of this story lives in
// `image-viewer-containment.spec.ts` (D-3).

/**
 * Open the viewer with the main frame's `variant=full` request under this
 * test's control. `stubSotDetail` already serves a 1x1 PNG for every content
 * request; registering AFTER it wins, because Playwright matches route
 * handlers in reverse registration order, and `route.fallback()` hands the
 * non-`full` variants straight back to the shared stub so the gallery page and
 * the thumb strip behave normally.
 */
async function openViewerWithFullImage(
  page: Page,
  handleFull: (route: Route) => Promise<void> | void,
) {
  await stubSotDetail(page, { imageCount: 2 });
  await page.route("**/api/models/**/files/**/content**", async (route: Route) => {
    if (new URL(route.request().url()).searchParams.get("variant") !== "full") {
      return route.fallback();
    }
    return handleFull(route);
  });
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
}

// ── AC-6: focus trap / Escape / return focus ──────────────────────────────
// Escape had ZERO coverage anywhere before this story (V-9). The return-focus
// half is asserted HERE and not only in jsdom: Story 53.2 measured Base UI's
// focus manager behaving differently in real Chromium than in jsdom (a
// self-disabling control blurred to `<body>` in Chromium while jsdom modelled
// no blur at all), so a jsdom-only focus claim is not sufficient evidence for
// a focus contract.

test("Escape closes the viewer and returns focus to the gallery trigger", async ({ page }) => {
  await openViewer(page);
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();

  await page.keyboard.press("Escape");
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "detached" });
  await expect(page.getByTestId("gallery-fullscreen-trigger")).toBeFocused();

  // The close-button path carries the SAME contract (`EXPERIENCE.md:234`
  // states focus trap, Escape and return focus as one contract, not three).
  await page.getByTestId("gallery-fullscreen-trigger").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });
  await page.getByTestId("image-viewer-close").click();
  await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "detached" });
  await expect(page.getByTestId("gallery-fullscreen-trigger")).toBeFocused();
});

test("the open viewer takes focus and Tab walks its own controls", async ({ page }) => {
  await openViewer(page);
  // Base UI moves focus into the popup on open.
  await expect(page.getByTestId("image-viewer-close")).toBeFocused();

  // The dialog's OWN tab order reaches every ENABLED control. Zoom Out and
  // Reset are `disabled` at scale 1.0 (mockup state A) and are correctly
  // skipped rather than being focusable dead ends.
  // The two thumbs are disambiguated by `data-thumb-idx`: collapsing both to
  // the bare testid would let a regression that PINS focus on the first thumb
  // — exactly the class of focus bug this story is about — produce an
  // identical array and pass.
  const order: string[] = [];
  for (let i = 0; i < 5; i += 1) {
    await page.keyboard.press("Tab");
    order.push(
      await page.evaluate(() => {
        const el = document.activeElement;
        if (el === null) return "outside the viewer";
        const testid = el.getAttribute("data-testid");
        if (testid === null) return "outside the viewer";
        const idx = el.getAttribute("data-thumb-idx");
        return idx === null ? testid : `${testid}[${idx}]`;
      }),
    );
  }
  expect(order).toEqual([
    "image-viewer-prev",
    "image-viewer-next",
    "image-viewer-zoom-in",
    "image-viewer-thumb[0]",
    "image-viewer-thumb[1]",
  ]);

  // POINTER modality does hold, even though keyboard modality does not (see
  // the ledgered test below): the backdrop owns every hit-test over the page
  // behind, so nothing back there is clickable while the viewer is open.
  expect(
    await page.evaluate(
      () => document.elementFromPoint(5, 5)?.getAttribute("data-slot") ?? "none",
    ),
  ).toBe("dialog-overlay");
});

// AC-6's focus-TRAP clause — the one clause of this story that could NOT be
// satisfied, recorded as an executable expected-failure rather than deleted.
//
// MEASURED this run in real Chromium, on all four projects, in BOTH
// directions, so it is not a document-end wrap artifact of headless Tab:
//   - `Shift+Tab` from the initially-focused close button lands straight on
//     the page BEHIND the dialog (the file row's delete button, the download
//     link, the 3D-preview toggle, the render checkbox);
//   - `Tab` past the last thumb reaches a Base UI focus guard and then the
//     header links and the theme toggle;
//   - `#root` carries NEITHER `inert` NOR `aria-hidden` while the dialog is
//     open, so the background is traversable by a screen reader too.
// The scroll lock and the pointer backdrop DO engage, so `modal` is on; it is
// specifically the focus/AT-hiding half that is absent.
//
// The defect is in the shared `ui/dialog.tsx` + `@base-ui/react` 1.4.1 modal
// wiring, NOT in this viewer — the viewer passes no prop that could disable
// it, and the blast radius is EVERY dialog in the app. `ui/dialog.tsx` is § 5
// "Never" for Story 53.3 (`architecture.md:3375`), so the repair is not this
// story's to make; it is ledgered in `deferred-work.md`.
//
// `test.fail()` rather than a deleted test: this is the CORRECT contract,
// kept executable. The day the modal wiring is fixed, Playwright reports
// "expected to fail but passed" and forces the ledger entry to be closed.
test("focus never leaves the open viewer in either Tab direction", async ({ page }) => {
  // The fixture runs BEFORE `test.fail()` is declared, on purpose. Playwright
  // absorbs any throw in an expected-failure test, so declaring it up front
  // would also absorb a broken stub, a renamed trigger or a viewer that never
  // mounts — and the pin would silently stop asserting anything about focus
  // while still reporting green. Only the focus assertions below are allowed
  // to be the expected failure.
  await openViewer(page);
  await expect(page.getByTestId("image-viewer-root")).toBeVisible();
  test.fail(
    true,
    "focus trap absent in the shared modal wiring; out of Story 53.3's blast radius (deferred-work.md)",
  );
  const insideDialog = () =>
    page.evaluate(
      () => document.querySelector('[role="dialog"]')?.contains(document.activeElement) ?? false,
    );

  // Both directions are COLLECTED first and asserted once at the end. Asserting
  // inside the loop would throw on the very first escape — which the record
  // says is `Shift+Tab` #1 — so the `Tab` half would never execute at all for
  // as long as the defect exists, despite the comment block above claiming
  // both directions are pinned. Collecting keeps the claim true and makes the
  // eventual "expected to fail but passed" cover both directions.
  const escapes: string[] = [];
  for (const key of ["Shift+Tab", "Tab"] as const) {
    await page.getByTestId("image-viewer-close").focus();
    // More presses than the dialog has focusable controls, so the cycle has
    // to wrap: a trap that only holds for the first pass is not a trap.
    for (let i = 0; i < 10; i += 1) {
      await page.keyboard.press(key);
      if (!(await insideDialog())) escapes.push(`${key} #${i + 1}`);
    }
  }
  expect(escapes, `focus escaped the dialog on: ${escapes.join(", ")}`).toEqual([]);
});

// ── AC-7: body-scroll restoration across REPEATED open-close ──────────────

test("body scroll is fully restored after repeated open-close cycles", async ({ page }) => {
  await stubSotDetail(page);
  await page.goto(`/catalog/${MODEL_ID}`);
  await waitForReady(page);

  // The same two no-op guards the single-cycle test states, for the same
  // reasons: `ScrollLocker.lock` bails out with a NO-OP restore when the
  // document is already overflow hidden/clip, and "scrolling was prevented"
  // proves nothing on a page that was never scrollable.
  const overflowBefore = await effectiveViewportOverflow(page);
  expect(["hidden", "clip"]).not.toContain(overflowBefore);
  const inlineBefore = await inlineOverflowState(page);
  expect(await wheelAndReadScrollY(page)).toBeGreaterThan(0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

  // Base UI's `useScrollLock` is REF-COUNTED, so an unbalanced
  // acquire/release is invisible on a single cycle and only surfaces after
  // several — which is exactly what `epics.md:4579`'s "repeated open-close"
  // is asking to be pinned.
  for (let cycle = 1; cycle <= 3; cycle += 1) {
    await page.getByTestId("gallery-fullscreen-trigger").click();
    await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "visible" });

    await expect
      .poll(() => effectiveViewportOverflow(page), { message: `cycle ${cycle}: locked while open` })
      .toBe("hidden");
    expect(await wheelAndReadScrollY(page), `cycle ${cycle}: wheel really suppressed`).toBe(0);

    await page.getByTestId("image-viewer-close").click();
    await page.waitForSelector('[data-testid="image-viewer-root"]', { state: "detached" });

    await expect
      .poll(() => inlineOverflowState(page), {
        message: `cycle ${cycle}: inline overflow overrides restored`,
      })
      .toEqual(inlineBefore);
    expect(
      await effectiveViewportOverflow(page),
      `cycle ${cycle}: effective viewport overflow restored`,
    ).toBe(overflowBefore);
    expect(
      await page.evaluate(() => window.scrollY),
      `cycle ${cycle}: scroll position unchanged`,
    ).toBe(0);
    expect(
      await wheelAndReadScrollY(page),
      `cycle ${cycle}: a real wheel gesture scrolls the page again`,
    ).toBeGreaterThan(0);
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  }
});

// ── AC-8: slow load and image error ───────────────────────────────────────
// Mockup states D and E. The THIRD failure path in AC-8 — a `renderImage`
// that never mounts an `<img>` at all — is deliberately NOT here: no visual
// spec has ever opened the viewer from `/share` (V-21), and reproducing it
// would mean building a whole share harness for one assertion. It is a
// property of the component's prop boundary and is asserted in
// `ImageFullscreenViewer.test.tsx` with fake timers instead.

test("slow load keeps the zoom controls mounted, disabled and ANNOUNCED", async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  // Everything that can throw runs inside `try` so the gated route handler is
  // ALWAYS resolved — INCLUDING `openViewerWithFullImage`, because a renamed
  // testid or stub drift breaks the OPEN sequence, not the assertions. Left
  // unresolved, `page.route`'s handler is stranded mid-flight and the real
  // message is buried under a teardown error, on all four projects at once.
  //
  // This block is NO LONGER bounded by `IMAGE_READY_TIMEOUT_MS` (15 s). It was
  // while the readiness watchdog armed on the ordinary `<img>` path too — the
  // gate outrunning the timer would have flipped `imageStatus` to `error`
  // under the assertions. DN-2 narrowed the arm site to the never-mounted-
  // `<img>` branch, so a mounted-but-slow image now stays `loading` for as
  // long as it takes, which is precisely the semantics this test asserts.
  try {
    await openViewerWithFullImage(page, async (route) => {
      await gate;
      await route.fallback();
    });

    // Mockup state D: mounted but disabled...
    await expect(toolbar(page)).toBeVisible();
    for (const control of [zoomIn(page), zoomOut(page), zoomReset(page)]) {
      await expect(control).toBeDisabled();
    }
    // ...and the disabled state is ANNOUNCED, not merely dimmed
    // (`EXPERIENCE.md:259`). Read the live region's TEXT rather than its
    // visibility: it is `sr-only` until actually zoomed BY DESIGN (V-16), so a
    // `toBeVisible()` here would fail correctly and prove the wrong thing.
    await expect(page.getByTestId("image-viewer-zoom-level")).toHaveText(
      "Wczytywanie pełnego obrazu…",
    );
    // Close stays live throughout — a slow image never traps the user either.
    await expect(page.getByTestId("image-viewer-close")).toBeEnabled();

    // No baseline for state D (D-8): visually it is the existing rest state
    // with the three controls disabled, which `image-viewer-toolbar-rest-*`
    // already captures.
  } finally {
    release();
  }
  await expect(zoomIn(page)).toBeEnabled();
  await expect(page.getByTestId("image-viewer-zoom-level")).toBeEmpty();
});

test("a failed image renders the inline error and never traps the user", async ({ page }) => {
  await openViewerWithFullImage(page, (route) =>
    route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }),
  );

  const error = page.getByTestId("image-viewer-error");
  await expect(error).toBeVisible();
  // The copy is the UX spine's Polish, transcribed from mockup state E
  // rather than translated; `playwright.config.ts` forces `pl-PL`.
  await expect(error).toHaveText("Nie udało się wczytać zdjęcia.");
  // The live region announces the failure instead of falling through to "".
  await expect(page.getByTestId("image-viewer-zoom-level")).toHaveText(
    "Nie udało się wczytać zdjęcia.",
  );

  // The error paints inside the frame but outside the transform layer.
  expect(
    await error.evaluate(
      (el) => document.querySelector('[data-testid="image-viewer-transform"]')?.contains(el) ?? true,
    ),
  ).toBe(false);

  // Close, chevrons, strip, counter and toolbar all stay reachable...
  await expect(toolbar(page)).toBeVisible();
  for (const control of [zoomIn(page), zoomOut(page), zoomReset(page)]) {
    await expect(control).toBeDisabled();
  }
  await expect(page.getByTestId("image-viewer-strip")).toBeVisible();
  await expect(page.getByTestId("image-viewer-counter")).toBeVisible();
  await expect(page.getByTestId("image-viewer-close")).toBeEnabled();

  // ...and OPERABLE, not merely present: the error overlay is
  // `pointer-events-none`, so a chevron underneath it still takes the click.
  await page.getByTestId("image-viewer-next").click();
  await expect(page.getByTestId("image-viewer-counter")).toHaveText("2 / 2");
  await page.getByTestId("image-viewer-close").click();
  await expect(page.getByTestId("image-viewer-root")).toHaveCount(0);
});

test("image viewer inline error state matches baseline", async ({ page }) => {
  // D-8 — the ONE new visual state this story captures, because it is new
  // pixels no baseline covers. Four PNGs, one per fixed project.
  await openViewerWithFullImage(page, (route) =>
    route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }),
  );
  // Epic 45/46 rule: an explicit `toBeVisible()` on the concrete state before
  // every `toHaveScreenshot`.
  await expect(page.getByTestId("image-viewer-error")).toBeVisible();
  await expect(page.getByTestId("image-viewer-error")).toHaveText(
    "Nie udało się wczytać zdjęcia.",
  );
  await expect(toolbar(page)).toBeVisible();
  await expect(zoomIn(page)).toBeDisabled();
  await expect(page).toHaveScreenshot("image-viewer-error.png");
});
