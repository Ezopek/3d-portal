# Sprint Change Proposal — 2026-08-01

## Shipped Android Chromium lightbox fit-to-frame defect → Story 53.4 inside open Epic E53

| | |
|---|---|
| **Date** | 2026-08-01 |
| **Author of record** | repo-local Claude Opus 5, BMAD author of record (native `bmad-correct-course`) |
| **Baseline** | `main` == `origin/main` @ `36edc9c6483dd8099d8c6ed1f0b734c15cd0700f`, clean tree |
| **Mode** | Batch (the change was handed over fully specified; no elicitation loop was run) |
| **Trigger class** | Shipped-defect report backed by **physical device evidence** |
| **Scope classification** | **Moderate** — one new story inside an already-open epic; no PRD change, no architecture decision change, no MVP re-scope |
| **Routes to** | `bmad-create-story` → `bmad-dev-story` (per-story `G26-DEVGO` still required) |
| **Gates touched** | **NONE.** `G26-LIB` stays 🔓 OPEN. `epic-53` stays `in-progress`. `G26-DEVGO` stays 🔓 OPEN. |

> **Provenance honesty, stated once and binding on every sentence below.** This document was written by the repo-local Claude Opus 5 agent. **Ezop did not review it. No human reviewed it.** Ezop's role in this change is exactly one thing: he **captured the three screenshots on his own phone** and handed them over. That is operator *evidence collection*, not sign-off, not code review, and not approval of anything in this file. Every technical claim below is either (a) something this agent read directly out of the evidence PNGs or the repo, and says so, or (b) an explicitly labelled **hypothesis** for Story 53.4 to confirm or kill.

---

## 1. Issue Summary

### 1.1 What is wrong

On a **physical** Android phone running a **Brave / Chromium-family** browser, the shipped fullscreen image lightbox on `/catalog/$modelId` **does not fit the photo inside the visible frame at its reset / minimum scale**. The right-hand part of the viewer — the photo's right edge *and* the zoom-out control on the toolbar — sits outside the visible right edge of the screen and is clipped.

This contradicts the invariant Epic E53 (and Story 48.1 before it) is built on, and which the automated suite asserts and reports green.

### 1.2 How it was found

Reported by the operator (Ezop) from ordinary use of the live portal, not from a test run and not from a protocol. Three screenshots were handed over as evidence. There was **no G0–G15 protocol run**, no scripted repro, and no instrumentation — this is a field defect report with photographs, and it is recorded as exactly that.

### 1.3 Why it matters more than an ordinary UI bug

The automated evidence and the physical evidence **disagree**. `apps/web/tests/visual/image-viewer-containment.spec.ts` asserts containment at scale = 1 across a geometry matrix in both orientations, in light and dark, on emulated `mobile-*` projects, and it passes (722 passed / 46 skipped / 0 failed at Story 53.3's gate). The phone says otherwise. Whatever Story 53.4 finds, it must also explain **why the suite could not see this**, or the same class of defect ships again behind the same green gate.

---

## 2. Evidence (verified, not quoted)

All three files were re-hashed and re-opened by this agent in this session; the hashes below are the values this agent measured, not values copied from the handover.

| File | SHA-256 (measured) | What it establishes |
|---|---|---|
| `Screenshot_20260801-014633.png` | `511356a0c74893411d15eb37fd5b8c5961d824a6fde317375b22c5d5512d8d3a` | The defect itself. 960×2142, portrait. |
| `Screenshot_20260801-014837.png` | `1b868e04c5337a0399b85ffef771c238af53de3de5f674fb69f4157f701f29b1` | Device identity: **Pixel 9 Pro** (Android device-details screen, pl-PL UI). |
| `Screenshot_20260801-014900.png` | `f6e32e3eae7ff10daf279ba9b64063ee922fb5bd3493eeff1e184f951e139a75` | Browser/OS identity: **Brave 1.92.144, Chromium 150.0.7871.186**, **Android 17, Build/CP2A.260705.006**. |

**Canonical source:** `/mnt/download/Screenshot_20260801-014633.png` on Fenrir.
**Controller working copies:** `/tmp/3d-portal-android-evidence/` — **outside the repository, and deliberately not committed.**

> **PII note.** The device-identity screenshot displays the phone's **IMEI**. It is deliberately **not transcribed** into this or any other repo artifact, and the PNGs themselves must not be committed. If a future story needs device provenance in-repo, record model + OS build only.

### 2.1 What this agent read directly out of the defect screenshot

Observations, in decreasing order of certainty:

1. **Context is right.** The Brave omnibox reads `3d.ezop.ddns.net/catalog/361625a5-77e…` — the live portal, model-detail route, fullscreen viewer open. Viewer chrome is all present and identifiable: the `1 / 11` counter (top-left), the previous chevron (left edge), the bottom thumbnail strip, and the zoom toolbar (bottom-right).
2. **The left inset is honoured.** There is a narrow dark gutter down the left side of the photo, consistent with the shipped `left-[1vw]` anchoring.
3. **The right inset is not.** The photo runs flush to — and past — the right edge of the screen. **There is no matching right gutter.** The subject (a pink planter held in a hand) is visibly cut off by the screen edge rather than letterboxed.
4. **The toolbar is clipped too.** Cropping the bottom-right region and inspecting it directly: the toolbar pill holding `+` and `−` is **cut off by the screen edge** — the `−` button's circle is sliced. This is the load-bearing observation: the toolbar is a chrome layer anchored *outside* the transform layer, so its clipping cannot be explained by image sizing at all. **The whole viewer box overflows to the right, not just the photo.**
5. **Consistent with the fit floor.** The `−` glyph renders in a dimmed/lower-contrast treatment relative to `+`, which is what the shipped disabled zoom-out control looks like at `scale === MIN_SCALE`. Combined with the operator's statement that this is the reset/minimum state, the reading is that **the overflow exists at the fit floor, before the user zooms at all.** A screenshot cannot read out the actual `scale` value; Story 53.4 must confirm it by measurement rather than inherit it from here.

### 2.2 What this evidence is NOT — binding constraints

- ❌ **NOT Chrome-for-Android evidence.** Brave is Chromium-family but is a different browser with its own shields, its own UI chrome and its own viewport behaviour. Nothing here may be cited as Chrome-for-Android.
- ❌ **NOT a completed G0–G15 protocol.** No protocol was run. Story 53.3 § 11 remains **entirely blank**.
- ❌ **NOT gesture-quality evidence.** These are static frames. They say nothing about pinch, pan, double-tap, or fling.
- ❌ **NOT a `G26-LIB` closure and not a step toward one.** See § 5.
- ❌ **NOT human review, NOT an Ezop sign-off** on any code, doc or decision.
- ⚠️ **The deployed build is unrecorded.** The evidence does not capture a version/build string. Story 53.4 must record the exact deployed version it reproduces against, and again at retest.

---

## 3. Impact Analysis

### 3.1 Epic impact

| Artifact | Impact |
|---|---|
| **E53** | Gains **Story 53.4** (bugfix). E53 was already `in-progress` with `G26-LIB` open; it now has open work again *in fact* and not only *in gate bookkeeping*. |
| **E48** | Story 48.1's fix is **not** proven wrong — it fixed a measured `left:50%` vs `w-[98vw]` mixed-reference-box displacement, and the left inset in the evidence still behaves as 48.1 intended. But 48.1's residual-risk statement ("other `DialogContent` consumers may exhibit the same pattern") is now joined by a sharper fact: **the same *class* of defect survives in the image lightbox itself on at least one real Chromium build.** |
| **E54** | **Not reopened.** E54 stays `done`. 54.2's cross-surface a11y/visual audit ran on emulated projects and legitimately could not see this. |
| **Initiative 26** | The standing description — *"code- and docs-complete with `G26-LIB` open"* — must **no longer** be used unqualified. Correct phrasing from today: **"code- and docs-complete except for the open Android Chromium lightbox fit defect (Story 53.4), with `G26-LIB` open."** |

### 3.2 Story impact

- **53.1 / 53.2 / 53.3 stay `done`.** They are not reopened, not re-reviewed, and not retro-graded. Their records were honest about exactly this exposure: every one of them states in terms that all evidence was jsdom / headless-Chromium / emulated only and that no physical Android evidence existed. **The gap this defect walked through was declared in advance, in writing, by the stories themselves.** That is the system working, late.
- **53.4 is new** and is the only owner of this defect.

### 3.3 Artifact conflicts

| Artifact | Conflict | Resolution |
|---|---|---|
| `epics.md` E53 | Enumerates three stories; the epic has open work with no owner. | **Add Story 53.4 sketch.** (§ 6.1) |
| `sprint-status.yaml` | No `53-4-*` key; nothing for `bmad-create-story` to pick up. | **Add key at `backlog`.** (§ 6.2) |
| `architecture.md` Decision BA | Lists carried-forward 48.1 invariants incl. the single-reference-box rule. The rule is *stated* correctly; the shipped code does not *achieve* it on this browser. | **No edit now.** Decision BA is a procedure decision and is not falsified by an implementation defect. If 53.4's root cause proves the *invariant as written* is insufficient (rather than the implementation being non-compliant with it), 53.4 must come back through `bmad-correct-course` to amend Decision BA — it may not silently rewrite it. |
| `prd.md` | FR26-VIEW-1 unchanged; this is a defect against shipped behaviour, not a requirement change. | **No edit.** |
| `deferred-work.md` | — | **No entry.** That ledger tracks findings deferred *without* an owner. This defect has a named owning story from the moment it is recorded, so an entry would be a duplicate that later drifts. |

### 3.4 Technical impact — hypotheses only, no root cause is asserted

This agent read the shipped implementation to bound the search. **Nothing below is a diagnosis.** Story 53.4 owns the diagnosis and is free to reject all of these.

Relevant shipped geometry (read at `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx`):

- `DialogContent` — `h-[95dvh] w-[98vw] max-w-[calc(100%-2vw)] left-[1vw] top-[2.5dvh] translate-x-0 translate-y-0`
- image — `max-h-[calc(95dvh-5rem)] max-w-full object-contain`, inside an `absolute inset-0` transform layer
- `MIN_SCALE = 1` (`imageViewer/zoom.ts:13`) — fit is delegated to CSS `object-contain`, not to a measured fit ratio

Candidate surfaces:

- **H1 — layout vs visual viewport, again.** The in-file comment asserts that `left:50%` resolves against the layout viewport while `w-[98vw]` resolves against the **visual** viewport. Per spec, `vw` resolves against the initial containing block (layout viewport), not the visual viewport. **If that comment's premise is wrong, `98vw` + `left:1vw` can exceed the visible width whenever the layout viewport is wider than the visible area** — which produces exactly the observed asymmetry (correct left inset, overflowing right edge, clipped right-anchored toolbar). **Strongest candidate; test it first.**
- **H2 — `max-w-[calc(100%-2vw)]` fails to cap.** The cap exists to counter the left anchoring, and its own comment concedes it is *"inert wherever the gutter is 0"* and that **headless CI cannot exercise it**. An untested counterweight is a good place for a bug to live.
- **H3 — Brave-specific chrome/viewport behaviour** (shields, custom toolbar, Android 17 edge-to-edge/`viewport-fit` handling) shifting the visible area relative to the layout viewport.
- **H4 — `object-contain` fits the wrong box.** The image is capped by `max-w-full` against a transform layer that is itself inside an over-wide dialog, so a "contained" image can still be off-screen. This would explain the photo but **not** the clipped toolbar, so H4 alone is insufficient — which is itself a useful constraint.

**The suite-blindness question is first-class scope.** Whatever the cause, 53.4 must state why the emulated `mobile-*` projects report green — the answer is likely that Playwright emulation gives layout viewport == visual viewport == device width with overlay scrollbars, so the entire failure mode is unrepresentable there.

---

## 4. Recommended Approach

**Chosen path: Direct Adjustment — add one bugfix story inside the already-open epic.**

Considered and rejected:

- **Quick-fix outside BMAD (`bmad-quick-dev`).** Rejected. E53 is open, the defect is squarely inside its subject matter, and the epic's gate story is unfinished. A quick fix would leave the defect unledgered inside an open epic and would produce a code change with no story record — precisely the provenance failure this project's records are built to prevent.
- **Rollback of 53.2/53.3.** Rejected. The defect class predates them (48.1 territory) and the 53.x work is independently valuable. Nothing suggests rollback simplifies the repair.
- **Reopen E54 / broaden into a cross-surface audit.** Rejected as scope creep. One defect, one story.
- **Fold into `G26-LIB` closure.** Rejected — and would be an outright honesty failure. See § 5.

**Effort:** small-to-moderate. The repro is likely cheap once the right viewport condition is identified; the fix should be a small CSS/geometry change; the expensive parts are (a) making the regression test able to *fail* on the real condition and (b) the physical retest, which only the operator can perform.

**Risk:** the geometry is shared with a shipped, baselined surface. `apps/web/src/ui/dialog.tsx` remains **Ask First** (Decision BA) — blast radius is every dialog in the app. Baseline churn is a live risk and is capped explicitly in § 6.1.

**Timeline:** E53 and `G26-LIB` stay open until a **deployed** repair passes a **fresh physical retest**. This change does not shorten that.

---

## 5. Gate rulings (binding)

1. **`G26-LIB` stays 🔓 OPEN — and this evidence does not advance it.** `G26-LIB` closes on a non-provisional Story 53.1 recommendation **plus physical Android Chrome evidence**. This is **Brave**, and it is **defect** evidence rather than gesture-acceptance evidence. It is the wrong browser *and* the wrong kind of evidence. Nothing in Story 53.4 may be cited toward `G26-LIB`.
2. **`epic-53` stays `in-progress`.** It now has an open story as well as an open gate.
3. **`G26-DEVGO` stays 🔓 OPEN.** Creating and validating Story 53.4 grants no code authorization; the controller must issue per-story dev-go before `bmad-dev-story` runs, exactly as for 53.1–53.3.
4. **Story 53.3 § 11 stays blank.** Nothing here may be used to fill any cell of the physical protocol.
5. **No human review is claimed anywhere.** The operator supplied screenshots; that is the entire human contribution.
6. **The pre-existing E53 residuals are NOT absorbed into 53.4.** The `/share` never-mounted-`<img>` residual, the mounted-and-hung `/catalog` residual (both `status: OPEN` in `deferred-work.md`), the `ui/dialog.tsx` focus-trap defect (routed to 54.2, closed unmet), and the double-tap chrome-flash deferral (needs a 53.2 AC-3 amendment) all remain owed to a **separate** follow-up story. Story 53.4 is the fit-to-frame defect and nothing else.

---

## 6. Detailed Change Proposals

Three files. No product code, no tests, no locales, no baselines, no commit.

### 6.1 `_bmad-output/planning-artifacts/epics.md` — insert Story 53.4 sketch

**Location:** § Epic E53, immediately after the Story 53.3 sketch (`epics.md:4577-4579`), before `#### Epic E54`.

**OLD:** E53 enumerates Stories 53.1, 53.2, 53.3 and ends.

**NEW:** adds `##### Story 53.4 — Android Chromium lightbox fit-to-frame repair (FR26-VIEW-1, NFR26-VISUAL-1)` — a bugfix sketch whose spine is: **reproduce deterministically → add a failing regression → minimal root-cause fix → preserve zoom/pan inspectability above 1.0 → deploy → request fresh physical retest.**

**Rationale:** an open epic with unowned open work misreports the plan. The sketch is deliberately written as a *sequence with a failing test before the fix*, because the defining fact of this defect is that the existing green suite cannot see it.

**Rationale for the tight boundary in the sketch:** `ui/dialog.tsx` stays Ask First; the 48.1 invariants stay binding; unrelated E53 residuals stay out (§ 5.6); baseline churn must be justified per PNG rather than blanket-refreshed.

### 6.2 `_bmad-output/implementation-artifacts/sprint-status.yaml` — add the story key

**OLD:**
```yaml
  53-3-lightbox-test-contract: done  # …
  epic-53-retrospective: optional  # …
```

**NEW:**
```yaml
  53-3-lightbox-test-contract: done  # …
  53-4-android-chromium-lightbox-fit-repair: backlog  # ADDED 2026-08-01 …
  epic-53-retrospective: optional  # …
```

**Status choice — `backlog`, deliberately.** `backlog` is the only status `bmad-create-story` picks up as next work; `ready-for-dev` would falsely assert a story artifact exists and had been validated. `epic-53` needs no flip — it is already `in-progress`.

**Also updated:** `last_updated` gains a dated note recording this change and re-stating the § 5 gate rulings, matching this file's established convention.

### 6.3 This document

The Sprint Change Proposal itself, at `_bmad-output/planning-artifacts/sprint-change-proposal-2026-08-01-e53-android-lightbox-fit-defect.md`.

### 6.4 Explicitly NOT changed

`prd.md` · `architecture.md` (incl. Decision BA and the `G26-*` gate line) · `deferred-work.md` · every file under `apps/`, `workers/`, `infra/` · every locale file · every visual baseline · Stories 53.1/53.2/53.3 records · `epic-53` and `epic-54` statuses · Story 53.3 § 11. **Nothing was committed.**

---

## 7. Implementation Handoff

**Scope: Moderate** — backlog reorganization inside an open epic; PO/DEV coordination, no PM/Architect replan.

**Sequence:**

1. `bmad-create-story` → creates `53-4-android-chromium-lightbox-fit-repair` from the § 6.1 sketch (`backlog` → `ready-for-dev`; the workflow's own bookkeeping).
2. `bmad-create-story` Validate pass (VS).
3. **Controller issues per-story `G26-DEVGO`** — mandatory, not implied by validation.
4. `bmad-dev-story` → repro, failing regression, minimal fix.
5. `bmad-code-review` + independent Aider review (`laura-aider-review-diff`; Gemini is **not** a default reviewer; Codex is fallback/high-stakes only).
6. Full `infra/scripts/check-all.sh` standalone; `baseline-reviewed:` lines for any changed PNG.
7. Merge, push, **deploy**.
8. **Operator requests a fresh physical retest** — Chrome for Android for `G26-LIB`, Brave for this defect. They are different questions and must not be conflated.

**Success criteria for Story 53.4:**

- The defect reproduces **deterministically** — an identified, written-down viewport/browser condition, not "sometimes on a phone".
- A regression test **fails before the fix and passes after**, and the story states **why the existing suite could not fail** on this.
- The fix is **minimal and root-cause**, not a clamp that masks the geometry.
- **Zoom and pan above 1.0 remain fully inspectable** — no fix that fits the image by disabling the thing the whole epic exists to provide.
- Every 48.1 / Decision BA invariant still holds; `ui/dialog.tsx` untouched unless explicitly asked and granted.
- Deployed, with the build version recorded.
- Fresh physical retest **requested** — the story closes on the repair and the request, and may **not** claim the retest result until it exists.

**`G26-LIB` and `epic-53` remain OPEN throughout, and Story 53.4 closing does not close either of them.**
