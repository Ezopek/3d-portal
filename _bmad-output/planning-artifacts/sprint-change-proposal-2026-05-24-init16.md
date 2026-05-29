---
title: "Sprint Change Proposal — Initiative 16 (Triage Backlog Cleanup — Post-Init-15 Sweep)"
type: sprint-change-proposal
initiative_scope: [16]
status: approved
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-24
approved_by: Ezop
approved_at: 2026-05-24
approved_via: |
  AskUserQuestion selection "Approve — lecę Init 16 ITCM autonomous" 2026-05-24
  immediately after SCP draft surfaced. Phase A kickoff authorized; Phase B/C/D
  proceed per §3.2 sequencing with operator surface limited to designer UX
  session, real product blockers, and final close-out summary.
execution_directive: |
  Operator authorized "wszystkie otwarte backlog itemy (chyba że z deferred na
  jakąś datę konkretną)" + "wszelkie techniczne rzeczy zostawiam Tobie, do mnie
  uderzaj z biznesowym grillingiem jeżeli coś będziesz miał" via 2026-05-24
  follow-up after TB-038 was added to backlog. ITCM autonomous mode per
  [[feedback_itcm_autonomous_mode]]; no operator-handshake pauses; hard-stop
  only on 5h ≥ 80% (sleep through reset per [[feedback_autonomous_sleep_on_budget]]),
  7d ≥ 95%, or real product blocker. Voice-heavy grilling for TB-037 (fullscreen
  viewer surface scope, TB-022 inclusion, TB-026 rate-limit threshold) FIRED
  AND ANSWERED 2026-05-24 BEFORE SCP draft (per [[feedback_voice_heavy_dedicated_grilling]]
  "stronger upfront grilling over mid-init monitoring").
mode: batch-presented (operator-pragmatic variant of BMAD Incremental — full
  draft surfaced once, operator feedback consolidated; matches Init 6 / Init 7+8+9 /
  Init 10 / Init 11-15 SCP precedent)
change_scope_classification: moderate  # 1 new initiative, 3 new epics + 1 standalone story, ~8 stories
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                      # extend (Initiative 16 H2 with FR16-* / NFR16-*)
  - _bmad-output/planning-artifacts/architecture.md             # extend (Decisions W + X + Y — gallery tier pipeline, blob cache hardening, per-token rate-limit)
  - _bmad-output/planning-artifacts/epics.md                    # extend (Initiative 16 H2 + Epic E22 + E23 + E24 + Standalone S25.1)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # extend (E22 + E23 + E24 + S25.1 entries, status backlog)
  - _bmad-output/triage-backlog.md                              # 9 open candidates being promoted (TB-030 + TB-033 + TB-034 + TB-035 + TB-036 + TB-037 + TB-038 + TB-026 sub#6 per-token + TB-027 verify); housekeeping: close TB-029 (already shipped via Story 20.2)
  - sprint-change-proposal-2026-05-23-init-11-15.md             # predecessor SCP (Init 11-15)
predecessor_initiative: 15
trigger:
  source: |
    Operator request 2026-05-24 ("możemy teraz wszystkie otwarte backlogowe
    Ireny które nadają się na realizację teraz spakować, rozpisać na epic/story
    i zrealizować w naszej znanej i lubianej autonomicznej pętli z Tobą jako
    moim ITCM, zgodnie z bmad") + follow-up clarification ("chcę wszystkie
    backlog itemy chyba że z deferred na jakąś datę konkretną; jeżeli coś
    wymaga sesji designera czy grillingu to też wrzucamy i ogarniamy od razu;
    wszelkie techniczne rzeczy zostawiam Tobie, wierzę też w naszą designerkę,
    do mnie uderzaj z biznesowym grillingiem jeżeli coś będziesz miał").
  shape: |
    Open `status: candidate` items in `_bmad-output/triage-backlog.md`
    post-Init-15 close-out: 9 items genuinely open (after subtracting items
    closed by Init 11-15 stories that operator's grouping did not yet know
    about — TB-018 #2 via Story 21.1, TB-023 via Story 21.2, TB-022 via
    Story 20.3, TB-027 via Story 20.1 partial, TB-029 via Story 20.2 review),
    plus TB-038 added 2026-05-24 same session. Date-deferred TB-017 (trigger
    2027-05-20) excluded per operator directive.
  evidence_class: |
    Mixed — direct operator hands-on observation (TB-038 mobile photo-reorder,
    TB-037 operator-proposed 3-tier image pipeline post-Init-12 share-view
    hands-on use) + HAR-confirmed root-cause-pinned bug (TB-036 503 carousel
    fetches, HAR at tmp/shared-model-example.har) + Codex round-2 P2 findings
    on shipped Init 11-15 work (TB-033 blob cache StrictMode, TB-034 STL
    preview source-tracking, TB-030 _admin_token helper) + backfill hygiene
    (TB-035 one unidentified format warning during Init 11-15 deploy).
business_decisions_aligned_pre_scp:
  - fullscreen_viewer_surface_scope: |
      Operator AskUserQuestion 2026-05-24 selected "Share + authenticated
      catalog detail (symetrycznie)" over "Tylko /share/<token>" or "Designerka
      decyduje". Rationale: symmetric surface gives authenticated users parity
      with anonymous viewers; designer scope = UX shape (modal, sizes, gesture)
      not surface scope (which is a product decision). Carries forward to
      Story 22.3 AC. Per [[feedback_share_view_scope_boundary]] this is the
      operator-blessed image-quality exception to the post-Init-12 share-view
      UX terminus.
  - tb_022_inclusion: |
      Operator AskUserQuestion 2026-05-24 selected "Include teraz dla
      kompletności" over "Defer per boring-tech". Rationale: symmetric
      fullscreen viewer may need Viewer3D-stylowanego lightboxa; srcOverride
      pattern useful broader. HOWEVER pre-SCP enumeration revealed TB-022
      ALREADY DONE via Init 13 Story 20.3 (commit 8284032 + 027e710 lint
      fix-up). SCP folds operator's "include" intent into Story 22.3 — the
      fullscreen viewer build will USE the Story 20.3 srcOverride hook (its
      first non-default-auth consumer beyond the Init 12 Story 19.7
      share-view 3D viewer); no new srcOverride work in Init 16.
  - share_rate_limit_threshold: |
      Operator AskUserQuestion 2026-05-24 selected "Dodać app-level per-token
      request-count cap (np. 60 req/min/token)" over "Nginx caps + smaller
      TB-037 tiers wystarczą" or "Defer". Rationale: defense-in-depth on top
      of existing per-IP rate-limit (Init 12 Story 19.1) — per-token cap
      catches attackers using IP pool against a scraped token. Becomes Story
      23.3 with explicit numeric threshold (60 req/min/token) carried into AC.
recon_subagents_completed: []  # all pre-enumeration done by Claude main session via Read/grep/sprint-status inspection — no subagent dispatch needed
operator_blockers: []  # none at SCP draft time; voice-heavy grilling already fired and answered
---

# Sprint Change Proposal — Initiative 16 (Triage Backlog Cleanup — Post-Init-15 Sweep)

## Section 1 — Issue Summary

### 1.1 Problem statement

After the Init 11-15 close-out (2026-05-23 aggregate retro), the
`_bmad-output/triage-backlog.md` file accumulated a fresh wave of candidates
sourced from two channels: (a) **operator hands-on observations on the
deployed Init 12-13 share-view + catalog UX surfaces** (TB-036 carousel 503s,
TB-037 image quality tiering need, TB-038 mobile photo-reorder drag fight),
and (b) **Codex round-2 P2 findings on Init 11-15 work that were
hardening-class rather than blocker-class** (TB-030 _admin_token helper
sweep, TB-033 blob cache StrictMode + revocation, TB-034 STL preview
source-tracking + single-flight lock).

Operator's 2026-05-24 directive ("paczka ze wszystkich obecnie otwartych
backlog tematów, minus date-deferred") green-lights a coordinated backlog
sweep. Pre-SCP enumeration against `sprint-status.yaml` revealed that
**several items operator's grouping inherited from the standing TB list are
ALREADY DONE** as side-effects of Init 11-15 stories — Init 16's first
hygiene act is reconciling this state divergence so the new initiative does
not duplicate shipped work:

| Standing TB | Operator's intent | Actual state | Init 16 disposition |
|--------|--------|--------|--------|
| TB-018 #2 (hydrate DB pollution) | Include in test infra story | DONE via Init 9 Story 14.2 (commit fa4a628) — Story 21.1 verified | Crosswalk note only; no work |
| TB-022 (Viewer3DInline srcOverride hook) | "Include now" per AskUserQuestion | DONE via Init 13 Story 20.3 (commit 8284032 + 027e710) | Story 22.3 USES it; no new srcOverride work |
| TB-023 (credentialless test fixture) | Include in test infra story | DONE via Init 14 Story 21.2 (commit ea3bfd0) | Crosswalk note only; no work |
| TB-027 (catalog full-res srcSet) | Include in image pipeline | PARTIAL via Init 13 Story 20.1 (commit a9d7d18 — srcSet 2x dropped) | Story 22.4 verifies post-tier-ship; TB-032 follow-up subsumed by TB-037 |
| TB-029 (Admin Add Model CTA) | Already noted as housekeeping | DONE via Init 13 Story 20.2 (commit 7f6dd10 + 83b225a) — currently sprint-status `review` pending final Codex | Housekeeping: flip TB-029 backlog status to `done`; no Init 16 work |
| TB-026 sub#6 per-IP | Include in share security | DONE via Init 12 Story 19.1 (commit 2232b77 + 57faba1) — share_anon_ratelimit_key per-IP middleware | Story 23.3 ADDS per-token cap on top |
| TB-026 sub#7 throughput | Include in share security | SHIPPED IN CODE via Init 12 Story 19.2 (uncommitted in configs repo, status `review`) | Cross-init dependency: operator infra-side deploy + sync.sh; no Init 16 code work |

**Net Init 16 in-scope set (9 items):** TB-030, TB-033, TB-034, TB-035,
TB-036, TB-037, TB-038, TB-026 sub#6 per-token addition (new operator
decision 2026-05-24), TB-027 verification (post-Story-22 tier ship).

**Out of Init 16 scope (intentional):**
- **TB-017 — TOTP_FERNET_KEY rotation runbook** (trigger 2027-05-20).
  Date-deferred per operator standing directive; runbook authoring ≤2 months
  before trigger.
- **TB-026 sub#1-5 — share-view UX enrichment** (carousel, STL preview
  images, 3D viewer, file list, description). OUT per [[feedback_share_view_scope_boundary]]
  (post-Init-12 share view is intentionally TERMINUS for UX iteration; only
  security hardening warranted). TB-037 fullscreen viewer is the deliberate
  image-quality exception to terminus — NOT UX enrichment, IS quality tier
  semantics.
- **TB-032 — `?variant=thumb2x` retina pipeline.** Subsumed by TB-037 (Story
  22.2 retina sizing will be designer-tuned; if TB-037 gallery tier covers
  the retina need adequately, TB-032 is closed-by-displacement; if not,
  resurfaces as Init 17+ candidate).

### 1.2 Scope summary

**Total scope estimate: ~16-22 h across 3 epics + 1 standalone story, ~8 stories.**

| Epic / Story | Theme | TB candidates resolved | Job-shape | Voice-heavy? |
|---|---|---|---|---|
| **Epic 22** | Image tier pipeline + symmetric fullscreen viewer | TB-037, TB-036, TB-035, TB-027 (verify), TB-032 (subsumed) | Designer-led + backend + FE; ~12-15 h | Yes (fullscreen UX — DESIGNER drives, not operator) |
| **Epic 23** | Share-view security hardening (post-Init-12 tail) | TB-033, TB-034, TB-026 sub#6 per-token | Backend + FE hardening; ~5-7 h | No (autonomous design choices: TB-033 policy, TB-034 keying) |
| **Epic 24** | Test infrastructure hygiena | TB-030 | Pure refactor (13 files); ~1 h | No |
| **Standalone Story 25.1** | Mobile photo-reorder touch-action | TB-038 | CSS one-liner; ~30 min | No |

### 1.3 Voice-heavy decisions already aligned

Per [[feedback_voice_heavy_dedicated_grilling]] ("operator prefers stronger
upfront grilling over mid-init monitoring"), all voice-heavy items were
grilled BEFORE this SCP was drafted. Answers locked into Story AC at SCP-time:

1. **TB-037 fullscreen viewer SURFACE scope** — symmetric (share +
   authenticated catalog detail). Drives Story 22.3 AC1: viewer mounts on
   both `/share/$token` and authenticated `/catalog/$modelId` detail page.
   Designer engagement (Task #5) handles UX SHAPE (modal vs lightbox library,
   dimensions, gestures, trigger placement) — operator carved out scope
   division: "designerka decyduje [o UX], do mnie uderzaj z biznesowym
   grillingiem".
2. **TB-022 inclusion** — confirmed, but Init 13 Story 20.3 already shipped
   the srcOverride hook. Folded into Story 22.3 as consumer (no new
   srcOverride work).
3. **TB-026 share rate-limit** — app-level per-token cap ON TOP OF existing
   per-IP cap (defense-in-depth). 60 req/min/token target locked into Story
   23.3 AC2 as configurable env (`SHARE_PER_TOKEN_RATELIMIT_PER_MINUTE`,
   default 60).

## Section 2 — Impact Analysis

### 2.1 Epic Impact

**Current epics (Init 11-15) in `working` or `review` status at SCP draft time:**

- `epic-19: working` — 3 stories `done`, 3 stories `review` (19.2 nginx
  throughput cap pending operator deploy + sync.sh, 19.5 ShareCarousel
  pending Codex review, 19.6 STL preview render pending Codex review). Init
  16 does NOT modify Epic 19 scope; operator's manual deploy of 19.2 +
  Codex round-out on 19.5/19.6 close it naturally.
- `epic-21: done` — closed during 2026-05-23 batch.

**No Init 11-15 epic re-scoping is needed for Init 16.** All Init 16 epics
are NEW; the Init 11-15 close-out tail (19.2 deploy, 19.5+19.6 Codex)
proceeds independently and converges into the Init 11-15 retro that has
already shipped.

**New epics introduced by Init 16:**

| Epic | Status at SCP-time | Sequencing | Notes |
|------|-------|------|-------|
| Epic 22 — Image tier pipeline + fullscreen viewer | backlog | Designer engagement (Task #5) BEFORE Story 22.3 spec; Stories 22.1 (BE) and 22.2 (FE consumers) can run in parallel after designer UX spec; 22.4 hygiene last | Biggest epic; resolves operator-felt perf pain (TB-036 503s, TB-037 4MB blobs in carousel) |
| Epic 23 — Share-view security hardening | backlog | Independent of Epic 22; all 3 stories sequenceable in any order; 23.3 carries operator-stated 60 req/min threshold | Per [[feedback_share_view_scope_boundary]] this closes the share-view security tail; no further UX work expected on `/share/*` post-Init-16 |
| Epic 24 — Test infrastructure hygiena | backlog | Independent; single story; ~1h | Refactor-only; no behavior change |
| Standalone Story 25.1 (mobile photo-reorder touch-action) | backlog | Independent; ~30 min | Smallest unit; can ride along with any Init 16 deploy |

### 2.2 Story Impact

**Current sprint-status carryover:**

- Stories `19-2`, `19-5`, `19-6`, `20-2` are in `review` status. Init 16
  does NOT touch these. They will close via Codex round-out + operator deploy
  (19.2 case) outside Init 16 execution.

**New stories under Init 16:**

| Story | Title | TB | Codex routing | Designer? |
|---|---|---|---|---|
| 22.1 | Backend gallery tier worker + variant routing + backfill | TB-037 BE | gpt-5.5 (worker + Alembic) | No |
| 22.2 | FE carousel gallery-tier consumption (share + catalog detail) | TB-037 FE | gpt-5.4-mini (FE) | No |
| 22.3 | Symmetric fullscreen viewer (share + catalog detail) | TB-037 viewer + TB-022 consumer | gpt-5.4-mini (FE) | Yes (UX spec upfront) |
| 22.4 | Post-tier hygiene (TB-035 unidentified format + TB-027 verify + TB-036 503 verify) | TB-035, TB-027 verify, TB-036 verify | gpt-5.4-mini | No |
| 23.1 | Share-view blob cache hardening (StrictMode refcount + revocation) | TB-033 | gpt-5.5 (security/concurrency class) | No |
| 23.2 | STL preview source-tracking + single-flight lock | TB-034 | gpt-5.5 (security/data-integrity class) | No |
| 23.3 | Share per-token rate-limit middleware | TB-026 sub#6 per-token | gpt-5.5 (security class) | No |
| 24.1 | Centralized `_admin_token` helper sweep (13 files) | TB-030 | gpt-5.4-mini (routine refactor) | No |
| 25.1 | Mobile photo-reorder `touch-action: none` on dnd-kit handle | TB-038 | gpt-5.4-mini (routine FE) | No |

### 2.3 Artifact Conflicts

**PRD (`_bmad-output/planning-artifacts/prd.md`):**
- Extend with `## Initiative 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)`
  H2 section.
- FR16-* requirements: FR16-TIER-1 (gallery variant pipeline), FR16-VIEWER-1
  (symmetric fullscreen viewer), FR16-HARDENING-1 (blob cache + STL preview
  + per-token rate-limit), FR16-HYGIENE-1 (test helper centralization +
  mobile drag CSS).
- NFR16-* requirements: NFR16-PERF-1 (gallery tier ≤500 KB longest-edge
  designer-tuned), NFR16-DETERMINISM-1 (3× consecutive pass discipline
  carried forward), NFR16-VISUAL-VERIFICATION-1 (every UI story carries
  agent-browser pre-CR pass per [[feedback_frontend_visual_verification]]),
  NFR16-SECURITY-1 (per-token rate-limit threat-vector enumeration per
  [[feedback_security_vector_enumeration]]).

**Architecture (`_bmad-output/planning-artifacts/architecture.md`):**
- Extend with `## Initiative 16` H2 section.
- Decision W: gallery tier variant pipeline shape (build-time worker output
  + `?variant=gallery` routing + designer-tuned dimensions).
- Decision X: blob cache hardening shape (pending refcount map + revocation
  policy A=page-mount-scoped clear).
- Decision Y: per-token rate-limit middleware shape (Redis sliding window
  per share-token, additive to existing per-IP middleware from Story 19.1).

**Epics (`_bmad-output/planning-artifacts/epics.md`):**
- Extend with `## Initiative 16` H2 section.
- Epic E22 + E23 + E24 + Standalone S25.1 declared with story IDs and
  sequencing notes.

**Note:** Initiatives 13, 14, 15 may not yet be H2-appended to epics.md/prd.md
based on pre-enumeration. If absent, Init 16 SCP execution surfaces a
housekeeping todo: backfill Init 13/14/15 H2 sections from their respective
SCPs (Init 11-15 SCP §2-5). Tracked as Task #3 sub-bullet.

### 2.4 Technical Impact

**Code surfaces affected:**

- Backend Python:
  - `apps/api/app/workers/generate_thumbnail.py` — extend to also produce
    `.gallery.webp` variant (Story 22.1)
  - `apps/api/app/modules/sot/router.py:variant routing` — add `gallery`
    branch (Story 22.1)
  - `apps/api/scripts/enqueue_thumbnail_backfill.py` +
    `infra/scripts/backfill-thumbnails.sh` — extend for gallery tier
    sweep (Story 22.1)
  - `apps/api/app/modules/share/router.py:dispatch` — add per-token rate-
    limit middleware OR extend existing middleware with token-keyed
    additional cap (Story 23.3)
  - `workers/render/render/worker.py:render_stl_previews` — source-track
    by STL sha256 OR add FK (Story 23.2 design choice)
  - `apps/api/tests/_test_helpers.py` (NEW) — centralized `admin_token`,
    `agent_token`, `member_token` helpers; 13 test files migrate (Story 24.1)

- Frontend TypeScript/React:
  - `apps/web/src/ui/custom/ModelCard.tsx` + `CardCarousel.tsx` —
    `?variant=thumb` stays; gallery tier introduced in carousel main-frame
    consumers (Story 22.2)
  - `apps/web/src/routes/share/$token.tsx:ShareCarousel` — switch main
    frame to `?variant=gallery` (Story 22.2); thumb strip stays
    `?variant=thumb`
  - NEW `apps/web/src/modules/catalog/components/ImageFullscreenViewer.tsx`
    (working name; designer may rename) — symmetric component consumed by
    both `/share/$token` and `/catalog/$modelId` detail page (Story 22.3)
  - `apps/web/src/routes/share/$token.tsx:_shareBlobCache` +
    `_shareBlobInflight` — add `_pending` count map for StrictMode safety +
    page-unmount revocation policy (Story 23.1)
  - `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:DragHandle` —
    add `touch-none` Tailwind class (Story 25.1)

- Infrastructure:
  - No new infra. Existing Story 19.2 `limit_rate 2m` + `limit_conn
    share_anon_conn 5` are SUFFICIENT at nginx level; Init 16 layers
    per-token cap at app level (Redis sliding window) per operator's
    defense-in-depth choice.

- Testing surfaces:
  - Centralized `_test_helpers.py` consumed by 13 test files (Story 24.1)
  - StrictMode-safe acquireShareBlob test (Story 23.1)
  - Single-flight lock contention test (Story 23.2)
  - Per-token rate-limit middleware tests (Story 23.3)
  - Backfill hygiene smoke for gallery tier (Story 22.4 — `inspected=N
    rendered=N errors=0` post-tier-ship)
  - Mobile photo-reorder agent-browser visual verify on touch viewport
    (Story 25.1)

**Auto-deploy:** Per [[feedback_auto_deploy_dev]], every code-merge to `main`
triggers `infra/scripts/deploy.sh` to .190. Doc-only commits skip. Per-story
shipping order will produce ~8 deploys + 0-2 fix-up deploys.

## Section 3 — Recommended Approach

### 3.1 Path forward selection

**Option 1 — Direct Adjustment (1 new initiative, 3 new epics + 1 standalone
story): SELECTED.**

Rationale:
- Operator directive explicitly scopes "wszystkie otwarte backlog itemy"
  into ONE coordinated initiative. No reverting Init 11-15 work is needed
  (pre-enumeration already reconciled the partial-overlap items).
- Per [[feedback_default_to_bmad_workflow]]: multi-PR batches from review
  docs ARE epics in disguise. Folding 9 candidates into 3+1 BMAD units
  (~8 stories) respects that signal.
- Per [[feedback_vanilla_bmad_first]]: ceremony stays in force — full
  CS/DS/CR cycle per story, ER per epic, sprint-status update before
  execution.
- Effort: ~16-22 h estimated. 5h Anthropic budget at SCP-draft = 1.0% used,
  so plenty of headroom; expected to fit comfortably in 2-3 5h sessions.
- Risk: Low. Stories are surgical (one-file CSS, blob cache patch, per-
  token middleware, helper sweep). The only "design-level" story is 22.3
  (fullscreen viewer UX) and that's gated by designer engagement BEFORE
  spec authoring — the operator-blessed pattern.

Option 2 (Rollback) and Option 3 (PRD MVP Review) considered and rejected:
- Rollback: nothing in Init 11-15 needs reverting; the partial-overlap
  items (TB-027 / TB-029 / TB-022) are correctly shipped at their reduced
  scope. Init 16 builds ON them, not against them.
- MVP Review: MVP scope is not affected. All Init 16 items are quality /
  hardening / hygiene; no new product surface that requires PRD goal
  recalibration.

### 3.2 Initiative sequencing within Init 16

Designer engagement (Task #5) gates Story 22.3 spec authoring. Other
stories can run before, during, or after the designer session. **Recommended
chain** for autonomous execution:

```
Phase A (kick-off):
  Task #3 — sprint-status + epics.md/prd.md/architecture.md H2 append
  Task #4 — bmad-sprint-planning (formal sprint-status entries)
  Task #5 — designer UX session for Story 22.3 (UPFRONT — no time-on-the-clock pressure)

Phase B (parallel within constraints):
  Epic 24 / Story 24.1 — TB-030 helper sweep (~1h, low risk, easy first win to confirm chain works)
  Standalone Story 25.1 — TB-038 mobile drag (~30 min, mechanical CSS)
  Epic 23 stories (any order):
    Story 23.1 — TB-033 blob cache hardening
    Story 23.2 — TB-034 STL preview source-tracking + lock
    Story 23.3 — TB-026 per-token rate-limit

Phase C (image pipeline + viewer — sequenced):
  Story 22.1 — TB-037 backend (gallery tier worker + variant routing + backfill)
  Story 22.2 — TB-037 FE consumption (depends on 22.1 backend shipped)
  Story 22.3 — TB-037 symmetric fullscreen viewer (depends on designer UX + 22.2 carousel landed)
  Story 22.4 — TB-035 + TB-027 verify + TB-036 verify (depends on 22.1 backend deployed for backfill rerun)

Phase D (close-out):
  Task #9 — Epic 22/23/24 retros (aggregate per [[feedback_batch_close_out_rule]] if cross-epic lessons emerge)
  Update triage-backlog.md with final TB statuses
  Sprint-status.yaml flip all Init 16 epics to done
```

### 3.3 Codex routing strategy

Per [[feedback_codex_model_routing]] (Pro 5x baseline) and
[[feedback_codex_parallel_review]]:

- **gpt-5.5 (heavy / security / data-integrity):** 22.1 (Alembic + worker
  changes), 23.1 (concurrency + revocation), 23.2 (single-flight lock +
  data correctness), 23.3 (security class).
- **gpt-5.4-mini (routine / FE / hygiene):** 22.2, 22.3, 22.4, 24.1, 25.1.
- **Parallel reviews:** up to 3 concurrent on routine-class only (per
  [[feedback_codex_parallel_review]]); heavy/security single-flight.
- **Pre-merge gate per [[feedback_pre_merge_gate_checklist]]:** routing
  intent classified BEFORE Codex invocation; full-suite pytest for shared-
  state changes (24.1 touches 13 test files, full-suite mandatory); `npm
  run build` for FE route changes (22.2, 22.3); visual verify for rendered
  components (22.2 carousel, 22.3 fullscreen, 25.1 mobile drag).

### 3.4 Designer engagement shape (Story 22.3)

Per operator directive "wierze też w naszą designerkę", invoke
`bmad-agent-ux-designer` (Sally) BEFORE Story 22.3 spec authoring. UX session
input: TB-037 verbatim shape + symmetric surface decision (both /share and
/catalog detail). Designer produces UX spec covering:
1. **Modal pattern:** custom matching 3D viewer modal style OR OOTB library
   (PhotoSwipe, react-image-lightbox, yet-another-react-lightbox).
2. **Gallery tier dimensions:** longest-edge target (designer-tuned;
   operator's intuition "do najmniejszej krawędzi takiej, jaka maksymalnie
   może nam się pojawić" suggests 1280-1920px range).
3. **Trigger pattern:** button-in-carousel-header / click-on-main-frame /
   keyboard-shortcut / combo.
4. **Mobile gesture support:** pinch-zoom + swipe-down-to-close /
   desktop-only first / progressive.
5. **i18n keys** for trigger label and close affordance.

Designer UX spec lands as inline section in Story 22.3 spec file BEFORE
`bmad-create-story` finalizes. Codex review on the spec is optional but
recommended (gpt-5.4-mini quick pass) per [[feedback_pre_merge_gate_checklist]].

### 3.5 Operator interaction surface during execution

Per [[feedback_itcm_autonomous_mode]] post-SCP-approval: I OWN all execution.
Operator surface limited to:
- Initial designer engagement (Story 22.3 UX session — designer may grill
  operator on positioning/voice; that flows through me as ITCM)
- Real product blockers (e.g., a Codex round-2 P1 reveals an architectural
  contradiction → escalate)
- Initiative completion summary
- Manual infra dependency: Story 19.2 nginx config deploy is the only
  cross-Init dependency; if operator hasn't shipped it before Init 16
  finishes, throughput cap remains code-only-no-runtime — flagged as
  cross-init carry-over, not Init 16 blocker.

No operator-handshake pauses on per-story Codex round-1 / round-2 fix-up
cycles (precedent: Init 11-15 18 reviews / 11% of 5h budget / 0 operator
interrupts).

## Section 4 — Detailed Change Proposals

### 4.1 Epic E22 — Image Tier Pipeline + Symmetric Fullscreen Viewer

**Story 22.1 — Backend gallery tier worker + variant routing + backfill**
- AC1: `generate_thumbnail` worker produces BOTH `<basename>.thumb.webp`
  (existing) AND `<basename>.gallery.webp` (NEW) at thumbnail-job dispatch
  on upload. Dimensions: thumb=128px longest-edge (existing); gallery=designer-
  tuned target (default 1920px pending designer override).
- AC2: `GET /api/models/{id}/files/{fid}/content?variant=gallery` returns
  the gallery WebP blob; falls back to original silently when sibling
  missing (mirror existing thumb fallback pattern).
- AC3: Backfill script `enqueue_thumbnail_backfill.py` extended to also
  generate gallery tier for existing files. Smoke output shape:
  `inspected=N already_present=A enqueued=E rendered=R missing_original=0
  errors=0` (errors >0 surfaces TB-035-style for Story 22.4).
- AC4: Alembic migration applied if storage shape changes (likely
  none — sibling-file pattern matches existing). Full pytest 850/850+ PASS.
- AC5: Codex review on gpt-5.5; round-2 fix-ups if P1/P2 surface; CLEAN
  required before next-story handoff.
- Codex routing: gpt-5.5 (worker + storage layer).

**Story 22.2 — FE carousel gallery-tier consumption (share + catalog detail)**
- AC1: `apps/web/src/routes/share/$token.tsx:ShareCarousel` main frame
  switches from `data.images` URLs (currently full) to `?variant=gallery`.
  Thumb strip stays `?variant=thumb`.
- AC2: `apps/web/src/ui/custom/CardCarousel.tsx` (catalog detail surface)
  main frame consumes `?variant=gallery`. Card-grid stays `?variant=thumb`
  (Story 20.1 baseline).
- AC3: Visual baselines regenerated for carousel surface across 4 viewport
  projects. Operator manual verify per [[feedback_frontend_visual_verification]].
- AC4: Vitest tests cover new variant URL construction. lint + tsc clean.
- AC5: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini (routine FE).

**Story 22.3 — Symmetric fullscreen viewer (share + catalog detail)**
- AC1 (designer-locked): UX shape per designer-produced spec (modal vs
  lightbox library, trigger pattern, gesture support, i18n keys).
- AC2: Component mounts on BOTH `/share/$token` AND
  `/catalog/$modelId` detail page per operator's symmetric directive.
- AC3: Fetches `?variant=full` (= original blob) for fullscreen frame;
  thumb strip in fullscreen view uses `?variant=thumb` to preserve
  bandwidth-bounded preload.
- AC4: For anonymous (/share) route: integrates with Story 23.1
  `acquireShareBlob` cache + reuses Init 12 share file-list endpoint
  (Decision T).
- AC5: For authenticated (/catalog) route: uses default-auth URL
  construction. NO srcOverride needed (Story 20.3 srcOverride hook is
  the Viewer3DInline pattern; this is image, not 3D).
- AC6: Visual baselines created (NEW surface); 4 viewport projects;
  operator manual verify.
- AC7: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini (routine FE).

**Story 22.4 — Post-tier hygiene (TB-035 + TB-027 verify + TB-036 verify)**
- AC1: TB-035 — grep `thumbnail.unidentified` warning post-gallery-tier
  backfill run, identify file_id, classify (corrupt / unsupported / SVG
  trivial), document outcome in `_bmad-output/implementation-artifacts/spec-22-4-*.md`.
- AC2: TB-027 verify — sample 5-10 catalog cards on retina viewport
  devtools, capture actual served URL + Content-Length for thumb +
  gallery; confirm gallery tier serves at expected size band (~150-500
  KB) not falling back to original. Documented in spec.
- AC3: TB-036 verify — re-run HAR capture analog on share-view carousel
  load; count 503 vs 200 vs blob-cached. Expected near-zero 503 once
  gallery tier is ~10× smaller → slot release ~10× faster → less
  overlap.
- AC4: Cleanup commit if any one-shot fixes emerge from (1)-(3); otherwise
  hygiene-pass-only doc commit.
- AC5: Codex review gpt-5.4-mini (no functional change typical).
- Codex routing: gpt-5.4-mini.

### 4.2 Epic E23 — Share-View Security Hardening

**Story 23.1 — Share-view blob cache hardening (StrictMode refcount + revocation)**
- AC1: `acquireShareBlob` at `apps/web/src/routes/share/$token.tsx:88-148`
  tracks inflight subscribers in `_pending: Map<string, number>` map;
  increment _pending[src] before fetch starts; in resolve handler, use
  _pending[src] as initial refCount (if 0 — all unmounted, revoke blob +
  skip cache entry creation).
- AC2: Page-mount-scoped cache invalidation (autonomous design choice
  Decision X: option A from TB-033 fix-shape options). Clear `_shareBlobCache`
  + `_shareBlobInflight` when `/share/$token` route unmounts.
  Rationale: simplest, deterministic, preserves "revoke → close → reopen"
  contract.
- AC3: Deterministic mounting test mocks StrictMode double-mount; asserts
  refCount converges to 0 + URL revoked when all consumers unmount with
  inflight load.
- AC4: Vitest tests + full-pytest no-regression (no backend changes).
- AC5: Codex review gpt-5.5 (concurrency class) CLEAN.
- Codex routing: gpt-5.5.

**Story 23.2 — STL preview source-tracking + single-flight lock (TB-034)**
- AC1 (autonomous design choice Decision X.2): source-track by STL sha256
  (option A from TB-034) — `ModelFile.original_name = f"<view>-{stl_sha256[:8]}.png"`.
  Worker counts only previews matching CURRENT primary STL's sha256.
  Rationale: boring-tech; avoids new FK column + migration; sha256 is
  already computed during upload.
- AC2: Single-flight Redis SETNX lock with TTL=300s at
  `apps/api/app/modules/share/router.py:dispatch`. Pattern: `lock_key =
  f"share:stl_preview_lock:{stl_for_preview}"`; `acquired = await
  redis.set(lock_key, "1", nx=True, ex=300)`. Worker releases lock on
  completion / failure.
- AC3: Race-condition contention test: spawn 2 concurrent share-view
  requests via TestClient; assert only ONE arq job enqueued for the
  same STL.
- AC4: Stale-preview cleanup task (separate from this story scope per
  TB-034 fix-shape) — if operator surfaces STL-replace workflow later,
  fold into Init 17+; flagged in spec.
- AC5: Codex review gpt-5.5 (data-integrity class) CLEAN.
- Codex routing: gpt-5.5.

**Story 23.3 — Share per-token rate-limit middleware (TB-026 sub#6 per-token)**
- AC1: New middleware OR extension of existing `share_anon_ratelimit_*`
  middleware at `apps/api/app/modules/share/router.py`. Per-token sliding
  window via Redis: ZADD timestamps to sorted set keyed `share_token_ratelimit:<token>`;
  ZREMRANGEBYSCORE old timestamps; ZCARD count vs cap.
- AC2: Configurable env: `SHARE_PER_TOKEN_RATELIMIT_PER_MINUTE` (default
  60 per operator decision), `SHARE_PER_TOKEN_RATELIMIT_WINDOW_SECONDS`
  (default 60). 429 response with `Retry-After` header on overage.
- AC3: Composable with Story 19.1 per-IP middleware: both checks fire;
  EITHER overage returns 429. Test fixture exercises both legs
  independently.
- AC4: Threat-vector enumeration in spec per [[feedback_security_vector_enumeration]]:
  share-token leak vectors (referrer header, log, screenshot share),
  IP-pool-attacker scenarios, retry-after backoff exploitation, share-
  scoped DDoS multiplier.
- AC5: Pytest fixtures + full-suite no-regression. Operator pen-test via
  ezop-kbk.ddns.net (per [[reference_external_test_source]]) AFTER deploy
  to .190.
- AC6: Codex review gpt-5.5 (security class) CLEAN.
- Codex routing: gpt-5.5.

### 4.3 Epic E24 — Test Infrastructure Hygiena

**Story 24.1 — Centralized `_admin_token` helper sweep (TB-030)**
- AC1: New `apps/api/tests/_test_helpers.py` exports `admin_token(user_id)`,
  `agent_token(user_id)`, `member_token(user_id)` reading `get_settings().jwt_secret`
  (not hardcoded constant).
- AC2: 13 test files migrated to import + call helper: `test_sot_admin_categories.py`,
  `test_sot_admin_external_links.py`, `test_sot_admin_tags.py`,
  `test_sot_admin_notes.py`, `test_sot_admin_files.py`,
  `test_sot_admin_prints.py`, `test_sot_auth_boundary.py`,
  `test_2fa_verify.py`, `test_2fa_enrollment.py`, `test_2fa_disable.py`,
  `test_2fa_regenerate.py`, `test_enforce_2fa_login.py`,
  `test_thumbnail_pipeline.py`.
- AC3: Reference pattern: Story 18.4 `be11035` (`test_last_active_middleware.py`)
  + Story 18.4 round-2 `2ae6569` (`test_sot_admin_models.py`).
- AC4: Full pytest 846/846 PASS deterministic 3× consecutive
  (NFR16-DETERMINISM-1).
- AC5: Codex review gpt-5.4-mini CLEAN. No FE / no doc impact.
- Codex routing: gpt-5.4-mini.

### 4.4 Standalone Story S25.1 — Mobile photo-reorder touch-action

**Story 25.1 — Mobile photo-reorder `touch-action: none` on dnd-kit handle (TB-038)**
- AC1: `apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx:244-253`
  `DragHandle` button className extended with Tailwind `touch-none`
  (= `touch-action: none`).
- AC2: Verify on real touch device (or agent-browser touch emulation per
  [[feedback_frontend_visual_verification]]) that vertical drag reorders
  rows without scrolling the page; touching outside the grip area
  (`flex-1` button) still scrolls naturally.
- AC3: Optionally revisit TouchSensor `delay: 250` activation threshold
  ([PhotosTab.tsx:46-51](../../apps/web/src/modules/catalog/components/tabs/PhotosTab.tsx#L46-L51))
  for snappier feel post-fix — if operator surfaces during review.
- AC4: Existing vitest tests no-regression; tsc + lint clean.
- AC5: Codex review gpt-5.4-mini CLEAN.
- Codex routing: gpt-5.4-mini.

## Section 5 — Implementation Handoff

### 5.1 Scope classification

**MODERATE** — 1 new initiative, 3 new epics + 1 standalone story, ~8 stories.
Implementation handoff fully within Developer agent (Claude as ITCM autonomous
per [[feedback_itcm_autonomous_mode]]); no PM/Architect escalation needed;
operator surface = designer UX session + cross-init dependency note + final
approval.

### 5.2 Agent / role assignment

| Phase | Agent | Responsibility |
|---|---|---|
| SCP approval | Operator (Ezop) | Explicit yes/no on this document |
| Sprint planning + artifact append | Claude (BMAD bmad-sprint-planning skill) | Append Init 16 H2 to prd.md/architecture.md/epics.md; add E22/E23/E24/S25.1 entries to sprint-status.yaml as backlog; close TB-029 in triage-backlog.md (housekeeping) |
| Designer UX session | Claude + bmad-agent-ux-designer (Sally subagent) | Produce UX spec for Story 22.3 fullscreen viewer; designer may grill operator via Claude as proxy if voice-heavy points emerge |
| Story execution | Claude (BMAD bmad-create-story → bmad-dev-story → bmad-code-review cycle per story) | Full BMAD ceremony; auto-deploy per merge per [[feedback_auto_deploy_dev]]; Codex review per routing in §3.3 |
| Epic retros | Claude (BMAD bmad-retrospective skill) | Per-epic OR aggregate per [[feedback_batch_close_out_rule]] if cross-epic lessons emerge |
| Init 16 close-out | Claude + Operator | Update triage-backlog statuses for all 9 resolved TB items + final operator sign-off |

### 5.3 Success criteria

- All 9 in-scope TB candidates flipped `candidate` → `done` (or
  `closed-by-displacement` for TB-032).
- TB-029 housekeeping: status flipped `candidate` → `done` (Init 13 Story
  20.2 reconciliation).
- Sprint-status.yaml epic-22 / epic-23 / epic-24 all `done` with story
  detail comments.
- All Codex reviews CLEAN (round-1 OR round-2 fix-up acceptable; round-3+
  surfaces as new TB candidate per [[feedback_preexisting_issue_threshold]]).
- Full pytest 850+/850+ PASS deterministic 3× consecutive per NFR16-DETERMINISM-1.
- Vitest 408+/408+ PASS; tsc + lint clean across all FE changes.
- Visual baselines refreshed for Stories 22.2 (carousel) + 22.3
  (fullscreen) + 25.1 (mobile drag) with operator-blessed sign-off.
- All deploys to .190 with verify-symbolication PASS + runbook fingerprint
  OK per [[feedback_auto_deploy_dev]].

### 5.4 Cross-init dependencies

- **Init 12 Story 19.2 (nginx throughput cap deploy)** — operator manual
  infra task pending (configs repo uncommitted). Not an Init 16 blocker,
  but pen-test exercise in Story 23.3 AC5 expects both per-IP nginx cap
  AND per-token app-level cap to be live for full DDoS posture. If 19.2
  still un-deployed at Init 16 close, flag in retro + carry forward to
  Init 17 reminder.

### 5.5 Initiative 13-15 H2-append housekeeping

Pre-enumeration revealed Initiatives 13, 14, 15 may not be H2-appended to
`epics.md` / `prd.md` / `architecture.md` (only Init 0-12 visible at grep
time). The Init 11-15 SCP carried the H2 content but landing into the
canonical docs may have been skipped. **Task #3** sub-bullet: as part of
Init 16 sprint-planning, verify + backfill the Init 13/14/15 H2 sections
from the predecessor SCP into the canonical docs. If already present (grep
limitation), no-op. Doc-only commit; auto-deploy skipped.

## Section 6 — Final Review

### 6.1 Checklist completion summary

| Section | Items | Status |
|---|---|---|
| §1 Trigger and Context | 1.1, 1.2, 1.3 | All [Done] |
| §2 Epic Impact Assessment | 2.1, 2.2, 2.3, 2.4, 2.5 | All [Done] (2.5 — no resequencing needed; Init 11-15 tail closes naturally outside Init 16) |
| §3 Artifact Conflict and Impact Analysis | 3.1, 3.2, 3.3, 3.4 | All [Done] |
| §4 Path Forward Evaluation | 4.1, 4.2, 4.3, 4.4 | Option 1 selected; 4.2 + 4.3 [Not viable] documented |
| §5 SCP Components | 5.1, 5.2, 5.3, 5.4, 5.5 | All [Done] |
| §6 Final Review | 6.1, 6.2, 6.3, 6.4, 6.5 | 6.1-6.2 [Done]; 6.3 [Awaiting operator]; 6.4 [Blocked-by 6.3]; 6.5 [Blocked-by 6.3] |

### 6.2 Asks of operator

**One ask:** explicit yes/no/revise on this SCP. On approval:
- Sprint-status.yaml + epics.md/prd.md/architecture.md H2 append proceed
  autonomously (Task #3).
- bmad-sprint-planning fires (Task #4).
- Designer UX session for Story 22.3 fires (Task #5; designer may surface
  questions to operator via me).
- Per-story autonomous loop begins (Task #6/7/8).
- All other operator interactions are voluntary (designer-proxy questions,
  cross-init dep on Story 19.2 deploy).

### 6.3 Memory entries informing this initiative

- [[feedback_default_to_bmad_workflow]] — multi-PR batches = epics in
  disguise → SCP path
- [[feedback_vanilla_bmad_first]] — full BMAD ceremony preserved
- [[feedback_itcm_autonomous_mode]] — Claude OWNS execution post-SCP
- [[feedback_voice_heavy_dedicated_grilling]] — TB-037 grilling fired
  upfront
- [[feedback_scp_pre_enumeration_phase]] — enumeration completed pre-draft
- [[feedback_share_view_scope_boundary]] — share-view terminus boundary;
  TB-037 fullscreen = quality exception not UX enrichment
- [[feedback_codex_model_routing]] — Pro 5x routing per story
- [[feedback_codex_parallel_review]] — parallel routine reviews
- [[feedback_pre_merge_gate_checklist]] — typed pre-Codex gate
- [[feedback_frontend_visual_verification]] — UI story visual verify gate
- [[feedback_security_vector_enumeration]] — Story 23.3 threat-vector
  enumeration upfront
- [[feedback_auto_deploy_dev]] — per-merge auto-deploy
- [[feedback_batch_close_out_rule]] — review-fix-commit closes batches
- [[feedback_pytest_timeout]] — `timeout 600` wrapper on pytest invocations
- [[feedback_lazy_import_discipline]] — Story 22.3 lazy import for viewer
- [[feedback_shared_cache_in_react]] — Story 23.1 informed by prior cache
  hardening guidance
- [[feedback_worker_single_flight]] — Story 23.2 single-flight discipline
- [[feedback_threejs_hsl_parsing]] — bonus tag-along; not triggered in
  Init 16 unless viewer touches three.js Color tokens
- [[feedback_collaboration_division]] — operator infra-side dep (Story
  19.2 deploy) respected
- [[reference_external_test_source]] — Story 23.3 pen-test source

---

**End of SCP draft.** Awaiting operator approval (yes / revise / no).
