---
title: 'E48.1 — Mobile fullscreen image viewer containment + reachable close'
type: 'bugfix'
created: '2026-07-26'
status: 'done'
review_loop_iteration: 2
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On a phone, opening a catalog image in the fullscreen viewer can render the dialog shifted to the right: only the left part is visible, the layout extends past the right edge of the visual viewport, and the top-right close button lands outside it — the user is trapped with no exit affordance.

**Approach:** Make `ImageFullscreenViewer`'s Dialog geometry self-contained in *viewport* units anchored to the viewport origin, instead of relying on percentage-of-containing-block centering, which silently mis-centers whenever mobile Chrome's layout viewport is wider or taller than the visual viewport. Pure CSS on the one component; no gestures, no dependency.

## Boundaries & Constraints

**Always:** the complete image fits the main frame at initial scale for portrait / landscape / extreme-wide sources; the close control stays inside the visual viewport and is clickable; both mounts (`/catalog/$modelId` via `ModelGallery`, `/share/$token` via `ShareCarousel`) keep their existing `renderImage` / `renderThumb` auth boundaries untouched; no horizontal page overflow introduced; rendering on a non-overflowing viewport stays pixel-identical to today.

**Ask First:** any change to the shared `apps/web/src/ui/dialog.tsx` primitive (blast radius = every dialog in the app); any change to the mobile `ModuleRail` nav.

**Never:** pinch-to-zoom, pan, or swipe-down-to-close (Initiative 26 research); new lightbox / gesture dependency; suppressing browser pinch-zoom via `user-scalable=no` (a11y); touching Initiative 26 taxonomy/search planning.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Extreme-wide source | 6000×1200 PNG, Pixel 5 viewport | dialog, viewer root and close button inside the viewport; `<img>` box inside the main frame | N/A |
| Extreme-portrait source | 1200×6000 PNG, Pixel 5 viewport | same containment; image height capped by the main frame | N/A |
| Page overflows horizontally | any source + document scroll width > visual viewport width (mobile layout viewport expands) | dialog stays anchored at `1vw` from the visual viewport's left edge; close button reachable and closes the viewer | N/A |
| Non-overflowing viewport | desktop 1280×720, mobile 393×727 | geometry identical to the pre-fix centered layout (no visual baseline delta) | N/A |

</frozen-after-approval>

## Code Map

- `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` -- the only file with the defect; `DialogContent` className carries the geometry, the main-frame div carries `min-h-0` + the image `max-h`.
- `apps/web/src/ui/dialog.tsx` -- shared primitive supplying `fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2` (read-only here; overridden per-instance via `cn`/`twMerge`).
- `apps/web/tests/visual/image-viewer-containment.spec.ts` -- NEW geometry regression spec (bounding boxes, not snapshots).
- `apps/web/tests/visual/api-stubs.ts` -- `stubSotDetail` serves a 1×1 PNG, which is why no existing spec could reproduce an intrinsic-size-driven layout bug.
- `apps/web/src/modules/catalog/components/ModelGallery.tsx`, `apps/web/src/routes/share/$token.tsx` -- the two mounts; unchanged, but both inherit the fix.

## Tasks & Acceptance

**Execution:**
- [x] `apps/web/tests/visual/image-viewer-containment.spec.ts` -- add geometry regressions with synthetic extreme-wide/extreme-tall PNGs, a real two-image strip, and a viewport-relative forced-overflow case that proves overflow exists on every project.
- [x] `apps/web/tests/visual/api-stubs.ts` -- add an opt-in two-image detail fixture; default callers remain byte-for-byte unchanged.
- [x] `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` -- add `data-testid="image-viewer-frame"` to the main-frame div -- the "image inside the main frame" assertion needs a stable handle.
- [x] `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` -- replace inherited centering with viewport-anchored geometry, cap width against the containing block for classic-scrollbar safety, and move the height budget from `vh` to `dvh`.
- [x] `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/catalog-detail-image-viewer-open-mobile-{light,dark}.png` -- regenerate the two mobile baselines -- `left: 50%` of 393px resolved to 3.9375px, `left: 1vw` resolves to 3.93px; the 0.0075px delta re-rasterises the close-button glyph.

**Acceptance Criteria:**
- Given the document's scroll width exceeds the visual viewport width, when the fullscreen viewer opens, then the dialog's right edge stays within the visual viewport and the close button is visible, clickable, and dismisses the viewer.
- Given any of the source aspect ratios in the matrix, when the viewer opens, then the rendered `<img>` bounding box lies inside the main-frame bounding box at initial scale (no cropping, no pan required).
- Given a viewport that does not overflow, when the viewer opens, then the layout is geometrically identical to the pre-fix centered layout; the only permitted baseline delta is sub-pixel re-rasterisation, inspected per PNG before regeneration.

## Spec Change Log

- **2026-07-26 — planning claim corrected against the measured result.** The pre-implementation AC asserted *"all four visual baselines … remain unchanged"*. Actual: `desktop-light` / `desktop-dark` are byte-identical, `mobile-light` (32 px) and `mobile-dark` (19 px) changed. Both diff PNGs were inspected: the delta is confined to the close-button `X` glyph — dialog edges, image box and thumb strip unmodified. Cause is a 0.0075 px offset (`left: 50%` of 393 px = 3.9375 px → `left: 1vw` = 3.93 px) crossing an antialiasing boundary. AC amended to the honest invariant. Known-bad state avoided: blanket-regenerating four baselines and reporting "no visual delta".
- **2026-07-26 — operator's stated hypothesis recorded as disproved, not silently dropped.** Intent named missing `min-w-0` across the Dialog grid / nested flex as the likely cause. Measured refutation is in Design Notes; no `min-w-0` was added, because adding a provably inert class would misrepresent the fix. KEEP: the regression spec exercises the intrinsic-size path anyway, so the invariant is locked even though the class is absent.

## Design Notes

Measured root cause (Pixel-5-class emulation, viewport 280 CSS px, `/catalog/<id>`):

```
document.documentElement.clientWidth  280   visualViewport.width 280   100vw = 280px
window.innerWidth                     335   fixed-position ICB   335   (layout viewport, expanded by page overflow)
dialog computed: left 167.5px (= 50% of 335), width 274.391px (= 98vw of 280), translate -50% -50%
dialog rect [30.3 .. 304.7]   close rect [252.7 .. 292.7]   → 12.7px of the close button outside the viewport
```

`left: 50%` resolves against the **layout viewport** while `w-[98vw]` resolves against the **visual viewport**. The centering formula `left-1/2 + -translate-x-1/2` is only correct while the two are equal; mobile Chrome expands the layout viewport as soon as the document overflows horizontally, and the dialog is displaced right by `(ICB − 100vw) / 2`. Anchoring with `left-[1vw]` + `translate-x-0` expresses both the offset and the size in the same unit, so the geometry can no longer drift; on a non-overflowing viewport `1vw` is exactly the margin the centered layout produced, so there is no visual delta.

The controller's original hypothesis — missing `min-w-0` on the Dialog grid / nested flex items letting the image's intrinsic width blow up the grid track — was **tested and disproved**: with a 6000×1200 source at Pixel 5, `grid-template-columns` computes to `385.125px`, because the main frame is `overflow-hidden` (min-content contribution 0) and the thumb strip is `overflow-x-auto`. No `min-w-0` is added; the regression spec locks the intrinsic-size path so a future change to those overflow properties fails loudly.

Height moves `vh → dvh` for the same class of reason: on a phone `vh` is the *large* viewport (browser toolbar hidden), so `h-[95vh]` overshoots the currently visible area whenever the toolbar is showing. `dvh` tracks the visible area. Not observable in headless Chromium (`dvh === vh` there) — reasoned, not test-covered.

Safe-area insets are deliberately **not** handled: `index.html` uses the default `viewport-fit=auto` (no `viewport-fit=cover`), so the browser already keeps the layout viewport inside the safe area.

Residual risk is explicitly deferred to Initiative 26: `Viewer3DModal` and other shared `DialogContent` consumers may exhibit the same mixed-reference-box pattern, while the full image viewer still lacks pinch/pan and physical-Android dynamic-toolbar evidence. This quickfix intentionally changes only the reported image lightbox consumer.

## Verification

**Commands** (all run from `apps/web/`; recorded results are actual, not expected):

| Command | Result |
|---|---|
| `npx playwright test --config=tests/visual/playwright.config.ts tests/visual/image-viewer-containment.spec.ts` — CSS reverted, `data-testid` kept | **10 passed / 2 failed** — `mobile-light` + `mobile-dark` "stays reachable when the page overflows horizontally"; dialog right edge `642.56` vs viewport `393`. Desktop projects pass (`isMobile: false` → no layout-viewport expansion). |
| same command, final fix + review regressions applied | **14 passed / 2 documented mobile skips / 0 failed** (4 tests × 4 projects; actual-root-scroll case runs where Chromium permits `scrollX`) |
| `npm run typecheck` | clean (`tsc -b`, no output) |
| `npm run lint` | `ESLint: No issues found` (`--max-warnings=0`) |
| `npm run test` | **785 passed / 785**, 136 files |
| `npx playwright test … catalog-detail.spec.ts` ×3, 4 projects | the 2 viewer baselines fail in all 3 runs → deterministic, mine; `catalog-detail-member` (desktop-dark) never reproduced → flake-candidate, not attributable to this diff |
| `npm run test:visual` | **536 passed / 32 expected skips / 0 failed** |
| `infra/scripts/check-all.sh` | **16 / 16 stages passed; all green** |

**Baseline triage** (repo rule: classify before `--update-snapshots`, never blanket-regen):

- `catalog-detail-image-viewer-open-mobile-light.png` + `-mobile-dark.png` — **intended sub-pixel rasterization change**. Laura inspected old/new/8× RGB diff composites: dialog/image/control box geometry is unchanged, all edges and close remain visible, and differences are confined to fractional edge/glyph rasterization. No clipping or layout regression.
- All other full-suite failures — **not attributable to this diff**: with the CSS change stashed out, the same specs failed on a *different* set of tests/projects. Preserved as pre-existing environmental drift, deliberately not repaired here (out of scope for a one-component quickfix).

**Review loop:** native BMAD review verified the measured root cause and requested stronger forced-overflow, real two-image-strip, classic-scrollbar-cap, and test-maintainability coverage. Those findings were resolved. Final repo-aware independent Aider review and a fresh final native BMAD re-review both inspected the actual component/spec/tests and returned **APPROVE**.

**Manual checks (if no CLI):**
- `dvh` behaviour is not observable headless (`dvh === vh` with no dynamic browser toolbar). Requires operator hands-on verification on a real phone with the toolbar visible.
