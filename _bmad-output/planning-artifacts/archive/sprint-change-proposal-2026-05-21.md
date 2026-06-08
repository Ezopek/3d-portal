---
title: "Sprint Change Proposal — Initiatives 7 + 8 + 9 (Account & Admin UX Polish + Catalog Mobile & Image Performance + Test Isolation Cleanup)"
type: sprint-change-proposal
initiative_scope: [7, 8, 9]
status: shipped
shipped_at: 2026-05-22
shipped_via: |
  TB-015 quick-dev + 10 stories across 3 epics shipped autonomously in single chained session 2026-05-21→2026-05-22:
  - TB-015 (Wyczyść pomiary footer pointer-events): e59abe5
  - Epic E14 Init 9 (Test Isolation Cleanup): 14.1 (1d5f7a8 + f42f5cf P2 fix-up) + 14.2 (fa4a628) + 14.3 (313dd33)
  - Epic E12 Init 7 (Account & Admin UX Polish): 12.1 (9ce0463 + f1ef465 P2 fix-up) + 12.2 (db8d892) + 12.3 (e9525a9) + 12.4 (1c49039) + 12.5 (184e39e + 7f09a42 P2+P3 fix-up)
  - Epic E13 Init 8 (Catalog Mobile & Image Performance): 13.1 (0611e6d) + 13.2 (aa6a8eb)
  Total: 14 commits, 11 distinct deliverables, 4 Codex fix-up loops closed (f42f5cf, f1ef465, 7f09a42, plus one more for 12.5).
  Codex reviews: 12.1 P2 → fix-up f1ef465 → CLEAN; 12.2 CLEAN; 12.3 CLEAN; 12.4 CLEAN; 12.5 P2+P3 → fix-up 7f09a42 → CLEAN; 13.1 review log incomplete but effectively-clean (4-line CSS + comprehensive automated + agent-browser verification); 13.2 awaits.
  Operator directive "lecimy do końca jak init 5" honored — no operator-handshake pauses, autonomous chain executed through 2026-05-21→2026-05-22 boundary. NFR7-UX-1 + NFR8-UX-1 agent-browser visual verifications PASS on all 7 UI stories. NFR8-PERF-1 thumbnail size measured 9-14 KB across phone-photo fixture set (well under 50 KB budget).
  TB-018 all 3 carry-forward test-isolation items CLOSED via Initiative 9.
  Operator retros (epic-12, epic-13, epic-14) deferred — operator-triggered next session.
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-21
approved_by: Ezop
approved_at: 2026-05-21
approved_via: one-word Polish "approve" response after rev. 1 SCP surfaced (rev. 0 → rev. 1 mid-review revision per operator scope-pull adding Initiative 9 / TB-018 promotion)
execution_directive: "lecimy do końca jak init 5" — no operator-handshake pauses; autonomous chain across sessions until SCP shipped. Hard-stop only on 5h ≥ 80% (sleep through reset per [[feedback_autonomous_sleep_on_budget]]) or real product blocker. No extra_usage opt-in.
mode: batch-presented (operator-pragmatic variant of BMAD Incremental — full draft surfaced once, operator feedback consolidated; matches Init 6 SCP precedent)
change_scope_classification: moderate
related_artifacts:
  - _bmad-output/triage-backlog.md                              # TB-015 (#3 promoted via quick-dev) + TB-018 (3 test issues promoted via Initiative 9 per operator scope-pull 2026-05-21)
  - _bmad-output/planning-artifacts/prd.md                      # to be extended (Initiative 7 + Initiative 8 + Initiative 9 sections)
  - _bmad-output/planning-artifacts/architecture.md             # to be extended (Initiative 7 + Initiative 8 sections; Init 9 architecture section minimal — test-infrastructure only, no product-architecture impact)
  - _bmad-output/planning-artifacts/epics.md                    # to be extended (Initiative 7 H2 + Initiative 8 H2 + Initiative 9 H2 + ~10 stories total)
  - _bmad-output/implementation-artifacts/sprint-status.yaml    # to be extended (E12 + E13 + E14 entries, all status backlog)
  - sprint-change-proposal-2026-05-20-post-cutover-auth.md      # predecessor SCP (Init 6); this SCP follows the same Initiative-N H2-append pattern
  - ~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_frontend_visual_verification.md  # new memory 2026-05-21 — codifies visual-verification gate baked into AC for all UI stories in this SCP
supersedes: none
superseded_by: none
predecessor_initiative: 6
trigger:
  source: operator hands-on batch report 2026-05-21 (~17:00 UTC, immediately after Init 6 close-out commit 05a2f1a) + operator scope-pull 2026-05-21 (TB-018 from "future dedicated CC session" → "include in this batch — test debt actively blocks Init 7 stories")
  shape: 9 user-reported items (mix bug / enhancement / feature-gap / UX-discoverability) + 3 pre-existing test-isolation issues (promoted to Initiative 9 per operator scope-pull, originally parked in TB-018 for future session)
  evidence_class: direct operator observation, no automated-gate finding, no security audit
---

# Sprint Change Proposal — Initiatives 7 + 8 + 9 (Account & Admin UX Polish + Catalog Mobile & Image Performance + Test Isolation Cleanup)

## Section 1 — Issue Summary

### 1.1 Problem statement

Initiative 6 structurally closed on 2026-05-21 with all seven Stories 11.1–11.7 shipped, cutover-smoke Scenario 5 (external-anonymous probe) PASS, and default-deny portal-self-auth verified. Within hours of Init 6 retro close (commit `05a2f1a`), the operator surfaced a batch of nine user-experience issues discovered through hands-on use of the running portal at `https://3d.ezop.ddns.net`:

- **One regression bug** — TB-015 "Wyczyść pomiary" 3D viewer footer button is unclickable (`pointer-events-none` on parent wrapper swallows footer click; per-row × works because rows individually re-enable pointer events).
- **Five UX-polish items** — admin Users panel needs default-hide for inactive accounts with reveal-toggle (#2); admin Invites tab is grayed-out in nav despite admin role, missing Polish translations, table overflows viewport with huge wasted left margin (#5); registration auto-derives display name from email prefix with no user choice (#6); 2FA enrollment feature exists at `/settings/2fa` but has no nav discoverability path (#7); `/settings/sessions` lists individual API/curl probe sessions cluttering the active-session view with no pagination/sort/filter (#4).
- **Two catalog visual-quality items** — catalog cards serve full-resolution phone photos (8K+) over mobile data with no thumbnail pipeline (#8); mobile catalog carousel has no prev/next arrows because the `opacity-0 group-hover:opacity-100` pattern doesn't fire on touch devices (#9).
- **Three pre-existing test-isolation issues** (operator-grouped, originally parked in TB-018, **promoted into this SCP's scope as Initiative 9 per operator scope-pull 2026-05-21**) — 18 vitest failures in `modules/admin/*` test files (text/role/label finder mismatches predating Init 6); `test_hydrate_creates_local_tree` DB-state pollution from `test_sot_model_file_content.py::FAKE_STL_PAYLOAD_AAA` leaking into `/api/models` listing; visual-regression hook-context flake on admin-invites + admin-users baselines (standalone PASS / check-all.sh hook context FAIL). The pull-forward is technically motivated, not just preference-driven: the three issues actively interfere with Initiative 7 stories — Stories 12.1 (admin invites unblock) and 12.2 (admin users inactive-filter) modify EXACTLY the components whose test files are red (`InvitesPage.test.tsx`, `UsersPage.test.tsx`, etc.) AND whose visual-regression baselines hit the hook-context flake on `check-all.sh`; without prior cleanup, both stories develop on unreliable test signal (pre-existing failures mask new regressions; hook-flake baselines can't distinguish real visual deltas from infrastructure noise). The hydrate DB-pollution affects Stories 12.3 (display name → `User` model touch), 12.5 (sessions endpoint extensions), and 13.2 (`ModelFile` thumbnail pipeline) test surfaces less directly but shares the same `apps/api/tests/conftest.py` isolation contract. **ITCM decision (2026-05-21):** promote TB-018 to dedicated **Initiative 9 (Epic E14)** scheduled FIRST in the execution chain before E12 (Init 7) and E13 (Init 8) — see §3.2.3 bundling rationale.

The batch additionally carried a single high-signal **meta-feedback** from the operator: Initiative 6 shipped the admin Invites page (and its supporting nav surface) without any human-or-agent visual-verification pass — the three independent UX defects in #5 (gray nav tab, untranslated keys, viewport overflow) ALL passed type-check + lint + vitest unit tests + the production build pipeline + Codex pre-merge auth-boundary review, and ALL would have been caught by 30 seconds of any sentient observer loading the page in a browser. This is the same defect class as the Init 5 SCP § 3.4 "auth-boundary contract audit before drafting" pattern (memory [[auth-boundary-contract-audit]]), but applied to frontend UX: automated gates verify *correctness*, not *observable quality*. The fix is procedural — a new mandatory acceptance-criteria pattern requiring agent-browser (or Playwright fallback) visual verification before code-review for any UI-touching story. The fix has been codified as memory [[feedback_frontend_visual_verification]] (saved 2026-05-21 in this same session, before SCP drafting) and is baked into the AC contract of every UI story proposed below.

### 1.2 Issue categorization

Per CC checklist §1.2: **Mixed categorization — predominantly New requirements emerged from stakeholder hands-on use, with a single failed-approach element.**

- Items #2, #4, #6, #8, #9 are **new requirements from stakeholder** — operator surfaced UX gaps that were never in Init 1–6 PRD scope. The portal v1 (Init 0) shipped with minimum-viable surfaces in admin/users, registration, sessions, catalog-card images, and catalog-carousel — these surfaces are now being raised from minimum-viable to operator-acceptable.
- Item #3 (TB-015 "Wyczyść pomiary") is a **previously-identified bug from operator hands-on use 2026-05-17** (per existing triage-backlog entry). Promotion-class, not new-discovery.
- Item #5 (admin Invites) is **misunderstanding of original requirements** mixed with **failed approach** — the nav surface was shipped intentionally disabled with `aria-disabled="true"` as a placeholder in Initiative 5 Epic 8 (admin invites), but no follow-up story re-enabled it; the missing translations and viewport-overflow are post-shipping polish gaps that were tolerated by automated gates.
- Item #7 (2FA discoverability) is **misunderstanding of original requirements** — Init 5 Epic 7 shipped TOTP 2FA enrollment as a complete flow (frontend + 5 backend endpoints) but routed it only at `/settings/2fa` direct URL, with no settings-hub landing page and no nav link from any other surface. The feature exists, the navigation does not.
- The three test-isolation items originally in TB-018 are **previously-identified pre-existing issues from earlier sprints** — categorically a **mix of misunderstanding of original requirements** (test fixtures whose isolation contract didn't withstand later additions) **+ failed approach requiring different solution** (the existing `apps/api/tests/conftest.py` + `apps/web/tests/visual/check-all.sh` patterns don't fully isolate state across test boundaries). **Originally parked for future CC session, promoted to Initiative 9 in this SCP per operator scope-pull 2026-05-21** (rationale in §1.1 above + §3.2.3 below).

### 1.3 Issue triggers — relationship to closed initiatives

- **Init 0 (Product Foundation)** — items #8, #9 touch the catalog read-surface that shipped in E0.4 (Catalog Read Surface). Both are post-MVP polish, not regression of E0.4 acceptance.
- **Init 5 (Public Registration & User Account Management)** — items #2, #5, #6, #7 touch surfaces shipped in E6 (member role + invite-based registration), E7 (TOTP 2FA), E8 (Admin panel: users + invites). Item #5's disabled-nav-tab placeholder is the only one tracing to a known Init 5 follow-up gap; the others are new polish requirements on shipped surfaces.
- **Init 6 (Post-Cutover Default-Deny Auth Posture)** — no items in this batch touch Init 6 surfaces. The meta-feedback about visual verification was provoked by Init 6's admin Invites shipping with the three UX defects in #5, but the fix is procedural (new AC pattern for future stories), not a retroactive Init 6 modification.
- **TB-015** — direct operator observation 2026-05-17 + 2026-05-21 re-surfacing. Root cause pinned in this session's recon: `pointer-events-none` on `Viewer3DModal.tsx:390` wrapper. One-line fix candidate.
- **TB-018 → Initiative 9 (E14)** — three pre-existing test-isolation issues that have lingered through Init 5 + 6 close-outs without dedicated remediation. Initiative 5 retro item #8 flagged the `test_hydrate_creates_local_tree` pollution; the 18 admin vitest failures and the visual-regression hook-context flake are observed across multiple sprint sessions (≥3 sessions historically, exceeding the [[feedback_preexisting_issue_threshold]] threshold for promotion candidacy). **Promoted in this SCP** because their test surfaces (admin module vitest + admin visual baselines + `User`/`ModelFile` pytest fixtures) coincide exactly with Initiative 7 Stories 12.1, 12.2, 12.3, 12.5 + Initiative 8 Story 13.2 — leaving them parked would force the new stories to develop on unreliable test signal, undermining the very visual-verification gate (NFR7-UX-1 / NFR8-UX-1) this SCP introduces.

### 1.4 Evidence

All inputs are confirmed present and cross-referenced:

- **Operator batch report:** in-session user message 2026-05-21 ~17:00 UTC, verbatim 9-item list with operator's own framing for each ("powinniśmy defaultowo ukrywać nieaktywne konta", "do zastanowienia czy to OK", "zostawiam do decyzji ITCMowi", "trochę bije mnie to, że zakładka zaproszeń nie była odpowiednio przetestowana"). Stored in conversation transcript.
- **Pre-session technical recon** (Explore subagent dispatched 2026-05-21 before SCP drafting):
  - Item #3 root cause: `apps/web/src/modules/catalog/components/viewer3d/Viewer3DModal.tsx:390` wrapper has `pointer-events-none`; `MeasureSummary.tsx:83-86` "Wyczyść pomiary" button in footer is not in the `pointer-events-auto` row-override.
  - Item #5 nav-disable: `apps/web/src/modules/admin/AdminTabs.tsx:31-44` renders invites tab as `<span aria-disabled="true">` (hardcoded), not as a `<Link>`.
  - Item #5 i18n: ~20 keys missing from `apps/web/src/locales/pl.json` + `en.json` (e.g. `admin.invites.title`, `admin.invites.column_role`, etc.).
  - Item #5 viewport: admin layout left-margin (Init 5 admin module layout) wastes horizontal space; table contents overflow viewport with no horizontal scroll.
  - Item #7 feature presence: `apps/web/src/routes/settings/2fa.tsx` + `apps/web/src/modules/auth/Settings2faPage.tsx` + 5 backend endpoints (`/api/auth/2fa/{enroll,enroll/confirm,disable,status,recovery-codes/regenerate}`) all exist and work. Routes/settings/ contains only `2fa.tsx` and `sessions.tsx` — no `_layout.tsx`, no `index.tsx`, no settings hub.
  - Item #8 pipeline absence: `apps/api/app/modules/sot/router.py:189-222` `GET /api/models/{model_id}/files/{file_id}/content` streams raw file bytes from disk. No thumbnail generation in upload path (`apps/api/app/modules/admin/router.py` model-file create endpoints), no Pillow integration. Frontend `apps/web/src/modules/catalog/components/ModelGallery.tsx:12-14` requests via `srcFor(modelId, fileId)` → full file.
  - Item #9 carousel arrows: `apps/web/src/ui/custom/CardCarousel.tsx:151-170` arrow buttons use `opacity-0 group-hover:opacity-100`; same pattern in `ModelGallery.tsx:86-105`. No `sm:` breakpoint conditional.
  - Item #2 inactive users filter absence: `apps/web/src/modules/admin/UsersPage.tsx:92-98` query accepts `search` param but no `is_active` filter; users-list returns all rows regardless of status.
  - Item #4 sessions list shape: `apps/api/app/modules/auth/router.py:371-406` groups RefreshToken rows by `family_id` and returns one entry per family with `user_agent` + `ip`. Each new login = new family = new entry. Curl probes that complete a login flow create real sessions. Endpoint already accepts pagination params (offset/limit) per L351-368 but frontend `apps/web/src/routes/settings/sessions.tsx:14-106` doesn't wire them.
- **Triage backlog state:**
  - **TB-015** (Wyczyść pomiary) — existing entry from 2026-05-17, updated 2026-05-21 with pinned root cause (this session). Status: candidate, awaiting promotion to `bmad-quick-dev` per §3.4 execution flow.
  - **TB-018** (3 test-isolation issues bundle) — new entry created 2026-05-21 in this session. **Status flips to `promoted` on SCP approval**; promotion vehicle = Initiative 9 (E14) in THIS SCP, per operator scope-pull. Originally framed as "future dedicated CC session" parking; revised mid-SCP-review to in-batch promotion (this revision visible in this very file's git history).
- **Operator business alignment** (asked + answered in this same session, 2026-05-21):
  - Display name strategy (#6): **option A — optional field on registration form with auto-suggest from email prefix, editable in settings post-registration.** Operator-selected.
  - Other items: operator delegated technical decisions to ITCM per memory [[itcm-autonomous-mode]] (effective 2026-05-19 forward) — no further business questions.
- **Memory inputs:**
  - [[itcm-autonomous-mode]] — frame for SCP-then-execute autonomous chain.
  - [[feedback_default_to_bmad_workflow]] — first-action routing through BMAD (this SCP).
  - [[feedback_vanilla_bmad_first]] — bmad-correct-course as canonical entry for post-ship scope change.
  - [[feedback_bmad_skill_discovery_checklist]] — session-start bmad-help (executed at start of this session).
  - [[feedback_preexisting_issue_threshold]] — TB-018 bundle is operator-direct surfacing, not threshold-derived auto-stub.
  - [[feedback_frontend_visual_verification]] — new memory saved 2026-05-21 this session, codifies AC pattern baked into every UI story below.
  - [[feedback_auto_deploy_dev]] — every code-merge to main fires `deploy.sh` (doc-only commits skipped).
  - [[feedback_invoke_codex_directly]] + [[feedback_codex_review_invocation]] + [[feedback_codex_review_mental_model]] — code-review on each story uses Codex directly.

Halt-conditions per CC checklist §1: trigger clear ✓, evidence sufficient ✓.

### 1.5 Production state at SCP creation time (2026-05-21)

| Surface | Init 6 close state (2026-05-21) | Initiative 7 + 8 target |
|---|---|---|
| `/admin/invites` (nav tab) | grayed out (`<span aria-disabled>` placeholder) | enabled `<Link>` for admin role |
| `/admin/invites` (page i18n) | ~20 raw i18n keys rendered as literal text | full pl/en translation parity per existing admin module convention |
| `/admin/invites` (table layout) | overflows viewport, huge left margin | fits viewport at desktop default + admin mobile (≤414px); left-margin compressed |
| `/admin/users` (default filter) | shows all users incl. inactive | hides inactive by default; checkbox "Pokaż nieaktywne konta" reveals |
| Registration form | display name auto-derived from email prefix, no field | optional display-name field with auto-suggest, post-registration edit at `/settings/profile` |
| `/settings` (hub) | does not exist (404) | hub page lists Profile + 2FA + Sessions with i18n labels |
| `/settings/2fa` discoverability | only direct URL | nav link from `/settings` hub + user-menu in header |
| `/settings/sessions` (UX) | unbounded list incl. curl probes, no pagination/sort/filter | pagination (20/page), sort by last_used_at desc default, checkbox "Pokaż API/non-browser sesje" OFF by default (UA-pattern filter) |
| Catalog cards (image source) | full-resolution original (8K+ phone photos) | scaled thumbnail (800px longest side WebP @ q80) via query-param variant; full-res preserved for detail view |
| Catalog cards (mobile carousel) | arrows invisible on touch (`opacity-0 group-hover`) | arrows visible on mobile (`sm:opacity-0 sm:group-hover`); desktop unchanged |
| 3D viewer "Wyczyść pomiary" | unclickable (pointer-events-none on wrapper) | clickable; clears all measurements |
| Vitest admin module test suite | 18 failures (text/role/label finder mismatches predating Init 6) | 0 failures; finders aligned with current i18n + DOM shape (Story 14.1) |
| `test_hydrate_creates_local_tree` (pytest) | flaky — fails when run after `test_sot_model_file_content` due to FAKE_STL_PAYLOAD_AAA seed leak | deterministic; conftest isolation closed (Story 14.2) |
| Visual-regression hook-context (`check-all.sh`) | admin-invites + admin-users baselines FAIL via hook, PASS standalone (port/cache/build collision) | parity: hook context produces same verdict as standalone for ALL baselines (Story 14.3) |

### 1.6 Non-trigger surfaces explicitly out of scope

- **Init 0–6 auth/security posture** — untouched. NFR6-SEC-1 audit gate stays valid through this SCP's stories.
- **Catalog data integrity** — soft-delete patterns, Alembic migration discipline, `portal-content` → `portal-state` separation — untouched.
- **Render pipeline** — no changes to STL render worker or 4-view materializer.
- **Observability** — no new audit events except those incidentally emitted by the thumbnail pipeline upload path (standard `model.file.created` already covered).
- **Edge proxy / nginx** — no edge config changes; thumbnail variants ride the same `/api/models/...` prefix.
- ~~**TB-018 carry-forward** — deferred to a dedicated future CC session, NOT executed in this batch.~~ **Revised mid-SCP-review 2026-05-21**: TB-018 is now in scope as Initiative 9 (E14), see §3.2.3 + §4.1.3 + §4.2.3 + §4.3.3 + §4.4.

---

## Section 2 — Impact Analysis

### 2.1 Epic impact

| Epic state | Count | Detail |
|---|---|---|
| Init 5 + 6 epics SHIPPED + retro-closed | 6 | E6, E7, E8, E9, E10, E11 — all `done`. **No retroactive modification** — closed epics' audit trail stays intact. |
| To add | 3 initiatives × 10 stories total | Initiative 9 = Epic E14 (3 stories: 14.1–14.3, test-isolation cleanup, scheduled FIRST). Initiative 7 = Epic E12 (5 stories: 12.1–12.5, account & admin UX polish, scheduled second). Initiative 8 = Epic E13 (2 stories: 13.1, 13.2, catalog mobile + image perf, scheduled third). |
| To modify | 0 | No retroactive epic-level modifications. The visual-verification gate is a new procedural addition to Stories 12.1–13.2's AC contract, not a retroactive Init 6 modification. Initiative 9 stories do NOT carry NFR7-UX-1 / NFR8-UX-1 — they are test-infrastructure work without observable UI surfaces (14.1 vitest finder fixes are non-rendering test edits; 14.2 is pytest conftest work; 14.3 is hook-context infrastructure work; per §3.3.2 below). |
| To remove | 0 | None. |

### 2.2 Story impact

- **All prior shipped stories untouched.** Init 5 Stories 6.1–10.4 and Init 6 Stories 11.1–11.7 carry forward unmodified.
- **TB-015 (#3 Wyczyść pomiary)** promotes from triage-backlog to standalone `bmad-quick-dev` invocation, NOT a story in either new epic. Rationale: ~1-line fix; quick-dev is the right vehicle per memory [[itcm-autonomous-mode]] guidance that "drobna zmiana / bugfix that fits in one commit → bmad-quick-dev" (verbatim from project-context.md L204).
- **TB-018 (3 test-isolation issues)** promotes from triage-backlog to **Initiative 9 (E14)** with three stories. Rationale in §3.2.3 below.
- **New stories added:** Epic E14: 14.1 (vitest admin finder fixes), 14.2 (pytest hydrate DB-pollution close), 14.3 (visual-regression hook-context flake close). Epic E12: 12.1 (Admin Invites unblock), 12.2 (Admin Users inactive-filter), 12.3 (Display name on registration), 12.4 (Settings hub + 2FA discoverability), 12.5 (Sessions UX). Epic E13: 13.1 (Mobile carousel arrows), 13.2 (Thumbnail pipeline).

### 2.3 Artifact conflict analysis

**PRD impact (prd.md):**

- ADD `## Initiative 9 — Test Isolation Cleanup` H2 section. Brownfield test-infrastructure cleanup; FRs are test-success-criteria (FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1). No customer-observable behavior change. Section contains: Overview, Functional Requirements (3 FRs above), Non-Functional Requirements (NFR9-DETERMINISM-1 — test-success determinism across run-order permutations), Cross-references.
- ADD `## Initiative 7 — Account & Admin UX Polish` H2 section. Follows established Initiative-N H2-append pattern (per project-context.md L208–211 + memory [[feedback_vanilla_bmad_first]]). Section contains: Overview, Functional Requirements (FR7-ADMIN-INVITES-1..3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1..2, FR7-SESSIONS-1..2), Non-Functional Requirements (NFR7-UX-1 visual verification gate, NFR7-A11Y-1 keyboard reach for new controls), Cross-references.
- ADD `## Initiative 8 — Catalog Mobile & Image Performance` H2 section. Section contains: Overview, Functional Requirements (FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1..3), Non-Functional Requirements (NFR8-PERF-1 thumbnail payload size budget, NFR8-COMPAT-1 WebP fallback posture, NFR8-UX-1 visual verification gate), Cross-references.
- UPDATE Initiatives Index table (prd.md L79–84): add Init 7 + Init 8 + Init 9 rows. Status `planning`. Update frontmatter `initiatives:` array.

**Architecture impact (architecture.md):**

- ADD `## Initiative 9 — Test Isolation Cleanup` H2 section. **No architectural decisions** — test-infrastructure work only, no product-architecture impact. Section is pointer-only (refers to Init 0–6 architecture as load-bearing; this initiative does not modify the auth contract, route table, data plane, or any product-architecture invariant). Listed for index-table completeness.
- ADD `## Initiative 7 — Account & Admin UX Polish` H2 section. Light-touch — UX polish, not architectural overhaul. Section contains: Overview, Decisions In-Scope (Decision Q: settings hub topology). Most stories in Epic E12 are component-level and don't require new architectural decisions.
- ADD `## Initiative 8 — Catalog Mobile & Image Performance` H2 section. Section contains: Overview, Decisions In-Scope (Decision P: on-upload thumbnail pipeline + WebP target + query-param variant endpoint shape).
- UPDATE Initiatives Index table (architecture.md L83): add Init 7 + Init 8 + Init 9 rows.

**UX Design impact:** No UX design document currently exists in `planning-artifacts/`. UX decisions are absorbed into individual story specs (per Init 0–6 precedent). No new artifact needed. Initiative 9 has no UX impact (test-infrastructure).

**Implementation artifact impact (sprint-status.yaml):**

- ADD `epic-14: Test Isolation Cleanup` section with 3 story entries (14.1–14.3), all `backlog` status. **Scheduled FIRST** in the execution chain.
- ADD `epic-12: Account & Admin UX Polish` section with 5 story entries (12.1–12.5), all `backlog` status.
- ADD `epic-13: Catalog Mobile & Image Performance` section with 2 story entries (13.1, 13.2), all `backlog` status.

**Triage backlog (triage-backlog.md):**

- TB-015 — already updated 2026-05-21 with pinned root cause. Status flip from `candidate` → `promoted` happens when bmad-quick-dev invocation begins.
- TB-018 — already added 2026-05-21. Status flips to `promoted` on SCP approval; promotion vehicle = Initiative 9 (E14) in THIS SCP.

### 2.4 Technical impact

**Code surfaces touched:**

- **Frontend (apps/web/src/):**
  - `modules/admin/AdminTabs.tsx` — replace `<span aria-disabled>` with `<Link>` for invites tab (Story 12.1).
  - `modules/admin/InvitesPage.tsx` + child components — i18n key parity, table layout fix (Story 12.1).
  - `modules/admin/UsersPage.tsx` — add `is_active` filter UI + query param wiring (Story 12.2).
  - `modules/auth/RegistrationPage.tsx` (or wherever the registration form lives — TBD during Story 12.3 spec phase) — add optional display-name field, auto-suggest from email prefix (Story 12.3).
  - `routes/settings/index.tsx` (NEW) — settings hub landing page (Story 12.4).
  - `routes/settings/profile.tsx` (NEW) — display-name edit page (Story 12.3 ↔ 12.4 boundary).
  - `shell/AppShell.tsx` or `shell/TopBar.tsx` — add user-menu link to `/settings` (Story 12.4).
  - `routes/settings/sessions.tsx` — pagination, sort, UA-filter checkbox (Story 12.5).
  - `ui/custom/CardCarousel.tsx` + `modules/catalog/components/ModelGallery.tsx` — `sm:opacity-0` breakpoint conditional (Story 13.1).
  - `modules/catalog/components/ModelGallery.tsx` (and any catalog-card image-srcing site) — `srcSet` with thumbnail variant (Story 13.2).
  - `locales/pl.json` + `locales/en.json` — new keys for admin invites (12.1) + settings hub (12.4) + display name (12.3) + sessions UX (12.5).

- **Backend (apps/api/):**
  - `app/modules/admin/router.py` — users-list endpoint extends query to accept `is_active` param (Story 12.2). Verify the existing endpoint shape first; may already accept it.
  - `app/modules/auth/router.py` — registration endpoint accepts optional `display_name` field in request body, falls back to email prefix if absent (Story 12.3); sessions endpoint extends to accept pagination + sort + UA-filter params (Story 12.5).
  - `app/modules/admin/router.py` or new module — display-name update endpoint for self-service (Story 12.3).
  - `app/core/db/models.py` — verify `User.display_name` field exists; if not, add via Alembic migration (Story 12.3). **TBD during spec phase — likely already exists per Init 5 User model.**
  - `app/modules/sot/router.py` — extend `/api/models/{model_id}/files/{file_id}/content` to accept `variant=thumb` query param OR add sibling endpoint (Story 13.2 — Decision P).
  - `app/modules/admin/router.py` (or admin-side file-upload handler) — on file upload of image kind, enqueue thumbnail generation job (Story 13.2).

- **Worker (workers/render/ OR new sibling):**
  - On-upload thumbnail generation. **Decision needed:** does this fit in the existing `workers/render/` worker (which uses trimesh + matplotlib for STL render), or does it warrant a new `workers/thumbnail/` sibling worker? Recommendation: extend existing arq worker in `apps/api/app/workers/` (NOT the render worker) with a `generate_thumbnail` task — thumbnails are I/O-light (Pillow CPU), don't need the heavy matplotlib stack. **TBD during Story 13.2 spec phase; SCP-level decision deferred to spec.**
  - `apps/api/pyproject.toml` — verify Pillow ≥11 is already pinned (per project-context.md L24, worker has Pillow ≥11; API may not). If not, add (Story 13.2).

- **Infra:**
  - `infra/scripts/backfill-thumbnails.sh` (NEW) — one-shot script to walk existing model files of image kind and generate thumbnails. Idempotent (skip files where thumbnail already exists). Run once post-deploy of Story 13.2.

**Test surfaces touched (Initiative 7 + 8):**

- Each story adds vitest unit/integration tests (per project-context.md L114–119 frontend convention) + pytest tests (per L93–104 backend convention) where applicable.
- Each story adds at minimum one Playwright visual smoke matching the desktop-light + mobile-light projects (per project-context.md L110–112 4-project matrix). Per the new `feedback_frontend_visual_verification` memory, the visual smoke is mandatory not optional.
- Story 13.2 adds a pytest test for thumbnail generation idempotency, content-type, file-size bound (NFR8-PERF-1 verification).

**Test-infrastructure surfaces touched (Initiative 9):**

- **Story 14.1 (vitest admin):** `apps/web/src/modules/admin/InvitesPage.test.tsx`, `GenerateInviteModal.test.tsx`, `InviteTokenDisplayModal.test.tsx`, `ResetLinkDisplayModal.test.tsx`, `UsersPage.test.tsx` — all 5 files have finder mismatches; fix is regenerate selectors against current i18n keys + DOM shape. May require touching the components themselves only if a test-only fix is structurally infeasible — but ITCM constraint: prefer test-side fixes unless component side has an actual bug. Verify final test count: 18 failing → 0 failing.
- **Story 14.2 (pytest hydrate):** `apps/api/tests/test_hydrate_local_tree.py` + `apps/api/tests/test_sot_model_file_content.py` + `apps/api/tests/conftest.py` — root cause investigation likely in conftest fixture scoping (probable: a session-scoped fixture that should be function-scoped, OR a missing rollback in the `_isolated_db` chain when FAKE_STL_PAYLOAD_AAA is committed). Fix tightens the isolation contract.
- **Story 14.3 (visual-regression hook context):** `apps/web/.husky/_check-baseline-review.mjs` + `apps/web/tests/visual/playwright.config.ts` + `infra/scripts/check-all.sh` (or wherever the hook chain lives) — root-cause is unconfirmed (likely build SHA drift, port collision with concurrent vitest, OR snapshot baseline cache invalidation timing). Story 14.3 begins with an instrumentation pass (log the actual port + build SHA + image hash at visual-stage entry) to pin the root cause before fix.

**Migration impact:**

- Story 12.3 — IF `User.display_name` field doesn't already exist, add Alembic migration `apps/api/migrations/versions/<seq>_add_user_display_name.py`. If it exists (likely — Init 5 User model is rich), no migration needed.

**Deploy impact:**

- Standard `infra/scripts/deploy.sh` flow after each story merge (per memory [[feedback_auto_deploy_dev]]). Doc-only commits skipped per the doc-only-commit rule.
- Backfill script (`infra/scripts/backfill-thumbnails.sh`) runs once after Story 13.2 deploy. Operator-supervised, not part of `deploy.sh` automation.

**Cross-repo impact:** None. No edge proxy changes. No sibling configs changes.

---

## Section 3 — Recommended Approach

### 3.1 Path forward selection — Option 1 Direct Adjustment

Per CC checklist §4: Option 1 (Direct Adjustment via three new initiatives + one quick-dev) is selected.

- **Option 2 (Potential Rollback)** evaluated: **Not viable.** No completed work to roll back — all 9 user-reported items are new requirements, polish gaps, or one previously-identified bug; the 3 TB-018 items are pre-existing test-infrastructure debt, not regressions to revert. No Init 5/6 stories produced incorrect output that needs reverting.
- **Option 3 (PRD MVP Review)** evaluated: **Not viable.** PRD MVP was Init 0 (the portal v1 cutover) — that shipped in 2026-04 and is closed. No active MVP under threat. All subsequent initiatives (1–6) have been additive expansions; Initiatives 7 + 8 + 9 follow the same additive-extension pattern.
- **Option 1 (Direct Adjustment)** selected: three new initiatives + one quick-dev, no rollback, no MVP revisit. Effort estimate: **Medium-High** (~10 stories total: 3 test-infrastructure Init 9 + 5 frontend-heavy Init 7 + 2 cross-cutting Init 8). Risk: **Low** (no security boundary, no auth contract change, no data-integrity risk; Init 9 is investigative for 14.3 but bounded). Timeline: **4–6 days back-to-back autonomous execution** (Init 9: ~½–1 day with 14.3's instrumentation pass dominating; Init 7: ~2–3 days; Init 8: ~1–2 days; conservative estimate adds buffer for Codex review intercepts).

### 3.2 Bundling rationale — why 3 initiatives + 1 quick-dev, not 1 mega-epic

ITCM-proposed (and SCP-validated) breakdown:

#### 3.2.1 Initiative 7 (Epic E12) — Account & Admin UX Polish

Groups items #2, #4, #5, #6, #7. Common theme: **self-service + admin surfaces touching auth-adjacent flows.** Stories share frontend module families (admin, settings, registration), share an i18n locale-key extension pattern, and share the new visual-verification gate AC contract. Bundling into one epic gives one retro at the end vs five mini-retros.

#### 3.2.2 Initiative 8 (Epic E13) — Catalog Mobile & Image Performance

Groups items #8, #9. Common theme: **catalog list-page visual quality on mobile.** Both stories touch the catalog read-surface (E0.4 lineage), both have measurable performance/UX impact, and Story 13.2 (thumbnail pipeline) is the bigger backend-touching story that benefits from being scoped separately from UX-polish work.

#### 3.2.3 Initiative 9 (Epic E14) — Test Isolation Cleanup (operator scope-pull 2026-05-21)

Groups the three TB-018 items (vitest admin finders, pytest hydrate pollution, visual-regression hook flake). Common theme: **test-infrastructure isolation contracts that pre-date Initiatives 5+6 and have failed silently through multiple sprint close-outs.**

**Why promoted into this SCP** (revised mid-review per operator scope-pull):

1. **Direct interference with Init 7 + 8 stories.** All three TB-018 items touch surfaces that Stories 12.1, 12.2, 12.3, 12.5, and 13.2 will modify. Leaving them parked means new stories develop on unreliable test signal — exactly the failure mode the new NFR7-UX-1 / NFR8-UX-1 visual-verification gate is supposed to prevent. Visual gate cannot compensate for a `check-all.sh` baseline that fails for unrelated infrastructure reasons.
2. **Pre-existing-issue threshold** (per memory [[feedback_preexisting_issue_threshold]]): each of the three items has surfaced in ≥3 sprint sessions historically. The threshold is met for promotion candidacy regardless of operator pull-forward; operator pull-forward is the procedural promotion event.
3. **Cohesion as a test-infrastructure work unit.** Three test-isolation issues belong together: they're all isolation-contract problems, all benefit from one coherent cleanup pass, all share the same retro question ("how solid is our test isolation across the three frameworks — vitest, pytest, playwright?"). Splitting them across Init 7 stories (preamble) would dilute both Init 7's retro scope and the test-cleanup learning.

**Why scheduled FIRST (before E12, E13):**

- Story 14.1 unblocks Stories 12.1 + 12.2 admin-test surface (failing tests get reset to green, new admin work has reliable signal).
- Story 14.3 unblocks Stories 12.1 + 12.2 visual-regression baselines (admin-invites + admin-users baselines become trustworthy under `check-all.sh`).
- Story 14.2 unblocks Stories 12.3 + 12.5 + 13.2 backend-test surface (User/ModelFile test isolation tightened).

**Why not bundle into Init 7 as a Story 12.0 preamble:** that would violate the project's "epics deliver user value" principle (per epics.md L93 — "Initiatives 1+ must follow normal 'epics deliver user value' standards"). Test-isolation work delivers infrastructure value, not user value; it belongs in its own epic with its own retro asking infrastructure-oriented questions, not user-experience-oriented ones.

**Why not three standalone quick-devs:** Story 14.3 (visual-regression hook context flake) is investigative — root cause is unconfirmed; the first task is an instrumentation pass to pin the cause before the fix. That investigation work doesn't fit project-context.md L204's quick-dev framing ("drobna zmiana / bugfix that fits in one commit"). Bundling 14.3 alongside 14.1 + 14.2 in one epic keeps the BMAD vanilla CS → DS → CR cycle uniform.

#### 3.2.4 TB-015 (#3 Wyczyść pomiary) — standalone quick-dev

Pinned 1-line fix; bundling into any epic adds ceremony cost without saving execution time. Per project-context.md L204 routing rule.

#### 3.2.5 Why not one mega-epic across Init 7 + 8 + 9?

Three epics give cleaner retrospective scope: E14 retro asks "how solid is test isolation across vitest / pytest / playwright?" (infrastructure-oriented); E12 retro asks "how did account/admin self-service work go?" (UX product surface); E13 retro asks "how did catalog mobile + thumbnails work?" (performance + mobile UX). One mega-epic would dilute all three retros and mix unrelated learnings.

#### 3.2.6 Why not many small epics (one per item)?

Five epics for five admin-self-service stories is over-ceremony — they're cohesive enough that one epic captures the unit of work. Two stories for catalog mobile is borderline epic-sized; below that it's quick-dev territory. Three test-infrastructure items is borderline epic-sized; bundling them gives a real test-infrastructure retro, whereas splitting them loses the cross-framework learning.

### 3.3 Per-story acceptance-criteria contract

#### 3.3.1 Visual verification gate (Stories 12.1–13.2)

Every Story 12.1–13.2 has, in addition to story-specific functional acceptance criteria, the following **mandatory non-functional AC pattern** (codified by memory [[feedback_frontend_visual_verification]] saved 2026-05-21):

> **Visual verification gate (NFR7-UX-1 / NFR8-UX-1):** Before marking this story ready for code-review, the implementing agent MUST load the affected route(s) in a real browser (agent-browser primary via CDP on `localhost:9222` per global CLAUDE.md, Playwright fallback) and capture snapshots of:
> - Desktop default viewport (1280×720)
> - Mobile viewport (≤414px width)
>
> Verification checklist (all MUST pass before CR):
> - Route loads without console errors
> - All i18n keys resolve (no `module.section.key` raw key visible)
> - No viewport overflow (horizontal scroll only if intentional)
> - All interactive elements clickable (no `pointer-events: none` swallowing — the TB-015 class)
> - Nav links to/from this surface are enabled where appropriate (per Init 6 admin-invites incident lesson)
>
> Snapshots attached to the Dev Agent Record. CR may reject the story if snapshots are missing OR show any of the above defects.

This is a **non-negotiable AC** for every UI-touching story in this batch. It does NOT supplant the existing visual-regression Playwright matrix (per project-context.md L110 + L191 + L254) — that stays as the CI gate. The new requirement is a *pre-CR human-or-agent eyeball pass* on top of automated visual regression, motivated by Init 6's admin-invites shipping with three eyeball-catchable defects that nonetheless passed all four Playwright matrix projects (mobile-light + mobile-dark + desktop-light + desktop-dark had baselines, just the baselines themselves missed the defects).

Story 13.2 (thumbnail pipeline) also adds a **backend NFR**: NFR8-PERF-1 — thumbnail variant payload MUST be ≤50 KB for typical phone photos (input ≥1 MB). Verified by pytest fixture loading representative samples.

#### 3.3.2 Initiative 9 (Stories 14.1–14.3) — explicit scope exclusion for NFR7-UX-1 / NFR8-UX-1

Initiative 9 stories do **NOT** carry the NFR7-UX-1 / NFR8-UX-1 visual-verification gate as an AC, because:

- **Story 14.1 (vitest admin finder fixes):** test-only edits to `*.test.tsx` files — no rendered UI surface to verify. The very tests being fixed verify the rendered UI; success criterion is "0 vitest failures in admin module" (FR9-VITEST-ADMIN-1).
- **Story 14.2 (pytest hydrate DB-pollution close):** test-only edits to `conftest.py` / test data scope — no UI surface. Success criterion is "`test_hydrate_creates_local_tree` passes deterministically when run after `test_sot_model_file_content` across 10 consecutive runs" (FR9-PYTEST-HYDRATE-1 + NFR9-DETERMINISM-1).
- **Story 14.3 (visual-regression hook flake):** infrastructure-only fix to the hook chain — the actual rendered baselines are NOT modified by this story (they're the SAME baselines that pass standalone today). Success criterion is "`check-all.sh` produces identical pass/fail verdict for ALL existing visual-regression baselines compared to `npx playwright test --config=...` standalone invocation" (FR9-VISUAL-HOOK-1).

Initiative 9 stories instead carry **NFR9-DETERMINISM-1**: each cleanup MUST be verified by running the affected test suite ≥3 times back-to-back without failure (or with deterministic failure for the right reason). This is the test-infrastructure analog of the UI visual-verification gate: it's a procedural commitment to "the fix actually fixed it, repeatably."

### 3.4 Execution flow (autonomous chain)

After this SCP is operator-approved:

```
[This session — current]
  → bmad-correct-course produces SCP (this document, 2026-05-21 SCP, revised
    mid-review 2026-05-21 to add Initiative 9 per operator scope-pull)

[Next session — fresh context]
  → bmad-quick-dev (TB-015 promotion, #3 Wyczyść pomiary)
    → spec + 1-line fix + agent-browser verify + Codex review + deploy
    → ship-day-1 standalone

[After quick-dev close]
  → bmad-edit-prd (Init 7 + Init 8 + Init 9 PRD H2 extension)
    → updates prd.md with Init 7 + Init 8 + Init 9 sections per shape in §4.1 below
  → manual epics.md + architecture.md extension (no bmad-edit-epics skill)
    → Init 7 + Init 8 + Init 9 H2 sections per shape in §4.2 + §4.3 below
  → manual sprint-status.yaml extension (no bmad-extend-sprint skill — Init 6 precedent confirms manual append)
    → E14 + E12 + E13 backlog entries per shape in §4.4 below

[Init 9 epic execution — FIRST, unblocks E12/E13 test surfaces]
  → bmad-create-story (14.1) → bmad-dev-story → bmad-code-review → deploy
    (repeat for 14.2, 14.3)
  → bmad-retrospective (Init 9)

[Init 7 epic execution — second, develops on now-reliable test signal]
  → bmad-create-story (12.1) → bmad-dev-story → bmad-code-review → deploy
    (repeat for 12.2, 12.3, 12.4, 12.5)
  → bmad-retrospective (Init 7)

[Init 8 epic execution — third]
  → bmad-create-story (13.1) → bmad-dev-story → bmad-code-review → deploy
  → bmad-create-story (13.2) → bmad-dev-story → bmad-code-review → deploy
  → bmad-retrospective (Init 8)

[Sprint close]
  → sprint-status.yaml epic-14 + epic-12 + epic-13 entries flip to `done`
  → SCP status: shipped
```

Token-budget pauses (per memory [[feedback_autonomous_sleep_on_budget]]):

- 5h ≥ 80% → sleep through reset, then continue.
- 7d ≥ 95% → pause at next epic boundary, surface to operator.
- No `extra_usage` opt-in.

**Natural pause points** (low-cost interruption boundaries if budget triggers):

- After TB-015 quick-dev ships, before bmad-edit-prd runs.
- After Init 9 retro closes, before Init 7 begins (clean handoff: test infrastructure done, UX work next).
- After Init 7 retro closes, before Init 8 begins (clean handoff: admin/account UX done, catalog work next).

---

## Section 4 — Detailed Change Proposals

### 4.1 PRD extension — Initiative 7 + Initiative 8 + Initiative 9 H2 sections

The three sections below extend `_bmad-output/planning-artifacts/prd.md` via manual append (no bmad-edit-prd needed for first draft; bmad-edit-prd can validate after). The PRD Initiatives Index table at prd.md L79 also gets three new rows (added in the manual edit pass).

**Append order in prd.md:** Initiative 7 → Initiative 8 → Initiative 9 (file-order; Initiative-number-ascending matches Init 0–6 precedent regardless of execution scheduling). Execution order is Init 9 → Init 7 → Init 8 per §3.4 — file order and execution order are independent dimensions.

#### 4.1.1 PRD § Initiative 7 — Account & Admin UX Polish

```markdown
## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status TBD pending operator approval). Predecessor Initiative 6 closed 2026-05-21 (Stories 11.1–11.7 shipped, cutover-smoke Scenario 5 PASS, audit gate PASS, commit `05a2f1a`). Initiative 7 is **additive polish** on Init 5 admin + account self-service surfaces and Init 0 registration flow. Single Epic E12 with 5 stories.

### Overview

Initiative 5 shipped a complete authentication + admin substrate (E6 member role + invites, E7 TOTP 2FA, E8 admin panel users + invites) but the user-facing surfaces have minimum-viable UX. Operator hands-on use 2026-05-21 surfaced five polish gaps: admin Invites nav tab is grayed-out placeholder despite admin role + missing translations + viewport overflow; admin Users panel has no inactive-user filter; registration auto-derives display name from email prefix with no user agency; 2FA enrollment feature is fully present but undiscoverable (no settings hub, no user-menu link); active-sessions list grows unbounded with no pagination/sort/filter, cluttered by API/curl probe sessions.

Initiative 7 raises these surfaces to operator-acceptable UX with five stories, all frontend-heavy. Each story carries a mandatory pre-CR visual-verification AC (NFR7-UX-1) as direct response to Init 6's admin-invites shipping incident.

### Functional Requirements

- **FR7-ADMIN-INVITES-1: Admin Invites nav tab is enabled for admin role.** `apps/web/src/modules/admin/AdminTabs.tsx` replaces the hardcoded `<span aria-disabled="true">` invites entry with a `<Link to="/admin/invites">` element matching the existing styling of the other admin tabs (Users, Models, Categories, Tags, Audit). **Verifiable:** authenticated admin loading `/admin` sees a clickable Invites tab in the admin nav; non-admin authenticated users continue to see the admin module gated (per Init 5 admin role check).
- **FR7-ADMIN-INVITES-2: Admin Invites page renders complete pl/en translations.** The ~20 i18n keys currently missing from `apps/web/src/locales/pl.json` + `en.json` (e.g. `admin.invites.title`, `admin.invites.column_role`, `admin.invites.action_revoke`, etc. — full key list enumerated during Story 12.1 spec) are added with parity between Polish and English locale files. **Verifiable:** loading `/admin/invites` with `lang=pl-PL` renders Polish labels; with `lang=en-US` renders English labels; no raw `admin.invites.*` key strings visible in DOM.
- **FR7-ADMIN-INVITES-3: Admin Invites table fits viewport at desktop default and admin-mobile breakpoints.** Table layout is responsive (max-width on table container, horizontal scroll if needed for narrow viewports, left margin compressed from current Init 5 default). **Verifiable:** Playwright snapshot of `/admin/invites` at desktop-light (1280×720) shows complete table within viewport; mobile-light (390×844 Pixel 5) shows table with horizontal scroll affordance and no right-edge clipping.
- **FR7-ADMIN-USERS-1: Admin Users panel hides inactive users by default with checkbox toggle.** `apps/web/src/modules/admin/UsersPage.tsx` query adds an `is_active` filter param defaulting to `True`. A checkbox labeled "Pokaż nieaktywne konta" / "Show inactive accounts" toggles the filter to `None` (shows all). Inactive rows when shown are visually distinguishable (e.g. muted text color via theme token) but not hidden. **Verifiable:** default load of `/admin/users` shows only `is_active=true` rows; checkbox-checked load shows all rows with inactive rows visually muted.
- **FR7-REG-DISPLAY-1: Registration form accepts optional display name with auto-suggest from email prefix.** Registration page (path TBD during Story 12.3 spec — likely `apps/web/src/routes/auth/register.tsx` or similar) adds an optional `display_name` text field below the email field. On email blur, if the display-name field is empty, populate with email prefix (text before `@`). User can edit/override before submit. Backend `POST /api/auth/register` accepts an optional `display_name` field in the request body. Backend stores the provided value if non-empty; falls back to email prefix server-side if absent. **Verifiable:** filling registration form with email `foo@example.com` populates display-name field with `foo`; user typing `Foo Bar` before submit results in `display_name="Foo Bar"` on the created User row.
- **FR7-SETTINGS-HUB-1: A `/settings` hub page exists and lists all settings sections.** New route `apps/web/src/routes/settings/index.tsx` renders a hub listing: Profile (`/settings/profile`), 2FA (`/settings/2fa`), Sessions (`/settings/sessions`). Each entry is a card or list-row with i18n label + brief description. Anonymous users redirected to `/login?next=%2Fsettings` (per Init 6 FR6-SHELL-1 shell-level AuthGate). **Verifiable:** authenticated user loading `/settings` sees three section entries; clicking any entry navigates to the section route.
- **FR7-SETTINGS-HUB-2: A "Settings" link is visible in the user-menu in the top-bar.** `apps/web/src/shell/TopBar.tsx` (or wherever the user-menu dropdown lives) adds a "Settings" link routing to `/settings`. Placement after the user's name/avatar and before "Sign out". **Verifiable:** authenticated user clicking the user-menu avatar/dropdown sees a "Settings" entry routing to `/settings`.
- **FR7-SESSIONS-1: Active sessions list supports pagination with default page size 20.** `apps/web/src/routes/settings/sessions.tsx` paginates the existing `/api/auth/sessions` endpoint response (which already accepts `offset` + `limit` per backend code at L351-368). UI: page-size selector (default 20, options 10/20/50), prev/next page controls, total-count indicator. **Verifiable:** session list with >20 entries shows pagination controls; clicking next page advances the offset.
- **FR7-SESSIONS-2: Active sessions list filters non-browser User-Agents by default with reveal-toggle.** `apps/web/src/routes/settings/sessions.tsx` adds a checkbox labeled "Pokaż API/non-browser sesje" / "Show API/non-browser sessions" defaulting OFF. When OFF, sessions whose `user_agent` matches a non-browser pattern (e.g. `curl/`, `httpie/`, `python-requests/`, `Mozilla/5.0` not matching a known-browser-fingerprint set TBD during Story 12.5 spec) are excluded from the list. When ON, all sessions show with the non-browser sessions visually distinguishable (e.g. icon or muted color). Sort defaults to `last_used_at DESC`. **Verifiable:** session list with browser + curl entries shows only browser entries by default; checkbox-checked shows all entries with curl entries visually distinguishable.

### Non-Functional Requirements

- **NFR7-UX-1: Pre-CR visual verification gate on every UI story.** Stories 12.1–12.5 each have a mandatory non-functional AC: before marking ready for code-review, the implementing agent loads affected routes in a real browser (agent-browser primary, Playwright fallback) at desktop-default (1280×720) and mobile (≤414px) viewports, captures snapshots, and verifies: (a) route loads without console errors, (b) all i18n keys resolve (no raw `module.section.key` literals), (c) no unintended viewport overflow, (d) all interactive elements clickable (TB-015 class — no `pointer-events: none` swallowing), (e) nav links to/from this surface enabled where appropriate (Init 6 admin-invites class). Snapshots attached to Dev Agent Record. CR may reject for missing snapshots OR observable defects.
- **NFR7-A11Y-1: New interactive controls reachable by keyboard.** Checkboxes (FR7-ADMIN-USERS-1, FR7-SESSIONS-2), enabled nav link (FR7-ADMIN-INVITES-1), display-name field (FR7-REG-DISPLAY-1), pagination controls (FR7-SESSIONS-1), user-menu Settings link (FR7-SETTINGS-HUB-2) are all keyboard-reachable via Tab + activated via Enter/Space per shadcn/ui + base-ui default behavior. **Verifiable:** Playwright keyboard-navigation test reaches each new control within ≤10 Tab presses from page-load focus position.
- **NFR7-COMPAT-1: Initiative 6 default-deny posture preserved.** No new public routes added to `_PUBLIC_ROUTES` allowlist in `apps/api/app/main.py`. All new backend endpoints in Initiative 7 (display-name update endpoint, settings-related endpoints if any) carry `current_user` Depends. **Verifiable:** Story 11.4 route enforcement test continues to pass after Initiative 7 stories merge.

### Cross-references

- Predecessor: Initiative 6 (Post-Cutover Default-Deny Auth Posture) — closed 2026-05-21 `05a2f1a`.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this document).
- Source observations: operator batch report 2026-05-21 + pre-SCP Explore subagent recon 2026-05-21.
- Architecture extension: `architecture.md` § Initiative 7 (Decision Q — settings hub topology; light-touch).
- Epics extension: `epics.md` § Initiative 7 (single Epic E12 with 5 stories 12.1–12.5).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via manual epics.md-mirroring append (epic-12 with 5 backlog stories).
- Memory entries informing this initiative: [[itcm-autonomous-mode]], [[feedback_frontend_visual_verification]], [[feedback_default_to_bmad_workflow]].
- Triage cross-reference: TB-018 (test-isolation cleanup bundle) is NOT part of Initiative 7 — it has been promoted to its own **Initiative 9** in THIS SCP per operator scope-pull 2026-05-21, scheduled FIRST in the execution chain to unblock Init 7's admin test surfaces. See §4.1.3 + §4.3.3 for Init 9 spec.
```

#### 4.1.2 PRD § Initiative 8 — Catalog Mobile & Image Performance

```markdown
## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status TBD pending operator approval). Predecessor Initiative 7 (Account & Admin UX Polish) running in parallel — Initiative 8 has no Init 7 dependency. Single Epic E13 with 2 stories.

### Overview

Initiative 0 (Product Foundation) shipped the catalog read-surface (E0.4) with minimum-viable visual quality on mobile and no image transformation pipeline. Operator hands-on use 2026-05-21 surfaced two catalog UX gaps: mobile catalog carousel has no prev/next arrows because the `opacity-0 group-hover:opacity-100` pattern doesn't fire on touch devices (users can only navigate via dots, hard to hit, and accidentally click into the model detail); catalog cards serve full-resolution original images (operator uploads 8K+ phone photos that take seconds to load on mobile data and waste bandwidth).

Initiative 8 raises catalog mobile UX with two stories: 13.1 makes mobile carousel arrows always-visible at sm-breakpoint and below; 13.2 introduces an on-upload thumbnail pipeline (Pillow, 800px longest side, WebP @ q80) with a query-param variant endpoint, srcSet on catalog cards, and a one-shot backfill script for existing uploads.

### Functional Requirements

- **FR8-CAROUSEL-MOBILE-1: Catalog carousel prev/next arrows are visible on mobile (≤sm breakpoint).** `apps/web/src/ui/custom/CardCarousel.tsx` and `apps/web/src/modules/catalog/components/ModelGallery.tsx` arrow buttons change from `opacity-0 group-hover:opacity-100` (current — invisible on touch) to `sm:opacity-0 sm:group-hover:opacity-100` (new — desktop unchanged behavior, mobile always-visible). **Verifiable:** Playwright snapshot of catalog list page at mobile-light (390×844 Pixel 5) shows prev/next arrow buttons rendered visibly; desktop-light (1280×720) snapshot shows arrows hidden until hover (current behavior preserved).
- **FR8-THUMB-1: Image-kind file uploads generate a thumbnail variant on upload.** `apps/api/app/modules/admin/router.py` model-file create endpoint (image kind) enqueues an arq task that generates a thumbnail variant via Pillow: 800px longest side, WebP container, quality 80, EXIF orientation honored. Thumbnail stored alongside original in `portal-content` volume with naming convention `<original-filename>.thumb.webp`. **Verifiable:** uploading a 4000×3000 JPEG as image-kind file results in (a) original preserved as-is, (b) sibling `<filename>.thumb.webp` file created within 30 seconds, (c) thumbnail is 800×600 (longest-side scaled), (d) thumbnail file size ≤50 KB (NFR8-PERF-1).
- **FR8-THUMB-2: Asset content endpoint supports `variant=thumb` query param.** `apps/api/app/modules/sot/router.py` GET `/api/models/{model_id}/files/{file_id}/content?variant=thumb` returns the thumbnail variant if it exists; falls back to original if not (e.g. for files uploaded before thumbnail pipeline shipped and not yet backfilled). **Verifiable:** `curl /api/models/.../files/.../content?variant=thumb` returns the `.thumb.webp` file with `Content-Type: image/webp`; same request without `variant=thumb` returns original with original content-type.
- **FR8-THUMB-3: Catalog cards request thumbnail variant via srcSet.** `apps/web/src/modules/catalog/components/ModelGallery.tsx` (and any catalog-card image-srcing site) renders `<img srcSet="${full} 2x, ${thumb} 1x">` or equivalent. Detail view (model-page large image) continues to use full-resolution original. **Verifiable:** Playwright network capture on catalog list shows requests to `?variant=thumb` URLs; model-detail page navigation shows requests to full-res URLs.

### Non-Functional Requirements

- **NFR8-PERF-1: Thumbnail variant payload ≤50 KB for typical phone-photo inputs.** Pytest fixture exercises Pillow pipeline with representative samples (3000×4000 JPEG, 4000×3000 JPEG, 2000×3000 PNG with alpha) and asserts output ≤50 KB per sample. **Verifiable:** test fixture in `apps/api/tests/test_thumbnail_pipeline.py` runs in <5s and passes for all sample categories.
- **NFR8-COMPAT-1: WebP browser support fallback posture.** WebP is supported by all browsers in the project's tested matrix (Chromium-based, Firefox 65+, Safari 14+). Frontend does NOT include a JPEG fallback `<source>` in `<picture>`; if a future browser-compat regression surfaces, the fallback gets added in a follow-up story. **Decision rationale:** the project's user base is technical (operator + invited members on modern browsers); WebP compatibility headache is not load-bearing today.
- **NFR8-UX-1: Pre-CR visual verification gate on every UI story.** Same shape as NFR7-UX-1 — Stories 13.1 and 13.2 both have the mandatory pre-CR agent-browser snapshot pass. Especially important for 13.1 (mobile-only behavior change) and 13.2 (srcSet wiring is easy to miss in unit tests).

### Cross-references

- Predecessor: Initiative 0 (Product Foundation) — shipped retrospective 2026-04 v1.
- Parallel-running: Initiative 7 (Account & Admin UX Polish) — no Init 7 dependency.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this document).
- Source observations: operator batch report 2026-05-21 items #8 + #9 + pre-SCP Explore subagent recon 2026-05-21.
- Architecture extension: `architecture.md` § Initiative 8 (Decision P — thumbnail pipeline shape; on-upload + query-param variant + backfill).
- Epics extension: `epics.md` § Initiative 8 (single Epic E13 with 2 stories 13.1 + 13.2).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended via manual epics.md-mirroring append (epic-13 with 2 backlog stories).
- Memory entries informing this initiative: [[itcm-autonomous-mode]], [[feedback_frontend_visual_verification]].
```

#### 4.1.3 PRD § Initiative 9 — Test Isolation Cleanup

```markdown
## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md` (status TBD pending operator approval). Predecessor Initiative 6 closed 2026-05-21. Initiative 9 is **brownfield test-infrastructure cleanup** on test surfaces that pre-date Initiatives 5+6 and have failed silently through multiple sprint close-outs. **Scheduled FIRST in this SCP's execution chain** (before Initiative 7 + Initiative 8) because the test surfaces directly interfere with planned Init 7 + 8 stories. Single Epic E14 with 3 stories.

### Overview

Three pre-existing test-isolation gaps surfaced across Initiative 5 + 6 close-outs and were originally parked in `_bmad-output/triage-backlog.md` as TB-018 for a future dedicated CC session. Operator scope-pull 2026-05-21 promoted them into this SCP's scope, with the technical rationale that the affected test surfaces (admin module vitest + admin visual baselines + User/ModelFile pytest fixtures) coincide with Initiative 7 Stories 12.1, 12.2, 12.3, 12.5 + Initiative 8 Story 13.2 — leaving the issues parked would force the new stories to develop on unreliable test signal.

Initiative 9 closes the three gaps with three stories, each verified by determinism (NFR9-DETERMINISM-1). Initiative 9 does NOT carry the NFR7-UX-1 / NFR8-UX-1 visual-verification gate because its stories are test-infrastructure-only and have no observable UI surface (test files, conftest, hook chain).

### Functional Requirements

- **FR9-VITEST-ADMIN-1: Vitest admin module test suite has 0 failures.** `apps/web/src/modules/admin/InvitesPage.test.tsx` + `GenerateInviteModal.test.tsx` + `InviteTokenDisplayModal.test.tsx` + `ResetLinkDisplayModal.test.tsx` + `UsersPage.test.tsx` collectively go from 18 failing tests to 0 failing tests. Fix path: regenerate finder selectors (text/role/label matchers) against the current i18n keys + DOM shape. ITCM constraint: prefer test-side fixes; component-side changes only if structurally infeasible (and any component-side change must be justified in the story's Dev Agent Record as "this is an actual component bug, not a test bug"). **Verifiable:** `npm run test apps/web/src/modules/admin/` returns 0 failures; 5 affected files all pass; total admin-module vitest count grows or stays same (no test deletions to mask failures).
- **FR9-PYTEST-HYDRATE-1: `test_hydrate_creates_local_tree` passes deterministically when run after `test_sot_model_file_content`.** Root cause investigation (Story 14.2): identify the leak path of `FAKE_STL_PAYLOAD_AAA` from `test_sot_model_file_content.py` into the `/api/models` listing that `test_hydrate_creates_local_tree` iterates. Fix tightens the `apps/api/tests/conftest.py` isolation contract (probable: function-scoped DB fixture, or explicit teardown for FAKE_STL seeds, or DB transaction rollback at test exit). **Verifiable:** running `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in this exact order across 10 consecutive invocations yields all-PASS (NFR9-DETERMINISM-1 confirmation).
- **FR9-VISUAL-HOOK-1: Visual-regression hook-context produces identical pass/fail verdict to standalone Playwright invocation across ALL existing baselines.** Investigation (Story 14.3 begins with instrumentation pass): determine whether the divergence is port collision, build-SHA drift, snapshot cache invalidation, or environment-variable propagation. Fix removes the divergence. **Verifiable:** `infra/scripts/check-all.sh` visual stage and `cd apps/web && npx playwright test --config=tests/visual/playwright.config.ts` produce same `passed/failed/skipped` counts for the full baseline set, run back-to-back, ≥3 consecutive runs in each context (NFR9-DETERMINISM-1).

### Non-Functional Requirements

- **NFR9-DETERMINISM-1: Each Initiative 9 fix is verified by ≥3 consecutive successful runs of the affected test suite.** This is the test-infrastructure analog of the UI visual-verification gate — a procedural commitment to "the fix actually fixed it, repeatably, not just luckily once." Story 14.1 verification: `npm run test apps/web/src/modules/admin/` 3× consecutive. Story 14.2 verification: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` 3× consecutive. Story 14.3 verification: full visual-regression baseline set via `check-all.sh` 3× consecutive vs standalone 3× consecutive, identical verdict each time. Logged in Dev Agent Record per story.
- **NFR9-SCOPE-1: No production-code changes in Initiative 9 stories.** All work is test-side (test files, conftest, hook chain). If any of the three stories surface what looks like a production-code bug (e.g. a real component bug masquerading as a finder mismatch), the story stops, the bug is escalated to operator as a real product blocker, and Initiative 9 does not absorb the fix. Production-code fixes belong in a follow-up story under whichever initiative owns the surface.

### Cross-references

- Predecessor: Initiative 6 (Post-Cutover Default-Deny Auth Posture) — closed 2026-05-21 `05a2f1a`.
- Successor (Initiative 9 unblocks): Initiative 7 (Account & Admin UX Polish), specifically Stories 12.1, 12.2, 12.3, 12.5; Initiative 8 (Catalog Mobile & Image Performance), specifically Story 13.2.
- Source SCP: `sprint-change-proposal-2026-05-21.md` (this document).
- Source observations: TB-018 entry in `_bmad-output/triage-backlog.md` + operator scope-pull 2026-05-21 (mid-SCP-review).
- Architecture extension: `architecture.md` § Initiative 9 (pointer-only — no architectural decisions; test-infrastructure only).
- Epics extension: `epics.md` § Initiative 9 (single Epic E14 with 3 stories 14.1, 14.2, 14.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-14.
- Memory entries informing this initiative: [[feedback_preexisting_issue_threshold]] (threshold-derived candidacy mechanism), [[feedback_vitest_manual_cleanup]] (global `vitest.setup.ts` registers `afterEach(cleanup)` since commit a026e97 — Story 14.1 cleanups should NOT re-introduce per-file boilerplate), [[feedback_pytest_timeout]] (Story 14.2 verification MUST wrap pytest in `timeout 600`), [[feedback_visual_failure_mode_triage]] (Story 14.3 grep failure-mode breakdown before fixing).
- Triage cross-reference: TB-018 entry status flips `candidate` → `promoted` on SCP approval, then `promoted` → `done` per-Story-14.x close. TB-015 promotion (standalone quick-dev) is independent of Initiative 9.
```

### 4.2 Architecture extension — Initiative 7 + Initiative 8 H2 sections (+ Initiative 9 pointer-only)

Append the following to `_bmad-output/planning-artifacts/architecture.md`. Initiative 7 has one architectural decision (settings-hub topology — Decision Q); Initiative 8 has one architectural decision (thumbnail pipeline shape — Decision P). Both are light-touch — no new system components, no schema changes (modulo Story 12.3's display_name field which may already exist).

#### 4.2.1 Architecture § Initiative 7 — Account & Admin UX Polish

```markdown
## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Brownfield UX polish on Init 5 admin + account self-service surfaces and Init 0 registration. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 7" (FR7-* + NFR7-*). Single Epic E12 with 5 stories.

### Overview

Initiative 7 stories are primarily component-level changes on shipped frontend surfaces. The only architectural decision is the topology of the new settings hub (Decision Q) — does it become a route-layout wrapper, a flat list-of-cards landing, or a tab-style navigator? Decision below selects the flat list-of-cards landing for minimum coupling to Init 5/6 admin substrate.

### Decisions In-Scope (Q)

#### Decision Q — Settings hub topology

- **Realizes:** FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2.
- **Choice:** flat list-of-cards landing page at `/settings`. Each card links to a sibling route (`/settings/profile`, `/settings/2fa`, `/settings/sessions`). No shared layout component between `/settings` and its children (so `/settings/2fa` continues to render `Settings2faPage` as a full-page component, not as a tab body). User-menu in `TopBar.tsx` gains a "Settings" link routing to `/settings`.
- **Alternatives rejected:**
  - Route-layout wrapper (`/settings/_layout.tsx` with persistent sidebar nav) — over-engineering for three sections; couples sibling layouts that have distinct content needs (2FA enrollment flow has wizard-style steps; sessions has table; profile has form).
  - Tab-style navigator (one route, three tab panels) — breaks deep-link semantics; current direct URL `/settings/2fa` would either need a query-param shim or break existing 2FA enrollment links from notifications/emails.
- **Rationale:** simplest topology that solves discoverability. Cards-on-landing is consistent with the existing `/admin` admin landing pattern (Init 5 E8). Three sections is the project's complete settings surface for the near term; future additions (notification preferences, API tokens, etc.) follow the same card-add pattern.
- **Cascading:** none. No new shared components, no schema changes, no new backend endpoints required for the hub itself (children's endpoints already exist).
```

#### 4.2.2 Architecture § Initiative 8 — Catalog Mobile & Image Performance

```markdown
## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Brownfield additive — thumbnail pipeline on Init 0 catalog read-surface. Source SCP: `sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 8" (FR8-* + NFR8-*). Single Epic E13 with 2 stories.

### Overview

Initiative 8 introduces an image transformation layer between the existing `portal-content` volume binary storage and the `/api/models/.../content` read endpoint. The pipeline is on-upload (deterministic, cacheable, no per-request CPU spike) rather than on-the-fly. The variant is served via query param on the existing endpoint (no new route prefix, no nginx changes). Decision P below documents the pipeline shape, format/quality choice, and backfill posture.

### Decisions In-Scope (P)

#### Decision P — On-upload thumbnail pipeline, WebP @ q80, 800px longest side, query-param variant

- **Realizes:** FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1.
- **Choice:** thumbnail generation triggered as an arq task enqueued from the admin model-file create endpoint when the uploaded file's kind is `image`. Task runs in the existing `apps/api/app/workers/__init__.py` `WorkerSettings` (NOT the dedicated render worker — thumbnails are I/O-light Pillow CPU and don't warrant the matplotlib-heavy render-worker isolation). Output filename convention: `<original-filename>.thumb.webp` co-located with original in `portal-content`. The asset content endpoint `GET /api/models/{model_id}/files/{file_id}/content` accepts an optional `variant=thumb` query param; when present and the thumbnail file exists, serves the WebP variant; when absent, serves original. Frontend catalog cards request via `srcSet` with `?variant=thumb`. Detail view continues to request full-res original (no srcSet).
- **Backfill:** one-shot script `infra/scripts/backfill-thumbnails.sh` walks `ModelFile` rows of `kind=image` AND missing thumbnail, enqueues the same arq task per row. Operator-supervised (not part of `deploy.sh` automation). Idempotent (skip if thumbnail already exists).
- **Alternatives rejected:**
  - On-the-fly thumbnail generation (resize per request) — per-request CPU spike, harder to cache, defeats the latency-budget benefit.
  - New dedicated `workers/thumbnail/` sibling worker — over-engineering for a thin Pillow task; the existing arq worker has spare cycles.
  - JPEG @ q85 instead of WebP @ q80 — WebP gives 25-35% smaller files at equivalent visual quality; JPEG fallback unnecessary for the project's user base per NFR8-COMPAT-1.
  - Separate thumbnail endpoint `/api/models/.../thumb` — query-param variant keeps the existing route shape and avoids nginx config touches.
- **Rationale:** simplest pipeline that hits NFR8-PERF-1's 50 KB payload budget for typical phone-photo inputs. On-upload is deterministic and cache-friendly. Query-param variant rides existing route + middleware + auth posture (no new public route, no `_PUBLIC_ROUTES` allowlist change — preserves Init 6 default-deny).
- **Cascading:** Pillow ≥11 must be in `apps/api/pyproject.toml` (verify during Story 13.2 spec; per project-context.md L24 it's confirmed in worker but not necessarily API). Backfill script must be run once post-Story-13.2-deploy by operator. No nginx, no auth, no schema changes.
```

#### 4.2.3 Architecture § Initiative 9 — Test Isolation Cleanup (pointer-only)

```markdown
## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Brownfield test-infrastructure cleanup. Source SCP: `sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 9" (FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1). Single Epic E14 with 3 stories.

### Overview

Initiative 9 is test-infrastructure-only work. **No new architectural decisions, no product-architecture changes, no schema changes, no auth contract changes.** Init 0–6 product architecture is load-bearing for the fixes; Initiative 9 does not modify it.

The three stories operate within existing test-infrastructure contracts:

- **Story 14.1** operates within the vitest + @testing-library/react contract documented at `apps/web/vitest.setup.ts` (global `afterEach(cleanup)`) and `apps/web/vitest.config.ts` (jsdom env, `globals: false`). No contract changes.
- **Story 14.2** operates within the pytest + SQLModel + fakeredis contract documented at `apps/api/tests/conftest.py` (`_isolated_db`, `_patch_arq_pool`). Story 14.2 may tighten fixture scoping or add explicit teardowns, but does NOT modify the broader test isolation architecture.
- **Story 14.3** operates within the husky + playwright + check-all.sh contract documented at `apps/web/.husky/_check-baseline-review.mjs` + `_check-visual-coverage.mjs` and the visual-regression Playwright config at `apps/web/tests/visual/playwright.config.ts`. Story 14.3 may add instrumentation logging or fix a port/SHA/cache divergence, but does NOT modify the baseline-acceptance gate or visual-coverage contract.

This section is listed in the architecture document for Initiatives Index completeness; there are no design decisions to record.
```

### 4.3 Epics extension — Initiative 7 + Initiative 8 + Initiative 9 H2 sections

Append the following to `_bmad-output/planning-artifacts/epics.md`. Project-global epic numbering continues: Init 7 = E12, Init 8 = E13. Story numbering is `<epic>.<local>` per project-context.md L210 convention.

#### 4.3.1 Epics § Initiative 7

```markdown
## Initiative 7 — Account & Admin UX Polish

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 7" (FR7-ADMIN-INVITES-1..3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1..2, FR7-SESSIONS-1..2 + NFR7-UX-1, NFR7-A11Y-1, NFR7-COMPAT-1). Source architecture section: `architecture.md` § "Initiative 7" (Decision Q). Single Epic E12 with 5 stories.

**Init 5 + 6 unchanged.** Initiative 7 is purely additive polish on shipped surfaces. No Init 5/6 epic retro-modification.

### Overview

Single epic E12 with 5 stories. Sequence: 12.1 (Admin Invites unblock — nav tab + translations + table layout) → 12.2 (Admin Users inactive-filter) → 12.3 (Display name on registration + self-service edit) → 12.4 (Settings hub + 2FA discoverability + user-menu link) → 12.5 (Sessions UX — pagination + sort + UA-filter). Stories 12.3 and 12.4 share the new `/settings/profile` route surface (12.3 creates it, 12.4 wires the hub link); 12.3 → 12.4 sequencing is recommended but not strict.

Each story carries NFR7-UX-1 (pre-CR visual verification gate) as a mandatory non-functional acceptance criterion.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E12 | Account & Admin UX Polish | 5 (12.1–12.5) | Medium | Low (no security boundary, no schema risk; mostly component-level changes on shipped surfaces) | FR7-ADMIN-INVITES-1..3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1..2, FR7-SESSIONS-1..2 + NFR7-UX-1, NFR7-A11Y-1, NFR7-COMPAT-1 | none (entry epic for Init 7) |

**Total: 5 stories.** Effort estimate: 2–3 days back-to-back autonomous execution (~½–1 day per story, faster than Init 6 auth-boundary stories due to lower risk profile).

### Epic 12 — Account & Admin UX Polish

**Goal.** Raise five user-facing surfaces (admin invites, admin users, registration, settings discoverability, active sessions) from minimum-viable to operator-acceptable UX. Bake in the new pre-CR visual-verification gate as a procedural fix for the Init 6 admin-invites shipping incident class.

**Acceptance gate.**

1. `/admin/invites` nav tab is enabled for admin role; clicking it routes to the existing page; page renders complete pl/en translations; table fits viewport at desktop default and mobile-light.
2. `/admin/users` defaults to `is_active=true` rows; "Pokaż nieaktywne konta" checkbox toggle shows all rows.
3. Registration form has optional display-name field with auto-suggest from email prefix; backend accepts display_name; `/settings/profile` allows self-service edit.
4. `/settings` hub exists with three section entries (Profile, 2FA, Sessions); user-menu in TopBar has "Settings" link.
5. `/settings/sessions` paginates at default 20/page, sorts by `last_used_at DESC` default, has "Pokaż API/non-browser sesje" checkbox toggle (default OFF — filters curl/non-browser UA patterns).
6. Each story (12.1–12.5) has agent-browser snapshots at desktop-default + mobile-light viewports attached to Dev Agent Record.

**FRs realized:** FR7-ADMIN-INVITES-1, FR7-ADMIN-INVITES-2, FR7-ADMIN-INVITES-3, FR7-ADMIN-USERS-1, FR7-REG-DISPLAY-1, FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2, FR7-SESSIONS-1, FR7-SESSIONS-2.

**Architectural anchors:** Decision Q (Initiative 7 — settings hub topology).

**Blocked by:** none. Operator-confirmed business intent (display name option A; default-OFF inactive filter; default-OFF API/non-browser session filter). Other technical choices ITCM-delegated.

##### Story 12.1 — Admin Invites unblock (nav tab + translations + table layout)

**Realizes:** FR7-ADMIN-INVITES-1, FR7-ADMIN-INVITES-2, FR7-ADMIN-INVITES-3, NFR7-UX-1.
**Architectural anchor:** none (component-level).
**Depends on:** none (E12 entry story).

Acceptance check shape:

- `apps/web/src/modules/admin/AdminTabs.tsx`: invites entry changes from `<span aria-disabled="true" cursor-not-allowed opacity-50>` to a `<Link to="/admin/invites">` with the same styling as other admin tabs.
- `apps/web/src/locales/pl.json` + `apps/web/src/locales/en.json`: full key set for admin invites page added (key list enumerated during spec phase by reading the existing `InvitesPage.tsx` + child components and pulling every `t("admin.invites.*")` call). Parity between pl and en.
- Admin invites table layout: max-width on container, left-margin compressed to match other admin pages, horizontal scroll if needed for mobile viewport.
- Visual smoke per NFR7-UX-1: agent-browser snapshot at desktop-default + mobile-light. Verify nav-tab enabled, no raw i18n keys, table fits.

##### Story 12.2 — Admin Users inactive-filter (default-hide + checkbox toggle)

**Realizes:** FR7-ADMIN-USERS-1, NFR7-A11Y-1 (checkbox keyboard reach).
**Architectural anchor:** none.
**Depends on:** 12.1 (sequential preference — both in admin module, easier to review together) OR none (technically independent).

Acceptance check shape:

- `apps/web/src/modules/admin/UsersPage.tsx`: add `is_active` filter state, default `true`. Add checkbox below page header: "Pokaż nieaktywne konta" / "Show inactive accounts", default unchecked. Checked → query without `is_active` filter (returns all). Unchecked → query with `is_active=true`.
- Backend: verify `apps/api/app/modules/admin/router.py` users-list endpoint accepts `is_active` query param. If not, extend (small change — likely adds `is_active: bool | None = None` to existing query).
- Inactive rows when shown: muted visual style (e.g. text-muted-foreground theme token).
- Visual smoke per NFR7-UX-1.

##### Story 12.3 — Display name on registration + self-service edit

**Realizes:** FR7-REG-DISPLAY-1, NFR7-A11Y-1.
**Architectural anchor:** none (the new `/settings/profile` route is component-level under Decision Q's hub topology).
**Depends on:** none.

Acceptance check shape:

- Registration form (path TBD during spec — likely `apps/web/src/routes/auth/register.tsx`): add optional `display_name` text field below email. On email blur, populate display-name field with email prefix if empty.
- Backend `POST /api/auth/register`: accept optional `display_name` in request body; if absent, fall back to email prefix server-side.
- New route `apps/web/src/routes/settings/profile.tsx`: form to edit display_name. PATCH (or PUT) to a new endpoint `PATCH /api/auth/me/display-name` (or extend existing self-service user endpoint if exists). Auth: `current_user`.
- Verify `User.display_name` field already exists in `apps/api/app/core/db/models.py`. If not, add Alembic migration.
- Visual smoke per NFR7-UX-1.

##### Story 12.4 — Settings hub + 2FA discoverability + user-menu link

**Realizes:** FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2, NFR7-A11Y-1.
**Architectural anchor:** Decision Q.
**Depends on:** 12.3 (sequential — 12.3 creates `/settings/profile`, 12.4 wires the hub link to it). If 12.3 not yet shipped, 12.4 can ship the hub with only 2FA + Sessions entries and add Profile entry in a follow-up.

Acceptance check shape:

- New route `apps/web/src/routes/settings/index.tsx`: hub landing with three cards (Profile, 2FA, Sessions). Each card has i18n title + brief description (i18n key set added to pl/en).
- `apps/web/src/shell/TopBar.tsx` (or wherever user-menu lives): add "Settings" entry to user-menu dropdown, routing to `/settings`. i18n key added.
- Anonymous user redirect: `/settings` is shell-AuthGate protected per Init 6 FR6-SHELL-1 (no change needed in this story — already covered).
- Visual smoke per NFR7-UX-1 — emphasis on user-menu visibility and hub landing render.

##### Story 12.5 — Sessions UX (pagination + sort + UA-filter)

**Realizes:** FR7-SESSIONS-1, FR7-SESSIONS-2, NFR7-A11Y-1.
**Architectural anchor:** none.
**Depends on:** none (technically independent of 12.4).

Acceptance check shape:

- `apps/web/src/routes/settings/sessions.tsx`: wire `offset` + `limit` query params to existing `/api/auth/sessions` endpoint (backend already accepts them). Page-size selector (default 20, options 10/20/50). Prev/next page controls. Total-count indicator.
- Sort: default `last_used_at DESC`. Backend may already do this; verify during spec.
- UA-filter checkbox "Pokaż API/non-browser sesje" / "Show API/non-browser sessions". Default OFF. Filter pattern: TBD during spec — likely a list of substrings (e.g. `curl/`, `python-requests/`, `httpie/`, `wget/`, `Go-http-client/`, plus check for absence of common browser markers like `Mozilla/`, `Chrome/`, `Safari/`). Filter applied client-side OR server-side — TBD during spec.
- Visual smoke per NFR7-UX-1.

### Cross-references

- PRD: `prd.md` § Initiative 7.
- Architecture: `architecture.md` § Initiative 7 (Decision Q).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-12.
```

#### 4.3.2 Epics § Initiative 8

```markdown
## Initiative 8 — Catalog Mobile & Image Performance

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 8" (FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1..3 + NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1). Source architecture section: `architecture.md` § "Initiative 8" (Decision P). Single Epic E13 with 2 stories.

**Init 0 + 5 + 6 unchanged.** Initiative 8 is purely additive — catalog read-surface UX polish + new thumbnail pipeline layer.

### Overview

Single epic E13 with 2 stories. Sequence: 13.1 (Mobile carousel arrows — small CSS fix) → 13.2 (Thumbnail pipeline — backend pipeline + endpoint + frontend srcSet + backfill script). 13.1 is faster ship-day-1; 13.2 is the bigger cross-cutting story.

Each story carries NFR8-UX-1 (pre-CR visual verification gate). Story 13.2 also has NFR8-PERF-1 backend payload-size budget.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E13 | Catalog Mobile & Image Performance | 2 (13.1, 13.2) | Medium-Low | Low (no security boundary; Pillow is well-trodden) | FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1 | none (entry epic for Init 8) |

**Total: 2 stories.** Effort estimate: 1–2 days back-to-back autonomous execution (13.1 is hours; 13.2 is ~1 day with backend + frontend + backfill + tests).

### Epic 13 — Catalog Mobile & Image Performance

**Goal.** Make catalog list-page usable on mobile (visible carousel arrows) and bandwidth-friendly (thumbnail variants instead of full-res 8K photos). Establish the thumbnail pipeline as future-extensible (variant param can grow to cover other size targets if needed).

**Acceptance gate.**

1. Catalog list page on mobile (≤sm breakpoint) shows prev/next arrow buttons on each card carousel; desktop hover behavior preserved.
2. Image-kind file upload generates `.thumb.webp` variant within 30s; thumbnail file size ≤50 KB for typical phone photos.
3. `GET /api/models/{model_id}/files/{file_id}/content?variant=thumb` returns thumbnail; same request without variant returns original.
4. Catalog cards request thumbnails via srcSet; detail view requests full-res.
5. Backfill script processes existing image-kind files without thumbnail, skips files that already have one (idempotent).
6. Each story has agent-browser snapshots at desktop + mobile viewports.

**FRs realized:** FR8-CAROUSEL-MOBILE-1, FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3.

**Architectural anchors:** Decision P (Initiative 8 — thumbnail pipeline shape).

**Blocked by:** none. ITCM technical decisions ratified by operator delegation 2026-05-21.

##### Story 13.1 — Mobile carousel arrows always-visible at ≤sm breakpoint

**Realizes:** FR8-CAROUSEL-MOBILE-1, NFR8-UX-1.
**Architectural anchor:** none (CSS-only change).
**Depends on:** none.

Acceptance check shape:

- `apps/web/src/ui/custom/CardCarousel.tsx`: arrow button classes change from `opacity-0 group-hover:opacity-100 ...` to `sm:opacity-0 sm:group-hover:opacity-100 ...` (Tailwind v4 `sm:` prefix applies above sm-breakpoint; below sm-breakpoint = mobile = always visible).
- `apps/web/src/modules/catalog/components/ModelGallery.tsx`: same pattern applied to its arrow buttons.
- Verify the existing CardCarousel.test.tsx tests still pass (5/5 per QD-3 close-out 2026-05-10) — likely no test changes needed since the change is purely CSS.
- Playwright visual-regression baselines update for catalog list at mobile-light + mobile-dark (per project-context.md L110 4-project matrix). Baseline-reviewed lines per pre-commit hook contract.
- Visual smoke per NFR8-UX-1 — emphasis on mobile-light (the new visible-arrows behavior).

##### Story 13.2 — Thumbnail pipeline (on-upload + variant endpoint + srcSet + backfill)

**Realizes:** FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1.
**Architectural anchor:** Decision P.
**Depends on:** none (technically) but ship after 13.1 to keep the smaller visual change separate from the bigger backend change.

Acceptance check shape:

**Backend (Pillow integration):**

- `apps/api/pyproject.toml`: verify Pillow ≥11 present; if not, add (worker already has it per project-context.md L24).
- `apps/api/app/workers/__init__.py`: new arq task `generate_thumbnail(model_file_id: int)` that loads the original file, generates 800px-longest-side WebP @ q80 via Pillow, saves as sibling `<original-filename>.thumb.webp` in `portal-content`.
- `apps/api/app/modules/admin/router.py` model-file create endpoint (image kind): on successful file save, enqueue `generate_thumbnail(file.id)`. Verify by integration test that thumbnail file appears on disk after task runs.
- `apps/api/app/modules/sot/router.py` GET content endpoint: accept `variant: str | None = Query(None)` query param; when `variant == "thumb"` and thumbnail file exists, serve thumbnail (Content-Type: image/webp); when thumbnail missing OR variant absent, serve original.
- `apps/api/tests/test_thumbnail_pipeline.py` (NEW): unit tests for thumbnail generation (size budget per NFR8-PERF-1), integration tests for upload → enqueue → thumbnail file presence, endpoint tests for variant routing.

**Frontend (srcSet):**

- `apps/web/src/modules/catalog/components/ModelGallery.tsx` (and any catalog-card image-srcing site): render `<img>` with both `src` (thumbnail URL with `?variant=thumb`) and `srcSet` for retina (`?variant=thumb` @ 1x, full URL @ 2x — OR adjust based on what the spec phase determines is the right multiplier strategy).
- Catalog-detail page (model-page large image): continues to use full-resolution original, no srcSet.

**Backfill:**

- `infra/scripts/backfill-thumbnails.sh`: bash script that connects to API (using existing agent credentials or admin token from `.env`), queries `/api/models?include_files=true` (or equivalent listing endpoint), filters to image-kind files without thumbnails, enqueues `generate_thumbnail` for each via admin endpoint OR direct arq enqueue.
- Idempotent: re-running the script skips files that already have thumbnails.
- Run once post-deploy by operator (not automated in `deploy.sh`).

**Visual smoke per NFR8-UX-1:** catalog list page at desktop + mobile, model-detail at desktop + mobile. Verify catalog cards render quickly with thumbnail-sized payloads; detail view still uses full-res.

### Cross-references

- PRD: `prd.md` § Initiative 8.
- Architecture: `architecture.md` § Initiative 8 (Decision P).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-13.
```

#### 4.3.3 Epics § Initiative 9

```markdown
## Initiative 9 — Test Isolation Cleanup

**Status:** 🚧 planning (started 2026-05-21). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md`. Source PRD section: `prd.md` § "Initiative 9" (FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1). Source architecture section: `architecture.md` § "Initiative 9" (pointer-only — no architectural decisions). Single Epic E14 with 3 stories.

**Init 5 + 6 + product architecture unchanged.** Initiative 9 is test-infrastructure-only work.

### Overview

Single epic E14 with 3 stories. Sequence: 14.1 (vitest admin finders) → 14.2 (pytest hydrate pollution) → 14.3 (visual-regression hook flake). 14.1 + 14.2 can also run in parallel since they touch distinct frameworks; sequencing them gives cleaner Codex review boundaries. 14.3 begins with an instrumentation pass before fixing.

Each story carries NFR9-DETERMINISM-1 (≥3 consecutive successful runs of the affected test suite). NFR7-UX-1 / NFR8-UX-1 visual-verification gate does NOT apply (no rendered UI surface in any of these stories).

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E14 | Test Isolation Cleanup | 3 (14.1, 14.2, 14.3) | Low-Medium | Low (test-only; no production-code touches per NFR9-SCOPE-1) | FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1 + NFR9-DETERMINISM-1, NFR9-SCOPE-1 | none (entry epic for Init 9; scheduled FIRST in this SCP's execution chain) |

**Total: 3 stories.** Effort estimate: ~½–1 day back-to-back autonomous execution. 14.1 + 14.2 are bounded (hours each — known surfaces, known fix shapes). 14.3 has investigation-time variance (instrumentation pass → root cause → fix → verify) — pessimistic estimate ~4-8h.

### Epic 14 — Test Isolation Cleanup

**Goal.** Close three test-infrastructure isolation gaps that pre-date Init 5+6 and would interfere with Init 7+8 story development. Establish NFR9-DETERMINISM-1 as the test-infrastructure analog of the UI visual-verification gate.

**Acceptance gate.**

1. `npm run test apps/web/src/modules/admin/` returns 0 failures across all 5 affected files; verified by 3 consecutive runs.
2. `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` returns PASS deterministically across 10 consecutive invocations (in this exact order).
3. `infra/scripts/check-all.sh` visual stage and standalone `npx playwright test --config=tests/visual/playwright.config.ts` produce identical pass/fail verdict across the full baseline set, 3 consecutive runs in each context.
4. Each story's Dev Agent Record logs the 3-consecutive-run verification per NFR9-DETERMINISM-1.

**FRs realized:** FR9-VITEST-ADMIN-1, FR9-PYTEST-HYDRATE-1, FR9-VISUAL-HOOK-1.

**Architectural anchors:** none (test-infrastructure only).

**Blocked by:** none. Operator scope-pull 2026-05-21 promoted these from triage.

##### Story 14.1 — Vitest admin module finder fixes (18 failures → 0)

**Realizes:** FR9-VITEST-ADMIN-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (entry story).

Acceptance check shape:

- Identify the 18 failing tests across `apps/web/src/modules/admin/InvitesPage.test.tsx`, `GenerateInviteModal.test.tsx`, `InviteTokenDisplayModal.test.tsx`, `ResetLinkDisplayModal.test.tsx`, `UsersPage.test.tsx`. Capture failure log per test (text mismatch, role mismatch, label mismatch, missing element, etc.).
- For each failure: regenerate the finder against current i18n + DOM shape. Test-only change. If a finder reveals what looks like a real component bug (e.g. accessible-name regression in the component itself), STOP and surface to operator per NFR9-SCOPE-1.
- Verify: `npm run test apps/web/src/modules/admin/` returns 0 failures, 3 consecutive runs.
- Per-file afterEach(cleanup) audit per memory [[feedback_vitest_manual_cleanup]] — note: since commit a026e97 (global `vitest.setup.ts`), per-file afterEach is redundant; if any of the 5 affected files still has per-file boilerplate, leave it (harmless), don't introduce new ones.

##### Story 14.2 — Pytest hydrate DB-pollution isolation close

**Realizes:** FR9-PYTEST-HYDRATE-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 14.1).

Acceptance check shape:

- Reproduce: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in this order fails on `test_hydrate_creates_local_tree`; running `test_hydrate_creates_local_tree` alone passes. Confirm via 3 consecutive reproductions.
- Investigate `apps/api/tests/conftest.py`: `_isolated_db` is session-scoped per L96-97 in project-context.md. Check whether FAKE_STL_PAYLOAD_AAA is committed via a fixture that should be function-scoped, OR whether the test commits explicitly without rollback, OR whether the `/api/models` listing in hydrate scans the DB without filtering by something the FAKE seed lacks (e.g. soft-delete marker).
- Fix: tighten isolation. Probable shapes:
  - Convert offending fixture to function-scoped + add explicit teardown.
  - Add explicit DB rollback at test exit in the offending test.
  - Add explicit filter in `/api/models` listing or in `test_hydrate_creates_local_tree`'s expectations.
- Verify: `timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in order returns PASS deterministically, 10 consecutive runs (per FR9-PYTEST-HYDRATE-1 verification clause).
- Always wrap pytest in `timeout 600` per memory [[feedback_pytest_timeout]] — investigation runs should not become zombie-pytest sessions.

##### Story 14.3 — Visual-regression hook-context flake (admin-invites + admin-users baselines)

**Realizes:** FR9-VISUAL-HOOK-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1.
**Architectural anchor:** none.
**Depends on:** none (independent of 14.1, 14.2).

Acceptance check shape:

**Phase 1 — Instrumentation pass (no fix yet):**

- Add temporary logging to `infra/scripts/check-all.sh` (or wherever the visual stage entry is) capturing: the actual port the Playwright dev-server binds to, the build SHA being tested, the working directory at visual-stage entry, the env vars present (filtered to relevant ones — `PORT`, `VITE_*`, `NODE_ENV`, etc.).
- Reproduce hook-context failure on admin-invites + admin-users baselines. Capture the log output.
- Reproduce standalone-context pass on same baselines. Capture the standalone log output.
- Diff the two logs. Pin the divergence (port collision, SHA drift, env-var leak, etc.).

**Phase 2 — Fix (informed by Phase 1):**

- Apply the targeted fix at the divergence point. Could be one of: explicit port allocation in `check-all.sh` to avoid collision; explicit build artifact directory for visual stage; explicit env-var unset/set in the hook chain; or a Playwright config tweak.
- Per [[feedback_visual_failure_mode_triage]]: grep the failure log for snapshot vs timeout vs strict-mode-violation breakdown BEFORE deciding on `--update-snapshots`. Hook flake is likely NOT a baseline-snapshot issue; do not regen baselines as the fix.

**Phase 3 — Verify per NFR9-DETERMINISM-1:**

- 3 consecutive `infra/scripts/check-all.sh` runs → identical pass/fail verdict across full baseline set.
- 3 consecutive standalone Playwright runs → identical pass/fail verdict across full baseline set.
- Hook-context and standalone-context verdicts match.

**Phase 4 — Remove instrumentation logging** added in Phase 1 (or convert to permanent diagnostic log gated behind `DEBUG=1` env var per project-context.md L59 logging contract).

### Cross-references

- PRD: `prd.md` § Initiative 9.
- Architecture: `architecture.md` § Initiative 9 (pointer-only).
- SCP: `sprint-change-proposal-2026-05-21.md` (this batch's SCP).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` § epic-14.
- Memory entries informing this epic: [[feedback_preexisting_issue_threshold]], [[feedback_vitest_manual_cleanup]], [[feedback_pytest_timeout]], [[feedback_visual_failure_mode_triage]].
```

### 4.4 Sprint-status extension — epic-14 + epic-12 + epic-13 entries

Append the following to `_bmad-output/implementation-artifacts/sprint-status.yaml`. All three epics start with `backlog` status on all stories; status flips to `in_progress` → `dev_complete` → `review` → `merged` → `done` per Init 5/6 precedent. **Append order in sprint-status.yaml: epic-14 → epic-12 → epic-13**, mirroring execution scheduling (Init 9 first).

```yaml
# ─── Epic 14: Test Isolation Cleanup (Initiative 9) ───
# Added 2026-05-21 by sprint-change-proposal-2026-05-21.md (status TBD pending operator approval).
# Initiative 9 in _bmad-output/planning-artifacts/{prd,architecture,epics}.md.
# Sequencing within Init 9: 14.1 → 14.2 → 14.3 (or 14.1 ‖ 14.2 in parallel; 14.3 starts with instrumentation phase).
# Scheduled FIRST in this SCP's execution chain to unblock Init 7 + Init 8 test surfaces.
# Each story carries NFR9-DETERMINISM-1 (≥3 consecutive successful test-suite runs).
# NFR7-UX-1 / NFR8-UX-1 visual-verification gate does NOT apply (test-infrastructure only).
# Promotion source: TB-018 entry in _bmad-output/triage-backlog.md, promoted via operator scope-pull mid-SCP-review 2026-05-21.

epic-14:
  name: Test Isolation Cleanup
  initiative: 9
  status: backlog
  stories:
    14.1:
      title: Vitest admin module finder fixes (18 failures → 0)
      status: backlog
      depends_on: []
      frs: [FR9-VITEST-ADMIN-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1]
    14.2:
      title: Pytest hydrate DB-pollution isolation close
      status: backlog
      depends_on: []
      frs: [FR9-PYTEST-HYDRATE-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1]
    14.3:
      title: Visual-regression hook-context flake (admin-invites + admin-users baselines)
      status: backlog
      depends_on: []
      frs: [FR9-VISUAL-HOOK-1, NFR9-DETERMINISM-1, NFR9-SCOPE-1]

# ─── Epic 12: Account & Admin UX Polish (Initiative 7) ───
# Added 2026-05-21 by sprint-change-proposal-2026-05-21.md (status TBD pending operator approval).
# Initiative 7 in _bmad-output/planning-artifacts/{prd,architecture,epics}.md.
# Sequencing within Init 7: 12.1 → 12.2 → 12.3 → 12.4 (depends on 12.3) → 12.5.
# Each story carries NFR7-UX-1 mandatory pre-CR agent-browser visual verification.

epic-12:
  name: Account & Admin UX Polish
  initiative: 7
  status: backlog
  stories:
    12.1:
      title: Admin Invites unblock (nav tab + translations + table layout)
      status: backlog
      depends_on: []
      frs: [FR7-ADMIN-INVITES-1, FR7-ADMIN-INVITES-2, FR7-ADMIN-INVITES-3, NFR7-UX-1]
    12.2:
      title: Admin Users inactive-filter (default-hide + checkbox toggle)
      status: backlog
      depends_on: []
      frs: [FR7-ADMIN-USERS-1, NFR7-A11Y-1]
    12.3:
      title: Display name on registration + self-service edit
      status: backlog
      depends_on: []
      frs: [FR7-REG-DISPLAY-1, NFR7-A11Y-1]
    12.4:
      title: Settings hub + 2FA discoverability + user-menu link
      status: backlog
      depends_on: [12.3]  # 12.3 creates /settings/profile; 12.4 wires hub link
      frs: [FR7-SETTINGS-HUB-1, FR7-SETTINGS-HUB-2, NFR7-A11Y-1]
    12.5:
      title: Sessions UX (pagination + sort + UA-filter)
      status: backlog
      depends_on: []
      frs: [FR7-SESSIONS-1, FR7-SESSIONS-2, NFR7-A11Y-1]

# ─── Epic 13: Catalog Mobile & Image Performance (Initiative 8) ───
# Added 2026-05-21 by sprint-change-proposal-2026-05-21.md.
# Initiative 8 in _bmad-output/planning-artifacts/{prd,architecture,epics}.md.
# Sequencing within Init 8: 13.1 → 13.2 (recommended ship-13.1-first ordering).
# Each story carries NFR8-UX-1 mandatory pre-CR agent-browser visual verification.
# 13.2 also has NFR8-PERF-1 backend payload-size budget (≤50 KB thumbnail).

epic-13:
  name: Catalog Mobile & Image Performance
  initiative: 8
  status: backlog
  stories:
    13.1:
      title: Mobile carousel arrows always-visible at ≤sm breakpoint
      status: backlog
      depends_on: []
      frs: [FR8-CAROUSEL-MOBILE-1, NFR8-UX-1]
    13.2:
      title: Thumbnail pipeline (on-upload + variant endpoint + srcSet + backfill)
      status: backlog
      depends_on: []
      frs: [FR8-THUMB-1, FR8-THUMB-2, FR8-THUMB-3, NFR8-PERF-1, NFR8-COMPAT-1, NFR8-UX-1]
```

### 4.5 Triage-backlog updates

- **TB-015** — already updated 2026-05-21 with pinned root cause. On SCP approval, TB-015 moves to status `promoted` and bmad-quick-dev invocation begins (next session, fresh context, per execution flow §3.4).
- **TB-018** — already added 2026-05-21 as carry-forward bundle. **On SCP approval, status flips `candidate` → `promoted` via Initiative 9 (E14).** TB-018 entry stays as historical record; Initiative 9 PRD section + Epic 14 are the authoritative spec going forward. Per-Story-14.x close flips TB-018 sub-items to `done`; TB-018 entry overall flips to `done` when all three stories ship.

### 4.6 No-change artifacts

The following artifacts are explicitly NOT modified by this SCP:

- `_bmad-output/planning-artifacts/prd.md` § Initiative 0–6 — untouched.
- `_bmad-output/planning-artifacts/architecture.md` § Initiative 0–6 — untouched.
- `_bmad-output/planning-artifacts/epics.md` § Initiative 0–6 (E0–E11) — untouched.
- All shipped Story specs in `_bmad-output/implementation-artifacts/` (1-1-* through 11-7-*) — untouched.
- `docs/operations.md`, `docs/architecture.md`, `docs/design/*.md` — untouched (no operations changes; thumbnail pipeline runbook addition deferred to Story 13.2 spec).
- Cross-repo: no sibling configs touched (no edge proxy changes).

---

## Section 5 — Implementation Handoff

### 5.1 Scope classification — Moderate

Per CC checklist §6.4 classification:

- **NOT Minor** — multiple new epics with cross-cutting backend + frontend work (Story 13.2 in particular).
- **Moderate** — backlog reorganization needed (new epics, new stories, new sprint-status entries). Multi-story execution chain with retro per epic.
- **NOT Major** — no PRD MVP revisit, no architectural overhaul, no major timeline impact, no fundamental replan.

### 5.2 Handoff plan

**Routing:** Developer / Product Owner blend, executed in ITCM autonomous mode per memory [[itcm-autonomous-mode]]. The "Product Owner" role is absorbed by the operator's pre-SCP business alignment (display name option A; default-OFF filters; SCP approval); the "Developer" role is the agent chain through subsequent BMAD skills.

**Deliverables:**

1. **This SCP document** (the artifact being delivered now) — operator approval converts status `draft` → `approved`.
2. **TB-015 promotion** — bmad-quick-dev invocation in next session, ship-day-1.
3. **PRD extension** — `bmad-edit-prd` adds Init 7 + Init 8 + Init 9 sections per §4.1 above.
4. **Architecture extension** — manual edit (no `bmad-edit-architecture` skill) per §4.2 above (Init 7 + Init 8 + Init 9 pointer-only).
5. **Epics extension** — manual edit (no `bmad-edit-epics` skill) per §4.3 above.
6. **Sprint-status extension** — manual append per §4.4 above (epic-14 first, then epic-12 + epic-13).
7. **Story chain Epic E14 (FIRST)** — bmad-create-story → bmad-dev-story → bmad-code-review per story (14.1, 14.2, 14.3).
8. **Epic E14 retrospective** — bmad-retrospective at epic close.
9. **Story chain Epic E12** — bmad-create-story → bmad-dev-story → bmad-code-review per story (12.1, 12.2, 12.3, 12.4, 12.5).
10. **Epic E12 retrospective** — bmad-retrospective at epic close.
11. **Story chain Epic E13** — bmad-create-story → bmad-dev-story → bmad-code-review per story (13.1, 13.2).
12. **Epic E13 retrospective** — bmad-retrospective at epic close.
13. **Sprint-status close** — `done` flips for all stories in epic-14 + epic-12 + epic-13; SCP status flips to `shipped`.

**Success criteria for implementation:**

- All 10 stories merged with their respective FR/NFR acceptance criteria met.
- Each Story 12.1–13.2 has agent-browser visual smoke attached to its Dev Agent Record (NFR7-UX-1 / NFR8-UX-1 gate).
- Each Story 14.1–14.3 has 3-consecutive-run determinism verification logged in its Dev Agent Record (NFR9-DETERMINISM-1 gate).
- TB-015 closed via bmad-quick-dev with measurement-clear verified hands-on in agent-browser.
- TB-018 closed via Initiative 9 (all three sub-items resolved through Stories 14.1, 14.2, 14.3).
- Codex code-review pass per story (no P1 findings, or P1 findings addressed in follow-up commit).
- Backfill script (Story 13.2) run by operator post-deploy; verification that existing image-kind files now have thumbnails.
- All three epic retrospectives produced and surfaced.

### 5.3 Token-budget posture and pause-policy

Per memory [[feedback_autonomous_sleep_on_budget]]:

- **Current state (SCP creation + revision, 2026-05-21):** 5h 22%, 7d 74%, extra usage off, no opt-in.
- **Comfortable for Init 9** (3 test-only stories, ~½–1 day, low per-story budget). Likely fits in current 5h window.
- **Comfortable for Init 7** (5 stories, ~2–3 days). May straddle one 5h boundary; unlikely to hit week boundary.
- **Init 8 risk:** 7d may reach pause threshold before Story 13.2 completes — adding Init 9 ahead of E12/E13 pushes the 7d-exhaustion risk modestly later (test-only stories have lower per-story budget than UI stories). If 7d reaches 95% before Story 13.2 ships, pause at epic-13 entry boundary, surface to operator.
- **No `extra_usage` opt-in.** Standard limit only.

### 5.4 What surfaces during execution (operator-facing escalations)

Per memory [[itcm-autonomous-mode]] surface only:

- **Real product blockers** — e.g. if Pillow integration uncovers a malformed image in `portal-content` that breaks the entire upload path, surface for operator decision.
- **Initiative-level completion** — at Epic E12 retro close and at Epic E13 retro close, surface summary + next routing.
- **Token-budget pause** — at 5h ≥ 80% or 7d ≥ 95% trigger, surface pause + resume plan.
- **Codex P1 finding loops** — if a story can't pass Codex review after 2 fix-cycles, surface for operator review.
- **Memory-claim verification miss** — if a memory entry referenced during execution turns out to be stale or wrong (per "Before recommending from memory" rule), surface the correction.

No surfacing for: minor technical choices (CSS approach, endpoint signature, test boundaries), Codex P2/P3 findings (handled in fix-up commits), routine deploys, vitest/pytest flakes that resolve on retry, etc.

---

**End of SCP. Status: draft. Awaiting operator approval (yes / no / revise).**
