---
title: "Sprint Change Proposal — Initiative 17 (Post-Init-16 Operator Hands-On Findings + Housekeeping)"
type: sprint-change-proposal
initiative_scope: [17]
status: approved
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-24
approved_by: Ezop
approved_at: 2026-05-24
approved_via: |
  AskUserQuestion selection "Approve — lecę Init 17 ITCM autonomous" 2026-05-24
  same session as Init 16 close-out + operator-hands-on findings triage. Phase
  A-F autonomous execution authorized; family-time AFK clause active per
  updated [[feedback_autonomous_sleep_on_budget]]. Standing approval from
  Init 16 "klasycznie tryb autonomicznego ITCM" carries forward.
execution_directive: |
  Operator standing autonomous approval ("Teraz, ale chciałbym też wpakować
  resztę otwartych TB jeżeli jakieś są i klasycznie tryb autonomicznego ITCM")
  in force from same session as Init 16. Family-time AFK clause may activate
  per updated [[feedback_autonomous_sleep_on_budget]] family-time / AFK
  signal handling subsection (added 2026-05-24). No operator-handshake
  pauses; hard-stop only on 5h ≥ 80% (sleep through reset), 7d ≥ 95%, or
  real product blocker. Pre-SCP enumeration completed in same session via
  triage-backlog filings TB-044/045/046/047/048 + TB-039 carry-forward +
  TB-043 deferred-from-Story-22.3 + 4 stale-marker housekeeping discovery.
  No voice-heavy items (operator-confirmed P2/P3 + boring-tech fix-shapes).
mode: batch-presented (operator-pragmatic; matches Init 6 / Init 7+8+9 /
  Init 10 / Init 11-15 / Init 16 SCP precedent — full draft surfaced once,
  operator approve → autonomous execution)
change_scope_classification: moderate  # 1 new initiative, 3 epics + 1 standalone story + housekeeping, ~7 stories
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                      # extend (Initiative 17 H2 — minimal, mostly UX-polish FRs)
  - _bmad-output/planning-artifacts/architecture.md             # extend (Decision Z — semaphore on acquireShareBlob; small surface)
  - _bmad-output/planning-artifacts/epics.md                    # extend (Initiative 17 H2 + Epic E26 + E27 + E28 + Standalone S29.1)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # extend (E26 + E27 + E28 + S29.1 entries, status backlog)
  - _bmad-output/triage-backlog.md                              # 7 candidates promoted (TB-039 + TB-043 + TB-044 + TB-045 + TB-046 + TB-047 + TB-048); 4 stale-flips (TB-018 + TB-022 + TB-023 + TB-032)
  - sprint-change-proposal-2026-05-24-init16.md                 # predecessor SCP (Init 16)
  - init-16-retro-2026-05-24.md                                 # Init 16 retro (just shipped); §3.1 + §3.3 carry forward as Init 17 watch-items
predecessor_initiative: 16
trigger:
  source: |
    Operator hands-on post-Init-16-deploy testing 2026-05-24 surfaced 5
    findings (TB-044/045/046/047/048) with HAR + screenshot evidence.
    Plus 1 carry-forward TB-039 (Init 11-15 H2 backfill — deferred from
    Init 16 §5.5) + 1 deferred-from-Story-22.3 TB-043 (hidden-strip-drag
    P3). Plus 4 stale "candidate" status markers discovered in
    triage-backlog enumeration (TB-018, TB-022, TB-023, TB-032 — all
    already DONE via Init 11-15 stories but status field never flipped).
  shape: |
    7 actionable items + 4 stale-marker housekeeping flips. All P2/P3
    (no P1 security/data-integrity/blocker). Mix of UX-polish (TB-044
    viewer scaling, TB-046 ModelGallery strip variant, TB-048 button
    align, TB-043 hidden-strip P3), perf/regression (TB-047 share burst
    503), and diagnostic/doc (TB-045 backfill warning file_id, TB-039
    H2 backfill). All fix-shapes are boring-tech (CSS one-liners +
    one URL-extension + one semaphore + one logging tweak + one doc-only
    paste). No voice-heavy decisions; no designer engagement needed.
  evidence_class: |
    Direct operator observation + HAR capture + screenshot. TB-044 has
    side-by-side screenshots (full_pic_desktop.png vs full_pic_mobile.png).
    TB-047 has timing-resolved HAR (share_gallery.har) showing 8 fetches
    within 1ms + 3 nginx 503s with wait=0-1ms. TB-046 confirmed via
    model_site.har. TB-045 confirmed via backfill log
    (backfill_thumbnail_logs_2026_05_24.log). TB-048 visual screenshot
    (add_model_misalligned.png).
business_decisions_aligned_pre_scp:
  - all_p2_p3_no_hot_fix: |
      Operator 2026-05-24 confirmed all 5 new findings are P2/P3 (no
      security/data-integrity/blocker → no P1 hot-fix-now territory).
      Standard queue → next-session-batch promotion. Operator explicit
      request "Teraz, ale chciałbym też wpakować resztę otwartych TB" =
      same-session Init 17 cycle approved over deferred-to-future-session.
  - boring_tech_fix_shapes: |
      All 7 actionable items have boring-tech fix-shapes pre-specified
      in triage-backlog entries. TB-044 = CSS `min-h-0` flexbox trick +
      `max-h-[calc(95vh-5rem)]`. TB-046 = mirror Story 22.2 share-side
      pattern with `?variant=thumb` URL extension. TB-047 = Redis-style
      semaphore on acquireShareBlob with cap=4. Etc. No design choice
      pending; no voice-heavy grilling needed.
  - housekeeping_inline: |
      4 stale-marker flips (TB-018, TB-022, TB-023, TB-032) are doc-only
      ~5 min total. Fold into Init 17 close-out housekeeping pass
      alongside TB-029 (Init 13 reconciliation pattern from Init 16).
recon_subagents_completed: []  # all pre-enumeration done by Claude main session via triage-backlog write + HAR/screenshot analysis — no subagent dispatch needed
operator_blockers: []  # none at SCP draft time; operator-blocking verifications from Init 16 (Story 22.4 backfill, Story 23.3 pen-test) are independent of Init 17 — Init 17 doesn't depend on them
---

# Sprint Change Proposal — Initiative 17 (Post-Init-16 Operator Hands-On Findings + Housekeeping)

## Section 1 — Issue Summary

### 1.1 Problem statement

Init 16 (Triage Backlog Cleanup Batch) shipped 2026-05-24 with 14 commits +
14 deploys to .190 across Epic 22 (image tier pipeline + symmetric
fullscreen viewer), Epic 23 (share-view security hardening), Epic 24
(test infra), and Standalone Story 26.1 (mobile drag). Operator hands-on
verification post-deploy surfaced 5 findings — all P2/P3, all boring-tech
fix-shapes, no security/data-integrity/blocker class. Init 17 is a
focused follow-up sweep to clear the Init 16 close-out tail PLUS
catch-up housekeeping for Init 11-15 H2 backfill that was de-prioritized
during the Init 16 budget pacing.

This SCP follows the Init 16 mini-SCP precedent: batch-presented (single
draft surfaced for one operator approval, then autonomous execution),
ITCM autonomous mode (Claude OWNS dev/fix work via subagents/Codex/
direct edits; operator surface limited to real blockers or initiative
completion), full BMAD vanilla ceremony (CS/DS/CR per story + ER at
close).

### 1.2 Scope summary

**Total scope estimate: ~3.5-5 h actual work + ~5 min housekeeping flips
across 3 epics + 1 standalone story + 4 stale-marker housekeeping items.**

| Epic / Story | Theme | TB candidates resolved | Job-shape | Voice-heavy? |
|---|---|---|---|---|
| **Epic 26** | Image viewer + carousel UX polish | TB-044, TB-046 | FE CSS + URL-extension; ~1h | No (boring-tech CSS) |
| **Epic 27** | Share-view burst-mitigation + diagnostic gap | TB-047, TB-045 | FE semaphore + worker logging tweak; ~1.5h | No |
| **Epic 28** | Catalog admin toolbar polish + Story 22.3 hidden-strip P3 | TB-048, TB-043 | FE CSS only; ~1h | No (subjective UX accepted) |
| **Standalone Story 29.1** | Init 11-15 H2 backfill housekeeping | TB-039 | Doc-only paste-from-SCP; ~1-2h | No |
| **Housekeeping** | Stale-marker status flips | TB-018, TB-022, TB-023, TB-032 | ~5 min doc edits | No |

### 1.3 Voice-heavy decisions

**None.** Per operator's 2026-05-24 confirmation + boring-tech fix-shapes
in TB candidate entries, no voice-heavy AskUserQuestion grilling needed.
Init 17 SCP advances directly to autonomous execution post-approval.

### 1.4 Scope NOT in Init 17 (intentional)

- **TB-017** — TOTP_FERNET_KEY rotation runbook (trigger 2027-05-20).
  Date-deferred per operator standing directive; OUT.
- **TB-041 (mentioned only, never formally filed)** — stl_preview orphan
  cleanup task. Defensive maintenance; defer until operator surfaces a
  real STL-replace workflow on .190.
- **TB-042 (mentioned only, never formally filed)** — main-frame next/prev
  prefetch via IntersectionObserver on carousel navigation buttons.
  YAGNI per operator's typical share use case (5-15 photo carousels);
  defer until operator surfaces scroll-latency complaint.
- **TB-029 housekeeping** — already flipped during Init 16 SCP
  (commit reference covered).

## Section 2 — Impact Analysis

### 2.1 Epic Impact

**Current epics state at SCP draft time:**

All Init 16 epics (E22, E23, E24, Standalone S25.1) `done` per
sprint-status. Per-epic retros covered by aggregate Init 16 retro
(init-16-retro-2026-05-24.md). Story 22.4 closed as operator-verify-
pending (post-deploy backfill executed successfully per operator log
showing `rendered_gallery=597` + 2 unidentified warnings being TB-045).
Init 17 epics are all NEW; no Init 16 epic re-scoping needed.

**New epics introduced by Init 17:**

| Epic | Status at SCP-time | Sequencing | Notes |
|------|-------|------|-------|
| Epic 26 — Image viewer + carousel UX polish | backlog | Stories 25.1 + 25.2 sequenceable in any order (different surfaces) | Closes user-visible UX regressions on Init 16 NEW surface (viewer) + Init 16 follow-up (catalog detail strip) |
| Epic 27 — Share-view burst-mitigation + diagnostic gap | backlog | Story 27.1 + 26.2 sequenceable | Closes Init 12 carry-forward TB-036 root cause + Story 22.1 diagnostic gap |
| Epic 28 — Catalog admin toolbar + viewer hidden-strip polish | backlog | Story 28.1 + 27.2 sequenceable | Small CSS items; lowest priority but operator-friendly to close |
| Standalone Story 29.1 — Init 11-15 H2 backfill | backlog | Independent | Doc-only; can run last (no code-side dep) |
| Housekeeping (no story) | n/a | Inline during Init 17 close-out | TB-018/022/023/032 stale-marker flips |

**Note:** Epic numbering jumps from E22-E24 (Init 16) to E26-E28 (Init 17),
skipping no IDs. Sprint-status maintains per-Init epic block headers.

### 2.2 Story Impact

| Story | Title | TB | Codex routing | Designer? |
|---|---|---|---|---|
| 25.1 | Fullscreen viewer responsive scaling (max-h-calc + flex min-h-0) | TB-044 | gpt-5.4-mini | No |
| 25.2 | ModelGallery thumb strip consumes `?variant=thumb` | TB-046 | gpt-5.4-mini | No |
| 26.1 | Share-view fetch semaphore in acquireShareBlob (cap=4) | TB-047 | gpt-5.4-mini | No |
| 26.2 | Backfill warning emits file_id inline in message | TB-045 | gpt-5.4-mini | No |
| 27.1 | AddModelButton vertical-baseline alignment with search input | TB-048 | gpt-5.4-mini | No |
| 27.2 | ImageFullscreenViewer hidden-strip coords-based gesture guard | TB-043 | gpt-5.4-mini | No |
| 28.1 | Init 11-15 H2 backfill to prd.md + architecture.md + epics.md | TB-039 | gpt-5.4-mini | No (doc-only) |

### 2.3 Artifact Conflicts

**PRD (`_bmad-output/planning-artifacts/prd.md`):**
- Extend with `## Initiative 17 — Post-Init-16 Operator Hands-On
  Findings + Housekeeping` H2.
- FR17-* requirements (minimal): FR17-VIEWER-SCALE-1 (viewer fits
  viewport with strip), FR17-CAROUSEL-THUMB-1 (ModelGallery strip
  variant=thumb), FR17-SHARE-CONCURRENCY-1 (acquireShareBlob cap=4),
  FR17-BACKFILL-DIAGNOSTIC-1 (file_id inline in warning), FR17-TOOLBAR-
  ALIGN-1 (AddModelButton baseline), FR17-VIEWER-GESTURE-1 (hidden-strip
  coords guard), FR17-DOC-BACKFILL-1 (Init 11-15 H2 catch-up).
- NFR17-VISUAL-VERIFICATION-1 (Story 26.1 + 25.2 + 27.1 carry visual
  baseline regen).

**Architecture (`_bmad-output/planning-artifacts/architecture.md`):**
- Extend with `## Initiative 17` H2.
- Decision Z — share-view concurrency semaphore shape (cap=4, queued
  via Promise.resolve chain in `shareBlobCache.ts`; reuses existing
  module-level cache + pending map from Story 23.1).
- Plus Init 11-15 H2 catch-up sections (Story 29.1 / TB-039 deliverable):
  Init 11, 13, 14, 15 architecture-relevant subsections; Init 12 already
  present.

**Epics (`_bmad-output/planning-artifacts/epics.md`):**
- Extend with `## Initiative 17` H2 + E26/E27/E28/S29.1 story breakdown.
- Plus Init 11-15 H2 catch-up sections (Story 29.1 deliverable):
  - Init 11 (Epic 18) — not yet present
  - Init 13 (Epic 20) — not yet present
  - Init 14 (Epic 21) — not yet present
  - Init 15 (meta) — not yet present
  - Init 12 (Epic 19) — already present, no change
  - Init 16 — already present, no change

### 2.4 Technical Impact

**Code surfaces affected:**

- Frontend TypeScript/React (most of the work):
  - `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` — Story 26.1 CSS + Story 28.2 coords guard
  - `apps/web/src/modules/catalog/components/ModelGallery.tsx` — Story 26.2 `?variant=thumb`
  - `apps/web/src/routes/share/shareBlobCache.ts` — Story 27.1 semaphore
  - `apps/web/src/modules/admin/AddModelButton.tsx` OR `apps/web/src/modules/catalog/routes/CatalogList.tsx` — Story 28.1 CSS align

- Backend Python (minimal):
  - `apps/api/app/workers/generate_thumbnail.py` — Story 27.2 logging format
  - `apps/api/scripts/enqueue_thumbnail_backfill.py` — Story 27.2 parallel warning emit

- Documentation (Story 29.1 + housekeeping):
  - `_bmad-output/planning-artifacts/prd.md` — Init 11-15 H2 backfill + Init 17 H2
  - `_bmad-output/planning-artifacts/architecture.md` — Init 11-15 H2 backfill (where applicable) + Init 17 H2 + Decision Z
  - `_bmad-output/planning-artifacts/epics.md` — Init 11-15 H2 backfill + Init 17 H2
  - `_bmad-output/triage-backlog.md` — TB status flips (housekeeping) + Init 17 close-out summaries

**Auto-deploy:** Per [[feedback_auto_deploy_dev]] every code commit to
`main` triggers `infra/scripts/deploy.sh` to .190. Doc-only commits
(Stories 28.1 + housekeeping) skip deploy per skip-gate. Expected
~6 deploys + 0-2 fix-up deploys (lower than Init 16 since simpler
items + no expected security-class Codex rounds).

## Section 3 — Recommended Approach

### 3.1 Path forward selection

**Option 1 — Direct Adjustment (1 new initiative, 3 epics + 1
standalone + housekeeping): SELECTED.**

Rationale:
- Operator explicit request to bundle all open TBs into one cycle
  + autonomous ITCM mode.
- Per [[feedback_default_to_bmad_workflow]]: multi-item batches are
  epics in disguise → SCP path.
- All items boring-tech with clear fix-shapes pre-specified in TB entries.
- Effort: ~3.5-5h estimated. 5h Anthropic budget at SCP-draft = 10% used
  (post-reset), 4h10m remaining in window. Fits comfortably with margin.
- Risk: Low. CSS one-liners + URL extension + semaphore + logging
  format change + doc-only paste. No new architecture; no schema
  migration; no Codex security-class invocations.

Option 2 (Rollback) and Option 3 (PRD MVP Review) rejected:
- Rollback: nothing in Init 16 needs reverting. All Init 16 surfaces
  ship correctly; Init 17 patches operator-found edges.
- MVP Review: scope is purely follow-up polish; no MVP recalibration
  needed.

### 3.2 Initiative sequencing within Init 17

Per ITCM autonomous mode + lessons from Init 16:
- **Phase A**: sprint-status + epics.md/prd.md/architecture.md H2 append + housekeeping stale-flips
- **Phase B**: Epic 26 stories (UX polish — TB-044 user-visible regression highest priority)
- **Phase C**: Epic 27 stories (share burst-mitigation TB-047 + diagnostic TB-045)
- **Phase D**: Epic 28 stories (toolbar align + hidden-strip P3)
- **Phase E**: Standalone Story 29.1 (H2 backfill — doc-only, parallel with epic retros)
- **Phase F**: Init 17 retro + close-out

Recommended chain for autonomous execution:
```
Phase A (kick-off, ~10 min):
  Sprint-status Init 17 block + epics.md/prd.md/architecture.md Init 17 H2 + housekeeping stale-flips (TB-018/022/023/032)

Phase B (Epic 26 — biggest user impact, ~1.25h):
  Story 26.1 — TB-044 fullscreen viewer responsive scaling (CSS + visual baseline regen)
  Story 26.2 — TB-046 ModelGallery strip ?variant=thumb (1-2 LOC mirror)

Phase C (Epic 27 — share-view burst + diagnostic, ~1.5h):
  Story 27.1 — TB-047 acquireShareBlob semaphore cap=4
  Story 27.2 — TB-045 backfill warning file_id format

Phase D (Epic 28 — small polish, ~45min):
  Story 28.1 — TB-048 toolbar alignment
  Story 28.2 — TB-043 hidden-strip coords gesture guard

Phase E (Standalone, ~1-2h):
  Story 29.1 — TB-039 Init 11-15 H2 backfill (doc-only paste-from-SCPs)

Phase F (close-out, ~15 min):
  Init 17 retro (init-17-retro-2026-05-24.md)
  Update triage-backlog for all 7 actionable + 4 stale-flips
  Sprint-status final flips
```

### 3.3 Codex routing strategy

Per [[feedback_codex_model_routing]] (Pro 5x baseline):
- **gpt-5.4-mini (routine):** ALL 7 stories. No security/concurrency/
  data-integrity class items. Even Story 27.1 (semaphore) is FE
  concurrency primitive at app layer, not security; mini is sufficient.
- **Parallel reviews:** acceptable per [[feedback_codex_parallel_review]]
  routine class; up to 3 concurrent.
- **Pre-merge gate per [[feedback_pre_merge_gate_checklist]]:**
  - typecheck + lint mandatory
  - `npm run build` for FE route changes (Stories 25.1, 25.2, 26.1, 27.1, 27.2)
  - Full pytest for backend changes (Story 27.2 only)
  - Visual baselines for UI stories (Story 26.1, 25.2, 27.1 → catalog +
    share + admin surfaces)

### 3.4 No designer engagement needed

Init 16 Story 22.3 needed Sally subagent for fullscreen viewer UX
shape. Init 17 items are all known-shape fixes:
- TB-044: known CSS pattern (flexbox `min-h-0` + `max-h-[calc(...)]`)
- TB-046: known pattern (mirror Story 22.2 share-side)
- TB-047: known pattern (semaphore on existing module-level cache)
- TB-048: CSS baseline alignment
- TB-043: known pattern (coords-based check instead of contains)
- TB-045: logging format change
- TB-039: doc-only paste

No design decisions pending. No designer subagent dispatch in Init 17.

### 3.5 Operator interaction surface during execution

Per [[feedback_itcm_autonomous_mode]] post-SCP-approval: I OWN all
execution. Operator surface limited to:
- Real product blockers (Codex round-2 reveals architectural contradiction
  → escalate)
- Initiative completion summary
- Family-time AFK continuation per updated [[feedback_autonomous_sleep_on_budget]]

No designer-proxy questions (no designer in Init 17). No voice-heavy
mid-init grilling. Operator-blocking verifications from Init 16 (Story
22.4 backfill, Story 23.3 pen-test) are INDEPENDENT — Init 17 doesn't
depend on them.

## Section 4 — Detailed Change Proposals

### 4.1 Epic E26 — Image viewer + carousel UX polish

**Story 26.1 — Fullscreen viewer responsive scaling (TB-044)**
- AC1: `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx` main-frame flex container gets `min-h-0` class added (flexbox shrink-fix for content-overflow case).
- AC2: Main image `renderImage(...)` className changes from `max-h-full max-w-full object-contain` to `max-h-[calc(95vh-5rem)] max-w-full object-contain` to explicitly subtract strip height (`h-20` = 5rem). When `showNav === false` (single-image case), the calc has 5rem of unused space at bottom — acceptable trade-off (no design noticeable visual cost).
- AC3: Visual baselines regen for `catalog-detail-image-viewer-open-*` (4 viewports × light + dark = 8 PNGs).
- AC4: Operator manual verify post-deploy on portrait + landscape large images (4k/8k).
- AC5: typecheck + lint + vitest 424/424 PASS (no regression).
- AC6: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

**Story 26.2 — ModelGallery strip consumes `?variant=thumb` (TB-046)**
- AC1: `apps/web/src/modules/catalog/components/ModelGallery.tsx` adds `thumbUrlFor(modelId, fileId)` helper returning `${srcFor(...)}?variant=thumb`.
- AC2: Strip map block uses `thumbUrlFor` instead of raw `srcFor`. Main frame stays on `galleryUrlFor` (Story 22.2 baseline preserved).
- AC3: Visual baselines regen for `catalog-detail-*` (4 viewports). Expected near-zero diff (browser scales WebP up minimally for 64px display).
- AC4: typecheck + lint + vitest no regression.
- AC5: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

### 4.2 Epic E27 — Share-view burst-mitigation + diagnostic gap

**Story 27.1 — acquireShareBlob semaphore (TB-047)**
- AC1: `apps/web/src/routes/share/shareBlobCache.ts` adds module-level `_concurrentFetches: number = 0` counter + `_queue: Array<() => void> = []` queue + constant `MAX_CONCURRENT_FETCHES = 4`.
- AC2: `acquireShareBlob(src)` cache-miss branches now acquire semaphore: if `_concurrentFetches < MAX_CONCURRENT_FETCHES`, increment + proceed with fetch; else push a release-callback to `_queue` and wait for slot.
- AC3: Cold-fetch resolve handler decrements `_concurrentFetches` + shifts queue → calls next pending callback.
- AC4: Generation guard (Story 23.1 round-2) preserved — semaphore wraps the fetch, not the generation check.
- AC5: NEW vitest test SEMAPHORE-1: spawn 8 concurrent acquireShareBlob calls; assert only 4 fetches in-flight at any moment; remaining 4 release sequentially as initial 4 resolve.
- AC6: NEW vitest test SEMAPHORE-2: semaphore release fires correctly on fetch rejection (network error path).
- AC7: typecheck + lint + vitest 426/426 PASS (424 baseline + 2 new).
- AC8: `npm run build` CLEAN.
- AC9: Codex review gpt-5.4-mini CLEAN. Round-2 acceptable if concurrency edge cases surface.
- Codex routing: gpt-5.4-mini.

**Story 27.2 — Backfill warning file_id inline (TB-045)**
- AC1: `apps/api/app/workers/generate_thumbnail.py` line ~152-160 warning format changes from `_LOG.warning("thumbnail.unidentified", extra={...})` to `_LOG.warning("thumbnail.unidentified: model_file_id=%s storage_path=%s", str(model_file_id), row.storage_path, extra={...})`.
- AC2: Parallel change in gallery counterpart warning emission (added by Story 22.1).
- AC3: Mirror change in `enqueue_thumbnail_backfill.py` for any warning sites emitting unidentified-format.
- AC4: Structured `extra={"labels.model_file_id": ..., "labels.storage_path": ...}` preserved for GlitchTip compatibility.
- AC5: Full pytest 911/911 PASS 3× consecutive deterministic.
- AC6: ruff check + format CLEAN.
- AC7: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

### 4.3 Epic E28 — Catalog admin toolbar polish + viewer hidden-strip P3

**Story 28.1 — AddModelButton vertical-baseline alignment (TB-048)**
- AC1: Inspect `apps/web/src/modules/catalog/routes/CatalogList.tsx` toolbar JSX + `apps/web/src/modules/admin/AddModelButton.tsx` className.
- AC2: Identify alignment-breaking class (likely AddModelButton lacks `self-stretch` or `inline-flex items-center` in parent; OR search input has unintentional `mt-*`).
- AC3: Apply minimal CSS fix to align AddModelButton baseline with search input (1-3 LOC).
- AC4: Visual baseline regen for catalog list page (4 viewports). Operator manual verify.
- AC5: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

**Story 28.2 — ImageFullscreenViewer hidden-strip coords gesture guard (TB-043)**
- AC1: `apps/web/src/modules/catalog/components/imageViewer/ImageFullscreenViewer.tsx:onTouchStart` changes from `strip.contains(e.target)` check to coordinate-based: capture `touchStart.current` with `stripOrigin: boolean` flag computed via `stripRef.current?.getBoundingClientRect()` + comparing `touch.clientY` to strip's vertical bounds.
- AC2: `onTouchEnd` logic: if `start.stripOrigin === true`, suppress `step()` call (no navigation from strip-origin drags). Tap-toggle-chrome behavior preserved.
- AC3: Pre-existing `pointer-events-none` on hidden strip preserved (Story 22.3 round-3 patch stays as-is) — coords check + pointer-events-none together cover all 4 cells of the gesture-state matrix.
- AC4: typecheck + lint + vitest 5/5 PASS in ImageFullscreenViewer.test.tsx.
- AC5: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

### 4.4 Standalone Story S29.1 — Init 11-15 H2 backfill (TB-039)

- AC1: Append Init 11 H2 section to `epics.md`, `prd.md`, `architecture.md` (already present in epics.md — confirm; absent in prd.md, architecture.md → add).
- AC2: Append Init 12 H2 (already present in all 3 per Init 16 SCP §5.5 verification → no-op or trivial verify).
- AC3: Append Init 13 H2 section to all 3 canonical docs (currently absent per Init 16 SCP §5.5 finding).
- AC4: Append Init 14 H2 (currently absent).
- AC5: Append Init 15 (meta) H2 — minimal, could be a single paragraph since Init 15 was non-PRD-impacting meta/skill-file work.
- AC6: Source paste-from: `sprint-change-proposal-2026-05-23-init-11-15.md` § Init 11/13/14/15 subsections.
- AC7: Doc-only commit, deploy SKIPPED per [[feedback_auto_deploy_dev]] doc-only skip clause.
- AC8: Codex review optional (doc-only); skip OR routine review.
- Codex routing: gpt-5.4-mini if invoked.

### 4.5 Housekeeping (inline, no story)

Status flips in `_bmad-output/triage-backlog.md`:
- **TB-018** — Test-isolation cleanup bundle. All 3 sub-items already closed: #1+#3 via Init 9 Stories 14.1/14.3; #2 via Init 9 Story 14.2 (Init 14 Story 21.1 verified-no-op). Status: candidate → done. Resolution body: cite the 4 commits + retro pointer.
- **TB-022** — Viewer3DInline `srcOverride` hook. Already done via Init 13 Story 20.3 (commit 8284032 + 027e710). Status: candidate → done.
- **TB-023** — Credentialless test fixture. Already done via Init 14 Story 21.2 (commit ea3bfd0). Status: candidate → done.
- **TB-032** — `?variant=thumb2x` retina pipeline. Already closed-by-displacement via Init 16 Epic 22 (TB-037 gallery tier covers retina need). Status: candidate → closed-by-displacement (note variant — not "done" since it's not the original-intent fix, but functionally equivalent).

All 4 flips are doc edits with cross-reference cites in the Resolution body. ~5 min total.

## Section 5 — Implementation Handoff

### 5.1 Scope classification

**MODERATE** — 1 new initiative, 3 new epics + 1 standalone story, ~7
stories. Implementation handoff fully within Developer agent (Claude as
ITCM autonomous); no PM/Architect escalation; no designer engagement.

### 5.2 Agent / role assignment

| Phase | Agent | Responsibility |
|---|---|---|
| SCP approval | Operator (Ezop) | Explicit yes/no on this document |
| Sprint planning + artifact append + housekeeping flips | Claude (BMAD bmad-sprint-planning + direct edits) | Append Init 17 H2 to canonical docs; add E26/E27/E28/S29.1 entries to sprint-status; flip 4 stale TB markers |
| Story execution | Claude (BMAD bmad-create-story → bmad-dev-story → bmad-code-review per story OR direct subagent dispatch for mechanical work) | Full BMAD ceremony per story; auto-deploy per merge; Codex review per §3.3 routing |
| Epic retros | Claude (BMAD bmad-retrospective) | Aggregate per Init 16 precedent (init-17-retro-2026-05-24.md) |
| Init 17 close-out | Claude + Operator | Final triage-backlog updates + operator sign-off |

### 5.3 Success criteria

- All 7 in-scope TB candidates flipped `candidate` → `done` (or `closed-by-displacement` for TB-032).
- All 4 stale-marker housekeeping flips complete.
- Sprint-status epic-25 + epic-26 + epic-27 + 29-1-* all `done`.
- All Codex reviews CLEAN (round-1 OR round-2 fix-up acceptable).
- Full vitest 426+/426+ PASS (424 baseline + 2 from Story 27.1 semaphore tests + potential 0-2 from other stories).
- Full pytest 911+/911+ PASS deterministic (no regression on backend changes; Story 27.2 is logging-only).
- Visual baselines refreshed for Stories 25.1 + 25.2 + 27.1.
- All code commits deployed to .190 with verify-symbolication PASS + runbook fingerprint OK.
- Init 11-15 H2 sections complete in canonical docs.

### 5.4 Cross-init dependencies

**None blocking Init 17 execution.** Init 16 operator-blocking verifications (Story 22.4 backfill rerun — already done per operator log; Story 23.3 pen-test — deferred) are independent.

## Section 6 — Final Review

### 6.1 Checklist completion summary

| Section | Items | Status |
|---|---|---|
| §1 Trigger and Context | 1.1, 1.2, 1.3, 1.4 | All [Done] |
| §2 Epic Impact Assessment | 2.1, 2.2, 2.3, 2.4 | All [Done] |
| §3 Recommended Approach | 3.1, 3.2, 3.3, 3.4, 3.5 | All [Done] |
| §4 Detailed Change Proposals | 4.1, 4.2, 4.3, 4.4, 4.5 | All [Done] |
| §5 Implementation Handoff | 5.1, 5.2, 5.3, 5.4 | All [Done] |
| §6 Final Review | 6.1, 6.2, 6.3 | 6.1-6.2 [Done]; 6.3 [Awaiting operator] |

### 6.2 Asks of operator

**One ask:** explicit yes/no/revise on this SCP. On approval:
- Sprint-status.yaml + epics.md/prd.md/architecture.md H2 append + housekeeping flips proceed autonomously.
- Per-story autonomous loop begins (Stories 25.1 → 25.2 → 26.1 → 26.2 → 27.1 → 27.2 → 28.1).
- All other operator interactions are voluntary (Story 23.3 pen-test, Story 22.4 verify remain independent).

### 6.3 Memory entries informing this initiative

- [[feedback_default_to_bmad_workflow]] — multi-item batch → SCP path
- [[feedback_vanilla_bmad_first]] — full BMAD ceremony preserved
- [[feedback_itcm_autonomous_mode]] — Claude OWNS execution post-SCP
- [[feedback_scp_pre_enumeration_phase]] — pre-enumeration COMPLETED during Init 16 retro + operator hands-on
- [[feedback_codex_model_routing]] — gpt-5.4-mini all stories
- [[feedback_pre_merge_gate_checklist]] — typed pre-Codex gate
- [[feedback_frontend_visual_verification]] — UI story visual verify gate
- [[feedback_auto_deploy_dev]] — per-merge auto-deploy
- [[feedback_autonomous_sleep_on_budget]] — family-time clause active per Init 16 update
- [[feedback_share_view_scope_boundary]] — share-view terminus respected (Story 27.1 is bug-fix not UX iteration)
- [[feedback_lazy_import_discipline]] — Story 28.2 doesn't touch lazy barrels (CSS-only)
- [[feedback_docs_hygiene]] — Story 29.1 closes Init 11-15 H2 backfill debt per "adopt or archive"

---

**End of SCP draft.** Awaiting operator approval (yes / revise / no).
