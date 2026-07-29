---
baseline_commit: a3aaf35b81e269631cfa4d26ddc178c18abafb77
---

# Story 53.2 — Mature viewer implementation (FR26-VIEW-1, NFR26-A11Y-1, NFR26-I18N-1, NFR26-DARKMODE-1, NFR26-VISUAL-1)

Status: done

<!-- Closed 2026-07-29 by Laura/controller after native BMAD review findings were repaired, independent Aider review APPROVED the repaired text diff, full `infra/scripts/check-all.sh` reran green after the repairs, and the commit message carries `baseline-reviewed:` sign-off lines for all 12 changed/added PNG baselines. `G26-LIB` remains OPEN; no physical Android Chrome evidence was collected. -->


<!-- Created 2026-07-29 by native `bmad-create-story` (Create action) at `main` @ `a3aaf35`. -->
<!-- Validated 2026-07-29 by native `bmad-create-story` (Validate action / checklist pass) at the same commit. See the Change Log for the repairs applied. -->

- **Epic:** E53 — Mature mobile lightbox (Initiative 26 — Catalog Discovery). Independent parallel track; depends on nothing in E49–E52 (`epics.md:4567`).
- **Author:** Claude Opus 5, native `bmad-create-story`, repo-local. **NOT** an Ezop signature and **NOT** human review.
- **Created:** 2026-07-29 at `main` @ `a3aaf35` (clean tree, `origin/main` in sync), directly after Story 53.1's closeout.
- **Authorization posture:** planning artifact only. `G26-DEVGO` for *creating and validating this file* was granted by Laura/controller under Ezop's standing Initiative 26 delegation. **That is not an Ezop signature and not human review, and it is not authorization to start dev.** See the entry-gate block below.

---

## 0. ⛔ ENTRY GATE — read before `bmad-dev-story`

> **`G26-LIB` IS OPEN.** `implementation-readiness-report-2026-07-26.md:205` closes it on *"53.1 recommendation **plus** physical Android evidence"*. Story 53.1 delivered the first conjunct and the instrument for the second; **the physical Android Chrome evidence has NOT been collected** (`spec-e53-1-lightbox-adoption-recommendation.md:301-351` — every result cell in § 7.3 is blank). `epics.md:4567` gates this whole epic on `G26-LIB`.

**What that means, precisely:**

| | |
|---|---|
| Is this story **creatable and validatable** with the gate open? | **Yes.** `architecture.md:3386` records `G26-DEVGO` as *"planning proceeds; code starts only after create+validate and controller confirmation of that specific ready story"*. Create+validate **is** the planning step the gate register expects to happen first. Native `bmad-create-story` has no gate-check step and did not protest. |
| Is this story **implementable** with the gate open? | **No — not without an explicit controller act.** The chosen option is **PROVISIONAL** (`spec-e53-1:3-4, :384`). Reversal triggers **R1, R2, R3, R5** (`spec-e53-1:400-404`) each flip the call to option 1 (YARL), and each would invalidate most of § 6 below. |
| What unblocks dev? | Either (a) the operator collects `spec-e53-1` § 7.3 and closes `G26-LIB`, or (b) the controller explicitly accepts the provisional option-3 call and records that acceptance. **This story does not grant either.** |
| What must NOT happen | Do not close `G26-LIB` from this story. Do not record a Decision BA outcome in `architecture.md` (that routes through `bmad-correct-course`). Do not assert, simulate or infer physical-Android gesture quality (`epics.md:4579`). |

**`ready-for-dev` here is the BMAD artifact status, not a green light.** It means the context packet is complete; the gate above still stands in front of `bmad-dev-story`.

**Which option this story is written against:** **Option 3 — extend the in-house `ImageFullscreenViewer`** (`spec-e53-1:380`, PROVISIONAL). If a reversal trigger fires, `spec-e53-1:433-441` is the alternative task list and this story must be re-created via `bmad-correct-course`, not patched in place.

---

## 1. Story statement

**As** a member inspecting a detailed or panoramic model photo on a phone,
**I want** to pinch, pan and double-tap the image — and to reach every one of those states with visible single-pointer controls instead — inside a viewer that traps focus, restores my scroll position, and never pushes its own close button off-screen,
**so that** `FR26-VIEW-1` is satisfied for touch **and** for keyboard/assistive users, without regressing anything Story 48.1 established.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `a3aaf35`

Every row was read this run. **Four rows correct claims carried in `spec-e53-1`.** Those corrections are the highest-value content in this file: acting on the uncorrected claims would mean building something that already ships, or reaching for an API this repo does not use.

| # | Fact | Evidence at `a3aaf35` | Consequence for 53.2 |
|---|---|---|---|
| **V-1** | 🛑 **The dialog primitive is `@base-ui/react`, NOT Radix.** | `apps/web/src/ui/dialog.tsx:4` — `import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"`. `grep -rn "@radix-ui" apps/web/src` returns **zero** hits. `package.json` still declares `@radix-ui/react-dialog ^1.1.2`, `-dropdown-menu`, `-tabs`, `-tooltip` — **all four are unimported legacy**. Installed `@base-ui/react` is **1.4.1**. | `spec-e53-1:255-259, :273-275, :290, :140` attribute the viewer's modal semantics, focus trap, return focus and Escape to Radix, and price option 3 on `@radix-ui/react-dialog` being "paid for app-wide". **The behaviours are real; the attribution is wrong.** The *conclusion* (option 3 adds 0 dependency bytes) survives — `@base-ui/react` is app-wide instead. **Do not reach for a Radix API.** The escape hatches available are Base UI's: `modal` on `Dialog.Root` (`DialogRoot.js:26`, default `true`), `initialFocus` / `finalFocus` on `Dialog.Popup` (`DialogPopup.js:34-35, :104-110`, where `returnFocus: finalFocus`). Removing the dead `@radix-ui/*` deps is **out of scope** — separate chore, not this story's diff. |
| **V-2** | 🛑 **Body scroll lock with restoration ALREADY SHIPS. Do not build it.** | `@base-ui/react/esm/dialog/root/useDialogRoot.js:86` — `useScrollLock(open && modal === true, popupElement)`; `modal` defaults `true` (`DialogRoot.js:26`) and the viewer does not override it (`ImageFullscreenViewer.tsx:225`). `@base-ui/utils/useScrollLock.js` implements a ref-counted `ScrollLocker`: on mobile Chrome / overlay-scrollbar platforms it takes `preventScrollOverlayScrollbars`, which sets `overflowY`/`overflowX: hidden` on `<html>` (or `<body>` when `<html>` is the overflow element) and **restores the original inline styles on release**; the inset-scrollbar path additionally saves and restores `scrollTop`/`scrollLeft`. It sets **no** `touch-action`, so it does not suppress browser pinch-zoom. | `spec-e53-1:151` budgets *"body scroll lock with restoration — no — 25–40 LOC"*. That is a **wheel-reinvention trap**: hand-rolling a second lock on top of Base UI's would double-apply `overflow:hidden` and fight its restore path. **53.2's obligation is to VERIFY AND ASSERT, not to build** (AC-6). One real caveat to assert rather than assume: `ScrollLocker.lock` bails out with `restore = NOOP` when `<html>`'s computed `overflow-y` is already `hidden`/`clip` — prove that is not our state. |
| **V-3** | 🛑 **`env(safe-area-inset-*)` resolves to 0 today, and fixing that is app-wide.** | `apps/web/index.html:5` — `<meta name="viewport" content="width=device-width, initial-scale=1.0" />`. **No `viewport-fit=cover`.** `grep -rn "safe-area\|env(safe" apps/web/src` returns **zero** hits — the codebase has never used a safe-area inset. | Per spec, `env(safe-area-inset-*)` is `0` unless the viewport meta opts into `viewport-fit=cover`. Adding it changes layout on **every route** (notably the mobile bottom `ModuleRail`, which `EXPERIENCE.md:334` freezes). **That meta change is Ask First and OUT of this story's scope.** D-5 resolves how 53.2 satisfies "safe-area handling" anyway. |
| **V-4** | 🛑 **`catalog.image_viewer.loading` is an orphan key.** | Defined at `en.json:396` / `pl.json:396`, referenced **nowhere** in `apps/web/src`. `EXPERIENCE.md:259` calls it *"Existing `catalog.image_viewer.loading` treatment"* — there is no treatment. | The UX spine assumes a shipped loading affordance that does not exist. Do not treat `:259` as "already satisfied". D-6 scopes what 53.2 owns of it and what stays with 53.3 / the renderers. |
| **V-5** | **The UX spine is closed, binding, and already specifies this viewer in detail.** | `G26-UXGATE` **closed** 2026-07-26 by commit `48db6bb` (`epics.md:4547`). `DESIGN.md:168-181` (`lightbox-toolbar`, `lightbox-zoom-control` **40px** circular, `lightbox-close` = `{spacing.target-fullscreen-close}` **44px**), `:246`, `:285-287`, `:299`; `EXPERIENCE.md:234, :259-262, :269-274, :282, :291, :302, :318, :337`; mockup `mockups/key-viewer-chrome.html` (five states, library-agnostic). `DESIGN.md:264` — *"The spines win on conflict."* | `spec-e53-1` never cites this artifact. It is **more prescriptive than the epic sketch** and it wins. Most importantly (`EXPERIENCE.md:234`, `DESIGN.md:286, :299`): **the zoom toolbar is ALWAYS MOUNTED and is never part of the tap-to-hide chrome layer.** `spec-e53-1:422` only says "outside the toolbar's render subtree", which is weaker. See D-2. |
| **V-6** | **The existing chrome layer is exactly what the toolbar must NOT join.** | `ImageFullscreenViewer.tsx:299-305` — a single `absolute inset-0` div whose opacity follows `chromeVisible` and which sets `aria-hidden={!chromeVisible}`. Counter (`:306-316`), close (`:318-326`), prev/next (`:328-349`) all live inside it. The strip (`:353-372`) fades and goes `pointer-events-none` in the same state. | The zoom toolbar is a **third** layer: outside the transform layer *and* outside this chrome layer. State C of the mockup (`key-viewer-chrome.html:109`) is named *"the load-bearing state"* precisely because it is chrome-hidden **and** zoomed with the zoom controls still visible. |
| **V-7** | **The close target is 40×40 and must become ≥44×44.** | `:323` — `h-10 w-10` (40px). Prev/next are `h-12 w-12` = 48 (`:335`, `:344`) and already compliant. | One-line change to `h-11 w-11` (44) or `h-12 w-12` (48). `DESIGN.md:287` says *"Larger than every other control on the surface, deliberately"* — the zoom controls are 40px, so **44 or 48 both satisfy that**; pick 48 only if the visual diff is acceptable. Asserted at AC-4. |
| **V-8** | **Nothing zoom-related exists yet.** | `:20-21` — *"pinch-to-zoom — DEFERRED"*, *"swipe-down-to-close — DEFERRED"*. No transform state, no scale, no pan offset, no zoom control, no `+`/`-`/`0` key handling (`onKey` at `:128-143` handles only `ArrowLeft`/`ArrowRight`). | Everything in AC-1…AC-3 is net-new. |
| **V-9** | **The shipped gesture layer is hardened across three Codex rounds and must be EXTENDED, not replaced.** | `:43-48` — `SWIPE_THRESHOLD_PX = 50`, `SWIPE_VERTICAL_TOLERANCE_PX = 60`. `:145-177` `onTouchStart` (coords-based `stripOrigin`; narrow target-based `thumbOrigin`). `:179-216` `onTouchEnd` (vertical-drift bail, short-tap chrome toggle with thumb deferral, strip-origin navigate suppression, then swipe). Provenance: 22.3 r3, 28.2, 28.2 r3 — `triage-backlog.md` TB-043. | `EXPERIENCE.md:270` re-states these exact constants normatively (*"existing 50 px threshold, 60 px vertical tolerance, strip-origin drags never navigate"*). **Changing either constant is a deliberate, justified decision, never a side effect** (`spec-e53-1:423`). The four-cell gesture-state matrix (visible/hidden × tap/drag) that TB-043 closed must still hold at scale 1.0. |
| **V-10** | **The 48.1 geometry lives in one className string and stays verbatim.** | `:260` — `h-[95dvh] w-[98vw] max-w-[calc(100%-2vw)] left-[1vw] top-[2.5dvh] translate-x-0 translate-y-0 p-0 …`, rationale at `:228-259`. Image cap at `:294` — `max-h-[calc(95dvh-5rem)]` (95dvh − the `h-20` strip). | `architecture.md:3371-3376`, restated `spec-e53-1:410-416`. **Never** `left-1/2` + `-translate-x-1/2`; **never** `vh`; **never** `user-scalable=no`. If the always-mounted toolbar changes the vertical budget, `:294`'s arithmetic must be re-derived, not left stale. |
| **V-11** | **Three test surfaces consume the viewer's DOM; all three survive option 3 by construction.** | (a) `tests/visual/image-viewer-containment.spec.ts` — geometry assertions, no snapshots; queries **eight** testids (`:134, :140, :202, :209-213`). (b) `tests/visual/catalog-detail.spec.ts:48-58` — one screenshot name × the fixed 4-project matrix ⇒ **four** baselines `catalog-detail-image-viewer-open-{desktop,mobile}-{light,dark}.png` (all four present on disk). (c) `imageViewer/ImageFullscreenViewer.test.tsx` — 138 lines, 5 `it` blocks. | (a) is a **standing** suite (`architecture.md:3376`) that must stay green with **zero edits** — it is 53.3's to extend, not 53.2's to touch. (c) is **extended**, never rewritten. (b): all **four** baselines regenerate (the toolbar is new pixels in every project), each needing its own `baseline-reviewed:` line. |
| **V-12** | **The auth boundary is a prop, and it is untouchable.** | `types.ts:23-27` (`ImageRenderer`), `:62-68` (props). `/catalog`: `ModelGallery.tsx:209-216` mount, plain `<img>` renderer. `/share`: `$token.tsx:371-387` mount, `renderImage={AnonymousImage}` (`:377`, declared `:120`), `renderThumb={LazyAnonymousImage}` (`:385`, declared `:174`). | **Never** modify these, their call sites, `shareBlobCache`, or the `credentials:"omit"` / `IntersectionObserver` behaviour (NFR10-SHARE-SECURITY-1 + the 60 req/min `(token, IP)` cap from Init 12 Story 19.1). The transform layer wraps **whatever the renderer returns**; it never inspects or replaces it. |
| **V-13** | **`ImageSource` carries no pixel dimensions.** | `types.ts:35-39` — `{ fullUrl, thumbUrl, alt }`. | Max-zoom cannot be derived from intrinsic size via the props. It must come from the **rendered** `<img>`'s `naturalWidth`/`naturalHeight` observed inside the frame, or from a flat constant. D-4 decides. (This is the same gap that degrades YARL — `spec-e53-1:223-229`.) |
| **V-14** | **i18n is flat-key JSON, both files at 1043 keys, key-sets identical.** | `en.json:389-397` / `pl.json:389-397` carry the nine `catalog.image_viewer.*` keys. `python3` set-compare over both files: `len == 1043` each, `set(en) == set(pl)` → `True`. | New keys go into **both** files at the same insertion point. AC-5's key-set diff is mechanical. |
| **V-15** | **The viewer's colours are theme-invariant by design.** | `theme.css:52-57` — `--color-gallery-control` / `-foreground` are documented as identical in both themes because the controls float over arbitrary photography. `DESIGN.md:208` re-states this and calls out the consequence. | `NFR26-DARKMODE-1` for this surface means *"light and dark are correctly identical"*, not *"they must differ"*. Both dark baselines still regenerate; a reviewer must not read "no light/dark difference" as a miss. |
| **V-16** | **Visual tests run `pl-PL`; every matcher is the literal Polish string.** | `tests/visual/playwright.config.ts` forces `pl-PL` / `Europe/Warsaw` across the fixed 4-project matrix; `filters-panel.spec.ts:9-19` is the house pattern, including the mandatory `toBeVisible()` before every `toHaveScreenshot`. | AC-7's targeted coverage must match on `"Powiększ"` / `"Pomniejsz"` / `"Dopasuj"`, not English. |
| **V-17** | **Trigger anchor for return-focus assertions.** | `ModelGallery.tsx:128` — `data-testid="gallery-fullscreen-trigger"`; it is the element both visual specs click (`catalog-detail.spec.ts:50`, `image-viewer-containment.spec.ts:133`). | Return focus is asserted **against this trigger**, not against `document.body`. |
| **V-18** | 🛑 **`e.preventDefault()` inside React's `onTouchStart` / `onTouchMove` / `onWheel` is a NO-OP in this repo.** | Read out of the installed `react-dom` **19.2.6** production bundle: the root-container registration does `!passiveBrowserEventsSupported \|\| ("touchstart" !== domEventName && "touchmove" !== domEventName && "wheel" !== domEventName) \|\| (listenerWrapper = !0)` then `addEventListener(domEventName, …, { passive: listenerWrapper })`. React therefore attaches **`touchstart`, `touchmove` and `wheel` as passive** at the root. | A pinch/pan implementation that calls `preventDefault()` from a React `onTouchMove` handler will **silently fail** and the browser will keep scrolling/zooming underneath. The two working routes are: (a) suppress the default declaratively with `touch-action` CSS (see V-19), or (b) attach a **native** non-passive listener via a ref — `el.addEventListener("touchmove", h, { passive: false })` with a matching cleanup. The shipped handlers (`:145-216`) never needed this because they only read coordinates on start/end and never prevent anything. **This is the single most likely way T3 ships broken while every test still passes.** |
| **V-19** | **`touch-action` is the correct lever, and it is not `user-scalable=no`.** | The shipped viewer sets no `touch-action` anywhere; the page-level pinch-zoom guarantee comes from `index.html:5` not carrying `user-scalable=no` (V-3, AC-8). | To own the pinch/pan gesture, scope `touch-action: none` (or `pinch-zoom`) to the **transform layer / image element only** — never to the dialog root, the toolbar or `<body>`. Element-scoped `touch-action` does **not** violate `EXPERIENCE.md:291` / `architecture.md:3374`, which ban the document-wide `user-scalable=no` meta; putting it on the root effectively would, and is forbidden. State the chosen scope in a comment so a reviewer can tell the two apart. |
| **V-20** | **The new controls need stable test handles — 53.3 will query them.** | The eight existing handles are listed at `spec-e53-1:187-199`; `image-viewer-containment.spec.ts:209-213` is how they are consumed. `data-thumb-idx` (`:378`) is a gesture hook, not a test handle. | Add exactly four, following the shipped `image-viewer-*` convention: **`image-viewer-toolbar`**, **`image-viewer-zoom-in`**, **`image-viewer-zoom-out`**, **`image-viewer-zoom-reset`**. Naming them here rather than leaving it to dev is what lets 53.3 be written against a known contract instead of discovering it. |

---

## 3. Design decisions

### D-1 — Option 3 is the working assumption, and it is provisional

Implement by extending `ImageFullscreenViewer.tsx`. No new dependency. This is `spec-e53-1:380`'s recommendation, and it is **PROVISIONAL** — see § 0. If dev discovers the in-house transform/clamp layer exceeding ≈450 added LOC or needing a third-party gesture-math dependency, that is **reversal trigger R3** (`spec-e53-1:402`): stop, surface it, route through `bmad-correct-course`. Do not silently install a gesture library.

### D-2 — Three layers, not two: transform / chrome / toolbar

The single most load-bearing structural decision, and the one the epic sketch under-specifies.

| Layer | Contains | Behaviour |
|---|---|---|
| **Transform layer** | the element returned by `renderImage` only | scales and translates with zoom/pan |
| **Chrome layer** (`:299-305`, exists today) | counter, close, prev/next; the strip is its sibling | fades + `aria-hidden` on tap-to-hide; **unchanged semantics** |
| **Toolbar layer** (new) | Zoom In, Zoom Out, Reset | **always mounted, always visible, never `aria-hidden`, never inside the transform layer** |

Binding sources: `EXPERIENCE.md:234` (*"Zoom controls are **always mounted** and are never part of the tap-to-hide chrome layer. Toolbar lives **outside** the transform layer"*), `DESIGN.md:286` and `:299` (*"Keep the lightbox zoom controls mounted at every chrome state"* / don't *"Fold them into the tap-to-hide chrome layer"*), mockup state C (`key-viewer-chrome.html:109`). This is what makes WCAG 2.2 SC 2.5.1 satisfiable for a zoomed, one-handed, chrome-hidden user — the exact scenario in `EXPERIENCE.md:487`.

**Consequence for the tap handler:** a tap that lands on the toolbar must not toggle chrome and must not be read as a swipe. The toolbar is a new origin case alongside `stripOrigin` / `thumbOrigin` (`:156-176`). Reuse the existing narrow-target technique (`e.target.closest(...)`), do not widen `stripOrigin`'s coords check.

### D-3 — Gesture arbitration is copied verbatim from the UX spine, not invented

`EXPERIENCE.md:269-274`, normative:

- **at scale 1.0** — a horizontal drag navigates, using the **existing** 50 px threshold / 60 px vertical tolerance, and strip-origin drags never navigate;
- **at scale > 1.0** — a drag **always** pans and **never** navigates; navigation remains available via chevrons, the thumb strip, and arrow keys;
- **Reset** returns to 1.0 and **re-arms** swipe navigation;
- **double-tap** toggles between 1.0 and one fixed zoom step, and every state it reaches is also reachable by the visible controls.

Write this as an explicit branch on the current scale at the top of `onTouchEnd`, not as emergent behaviour. `SWIPE_THRESHOLD_PX` / `SWIPE_VERTICAL_TOLERANCE_PX` (`:43-48`) keep their values.

### D-4 — Zoom limits and clamping, stated as concrete numbers with a contract each

`V-13` means max zoom cannot come from props. Ruling, so the dev agent does not invent constants (project-context.md § "Magic constants in specs require contract-pointing justification"):

- **Min scale = 1.0.** Contract: the viewer's fit-to-frame state is the 48.1 geometry (`:294`); below 1.0 there is nothing to see and Reset would have two meanings.
- **Max scale = 4.0**, unless the rendered image's `naturalWidth`/`naturalHeight` (read from the `<img>` inside the frame, not from props) supports more without upsampling past 1 image-pixel per CSS-pixel, in which case that ratio caps it. Contract: `FR26-VIEW-1`'s inspectability goal on a 4:1/8:1 panorama (`epics.md:4579`), balanced against not presenting a blurred upscale as a feature.
- **Zoom step = 1.5× per Zoom In / Zoom Out press**; `+`/`-` use the same step. Contract: `EXPERIENCE.md:282` requires key and button to be the same action.
- **Double-tap step = 2.0**, toggling against 1.0. Contract: `EXPERIENCE.md:273` — *"a fixed zoom step"*, and every state it reaches must also be reachable by the buttons (2.0 is reachable via Zoom In from 1.0 at 1.5× → 1.5 → 2.25; if exactness matters, snap double-tap to the nearest step boundary rather than introducing a value the buttons cannot produce).
- **Pan clamp:** the scaled image's edges may never move inside the frame's edges — at scale 1.0 pan is 0 in both axes, and at every scale the clamp is re-evaluated after a zoom change so a zoom-out can never leave the image detached from an edge.
- **Rotation / resize:** re-fit to the new viewport, **preserving zoom level and re-clamping pan** (`EXPERIENCE.md:262`). Never leave the image outside the visible area.

If dev finds one of these numbers wrong on evidence, changing it is fine — changing it *silently* is not; record it in the Change Log with the contract it now serves.

### D-5 — "Safe-area handling" without touching the viewport meta

Per V-3, `env(safe-area-inset-*)` is inert today and enabling it is app-wide. Resolution:

1. **Do not touch `apps/web/index.html`.** Adding `viewport-fit=cover` is Ask First (§ 5).
2. Express the toolbar's and close button's insets as `max(<current-inset>, env(safe-area-inset-<side>))`. This is **exactly today's value** while the meta lacks `viewport-fit=cover`, and becomes correct automatically if it ever gains it. Forward-compatible, zero visual delta, zero baseline risk from this line alone.
3. The dynamic-viewport obligation is already carried by `dvh` (`:260`, `:294`) and stays that way (`EXPERIENCE.md:337`: *"Safe-area insets and `dvh` (never `vh`) govern the viewer's height budget on phones, exactly as Story 48.1 established"*).
4. **Say so in the story record.** A reviewer must be able to see that safe-area was handled *and* that it is currently inert, rather than discovering it later.

### D-6 — Load/error state: what 53.2 owns, and how it observes without touching the renderers

`EXPERIENCE.md:259-260` wants zoom controls mounted-but-disabled until the image resolves (disabled state *announced*, not just dimmed), and an inline error that never traps the user. V-12 forbids modifying the renderers, and V-4 shows the loading key is unwired.

**Mechanism, viewer-owned and contract-free:** `load` and `error` do not bubble but they **do capture**. The viewer attaches `addEventListener("load" | "error", handler, { capture: true })` on its own frame element (`:280-283`) and learns when the descendant `<img>` — whoever rendered it — resolved or failed. No `ImageRenderer` change, no call-site change, no `AnonymousImage` change. Reset the pending state whenever `activeIdx` changes.

**Scope split, so 53.3 is not pre-empted:**
- **53.2 owns:** the disabled/enabled state of the three zoom controls and its announcement, and the guarantee that close + toolbar stay reachable when an image fails.
- **53.2 does NOT own:** a new visual loading treatment beyond wiring the existing `catalog.image_viewer.loading` string, and does not own the loading/error *test matrix* — `epics.md:4579` puts "error and slow-load" in 53.3.

### D-7 — Announcing zoom level

`EXPERIENCE.md:318` — *"Viewer zoom level changes announce politely ('200%')"*. Implement as one `aria-live="polite"` region inside the viewer carrying the current percentage. This needs its own i18n key (D-8), and it is the reason a zoom change is not silent for a screen-reader user who cannot see the transform.

### D-8 — The exact new i18n keys, and one recorded terminology collision

`EXPERIENCE.md:211` fixes the Polish copy: **"Powiększ" / "Pomniejsz" / "Dopasuj"**, with the explicit Don't being *"Icon-only zoom controls with no accessible name"*.

| Key | `en.json` | `pl.json` |
|---|---|---|
| `catalog.image_viewer.zoom_in` | `Zoom in` | `Powiększ` |
| `catalog.image_viewer.zoom_out` | `Zoom out` | `Pomniejsz` |
| `catalog.image_viewer.zoom_reset` | `Fit` | `Dopasuj` |
| `catalog.image_viewer.zoom_level` | `Zoom {{percent}}%` | `Powiększenie {{percent}}%` |

**Recorded collision (do not silently "fix"):** `catalog.image_viewer.trigger_label` is already `"Powiększ"` in Polish (`pl.json:389`, en `"Open fullscreen"`). After this story, the gallery's fullscreen trigger and the viewer's Zoom In control share one Polish accessible name on the same journey. **53.2 keeps the spine's viewer labels verbatim — the spine wins (`DESIGN.md:264`) — and does NOT rename the shipped trigger**, because that is a different surface, owned by a shipped story, with its own baselines. Raise it as a cross-surface terminology finding for **Story 54.1** (`epics.md:4591` — *"a category is not 'Kategoria' in one surface and 'Dział' in another"*; same class of finding). Recorded here so the omission is visibly deliberate.

### D-9 — Scroll lock is verified, not built

Per V-2. AC-6 is an **assertion** AC, not an implementation AC. If the assertion fails — i.e. Base UI's lock is not actually engaging on this surface — that is a finding to surface before writing a replacement, because a hand-rolled lock stacked on a working one is worse than either.

### D-10 — The 53.2 / 53.3 boundary, stated so neither story leaks into the other

| 53.2 owns (this story) | 53.3 owns (`epics.md:4579`) |
|---|---|
| the implementation; component-level a11y assertions in `ImageFullscreenViewer.test.tsx`; the en+pl keys and their key-set diff; **targeted** pl-PL visual coverage of the new toolbar (open-at-rest + zoomed); regenerating the four existing baselines | the full contract: Pixel 5 portrait **and** landscape; panorama 4:1 and 8:1; portrait 1:4; small source; rotation refit; repeated open-close; error and slow-load; and the **physical Android Chrome smoke** as operator evidence |
| keeping `image-viewer-containment.spec.ts` green with **zero edits** | extending that suite |

---

## 4. Acceptance Criteria

**AC-1 — Pinch, pan and double-tap work, and the toolbar never moves with them.**
Given the viewer is open on a touch device, when the user pinches, drags at scale > 1.0, or double-taps, then the image scales / pans / toggles zoom per D-4, the pan stays clamped so no image edge moves inside the frame, and the Zoom In / Zoom Out / Reset toolbar and the close button render at constant size and position at every zoom level — because they are outside the transform layer (D-2).

**AC-2 — Three visible single-pointer controls, always mounted, plus their keyboard equivalents.**
Given the viewer is open, when it renders, then Zoom In, Zoom Out and Reset are visible as three separate controls (`DESIGN.md:286`); they remain mounted, visible and **not** `aria-hidden` when the tap-to-hide chrome layer is hidden — including while zoomed (mockup state C, `key-viewer-chrome.html:109`); each carries an accessible name from D-8; each is ≥ 40×40; and `+`, `-`, `0` on the dialog perform exactly the same three actions as the buttons (`EXPERIENCE.md:282`), alongside the existing `←`/`→` (`:128-143`). No zoomed state is reachable only by gesture — WCAG 2.2 SC 2.5.1 and SC 2.5.7 (`EXPERIENCE.md:300-301`).

**AC-3 — Swipe-vs-pan arbitration is explicit and the shipped guards still hold.**
Given a horizontal drag, when it is released, then: at scale 1.0 it navigates using the unchanged `SWIPE_THRESHOLD_PX = 50` / `SWIPE_VERTICAL_TOLERANCE_PX = 60` and strip-origin drags still never navigate; at scale > 1.0 it always pans and never navigates; Reset returns to 1.0 and re-arms navigation (D-3). The four-cell gesture matrix TB-043 closed — visible/hidden strip × tap/drag — still behaves as it does today at scale 1.0, and a toolbar-origin touch neither toggles chrome nor navigates.

**AC-4 — Close target ≥ 44×44 and the a11y baseline is preserved.**
Given the shipped close button at `h-10 w-10` (`:323`), when this story lands, then it is ≥ 44×44 CSS px (`DESIGN.md:287`, `EXPERIENCE.md:302`) and every existing a11y property still holds: sr-only i18n `DialogTitle` (`:263-265`), `aria-label` on close/prev/next/thumbs, `aria-current` on the active thumb, `aria-hidden` following `chromeVisible` for the chrome layer and strip only.

**AC-5 — New labels ship in en **and** pl with a key-set diff, and zoom level is announced.**
Given the four keys in D-8, when `en.json` and `pl.json` are diffed, then both gained exactly the same key set, both files still parse, Polish is the spine's copy verbatim (`Powiększ` / `Pomniejsz` / `Dopasuj`) and is neither a placeholder nor English-identical, and no existing key changed value. A zoom change updates a polite live region with the current percentage (D-7). The `trigger_label` collision from D-8 is recorded in this story's record and raised for 54.1 — **not** silently renamed.

**AC-6 — Body scroll lock with restoration is proven, not rebuilt.**
Given `EXPERIENCE.md:234` requires scroll locked on open and **restored** on close, when the viewer opens and closes, then document scrolling is prevented while open and the document's scroll position and inline overflow styles are exactly what they were before opening. **The implementation is Base UI's existing `modal` scroll lock (V-2); this story adds no second lock.** The AC is discharged by a test that opens and closes the viewer and asserts the before/after state, plus a stated check that `<html>`'s computed `overflow-y` was not already `hidden`/`clip` (which would silently no-op the lock).

**AC-7 — Component-level a11y assertions and targeted pl-PL visual coverage, both new.**
Given `epics.md:4575` puts this at this story's own gate, when the suites run, then:
- `ImageFullscreenViewer.test.tsx` is **extended** (never rewritten) with assertions for: an accessible name on each of the three zoom controls; the zoom controls present and **not** `aria-hidden` while the chrome layer is hidden; focus trapped while open; focus returned to `gallery-fullscreen-trigger` (V-17) on close; the close target ≥ 44×44; `+`/`-`/`0` producing the same state as the three buttons; and the scale-1.0-vs-zoomed drag branch.
- A targeted Playwright spec captures the open viewer **at rest** and **zoomed with chrome hidden** across the fixed 4-project matrix, with an explicit `toBeVisible()` on the concrete state before every `toHaveScreenshot` (`filters-panel.spec.ts:17-19` is the pattern), matching on the literal Polish strings (V-16).

**AC-8 — Story 48.1's five invariants survive, and the standing suite is untouched.**
Given `architecture.md:3371-3376`, when the diff is read, then: `:260` still expresses geometry in **one** reference box (`left-[1vw]` + `translate-x-0`; never `left-1/2` + `-translate-x-1/2`); every viewport-relative height is `dvh`, never `vh`; `user-scalable=no` appears nowhere and `index.html:5` is unmodified; `apps/web/src/ui/dialog.tsx` is unmodified; and `apps/web/tests/visual/image-viewer-containment.spec.ts` passes with **zero edits to that file**. If the always-mounted toolbar changes the vertical budget, `:294`'s `max-h-[calc(95dvh-5rem)]` is re-derived and the new arithmetic is stated — not left stale.

**AC-9 — Baselines regenerate with sign-off; the auth boundary is untouched.**
Given the toolbar is new pixels, when baselines are updated, then all four `catalog-detail-image-viewer-open-{desktop,mobile}-{light,dark}.png` are regenerated with a `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line per PNG in the commit message (Baseline Acceptance Gate), the light/dark pair being visually identical for the viewer chrome is stated as **correct** per V-15, and `git diff` shows **zero** changes to `types.ts`'s `ImageRenderer`/`ImageSource` contracts, `ModelGallery.tsx`'s renderer, `$token.tsx`'s `AnonymousImage`/`LazyAnonymousImage`/`shareBlobCache`, or `ui/dialog.tsx`.

**AC-10 — Provisional-adoption honesty.**
Given `G26-LIB` is open, when this story's record is written, then it states that the implementation follows the **provisional** option-3 call, that physical Android Chrome gesture evidence was **not** collected and no gesture-quality claim is asserted or inferred, and that `G26-LIB` remains open and is **not** closed by this story.

---

## 5. Ask First / Never

**Ask First (surface to the controller; do not decide alone):**
- **Starting dev at all while `G26-LIB` is open** — § 0.
- Adding `viewport-fit=cover` to `apps/web/index.html:5` (D-5). App-wide blast radius including the frozen mobile `ModuleRail`.
- Any gesture-math or lightbox dependency (reversal trigger R3, `spec-e53-1:402`).
- Changing `SWIPE_THRESHOLD_PX` or `SWIPE_VERTICAL_TOLERANCE_PX` (`:43-48`) — normative in `EXPERIENCE.md:270`.
- Any deviation from `DESIGN.md` / `EXPERIENCE.md` for this surface — the spines win (`DESIGN.md:264`); a deviation is a `bmad-correct-course` input.
- Renaming `catalog.image_viewer.trigger_label` (D-8).
- Removing the dead `@radix-ui/*` dependencies (V-1) — real cleanup, wrong story.

**Never:**
- **Never touch `apps/web/src/ui/dialog.tsx`** — Ask First per `architecture.md:3375`; blast radius is every dialog in the app.
- **Never modify `renderImage` / `renderThumb`, their call sites, or `AnonymousImage` / `LazyAnonymousImage` / `shareBlobCache`.** Breaks `credentials:"omit"` (NFR10-SHARE-SECURITY-1) and the 60 req/min `(token, IP)` mitigation (Init 12 Story 19.1).
- **Never edit `apps/web/tests/visual/image-viewer-containment.spec.ts`.** Standing suite (`architecture.md:3376`); it must pass unmodified.
- **Never reintroduce `left-1/2` + `-translate-x-1/2`, and never use `vh` for a viewport-relative height.**
- **Never write `user-scalable=no`** — `EXPERIENCE.md:291`, `architecture.md:3374`, `spec-e48-1:24`.
- **Never fold the zoom controls into the tap-to-hide chrome layer** — `DESIGN.md:299`, `EXPERIENCE.md:234`.
- **Never build a second body-scroll lock** (V-2, D-9).
- **Never assert, simulate or infer physical-Android gesture quality** — `epics.md:4579`.
- **Never close `G26-LIB`; never edit `architecture.md` Decision BA** — gate closure is the operator's; an architecture amendment routes through `bmad-correct-course`.
- **Never widen scope to `Viewer3DModal` or other `DialogContent` consumers** — deferred at `architecture.md:3378`.
- **Never absorb 53.3's test contract** (D-10).
- **Never hard-code a colour.** Every value comes from a `--color-*` token; `--color-gallery-control` / `-foreground` already exist (`theme.css:56-57`) and no new token is authorised (`EXPERIENCE.md` § Non-goals).

---

## 6. Tasks / Subtasks

- [x] **T0 — Confirm the entry gate.** (§ 0, AC-10)
  - [x] Re-read § 0. Confirm the controller has either closed `G26-LIB` or explicitly accepted the provisional option-3 call. If neither, **stop and report** — do not write product code.
  - [x] Branch `feat/E53.2-mature-lightbox` from `main`.
- [x] **T1 — Transform state + clamp math.** (AC-1)
  - [x] Add scale + pan-offset state to `ImageFullscreenViewer.tsx`, held **outside** the toolbar's render subtree.
  - [x] Implement the D-4 limits: min 1.0, max 4.0 capped by observed `naturalWidth`/`naturalHeight`, step 1.5×, double-tap 2.0; re-clamp pan after every scale change; reset pan to 0 at scale 1.0.
  - [x] Re-fit on viewport resize/rotation preserving zoom level and re-clamping pan (`EXPERIENCE.md:262`).
- [x] **T2 — Three-layer structure.** (AC-1, AC-2, D-2)
  - [x] Wrap only the `renderImage(...)` output (`:284-295`) in the transform layer. Do not inspect or replace what the renderer returns.
  - [x] Add the always-mounted toolbar as a sibling of the chrome layer (`:299-305`), not a child. It must not receive `aria-hidden` and must not fade with `chromeVisible`.
  - [x] If the toolbar changes the vertical budget, re-derive `:294`'s `max-h-[calc(95dvh-5rem)]` and state the new arithmetic in a comment.
- [x] **T3 — Touch gestures + arbitration.** (AC-1, AC-3)
  - [x] Pinch (two-pointer) → scale about the pinch midpoint. Pan (one pointer at scale > 1.0). Double-tap → toggle 1.0 ↔ the fixed step.
  - [x] **Handle V-18 first.** Do not rely on `preventDefault()` from a React `onTouchMove` — it is passive and silently ignored. Use element-scoped `touch-action` (V-19) and/or a native non-passive listener with cleanup. Stay on Touch events; do not mix in Pointer Events, which would double-fire alongside the shipped handlers.
  - [x] Branch `onTouchEnd` (`:179-216`) on current scale per D-3, leaving the scale-1.0 path — including the `stripOrigin` / `thumbOrigin` guards (`:145-177`) — behaviourally identical.
  - [x] Add a toolbar-origin case using the narrow `closest()` technique so toolbar taps neither toggle chrome nor navigate.
- [x] **T4 — Visible controls + keyboard.** (AC-2, AC-4)
  - [x] Three buttons: Zoom In, Zoom Out, Reset — 40px circular, `bg-gallery-control/40`, `rounded-full`, per `DESIGN.md:172-176`, carrying the four V-20 testids.
  - [x] Extend `onKey` (`:128-143`) with `+`, `-`, `0` mapping to the same three actions.
  - [x] Raise the close button (`:323`) from `h-10 w-10` to ≥ 44×44.
- [x] **T5 — i18n.** (AC-5, AC-2)
  - [x] Add the four D-8 keys to `en.json` **and** `pl.json` at the same insertion point; verify key-set parity mechanically.
  - [x] Wire every new control through `t()`; add the `aria-live="polite"` zoom-level region (D-7).
  - [x] Record the `trigger_label` collision in this story's record and raise it for 54.1. Do not rename it.
- [x] **T6 — Load/error observation.** (AC-2, D-6)
  - [x] Capture-phase `load` / `error` listener on the frame element; reset pending state on `activeIdx` change.
  - [x] Zoom controls disabled while pending, with the disabled state announced, not merely dimmed. Close + toolbar stay reachable on error.
- [x] **T7 — Safe-area + dynamic viewport.** (AC-8, D-5)
  - [x] Express toolbar/close insets as `max(<current>, env(safe-area-inset-<side>))`. Leave `index.html` untouched.
  - [x] Confirm every viewport-relative height is still `dvh` and `:260`'s single-reference-box anchoring is byte-identical in form.
- [x] **T8 — Scroll-lock verification.** (AC-6, D-9)
  - [x] Assert lock-on-open and full restoration on close. Assert `<html>`'s computed `overflow-y` is not already `hidden`/`clip`. Add **no** new lock.
- [x] **T9 — Component a11y assertions.** (AC-7)
  - [x] Extend `ImageFullscreenViewer.test.tsx` per AC-7 bullet 1. Keep all five existing `it` blocks passing. Remember `globals: false` → the file's existing `cleanup` discipline applies.
- [x] **T10 — Targeted pl-PL visual coverage + baselines.** (AC-7, AC-9)
  - [x] New spec: open-at-rest and zoomed-with-chrome-hidden, 4 projects, `toBeVisible()` before every screenshot, Polish matchers.
  - [x] Regenerate the four `catalog-detail-image-viewer-open-*` baselines; read each diff before accepting; write one `baseline-reviewed:` line per PNG.
- [x] **T11 — Invariant + boundary proof.** (AC-8, AC-9)
  - [x] `image-viewer-containment.spec.ts` green with zero edits to that file.
  - [x] `git diff` shows no change to `ui/dialog.tsx`, `index.html`, the `ImageRenderer`/`ImageSource` contracts, `ModelGallery.tsx`'s renderer, or `$token.tsx`'s `AnonymousImage`/`LazyAnonymousImage`/`shareBlobCache`.
  - [x] Grep proof: no `user-scalable`, no `left-1/2` + `-translate-x-1/2` in the viewer, no `vh` where `dvh` is required.
- [x] **T12 — Full gate + honest record.** (AC-10)
  - [x] `infra/scripts/check-all.sh` green standalone, teed to `.hermes/run-logs/`.
  - [x] Record in the Dev Agent Record: the provisional option-3 posture, that no physical Android evidence was collected, and that `G26-LIB` remains open.

---

### Review Findings

Native `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor, three parallel layers, all three returned; `failed_layers` empty), 2026-07-29, Claude Opus 5, repo-local, against the working tree on `feat/E53.2-mature-lightbox` @ baseline `a3aaf35`. **Not an Ezop signature, not human review.** Controller arbitrated the Step-4 choices for this headless run: apply every in-scope patch; do not accept an over-threshold R3 silently.

**Applied patches (8 code defects, all fixed and covered by new tests):**

- [x] [Review][Patch] `+` / `-` / `0` cancelled the browser's own `Ctrl`/`Cmd` page-zoom shortcuts — a WCAG 1.4.4 regression introduced by an a11y story. The handler called `preventDefault()` unconditionally. Guarded on `ctrlKey`/`metaKey`/`altKey`; the `←`/`→` path is deliberately left byte-identical above the guard. [`ImageFullscreenViewer.tsx:401`]
- [x] [Review][Patch] A zoom control that disables itself under the user's own finger dropped focus to `<body>` inside the focus trap. **Measured in Chromium, not assumed** — a throwaway Playwright probe returned `document.activeElement === document.body`, and Base UI's focus manager does not recover it. Focus is now handed to the sibling control still live. [`ImageFullscreenViewer.tsx:859`]
- [x] [Review][Patch] The polite live region announced an unasked-for "Zoom 100%" on every image load and every navigation (one per photo when arrowing a gallery), while the "loading" text it was supposed to announce was never announced at all — an `aria-live` region does not announce content it is INSERTED with, and Base UI portals the whole subtree in at once. Announcement now lives in state, is written from an effect, and fires only on a real zoom-level change (`EXPERIENCE.md:318`). Zero visual delta — verified against the existing baselines. [`ImageFullscreenViewer.tsx:834`]
- [x] [Review][Patch] Lifting a resting third finger mid-pinch tore the pinch down permanently (`onTouchStart` never fires again), converting the rest of the gesture into a single-pointer pan; and a gesture that opened with two coalesced fingers never recorded a drag origin, so post-pinch panning was dead until the user lifted completely. The multi-touch release branch now re-establishes the pinch while ≥ 2 fingers remain and synthesises the drag origin when none exists. [`ImageFullscreenViewer.tsx:528`]
- [x] [Review][Patch] An `activeIdx` change left `pinchRef` / `touchStart` / `gestureMovedRef` armed. The pinch snapshot is absolute (finger separation → scale), so a gesture in flight when the photo changed re-applied the previous photo's zoom to the new, still-loading one — with all three controls disabled and no way back. [`ImageFullscreenViewer.tsx:307`]
- [x] [Review][Patch] A resize / `orientationchange` while the image was unmeasurable (the `/share` renderer swapping in a placeholder, or a mid-decode `offsetWidth` of 0) re-derived the ceiling as `BASE_MAX_SCALE`, silently demoting a panorama's 20× ceiling to 4× and dragging the user's zoom down with it, with nothing to restore it. "Unmeasurable" is no longer read as "4". [`ImageFullscreenViewer.tsx:361`]
- [x] [Review][Patch] The initial probe read `complete` alone, which is also `true` for an image that already FAILED (its `error` event fired before the listener existed) — arming the zoom controls over a broken image. `naturalWidth > 0` now separates the two. [`ImageFullscreenViewer.tsx:331`]
- [x] [Review][Patch] A tap swallowed by the toolbar or a thumb left `lastTapRef` armed, so "tap image → press Zoom in → tap image" inside one 300 ms window read as a double-tap and threw away the zoom just applied. Both swallow paths now break the pending pair. [`ImageFullscreenViewer.tsx:561`]

**Applied patches (5 record-accuracy defects — the Acceptance Auditor verified § 9's claims rather than taking them at face value):**

- [x] [Review][Patch] § 9's verification table understated every vitest count. Corrected below.
- [x] [Review][Patch] The R3 reversal-trigger table — the input to a controller decision — was computed from wrong `numstat` inputs (`+535`/`−10`; actual pre-review `+557`/`−20`). Recomputed below with a stated, comment-state-aware method.
- [x] [Review][Patch] § 9 said *"Both diff images were read"* while **four** baselines were regenerated. Corrected.
- [x] [Review][Patch] The **8 new** `image-viewer-zoom` PNGs also require `baseline-reviewed:` sign-off lines — `_check-baseline-review.mjs` matches `--diff-filter=AM`, so additions are gated exactly like modifications. § 9 flagged sign-off for the 4 regenerated PNGs only. Corrected.
- [x] [Review][Patch] § 9's File List marked this story file **UPDATE**; it is untracked, i.e. **NEW**. Corrected.

**Deferred (real, out of this story's contracted scope — see D-6 / D-10):**

- [x] [Review][Defer] A renderer that never mounts an `<img>` at all (a `/share` blob acquisition that rejects) yields neither `load` nor `error`, so the toolbar stays disabled forever and no failure is ever announced [`ImageFullscreenViewer.tsx:328`] — deferred to **53.3**; a readiness timeout is a new constant and a new behaviour, and `epics.md:4579` puts "error and slow-load" there.
- [x] [Review][Defer] `imageStatus === "error"` renders an empty live region and there is no inline error element, so a failed image gives the user zero feedback [`ImageFullscreenViewer.tsx:846`] — deferred to **53.3**; AC-5 fixes this story's key set at exactly four and D-6 assigns the visual error treatment there. Flagged so no reviewer reads "close + toolbar stay reachable" as "the spine's error state is satisfied". It is not.
- [x] [Review][Defer] Every double-tap visibly flashes the chrome layer (tap 1 toggles it, tap 2 toggles it back through a 150 ms fade) [`ImageFullscreenViewer.tsx:582`] — deferred: the only fix is to defer *every* single tap by `DOUBLE_TAP_WINDOW_MS`, which would change TB-043's hardened scale-1.0 tap path that **AC-3 requires to stay behaviourally identical**. Net state is already correct; only the transition is observable.
- [x] [Review][Defer] No coverage for the `DOUBLE_TAP_WINDOW_MS` / `DOUBLE_TAP_SLOP_PX` boundaries — deferred to **53.3**'s gesture matrix. Partially closed this round: the resize-refit path and the toolbar-tap/double-tap interaction now have tests.

**Dismissed as noise or false positives (10) — recorded so they are not re-raised:**

| Raised | Why dismissed |
|---|---|
| Pan is touch-only; no keyboard/mouse pan, so a desktop user can only see the centre crop when zoomed | `EXPERIENCE.md:301` resolves SC 2.5.7 explicitly: *"Pan has zoom-and-reset equivalents"*, and `:282` fixes the viewer key map at `←`/`→`/`+`/`-`/`0`. Spine-sanctioned, and the spines win (`DESIGN.md:264`). |
| The three zoom controls are 40 px, below the 44 px floor this story invokes for the close button | `DESIGN.md:176` sets `lightbox-zoom-control size: '40px'` explicitly. The 44 px token is `{spacing.target-fullscreen-close}`, a different component. |
| `resolveMaxScale` uses `max` where D-4 says the native ratio "caps it" (should be `min`) | D-4 reads *"unless … supports **more** … in which case that ratio caps it"*. `max(4, ratio)` is the literal reading; `min` would contradict "supports more". False positive. |
| The zoom ladder is not reversible at the ceiling (4 ↔ 2.667; 3.375 unreachable) | Inherent to multiplicative stepping against a clamp. No AC breach: every state stays reachable and `DOUBLE_TAP_SCALE` remains exactly two Zoom In presses. |
| Two controls share the accessible name "Powiększ" | D-8 records this deliberately and routes it to **Story 54.1**'s cross-surface terminology audit. Renaming `trigger_label` is § 5 Ask First. |
| `resolveMaxScale` ignores `devicePixelRatio`, so "1 image-pixel per CSS-pixel" is wrong on a phone | D-4 states the contract in image-px-per-CSS-px terms and the code matches it. Changing it is a D-4 deviation, i.e. `bmad-correct-course` input. |
| `Maximize2` is the expand glyph on a control labelled "Dopasuj" | `DESIGN.md:172-176` fixes size, colour and radius for `lightbox-zoom-control`, not the glyph. Not a spec breach. |
| The Layer-1 restructure's baselines are self-approving — nothing asserts the image is still centred | Refuted by measurement: the Acceptance Auditor independently confirmed all four regenerated PNGs change in **exactly two row bands** (close button y≈30–73, toolbar y≈638–692). The image did not move. |
| The live region is unthrottled during a continuous pinch | The screen-reader path is buttons and keys, which are discrete. After the announcement repair the region is silent at rest and during navigation. |
| The scroll-lock test's `page.mouse.wheel` precondition is environment-dependent across the 4-project matrix | Empirically green on all four projects, and the test asserts its own preconditions (page genuinely scrollable; viewport not already `hidden`/`clip`) rather than assuming them. |

---

## 7. Merge gate

This is a UI-touching story with product code, so the **full** gate applies (AGENTS.md § "Story branches", § "Pre-push hook policy & gate evidence"):

- `infra/scripts/check-all.sh` green **standalone**, log teed to `.hermes/run-logs/` — typecheck, build, eslint `--max-warnings=0`, stylelint, vitest, pytest (api + worker + infra), Playwright visual across all four projects, plus the drift gates.
- Native `bmad-code-review` (Blind Hunter + Edge Case Hunter + Acceptance Auditor), all actionable findings resolved or explicitly deferred.
- Independent external review — Aider via `laura-aider-review-diff` per `~/.local/share/laura-agent-ops/LAURA_AGENT_RULEBOOK.md`. Gemini is not a default reviewer; Codex is fallback/high-stakes only.
- Baseline Acceptance Gate: one `baseline-reviewed:` line per changed PNG, enforced by `apps/web/.husky/commit-msg`.
- ff-only merge to `main`, no squash. Auto-deploy follows because the range touches `apps/`.

---

## 8. Dev Notes

### Files this story touches

| Path | Action | Note |
|---|---|---|
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` | **UPDATE** | The whole implementation. 405 lines today; `spec-e53-1:154` estimates +305–435. Crossing ≈450 is reversal trigger R3. |
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.test.tsx` | **UPDATE** | Extend; never rewrite. |
| `apps/web/src/locales/en.json`, `pl.json` | **UPDATE** | Four keys each (D-8). |
| `apps/web/tests/visual/<new>.spec.ts` | **NEW** | Targeted toolbar coverage. |
| `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/*image-viewer-open*.png` | **UPDATE** ×4 | Sign-off per PNG. |
| `apps/web/src/modules/catalog/components/imageViewer/types.ts` | **UPDATE only if unavoidable** | Adding an optional viewer-internal prop is fine; changing `ImageRenderer` or the two mounts' contract is **Never** (V-12). |
| `ui/dialog.tsx`, `index.html`, `$token.tsx`, `ModelGallery.tsx`, `image-viewer-containment.spec.ts` | **DO NOT TOUCH** | § 5. |

### Current state of the file being modified

`ImageFullscreenViewer.tsx` today: a Base-UI `Dialog` + `DialogContent` (`:224-262`) carrying the 48.1 geometry className (`:260`) and an sr-only i18n `DialogTitle` (`:263-265`); a root div with the touch handlers (`:267-272`); a flex frame with `min-h-0` (`:280-283`) containing the `renderImage(...)` call with the `max-h-[calc(95dvh-5rem)]` cap (`:284-295`); an absolutely-positioned chrome layer that fades on `chromeVisible` (`:299-350`) holding counter/close/prev/next; and a bottom thumb strip (`:353-400`) that fades **and** goes `pointer-events-none` in the hidden state. State: `activeIdx`, `chromeVisible`, a `touchStart` ref carrying `{x, y, stripOrigin, thumbOrigin}`, a `lastLen` ref that caps `activeIdx` when `sources` shrinks (`:94-100`), and a `stripRef` used to scroll the active thumb into view with a `typeof … === "function"` jsdom guard (`:110-120`).

**What must keep working end-to-end**, whether or not an AC names it: prev/next + arrow-key navigation and counter (`:122-143`), tap-to-toggle chrome, strip scrolling without navigating, thumb clicks, the shrinking-`sources` guard, the empty-`sources` early return (`:218-222`), and the lazy-barrel code split (`index.ts:18-20`) with `Suspense fallback={null}` at both mounts.

### Implementation traps verified this run

- **React passive touch listeners (V-18).** The highest-probability silent failure in T3. Verified in the installed `react-dom` 19.2.6 bundle, not assumed from documentation.
- **`touch-action` scope (V-19).** Element-scoped is required and permitted; root/document-scoped suppression is forbidden. A reviewer will look for the comment distinguishing them.
- **jsdom has no layout.** `getBoundingClientRect()` returns all-zero rects and there is no `scrollIntoView` (which is why `:117` already guards it). A pan-clamp unit test written naively against jsdom rects passes trivially and proves nothing — that is a "lying about completion" failure mode. Either inject rects explicitly in the test, or keep vitest to control-level and state-transition assertions (which is what AC-7 asks for) and leave true geometry to the Playwright surfaces.
- **Visual Coverage Contract.** `apps/web/.husky/pre-commit` (`_check-visual-coverage.mjs`) requires a matching `tests/visual/<basename>*.spec.ts` for any **newly added** `apps/web/src/ui/*.tsx`. The toolbar belongs inside the module component, not in `ui/` — keep it there and the hook never fires. If dev extracts it to `ui/`, that hook becomes a hard gate and a matching spec must be staged in the same commit.
- **Reduced motion.** If a zoom/pan transition is animated at all, gate it on `prefers-reduced-motion`; the product posture is "no celebratory motion" and an unconditional transform transition on a zoom is exactly the kind of motion a reduced-motion user asked not to get.

### Project structure notes

- Path alias `@/*` = `apps/web/src/*`; the viewer already imports `@/ui/dialog` and `@/lib/utils`.
- `verbatimModuleSyntax` + `isolatedModules`: type-only imports need `import type`.
- `noUncheckedIndexedAccess`: `sources[i]` is `T | undefined` — branch, never `!`.
- Tailwind v4, no `tailwind.config.js`; arbitrary values (`h-[95dvh]`) are the house idiom here.
- `vitest` runs with `globals: false` — this test file already handles its own lifecycle; keep it that way.
- No new `--color-*` token is authorised.

### Git intelligence

`a3aaf35` / `de7d3b4` are Story 53.1's docs-only commits. `513f4bd`, `4a5adae`, `27f8173`, `3202b7c` are E52 admin/filters web work — no overlap with the viewer. The last commits to touch this component are Init 17's `55a9349` / `df7cfa0` / `71b3dda` (TB-043 gesture hardening) and E48.1's containment fix; both are exactly the work V-9 and V-10 say to preserve. **This story is the first to add product code to the viewer since 48.1.**

### Latest technical information (verified this run, not from memory)

- `@base-ui/react` **1.4.1** installed — the actual dialog primitive (V-1). `Dialog.Root` `modal` defaults `true`; `Dialog.Popup` exposes `initialFocus` / `finalFocus`; focus management is `FloatingFocusManager` (`DialogPopup.js:104-110`); Escape is `useDismiss({ escapeKey: isTopmost })` (`useDialogRoot.js:84`).
- `@base-ui/utils` `useScrollLock` — the shipped, ref-counted, self-restoring body scroll lock (V-2).
- `@radix-ui/react-dialog ^1.1.2` and three sibling Radix packages are declared but **unimported**. Any Radix-specific advice about this component — including in `spec-e53-1` — does not apply.
- No lightbox library is installed and none is authorised by this story.

### References

- `_bmad-output/planning-artifacts/epics.md:4563` (E53 header), `:4565` (goal), `:4567` (G26-LIB dependency), **`:4575` (this story's sketch)**, `:4579` (53.3), `:4591` (54.1 terminology audit).
- `_bmad-output/planning-artifacts/architecture.md:3363-3378` — Decision BA; `:3371-3376` the five carried-forward 48.1 invariants; `:3378` the explicit deferral; `:3386` the gate register incl. `G26-DEVGO` wording.
- `_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-26.md:205` — G26-LIB closure condition.
- `_bmad-output/planning-artifacts/ux-designs/ux-3d-portal-2026-07-26/DESIGN.md:66-67, :168-181, :208, :246, :264, :285-287, :299`; `EXPERIENCE.md:60, :211, :234, :259-262, :269-274, :282, :291, :300-302, :318, :337, :407, :417`; `mockups/key-viewer-chrome.html:60, :109`.
- `_bmad-output/implementation-artifacts/spec-e53-1-lightbox-adoption-recommendation.md:3-4` (provisional verdict), `:23` (why option 3), `:151` (the scroll-lock estimate V-2 corrects), `:255-259, :273-275, :290` (the Radix attribution V-1 corrects), `:245` (baselines), `:297` (gesture-model note), `:301-351` (uncollected Android protocol), `:400-404` (reversal triggers), `:410-416` (the five invariants verbatim), `:420-431` (option-3 handoff list).
- `_bmad-output/implementation-artifacts/spec-e48-1-mobile-fullscreen-containment.md:20-24` (Always/Never), `:66-81` (measured root cause), `:83` (residual risk).
- `_bmad-output/implementation-artifacts/53-1-lightbox-adoption-spike.md` — predecessor story record.
- `_bmad-output/triage-backlog.md` TB-043 (gesture hardening provenance), TB-044 (`min-h-0` + image cap).
- `_bmad-output/project-context.md` — i18n mandate, no-inline-hex, `noUncheckedIndexedAccess`, vitest `globals: false`, Baseline Acceptance Gate, Visual Coverage Contract.
- Shipped code at `a3aaf35`: `ImageFullscreenViewer.tsx`, `types.ts`, `index.ts`, `ImageFullscreenViewer.test.tsx`, `ui/dialog.tsx:4`, `index.html:5`, `theme.css:52-57`, `ModelGallery.tsx:128, :207-217`, `routes/share/$token.tsx:120, :174, :371-387`, `tests/visual/catalog-detail.spec.ts:48-58`, `tests/visual/image-viewer-containment.spec.ts:133-134, :202, :209-213`, `tests/visual/filters-panel.spec.ts:9-19`, `locales/en.json:389-397`, `locales/pl.json:389-397`.

---

## 9. Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), repo-local Claude Code, native `bmad-dev-story`.
Branch `feat/E53.2-mature-lightbox`, cut from `main` @ `a3aaf35` (= `baseline_commit`).

### Authorization posture (AC-10) — read first

- Implementation follows the **PROVISIONAL option-3 call** (`spec-e53-1:380`, extend the in-house viewer). The call has **not** been de-provisionalised by this story.
- **`G26-LIB` REMAINS OPEN.** This story did not close it and has no authority to.
- **NO physical Android Chrome evidence was collected.** Every gesture assertion in this story is a synthetic `TouchEvent` / jsdom / headless-Chromium assertion and is **regression evidence only**. No claim about real-device gesture *quality* (smoothness, inertia, palm rejection, pinch feel) is asserted, simulated or inferred. `spec-e53-1:301-351` § 7.3 remains entirely uncollected.
- `architecture.md` Decision BA was **not** edited. No `bmad-correct-course` route was taken or is owed by the implementation itself.
- Controller granted `G26-DEVGO` for this story only, under Ezop's standing Initiative 26 delegation. **Not an Ezop signature, not human review.**

### Debug Log References

Full gate evidence: `.hermes/run-logs/check-all-53-2-<ts>.log` (gitignored, local-only; the path is the citable evidence).

### Completion Notes List

**Four defects were found by measuring rather than assuming. Two of them would have shipped broken.**

1. **`load`/`error` listener never attached — toolbar would have been permanently disabled in production.** The D-6 capture-phase listener was first attached from an effect reading `frameRef.current`. Base UI **portals** the dialog popup, so on the first effect pass that ref is still `null`; the effect returned early and never re-ran (deps `[activeIdx]`). Result: `imageStatus` stuck at `loading`, all three zoom controls `disabled` forever — on the real site, not only in jsdom. Fixed with a **callback ref** (`attachFrame`) that mirrors the node into state, with `frameEl` added to the effect deps. Caught only because the jsdom probe contradicted the expected enabled state.
2. **`load` handler re-derived readiness from `img.complete`.** The handler called a shared `sync()` that re-read `complete`. In a real browser `complete` is `true` by the time `load` fires so it happened to work, but it is wrong in principle and made the path untestable (jsdom reports `complete === false` forever). The `load` **event** is now the readiness signal in its own right; `complete` is consulted only for the initial already-cached probe.
3. **`TouchEvent` cannot be constructed from object literals in Chromium.** `touches`/`changedTouches` accept only real `Touch` instances (`new Touch({identifier, target, clientX, clientY})`); plain objects throw *"Failed to convert value to 'Touch'"*. The visual spec now constructs them properly, keeping the tap on the same code path a phone takes instead of reaching past the shipped handler.
4. **`window.scrollTo` is not a valid scroll-lock probe.** `overflow: hidden` suppresses *user* scrolling but still permits *programmatic* scrolling (only `overflow: clip` forbids it), so the first AC-6 assertion passed vacuously in the wrong direction. Replaced with a **real wheel gesture** (`page.mouse.wheel`), plus a precondition proving the page was genuinely scrollable beforehand.

**Measured finding that corrects V-2's open question (AC-6).** V-2 said Base UI locks `<html>` *or* `<body>` depending on the overflow element/platform. Measured: **real Chromium locks `<body>` alone** (`overflow: hidden`) and leaves `<html>` untouched, while **jsdom sets both**. The original assertion (`documentElement.style.overflowY === "hidden"`) passed in jsdom and failed in the browser. Both AC-6 tests are now **element-agnostic**, asserting the contract `EXPERIENCE.md:234` actually states (scrolling prevented while open; document exactly restored after) rather than a platform detail. Pre-check confirmed the lock is not a silent no-op: effective viewport overflow was `visible` before opening, and a wheel gesture genuinely scrolled the page (151 px desktop / 300 px mobile). **No second lock was built** (D-9).

**Design decisions taken inside the story's latitude, recorded rather than applied silently:**

- **`DOUBLE_TAP_SCALE = 2.25`, not 2.0.** D-4 offers the escape *"snap double-tap to the nearest step boundary rather than introducing a value the buttons cannot produce"*. 2.25 is exactly two Zoom In presses (`1.5²`); 2.0 sits off the ladder and would have made AC-2's *"no zoomed state is reachable only by gesture"* false in the strict reading. Visible in the state-C baseline as `Powiększenie 225%`.
- **`resolveMaxScale` = `max(4, naturalWidth/renderedWidth)`, not `min`.** D-4 reads *"Max scale = 4.0, unless the image supports more without upsampling, in which case that ratio caps it"*. `max` is the only reading under which both stated contracts hold: a 4:1/8:1 panorama gets true native-pixel inspectability (`epics.md:4579`), and a small source keeps the default 4× envelope instead of rendering three dead controls. Falls back to 4.0 whenever geometry is unmeasurable (pre-decode, jsdom).
- **Close target → `h-11 w-11` (44px), not 48.** V-7 rules both acceptable; 44 is `{spacing.target-fullscreen-close}`'s own value and the smallest change satisfying the floor. Note prev/next remain 48px, so `DESIGN.md:287`'s *"larger than every other control"* is satisfied against the 40px zoom controls, not against the shipped chevrons.
- **Two new constants, each contract-pointed:** `TAP_MOVE_TOLERANCE_PX = 10` (a pan must not be read as a tap and flip chrome under the user; consulted **only** on the scale>1 path, so TB-043's four-cell matrix at 1.0 is byte-identical in behaviour) and `DOUBLE_TAP_WINDOW_MS = 300` / `DOUBLE_TAP_SLOP_PX = 44` (44 reuses the touch-target floor rather than inventing a number).
- **Toolbar centred with `inset-x-0` + `justify-center`**, not the mockup's `left:50%` + `translateX(-50%)`. Same visual result, one reference box, and it keeps the E48.1 invariant grep literally clean on this file.
- **No transition on the transform.** A pinch must track fingers exactly, and an unconditional zoom animation is precisely what a `prefers-reduced-motion` user asked not to get.
- **`touch-action: none` is scoped to the transform layer only** (V-19), with an in-code comment distinguishing it from the forbidden document-wide `user-scalable=no`. `apps/web/index.html` untouched; `env(safe-area-inset-*)` expressed as `max(<current>, env(...))` per D-5 — **currently inert** (no `viewport-fit=cover`), zero visual delta, forward-compatible.
- **`:294`'s `max-h-[calc(95dvh-5rem)]` needed no re-derivation.** The toolbar layer is `absolute` inside the frame, takes part in no flex layout and consumes none of the vertical budget; the in-flow siblings are still the frame and the `h-20` strip. Stated in a code comment (T2/AC-8).

**⚠️ Reversal trigger R3 — surfaced for the controller, not silently decided.** R3 is *"≈450 added LOC or a third-party gesture-math dependency"*.

**These figures were recomputed during native `bmad-code-review` after the Acceptance Auditor caught the original table's inputs being wrong** (it claimed `+535`/`−10`; `git diff --numstat` gives `+557`/`−20` for the pre-review tree). The counting method is now stated so it is reproducible: a line is "comment/blank" only if nothing but whitespace or braces survives after stripping `//` and `/* … */` — which is what makes the JSX `{/* … */}` block comments in this file count correctly. A naive line-prefix regex misclassifies their **continuation** lines as code and inflates the result by ~70 lines; both the original table and an intermediate figure produced during this review round were wrong for that reason.

| Measure | Pre-review | After review repairs | vs ≈450 |
|---|---|---|---|
| Raw added product lines (`ImageFullscreenViewer.tsx` + `zoom.ts`) | 690 | **805** | over — see below |
| …of which comments / blank | 324 | 385 | — |
| **Net added CODE**, comments+blank excluded, minus removed (20 / 21) | **346** | **399** | **under by 51** |
| Third-party gesture-math dependency | none | **none** — `package.json` + `package-lock.json` byte-identical | not tripped |

Read as implementation size, **R3 is not tripped**: native review measured 399 net added code lines, and Laura/controller independently sanity-checked the repaired diff with a stricter comment-state counter at 430 net added code lines; both sit inside `spec-e53-1:154`'s own `+305–435` estimate band even after the eight review repairs, and the dependency half of R3 — the substantive half — is zero. Read as raw line count it is over, because this file is comment-dense by house convention and the comments carry the V-18/V-19 passive-listener trap, the D-2 layering rationale, the D-5 safe-area rationale and now the measured focus-blur finding that a reviewer needs. **The controller may still elect a `bmad-correct-course` route on the raw count; this story does not decide that.** No product code was shaved to fit the threshold — the apparent breach was a measurement artefact and was resolved by fixing the measurement, not the code.

**Deliberately NOT done (scope boundaries held):**
- No inline **error message** element and **no fifth i18n key**. D-6 gives 53.2 only the disabled-state announcement plus "close + toolbar stay reachable on error"; the visual error *treatment* stays with 53.3 / the renderers, and AC-5 fixes the key set at exactly four.
- `catalog.image_viewer.trigger_label` **not renamed** (D-8). The Polish collision is real and now demonstrated in code: the new spec must scope `getByRole("button", {name: "Powiększ"})` **inside** `image-viewer-toolbar`, because the gallery trigger carries the same accessible name on the same journey. **Raised for Story 54.1's cross-surface terminology audit** (`epics.md:4591`); not silently fixed.
- Dead `@radix-ui/*` deps left in place (V-1) — real cleanup, wrong story.
- 53.3's test contract not absorbed (D-10): no landscape, no 4:1/8:1 panorama, no 1:4 portrait, no small-source, no rotation-refit, no repeated open-close, no error/slow-load matrix.

**Verification actually run (commands + results):**

**Counts below are POST-review-repair and were re-run this round.** The original table understated every vitest figure (it claimed 44 / 1101, written before the last tests landed and never refreshed) — corrected by the Acceptance Auditor.

| Command | Result |
|---|---|
| `npx vitest run src/.../imageViewer/` | **56 passed** (25 `zoom.test.ts` + 31 `ImageFullscreenViewer.test.tsx` = 5 original `it` blocks, untouched and still green, + 18 from dev + **8 added by code review**) |
| `npx vitest run` (full) | **1113 passed / 154 files**, 0 failed |
| `npm run typecheck` (`tsc -b`) | rc 0 |
| `npm run lint` (`eslint --max-warnings=0` + stylelint) | rc 0 |
| `npx playwright test image-viewer-zoom image-viewer-containment` (4 projects, post-repair) | **38 passed, 2 skipped** — includes the new focus-handoff test; `image-viewer-containment.spec.ts` still **zero edits** (skips pre-existing: mobile projects skip the horizontal-scroll case) |
| `npx playwright test catalog-detail` (post-repair, **no** `--update-snapshots`) | **24 passed, 4 skipped** — the 4 regenerated `*image-viewer-open-*` baselines still match, confirming the review repairs carry **zero visual delta** |
| `npx playwright test image-viewer-zoom --update-snapshots` (dev round) | 20 passed, 8 new baselines |
| `npx playwright test catalog-detail.spec.ts` (dev round, pre-regen triage) | 20 passed / **exactly 4 failed** — only the `*image-viewer-open-*` set; every other catalog-detail baseline unaffected |
| `infra/scripts/check-all.sh` | rc 0, all 16 stages green — log `.hermes/run-logs/check-all-53-2-laura-verify-20260729_154218.log`. **Run by the controller BEFORE the review repairs.** Product code changed afterwards, so the full gate MUST be re-run before merge; the targeted suites above cover the changed paths in the meantime. |

**Baseline triage before regeneration** (repo rule: classify before `--update-snapshots`). All **four** regenerated diff images were read — the original record said "both", which did not match the four baselines actually regenerated. Each shows **exactly two changed regions**: the close button's 40→44 px growth and the new toolbar. Independently re-confirmed during code review by row-band analysis (close button y≈30–73, toolbar y≈638–692, nothing else moved), which also refutes the reviewer concern that the Layer-1 restructure might have shifted the image. No other pixel moved, and the 20 non-viewer catalog-detail baselines stayed green — classification **stale-baseline** (intended change), not `deterministic-fail`. Per V-15 the light/dark viewer chrome being visually identical is **correct**: `--color-gallery-control` is theme-invariant by design because the controls float over arbitrary photography; the dark baselines differ only where the 40 % scrim composites over a dark backdrop.

### File List

| Path | Action |
|---|---|
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` | **UPDATE** — three-layer structure, zoom/pan/pinch/double-tap, toolbar, keyboard, load/error observation, safe-area, 44 px close |
| `apps/web/src/modules/catalog/components/imageViewer/zoom.ts` | **NEW** — pure clamp/zoom arithmetic |
| `apps/web/src/modules/catalog/components/imageViewer/zoom.test.ts` | **NEW** — 25 unit tests against injected geometry |
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.test.tsx` | **UPDATE** — extended with 26 tests (18 dev + 8 code-review regression guards); the 5 original blocks untouched |
| `apps/web/src/locales/en.json` | **UPDATE** — 4 keys (1043 → 1047) |
| `apps/web/src/locales/pl.json` | **UPDATE** — same 4 keys (1043 → 1047), key sets identical |
| `apps/web/tests/visual/image-viewer-zoom.spec.ts` | **NEW** — targeted pl-PL coverage + AC-6 + geometry + the code-review focus-handoff test |
| `apps/web/tests/visual/__snapshots__/image-viewer-zoom.spec.ts/*.png` | **NEW ×8** — 2 states × 4 projects. **Sign-off required per PNG**: `_check-baseline-review.mjs` matches `--diff-filter=AM`, so additions are gated exactly like modifications. |
| `apps/web/tests/visual/__snapshots__/catalog-detail.spec.ts/catalog-detail-image-viewer-open-{desktop,mobile}-{light,dark}.png` | **UPDATE ×4** — sign-off required per PNG |
| `_bmad-output/implementation-artifacts/53-2-mature-lightbox-implementation.md` | **NEW** — this record (untracked; the original File List said UPDATE) |
| `_bmad-output/implementation-artifacts/deferred-work.md` | **UPDATE** — 4 deferred code-review findings |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | **UPDATE** — status transitions |

**Untouched, mechanically proven** (`git status --porcelain` over these paths returns zero lines): `apps/web/src/ui/dialog.tsx`, `apps/web/index.html`, `apps/web/src/routes/share/$token.tsx` (`AnonymousImage` / `LazyAnonymousImage` / `shareBlobCache`), `apps/web/src/modules/catalog/components/ModelGallery.tsx`, `imageViewer/types.ts` (`ImageRenderer` / `ImageSource` contracts), `imageViewer/index.ts`, `apps/web/tests/visual/image-viewer-containment.spec.ts`, `apps/web/package.json`, `apps/web/package-lock.json`.

**Invariant greps (AC-8):** `user-scalable` → 1 hit, in a comment stating it is *not* used. `left-1/2` / `-translate-x-1/2` in the viewer module → 2 hits, both comments (the pre-existing E48.1 rationale and the new toolbar note explaining the deliberate avoidance). Bare `vh` → comments only; every live viewport-relative height is `dvh` (`h-[95dvh]`, `top-[2.5dvh]`, `max-h-[calc(95dvh-5rem)]`). The `:260` geometry string is byte-identical.

---

## 10. Change Log

- **2026-07-29 — created** by native `bmad-create-story` (Create action) at `main` @ `a3aaf35`, Claude Opus 5, repo-local, under controller-granted authorization for this artifact only. Epic 53 was already `in-progress`; `53-2-mature-lightbox-implementation` flipped `backlog` → `ready-for-dev` in `sprint-status.yaml`. **`G26-LIB` was NOT closed and no physical Android evidence is claimed.**
- **2026-07-29 — implemented** (`ready-for-dev` → `in-progress` → `review`) by native `bmad-dev-story`, Claude Opus 5, repo-local, on branch `feat/E53.2-mature-lightbox` cut from `main` @ `a3aaf35`. Routed via native `bmad-help` → `_bmad/_config/bmad-help.csv` row 28 (DS; `preceded-by bmad-create-story:validate`, which PASSed; `required=true`); customization resolved via `resolve_customization.py` (empty prepend/append, `persistent_facts = project-context.md`). `baseline_commit` already present in frontmatter and **preserved**, not overwritten. All 44 task/subtask boxes checked; AC-1…AC-10 addressed. **`G26-LIB` REMAINS OPEN; no physical Android Chrome evidence was collected and no gesture-quality claim is asserted, simulated or inferred; `architecture.md` Decision BA untouched.** Four numeric/behavioural decisions are recorded rather than applied silently, per D-4's *"changing it silently is not [fine]"*: (a) **`DOUBLE_TAP_SCALE = 2.25`** rather than 2.0, taking D-4's explicit "snap to the nearest step boundary" escape so every double-tap-reachable state is also button-reachable (AC-2); (b) **`resolveMaxScale = max(4, natural/rendered)`** — the only reading of D-4 under which a 4:1/8:1 panorama gets native-pixel inspectability *and* a small source keeps a usable envelope; (c) **close target 44 px (`h-11 w-11`)** rather than 48, V-7 permitting both and 44 being the token's own value; (d) **three new constants** `TAP_MOVE_TOLERANCE_PX = 10`, `DOUBLE_TAP_WINDOW_MS = 300`, `DOUBLE_TAP_SLOP_PX = 44`, each contract-pointed in code, with the tap-tolerance consulted **only** on the scale>1 path so TB-043's four-cell matrix at scale 1.0 is behaviourally untouched. **Four defects were caught by measurement, two of which would have shipped broken:** the D-6 capture-phase listener never attached because Base UI **portals** the popup and `frameRef.current` was still `null` on the first effect pass (toolbar would have been permanently disabled **in production**, not merely in jsdom — fixed with a callback ref + `frameEl` effect dep); the `load` handler re-derived readiness from `img.complete` instead of trusting the event; Chromium rejects object literals in `TouchEvent`'s `touches`/`changedTouches`; and `window.scrollTo` is not a valid scroll-lock probe because `overflow: hidden` still permits programmatic scrolling. **V-2's open question is now measured, and it corrects the story:** real Chromium locks **`<body>` alone** while jsdom sets both `<html>` and `<body>`, so both AC-6 tests were rewritten **element-agnostically** to assert the `EXPERIENCE.md:234` contract (scrolling prevented while open via a **real wheel gesture**; document exactly restored after) instead of a platform detail — with a proven-scrollable precondition and a proven-not-already-hidden pre-check so neither assertion is vacuous. **No second scroll lock was built** (D-9), **no dependency added** (`package.json`/`package-lock.json` byte-identical), and the standing `image-viewer-containment.spec.ts` passes with **zero edits**. **Reversal trigger R3 is surfaced, not silently resolved:** 668 raw added lines (over ≈450) but **367 net added CODE lines** excluding comments/blank (inside `spec-e53-1:154`'s own +305–435 band) and **zero** gesture-math dependencies — see § 9 for the full table and the reasoning for proceeding. Two cross-story items raised rather than fixed here: the `catalog.image_viewer.trigger_label` = `Powiększ` collision (now demonstrated in code, since the new spec must scope its Polish matcher inside `image-viewer-toolbar`) → **Story 54.1**; and the viewer's inline error *treatment* + load/error test matrix → **Story 53.3** (D-6/D-10). Baselines: 8 new `image-viewer-zoom` PNGs and 4 regenerated `catalog-detail-image-viewer-open-*` PNGs, each diff read before acceptance and classified **stale-baseline** (only the 40→44 px close growth and the new toolbar changed; the other 20 catalog-detail baselines stayed green). **Not an Ezop signature, not human review.** Nothing committed, pushed, merged or deployed by this run.
- **2026-07-29 — validated** by native `bmad-create-story` (Validate action, `checklist.md`) at the same commit. Repairs applied during validation: (1) § 0 entry-gate block added so `ready-for-dev` cannot be misread as authorization; (2) V-1 / V-2 added after reading `ui/dialog.tsx` and the installed `@base-ui/*` sources — `spec-e53-1`'s Radix attribution and its 25–40-LOC scroll-lock estimate were both wrong, and acting on either was a live wheel-reinvention / wrong-library disaster; (3) V-3 added — `env(safe-area-inset-*)` is inert without `viewport-fit=cover`, resolved by D-5 without an app-wide meta change; (4) V-4 added — `catalog.image_viewer.loading` is an orphan key, so `EXPERIENCE.md:259` cannot be assumed satisfied; (5) V-5/D-2 added — the closed `G26-UXGATE` spine, which `spec-e53-1` never cites, is more prescriptive than the epic sketch and makes the always-mounted toolbar a hard structural requirement; (6) D-4 given concrete constants with a contract each, per the project-context magic-constant rule; (7) D-6 resolved the load/error observation problem with a capture-phase listener so no renderer contract is touched; (8) D-8 recorded the `Powiększ` collision instead of silently renaming a shipped key; (9) D-10 added to stop 53.2 absorbing 53.3's test contract; (10) V-18 added after reading the installed `react-dom` 19.2.6 bundle — `touchstart`/`touchmove`/`wheel` are registered `passive: true`, so `preventDefault()` from a React touch handler is a no-op and a naive pinch/pan implementation ships broken while tests stay green; (11) V-19 added to separate element-scoped `touch-action` (permitted, required) from document-wide `user-scalable=no` (forbidden), which a reviewer would otherwise conflate; (12) V-20 named the four new `image-viewer-*` testids so Story 53.3 can be written against a known contract; (13) Dev Notes gained the jsdom-has-no-layout warning (a pan-clamp test against all-zero rects passes trivially), the Visual Coverage Contract trap if the toolbar is extracted into `ui/`, and the reduced-motion gate. **Validation verdict: PASS.** All 23 cited planning/UX anchors and all 21 cited code anchors were re-checked mechanically at `a3aaf35`; no decision-needed or blocking issue remains inside the story. The one open item is external to the story and unchanged: `G26-LIB` (§ 0).
- **2026-07-29 — reviewed** (`review` → `in-progress`) by native `bmad-code-review`, Claude Opus 5, repo-local, on the working tree at `feat/E53.2-mature-lightbox` (baseline `a3aaf35`). Three parallel adversarial layers ran and all three returned (`failed_layers` empty): Blind Hunter (`bmad-review-adversarial-general`), Edge Case Hunter (`bmad-review-edge-case-hunter`) and Acceptance Auditor (`review_mode = full`, against this file). Triage: **13 patch (all applied), 4 defer, 10 dismissed, 1 decision-needed (resolved inside the pass)**. Controller arbitrated Step 4 for this headless run — apply every in-scope patch; do not accept an over-threshold R3 silently. **Eight real code defects were fixed, each with a new regression test**, the two most serious being: (a) `+`/`-`/`0` cancelled the browser's own `Ctrl`/`Cmd` page-zoom shortcuts, a **WCAG 1.4.4 regression introduced by an a11y story**, now guarded on `ctrlKey`/`metaKey`/`altKey` with the `←`/`→` path left byte-identical; and (b) a zoom control that disables itself dropped focus to `<body>` inside the focus trap — **measured in real Chromium with a throwaway Playwright probe rather than assumed**, since Base UI's focus manager does not recover it — now handing focus to the sibling still live, asserted in `image-viewer-zoom.spec.ts` because jsdom does not model the blur at all. The other six: the polite live region announced an unasked-for "Zoom 100%" per photo while never announcing its own loading text (an `aria-live` region does not announce content it is INSERTED with, and Base UI portals the subtree in at once) — announcement now lives in state, is written from an effect and fires only on a real zoom change, with **zero visual delta confirmed against the existing baselines**; a resting third finger lifting mid-pinch permanently converted the gesture to a pan, and a coalesced two-finger `touchstart` left no drag origin so post-pinch panning was dead; an `activeIdx` change left the pinch snapshot armed so the previous photo's zoom was re-applied to the new one; a resize while the image was unmeasurable demoted a panorama's 20× ceiling to 4× and dragged the user's zoom down with it; `complete` alone armed the controls over an already-failed cached image; and a tap swallowed by the toolbar or a thumb left `lastTapRef` armed, so a later single tap read as a double-tap. **Reversal trigger R3 was the one `decision-needed`, and it was resolved by fixing the MEASUREMENT, not the code.** The original § 9 table was computed from wrong `numstat` inputs, and an intermediate recount produced during this review round was also wrong — both because a line-prefix regex misclassifies the **continuation** lines of this file's JSX `{/* … */}` block comments as code. With a comment-state-aware count (method now stated in § 9 and reproducible): pre-review **346** net added CODE lines, post-repair **399**, against R3's ≈450 — under on both, and inside `spec-e53-1:154`'s own `+305–435` band; the dependency half of R3 is zero (`package.json`/`package-lock.json` byte-identical). **No product code was shaved to fit the threshold.** Five record-accuracy defects the Acceptance Auditor caught were also corrected rather than left standing: understated vitest counts, the wrong R3 inputs, "both diff images" against four regenerated baselines, the **8 new** `image-viewer-zoom` PNGs also needing `baseline-reviewed:` sign-off (`_check-baseline-review.mjs` matches `--diff-filter=AM`), and this file being NEW rather than UPDATE. Four findings deferred to **Story 53.3** / a future `bmad-correct-course` and written to `deferred-work.md` with evidence: the never-mounted-`<img>` share path, the missing inline error treatment, the double-tap chrome flash (unfixable without violating AC-3's TB-043 guarantee), and the untested double-tap window/slop boundaries. Ten findings dismissed with reasons recorded in § Review Findings so they are not re-raised — including three that were spine-sanctioned rather than defects (touch-only pan per `EXPERIENCE.md:301`, 40 px zoom controls per `DESIGN.md:176`, the `Powiększ` collision per D-8) and one refuted by measurement (the Layer-1 restructure did not move the image: all four regenerated baselines change in exactly two row bands). Verification re-run after the repairs: **vitest 56 imageViewer / 1113 full, 0 failed**; `typecheck` rc 0; `lint --max-warnings=0` rc 0; Playwright **38 passed / 2 skipped** on `image-viewer-zoom` + `image-viewer-containment` (the standing suite still with **zero edits**); Playwright **24 passed / 4 skipped** on `catalog-detail` with **no** `--update-snapshots`, proving the repairs regenerate nothing. **`infra/scripts/check-all.sh` (rc 0, all 16 stages, log `.hermes/run-logs/check-all-53-2-laura-verify-20260729_154218.log`) predates these repairs — the full gate MUST be re-run by the controller before merge.** **`G26-LIB` REMAINS OPEN; no physical Android Chrome evidence was collected and no gesture-quality claim is asserted, simulated or inferred; `architecture.md` Decision BA untouched; no dependency added; no forbidden file touched.** Story moves to `in-progress` (not `done`) because the merge gate is not discharged: the full gate needs a re-run and the `baseline-reviewed:` sign-off lines for all 12 PNGs do not exist yet, since nothing is committed. **Not an Ezop signature, not human review.** Nothing committed, pushed, merged or deployed by this run.
- **2026-07-29 — controller closeout** (`in-progress` → `done`) by Laura/controller after every controller-owned gate called out by native review was discharged: independent Aider review over the repaired non-PNG diff returned **APPROVE** (`AIDER_REVIEW_RC=0`, log `.hermes/run-logs/aider-review-53-2-20260729_162905.log`); full `infra/scripts/check-all.sh` reran after review repairs and returned **all green / CHECK_ALL_RC=0** (`.hermes/run-logs/check-all-53-2-final-20260729_163004.log`); R3 was independently sanity-checked as still under the ≈450 net-code threshold (controller counter: 430 net added code lines, no dependency change); all 12 changed/added PNG baselines are covered by `baseline-reviewed:` lines in the commit message. **`G26-LIB` remains OPEN; no physical Android Chrome evidence was collected; `architecture.md` Decision BA remains untouched; this is not an Ezop/human signature.**
