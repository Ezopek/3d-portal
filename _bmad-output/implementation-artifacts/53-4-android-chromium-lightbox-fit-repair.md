---
baseline_commit: 36edc9c6483dd8099d8c6ed1f0b734c15cd0700f
---

# Story 53.4 — Android Chromium lightbox fit-to-frame repair (FR26-VIEW-1, NFR26-VISUAL-1)

Status: done — **and `done` means exactly what it meant for Story 53.3: the CODE-SIDE MERGE GATE is discharged and the branch is READY TO COMMIT + FF-MERGE. NOT committed, NOT merged, NOT pushed, NOT deployed, NO post-deploy smoke, and the § 9 physical Brave retest is NOT REQUESTED YET.** Those remaining steps are controller-owned and still **owed** — see § 6 T6/T7 and § 12 "Closeout posture". **`G26-LIB` STAYS 🔓 OPEN, `epic-53` STAYS `in-progress`, Story 53.3 § 11 STAYS BLANK, and this story's § 9 STAYS EMPTY.**

<!-- Created 2026-08-01 by native `bmad-create-story` (Create action) at `main` @ `36edc9c`, from the Epic E53 sketch (`epics.md:4581-4585`) and SCP `sprint-change-proposal-2026-08-01-e53-android-lightbox-fit-defect.md`. -->
<!-- Validated 2026-08-01 by native `bmad-create-story` (Validate action / `checklist.md` pass) at `main` @ `36edc9c`, in a second, separate session after the create/validate session was killed. The corrections that pass applied are listed in § 11, which is the validation record of record. -->

- **Epic:** E53 — Mature mobile lightbox (Initiative 26 — Catalog Discovery). Independent parallel track, **gated on `G26-LIB`** (`epics.md:4565-4567`).
- **Author:** Claude Opus 5, native `bmad-create-story`, repo-local. **NOT** an Ezop signature and **NOT** human review.
- **Created:** 2026-08-01 at `main` @ `36edc9c` (`origin/main` in sync; working tree carries only the three BMAD planning/status files this change and its predecessor SCP produced).
- **Trigger:** a shipped-defect report backed by **physical device evidence** (three operator screenshots), routed here by native `bmad-correct-course`. The operator's entire contribution is **evidence collection**. It is not sign-off, not code review, and not approval of anything in this file.
- **Authorization posture:** planning artifact only. Creating and validating this file was authorized by Laura/controller. **That is not authorization to start dev.** See § 0.

---

## 0. ⛔ ENTRY GATE — read before `bmad-dev-story`

**`G26-DEVGO` is 🔓 OPEN.** `architecture.md:3386`: *"planning proceeds; code starts only after create+validate and controller confirmation of that specific ready story."* `ready-for-dev` above is the BMAD artifact status, **not** a green light. The controller's create/validate authorization for this pass was explicit that dev-story is a **separate** grant. Do not open a branch, do not touch `apps/`.

**`G26-LIB` is 🔓 OPEN and this story does not move it — not by one line.** `G26-LIB` closes on a non-provisional Story 53.1 recommendation **plus physical Android *Chrome* evidence** (`implementation-readiness-report-2026-07-26.md:205`). The evidence that triggered this story is:

| | |
|---|---|
| **Browser** | **Brave 1.92.144** (Chromium 150.0.7871.186). Chromium-family, but a **different browser** with its own shields, chrome and viewport behaviour. |
| **Kind** | **Defect** evidence — a thing is broken. `G26-LIB` wants **gesture-acceptance** evidence — a person judging pinch/pan quality. |

It is the **wrong browser** *and* the **wrong kind** of evidence. Nothing produced by this story may be cited toward `G26-LIB`, toward Story 53.3 § 11 (which stays **entirely blank**), or toward any gesture-quality claim.

**The two retests are different questions and must never be conflated:**

| Question | Browser | Closes |
|---|---|---|
| Is the fit-to-frame defect repaired? | **Brave** on the reporting device | This story's AC-9 |
| Are the gestures acceptable to a person? | **Chrome for Android** | `G26-LIB` (not this story) |

**`epic-53` stays `in-progress`.** It now has an open story as well as an open gate, and **Story 53.4 closing closes neither `epic-53` nor `G26-LIB`.**

**Evidence handling.** The three PNGs live at `/mnt/download/` on Fenrir with controller working copies in `/tmp/3d-portal-android-evidence/` — **outside the repository and deliberately never committed**. The device-identity screenshot displays the phone's **IMEI**; it is not transcribed into this or any other repo artifact. If device provenance is ever needed in-repo, record **model + OS build only**.

---

## 1. Story statement

**As** a member inspecting model photos on a physical Android phone,
**I want** the fullscreen lightbox to actually fit the photo — and its own controls — inside the part of the screen I can see, at the reset/minimum scale, before I zoom anything,
**so that** `FR26-VIEW-1`'s inspectability promise is true on the device it was written for; **and, as the next agent who will trust this suite,** I want the story to state *why a green containment suite could not see this*, so the same class of defect cannot ship again behind the same green gate.

---

## 2. `VERIFY-AT-CREATE-STORY` — traced against shipped code at `36edc9c`

The epic sketch's `VERIFY-AT-CREATE-STORY` asks for two things: **the shipped geometry as it actually stands on `main`**, and **what the containment suite does and does not measure.** Every row below was read or measured *this run*. **Rows V-2, V-4, V-5, V-11 and V-12 correct or complete assumptions a naive reading of the sketch or the SCP would produce.**

| # | Fact | Evidence at `36edc9c` | Consequence for 53.4 |
|---|---|---|---|
| **V-1** | **The shipped geometry, verbatim.** | `ImageFullscreenViewer.tsx:870` — `className="h-[95dvh] w-[98vw] max-w-[calc(100%-2vw)] left-[1vw] top-[2.5dvh] translate-x-0 translate-y-0 p-0 outline-none bg-background/95 backdrop-blur-sm sm:max-w-[calc(100%-2vw)]"`. Image: `:938` — `max-h-[calc(95dvh-5rem)] max-w-full object-contain`, inside the `absolute inset-0` transform layer (`:914-921`). | This is the entire box under investigation. Four viewport-relative quantities (`98vw`, `1vw`, `calc(100%-2vw)`, `95dvh`) plus one percentage cap, and the defect is an asymmetry between the left and right insets. Read the whole rule set before changing any part of it. |
| **V-2** | 🛑 **The deployed build is NOT `main` HEAD — but the viewer sources are byte-identical to it.** | `infra/.last-deploy-sha` = `1906498064e49cb49f57208e4ec93faf91865b97`. HEAD is `36edc9c`. The two commits in between (`be0b762`, `36edc9c`) are both `docs:` and were correctly skipped by the range-based deploy gate. **Measured this run:** `git diff --quiet 1906498 36edc9c -- apps/web/src apps/web/tests apps/web/index.html` → **exit 0, identical.** | The SCP correctly flags that the evidence *records* no build string (§ 2.2). This row supplies what can be established without one: **whatever build the phone was on, the viewer source it ran is the source on `main` today.** So (a) reproduce against HEAD — do **not** check out `1906498` to "match production"; (b) AC-1 still requires recording the **actual** deployed version string observed at repro, because "identical sources" is an inference about code, not an observation of the running artifact. |
| **V-3** | **Fit is delegated to CSS, not to a measured fit ratio.** | `zoom.ts:13` — `MIN_SCALE = 1`. There is no computed fit-to-frame factor anywhere; "fit" is whatever `object-contain` + `max-h-[calc(95dvh-5rem)]` + `max-w-full` produce inside the frame. | The defect is therefore **not** an arithmetic bug in `zoom.ts` — the clamp maths never gets a chance to be wrong at scale 1.0. It is a **box** problem. This is a strong prior, not a conclusion: the story still owns the diagnosis. |
| **V-4** | 🛑🛑 **Two shipped comments encode mutually inconsistent premises about which browser API reports which viewport — and the containment gate rests on one of them. Nothing in the repo consults `window.visualViewport` at all.** | (a) `ImageFullscreenViewer.tsx:840-848` asserts *"`left: 50%` resolves against … mobile Chrome's LAYOUT viewport … while `w-[98vw]` resolves against the VISUAL viewport."* (b) `image-viewer-containment.spec.ts:265-268` asserts the pairing the other way round for the measurement APIs: *"`documentElement.clientWidth` tracks the VISUAL viewport; `innerWidth` tracks the layout viewport."* (c) **Measured this run:** `grep -rn "visualViewport" apps/web/src apps/web/tests` → **zero hits.** | This is the single most consequential row in the table. `assertContained` (`:264-295`) judges *every* containment claim in the suite against `document.documentElement.clientWidth`, on the strength of comment (b). **If (b) is wrong, the suite has been asserting containment against the wrong box the whole time** — which would be a complete, mechanical explanation of AC-3's question. Per CSS/CSSOM as normally read, `vw` resolves against the **initial containing block** (= layout viewport) and `document.documentElement.clientWidth` reports the **layout** viewport, while `window.visualViewport.width` reports the visual one — i.e. **(a) and (b) are each suspect, in opposite directions.** **53.4 must settle this by measurement, in a real browser and on the device, and must not settle it by citation — including by citing this row.** |
| **V-5** | 🛑 **"Nobody tested horizontal overflow" is NOT the explanation. That test exists, runs on `mobile-*`, and is green.** | `image-viewer-containment.spec.ts:128-140` (`forceHorizontalPageOverflow`, which injects `width: calc(100vw + 200px)` and *polls until `scrollWidth > clientWidth`*) and `:325-331` (`test("fullscreen viewer stays reachable when the page overflows horizontally")`). It calls `assertContained(page, { overflow: true })` **and** `assertDismissible(page)`. | The obvious hypothesis is pre-refuted. Whatever the suite is blind to is **subtler** than a missing case: either the emulated environment cannot *produce* the divergence the real device has, or the assertion measures the wrong box (V-4), or the real condition is not page overflow at all. AC-3 is not discharged by "we added the missing overflow test" — that test is already there. |
| **V-6** | **The Playwright matrix is 4 fixed projects of Pixel 5 *emulation*; `mobile-*` is never Android.** | `tests/visual/playwright.config.ts:18-35` — `desktop-light`, `desktop-dark`, `mobile-light`/`mobile-dark` = `devices["Pixel 5"]`. `locale: "pl-PL"`, `timezoneId: "Europe/Warsaw"`. `project-context.md:110` states the matrix is fixed. | Placing a test in `tests/visual/` buys light+dark and desktop+mobile for free. **Adding a fifth project is Ask First** (§ 5, carried from 53.3 V-3). And every "mobile" result in this repo is a desktop Chromium with an emulated viewport — the exact gap this defect walked through. |
| **V-7** | **There is no `viewport-fit=cover`, and no `user-scalable=no`.** | `apps/web/index.html:5` — `<meta name="viewport" content="width=device-width, initial-scale=1.0" />`. Measured this run. | Consequences, both live: (a) every `env(safe-area-inset-*)` in the viewer (`:1021`, `:1068`) resolves to **0** today (53.2 D-5 designed for exactly this), so safe-area is *not* currently a candidate cause; (b) **Android 15+ / Android 17 edge-to-edge behaviour is a real H3 candidate** and interacts with this meta. **Adding `viewport-fit=cover` is an app-wide change and is Ask First** (§ 5). |
| **V-8** | **The `max-w-[calc(100%-2vw)]` counterweight is, by its own comment, unexercised by CI.** | `ImageFullscreenViewer.tsx:853-863`: *"It is inert wherever the gutter is 0 (`100% == 100vw`, so the cap equals `98vw`), which is why headless CI cannot exercise it — Chromium here uses overlay scrollbars (measured: `clientWidth == innerWidth == 100vw == 1280`)."* | An untested counterweight, written to defend precisely the right-edge overflow that is now reported, is a good place for a bug to live (SCP H2). Note also what that parenthetical *measures*: on the CI browser `clientWidth == innerWidth`. **That equality is the emulation artefact V-4 and V-5 both point at** — where the two are equal, no divergence of any kind is representable. |
| **V-9** | **The clipped toolbar cannot be explained by image sizing — it is a sibling of the chrome layer, anchored to the frame, outside the transform layer.** | `ImageFullscreenViewer.tsx:1068` — `className="pointer-events-none absolute inset-x-0 bottom-[max(1rem,env(safe-area-inset-bottom))] flex flex-col items-center gap-2"`, centred with `inset-x-0` + `items-center` (single reference box, never `left-1/2`), containing the always-mounted toolbar at `:1091-1126`. | Corroborates the SCP's load-bearing observation mechanically: a toolbar centred on `inset-x-0` renders off-screen only if the box it is inset against is itself off-screen. **So `object-contain` fitting the wrong box (SCP H4) is insufficient alone** — it would explain the photo and not the toolbar. Any candidate root cause must explain **both**, or it is incomplete. |
| **V-10** | **`ui/dialog.tsx`'s base classes are what the viewer's `className` is overriding — including the centering the E48.1 invariant bans.** | `ui/dialog.tsx:53-59` — `DialogPrimitive.Popup` ships `fixed top-1/2 left-1/2 … -translate-x-1/2 -translate-y-1/2 … max-w-[calc(100%-2rem)] … sm:max-w-sm`. The viewer overrides all five (`translate-x-0 translate-y-0 left-[1vw] top-[2.5dvh]`, plus **both** `max-w-` and `sm:max-w-`). | Two consequences. (a) The override is load-bearing and **partially reintroducible by accident** — dropping `sm:max-w-[calc(100%-2vw)]` alone would silently restore `sm:max-w-sm`. (b) **`ui/dialog.tsx` is Ask First** (`architecture.md:3375`); blast radius is every dialog in the app. If the root cause lands there, **stop and ask** (§ 5). |
| **V-11** | 🛑 **The locale key sets are 1050/1050 today, not the 1048 Story 53.3 recorded.** | Measured this run: both `en.json` and `pl.json` flatten to **1050** keys; the 14 `catalog.image_viewer.*` keys are unchanged. Stories 54.1/54.2 moved the count after 53.3 was written. | Any AC or check that pins a key count must use **1050 → 1050** as its baseline. **This story is expected to ship ZERO new keys** — a geometry repair has no copy. If the fix somehow demands copy, that is a scope signal worth surfacing, not a key to add quietly. |
| **V-12** | 🛑 **Seven E53 residuals are open in the ledger and NONE of them belongs to this story.** | `deferred-work.md`, all `status: OPEN`: the `/share` DN-4 in-viewer-navigation watchdog gap (`:294-296`); the mounted-and-hung unreported stall (`:297-300`); the failure retry dead-end (`:266-269`); the X-axis-only double-tap slop pin (`:270-273`); the `sources`-swap-at-unchanged-`activeIdx` carry-over (`:274-277`); the `error → error` silent announcement (`:285-288`); and the double-tap chrome flash (`:225-227`, which needs a **53.2 AC-3 amendment via `bmad-correct-course`**, never an in-story patch). | SCP § 5.6 is binding: **Story 53.4 is the fit-to-frame defect and nothing else.** These stay owed to a separate follow-up story. Touching one here is scope creep even if the file is already open in the editor. |
| **V-13** | **The visual suite is a *layout* gate, and that is exactly what this story needs — but a geometry repair WILL move pixels.** | 54.2 proved (`deferred-work.md:259-261`) that Playwright's default `toHaveScreenshot` `threshold: 0.2` absorbs a 49-level greyscale shift, so baselines do **not** gate colour; a computed-contrast probe (`tests/visual/a11y-contrast-gate.spec.ts`) was added for that. A **box-geometry** change is the one class this threshold does catch. | Expect real baseline churn on any viewer-geometry change, and expect it to be **meaningful**. Triage every failure (`stale-baseline` / `deterministic-fail` / `flake-candidate`) before regenerating anything, and carry a `baseline-reviewed:` line per changed PNG (`project-context.md` § UI quality gates). **No blanket `--update-snapshots`** (§ 5). |

---

## 3. Design decisions

### D-1 — This is one bugfix, worked as a strict sequence, and the sequence is the deliverable

The epic sketch fixes the order and it is not decorative: **(1) reproduce deterministically → (2) failing regression + the suite-blindness explanation → (3) minimal root-cause fix → (4) inspectability preserved → (5) deploy → (6) request fresh physical retest.**

Steps 1 and 2 come **before** any product-code edit because the defining fact of this defect is that a green suite could not see it. A fix landed first, with a test written afterwards to match it, would reproduce the exact failure mode this story exists to close: a test that agrees with the code rather than one that constrains it. `AGENTS.md` § "Execution discipline" already requires red → green → refactor and *reproduce → narrow → root-cause → fix → verify*; this story makes both mechanically checkable in AC-1/AC-2.

### D-2 — What "deterministic" means, and the honest fallback if it is unreachable

**Deterministic = an identified, written-down viewport/browser condition that reproduces the overflow on demand.** Never *"sometimes on a phone"*. Concretely, the record must state: the surface (`/catalog/$modelId`, viewer open, reset scale), the device/browser/OS build, the deployed version string, and **the condition** — the specific property of the environment (measured, e.g. a divergence between two viewport metrics; or a browser behaviour) under which the right edge overflows.

**Preference order for where the repro lives:**

1. **In the automated suite** — a Playwright case that fails on today's `main`. Strongly preferred; it is what makes step 2 possible at all.
2. **A written manual protocol** — exact, numbered, re-runnable steps with the measurement to take at each one, *if and only if* the condition provably cannot be produced in Playwright (which is a plausible outcome given V-5 and V-8, and would itself be a first-class finding).

**If the outcome is (2), say so plainly in the record and state what blocks (1).** A story that quietly downgrades from an automated repro to "we looked at it on the phone" has not discharged AC-1. Note that (2) does **not** discharge AC-2 either — see D-3.

### D-3 — The regression must fail for the *right* reason, and this repo has already been burnt by the alternative

AC-2 asks for a test that **fails before the fix and passes after**. The failure mode to avoid is a test that **asserts the defect** rather than the **contract** — i.e. one that only fails today because it was written against today's broken geometry, and which would go green against a fix that merely moved the problem.

This is not hypothetical here. The DN-4 entry (`deferred-work.md:295`) records exactly this trap, in this component: *"no test in the current suite can exhibit the ordering … the regression pin must be written in the hooks-in-the-viewer's-fiber shape or it will pin a stand-in … writing one against the current probe would assert the defect rather than the contract."*

**So the new test must state, at the assertion, the contract it encodes** — "no part of the viewer box extends beyond the region the user can see, at reset scale" — and not "the right edge equals *X*". If the contract cannot be expressed without first settling V-4, then settling V-4 is a prerequisite of the test, not an afterthought.

**If the condition proves un-producible in Playwright (D-2 case 2):** AC-2 is then met by a **vitest or Playwright test of the corrected geometry rule itself** — whatever the root cause turns out to be, the repair changes something checkable — plus an explicit statement that the *end-to-end* condition has no automated pin and why. Recording that gap is mandatory; it is a ledger entry, not a footnote.

### D-4 — Settling V-4 is in scope, and correcting a wrong assertion premise is allowed *once it is proven wrong*

Story 53.3 § 5 carried a blanket **"Never rewrite an existing test."** That rule was right for a story extending a standing suite. It is **narrowed here, deliberately and only here**, because V-4 raises the possibility that `assertContained`'s central premise is inverted — and a suite that measures the wrong box is not a suite this story may leave standing while claiming AC-3.

**The narrowed rule:**

- Changing an existing assertion in `image-viewer-containment.spec.ts` is permitted **only** when the change is forced by a **measurement** that proves the current premise wrong, and the measurement is recorded in the story with the numbers it produced.
- Any such change is a **contract correction** and must be called that in the record, in the commit message, and in a comment at the assertion. It may **not** be made silently, opportunistically, or "while nearby".
- The four pre-53.3 test bodies (`:305-346`) and the 53.3 additions stay **byte-identical** otherwise.
- A *failing* legacy assertion that has **not** been proven wrong is still a **finding to surface**, never a line to edit.

**Rejected alternative:** leaving the suite untouched and describing the blindness in prose only. That satisfies the letter of AC-3 and none of its purpose — the next story would inherit the same false green.

### D-5 — Minimal and root-cause means *the overflowing box stops overflowing*, not *the overflow stops being visible*

The sketch says "not a clamp that hides the geometry". Made concrete — **these are rejected as the primary repair**, in each case because they suppress the symptom while leaving the box wrong:

| Rejected | Why |
|---|---|
| `overflow-x: hidden` on the dialog, viewer root or `body` | Hides the clipped toolbar rather than bringing it back into view. The user still cannot press `−`. |
| Shrinking the image (`max-w-[90%]`, a smaller `max-h`) | Treats the photo as the overflowing thing. V-9 shows it is not — the **toolbar** is clipped too. |
| Capping `maxScale`, or lowering `BASE_MAX_SCALE` | Trades away exactly the inspectability the epic exists to deliver. See D-6. |
| Re-centering with `left-1/2` + `-translate-x-1/2` | Reintroduces the mixed-reference-box pattern Story 48.1 removed. **Banned invariant** (`architecture.md:3372`). |
| A media query or user-agent branch for Brave/Android | Encodes a browser name instead of the geometry rule. The next Chromium build inherits the bug. |

**Accepted shape:** whatever the diagnosis, the repair changes *which box the geometry resolves against, or the rule that sizes it*, so that the viewer's own boxes are inside the region the user can see — and the failing regression from AC-2 turns green **because of that**, verified by re-reading the measurement, not by the test merely passing.

### D-6 — Inspectability above 1.0 is a hard invariant, stated as concrete checks

`FR26-VIEW-1` exists so a panoramic photo is inspectable on a phone. A fix that fits the image by weakening zoom is a regression dressed as a repair. The following must all still hold after the fix, and AC-5 makes them checkable:

- `MIN_SCALE = 1`, `BASE_MAX_SCALE = 4`, `ZOOM_STEP = 1.5`, `DOUBLE_TAP_SCALE`, and `resolveMaxScale`'s `max(BASE_MAX_SCALE, naturalWidth / renderedWidth)` semantics are **unchanged** (`zoom.ts`). Changing any of them is **Ask First** (§ 5, carried from 53.3).
- The three toolbar controls stay **mounted, visible, never `aria-hidden`, and outside both the transform and chrome layers** (`DESIGN.md:299`, `EXPERIENCE.md:234`, V-9).
- `image-viewer-containment.spec.ts::the zoom ceiling is measured from the source, not fixed at the default envelope` (`:710-740`) still passes **unchanged** — a panorama still earns a ceiling **above** `BASE_MAX_SCALE`, and the small source still keeps the default envelope.
- `image-viewer-containment.spec.ts::pan is pinned at 1.0, clamped when zoomed, and reset returns to exactly 1.0` (`:648-708`) still passes **unchanged**.
- The rotation refit test (`:572-644`) still passes **unchanged**.
- **The containment suite is not the only standing pin, and the two that a box-geometry change threatens *most* live in the other spec.** `image-viewer-zoom.spec.ts::toolbar geometry is invariant across zoom levels (outside the transform layer)` (`:194-220`) captures the toolbar's `boundingBox` before and after zooming and asserts it did not move — it is the executable form of V-9, and a repair that re-anchors the toolbar's containing box is exactly what breaks it. `image-viewer-zoom.spec.ts::close and zoom controls meet their target-size floors` (`:177-192`) asserts the ≥44×44 floors from `boundingBox()`, which a width or inset change can move. **Both must pass with their bodies unchanged.**

If the fix makes any of those six fail, **that is the finding** — surface it, do not adjust the test to suit the fix.

### D-7 — Baseline churn is expected, justified per PNG, and never blanket-refreshed

A box-geometry repair moves pixels, and V-13 says this is the one class the default threshold actually catches. So:

- Run the full four-project visual suite, then **triage every failure** before regenerating anything: `stale-baseline` (regen OK) / `deterministic-fail` (a real bug — surface it) / `flake-candidate` (3× probe). **The rule lives in `AGENTS.md:341` § "Visual baseline triage before regen"** — *not* in `project-context.md`, which carries only the Baseline Acceptance Gate (`:243-245`). Story 53.3 § 8 miscites it; do not inherit that.
- **The candidate set is enumerable — 16 PNGs, and no others carry the viewer.** `__snapshots__/catalog-detail.spec.ts/catalog-detail-image-viewer-open-{desktop,mobile}-{light,dark}.png` (4) and `__snapshots__/image-viewer-zoom.spec.ts/image-viewer-{error,toolbar-rest,toolbar-zoomed-chrome-hidden}-{desktop,mobile}-{light,dark}.png` (12). The containment suite owns **zero** baselines by design (§ 7), so a PNG appearing under `__snapshots__/image-viewer-containment.spec.ts/` means something was added that does not belong. **Treat the four `image-viewer-error-*` PNGs as the most sensitive four in the set:** 54.2 AC-7 only just re-settled them (`deferred-work.md:259-261`), so movement there needs its own explanation rather than a `stale-baseline` label by default.
- Every changed PNG carries its own `baseline-reviewed: <basename>, <reviewer>, YYYY-MM-DD` line in the commit message (enforced by `apps/web/.husky/_check-baseline-review.mjs`; matches `--diff-filter=AM`).
- **Never `--update-snapshots` across the suite.** Scope with `-g` to the specific test, as the DN-3 repair did.
- The reviewer named on a `baseline-reviewed:` line must be **the agent or person who actually looked at the diff**. Do not attribute inspection to anyone who did not perform it.

### D-8 — The story closes on the repair **and the request**, never on the retest result

`epics.md:4585` and SCP § 7 both end the sequence at *"request a fresh physical retest"*. The dev agent has no phone. Therefore:

- The story may close with § 9's retest block **empty**, stating plainly that the retest was **requested and not yet performed**.
- **No cell of § 9 may ever be filled from an emulator, DevTools device mode, a desktop touchscreen, a Playwright run, or inference from any of them.** An empty cell is honest; a synthesised one is a lie about a gate.
- § 9 is a **new** block for **this defect on Brave**. It is **not** Story 53.3 § 11, it does not feed § 11, and § 11 stays blank (§ 0).

### D-9 — If the invariant *as written* proves insufficient, stop and route back through `bmad-correct-course`

SCP § 3.3 rules this in advance and it is binding. `architecture.md` Decision BA states the single-reference-box invariant as a **procedure decision**; an implementation defect does not falsify it. But if the diagnosis shows the **rule as written** is insufficient — rather than the implementation being non-compliant with it — then amending Decision BA is a **`bmad-correct-course` input**, not something this story may rewrite. **Stop and surface it.** (Same posture for `epics.md` and `prd.md`: FR26-VIEW-1 is unchanged; this is a defect against shipped behaviour, not a requirement change.)

---

## 4. Acceptance Criteria

**AC-1 — The defect reproduces deterministically, and the environment is recorded rather than assumed.**
Given the shipped viewer, when the repro is established, then the record states: the **exact deployed version string observed** at repro time (not inferred — V-2), the `main` SHA the repro was run against, the device model / browser + version / OS build, the surface and state (`/catalog/$modelId`, viewer open, **reset / minimum scale, before any zoom**), and **the written condition** under which the right edge overflows. The condition is a property of the environment, stated in terms that let someone else reproduce it — never *"sometimes on a phone"*. If the repro is a written manual protocol rather than an automated case, the record says so explicitly and states what blocks automation (D-2).

**AC-2 — A regression test FAILS FIRST, and its red output is recorded.**
Given AC-1's condition, when a regression test is written **before** any product-code change, then it **fails on unmodified `main`** — with the failing output pasted into the record (test name, assertion, measured vs expected numbers) — and **passes after the fix**, with that output recorded too. The assertion encodes the **contract** ("no part of the viewer box extends beyond the region the user can see at reset scale"), stated at the assertion site, and **not** the defect's current numbers (D-3). If the end-to-end condition proves un-producible under Playwright, AC-2 is met by a test of the corrected geometry rule **plus** an explicit, ledgered statement that the end-to-end path has no automated pin and why.

**AC-3 — The story explains why the existing green suite could not fail, and the explanation survives V-5 and V-8.**
Given that `image-viewer-containment.spec.ts` asserts containment at scale 1 across the geometry matrix in both orientations, on `mobile-light`/`mobile-dark`, **including a page-horizontal-overflow case**, and reports green (722 passed / 46 skipped / 0 failed at Story 53.3's gate), when the root cause is known, then the record states **mechanically** why that suite is blind to it. The explanation must engage with the facts that (a) the overflow case **already exists and is green** (V-5), (b) the emulated environment measures `clientWidth == innerWidth == 100vw` (V-8), and (c) nothing in the repo consults `window.visualViewport`, while two shipped comments make **opposite** claims about which API reports which viewport (V-4). *"We were missing an overflow test"* is a **refuted** answer and does not discharge this AC. Whichever reading of V-4 is correct is settled by **measurement with recorded numbers**, not by citation.

**AC-4 — The fix is minimal, root-cause, and its boundaries are proven mechanically.**
Given D-5, when the diff is read, then the repair makes the overflowing box stop overflowing rather than hiding the overflow; **none** of D-5's five rejected shapes is the primary repair; and `git diff --name-only` shows changes confined to the viewer's own geometry surface plus tests and (if triaged) baselines. **`git diff` shows ZERO changes to** `apps/web/src/ui/dialog.tsx`, `apps/web/index.html`, `imageViewer/zoom.ts`, `imageViewer/types.ts`, `routes/share/$token.tsx`, `routes/share/shareBlobCache.ts`, `ModelGallery.tsx`, `package.json`, `package-lock.json`, and every locale file (V-11).

**The zero-diff list splits by § 5 class, and the split is load-bearing** — H3 makes `viewport-fit=cover` in `index.html` a live candidate, so this AC must not be written in a form the story cannot satisfy if the controller grants it:

- **§ 5 `Never`** — `ui/dialog.tsx`, `types.ts`, `routes/share/*`, `ModelGallery.tsx`, `package.json`, `package-lock.json`. Zero-diff is **unconditional**. A change here fails AC-4 outright.
- **§ 5 `Ask First`** — `index.html`, `zoom.ts`, the locale files. Zero-diff is the **default and the expected outcome**. It is satisfied *either* by a zero diff *or* by a diff carried by an **explicit controller grant recorded verbatim in § 12** with the question asked, the answer given, and the date. **An ungranted change to any of these fails AC-4 exactly as a `Never` change does** — the escape hatch is the grant, never the dev agent's own judgement.

**AC-5 — Zoom and pan above 1.0 remain fully inspectable.**
Given D-6, when the fix is in place, then `MIN_SCALE`, `BASE_MAX_SCALE`, `ZOOM_STEP`, `DOUBLE_TAP_SCALE` and `resolveMaxScale`'s semantics are unchanged; the three toolbar controls remain mounted, visible, non-`aria-hidden`, outside the transform and chrome layers, and reachable at every zoom level; and **all six** of D-6's named pre-existing tests — the geometry matrix, the ceiling test, the clamp/reset test and the rotation-refit test in `image-viewer-containment.spec.ts`, **plus `image-viewer-zoom.spec.ts`'s toolbar-geometry-invariance test (`:194-220`) and target-size-floor test (`:177-192`)** — pass **with their bodies unchanged**. A panorama still earns a ceiling above `BASE_MAX_SCALE` and a small source still keeps the default envelope, **verified by running them**, not asserted.

**AC-6 — Every Story 48.1 / Decision BA invariant still holds.**
Given `architecture.md:3371-3376`, when the diff is read, then: geometry is expressed in **one** reference box (no `left-1/2` + `-translate-x-1/2` anywhere in the viewer); `dvh` is used and `vh` is not, for every viewport-relative height; `user-scalable=no` appears nowhere; `apps/web/src/ui/dialog.tsx` is **zero-diff**; and `image-viewer-containment.spec.ts` is green (as extended and, where D-4 applies, corrected-with-measurement). The `sm:max-w-[calc(100%-2vw)]` override is still present or deliberately superseded — not silently dropped back to `ui/dialog.tsx`'s `sm:max-w-sm` (V-10).

**AC-7 — i18n, visual and baseline discipline at this story's own gate.**
Given V-11 and D-7, when the gate is run, then: both locale files still hold **identical key sets at 1050** and **no key was added, removed or re-valued** (a geometry repair ships no copy; if copy proves necessary, that is surfaced as a scope signal first); every changed baseline was **triaged by class before regeneration** and carries its own `baseline-reviewed:` line naming the agent or person who **actually inspected** it; **no blanket `--update-snapshots` was run**; and `infra/scripts/check-all.sh` passed **standalone, all green**, with the log teed to `.hermes/run-logs/` and the exact path cited.

**AC-8 — Deployed, with the build recorded.**
Given AGENTS.md § Deployment, when the repair is merged to `main` (story branch, **ff-only**, no squash) and `infra/scripts/deploy.sh` has run, then the record carries the **deployed commit SHA and the release/version string** the running build reports, plus the post-deploy `/api/health` version. The repair is a `fix:` commit, so the range-based deploy gate will not skip it.

**AC-9 — A fresh physical retest is REQUESTED, bounded, and never claimed.**
Given § 9 and D-8, when this story closes, then either (a) the operator has filled § 9 from a **physical Android phone running Brave**, against the **deployed** repair, with device / browser version / OS build / deployed version / date recorded; or (b) § 9 is **empty** and the record states plainly that the physical retest was **requested and NOT performed**, that operator evidence remains **OPEN**, and that **`G26-LIB` remains OPEN**. **The dev agent cannot discharge (a).** No cell may be filled from an emulator, DevTools device mode, a desktop touchscreen, a Playwright run, or inference (§ 0, D-8).

**AC-10 — Evidence-class honesty, and the residuals stay unabsorbed.**
Given § 0, when the Dev Agent Record is written, then it: labels every automated result as **automated regression evidence** and makes no claim about real-device gesture quality; states that **`G26-LIB` was not advanced**, that the triggering evidence is **Brave and not Chrome for Android**, and that **`epic-53` stays `in-progress`**; states that Story 53.3 § 11 was **not** touched; states that `architecture.md` Decision BA was **not** edited (or that D-9's `bmad-correct-course` route was taken); claims **no human review and no Ezop sign-off** anywhere; and confirms that **none** of V-12's seven open E53 residuals was absorbed, patched or claimed closed by this story.

**AC-11 — `NFR26-DETERMINISM-1` is discharged before merge, with logs.**
Given `prd.md:2268` and `epics.md:4421` — which bind the determinism triple to **all** Initiative 26 stories, not to a subset — when the merge gate is run, then **three consecutive `npm run test` (vitest) runs report identical file and test counts with `rc=0`**, and the same holds for `pytest` **or** the record states plainly that the backend is untouched by this diff and pytest determinism is therefore not this story's obligation (the 51.4 precedent, `51-4-model-detail-category-display.md:184`). Each run is teed to `.hermes/run-logs/` and the exact paths are cited. **A single green `check-all.sh` does not discharge this** — it runs each suite once. Stories 53.2 and 53.3 both merged without an explicit determinism record; that is a gap in those stories, not a precedent this one inherits.

---

## 5. Ask First / Never

**Ask First (surface to the controller; do not decide alone):**

- **Starting dev at all** — § 0 / `G26-DEVGO`. This is the first one and it is not a formality.
- **Touching `apps/web/src/ui/dialog.tsx`** — blast radius is every dialog in the app (`architecture.md:3375`, V-10). If the root cause lands there, **stop**.
- **Touching `apps/web/index.html`** — in particular adding `viewport-fit=cover` (V-7). App-wide, and it changes what every `env(safe-area-inset-*)` in the app resolves to.
- **Any change to a `zoom.ts` constant or to `resolveMaxScale`'s semantics** (D-6). This story preserves them; it does not tune them.
- **Adding a fifth Playwright project** or otherwise widening the fixed 4-project matrix (V-6).
- **Adding any dependency**, including a test-only one.
- **Any deviation from `DESIGN.md` / `EXPERIENCE.md`** for this surface — the spines win (`DESIGN.md:264`); a deviation is a `bmad-correct-course` input.
- **Adding an i18n key** (V-11) — a geometry repair should need none; needing one is a scope signal.
- **A root cause that falsifies the Decision BA invariant *as written*** rather than the implementation's compliance with it — D-9.

**Never:**

- **Never claim `G26-LIB` progress, and never cite Brave evidence as Chrome-for-Android.** Wrong browser *and* wrong evidence class (§ 0).
- **Never fill a cell of Story 53.3 § 11**, or of this story's § 9, from anything but the stated physical device. An empty cell is honest.
- **Never claim human review or an Ezop sign-off.** The operator supplied screenshots; that is the entire human contribution.
- **Never claim the physical retest result** before it exists (D-8).
- **Never edit `architecture.md` Decision BA, or close any `G26-*` gate.** Gate closure is the controller's; an architecture amendment routes through `bmad-correct-course`.
- **Never reintroduce `left-1/2` + `-translate-x-1/2`, never use `vh` for a viewport-relative height, never write `user-scalable=no`** (`architecture.md:3372-3374`).
- **Never modify `renderImage` / `renderThumb`, their call sites, `AnonymousImage` / `LazyAnonymousImage`, or `shareBlobCache.ts`** — breaks `credentials:"omit"` (NFR10-SHARE-SECURITY-1) and the rate-limit + 4-slot semaphore (Init 12 Story 19.1, Init 17 TB-047).
- **Never widen scope to `Viewer3DModal` or other `DialogContent` consumers** — deferred at `architecture.md:3378`.
- **Never absorb any of V-12's seven open E53 residuals** — SCP § 5.6. Not the DN-4 `/share` watchdog gap, not the double-tap chrome flash, not the retry dead-end, not any of them.
- **Never "fix" the double-tap chrome flash** — it violates 53.2 AC-3 and needs an explicit amendment via `bmad-correct-course`.
- **Never rewrite an existing test to make a fix pass.** D-4's narrow exception applies only to a premise **proven wrong by recorded measurement**, and only when labelled as a contract correction.
- **Never blanket `--update-snapshots`.** Triage first (D-7).
- **Never hard-code a colour**; token-only, no new `--color-*`.
- **Never `git push --no-verify` past a red gate.** The only permitted use is the transport/output-only SIGPIPE case, with standalone green evidence already logged (`AGENTS.md` § "Pre-push hook policy & gate evidence").

---

## 6. Tasks / Subtasks

- [x] **T0 — Confirm the entry gate.** (§ 0, AC-10)
  - [x] Re-read § 0. Confirm the controller has issued a **per-story `G26-DEVGO`** for **53.4** specifically. If absent, **stop and report** — do not open a branch.
  - [x] Branch `fix/E53.4-android-chromium-lightbox-fit-repair` from `main` (AGENTS.md § "Story branches"; `fix/` prefix because this is a defect repair).
  - [x] Read `ImageFullscreenViewer.tsx`, `image-viewer-containment.spec.ts`, `image-viewer-zoom.spec.ts` and `zoom.ts` **end to end before writing a line** (V-1, V-4, V-5).

- [x] **T1 — Reproduce deterministically — IN EMULATION ONLY.** (AC-1, D-2) The device half of this task is **NOT PERFORMED**; see the unchecked subtask below and § 12 AC-1.
  - [x] Record the deployed version string observed at repro (`/api/health` version and the running bundle), the `main` SHA under test, device / browser / OS build.
  - [x] Narrow to a written condition. Measure **in the browser** (headless/emulated Chromium via Playwright + CDP), at minimum: `window.innerWidth`, `document.documentElement.clientWidth`, `window.visualViewport.width` / `.scale` / `.offsetLeft`, `document.documentElement.scrollWidth`, and the computed used values of `98vw`, `1vw` and `calc(100%-2vw)` on the dialog. **Settle V-4 with these numbers.**
  - [ ] Measure the same set **on the real device** (Brave / Android 17, the reporting handset). **NOT PERFORMED — no device access.** The dev agent has no handset, and nothing in § 12 is a device reading. On the device the condition is **inferred** from the three operator screenshots plus the emulated geometry, never measured; confirmation belongs to the § 9 physical retest (AC-9), which stays empty.
  - [x] Measure the same set in Playwright `mobile-light` and record the divergence (or its absence). This is the raw material for AC-3.
  - [x] Attempt an automated repro first; fall back to a written manual protocol only if provably necessary, and state what blocks automation.

- [x] **T2 — Failing regression + the suite-blindness explanation.** (AC-2, AC-3, D-3, D-4)
  - [x] Write the regression **before** touching product code. Run it on unmodified `main` and **paste the red output** into § 11.
  - [x] State the contract at the assertion site, not the defect's numbers.
  - [x] Write the AC-3 explanation against the measurements from T1, engaging explicitly with V-5 (the overflow test already exists and is green) and V-8 (`clientWidth == innerWidth` in emulation).
  - [x] If a premise in `assertContained` is proven wrong, apply the **contract correction** under D-4 — with the measurement recorded, a comment at the assertion, and the correction named in the commit message. Otherwise leave every existing body byte-identical.

- [x] **T3 — Minimal root-cause fix.** (AC-4, AC-6, D-5)
  - [x] Change the geometry rule so the viewer's own boxes are inside the visible region. No `overflow-x: hidden`, no image shrink, no ceiling cap, no re-centering, no UA branch.
  - [x] Re-run T2's regression: it must go green **because the measured overflow is gone**, re-read from the numbers, not merely because the assertion passed.
  - [x] Verify the 48.1 / Decision BA invariants mechanically, including that `sm:max-w-` is not silently dropped back to `ui/dialog.tsx`'s `sm:max-w-sm` (V-10).
  - [x] Confirm `apps/web/src/ui/dialog.tsx` zero-diff. If the fix needs it — **stop and ask** (§ 5).

- [x] **T4 — Prove inspectability above 1.0 survives.** (AC-5, D-6)
  - [x] Run the six named pre-existing tests with **unchanged bodies**: geometry matrix, ceiling, clamp/reset and rotation refit in `image-viewer-containment.spec.ts`, **plus `image-viewer-zoom.spec.ts`'s toolbar-geometry-invariance (`:194-220`) and target-size-floor (`:177-192`)**. Record the output.
  - [x] Confirm no `zoom.ts` constant and no `resolveMaxScale` semantics moved.
  - [x] Confirm the toolbar stays mounted / visible / non-`aria-hidden` / outside both layers at every zoom level.

- [x] **T5 — Gate, baselines, review.** (AC-7, AC-11) **COMPLETE 2026-08-01** — the two legs that stood unchecked below (the standalone `check-all.sh` and the independent Aider review) are both discharged; see § 12 "Independent Aider review" and "Controller fullgate".
  - [x] `npm run lint --max-warnings=0`, `npm run typecheck`, `npm run test`, `npm run test:visual` from `apps/web/`.
  - [x] **`NFR26-DETERMINISM-1`: `npm run test` ×3 consecutive with identical counts and `rc=0`**, each teed to `.hermes/run-logs/`. State the pytest posture explicitly (run ×3, or record that the backend is untouched). Do **not** treat the single `check-all.sh` vitest stage as this proof.
  - [x] Triage every visual failure by class **before** regenerating, against D-7's enumerated 16-PNG candidate set; scope regeneration with `-g`; one `baseline-reviewed:` line per changed PNG naming the actual inspector.
  - [x] Verify locale key sets are still identical at **1050** with no value changes.
  - [x] `infra/scripts/check-all.sh` **standalone**, teed to `.hermes/run-logs/`; cite the exact log path. **DISCHARGED 2026-08-01 by the controller fullgate: `.hermes/run-logs/check-all-53-4-20260801_053329.log`, `rc=0`, `passed: 16`, `all green.`** Run **after** the Aider review, over the current tree, `apps/web visual regression` **826 passed / 50 skipped / 0 failed**, zero baseline PNG changes. *(History, kept so the withdrawal is not re-erased: `check-all-20260801_030818.log` was green but finished 03:21, before the BLOCKING-1 fix at 03:49; `53-4-reviewfix-check-all-20260801_035047.log` was truncated mid-`apps/api pytest`. Neither is the evidence — the 05:33 run is.)*
  - [x] Native `bmad-code-review`; resolve or explicitly defer every actionable finding. **First run 2026-08-01 → `REQUEST_CHANGES`** (BLOCKING-1/-2 + NB-1..NB-4, all resolved or routed — § 12 "Review-fix pass"). **Re-runs 2026-08-01 → `REQUEST_CHANGES` twice more**, raising BLOCKING-3..9; all blockers were fixed, withdrawn to owed controller gates, or ledgered out-of-scope as recorded in § 12. **Final finish pass 2026-08-01 → `APPROVED`** (`.hermes/run-logs/t_962a3d46-bmad-code-review-final-20260801_045810.log`; Claude session `899e22d7-5eba-4021-832c-e6227b6bce83`).
  - [x] Independent external review: **Aider** via `laura-aider-review-diff` (routine default per the Laura Agent Rulebook). **Gemini is not a default reviewer.** Codex only for fallback / high-stakes / explicit operator request. **RUN 2026-08-01 — `.hermes/run-logs/aider-review-53-4-20260801_053242.log`, `rc=0`, literal verdict `REQUEST_CHANGES`.** It is recorded as `REQUEST_CHANGES` and **NOT as an Aider `APPROVE`**; the story proceeds on an explicit **controller arbitration** of that verdict, finding-by-finding, in § 12 "Independent Aider review". No Aider finding required a code or test change.

- [ ] **T6 — Merge and deploy.** (AC-8)
  - [ ] ff-only merge to `main`, no squash; delete the branch; push.
  - [ ] Run `infra/scripts/deploy.sh`. Record the deployed SHA, the release/version string, and the post-deploy `/api/health` version.

- [ ] **T7 — Request the physical retest and close honestly.** (AC-9, AC-10, D-8)
  - [ ] Write the § 9 request block with the exact steps and the exact measurements the operator should report. Leave every result cell **empty**.
  - [ ] Write the Dev Agent Record per AC-10: evidence class, `G26-LIB` untouched, Brave ≠ Chrome, `epic-53` still `in-progress`, § 11 of Story 53.3 untouched, Decision BA unedited, no human review claimed, V-12's seven residuals unabsorbed.

---

## 7. Dev Notes

### Relevant architecture patterns and constraints

- **Decision BA carried-forward invariants** (`architecture.md:3371-3376`): single reference box for viewport-anchored geometry; `dvh` not `vh`; never `user-scalable=no`; `ui/dialog.tsx` is Ask First; `image-viewer-containment.spec.ts` is a **standing** suite E53 keeps green. All five apply here without modification.
- **Three-layer viewer structure** (`ImageFullscreenViewer.tsx:30-43`): (1) transform layer — only the `renderImage` output, scales/translates; (2) chrome layer — counter/close/chevrons, fades on tap-to-hide; (3) toolbar layer — always mounted, outside both. **The toolbar being clipped is a statement about layer geometry, not about the image** (V-9).
- **`renderImage` is the auth boundary** and is untouchable (`architecture.md:3369`, NFR10-SHARE-SECURITY-1). Both mounts — `ModelGallery` on `/catalog/$modelId` and `ShareCarousel` on `/share/$token` — inject it; the viewer never inspects or replaces what it returns.
- **Frontend conventions** (`project-context.md`): no inline hex colours (Tailwind classes → `theme.css` tokens); `import type` under `verbatimModuleSyntax`; `noUncheckedIndexedAccess` means no `!` shortcuts; ESLint must pass at `--max-warnings=0`.

### Source tree components to touch

| Path | Expected role |
|---|---|
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` | **UPDATE** — the geometry under repair (`:870` dialog className; `:914-940` transform layer + image caps; `:1068` toolbar anchor). Read § "Current state" below before editing. |
| `apps/web/tests/visual/image-viewer-containment.spec.ts` | **UPDATE (additive; D-4 correction only if proven)** — the standing containment suite; home of the new regression. |
| `apps/web/tests/visual/__snapshots__/**` | **UPDATE (triaged)** — expected churn from a geometry change (D-7). |
| `apps/web/src/ui/dialog.tsx` | **NEVER** without an explicit grant (V-10). |
| `apps/web/index.html` | **ASK FIRST** (V-7). |
| `imageViewer/zoom.ts`, `imageViewer/types.ts`, `routes/share/*`, `ModelGallery.tsx`, locale files | **NEVER** (AC-4). |

### Current state of the file being modified (read this run, `36edc9c`)

`ImageFullscreenViewer.tsx` is ~1180 lines. What it does **today**, at the surface this story touches:

- `DialogContent` overrides five `ui/dialog.tsx` base classes to anchor the dialog at the viewport origin: `left-[1vw] top-[2.5dvh] translate-x-0 translate-y-0`, sized `w-[98vw] h-[95dvh]`, capped `max-w-[calc(100%-2vw)]` **and** `sm:max-w-[calc(100%-2vw)]` (`:870`). The in-file comment block at `:838-869` is the *reasoning* Story 48.1 recorded, and **part of its premise is what V-4 puts in question** — read it as a claim under test, not as documentation.
- The frame (`:891-895`) is `relative flex flex-1 min-h-0 items-center justify-center overflow-hidden`. `min-h-0` is the TB-044 flexbox shrink fix; `overflow-hidden` is what clips a zoomed image legitimately.
- The image is capped `max-h-[calc(95dvh-5rem)] max-w-full object-contain` (`:938`) — `95dvh` mirrors the dialog height, `5rem` is the `h-20` strip.
- The toolbar column (`:1068`) is `absolute inset-x-0 bottom-[max(1rem,env(safe-area-inset-bottom))]`, centred by `items-center`. `env(safe-area-inset-bottom)` is **0 today** (V-7).

**What must be preserved end-to-end** regardless of what the ACs say literally: the viewer must keep working on **both** mounts (`/catalog/$modelId` and `/share/$token`), in both orientations, in light and dark, with the strip / counter / chevrons / toolbar all reachable, scroll lock intact, and the `/share` credential boundary untouched. A story implementation must leave the system working, not merely satisfy its own ACs.

### Testing standards summary

- **Visual regression is mandatory for any UI change** — `npm run test:visual` from `apps/web/`, all four projects. A green typecheck and lint do not substitute.
- Playwright specs run `pl-PL`; every text matcher is the literal Polish string, and control lookups are **scoped to `image-viewer-toolbar`** because `viewer3d.tooltip.expand` shares a name (`image-viewer-containment.spec.ts:352-365`).
- The containment suite produces **no snapshots** by design — it is geometry assertions only. If a baseline appears there, something was added that does not belong.
- Every `toHaveScreenshot` is preceded by an explicit `toBeVisible()` on the concrete state.
- **Vitest `globals: false`** → every new multi-`it` test file needs `import { cleanup } from "@testing-library/react"; afterEach(cleanup);`.
- jsdom has **no layout engine**: a geometry assertion written against the mounted viewer in vitest reads all-zero rects and passes trivially. **Every geometry claim in this story belongs in Playwright or on the device.**
- **But vitest is not class-blind, and that is the trap in the sentence above.** `ImageFullscreenViewer.test.tsx:280-282` asserts the close button's `className` **contains `h-11` and `w-11` and does not contain `h-10`** — a string assertion, unaffected by the missing layout engine. A repair that retunes a control's sizing classes goes red there while every Playwright geometry test still passes. Read `ImageFullscreenViewer.test.tsx` before changing any `className` in the component, not only the Playwright specs.

### Project Structure Notes

- No new files are anticipated. The regression belongs **inside** `image-viewer-containment.spec.ts` — every helper it needs (`solidPng`, `openViewerWith`, `boxOf`, `expectWithinViewport`, `assertContained`, `rotate`) is file-local and **unexported** (Story 53.3 V-6), so a new spec file would duplicate ~130 lines of PNG encoder and geometry assertions. That was already ruled once, for exactly this reason.
- If the repair needs a measurement helper the suite lacks (e.g. a `visualViewport` reader), add it **to that file** as a new helper. Extraction into a shared module is explicitly rejected — it rewrites a standing regression suite for no functional gain.
- No conflicts with the unified project structure are expected. If the diagnosis forces a change outside `apps/web/src/modules/catalog/components/imageViewer/`, that is a scope signal to surface, not to absorb.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md#Story 53.4` — `:4581-4585`, the epic sketch and its `VERIFY-AT-CREATE-STORY` clause]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-08-01-e53-android-lightbox-fit-defect.md` — § 2 evidence, § 3.4 hypotheses H1–H4, § 5 gate rulings, § 7 success criteria]
- [Source: `_bmad-output/planning-artifacts/architecture.md#Decision BA` — `:3363-3386`, invariants and the `G26-*` gate line]
- [Source: `_bmad-output/planning-artifacts/prd.md#FR26-VIEW-1` — `:2256`; `#NFR26-VISUAL-1` — `:2267`; `#NFR26-A11Y-1` — `:2265`]
- [Source: `_bmad-output/implementation-artifacts/53-3-lightbox-test-contract.md` — § 0 evidence-class split, § 2 V-3/V-6, § 5 Ask First/Never, D-2/D-3/D-8]
- [Source: `_bmad-output/implementation-artifacts/deferred-work.md` — the seven open E53 residuals at `:225-227`, `:266-277`, `:285-288`, `:294-300`]
- [Source: `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` — `:838-870`, `:891-940`, `:1068`]
- [Source: `apps/web/tests/visual/image-viewer-containment.spec.ts` — `:1-20`, `:128-140`, `:264-295`, `:305-346`, `:539-740`]
- [Source: `apps/web/tests/visual/image-viewer-zoom.spec.ts` — `:177-192` target-size floors, `:194-220` toolbar geometry invariance; owns 12 of the 16 viewer baselines]
- [Source: `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.test.tsx` — `:280-282`, the `h-11`/`w-11` className assertions jsdom *can* see]
- [Source: `apps/web/src/ui/dialog.tsx` — `:42-81`]
- [Source: `apps/web/tests/visual/playwright.config.ts` — `:18-35`]
- [Source: `apps/web/index.html` — `:5`]
- [Source: `AGENTS.md` § "Branching and workflow", § "Pre-push hook policy & gate evidence", § "Execution discipline", § "Deployment"]
- [Source: `_bmad-output/project-context.md` § "UI quality gates" — `:243-245`, the Baseline Acceptance Gate; § "Magic constants in specs require contract-pointing justification" — `:287`; § "Visual regression matrix is fixed (4 projects)" — `:110`]
- [Source: `AGENTS.md` § "Visual baseline triage before regen" — `:341`. **This is where the triage rule lives**; it is not in `project-context.md`.]

---

## 8. Hypotheses to test (from SCP § 3.4) — **not** a diagnosis

The story owns the diagnosis and **may reject all of these**. They are recorded so the search is bounded, not so the answer is pre-supplied. Each carries the test that would kill it.

| # | Hypothesis | How to kill it |
|---|---|---|
| **H1** | The `w-[98vw]` / `left-[1vw]` anchoring overflows because `vw` resolves against a box wider than the visible area (the layout-vs-visual viewport question of V-4). **SCP calls this the strongest candidate; test it first.** | Measure the used width of `98vw` against `visualViewport.width` on the device. If they agree, H1 is dead. |
| **H2** | `max-w-[calc(100%-2vw)]` fails to cap — the counterweight its own comment says CI cannot exercise (V-8). | Measure the dialog's used `max-width` and compare to its used `width`. If the cap is binding and correct, H2 is dead. |
| **H3** | Brave- or Android-17-specific chrome/viewport behaviour (shields, custom toolbar, edge-to-edge / `viewport-fit` handling) shifts the visible area relative to the layout viewport (V-7). | Reproduce in **Chrome for Android** on the same device. If it reproduces identically, H3 as a *Brave*-specific cause is dead (and the finding gets stronger, though it still does **not** become `G26-LIB` evidence — wrong evidence class, § 0). |
| **H4** | `object-contain` + `max-w-full` fit an already-over-wide box. | **Insufficient alone by construction** — V-9 shows the toolbar is clipped too, and the toolbar is not inside the transform layer. H4 can only ever be a *contributing* factor to a cause that also explains the toolbar. |

**A fifth possibility the SCP does not list, raised by V-4 and worth holding open:** the geometry may be *correct* and the **suite's measurement premise** wrong — in which case the "defect" is real on the device but its cause is upstream of the CSS entirely (e.g. what the browser reports as the containing block). Do not let the four named hypotheses foreclose that.

---

## 9. Physical retest request — Brave on the reporting device (**operator-only; leave empty until performed**)

> **This block is NOT Story 53.3 § 11, does not feed it, and closes no gate.** It asks about **this defect** in **Brave**. `G26-LIB` needs a *different* browser and a *different kind* of evidence (§ 0). **No cell here may be filled from an emulator, DevTools device mode, a desktop touchscreen, a Playwright run, or inference from any of them.**

**Preconditions the dev agent must record before requesting:** deployed SHA · release/version string · `/api/health` version · the date the repair went live.

| Deployed version under test | Device | Browser + version | OS build | Date |
|---|---|---|---|---|
| _(to be filled)_ | _(to be filled)_ | _(to be filled)_ | _(to be filled)_ | _(to be filled)_ |

| # | Check | Expected | Observed |
|---|---|---|---|
| R-1 | Open `/catalog/<model>` and open the fullscreen viewer at reset scale. Is there a visible dark gutter on **both** the left and the right of the photo? | Yes, symmetric | |
| R-2 | Is the whole photo inside the screen — no edge cut off by the right screen edge? | Yes | |
| R-3 | Is the **entire** bottom-right zoom toolbar visible, with the `−` button's circle complete and not sliced? | Yes | |
| R-4 | Is the close button (top-right) fully visible and pressable? | Yes | |
| R-5 | Zoom in twice, then pan. Is the photo still inspectable and does pan work in both directions? | Yes | |
| R-6 | Press Reset. Does the viewer return to a correctly fitted photo with both gutters present? | Yes | |
| R-7 | Rotate to landscape and back. Does the fit survive both trips? | Yes | |
| R-8 | Repeat R-1..R-4 on a **panoramic** photo (widest one available). | Yes | |

**Result:** _(empty = NOT PERFORMED — say so plainly; do not infer)_

---

## 10. Change Log

| Date | Change |
|---|---|
| 2026-08-01 | Story created by native `bmad-create-story` (Create) at `main` @ `36edc9c`, from the `epics.md` E53 sketch and the 2026-08-01 SCP. Sprint status `backlog` → `ready-for-dev`. |
| 2026-08-01 | Native `bmad-create-story` Validate pass (`checklist.md`) at the same commit. **No corrections list was ever written** — the session was killed before § 11 was populated. See § 11 for the caveat. |
| 2026-08-01 | Artifact hygiene, this file only: § 11 replaced the `_Populated by the Validate pass._` placeholder with the honest empty-record caveat, and the row above stopped pointing at a corrections list that does not exist. No product code, tests, baselines or locales touched; nothing committed. |
| 2026-08-01 | **Native `bmad-dev-story` DEV PASS on branch `fix/E53.4-android-chromium-lightbox-fit-repair`** (controller per-story `G26-DEVGO` for 53.4 only), from `main` @ `36edc9c`. Status `ready-for-dev` -> `in-progress`. T0-T4 complete **except T1's real-device measurement, which is `NOT PERFORMED` (no device access)**, and T5 partially complete. **Root cause settled BY MEASUREMENT IN EMULATION, not citation — and INFERRED, not measured, on the reporting handset (confirmation is owed to the empty § 9 retest):** every viewport-relative unit the viewer used resolves against the LAYOUT viewport while the user sees the VISUAL viewport; at page scale 2 on `mobile-light` the dialog measured `3.92 -> 389.05` inside a `196.5`-wide visible region, with the centred toolbar cut at 196.48 — inside the `-` button, matching the device screenshot. **V-4 settled: BOTH shipped comments are false**, in opposite directions; `window.visualViewport` is the only correct source. RED 8 failed / GREEN 8 passed on the same command. Repair rebases the shipped ratios onto the measured visible region via CSS custom properties, keeping the `vw`/`dvh` expressions as `var()` fallbacks. **Zero baseline churn, zero locale change, every `Never` and `Ask First` file zero-diff, no controller grant needed.** `check-all.sh`, native `bmad-code-review`, Aider review, merge and deploy are **NOT yet done** and are owed. **GATES UNCHANGED: `G26-LIB` STAYS OPEN and is NOT advanced; `epic-53` STAYS `in-progress`; Story 53.3 `§ 11` STAYS BLANK; `§ 9` retest block STAYS EMPTY.** Decision BA NOT edited. **No human review, NOT an Ezop signature, no retest run or claimed.** |
| 2026-08-01 | **Native `bmad-create-story` Validate action RE-RUN to completion** at `main` @ `36edc9c`, in a fresh session, against `checklist.md`. Verdict **PASS WITH CORRECTIONS**: 6 corrections applied to this file (new **AC-11** determinism gate; D-6/AC-5/T4 widened from four pre-existing tests to six; D-7 baseline-triage miscitation fixed and the 16-PNG candidate set enumerated; AC-4 split by § 5 class so an `Ask First` grant is representable; § 7 vitest-`className` trap recorded; header comment corrected). Every § 2 `VERIFY-AT-CREATE-STORY` row was independently re-measured and **all thirteen hold**. § 11 now carries the real record. Sprint status key was already `ready-for-dev` and needed no change. **`G26-DEVGO` untouched and still OPEN; no code authorization; nothing committed.** |
| 2026-08-01 | **Native `bmad-code-review` → `REQUEST_CHANGES`, followed by a REVIEW-FIX PASS on the same branch** (review log `.hermes/run-logs/t_962a3d46-bmad-code-review-20260801_033228.log`). Both blocking findings were in the **claims** layer. **BLOCKING-1 fixed in code**: the fallback `max-w`/`sm:max-w` dropped E48.1's `calc(100%-2vw)` gutter cap, so the "byte-identical fallback" claim was false on exactly the platform class the cap exists for — both fallbacks are now `var(--viewer-w,calc(100%-2vw))`, verified in the compiled stylesheet. **BLOCKING-2 fixed in the record**: T1's real-device measurement is now a separate **unchecked** subtask marked `NOT PERFORMED — no device access`; § 12 AC-1 states that the condition is **measured in emulation and INFERRED on the device**, and this log's earlier "settled BY MEASUREMENT" row is qualified accordingly. **Root cause is NOT claimed closed on the handset** — that belongs to the still-empty § 9. Non-blocking: a panned-page regression was ADDED (covers `visualViewport.offsetLeft`/`.offsetTop` + the `scroll` listener; proven red-for-the-right-reason by deleting the offset terms), the `zoom toolbar` helper assertions were named in the D-4 list, and two findings (page-pinch trade-off; Chromium-only validation) were **routed to `deferred-work.md`, not absorbed**. Viewer specs 108 → **112 passed / 12 skipped / 0 failed**; ~~`check-all.sh` re-run standalone~~ — **that clause is WITHDRAWN by the next row: the re-run was truncated and never completed** — zero baseline churn and zero locale change still hold. **GATES STILL UNCHANGED: `G26-LIB` OPEN, `epic-53` `in-progress`, Story 53.3 § 11 blank, § 9 empty, Decision BA unedited. No human review claimed. Nothing committed.** Aider (`laura-aider-review-diff`, T5) is still owed. |
| 2026-08-01 | **Native `bmad-code-review` RE-RUN → `REQUEST_CHANGES` AGAIN, followed by a SECOND REVIEW-FIX PASS on the same branch** (review log `.hermes/run-logs/t_962a3d46-bmad-code-review-rerun-20260801_035348.log`). The re-run **confirmed BLOCKING-1 and BLOCKING-2 resolved** and NB-2/NB-3 ledgered, NB-4 named, and explicitly did **not** dispute the V-4 diagnosis or the repair geometry — both new blockers are in the **evidence** layer. **BLOCKING-3 fixed in the test**: the panned-page regression added in pass 1 was FLAKY in full-suite runs (reviewer: 3 failed, then 1 failed; green only in `-g` isolation) because Playwright derives click points in LAYOUT-viewport space while CDP dispatches them in VISUAL-viewport space, so at page scale 2 with a moved origin the synthetic pointer lands off the button — a harness artefact that nonetheless made the standing suite, and `check-all.sh`'s `apps/web visual regression` stage, intermittently RED. **All five `expectWithinVisibleRegion` assertions and both origin preconditions are kept verbatim**, so `visualViewport.offsetLeft`/`.offsetTop` and the `scroll` listener lose no coverage; only the click tail is replaced by a deterministic `document.elementFromPoint` hit test (`expectHittable`) on the two ENABLED controls. Click-through interaction coverage stays in the two origin-`0,0` page-scale tests. **BLOCKING-4 fixed in the record BY WITHDRAWAL, not by re-running**: the story had cited a PRE-FIX `check-all.sh` as if it covered the current tree while the post-fix run was truncated mid-`apps/api pytest`, so every all-green claim is struck in § 6 T5, § 12 Debug Log References and § 12 AC-7 / AC-11, both logs are named with exactly what is wrong with each, and **AC-7's check-all leg is now EXPLICITLY OWED to the controller fullgate**. Non-blocking: the AC-11 vitest triple was **re-run on the current tree** (`154 files / 1139 tests`, `rc=0`, identical ×3), and this key's `sprint-status.yaml` note now records both `REQUEST_CHANGES` verdicts instead of listing the review as merely owed. **Current-tree evidence and nothing beyond it:** `git diff --check` clean; `npm run typecheck` rc=0; both viewer specs × 4 projects **112 passed / 12 skipped / 0 failed on THREE consecutive full runs**. **NOT RUN AND NOT CLAIMED: `check-all.sh`, the full 4-project visual suite, `npm run build`.** **GATES STILL UNCHANGED: `G26-LIB` OPEN, `epic-53` `in-progress`, Story 53.3 § 11 blank, § 9 empty, Decision BA unedited. No human review claimed. Nothing committed.** A passing `bmad-code-review` re-run and Aider (`laura-aider-review-diff`, T5) are both still owed. |
| 2026-08-01 | **Native `bmad-code-review` RE-RUN #2 → `REQUEST_CHANGES` A THIRD TIME, followed by a THIRD REVIEW-FIX PASS on the same branch** (review log `.hermes/run-logs/t_962a3d46-bmad-code-review-rerun-2-20260801_041133.log`; triage in Claude session `2a75d88e-fa8f-4280-a535-f4ff1e622183`). The re-run **confirmed BLOCKING-3 resolved** and **BLOCKING-4 correctly marked OWED rather than falsely claimed**, and did not dispute the V-4 diagnosis or the repair geometry. **Unlike passes 1 and 2, two of the three new blockers are REAL DEFECTS in the shipped diff, both introduced by this story.** **BLOCKING-5 FIXED IN CODE** — a `visualViewport` resize resized the frame but never re-ran the zoom/pan refit, because this diff made `frame.clientWidth/Height` (the box `clampPan` measures legal travel against) a function of `visualViewport` while the refit effect still listened on `window` only, and a page pinch fires `visualViewport.resize`, not `window.resize`; the subscription is consolidated into the refit effect so ONE handler publishes geometry then re-clamps, and `commit()` gained an identity-reuse guard so the newly `scroll`-driven commits cannot re-render a `backdrop-blur` layer every compositor frame. **BLOCKING-6 MEASURED, THEN FIXED IN CODE** — the break is at **~2.45×**, not the reviewer's estimated ~2.7×, and had a second cause the review had not named: `DialogContent` is a grid, so the viewer root's `min-width: auto` pinned it at the thumb strip's 158px min-content and the **close button** rode that floor out of the visible region (root right edge 159.30 against a 131px region at page scale 3). Repaired with three classes and no redesign — `min-w-0` on the root, `flex-wrap`+`justify-center` on the toolbar, `shrink-0` on its three buttons — all no-ops at page scale 1, so **zero baseline churn, measured**. **BLOCKING-7 FIXED IN THE TEST by making the claim true**: `expectHittable` now asserts the hit-tested point lies inside the visible region as well as being topmost; proven with no source toggle — under an injected 0-origin regression the old occlusion-only check returns PASS on a control at y=43 while the region starts at y=80, the new bound returns FAIL. **THE BOUND IS RAISED, NOT REMOVED: AC-2 is claimed over a MEASURED ~1×–3× range and explicitly NOT unlimited.** Contained at 3 (+44.25px slack) and 3.5 (+10.52), OUT at 4/4.5/5; and a tighter limit — the wrapped toolbar covers the close button's centre from **~3.06×**. Both need a viewer redesign the review ruled out of scope, so both are **LEDGERED AS OWED (`deferred-work.md` DW-53.4-C)** with the tiny-height `--viewer-img-max-h` case. The regression test is pinned at page scale 3, deliberately the last safe step, so its +4.20px of close-button slack is the tripwire. Non-blocking: NB-1 fixed with a test (`--viewer-img-max-h` now dies if deleted), NB-2 pan poll gates on both axes, NB-5 fabricated `SSR` removed, NB-7 stale citations replaced by names; NB-4 only partly addressed and **not claimed fixed**; NB-3 ledgered; NB-6 left adjacent to the existing Chromium-only entry. A **50%-flaky new test was found and fixed inside this pass** (desktop-only, synthetic touch racing the zoom commit; `settleTwoFrames` + a retried idempotent precondition; 20/20 with `--repeat-each=5`) — pass 2's BLOCKING-3 was exactly such a flake reaching the reviewer, and this one did not. **Current-tree evidence:** `git diff HEAD --check` clean; `npm run typecheck` rc=0, independently re-run by the controller (`.hermes/run-logs/53-4-controller-typecheck-after-fix3-20260801_045148.log`); focused viewer specs × 4 projects **120 passed / 12 skipped / 0 failed**, controller's independent post-fix run `.hermes/run-logs/53-4-controller-viewer-after-fix3-run1-20260801_045158.log` rc=0 (112 → 120: pass 3 adds two tests × 4 projects). **NOT RUN AND NOT CLAIMED: `check-all.sh`, the full 4-project visual suite, `npm run build`, any real-device measurement.** **GATES STILL UNCHANGED: `G26-LIB` OPEN and not advanced, `epic-53` `in-progress`, Story 53.3 § 11 blank, § 9 empty, Decision BA unedited. No human review claimed. Nothing committed, nothing deployed.** A passing `bmad-code-review` re-review, Aider (`laura-aider-review-diff`, T5) and the controller fullgate are all still owed. |
| 2026-08-01 | **Native `bmad-code-review` FINAL FINISH PASS → `APPROVED`** after controller-applied claims-layer cleanup for BLOCKING-8/BLOCKING-9 and NB-8 (log `.hermes/run-logs/t_962a3d46-bmad-code-review-final-20260801_045810.log`, Claude session `899e22d7-5eba-4021-832c-e6227b6bce83`). Approval scope is **native review only**: `check-all.sh`, Aider, merge/deploy, and § 9 physical Brave retest remain owed; `G26-LIB` stays open and `epic-53` stays `in-progress`. |
| 2026-08-01 | **CHANGELOG TABLE HYGIENE, mechanical only.** A Claude permission denial had left this table's rows malformed; the repair re-formed the row boundaries and nothing else. **No claim was added, removed, strengthened or weakened by it**, and no product code, test, baseline or locale was touched. |
| 2026-08-01 | **INDEPENDENT AIDER REVIEW RAN — literal verdict `REQUEST_CHANGES`, `rc=0`** (`.hermes/run-logs/aider-review-53-4-20260801_053242.log`, `laura-aider-review-diff`, the routine default per the Laura Agent Rulebook; Gemini is not a default reviewer and Codex was not used). **This is recorded as `REQUEST_CHANGES`, NOT as an Aider `APPROVE`.** The controller arbitrated it finding-by-finding (§ 12) and found **no code or product blocker**: the "missing Aider review" finding is **self-referential and discharged by this very run**; the "check-all is OWED" finding was an **intentionally sequenced** debt that this run's successor discharges; the "no real-device measurement" and "§ 9 empty" findings are **already-explicit residuals the dev agent cannot discharge** and which must stay open (`§ 9` empty, `G26-LIB` OPEN, physical Brave retest still to be REQUESTED); and the ">3× page-scale bound" and "Chromium-only validation" findings are **already ledgered deferred work** (`DW-53.4-C` and the Chromium-only entry), not blockers to this scoped repair. No new security issue and no missing test requiring a code change was raised. **Zero code, test, baseline or locale change was made in response.** |
| 2026-08-01 | **CONTROLLER FULLGATE — `infra/scripts/check-all.sh` STANDALONE, ALL GREEN, run AFTER the Aider review.** `.hermes/run-logs/check-all-53-4-20260801_053329.log`, **`rc=0`**, summary **`passed: 16`**, **`all green.`**, 16/16 stages. `apps/web visual regression` **826 passed / 50 skipped / 0 failed**; **zero baseline PNG changes**, so D-7's triage candidate set stayed empty and **no `baseline-reviewed:` line is owed**. **AC-7's check-all leg is DISCHARGED** and the withdrawal recorded under BLOCKING-4 is now superseded by a run that genuinely covers this tree. Status **`in-progress` → `done`**, where **`done` = the code-side merge gate is discharged and the branch is READY TO COMMIT + FF-MERGE** (the Story 53.3 precedent, verbatim). **NOT committed, NOT merged, NOT pushed, NOT deployed, NO post-deploy smoke, and the § 9 physical Brave retest is NOT YET REQUESTED — T6 and T7 stay unchecked and controller-owned.** **GATES UNCHANGED: `G26-LIB` STAYS OPEN and is NOT advanced; `epic-53` STAYS `in-progress`; Story 53.3 § 11 STAYS BLANK; § 9 STAYS EMPTY; Decision BA unedited.** **No human review, NOT an Ezop signature, no physical retest run or claimed.** |

---

## 11. Validation record (native `bmad-create-story` Validate action, 2026-08-01)

**Verdict: ✅ PASS WITH CORRECTIONS — 6 applied, 0 waived, 0 blocking.** The artifact is validated-of-record. `G26-DEVGO` is **unchanged and still OPEN** — validation is not authorization (§ 0).

**Provenance.** Run by repo-local Claude Opus 5 (`claude-opus-5[1m]`) executing the native `bmad-create-story` **Validate** action against `.claude/skills/bmad-create-story/checklist.md`, at `main` @ `36edc9c`, in a **fresh session separate from the killed create/validate session**. This supersedes the empty-record caveat this section previously carried: that caveat described a session that never got here, and it was correct until this run. **No human reviewed this artifact. Not an Ezop signature.** Author of record is the agent, not the operator.

**Scope of the run.** Story artifact + status artifacts only. Zero product code, zero tests, zero baselines, zero locale files, no branch, nothing committed. The story remains a planning artifact.

### 11.1 Re-measurement of § 2 — all thirteen rows hold

Every `VERIFY-AT-CREATE-STORY` row was re-derived from the tree this run rather than read back from the story. **No row was corrected**, which is itself the finding: § 2 is trustworthy and the dev agent may rely on it.

| Row | Re-measured this run | Result |
|---|---|---|
| V-1 | `ImageFullscreenViewer.tsx:870` className verbatim; image caps at `:938` | ✅ exact |
| V-2 | `infra/.last-deploy-sha` = `1906498…`; `git diff --quiet 1906498 36edc9c -- apps/web/src apps/web/tests apps/web/index.html` → **exit 0** | ✅ exact |
| V-3 | `zoom.ts:13` `MIN_SCALE = 1`; no fit-ratio computation anywhere | ✅ exact |
| V-4 | viewer comment `:838-869` and spec comment `:265-268` do assert opposite pairings; `grep -rn visualViewport apps/web/src apps/web/tests` → **0 hits** | ✅ exact |
| V-5 | `forceHorizontalPageOverflow` at `:128-140`; overflow test at `:325-331` calling `assertContained(…{overflow:true})` **and** `assertDismissible` | ✅ exact |
| V-6 | `playwright.config.ts:18-35` — exactly 4 projects, `mobile-*` = `devices["Pixel 5"]` | ✅ exact |
| V-7 | `index.html:5` — `width=device-width, initial-scale=1.0`, no `viewport-fit`, no `user-scalable` | ✅ exact |
| V-8 | the `max-w-[calc(100%-2vw)]` comment and its `clientWidth == innerWidth == 100vw == 1280` parenthetical are present verbatim | ✅ exact |
| V-9 | toolbar at `:1068`, `inset-x-0` + `items-center`, sibling of the chrome layer, outside the transform layer | ✅ exact |
| V-10 | `ui/dialog.tsx:56` ships `fixed top-1/2 left-1/2 … -translate-x-1/2 -translate-y-1/2 … max-w-[calc(100%-2rem)] … sm:max-w-sm` | ✅ exact |
| V-11 | `en.json` and `pl.json` both flatten to **1050**; 14 `catalog.image_viewer.*` keys; **zero** en-only keys | ✅ exact |
| V-12 | all seven cited `deferred-work.md` entries re-read; all seven still `OPEN` | ✅ exact |
| V-13 | `deferred-work.md:259-261` does record the 54.2 threshold finding as RESOLVED | ✅ exact |

Every other file path the story cites was existence-checked and every `AGENTS.md`, `architecture.md`, `prd.md`, `epics.md` and SCP anchor was opened. **One citation was wrong** — C-4 below. `prd.md:2256/2265/2267`, `architecture.md:3371-3376`, `epics.md:4581-4585` and `AGENTS.md` §§ "Story branches" / "Deploy gate" / "Execution discipline" / "Pre-push hook policy & gate evidence" / "Deployment" all resolve as cited.

### 11.2 Corrections applied

| # | Class | Finding | Correction |
|---|---|---|---|
| **C-1** | 🚨 Critical — missing quality gate | **`NFR26-DETERMINISM-1` was absent from the story entirely.** `epics.md:4421` binds the 3× determinism triple to **all** Initiative 26 stories, and 49.1–49.5, 50.1, 50.2, 51.1, 51.2 and 51.4 each carry it as an explicit AC with logged evidence. AC-7 and T5 required only a single `check-all.sh`, which runs each suite **once** — so a dev agent following this story verbatim would merge without the triple. (53.2 and 53.3 also omit it; that is a gap in those stories, not a precedent.) | New **AC-11**; new T5 subtask requiring `npm run test` ×3 with identical counts teed to `.hermes/run-logs/`, and an explicit pytest posture statement. |
| **C-2** | 🚨 Critical — regression blind spot | **D-6/AC-5 named four pre-existing tests, all in `image-viewer-containment.spec.ts`, and omitted the two a box-geometry repair threatens most.** `image-viewer-zoom.spec.ts:194-220` (`toolbar geometry is invariant across zoom levels`) captures the toolbar `boundingBox` before/after zoom and asserts it did not move — the executable form of V-9, and precisely what re-anchoring the toolbar's containing box breaks. `:177-192` asserts the ≥44×44 target-size floors from `boundingBox()`. Neither was named anywhere in the story. | D-6 gained a sixth bullet; AC-5 now reads **all six**; T4 updated; both added to § 7 References. |
| **C-3** | ⚡ Enhancement — vague instruction | **D-7 said "expect baseline churn" without naming a single PNG**, leaving the dev agent to discover the candidate set at gate time. | D-7 now enumerates all **16** viewer baselines (4 under `catalog-detail.spec.ts/`, 12 under `image-viewer-zoom.spec.ts/`) and flags the four `image-viewer-error-*` PNGs as the most sensitive — 54.2 AC-7 only just re-settled them, so movement there needs its own explanation rather than a default `stale-baseline` label. |
| **C-4** | 🚨 Critical — broken citation | **`project-context.md` § "Visual baseline triage before regen" does not exist.** The rule lives at **`AGENTS.md:341`**. `project-context.md` carries only the Baseline Acceptance Gate (`:243-245`). The story cited the phantom section twice (D-7 and References), inheriting the same miscitation from Story 53.3 § 8. A dev agent would have gone looking for a section that is not there. | Both citations repointed to `AGENTS.md:341`, with the inherited error named so it stops propagating. `project-context.md`'s real anchors (`:110`, `:243-245`, `:287`) now carry line numbers. |
| **C-5** | 🚨 Critical — unsatisfiable AC | **AC-4 demanded ZERO diff to `index.html`, `zoom.ts` and the locale files while § 5 classes all three as `Ask First`, not `Never`.** H3 makes `viewport-fit=cover` a live candidate. As written, a controller-granted `index.html` change would leave the story unable to satisfy its own AC-4 — a deadlock between the AC and the escape hatch the story itself provides. | AC-4 split by § 5 class: `Never` files are unconditional zero-diff; `Ask First` files are satisfied by zero diff **or** by an explicit controller grant recorded verbatim in § 12. An **ungranted** change still fails AC-4 exactly as a `Never` change does. |
| **C-6** | ⚡ Enhancement — misleading guidance | **§ 7 told the dev agent jsdom has no layout engine — true for rects, and misleading about `className`.** `ImageFullscreenViewer.test.tsx:280-282` asserts the close button's class list contains `h-11`/`w-11` and not `h-10`. A control-sizing change goes red in vitest while every Playwright geometry test still passes. | § 7 Testing standards gained the counter-note; the test file added to References. |

**Nothing was waived.** No checklist item was marked "not applicable" to dodge a finding.

### 11.3 Checked and found sound — recorded so the dev agent does not re-litigate

- **Reinvention prevention** (checklist § 3.1): § 7 Project Structure Notes correctly rules that the regression belongs *inside* `image-viewer-containment.spec.ts` because `solidPng`, `openViewerWith`, `boxOf`, `expectWithinViewport`, `assertContained` and `rotate` are file-local and unexported — verified this run. A new spec file would duplicate ~130 lines. No gap.
- **Scope boundaries** (§ 3.5): V-12's seven residuals and § 5's Never list are complete against `deferred-work.md` and SCP § 5.6. No gap.
- **Regression prevention** (§ 3.4): D-5's five rejected shapes, D-6's invariants and AC-6's Decision BA checks cover the failure modes. C-2 was the one hole.
- **Evidence-class honesty** (§ 0, D-8, AC-9, AC-10): the Brave-vs-Chrome and defect-vs-gesture-acceptance splits are stated correctly and consistently in every place they appear. The § 9 request block is correctly empty. **`G26-LIB` is not advanced by this story and is not advanced by this validation.**
- **The containment suite owns zero baselines** — confirmed: `grep -c toHaveScreenshot` on it returns **0**, and no `__snapshots__/image-viewer-containment.spec.ts/` directory exists.

### 11.4 What this validation does NOT establish

- **It is not code authorization.** `G26-DEVGO` stays 🔓 **OPEN**. `ready-for-dev` is an artifact status. See § 0.
- **It is not a diagnosis.** The Validate action did not reproduce the defect, did not run Playwright, did not touch a device, and takes no position on H1–H4 or on which reading of V-4 is correct. **Settling V-4 remains the dev pass's job, by measurement (T1), not by citing § 11.**
- **It is not human review**, not an Ezop sign-off, and not operator evidence of any kind.
- **`epic-53` stays `in-progress`; Story 53.3 § 11 was not touched and stays blank.**

_See § 12 for the dev agent's own record._

---

## 12. Dev Agent Record

### Agent Model Used

Repo-local **Claude Opus 5** (`claude-opus-5[1m]`) executing native `bmad-dev-story` on branch `fix/E53.4-android-chromium-lightbox-fit-repair`, branched from `main` @ `36edc9c`. Session-start `bmad-help` handshake was run and returned `bmad-dev-story` as the canonical entry (phase `4-implementation`, `preceded-by: bmad-create-story:validate`, `required=true`).

**Branch-name deviation, recorded not hidden.** The controller's dev-go message named `feat/E53.4-…`; § 6 T0 of this story and `AGENTS.md` § "Story branches" both prescribe the `fix/` prefix for a defect repair, and the controller's own wording deferred to repo policy ("according to repo policy"). The branch is therefore `fix/E53.4-android-chromium-lightbox-fit-repair`. Renaming it is one command if the controller wants the literal `feat/` name.

### Debug Log References

All logs under the gitignored `.hermes/run-logs/`.

| Evidence | Path |
|---|---|
| AC-2 **RED** (before the fix) | `53-4-RED-20260801_02*.log` |
| AC-2 **GREEN** (after the fix) | `53-4-GREEN-20260801_02*.log` |
| AC-5 six pre-existing pins + both viewer specs, 4 projects | `53-4-viewer-specs-20260801_02*.log` |
| AC-7 full 4-project visual suite | `53-4-visual-full-20260801_03*.log` — **STALE: pre-dates both review-fix passes** |
| AC-5 / BLOCKING-3, both viewer specs × 4 projects, **three consecutive runs on the current tree** | `53-4-reviewfix2-viewer-specs-run{1,2,3}-20260801_04*.log` |
| AC-11 determinism, `npm run test` ×3, **current tree** | `53-4-controller-vitest-after-fix3-run{1,2,3}-20260801_0503*.log` (the earlier `53-4-reviewfix2-vitest-run{1,2,3}-20260801_041500.log` and `53-4-vitest-run{1,2,3}-20260801_03*.log` sets are **STALE** for the current tree) |
| AC-7 `check-all.sh` standalone — **DISCHARGED** | `.hermes/run-logs/check-all-53-4-20260801_053329.log` — **`rc=0`, `passed: 16`, `all green.`**, run 05:33→05:46 **after** the Aider review, over the current tree. Visual regression **826 / 50 skipped / 0 failed**, zero baseline PNG changes. *(The two earlier logs remain what BLOCKING-4 said they were and are NOT evidence: `check-all-20260801_030818.log` finished 03:21, before the 03:49 BLOCKING-1 fix; `53-4-reviewfix-check-all-20260801_035047.log` is truncated mid-`apps/api pytest`.)* |
| Independent **Aider** review (T5) — **RUN, literal `REQUEST_CHANGES`** | `.hermes/run-logs/aider-review-53-4-20260801_053242.log` — `rc=0`, verdict text **`REQUEST_CHANGES`**. Arbitrated by the controller; **not recorded as an APPROVE**. See § 12 "Independent Aider review". |

#### AC-1 — the condition, measured **in emulation** and **inferred** on the device

> **Scope of the word "measured", stated before the numbers (2026-08-01 review fix, BLOCKING-2).** Every metric in this section was read from **headless/emulated Chromium** driven by Playwright + CDP. **No measurement was taken on the reporting handset — the dev agent has no device access, and T1's device subtask is marked `NOT PERFORMED` for exactly that reason.** On the real device the condition is therefore **INFERRED** — from the three operator screenshots (the toolbar cut lands where the emulated geometry says it must) plus the fact that the divergence is a spec-level property of every mobile engine, not a Chromium quirk. **Confirming it on the device is § 9's job (AC-9), and § 9 is empty.** In particular, if the real Brave/Android-17 cause is H3 (edge-to-edge chrome) and `visualViewport` misreports the box there too, this repair is still correct and would still not fix the reported defect — that possibility is open until the physical retest returns.



**Environment of the field report** (from the SCP § 2, which re-hashed the three PNGs; transcribed as model + OS build only, never the IMEI): **Pixel 9 Pro**, **Brave 1.92.144 / Chromium 150.0.7871.186**, **Android 17, Build/CP2A.260705.006**, surface `3d.ezop.ddns.net/catalog/361625a5-77e…`, viewer open, zoom-out control rendered disabled ⇒ reset/minimum scale.

**Deployed version string observed at repro time** (AC-1 requires the observed value, not an inferred one): `GET /api/health` → `{"status":"ok","version":"0.1.0"}` on **both** `https://3d.ezop.ddns.net` and `http://192.168.2.190:8090`, read this run. Deployed bundle served at repro time: `assets/index-C806VXXe.js` / `assets/index-BruAafyw.css`. **Recorded honestly: `version` is a static `0.1.0` and does NOT identify a build**; the bundle hash is the only build-identifying string the running artifact exposes. `main` SHA under test: **`36edc9c`**; `infra/.last-deploy-sha` = `1906498`, and V-2's `git diff --quiet 1906498 36edc9c -- apps/web/src apps/web/tests apps/web/index.html` → exit 0 still holds, so the viewer source under test is the source on `main`.

**THE CONDITION.** *The visual viewport is narrower than the layout viewport.* Every viewport-relative quantity the viewer used — `w-[98vw]`, `left-[1vw]`, `max-w-[calc(100%-2vw)]`, `h-[95dvh]`, `top-[2.5dvh]` — resolves against the **layout viewport**, and `position: fixed` is laid out in that same box. The **visual** viewport is the region the user can see. On a phone the two diverge whenever the page is pinch-zoomed, which must remain available because `user-scalable=no` is banned (`EXPERIENCE.md:291`, `architecture.md:3374`). The condition is stated as the **divergence**, not as one cause of it, so the repair holds for every cause (page pinch, browser zoom setting, any Brave/Android-17 chrome behaviour that shrinks the visible region).

**Measured, `mobile-light`, viewer open at reset scale, page scale factor 2 — BEFORE the fix:**

| metric | value |
|---|---|
| `window.visualViewport.width` | **196.5** |
| `document.documentElement.clientWidth` | 393 |
| `window.innerWidth` | 393 |
| used `100vw` (fixed probe element) | 393 |
| used `100%` of a `position:fixed` box | 393 |
| dialog rect | `3.92 → 389.05` (w 385.13) — **192.55px outside the visible region** |
| zoom toolbar rect | `124.48 → 268.48`, centre **196.48** |
| close button rect | `333.05 → 377.05` — entirely outside the visible region |

The visible right edge sits at 196.5, and the toolbar's centre is 196.48 — so the cut falls **inside the zoom-out (`−`) button**. That is SCP § 2.1 observation 4 (*"the `−` button's circle is sliced"*) reproduced from geometry alone, and it is what makes the diagnosis explain the **toolbar** and not only the photo (V-9): the toolbar is centred with `inset-x-0` on a dialog box that is itself mostly off-screen.

**The repro is AUTOMATED** (D-2 preference 1). It lives in `image-viewer-containment.spec.ts` and runs on all four projects. Playwright cannot pinch; CDP `Emulation.setPageScaleFactor` produces the same visual-viewport-narrower-than-layout-viewport relation deterministically, and the relation *is* the condition. Stated plainly: **the page-scale factor is a stand-in for a device pinch, and the equivalence claimed is geometric, not behavioural.**

#### AC-3 — why the green suite could not fail, mechanically

Three independent reasons, each measured this run. *"We were missing an overflow test"* is refuted, as V-5 said it would be.

1. **The horizontal-overflow case already exists and is green (V-5) — and it cannot express this class.** Measured with `forceHorizontalPageOverflow` on `mobile-light`: `innerWidth` **593**, `scrollWidth` **593**, but `clientWidth` **393**, `visualViewport.width` **393**, used `100vw` **393**. It grows the document, never the visual/layout divergence. The dialog measured `3.92 → 389.05` inside 393 — genuinely contained. That test was right, and blind.
2. **Every containment assertion measured against the box the geometry is derived from.** `assertContained` read `document.documentElement.clientWidth`, which reports the **layout** viewport — the same box `98vw` is a percentage of. `1vw + 98vw ≤ clientWidth` is arithmetically true by construction **at every page scale**. The assertion was not missing; it was **vacuous** with respect to this defect class. Repaired as a D-4 contract correction (below).
3. **Nothing consulted `window.visualViewport` (V-4), and it is the only API that reports the visible region.** Re-measured: `grep -rn visualViewport apps/web/src apps/web/tests` → 0 hits before this story. The contract was not expressible in the terms the suite was written in.

V-8's `clientWidth == innerWidth == 100vw` equality is the emulation artefact both other reasons rest on: where three metrics are equal, no divergence of any kind is representable.

#### V-4 SETTLED BY MEASUREMENT — both shipped comments were wrong, in opposite directions

| Claim | Verdict | Measurement |
|---|---|---|
| `ImageFullscreenViewer.tsx:840-848` — *"`w-[98vw]` resolves against the VISUAL viewport"* | ❌ **FALSE** | used `100vw` = 393 = layout viewport, while the visual viewport was 196.5 at page scale 2. `vw` resolves against the layout viewport, always. |
| `image-viewer-containment.spec.ts:265-268` — *"`clientWidth` tracks the VISUAL viewport; `innerWidth` tracks the layout viewport"* | ❌ **FALSE, both halves** | page scale 2: `clientWidth` 393 vs visual 196.5 (so `clientWidth` is layout, not visual). Page overflow: `innerWidth` 593 vs `clientWidth` 393 (so `innerWidth` is neither metric reliably). |

Neither comment is repaired by citing the other. `window.visualViewport` is the only correct source, which is exactly the fifth possibility § 8 asked to be held open — the CSS was doing what CSS says, and the *measurement premise* was the wrong part.

#### AC-2 — RED before, GREEN after (same command both times)

```
npx playwright test --config=tests/visual/playwright.config.ts \
  image-viewer-containment -g "narrower than the layout viewport" --reporter=list
```

**RED, on unmodified product code — 8 failed, 0 passed** (4 projects × 2 scale factors), failing on the contract assertion:

```
Error: dialog right edge is inside what the user can see
expect(received).toBeLessThanOrEqual(expected)
    Expected: <= 197.5          (mobile-*, page scale 2)
    Received:    389.046875
    Expected: <= 263            (mobile-*, page scale 1.5)
    Received:    389.046875
```

**GREEN, after the fix — 8 passed (8.9s), 0 failed.**

**Verified green for the right reason, by re-reading the numbers rather than trusting the assertion** (T3). Same probe, same page scale 2, `mobile-light`, after the repair:

| | before | after |
|---|---|---|
| visible region width | 196.5 | 196.5 |
| dialog rect | `3.92 → 389.05` | **`1.95 → 194.52`** (w 192.56 = 0.98 × 196.5) |
| dialog left inset | 3.92 (= 1% of 393) | **1.95 (= 1% of 196.5)** |
| toolbar rect | `124.48 → 268.48` (centre 196.48, sliced) | **`26.23 → 170.23`** (centre 98.2 = half of 196.5) |
| close button rect | `333.05 → 377.05` (off-screen) | **`138.52 → 182.52`** |

At page scale 2.5 the dialog measures `1.56 → 155.61` inside a 157.2-wide region. The overflow is gone because the box is now derived from the visible region, not hidden behind a clamp.

#### D-4 contract correction — applied, and labelled as one

`assertContained` and `assertChromeContained` now take their reference box from `window.visualViewport` via a new `visibleRegion()` helper, with `expectWithinVisibleRegion()` stating the contract at the assertion site. The correction is carried in a comment block at the assertion with the numbers that forced it. Consequences recorded rather than glossed:

- **A `zoom toolbar` assertion was ADDED to both standing helpers** — `assertContained` (`image-viewer-containment.spec.ts:354`) and `assertChromeContained` (`:577`) each now also assert `expectWithinVisibleRegion("zoom toolbar", …)`. This edit was omitted from the first version of this list and is named here after the 2026-08-01 native `bmad-code-review` (non-blocking finding 4). It is **additive** — no existing assertion was weakened or removed by it — and it is the assertion that makes the standing helpers cover the control the device evidence actually shows sliced (V-9). Every pre-existing pin still passes with its own body unchanged.
- The dead `expectWithinViewport` helper was **removed**, not left standing: it tested against a 0-origin box, and `visualViewport.offsetLeft/offsetTop` are non-zero whenever a zoomed page is panned, so it could not express containment in that state at all.
- The `scrollWidth` check deliberately **keeps** `clientWidth` as its reference — `scrollWidth` is a layout-viewport-space quantity and that pairing was always correct. It is not part of the correction.
- The four pre-53.3 test bodies and every 53.3 addition are **byte-identical**. `git diff main -- apps/web/tests/visual/image-viewer-containment.spec.ts` touches helpers and appends the new section only.

#### AC-4 / AC-6 — the fix, and its boundaries

**Root cause repaired, not masked.** The viewer measures `window.visualViewport` (`width`, `height`, `offsetLeft`, `offsetTop`) and publishes the derived geometry as CSS custom properties on the dialog element, driven by `visualViewport` `resize` + `scroll` listeners through a callback ref (Base UI portals the popup, so the same callback-ref pattern `attachFrame` already uses is required). **CSS has no unit for the visual viewport**, so no choice of unit could have expressed this — that is the finding, and it is why the repair needs JS at all.

None of D-5's five rejected shapes was used: no `overflow-x: hidden`, no image shrink, no `maxScale`/`BASE_MAX_SCALE` cap, **no `left-1/2` + `-translate-x-1/2`**, no UA/browser branch.

The shipped ratios are **unchanged** and named (`VIEWER_WIDTH_RATIO = 0.98`, `VIEWER_INSET_X_RATIO = 0.01`, `VIEWER_HEIGHT_RATIO = 0.95`, `VIEWER_INSET_Y_RATIO = 0.025`), and every class keeps the original expression as the `var()` fallback — `w-[var(--viewer-w,98vw)]`, `h-[var(--viewer-h,95dvh)]`, `left-[var(--viewer-left,1vw)]`, `top-[var(--viewer-top,2.5dvh)]`, `max-w-[var(--viewer-w,calc(100%-2vw))]`, `sm:max-w-[var(--viewer-w,calc(100%-2vw))]`, `max-h-[var(--viewer-img-max-h,calc(95dvh-5rem))]`. Where `visualViewport` is unavailable (jsdom, SSR, older engines) the rendered geometry is byte-identical to what shipped; where the two viewports agree the computed values are numerically identical. That is why **1139 vitest tests and 814 visual assertions passed with zero baseline regeneration**.

> **Correction applied 2026-08-01 after native `bmad-code-review` (BLOCKING-1).** The first version of this fix shipped `max-w-[var(--viewer-w,98vw)]` / `sm:max-w-[var(--viewer-w,98vw)]`, which made the byte-identical claim above **FALSE on the fallback path**: the shipped cap is `calc(100%-2vw)`, and `98vw` equals it only where the classic-scrollbar gutter is zero — i.e. everywhere *except* the platform class E48.1 wrote the cap for. The fallback now carries the shipped expression verbatim, so the claim is true as written. Verified in the compiled stylesheet, not asserted: `npm run build` → `dist/assets/index-*.css` contains `max-width:var(--viewer-w, calc(100% - 2vw))` twice (base + `sm:`), so Tailwind resolves the nested `var()`-fallback-with-`calc` arbitrary value correctly. `--viewer-w` is set on the same element whenever `visualViewport` exists, so the measured path is unaffected — 108/108 on both viewer specs before and after this change.

`dvh` is used and `vh` is not. `sm:max-w-` is **deliberately superseded, not dropped** (AC-6, V-10) — and superseded only on the MEASURED path: there it existed to subtract a classic-scrollbar gutter that `vw` counted and `100%` did not, and `visualViewport.width` excludes that gutter by definition, so H2's untested counterweight is unnecessary rather than untested. On the **fallback** path E48.1's counterweight is carried through unchanged. Either way the cap is kept explicit so the element can never silently fall back to `ui/dialog.tsx`'s `sm:max-w-sm`.

**Zero-diff proven mechanically** — `git status --porcelain -- apps/ infra/ workers/` reports exactly two files:

- § 5 **`Never`** — `ui/dialog.tsx`, `imageViewer/types.ts`, `routes/share/*`, `ModelGallery.tsx`, `package.json`, `package-lock.json`: **all zero-diff.**
- § 5 **`Ask First`** — `apps/web/index.html`, `imageViewer/zoom.ts`, both locale files: **all zero-diff. No controller grant was needed and none was requested.** H3's `viewport-fit=cover` candidate was not exercised; the repair did not require it.

#### AC-5 — inspectability above 1.0

`MIN_SCALE`, `BASE_MAX_SCALE`, `ZOOM_STEP`, `DOUBLE_TAP_SCALE` and `resolveMaxScale` are untouched (`zoom.ts` zero-diff). **All six** D-6 pins pass **with their bodies unchanged**, verified by running them — geometry matrix, ceiling, clamp/reset and rotation refit in `image-viewer-containment.spec.ts`, plus `image-viewer-zoom.spec.ts`'s toolbar-geometry-invariance (`:194`) and target-size-floor (`:177`). Both viewer specs, all four projects: **112 passed / 12 skipped / 0 failed** (108 before the review-fix pass added the panned-page test; see below). The two page-scale regressions additionally drive the toolbar for real (zoom in → reset → dismiss) under the divergence rather than only measuring it; the panned-origin regression proves reachability by hit test instead, for the coordinate-space reason recorded under "Review-fix pass 2".

#### Review-fix pass — native `bmad-code-review`, 2026-08-01

Review log: `.hermes/run-logs/t_962a3d46-bmad-code-review-20260801_033228.log`. Verdict **REQUEST_CHANGES** — 2 blocking (both in the CLAIMS layer, neither requiring a logic change), 4 non-blocking, 7 dismissed as noise. Applied in a follow-up pass on the same branch, **nothing committed**. What each one did:

| Finding | Disposition | Where |
|---|---|---|
| 🔴 **BLOCKING-1** — the fallback `max-w-[var(--viewer-w,98vw)]` silently dropped E48.1's `calc(100%-2vw)` scrollbar-gutter cap, so this record's "byte-identical fallback" claim was false on exactly the platform class the cap was written for | **FIXED IN CODE** (the stricter of the two options the review offered): both fallbacks are now `var(--viewer-w,calc(100%-2vw))`. Comments in `ImageFullscreenViewer.tsx` and the AC-4/AC-6 block above corrected so the claim is true rather than qualified | `ImageFullscreenViewer.tsx:265-273`, `:947-956`, `:962` |
| 🔴 **BLOCKING-2** — T1 was checked `[x]` while its own text demands a measurement "on the real device", which was never taken | **FIXED IN THE RECORD.** T1 split: the browser/Playwright measurement stays `[x]`, the device measurement is a separate **unchecked** subtask marked `NOT PERFORMED — no device access`. § 12 AC-1 now opens with the scope of the word "measured"; § 10's "settled BY MEASUREMENT" is qualified to *in emulation*, with the device condition named as **inferred** and its confirmation left to the empty § 9 | § 6 T1, § 12 AC-1 header, § 10 row 4 |
| 🟡 **NB-1** — `visualViewport.offsetLeft`/`.offsetTop` and the `scroll` listener had **zero** coverage: page scale alone leaves the visible region's origin at `0,0` | **TEST ADDED**, not deferred. `the viewer follows the visible region when the user pans a zoomed page` pans the scaled page via CDP `Input.synthesizeScrollGesture` (wheel source — a touch gesture is consumed by the page) **after** the viewer is open, so only a live `scroll` listener can pass it. **Verified red for the right reason (D-3):** with both offset terms deleted from `syncVisibleRegion`, `mobile-light` fails with `dialog left edge … Expected >= 119, Received 1.953125`; restored, 4/4 projects green | `image-viewer-containment.spec.ts` — `panVisibleRegion` helper, `the viewer follows the visible region when the user pans a zoomed page` test. *(Line citations `:882-920` / `:975-1030` stood here and were **wrong** — review re-run #2 NB-7. They are replaced by names rather than re-numbered: three later passes moved the same code twice, and a name does not rot. Current positions: helper `:902`, test `:1079`.)* |
| 🟡 **NB-2** — page pinch no longer magnifies the lightbox; an unrecorded trade-off | **RULED AND LEDGERED** as an accepted consequence of AC-4 with the reasoning and a § 9 question attached | `deferred-work.md`, § "code review of 53-4-…" |
| 🟡 **NB-3** — the compensation is Chromium-only-validated | **LEDGERED** as a risk without coverage (no divergent engine evidence found; the new panned-page test is the one that would answer it on a non-Chromium project) | `deferred-work.md`, same section |
| 🟡 **NB-4** — the added `zoom toolbar` assertions in the two standing helpers were missing from the D-4 edit list | **NAMED** in the D-4 block above | § 12 D-4 |

**Re-verified after the fixes:** `git diff --check` clean · `npm run typecheck` (`tsc -b`) rc=0 · `npm run build` rc=0, and the compiled `dist/assets/index-*.css` contains `max-width:var(--viewer-w, calc(100% - 2vw))` twice, which is the mechanical proof BLOCKING-1's fix actually reaches the stylesheet · both viewer specs × 4 projects **112 passed / 12 skipped / 0 failed** (`.hermes/run-logs/53-4-reviewfix-viewer-specs-final-*.log`). **Zero baseline churn and zero locale change still hold; every § 5 `Never`/`Ask First` file is still zero-diff.** The two blocking findings were about *claims*, and the code change BLOCKING-1 asked for touches the FALLBACK path only — the measured path is byte-for-byte the same geometry that produced the 108/108 run before it.

> **CORRECTION (review re-run, BLOCKING-3 / BLOCKING-4).** Two claims in the paragraph above did not survive the re-review and are struck here rather than edited away:
> 1. *"`infra/scripts/check-all.sh` re-run standalone (log cited under AC-7)"* — **false**. The log cited under AC-7 pre-dated the BLOCKING-1 fix, and the post-fix run was truncated. See the AC-7 / AC-11 gates block; the leg is **owed**.
> 2. *"112 passed / 12 skipped / **0 failed** … restored, 4/4 projects green"* — **not reproducible as written**. The single run recorded here happened to be green; the reviewer's two independent runs of the same command were **3 failed** and **1 failed**, always the same new panned-page test. See "Review-fix pass 2" below.

#### Review-fix pass 2 — native `bmad-code-review` RE-RUN, 2026-08-01

Review log: `.hermes/run-logs/t_962a3d46-bmad-code-review-rerun-20260801_035348.log`. The re-run **confirmed BLOCKING-1 and BLOCKING-2 resolved** (the compiled stylesheet carries `max-width:var(--viewer-w, calc(100% - 2vw))` ×2; T1 is split with the device subtask unchecked; § 12 AC-1 and § 10 are qualified) and **NB-2/NB-3 ledgered, NB-4 named**. Verdict nonetheless **`REQUEST_CHANGES`** on two new findings, **both in the EVIDENCE layer — neither questions the repair's geometry**. Applied on the same branch, **nothing committed**.

| Finding | Disposition | Where |
|---|---|---|
| 🔴 **BLOCKING-3** — the panned-page test added as NB-1 is **flaky**. The reviewer ran the cited command twice: **3 failed** then **1 failed**, always `the viewer follows the visible region when the user pans a zoomed page`. In isolation (`-g`) it went 4/4 green every time, so it is a load-dependent flake. Every `expectWithinVisibleRegion` assertion passed, including both origin preconditions; the failure was always the *interaction* tail — `desktop-light` timed out in `click()` with the transform layer / strip / overlay intercepting pointer events, `mobile-light` clicked through but never left scale 1. **Mechanism:** Playwright derives the click point from `getBoundingClientRect()` (LAYOUT-viewport space) while CDP's `Input.dispatchMouseEvent` reads it in VISUAL-viewport space; at page scale 2 with a moved origin the two diverge by exactly `offsetLeft`/`offsetTop`, so the synthetic pointer lands off the button. The suite is a **standing** suite inside `check-all.sh`'s `apps/web visual regression` stage, so this made the merge gate intermittently red. | **FIXED IN THE TEST**, taking the reviewer's first option. The geometry half — which is what NB-1 exists for — is **kept verbatim**: both origin preconditions (`region.x > 0`, `region.y > 0`) and all five `expectWithinVisibleRegion` assertions still run, so `visualViewport.offsetLeft`/`.offsetTop` and the `scroll` listener keep exactly the coverage they had. Only the interaction tail changed: `zoomInControl().click()` → `zoomResetControl().click()` → `assertDismissible()` is replaced by a new `expectHittable()` helper that asserts, via `document.elementFromPoint` at the control's own centre, that the control is the topmost element there. `elementFromPoint` takes the *same* client coordinates `getBoundingClientRect()` reports, so it has no coordinate-space split and is deterministic. Applied to **zoom-in** and **close** — both enabled in this state; reset is legitimately disabled at the fit floor and "can a disabled control be hit" is not this story's contract. **Click-through interaction coverage is unchanged and stays where it is deterministic**: the two origin-`0,0` page-scale tests still do zoom in → reset → dismiss for real. | `image-viewer-containment.spec.ts` — `expectHittable` helper + the panned test's tail; `import type { Locator, … }` |
| 🔴 **BLOCKING-4** — the record cited a **pre-fix** `check-all.sh` as if it covered the current tree, and the post-fix run was truncated. | **FIXED IN THE RECORD, by withdrawal rather than by re-run.** The all-green claim is struck in three places (T5 subtask, Debug Log References, AC-7 / AC-11 gates block) and both logs are named with exactly what is wrong with each. **AC-7's check-all leg is now explicitly OWED to the controller fullgate.** No `check-all.sh` was run in this pass, so **nothing here claims one**. | § 6 T5, § 12 Debug Log References, § 12 AC-7 / AC-11 |
| 🟡 **NB-1 (re-run)** — the AC-11 vitest ×3 logs pre-dated the BLOCKING-1 fix. | **RE-RUN on the current tree**; new paths cited in the gates block below. | § 12 AC-7 / AC-11 |
| 🟡 **NB-2 (re-run)** — `sprint-status.yaml` still listed `bmad-code-review` as merely *owed*, with no verdict. | **FIXED IN THE RECORD**: the note now carries both `REQUEST_CHANGES` verdicts, both review-fix passes, and the owed re-review. | `sprint-status.yaml` |

**Verification for this pass, current tree, exact logs — and nothing beyond them:**

- `git diff --check` → clean. `npm run typecheck` (`tsc -b`, from `apps/web/`) → rc=0, no output.
- Both viewer specs × 4 projects, **three consecutive full runs** of the reviewer's own command (`npx playwright test --config=tests/visual/playwright.config.ts image-viewer --reporter=list`) → **112 passed / 12 skipped / 0 failed, rc=0, all three**. Logs: `53-4-reviewfix2-viewer-specs-run{1,2,3}-20260801_04*.log`. Full-suite runs, not `-g`-isolated — the shape under which the reviewer reproduced the flake.
- **What is NOT claimed:** no `check-all.sh` run, no full 4-project visual suite run, no `npm run build`, no real-device measurement. Three green focused runs are **evidence against** the flake, not proof of its absence; the standing suite's final word belongs to the controller fullgate.

#### Review-fix pass 3 — native `bmad-code-review` RE-RUN #2, 2026-08-01

Review log: `.hermes/run-logs/t_962a3d46-bmad-code-review-rerun-2-20260801_041133.log`; triage in Claude session `2a75d88e-fa8f-4280-a535-f4ff1e622183`. The re-run **confirmed BLOCKING-3 resolved** (four independent full-suite-shape green runs against the previous 2-of-2 red, with the five `expectWithinVisibleRegion` assertions and both origin preconditions intact) and **BLOCKING-4 correctly marked OWED rather than falsely claimed**. Verdict nonetheless **`REQUEST_CHANGES`** on three new findings. Unlike passes 1 and 2 — which were claims-layer and evidence-layer — **BLOCKING-5 and BLOCKING-6 are real DEFECTS in the shipped diff**, both of them coupling this story introduced. Applied on the same branch, **nothing committed**.

| Finding | Disposition | Where |
|---|---|---|
| 🔴 **BLOCKING-5** — a `visualViewport` resize resized the frame but never re-ran the zoom/pan refit. `--viewer-w`/`--viewer-h` now size the dialog, so `frame.clientWidth/Height` — the box `clampPan` measures legal travel against — and `img.offsetWidth` — the box the zoom ceiling derives from — **became functions of `visualViewport` in this diff**. A page pinch fires `visualViewport.resize` and **not** `window.resize`, and the refit effect listened on `window` only. Photo zoomed to 3× and panned to the edge, user pinches the page → frame halves → `panRef` keeps ~2× the legal travel (dead background dragged into view) and the ceiling is stale. **This coupling did not exist before this diff.** | **FIXED IN CODE.** The `visualViewport` `resize`/`scroll` subscription MOVED from the geometry effect into the refit effect, so there is exactly **one** handler and **one** subscription rather than two racing listeners: `syncVisibleRegion()` publishes the new geometry at the top of the handler, *then* the ceiling is re-derived and `commit()` re-clamps against the box that now exists. Order is explicit rather than a function of effect-declaration order, and the write count per event stays at one. `commit()` additionally gained an **identity-reuse guard** — `clampPan` returns a fresh `Vec2` every call, so with `scroll` now a commit source (one per compositor frame while panning a pinched page) `setPan` would have re-rendered a `backdrop-blur` fullscreen layer every frame on exactly the low-end Android class this defect came from; reusing the previous object when the clamp lands on the same pair makes React bail instead. | `ImageFullscreenViewer.tsx` — `useLayoutEffect` geometry publish, the refit `useEffect`, `commit` |
| 🔴 **BLOCKING-6** — the contract was unverified above the tested page-scale range and the toolbar has a fixed 144px max-content width. **MEASURED first, then fixed** — the review's ~2.7× estimate was close but the real break is at **~2.45×**, and there is a **second cause it had not named**. `mobile-light`, before: at scale 3 the region is 131px wide, the toolbar's right edge is at **152.30** and the close button's at **147.30**. The close button was riding a floor the review never looked at: `DialogContent` is a **grid**, so the viewer root is a grid item whose `min-width: auto` pinned it at the thumb strip's **158px min-content** — the root stayed 158px wide inside a 128px dialog, i.e. the whole viewer escaped the box it had just been taught to fit. | **FIXED IN CODE, minimally — no redesign, no control removed, no target shrunk.** Three classes: `min-w-0` on the root (the strip already carries `overflow-x-auto`, so shrinking past its content scrolls it rather than clipping anything); `flex-wrap` + `justify-center` on the toolbar; `shrink-0` on the three buttons so the re-flow cannot buy containment by squeezing targets below 40×40. At page scale 1 all three are no-ops (144px against a 385px dialog) — **zero baseline churn, measured, not assumed**. | `ImageFullscreenViewer.tsx` — viewer root, toolbar, 3 toolbar buttons |
| 🔴 **BLOCKING-7** — `expectHittable` was an occlusion check only, while the record claimed reachability. `document.elementFromPoint` is not clipped to the visible region, so under the 0-origin regression the panned test exists to kill, the button is unoccluded and the check **passes**. | **FIXED IN THE TEST — the claim made true, not retracted**, which is the option the review preferred. `expectHittable` now takes the `region` and asserts the **hit-tested point** lies inside it *before* asserting topmost-ness. **Proven to have teeth, measured:** with the 0-origin regression injected (the `offsetLeft`/`offsetTop` terms dropped from the published geometry), the old occlusion-only check returns **PASS** on a control whose centre is at y=43 while the visible region starts at y=80 — the new region bound returns **FAIL**. Both projects probed, identical verdicts. | `image-viewer-containment.spec.ts` — `expectHittable` `:1056`, both call sites |
| 🟡 **NB-2** — `panVisibleRegion` polled `offsetLeft + offsetTop` while the test hard-asserts **both** axes with no retry. | **FIXED**: the poll is now `Math.min(offsetLeft, offsetTop)`, which gates on the slower axis. | `image-viewer-containment.spec.ts:902` |
| 🟡 **NB-5** — `"SSR"` named as a fallback path in a Vite SPA with no server render. | **FIXED**: the word is removed; the fallback list reads `jsdom, older engines`. | `ImageFullscreenViewer.tsx` `syncVisibleRegion` comment |
| 🟡 **NB-7** — stale line citations for the panned test and its helper. | **FIXED** by replacing the numbers with names (they had already rotted twice); current positions noted parenthetically. | § 12 pass-1 NB-1 row |
| 🟡 **NB-1** — `--viewer-img-max-h` had **zero** tests that fail if the write is deleted. | **FIXED WITH A TEST, not ledgered.** The two page-scale tests now assert the photo's *used* `max-height` equals `0.95 × visualViewport.height − 5rem`, with a precondition that this differs from the `calc(95dvh−5rem)` fallback by >50px — so deleting the write makes the `dvh` fallback apply and the assertion fail. | `image-viewer-containment.spec.ts`, the `1.5×`/`2×` loop |
| 🟡 **NB-3** — no floor on the published sizes; tiny visual-viewport heights. | **LEDGERED, not fixed** — see DW-53.4-C below and "what is NOT claimed". | `deferred-work.md` |
| 🟡 **NB-4** — unthrottled `setProperty` per `visualViewport.scroll`. | **PARTLY ADDRESSED as a side effect of BLOCKING-5**: consolidating two subscriptions into one halves the per-event write count, and the `commit` identity guard removes the per-frame re-render that BLOCKING-5's fix would otherwise have added. The `setProperty` calls themselves are still unthrottled — **not claimed fixed**. | `ImageFullscreenViewer.tsx` |
| 🟡 **NB-6** — `visibleRegion()`'s fallback reverts to the vacuous D-4 box without `visualViewport`. | **NOT CHANGED.** Adjacent to the already-ledgered Chromium-only entry, which is where it belongs; no new entry filed. | — |

##### ⚠️ AC-2 IS SATISFIED OVER A MEASURED RANGE, NOT UNLIMITED

This is the honest headline of pass 3 and it is stated before the green numbers, not after them. **BLOCKING-6 raised the bound; it did not remove it.** Measured after the repair, `mobile-light` portrait, toolbar top edge vs the visible region:

| page scale | region.h | frame.h | toolbar rows | top slack | verdict |
|---|---|---|---|---|---|
| 3 | 242.33 | 150.20 | 2 × 40 = 96 | **+44.25** | contained |
| 3.5 | 207.71 | 117.33 | 2 × 40 = 96 | +10.52 | contained *(but see below)* |
| 4 | 181.75 | 92.66 | 2 × 40 = 96 | **−14.81** | **OUT** |
| 4.5 | 161.56 | 73.47 | 3 × 40 = 144 | −82.50 | **OUT** |
| 5 | 145.40 | 58.13 | 3 × 40 = 144 | −98.25 | **OUT** |

And a **tighter** limit sits below that one, found by *running* the test at 3.5 and reading the failure rather than by predicting it: the wrapped toolbar grows upwards from its bottom anchor and above **~3.06×** it covers the close button's centre — measured onset 3.05× (close still topmost, +0.44px) → 3.1× (the toolbar is topmost) → 3.2× (the zoom-out button is topmost).

Both limits are the same shape: the `h-20` thumb strip is a fixed 80px of a dialog only 172px tall at 4×, and repairing that means changing **what the viewer renders** at tiny heights. That is the viewer redesign this repair story is scoped out of, and the review said so explicitly. **It is therefore LEDGERED AS OWED — `deferred-work.md` DW-53.4-C — and this record claims containment over ~1×–3× only.** The regression test is pinned at **page scale 3** on all four projects: the first integer scale past the measured ~2.45 break, and deliberately the *last safe step*, so its +4.20px of close-button slack makes it the tripwire that fires if anything ever grows the toolbar or the strip.

On the two desktop projects Chromium refuses the emulation above 4× (`Emulation.setPageScaleFactor(4.5)` and `(5)` both leave `visualViewport.scale` at 4) and the viewer is contained at 3, 3.5 and 4 there (+90.00 / +56.56 / +31.50). **The phone projects are the tight ones, and they are the ones the defect was reported from.**

##### Red/green evidence — produced, not asserted

Each fix was toggled off against the finished tests. The source file was backed up to `.hermes/run-logs/53-4-fix3-backup/` first and restored by checksum afterwards (`1997c8bde1c929401f7aba09d91e722b`, verified identical).

- **BLOCKING-6 RED** — the three classes reverted, test at page scale 3: `mobile-light` **and** `mobile-dark` fail with `viewer root right edge is inside what the user can see — Expected: <= 132, Received: 159.296875`. The two desktop projects pass, which is correct: a 320px region has room for both the 158px min-content floor and the 144px toolbar. The defect is phone-shaped, exactly where it was reported.
- **BLOCKING-5 RED** — the subscription reverted to the pre-fix split: **3 of 4 projects** fail with the predicted symptom, `image right edge must not detach from the frame — Expected >= 128.671875, Received −30.71875` on the phones and `Expected >= 421.390625, Received −100.03125` on `desktop-dark` — i.e. 160px / 520px of dead background dragged into view because the pan was never re-clamped. That is BLOCKING-5's described failure, reproduced.
- **BLOCKING-7 RED** — proven **without any source toggle**: the 0-origin regression was injected from the test side by overwriting `--viewer-left`/`--viewer-top` with their offset-free values, and the two verdicts read directly. `mobile-light`: region origin `(120, 80)`, hit point `(160.52, 43.08)` → **old occlusion-only check PASS, new region bound FAIL**. `desktop-light`: region `(120, 80)`, hit `(599.58, 43.00)` → same split. The review's claim about the old helper is confirmed and the new assertion is what carries the regression.
- **GREEN** — all restored, then `120 passed / 12 skipped / 0 failed` across 4 projects.

##### A flake was found and fixed *in this pass*, before it could reach the gate

The new BLOCKING-5 test was **50% flaky on the two desktop projects** when first written (10 runs: 5 red, all on the `|pan| > 0` precondition; the phones were 100% green). Diagnosed rather than retried away: the synthetic touch sequence fired immediately after the zoom poll sometimes commits no pan, and inserting round-trips before the gesture made it 4/4. The fix is `settleTwoFrames()` — the suite's own existing wait — plus a **retried** precondition: `panBy` is absolute (`start.panX + dx`, and 4000px is past every clamp), so a repeat drag is idempotent and lands on the same clamped edge, while a pan that can *never* commit times out and fails loudly instead of degrading into a silent pass. **Verified 20/20 green** (`--repeat-each=5`, all four projects). This is recorded because pass 2's BLOCKING-3 was precisely a flake that reached the reviewer; this one did not.

##### Verification for this pass — current tree, exact commands, and nothing beyond them

- `git diff HEAD --check` → **clean**.
- `npm run typecheck` (`tsc -b`, from `apps/web/`) → **rc=0**, no output. Independently re-run by the controller after the final edits: `.hermes/run-logs/53-4-controller-typecheck-after-fix3-20260801_045148.log`, **rc=0**.
- Focused viewer specs × 4 projects, `npx playwright test --config=tests/visual/playwright.config.ts image-viewer --reporter=list` from `apps/web/` → **120 passed / 12 skipped / 0 failed**. Controller's independent post-fix run: `.hermes/run-logs/53-4-controller-viewer-after-fix3-run1-20260801_045158.log`, **rc=0, 120 / 12 / 0**. The count rises from 112 to 120 because pass 3 adds **two tests × 4 projects** (page scale 3; the `visualViewport` resize refit).
- Targeted stability run of the new BLOCKING-5 test: `--repeat-each=5` × 4 projects → **20 passed**.
- **What is NOT claimed for pass 3:** no `check-all.sh`, no full 4-project visual suite, no `npm run build`, no real-device measurement, **and no second full `image-viewer` run by this agent** — the controller's run is the independent second execution and is cited as such rather than being restated as mine. AC-7's check-all leg remains **OWED**.

#### AC-7 / AC-11 — gates

- `npm run typecheck` → clean. `npx eslint … --max-warnings=0` on both changed files → clean.
- ✅ **`check-all.sh` IS DISCHARGED — an all-green standalone run now exists for the current tree.** `.hermes/run-logs/check-all-53-4-20260801_053329.log`, started **05:33:29**, finished **05:46:59**, **`rc=0`**, summary **`passed: 16`**, **`all green.`**, 16/16 stages: apps/api ruff format + check, workers/render ruff format + check, apps/web typecheck, production build, lint (eslint + stylelint), vitest, apps/api pytest, workers/render pytest, infra/scripts pytest, apps/web visual regression, settings-env-compose-diff, uv-lock-check ×2, local-env-secrets. **It was run AFTER the Aider review**, so it covers the tree as reviewed. `apps/api pytest` **1961 passed / 3 skipped**; `apps/web visual regression` **826 passed / 50 skipped / 0 failed**.
  - **The BLOCKING-4 withdrawal is superseded by evidence, not by re-assertion.** The two earlier logs remain exactly what BLOCKING-4 found them to be and are **not** cited as evidence for anything: `.hermes/run-logs/check-all-20260801_030818.log` was genuinely `all green.` but finished **03:21**, before the 03:49 BLOCKING-1 fix; `.hermes/run-logs/53-4-reviewfix-check-all-20260801_035047.log` is **truncated** mid-`apps/api pytest` (stage 9/16) and its `apps/web visual regression` stage never ran.
- **Full 4-project visual suite: current, inside the fullgate — 826 passed / 50 skipped / 0 failed, 0 baseline PNG changes.** The older standalone `814 passed / 50 skipped / 0 failed` run is **STALE** (it pre-dates the review-fix passes) and is retained as history only; the 826 figure is the one that describes this tree, and the rise from 814 reflects the tests passes 1–3 added.
- **Baseline churn: ZERO.** No PNG under `apps/web/tests/visual/__snapshots__/**` changed, so D-7's triage had an empty candidate set and **no `baseline-reviewed:` line is owed**. `--update-snapshots` was **never** run, blanket or scoped. This is a measured outcome, not an assumption: at page scale 1 the visible region equals the layout viewport, so the computed geometry is numerically identical to what shipped.
- **Locale parity: `en.json` 1050 / `pl.json` 1050**, and `git diff main -- apps/web/src/locales/` is **empty**. Zero keys added, removed or re-valued (V-11).
- **`NFR26-DETERMINISM-1` (AC-11): `npm run test` ×3 consecutive → `154 files / 1139 tests` passed, `rc=0`, identical on all three runs.** Re-run by the controller after the final pass-3 edits because the pass-2 triple (`53-4-reviewfix2-vitest-run{1,2,3}-20260801_041500.log`) pre-dated the 04:47/04:50 pass-3 source edits and no longer described this tree. Current logs: `.hermes/run-logs/53-4-controller-vitest-after-fix3-run{1,2,3}-20260801_0503*.log` — same `154 files / 1139 tests`, `rc=0` on all three. The older sets are retained only as historical evidence of earlier trees.
- **pytest posture:** the diff is frontend-only — zero change under `apps/api/`, `workers/render/` or `infra/`. Per the 51.4 precedent (`51-4-model-detail-category-display.md:184`), pytest determinism is **not this story's obligation**; `check-all.sh` still runs the suite once.

#### Independent Aider review (T5) — literal `REQUEST_CHANGES`, arbitrated by the controller

**Run 2026-08-01 via `laura-aider-review-diff` — the routine diff-review default per the Laura Agent Rulebook.** Gemini is **not** a default reviewer and was not used; Codex is fallback / high-stakes / explicit-operator-request only and was not used. Log: **`.hermes/run-logs/aider-review-53-4-20260801_053242.log`**, process **`rc=0`**, over the dirty working-tree diff. Reviewer model line as logged: `openrouter/deepseek/deepseek-v3.2`, `ask` edit format, `Git repo: none`.

> 🚨 **THE LITERAL VERDICT IS `REQUEST_CHANGES`.** It is recorded here as `REQUEST_CHANGES` and **must not be read, cited or summarised as an Aider `APPROVE`.** The story proceeds on an explicit **controller arbitration** of that verdict — recorded below finding-by-finding — and **not** on a clean external approval. `rc=0` is the wrapper's process exit, not a verdict.

**Controller arbitration: no code or product blocker found. Zero code, test, baseline or locale change was made in response to this review.** Every finding falls into one of three classes — self-referential/sequencing, an already-explicit residual the dev agent cannot discharge, or already-ledgered deferred work.

| Aider finding (as written in the log) | Class | Controller ruling |
|---|---|---|
| Critical 1 — *"Missing independent Aider review … still unchecked and owed"* | **Self-referential** | **Discharged by this very run.** The finding describes the state of the record *at the moment the reviewer read it*; the review it asks for is the one producing the finding. § 6 T5's Aider subtask is now `[x]` and cites this log. |
| Critical 2 — *"Incomplete gate verification — `check-all.sh` is OWED"* | **Intentionally sequenced debt, now discharged** | The check-all leg was deliberately owed **until after** the external review, so the gate would cover the reviewed tree rather than a pre-review one. Discharged by `.hermes/run-logs/check-all-53-4-20260801_053329.log` (`rc=0`, `passed: 16`, `all green.`), run **after** this review. Not a defect in the diff. |
| Critical 3 — *"Unvalidated real-device measurements … NOT PERFORMED"* | **Already-explicit residual, NOT dev-agent-dischargeable** | **Correct, and it stays open.** The dev agent has no handset. This is stated in T1 (unchecked subtask), in § 12 AC-1's scope paragraph and in the Completion Notes. **It is not repaired here and must not be:** it is settled only by the § 9 physical Brave retest, which stays **empty** and is still to be **requested**. |
| Critical 4 / Missing-test 2 — *"Chromium-only validation of the visualViewport compensation"* | **Already ledgered** | `deferred-work.md`, § "Deferred from: code review of 53-4-…", the Chromium-only entry — `status: OPEN` as a **risk without coverage**. Adding a WebKit/Gecko project is a test-infrastructure decision outside a bugfix story (V-6 makes the 4-project matrix Ask First). Not a blocker to this scoped repair. |
| Important 1 / Missing-test 1 — *"only guaranteed up to ~3× page scale"*, *"no tests for very small visual viewports (< 100px)"* | **Already ledgered** | `deferred-work.md` **`DW-53.4-C`**, `status: OPEN — owed, and explicitly NOT claimed by Story 53.4`. Both the >3× bound **and** the tiny-height `--viewer-img-max-h` case (negative below 84.2px of visual-viewport height) are named there with measured numbers. § 12's *"AC-2 IS SATISFIED OVER A MEASURED RANGE, NOT UNLIMITED"* heading already states this **before** the green numbers. The reviewer is describing the story's own disclosed bound, not discovering an undisclosed one. |
| Important 3 — *"No physical retest performed; § 9 remains empty"* | **Already-explicit residual, NOT dev-agent-dischargeable** | Same ruling as Critical 3. D-8 and AC-9(b) make an **empty** § 9 the honest close; a filled one would be a lie about a gate. § 9 stays empty and the retest stays **requested-and-owed** (T7 unchecked). |
| Important 2 — *"Complexity increase … could introduce new failure modes"* · Important 4 — *"3 review cycles with REQUEST_CHANGES"* · Minor 1–3 | **Observation, no action** | No specific defect named. The complexity is load-bearing: **CSS has no unit for the visual viewport** (§ 12 AC-4/AC-6), so no choice of unit could express the repair. The three native review cycles are recorded in full with what each one found and fixed; that history is the record working, not a finding. |

**What the arbitration explicitly did NOT do:** it did not dismiss a security finding (**none was raised** — the reviewer's own "security/privacy" pass returned nothing), it did not overrule a "missing test" that required code (both missing-test items map onto ledgered entries), and it did not convert a `REQUEST_CHANGES` into an `APPROVE`. It ruled that **no Aider finding blocks the code-side merge gate**, while **preserving every residual the findings correctly point at as still open**.

#### Controller fullgate — `check-all.sh` standalone, all green, AFTER the Aider review

- **`.hermes/run-logs/check-all-53-4-20260801_053329.log`** — start `2026-08-01T05:33:29+02:00`, `RUN_EXIT rc=0 2026-08-01T05:46:59+02:00`. Summary block: **`passed:  16`** then **`all green.`** All 16 stages ✓, none skipped.
- **`apps/web visual regression` — 826 passed / 50 skipped / 0 failed** across all four projects. **`apps/api pytest` — 1961 passed / 3 skipped.**
- **Baseline churn: ZERO — re-confirmed by this run**, not carried forward as an assumption. No PNG under `apps/web/tests/visual/__snapshots__/**` changed, so D-7's triage candidate set is empty and **no `baseline-reviewed:` line is owed** on the closeout commit.
- This run **post-dates** the Aider review by 47 seconds and covers the tree exactly as reviewed. **AC-7's check-all leg is DISCHARGED.**

#### Closeout posture — what `done` means here, and what is still owed

**Discharged (code-side merge gate):** native `bmad-code-review` → `APPROVED` · independent Aider review → **run, literal `REQUEST_CHANGES`, controller-arbitrated, no code blocker** · `check-all.sh` standalone **all green** on this tree · `NFR26-DETERMINISM-1` vitest ×3 identical `rc=0` · locale parity 1050/1050 unchanged · zero baseline churn · every § 5 `Never`/`Ask First` file zero-diff.

**Owed and NOT claimed — controller-owned, in this order:**

1. **Commit** on `fix/E53.4-android-chromium-lightbox-fit-repair`. *(Nothing is committed as this record is written.)*
2. **ff-only merge to `main`, no squash; delete the branch; push** — T6, **unchecked**. **NOT DONE.**
3. **`infra/scripts/deploy.sh`**, then record the deployed SHA, the release/version string and the post-deploy `/api/health` version — **AC-8 is NOT satisfied**, and the deployed/version fields stay **owed, not done**. **No deploy and no post-deploy smoke has been run or is claimed.**
4. **Write the § 9 physical Brave retest REQUEST** — T7, **unchecked**. The retest is **not yet requested**, and § 9 stays **entirely empty**. AC-9 closes on branch (b): **requested and NOT performed**. **The dev agent cannot discharge it** — no cell may be filled from an emulator, DevTools device mode, a desktop touchscreen, a Playwright run, or inference.
5. **`G26-LIB` gesture-acceptance evidence on Chrome for Android** — a **different browser and a different evidence class** from this story's Brave defect evidence. **Not dev-agent-dischargeable, not requested by this story, and it stays 🔓 OPEN.**

**Unchanged by this closeout, stated so it cannot be inferred away:** **`G26-LIB` 🔓 OPEN and NOT advanced by one line** · **`epic-53` stays `in-progress`** (53.4 reaching `done` closes neither) · **Story 53.3 § 11 untouched and entirely blank** · **this story's § 9 empty** · **`architecture.md` Decision BA unedited** · **all seven V-12 E53 residuals still `OPEN` and unabsorbed** · **`DW-53.4-C` and the Chromium-only entry still `OPEN`** · **no human review, NOT an Ezop signature, no physical retest run, claimed, simulated or inferred.**

### Completion Notes List (AC-10)

- **Evidence class.** Every result above is **automated regression evidence** from headless/emulated Chromium. **No claim whatsoever is made about real-device gesture quality**, pinch feel, pan feel, or double-tap behaviour. The page-scale-factor repro is a *geometric* stand-in for a device pinch and is labelled as such at the assertion, in the component, and here. **The same applies to the panned-page test added in the review-fix pass: the pan is a synthesized WHEEL gesture, and the equivalence to a device pan is geometric, not behavioural.**
- **NOTHING WAS MEASURED ON THE REPORTING DEVICE.** T1's device subtask is `[ ]` / `NOT PERFORMED — no device access`, and every number in this record is emulated. On the handset the condition is **inferred**, and the root cause is therefore **not** closed there: if the real Brave/Android-17 cause is H3 (edge-to-edge chrome) and `visualViewport` misreports the box on that engine too, this repair is correct and still does not fix the reported defect. **§ 9 is the only thing that can settle that, and it is empty.**
- **`G26-LIB` was NOT advanced — not by one line.** The triggering evidence is **Brave**, not **Chrome for Android**, and it is **defect** evidence, not **gesture-acceptance** evidence. Nothing in this story may be cited toward `G26-LIB`.
- **Story 53.3 § 11 was NOT touched and stays entirely blank.** § 9 of this story is a separate block for a different question and is also empty.
- **`epic-53` stays `in-progress`.** 53.4 reaching `done` closes neither `epic-53` nor `G26-LIB`.
- **`architecture.md` Decision BA was NOT edited**, and D-9's `bmad-correct-course` route was **not** needed: the diagnosis shows the implementation was non-compliant with the single-reference-box rule (it resolved offset and size against a box that is not the one the user sees), **not** that the rule as written is insufficient. The rule is satisfied more strictly after the repair than before it — offset and size now come from the same *measured* box.
- **No human review and no Ezop sign-off are claimed anywhere.** The operator's entire contribution remains the three screenshots. This record is the agent's own.
- **None of V-12's seven open E53 residuals was absorbed, patched or claimed closed**: the `/share` DN-4 watchdog gap, the mounted-and-hung stall, the failure retry dead-end, the X-axis-only double-tap slop pin, the `sources`-swap carry-over, the `error → error` silent announcement, and the double-tap chrome flash are all untouched and still `OPEN`.
- **What T7's § 9 request will need to add once a deploy exists, recorded here because § 9 is not a section `bmad-dev-story` may edit.** The root cause is now known, so the retest can be *targeted* instead of exploratory: before R-1, the operator should **pinch-zoom the `/catalog/<model>` page in, then open the viewer**, and repeat R-1..R-4 in that state — that is the exact condition under which the shipped build fails, and the state a bare "open the viewer and look" retest may never enter. R-1..R-8 as written stay valid and unchanged. **§ 9 remains entirely empty and no cell may be filled from anything but the physical device.**
- **Two review findings ROUTED to `deferred-work.md`, not absorbed** (§ "Deferred from: code review of 53-4-android-chromium-lightbox-fit-repair (2026-08-01)"): the page-pinch-no-longer-magnifies trade-off (ruled ACCEPTED as the intended consequence of AC-4, with a § 9 question attached) and the Chromium-only validation of the `position: fixed` anchoring assumption (risk without coverage, no divergent-engine evidence found). Neither is claimed fixed. The third non-blocking finding — zero coverage of `visualViewport.offsetLeft`/`.offsetTop` — was **fixed with a test instead of ledgered**, and that test was proven red-for-the-right-reason before being kept.
- **New ledger candidate, surfaced not absorbed (D-3).** The end-to-end *device* path still has no automated pin — the repro automates the geometric **condition**, not a physical pinch on Brave/Android. That gap is what § 9's retest request exists to close, and it is stated here rather than filed as a `deferred-work.md` entry because this story owns it until the retest returns.

### File List

| Path | Change |
|---|---|
| `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` | **MODIFIED** — visual-viewport measurement + CSS custom properties; dialog and image geometry rebased onto them with the shipped `vw`/`dvh` expressions as fallbacks (**including E48.1's `calc(100%-2vw)` cap — review-fix BLOCKING-1**); the disproven E48.1 premise comment corrected. **Review-fix pass 3:** the `visualViewport` `resize`/`scroll` subscription consolidated into the refit effect so a page pinch re-runs the zoom/pan refit (**BLOCKING-5**); `commit()` identity-reuse guard; `min-w-0` on the viewer root, `flex-wrap`/`justify-center` on the toolbar and `shrink-0` on its three buttons so the viewer stays contained to page scale 3 (**BLOCKING-6**); the fabricated `SSR` fallback word removed (NB-5). |
| `apps/web/tests/visual/image-viewer-containment.spec.ts` | **MODIFIED** — new `visibleRegion()` / `expectWithinVisibleRegion()` helpers; `zoom toolbar` assertion added to `assertContained` + `assertChromeContained`; D-4 contract correction in both; dead `expectWithinViewport` removed; Story 53.4 regression section now **5 tests × 4 projects** — two page-scale (1.5×/2×), the panned-page origin test (pass 1, with `panVisibleRegion()` and the extracted `settleTwoFrames()`), and **two added by pass 3**: page scale 3 containment + target-size floor (**BLOCKING-6**) and `a visual-viewport resize re-clamps an existing zoom and pan` (**BLOCKING-5**). `expectHittable` now takes the visible region and asserts the hit-tested point lies inside it (**BLOCKING-7**); the pan poll gates on both axes (NB-2); the two page-scale tests pin the used `--viewer-img-max-h` against the `dvh` fallback (NB-1). |
| `_bmad-output/implementation-artifacts/53-4-android-chromium-lightbox-fit-repair.md` | **MODIFIED** — this record, § 6 task checkboxes (T1 split honestly), § 10 Change Log, Status. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | **MODIFIED** — story key `ready-for-dev` → `in-progress`; review notes. |
| `_bmad-output/implementation-artifacts/deferred-work.md` | **MODIFIED** — two routed findings from the 2026-08-01 native `bmad-code-review` appended in their own section; **review-fix pass 3 adds a second section with `DW-53.4-C`** — the measured page-scale bound above ~3× / close-button occlusion above ~3.06× / tiny-height `--viewer-img-max-h` floor, owed rather than claimed. |

No files added, no files deleted. **Zero snapshot baselines changed.**
