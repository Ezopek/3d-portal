---
title: "Sprint Change Proposal — Initiatives 11-15 (Triage Backlog Cleanup Batch)"
type: sprint-change-proposal
initiative_scope: [11, 12, 13, 14, 15]
status: approved
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-23
approved_by: Ezop
approved_at: 2026-05-23
approved_via: |
  AskUserQuestion selection "Approve — lecę Init 11 ITCM autonomous" 2026-05-23
  immediately after SCP draft surfaced (~10 min draft window). Phase A kickoff
  authorized; Phase B-E continue per §2.3 sequencing with voice-heavy grilling
  triggers preserved.
execution_directive: |
  Operator pre-approved 5-init clustering via AskUserQuestion 2026-05-23 (Option 1
  selected: "Clustering 5-inicjatywowy (Init 11-15)" — explicit follow-up "lecisz
  autonomicznie w trybie ITCM ze wszystkimi bez czekania"). ITCM autonomous mode
  per [[feedback_itcm_autonomous_mode]]; no operator-handshake pauses; hard-stop
  only on 5h ≥ 80% (sleep through reset per [[feedback_autonomous_sleep_on_budget]]),
  7d ≥ 95%, or real product blocker; no extra_usage opt-in. Phase 0 (Codex 0.133.0
  docs sync after Plus → Pro 5x upgrade) completed BEFORE Init 11 kickoff per
  operator instruction.
mode: batch-presented (operator-pragmatic variant of BMAD Incremental — full
  draft surfaced once, operator feedback consolidated; matches Init 6 / Init 7+8+9 /
  Init 10 SCP precedent)
change_scope_classification: major  # 5 new initiatives, 4+ new epics, ~20+ stories
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                      # extend (Initiative 11/12/13 H2 sections — Init 14/15 are non-PRD-impacting)
  - _bmad-output/planning-artifacts/architecture.md             # extend (Init 12 share rate-limit + STL preview pipeline + Init 13 srcSet / Add-Model decisions)
  - _bmad-output/planning-artifacts/epics.md                    # extend (Initiative 11/12/13/14 H2 + Epic E18 + E19 + E20 + E21 stories; Init 15 is meta/deferred — no epic)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # extend (E18 + E19 + E20 + E21 entries, all status backlog)
  - _bmad-output/triage-backlog.md                              # 13 candidates being promoted (TB-014 + TB-016-remaining + TB-017 + TB-018-#2 + TB-021 + TB-022 + TB-023 + TB-024 + TB-025 + TB-026 + TB-027 + TB-028 + TB-029)
  - sprint-change-proposal-2026-05-22-init10.md                 # predecessor SCP (Init 10); this SCP follows Initiative-N H2-append pattern
  - ~/.claude/codex-invocation-guide.md                         # already updated 2026-05-23 for Codex 0.133.0 + Pro 5x routing (Phase 0)
predecessor_initiative: 10
trigger:
  source: |
    Operator batch report 2026-05-22 evening (5 fresh items from hands-on portal use:
    add-note 404, share view austerity, catalog full-res perf, admin Users table
    scroll, admin Add Model discoverability) — plus operator explicit ask 2026-05-23
    morning to extend scope to "paczka ze wszystkich obecnie otwartych backlogowych
    tematów" covering all 13 open triage-backlog candidates.
  shape: |
    13 open `status: candidate` items in `_bmad-output/triage-backlog.md` spanning:
    5 fresh ops-observed bugs/UX (TB-025..TB-029 from 2026-05-22), 6 carry-forward
    candidates from Init 8/9/10 retros (TB-016 partial, TB-017, TB-018 remaining,
    TB-021, TB-022, TB-023, TB-024), 1 long-standing enum gap (TB-014 from 2026-05-13).
    Operator-aligned clustering: 5 initiatives by job-shape (quick wins / share epic /
    catalog UX / test infra / meta deferred).
  evidence_class: |
    Mixed — direct operator hands-on observation (TB-025+TB-027+TB-028+TB-029) +
    HAR-confirmed root-cause-pinned bug (TB-025 has tmp/notes_404.har) + multi-retro
    convergence (TB-016+TB-017+TB-018+TB-022+TB-023+TB-024 surfaced across Init 6-10
    retros) + Story 15.1 unmasked failures (TB-021) + agent-runbook full-pass review
    (TB-014 from 2026-05-13). No security audit, no external pen-test, no automated
    gate hit.
business_decisions_aligned_pre_scp:
  - clustering_shape: |
      Option 1 (5-init clustering) selected over Option 2 (mega-epic) / Option 3
      (only fresh 5 from 2026-05-22) / Option 4 (only quick wins). Rationale:
      Option 1 keeps each initiative tractable per [[feedback_default_to_bmad_workflow]]
      ("multi-PR batches are epics in disguise"), respects per-job-shape grouping
      (UX-led / epic-sized / quick / test-infra / meta), avoids force-fitting voice-heavy
      items (TB-026 share enrichment, TB-029 Add-Model UX) into a generic batch.
  - execution_mode: |
      ITCM autonomous "bez czekania" — Claude OWNS all dev/fix work via subagents/
      Codex/1M context; surfaces ONLY real product blockers or initiative completion.
      Per [[feedback_itcm_autonomous_mode]], BMAD vanilla-first stays in force —
      no skipping create-story / dev-story / code-review / retrospective cycles.
  - codex_routing: |
      Codex 0.133.0 + Pro 5x in effect (~5× Plus quota). Routing per new memory
      [[feedback_codex_model_routing]]: heavy reviews on `gpt-5.5`, routine /
      parallel reviews on `gpt-5.4-mini`, fast tiny iterations on `gpt-5.3-codex-spark`.
      Local + cloud share 5h window.
recon_subagents_completed: []  # all pre-enumeration done by Claude main session via grep/Read/HAR/git inspection — no subagent dispatch needed
operator_blockers: []  # none at SCP draft time; voice-heavy grilling for TB-029 (Add-Model UX) and TB-026 (rate-limit thresholds) will fire INSIDE Init 12+13 respectively, not blocking SCP approval
---

# Sprint Change Proposal — Initiatives 11-15 (Triage Backlog Cleanup Batch)

## Section 1 — Issue Summary

### 1.1 Problem statement

The `_bmad-output/triage-backlog.md` file has accumulated **13 open candidates**
(`status: candidate`) across roughly two weeks of multi-initiative work
(2026-05-13 through 2026-05-22). The accumulation is the natural by-product of
healthy triage discipline — per [[feedback_preexisting_issue_threshold]] and
the file's own purpose statement, items land here when they don't justify
inline absorption into the active story but should not be lost. The cost of
letting them sit indefinitely is two-fold: (a) ergonomic decay — operator
hands-on use surfaces the same bug class repeatedly when a one-commit fix
exists (TB-025 add-note 404 had its root cause pinned in the candidate
write-up but did not get promoted), and (b) cumulative scope-creep — what
starts as one isolated UX paper-cut (TB-027 catalog perf) compounds across
adjacent surfaces (TB-022 share-anon viewer, TB-029 Add-Model discoverability)
until the next initiative has to triage them mid-flight.

Operator's 2026-05-22 batch (5 fresh items) and 2026-05-23 morning extension
("paczka ze wszystkich obecnie otwartych") together green-light a coordinated
backlog-sweep across the 13 candidates. The operator's explicit selection
(AskUserQuestion 2026-05-23) of Option 1 ("Clustering 5-inicjatywowy")
constrains the SCP shape: **NOT one mega-epic**, **NOT a quick-dev batch**,
**but 5 separate initiatives clustered by job-shape**:

| Initiative | Theme | TB candidates | Job-shape | Voice-heavy? |
|-----------|-------|---------------|-----------|--------------|
| **Init 11** | Quick wins bundle | TB-025, TB-028, TB-014, TB-021, TB-016 remaining | Multi-quick-dev cluster, single epic, ~5h | No |
| **Init 12** | Share view enrichment + rate-limiting | TB-026 (alone, 7 sub-items) | Own epic, PRD-impacting, ~10-20h | Yes (rate-limit thresholds, sub-item priority) |
| **Init 13** | Catalog UX uplift | TB-027, TB-029, TB-022 | UX-led, joint UX session, 3 stories, ~5-8h | Yes (Add-Model placement, modal-vs-route) |
| **Init 14** | Test infrastructure hardening | TB-018 #2 (hydrate pollution), TB-023 (credentialless fixture) | Test-arch focus, 1-2 stories, ~4-6h | No |
| **Init 15** | Meta + deferred | TB-024 (BMAD skill templates), TB-017 (TOTP rotation runbook, trigger 2027-05-20) | Doc-only / skill-file, ~1-2h | No |

**Total scope estimate: ~25-50 h across 5 initiatives, ~20-25 stories.**

The operator's directive ("lecisz autonomicznie w trybie ITCM ze wszystkimi
bez czekania") permits sequential execution without per-init re-approval, but
**voice-heavy items (Init 12 sub-priority, Init 13 Add-Model UX) MUST trigger
dedicated grilling at the point of relevance** per
[[feedback_voice_heavy_dedicated_grilling]] — those are NOT autonomous
decisions, they are operator-voice product judgments delayed-not-skipped.

### 1.2 Issue categorization (CC checklist §1.2)

**Mixed categorization across the 13 candidates** — predominantly hygiene
sweep (operator-aligned ongoing practice), with two voice-heavy product
decisions (Init 12 rate-limit thresholds + Init 13 Add-Model UX) and one
root-cause-pinned bug from Init-10-era code (TB-025).

- **TB-025** (add-note 404): bug — Frontend ↔ Backend path-contract drift
  (FE POSTs to `/admin/notes`, API expects `/admin/models/{id}/notes`). Categorically
  **misunderstanding of original requirements** (test and FE were wrong-together
  since first write). Init-10-era code path; one-line code + one-line test fix.

- **TB-028** (Users table scroll mismatch): UX consistency — sibling admin
  pages diverged on overflow handling. Categorically **new requirement from
  stakeholder hands-on use** with **research-confirmed pattern** (the
  Invites-page wrapper is industry-standard fluid-table pattern; Users page
  was the outlier).

- **TB-014** (crealitycloud enum gap): backlog hygiene — agent runbook
  references a source host the backend can't disambiguate. Categorically
  **previously-deferred completeness gap**. PG enum extension migration.

- **TB-021** (Story 15.1 unmasked pytest failures): pre-existing test bugs
  exposed by Init 9 Story 15.1's deadlock fix. Two distinct deterministic
  failures: cross-file pollution (test_last_active_middleware) + missing
  admin auth on a default-deny-protected endpoint (test_sot_admin_models).
  Categorically **previously-masked-now-visible test-side bugs**.

- **TB-016 remaining** (agent runbook drift residue): 4 of 17 doc-drifts
  inline-patched during 2026-05-19 Sesja Z retro; 4 remaining are code-side
  (refresh_tokens autogenerate) + low-value cosmetic (Settings field naming).
  Categorically **hygiene closure**.

- **TB-026** (share view enrichment + rate-limiting): genuine epic-sized
  new product surface — anonymous share view currently ships minimum-viable
  STL download button only. 7 sub-items: carousel, STL preview renders
  (iso/front/side/top), 3D viewer (depends on TB-022), full file list,
  description, request-rate cap, throughput cap. Categorically **new
  requirement from stakeholder + security hardening** (DDoS surface).

- **TB-027** (catalog full-res perf): per-DPR srcSet investigation. ModelCard
  currently advertises `${thumbUrl} 1x, ${fullUrl} 2x` — retina displays
  select the 2x candidate = full-resolution original. Categorically **new
  requirement (perf complaint) requiring investigation phase first**.

- **TB-029** (Add Model CTA + modal): UX discoverability gap from Init 10
  Story 16.4 deferral (operator: "raczej nie [moja decyzja] :P"). Categorically
  **new requirement requiring UX session**.

- **TB-022** (Viewer3DInline srcOverride): pre-existing component debt from
  Init 0; only visible after Init 10 Story 16.3 (anonymous share viewer)
  needed the abstraction. Categorically **previously-deferred completeness
  gap with prerequisite role** (Init 12 TB-026 sub-item #3 depends on it).

- **TB-023** (credentialless surface test fixture): Init 10 Story 16.3 needed
  TWO Codex review rounds for full closure (both rounds caught cookie-leak
  bugs). Murat retro proposal: lock down maszynowo. Categorically **new test
  infrastructure to prevent regression class** (cookie leak to /api/share/*
  endpoints).

- **TB-018 #2** (test_hydrate_creates_local_tree DB pollution): Init 5 retro
  carry-forward; FAKE_STL_PAYLOAD_AAA seed leaks into /api/models listing,
  breaks hydrate count expectations. Items #1 and #3 of TB-018 already closed
  via Story 14.1 + 14.3. Categorically **previously-deferred test-isolation
  bug**.

- **TB-024** (BMAD skill template updates): Init 10 retro convergence — two
  meta-skill additions: bmad-create-story checklist gate ("verify against SoT
  + sprint-status for already-shipped endpoints") + architecture-decision
  template (read-path × write-path × {legacy, new} matrix for dual-field
  migrations). Categorically **meta-process improvement** to make the now-codified
  [[feedback_scp_pre_enumeration_phase]] memory enforceable at the skill level.

- **TB-017** (TOTP_FERNET_KEY rotation runbook): trigger date **2027-05-20**
  — 12 months from original Story 7.1 provisioning. Doc-only authoring now,
  scheduled reminder + actual rotation deferred to 2027. Categorically
  **operational continuity reminder**.

### 1.3 Issue triggers — relationship to closed initiatives

| Init | Status | Closed | TB candidates produced |
|------|--------|--------|------------------------|
| Init 6 | done | 2026-05-20 | TB-018 (3 items, 2 closed via 14.1+14.3, #2 remaining) |
| Init 7+8+9 | done | 2026-05-22 morning | — |
| Init 10 | done | 2026-05-22 evening | TB-021, TB-022, TB-023, TB-024, TB-025, TB-026, TB-027, TB-028, TB-029 (operator batch + retro convergence) |

The lopsided distribution (Init 10 produced 9 of the 13 candidates) is
expected: Init 10 was the largest single initiative (13 stories, ~6h
autonomous chain, broad UX + schema-migration + security-hardening surface),
and the operator hands-on review immediately after shipping was thorough.

**Cross-initiative dependency note:** Init 12 TB-026 sub-item #3 (3D viewer
on share view) depends on Init 13 TB-022 (Viewer3DInline srcOverride
extension). Sequence: Init 13 BEFORE Init 12 sub-item #3, OR Init 12 sub-item
#3 deferred to a post-Init-12 follow-up. Recommendation in §3: ship Init 13
first as it has lower scope variance, then Init 12 with TB-026 #3 included.

---

## Section 2 — Epic Impact Analysis

### 2.1 Existing epics — no scope change

Existing epics E1-E17 (Init 0 through Init 10) are **closed**. None require
modification under this SCP. The 13 candidates do not invalidate any
shipped epic.

### 2.2 New epics required

| Epic | Initiative | Title | TB candidates | Stories est. |
|------|-----------|-------|---------------|--------------|
| **E18** | Init 11 | Triage Quick Wins Bundle | TB-025, TB-028, TB-014, TB-021, TB-016 remaining | 5 stories (one per TB, ~30min–1h each) |
| **E19** | Init 12 | Anonymous Share View Enrichment + DDoS Hardening | TB-026 (7 sub-items) | 5-7 stories: schema/job for STL renders, FE carousel+file-list+description, 3D viewer integration (depends Init 13 TB-022), request-rate middleware, throughput-limit middleware/Nginx, threat-model doc |
| **E20** | Init 13 | Catalog UX Uplift | TB-027, TB-029, TB-022 | 3 stories: srcSet perf investigation+fix, Add Model CTA+modal (with UX session), Viewer3DInline srcOverride hook |
| **E21** | Init 14 | Test Infrastructure Hardening | TB-018 #2, TB-023 | 2 stories: hydrate pollution fix (pytest), credentialless fixture (pytest + playwright) |
| **(none)** | Init 15 | Meta — BMAD skills + TOTP runbook | TB-024, TB-017 | Init 15 is meta/deferred; ships as direct skill-file edits + doc authoring, NOT as epic-stories. Logged in sprint-status as `init-15-meta: done` after execution. |

**Init 15 deliberately bypasses epic structure** because (a) it ships
non-code artifacts (BMAD skill checklist files + ops runbook), (b) the verification
target is meta (regression-testing a checklist addition isn't a thing), and (c)
operator-aligned [[feedback_collaboration_division]] — meta-process improvements
are a maintenance class, not a story-cycle class.

### 2.3 Epic sequencing recommendation

```
Phase 0 (DONE 2026-05-23)
  └─ Codex 0.133.0 docs sync + Pro 5x routing memory + CLAUDE.md update

Phase A (start immediately after SCP approval)
  └─ E18 Init 11 Quick Wins Bundle [~5h, low complexity, low risk]
     ├─ Story 18.1 — TB-025 add-note 404 fix (FE path correction + test fix)
     ├─ Story 18.2 — TB-028 Users table overflow-x-auto wrapper
     ├─ Story 18.3 — TB-014 crealitycloud enum + Alembic migration
     ├─ Story 18.4 — TB-021 pytest 2 pre-existing failures fix
     └─ Story 18.5 — TB-016 remaining 4 runbook drifts closure

Phase B (after Phase A; UX session required)
  └─ E20 Init 13 Catalog UX Uplift [~5-8h + UX session]
     ├─ UX session (Sally / bmad-agent-ux-designer) — Add Model placement
     │   + modal-vs-route + srcSet retina policy
     ├─ Story 20.1 — TB-027 catalog srcSet perf investigation+fix
     ├─ Story 20.2 — TB-029 Add Model CTA + modal (admin-only, top-right)
     └─ Story 20.3 — TB-022 Viewer3DInline srcOverride extension (prep for Init 12)

Phase C (after Phase B because depends on TB-022)
  └─ E19 Init 12 Anonymous Share Enrichment + DDoS Hardening [~10-20h]
     ├─ Operator grilling — rate-limit thresholds (req/min + bytes/sec caps)
     │   + sub-item priority (security-hardening MUST > UX uplift)
     ├─ Story 19.1 — Request-rate middleware (priority 1 — security)
     ├─ Story 19.2 — Throughput-limit middleware / Nginx limit_rate (priority 1)
     ├─ Story 19.3 — Threat model doc in architecture.md Init 12 H2
     ├─ Story 19.4 — Share view full file list endpoint extension
     ├─ Story 19.5 — Share view description + carousel FE
     ├─ Story 19.6 — STL preview render job (iso/front/side/top)
     └─ Story 19.7 — 3D viewer integration via Viewer3DInline srcOverride (from TB-022)

Phase D (parallel-able with Phase C — different surface)
  └─ E21 Init 14 Test Infrastructure [~4-6h]
     ├─ Story 21.1 — TB-018 #2 hydrate pollution fix
     └─ Story 21.2 — TB-023 credentialless fixture (pytest + playwright)

Phase E (any time; doc-only)
  └─ Init 15 Meta [~1-2h]
     ├─ TB-024 — bmad-create-story checklist gate + arch-decision template
     └─ TB-017 — TOTP_FERNET_KEY rotation runbook (trigger date 2027-05-20)
```

**Recommendation:** **A → B → (C parallel-able with D) → E**. Phase A first
because (1) it's the shortest path to closing a multi-week ergonomic
irritation (TB-025 ergonomics), (2) all stories are isolated quick-devs
with low coordination cost, and (3) the autonomous chain warms up cheaply
before tackling epic-sized E19. Phase B before C because of the TB-022
dependency for Init 12 sub-item #7. Phase D parallel-able with C because the
test infra surface does not overlap share-endpoint code.

### 2.4 Voice-heavy item grilling — NOT autonomous decisions

Two items in this batch carry **voice-heavy product decisions** per
[[feedback_voice_heavy_dedicated_grilling]] and MUST trigger dedicated
operator-grilling at the point of relevance:

| Item | Voice-heavy decision | Grilling shape | Trigger point |
|------|---------------------|----------------|---------------|
| **TB-029** (Add Model CTA) | (a) Placement: top-right next to filter/sort vs ModuleRail vs floating action button; (b) Modal vs route to existing `/admin/models/new`; (c) Whether to keep direct URL as alternative entry. | Dedicated `AskUserQuestion` with 3-4 calibrating sub-questions OR `bmad-agent-ux-designer` (Sally) session for joint scoping. NOT options-grid. | At start of Story 20.2 (TB-029 dev), after Story 20.1 (perf) lands. |
| **TB-026** (Share enrichment) | (a) Sub-item priority — security-hardening (rate+throughput) vs UX uplift (carousel+renders+viewer) — which ships even if budget runs out mid-init? (b) Rate-limit thresholds — req/min cap + bytes/sec cap numbers; (c) Carousel scope — same as authed catalog detail or simplified? | Dedicated AskUserQuestion with 3-4 sub-questions covering priority + threshold numbers + scope. NOT options-grid. | At start of Init 12 / Story 19.1 (before drafting threat model doc). |

**Phases B-C-D execution stops at these grilling points and waits for
operator input.** Per [[feedback_itcm_autonomous_mode]] this is consistent —
ITCM autonomy applies AFTER product alignment; voice-heavy product decisions
are alignment, not implementation.

---

## Section 3 — Artifact Conflict and Impact Analysis

### 3.1 PRD impact

`_bmad-output/planning-artifacts/prd.md` requires three new H2 sections
appended per established Initiative-N pattern:

- **`## Initiative 11 — Triage Quick Wins Bundle`** — minimal PRD impact;
  bundle of small fixes that don't carry FR/NFR weight. May ship with just
  a top-line acknowledgement section + reference to epics.md E18.
- **`## Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening`**
  — full PRD section with NFR12-DDOS-* (rate-limit + throughput
  thresholds), FR12-SHARE-VIEW-* (carousel, file list, description,
  3D viewer, STL preview renders), NFR12-PERF-* (preview rendering job SLA).
- **`## Initiative 13 — Catalog UX Uplift`** — PRD section with
  FR13-CATALOG-* (Add Model CTA discoverability, srcSet variant policy)
  and possibly NFR13-PERF-1 (catalog list payload size budget).

**Init 14, Init 15 are NOT PRD-impacting** (Init 14 is test infra only;
Init 15 is meta + ops runbook).

Use `bmad-edit-prd` skill to extend `prd.md` for Init 12 and Init 13.
Init 11 PRD section can be drafted directly inline (simpler scope).

### 3.2 Architecture impact

`_bmad-output/planning-artifacts/architecture.md` requires extensions
under new H2 sections:

- **Init 12 Decisions** (anchor for E19):
  - **Decision Q** — Request-rate middleware: where (FastAPI middleware
    vs Nginx vs both), keying (per-token vs per-IP vs per-(token,IP) tuple),
    storage (Redis with `share:ratelimit:` prefix vs in-memory),
    response shape on 429 (Retry-After header).
  - **Decision R** — Throughput-limit: Nginx `limit_rate` for per-stream
    bytes/sec vs app-level streaming throttle vs hybrid. Concurrent
    connection cap per-IP.
  - **Decision S** — STL preview rendering pipeline: render-worker
    extension (workers/render/) producing iso.jpg + front.jpg + side.jpg
    + top.jpg per model, stored as ModelFile rows with new `image_kind`
    enum value `stl_preview`. Triggered by an arq cron OR on-first-share-access.
  - **Decision T** — Share view full file list — endpoint shape
    (`GET /api/share/{token}/files` returning paginated list with
    share-scoped download URLs).
- **Init 13 Decisions** (anchor for E20):
  - **Decision U** — srcSet retina policy: drop `2x` candidate vs
    generate a `@2x` variant blob vs accept the bandwidth cost. Operator
    will weigh in via UX session (Story 20.1 investigation phase).
  - **Decision V** — Add Model entry point: shape + placement
    (modal vs route + top-right vs ModuleRail). UX session output.
- **Init 14 Decisions** (anchor for E21):
  - **Decision W** — Credentialless fixture contract: pytest
    `anonymous_client` fixture shape + Playwright `assertCredentialless`
    helper signature. Applied retroactively to share-router test surfaces.
- **Init 11, Init 15: no architecture impact** (Init 11 is bugfix-bundle;
  Init 15 is meta/runbook).

### 3.3 UI/UX impact

UX session via `bmad-agent-ux-designer` (Sally) or `bmad-create-ux-design`
skill required for **Init 13 only**:
- Add Model CTA placement + visual treatment
- Modal vs route decision + form scope (full /admin/models/new form OR
  quick-add minimum)
- srcSet retina policy visual impact (does dropping `2x` perceptibly
  degrade retina catalog UX?)

**Init 11, Init 12, Init 14, Init 15: no UX design session required.**
Init 12 share-view enrichment is mostly parity-with-authed-detail
(carousel + file list + description match existing patterns); the
STL preview render layout is one-off and can be specified inline in
Story 19.6 spec.

### 3.4 Secondary artifact impact

- **`_bmad-output/implementation-artifacts/sprint-status.yaml`**: extend
  with E18 + E19 + E20 + E21 entries (~20 stories), `init-15-meta`
  bare item, all status `backlog` until promoted to `working`.
- **`_bmad-output/triage-backlog.md`**: each promoted TB switches to
  `Status: promoted` with the destination story ID line. TB-017 stays
  candidate until trigger date 2027-03-20 (12 months from now would
  promote it to a quick-dev).
- **`docs/operations.md`** OR new `docs/totp-fernet-rotation.md`: Init 15
  TB-017 deliverable — multi-key Fernet rotation runbook.
- **`docs/agents-add-model-runbook.md`**: TB-016 remaining drifts (~4
  edits in Story 18.5).
- **`infra/nginx-180/3d-portal.conf`** + mirror in `~/repos/configs/nginx/`:
  Init 12 throughput-limit may require nginx `limit_rate` directive
  addition; needs sync via configs repo per project-context.md rule
  ("edge proxy lives in `~/repos/configs/`").
- **`apps/api/migrations/versions/`**: TB-014 Alembic migration
  (`ALTER TYPE modelsource ADD VALUE 'crealitycloud'` × 2 enums); Init 12
  Decision S may add `ModelFile.image_kind = stl_preview` enum extension.
- **`~/.claude/skills/bmad-create-story/`** OR
  `_bmad/custom/bmad-create-story.toml`: Init 15 TB-024 checklist gate
  addition.
- **`~/.claude/skills/bmad-create-architecture/`** OR custom override:
  Init 15 TB-024 architecture-decision template addition.

---

## Section 4 — Path Forward Evaluation

### 4.1 Option 1 — Direct Adjustment (chosen)

**Viable.** Add new epics E18 + E19 + E20 + E21 + Init 15 meta-bucket;
extend prd.md / architecture.md / epics.md with Initiative 11-13 H2 sections;
populate sprint-status.yaml; execute per phase sequencing in §2.3.

- **Effort**: High (~25-50 h total across 5 inits, multi-session execution
  expected with sleep-through-reset per [[feedback_autonomous_sleep_on_budget]]).
- **Risk**: Low-medium. Each individual story is well-scoped; the only
  cross-init dependency (Init 13 TB-022 → Init 12 sub-item #3) is explicit
  in §2.3 phase ordering. Voice-heavy grilling points are explicit (§2.4)
  and won't get silently skipped.

### 4.2 Option 2 — Potential Rollback

**Not viable.** No completed work to revert. All 13 candidates are
forward-looking additions / fixes; nothing in the current shipped state
needs undoing.

### 4.3 Option 3 — PRD MVP Review (scope reduction)

**Not viable** as primary path, but **partial application within Init 12**:
TB-026 sub-item priority will be operator-graded — if budget runs out
mid-init, security hardening (rate+throughput) MUST ship; UX uplift
(carousel + STL preview renders + 3D viewer) MAY defer. This is in-init
scoping, not whole-SCP scope reduction.

### 4.4 Selected approach

**Option 1 (Direct Adjustment) — 5 new initiatives, 4 new epics + 1 meta-bucket,
phase-sequenced A→B→C∥D→E execution under ITCM autonomous mode**.

Justification:
- Operator pre-approved this clustering shape (Option 1 in
  AskUserQuestion 2026-05-23).
- Each TB candidate has pre-enumeration done (smoking guns, code maps,
  scope estimates) — promotion-to-story is straightforward.
- Voice-heavy items have explicit grilling triggers (§2.4), not
  silently rolled into autonomous flow.
- Phase sequencing respects the one cross-init dependency
  (Init 13 TB-022 before Init 12 sub-item #3).
- Token budget allows ITCM autonomous chain with sleep-through-reset
  fallbacks.

---

## Section 5 — Detailed Change Proposals

### 5.1 Initiative 11 — Triage Quick Wins Bundle (E18)

**Story 18.1 — TB-025 add-note 404 fix**

OLD:
```ts
// apps/web/src/modules/catalog/hooks/mutations/useCreateNote.ts:17
api<NoteRead>(
  "/admin/notes",
  { method: "POST", body: JSON.stringify(input) },
)
```

NEW:
```ts
api<NoteRead>(
  `/admin/models/${input.model_id}/notes`,
  { method: "POST", body: JSON.stringify(input) },
)
```

Plus matching test updates in `useCreateNote.test.tsx:28` and
`AddNoteSheet.test.tsx:65` (expected URL string). API contract verification:
backend `admin_router.py:871` accepts model_id from path; verify request
body shape doesn't require `model_id` field (likely safe to drop from body
since path carries it, but verify with admin_router signature).

Rationale: FE↔BE path contract drift; HAR-confirmed 404. Pinned root cause
in TB-025 write-up.

---

**Story 18.2 — TB-028 Users table overflow-x-auto wrapper**

OLD (UsersPage.tsx:360):
```tsx
<table className="w-full text-sm">
```

NEW:
```tsx
<div className="rounded border border-border overflow-x-auto">
  <table className="w-full text-sm">
    ...
  </table>
</div>
```

Mirrors `InvitesPage.tsx:228` pattern. Visual baseline regeneration likely
needed (admin-users-empty + admin-users-populated specs); verify the diff
intentionally per [[feedback_frontend_visual_verification]].

Rationale: cross-page consistency; operator preference unambiguous.

---

**Story 18.3 — TB-014 crealitycloud enum + Alembic migration**

Add `crealitycloud = "crealitycloud"` to both `ModelSource` and
`ExternalSource` StrEnums in `apps/api/app/core/db/models/_enums.py`.
New Alembic migration `0012_add_crealitycloud_enum.py`:
```py
# Non-transactional ALTER TYPE for PG ≤ 11; chains after 0011_index_ext_link_url
def upgrade():
    op.execute("ALTER TYPE modelsource ADD VALUE IF NOT EXISTS 'crealitycloud'")
    op.execute("ALTER TYPE externalsource ADD VALUE IF NOT EXISTS 'crealitycloud'")
```
Plus runbook update: `docs/agents-add-model-runbook.md` source-detection
table — drop the "(workaround)" caveat for crealitycloud.com.

Rationale: agent runbook references a source host the backend can't
disambiguate; small migration; closes a long-standing completeness gap.

---

**Story 18.4 — TB-021 pytest 2 pre-existing failures fix**

**Failure A — `test_redis_down_passes_through_with_warning` cross-file
pollution**: investigation phase first (~30 min) to identify which
earlier-running test file leaks state. Hypothesis bag (in order of
likelihood): autouse fixture from another file mutates a session-scoped
resource, OR caplog interaction with logger reconfiguration. Fix shape:
either add per-test isolation explicitly OR document the offender's
fixture scope mismatch and patch upstream.

**Failure B — `test_list_files_returns_image_kinds_in_position_order`
401 Unauthorized**: test uses unauthenticated `client` fixture; endpoint
requires admin since Init 6 NFR6-SEC-1 default-deny. Fix: switch to
admin-authed client fixture (mirror what other admin tests use). One-line
fix once the right fixture is identified.

Rationale: closes the carry-forward 401 + cross-file pollution unmasked
by Init 9 Story 15.1.

---

**Story 18.5 — TB-016 remaining 4 runbook drifts closure**

Patch the 4 remaining doc-drifts from the 17-item external-LLM feedback
(13 inline-patched 2026-05-19 Sesja Z). The 4 remaining are code-side
(refresh_tokens autogenerate) + low-value cosmetic (Settings field naming);
final scope confirmed during story prep against TB-016 detailed item-list.

Rationale: closes a hygiene candidate; small effort.

---

### 5.2 Initiative 12 — Anonymous Share View Enrichment + DDoS Hardening (E19)

**Pre-condition**: Operator-grilling on (a) sub-item priority, (b) rate-limit
thresholds, (c) carousel scope. Per §2.4 dedicated AskUserQuestion before
Story 19.1 spec draft.

**Story 19.1 — Request-rate middleware (priority 1, security)**

FastAPI middleware OR Nginx `limit_req_zone` for `/api/share/{token}/*`.
Decision Q in architecture.md Init 12 H2. Per-token-IP keying preferred
(per-token alone is too coarse — one user's link, many recipients —
while per-IP alone is too narrow — single recipient legitimate use).
Threshold from operator grilling (default starter: 60 req/min per
(token, IP) tuple; revisit numbers in PRD).

**Story 19.2 — Throughput-limit middleware / Nginx limit_rate**

Nginx `limit_rate` per-stream bytes/sec on `/api/share/{token}/files/*`
(downloads). Plus concurrent-connection cap per IP via
`limit_conn_zone` + `limit_conn`. Sync edge config via
`~/repos/configs/nginx/` per project-context rule. Decision R in
architecture.md.

**Story 19.3 — Threat model doc**

`architecture.md` Init 12 H2 section "§ Threat vectors enumerated" per
[[feedback_security_vector_enumeration]] — list cookie-sending vectors,
auth-state-consultation points, browser-default-credentials behaviors,
SPA reactivity gotchas. Specific to share-anon surface.

**Story 19.4 — Share view full file list endpoint**

`GET /api/share/{token}/files` returning paginated list of files for the
shared model with share-scoped download URLs (Init 6 Decision N pattern).
SoT model exposure for share context; admin permissions NOT consulted
(share token IS the auth).

**Story 19.5 — Share view description + carousel FE**

Bilingual description per Init 10 Decision L (body_pl + body_en).
Carousel parity with authenticated catalog detail (`ModelGallery.tsx`
style). Uses share-scoped image URLs.

**Story 19.6 — STL preview render job (iso/front/side/top)**

New render-worker task in `workers/render/`: input ModelFile (stl kind),
output 4 ModelFile rows with `image_kind = stl_preview` (new enum value;
Alembic migration). Renders via existing trimesh + matplotlib stack;
lazy-on-first-share-access OR proactively via arq cron (operator decides
during story spec).

**Story 19.7 — 3D viewer integration on share view**

Depends on TB-022 (Viewer3DInline srcOverride shipped in Story 20.3
during Phase B). Replace static download button with embedded inline
viewer; STL URL from share-scoped endpoint.

---

### 5.3 Initiative 13 — Catalog UX Uplift (E20)

**Pre-condition**: UX session with Sally (`bmad-agent-ux-designer` or
`bmad-create-ux-design`) covering Add Model placement + modal-vs-route +
srcSet retina policy.

**Story 20.1 — TB-027 catalog srcSet perf investigation+fix**

Investigation phase (~30 min) per [[feedback_scp_pre_enumeration_phase]]:
open browser devtools network tab on catalog list, sample 5-10 cards, check
actual served URL + Content-Length per response. Three hypotheses:
- (1) srcSet 2x design intent was correct, perf complaint reframes trade-off
- (2) Variant file missing for older models (backend `?variant=thumb`
  silently falls back to original)
- (3) CardCarousel gallery images use full-res non-primary slides

Fix shape depends on hypothesis. Decision U in architecture.md Init 13 H2.

**Story 20.2 — TB-029 Add Model CTA + modal**

Voice-heavy grilling first (§2.4). Then `AddModelButton` component in
catalog top-right toolbar, role-gated to admin. Either modal embedding
the `/admin/models/new` form (refactor needed) OR route-to-existing-page
(simpler). i18n keys, visual baselines, role-gated tests.

**Story 20.3 — TB-022 Viewer3DInline srcOverride extension**

Add optional `srcOverride: string | null` field to `StlFile` type at
`apps/web/src/modules/catalog/components/viewer3d/types.ts:3-8`. When
set, Viewer3DInline + Viewer3DModal + parseStl worker + stlCache use
`srcOverride` instead of the default `/api/models/{modelId}/files/{fileId}/content`
URL builder. Prepares Init 12 sub-item #7 (3D viewer on share view).

---

### 5.4 Initiative 14 — Test Infrastructure Hardening (E21)

**Story 21.1 — TB-018 #2 hydrate pollution fix**

`test_sot_model_file_content.py::FAKE_STL_PAYLOAD_AAA` seeds a row that
leaks into `/api/models` listing read by `test_hydrate_creates_local_tree`.
Investigation: identify the leak shape (missing rollback, session-scoped
fixture that should be function-scoped, OR explicit cleanup gap). Fix:
either change fixture scope OR add explicit teardown.

**Story 21.2 — TB-023 credentialless fixture**

Three artifacts (~50-100 LOC total):
1. pytest `anonymous_client` fixture in `apps/api/tests/conftest.py` (no
   cookies, no auth headers, assertion helper
   `assert_no_set_cookie_in_response`)
2. Apply parameterized assertion class to `tests/test_share_public.py` +
   `tests/test_share_admin.py` (read paths only)
3. Playwright `assertCredentialless(page)` helper in
   `apps/web/tests/visual/_test.ts`; apply to share-anon spec.

Decision W in architecture.md Init 14 H2.

---

### 5.5 Initiative 15 — Meta + Deferred

**TB-024 — BMAD skill template updates**

Two checklist additions:
1. **bmad-create-story** — add "Verify against SoT + sprint-status for
   already-shipped endpoints" gate before SCP `## H2` writing step.
   Ships as direct edit to `~/.claude/skills/bmad-create-story/checklist.md`
   OR project-local override in `_bmad/custom/bmad-create-story.toml`
   (operator chooses at promotion).
2. **bmad-create-architecture** (or equivalent skill producing arch
   decisions) — add architecture-decision template requiring
   read-path × write-path × {legacy, new} = 4-cell matrix for every
   schema migration with dual-field shape (e.g. body_pl + body_en).

Verification: meta — apply on first SCP of next initiative + monitor
whether the gate fires the kind of issue Init 10 surfaced mid-story.

**TB-017 — TOTP_FERNET_KEY rotation runbook**

Draft `docs/totp-fernet-rotation.md` (or extend `docs/operations.md`)
with multi-key MultiFernet shape + 4-step rotation sequence
(provision new key → restart with [new, old] → re-encrypt loop over
users table → drop old key from env). Plus calendar/cron reminder
at 2027-05-20 (12 months from Story 7.1 original Fernet provisioning).

---

## Section 6 — Implementation Handoff

### 6.1 Scope classification

**Major** — 5 new initiatives, 4 new epics, ~20-25 stories total, multi-day
ITCM autonomous execution expected.

### 6.2 Handoff plan

| Init | Recipient | Mode | Deliverables |
|------|-----------|------|--------------|
| Init 11 (E18) | Claude (ITCM autonomous) | bmad-create-story → bmad-dev-story → bmad-code-review (Codex `gpt-5.4-mini` for routine reviews) → bmad-retrospective at epic close | 5 stories shipped, sprint-status updates, deploy via `infra/scripts/deploy.sh` after each merge |
| Init 12 (E19) | Claude (ITCM autonomous AFTER operator-grilling) | PRD extend → architecture.md extend → bmad-create-epics-and-stories → sprint-planning → story cycles per phase | 5-7 stories shipped, threat-model doc, NFR12-DDOS-* compliance, nginx config sync |
| Init 13 (E20) | Claude (ITCM autonomous AFTER UX session) | UX session via bmad-agent-ux-designer → architecture.md Decision U+V → bmad-create-story per | 3 stories shipped + UX design artifact |
| Init 14 (E21) | Claude (ITCM autonomous) | bmad-create-story per | 2 stories shipped, no PRD impact |
| Init 15 | Claude (direct edits, no story cycle) | Direct edit of skill files + runbook authoring | Skill checklist updates committed; rotation runbook landed in docs/ |

### 6.3 Success criteria

- **Init 11**: 5 stories closed (all 5 TBs marked `Status: promoted` →
  `Status: done` in triage-backlog); 5/5 stories Codex-CLEAN;
  full deploy chain PASS after each merge.
- **Init 12**: NFR12-DDOS-* compliance verified (request-rate cap + throughput
  cap working under synthetic load); 3D viewer working on /share/<token>
  route (anonymous + authenticated parity); TB-026 marked done.
- **Init 13**: srcSet retina policy decision documented in architecture.md
  Decision U; Add Model CTA visible to admin (operator visual verification
  via agent-browser); Viewer3DInline srcOverride extension shipped (prep
  for Init 12 sub-item #7).
- **Init 14**: full pytest suite green deterministically 3× consecutive;
  credentialless assertions firing on share-anon test surface (every
  /api/share/<token>/* endpoint exercise asserts no Set-Cookie).
- **Init 15**: TB-024 skill files updated; TB-017 runbook landed + calendar
  reminder set.

### 6.4 Retro touchpoints

Per-initiative retros (`bmad-retrospective`) at each epic close (E18, E19,
E20, E21). Init 15 (meta) skips retro because it's not an epic. Aggregate
retro across Init 11-15 cluster ONLY if cross-init lessons emerge
worth codifying as memory (otherwise per-init retros suffice).

---

## Section 7 — Approval Gate

**Operator approval required to proceed**. Approval shape:
- Explicit "ok, lecimy" / "approve" / "go" via conversational reply.
- Implicit-by-silence is **NOT** sufficient for SCP approval; per
  [[feedback_default_to_bmad_workflow]] BMAD vanilla-first requires
  explicit alignment.

Once approved, this SCP becomes the **execution contract** for Init 11-15.
Voice-heavy grilling points (Init 12 priority + thresholds; Init 13 UX
session) WILL pause execution at the relevant story trigger, but the
SCP scope is locked at approval.

**Modifications post-approval require this SCP to be amended** — not
silently re-scoped during execution. Per [[feedback_default_to_bmad_workflow]]
multi-PR batches are epics in disguise; that applies to this SCP-defined
batch too.
