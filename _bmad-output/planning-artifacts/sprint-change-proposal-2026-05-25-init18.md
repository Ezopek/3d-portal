---
title: "Sprint Change Proposal — Initiative 18 (Share-Flow Membership-Path Completion, Phase A)"
type: sprint-change-proposal
initiative_scope: [18]
status: approved
proposed_by: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode)
proposed_at: 2026-05-25
approved_by: Ezop
approved_at: 2026-05-25
approved_via: |
  AskUserQuestion selection "Approve — ITCM autonomous (recommended)"
  2026-05-25. Operator authorized immediate bmad-create-story chain:
  Story 30.1 first (gpt-5.5 Codex), then Story 30.3 parallel
  (gpt-5.4-mini), then Story 30.2 after 30.1 ships (gpt-5.4-mini).
  Family-time AFK clause per [[feedback_autonomous_sleep_on_budget]]
  active.
execution_directive: |
  Pre-SCP business alignment phase: brainstorming session 2026-05-25-0030
  (4 phases, 23 ideas) + Sally UX recommendation
  (share-flow-membership-path-ux.md, 3 deliverables, 3 operator decisions
  all resolved 2026-05-25). ITCM autonomous mode from
  [[feedback_itcm_autonomous_mode]] does NOT yet apply — this SCP IS the
  business-alignment artifact; operator approval gate is required before
  ITCM kicks in for execution. Post-approval: standard autonomous Phase
  A-F execution; family-time AFK clause per
  [[feedback_autonomous_sleep_on_budget]]. No multi-PR-batch shortcut
  — full BMAD vanilla chain (create-story → dev-story → review →
  retrospective) per [[feedback_vanilla_bmad_first]] +
  [[feedback_default_to_bmad_workflow]].
mode: batch-presented (operator-pragmatic; matches Init 6 / 7+8+9 / 10 /
  11-15 / 16 / 17 SCP precedent — full draft surfaced once, operator
  approve → autonomous execution)
change_scope_classification: moderate  # 1 new initiative, 1 epic, 3 stories, single-Phase scope (Phase B deferred as future-initiative candidate)
related_artifacts:
  - _bmad-output/planning-artifacts/prd.md                         # extend (Initiative 18 H2 — FR18-* + NFR18-*)
  - _bmad-output/planning-artifacts/architecture.md                # extend (Initiative 18 H2 — Decisions AA + AB + AC)
  - _bmad-output/planning-artifacts/epics.md                       # extend (Initiative 18 H2 + Epic E30 — 3 stories)
  - _bmad-output/implementation-artifacts/sprint-status.yaml       # extend (epic-30 + 30-1 / 30-2 / 30-3 entries, status backlog)
  - _bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md   # source brainstorm (locked decisions)
  - _bmad-output/ux/share-flow-membership-path-ux.md               # Sally UX rec (resolved Decisions 1+2+3)
  - ~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_share_view_scope_boundary.md  # AMENDED 2026-05-25 with carve-out (separate edit, completed before SCP draft)
  - _bmad-output/triage-backlog.md                                 # Phase B (anonymous CONTENT parity) registered as future-initiative candidate; no new TB IDs filed by Init 18 itself
predecessor_initiative: 17
trigger:
  source: |
    Post-Init-12 hands-on observation surfaced 2026-05-24: the
    `/share/<token>` feature (shipped through Init 6 + Init 12) was
    designed under the implicit assumption of anonymous-only recipients.
    Real-world usage exposed at least three distinct recipient states
    (no-account-anonymous, has-account-not-logged-in, has-account-logged-
    in-elsewhere) — the system currently treats all three identically,
    producing a degraded experience for the active-session member who
    receives a share link from another member.
  shape: |
    Use-case-enumeration gap from feature inception (not a bug). Fix
    shape: completion of the membership-path decision tree at
    `/share/<token>`, NOT enrichment of the anonymous share-view (that
    surface stays TERMINUS per [[feedback_share_view_scope_boundary]]
    carve-out 2026-05-25). Three stories: backend authenticated
    resolve branch + return-URL flow; frontend conditional render +
    `MemberShareView` + dismissible info-bar; frontend share-view chrome
    additions (Sign in + LangToggle + ThemeToggle). Phase B (anonymous
    CONTENT parity — description placement, multi-STL listing,
    fullscreen viewer for anonymous) deferred as future-initiative
    candidate.
  evidence_class: |
    Direct operator observation 2026-05-24 + structured brainstorming
    session 2026-05-25-0030 (4 phases, 23 scenarios across one
    intent-blind path α; Path β killed at Phase 1) + Sally UX
    recommendation (`share-flow-membership-path-ux.md`, 3 deliverables,
    cross-pollination against Nextcloud / Pixieset / Google Docs /
    Notion / Figma / GitHub patterns). All three operator decisions
    (Sign in carve-out / Lang+Theme toggles / info-bar dismissal scope)
    resolved 2026-05-25 in Sally's doc before correct-course began.
business_decisions_aligned_pre_scp:
  - sender_intent_is_invisible_to_system: |
      Phase 1 lock-in (operator 2026-05-25): single-button SHARE,
      single URL shape (`/share/<token>`). Path β (multi-button SHARE
      with intent declaration at link-generation time) ruled OUT —
      rationale: friends-and-family user base spans tech-comfort
      spectrum (children, grandparents); forcing sender to declare
      share-intent creates avoidable cognitive load + UI complexity.
      Routing decisions are made server-side based on recipient state
      B only, never sender intent A.
  - terminus_policy_carve_out_not_reversal: |
      Sign in affordance + LangToggle + ThemeToggle in share-view
      chrome AND B5 enrich-in-place render are explicitly carved OUT
      of [[feedback_share_view_scope_boundary]] terminus policy as
      "membership-path completion" (NOT share-view enrichment).
      Anonymous share-view CONTENT (layout, carousel, gallery,
      description placement, STL listing, viewer behavior) stays
      UNTOUCHED. Memory amended 2026-05-25 with explicit carve-out
      language (separate edit completed before SCP draft).
  - enrich_in_place_not_redirect: |
      Phase 3 cross-pollination lock-in (Sally 2026-05-25, operator
      Decision 2 approved): B5 render uses Variant γ (canonical
      member catalog UI at `/share/<token>` URL + dismissible info-bar
      pointing at `/catalog/$id`). NOT auto-redirect to `/catalog/$id`.
      Rationale: GitHub / Nextcloud / Google Docs / Notion convention
      strongly prefers enrich-in-place over hard redirect (URL
      stability, bookmark-able, no back-button disorientation,
      brainstorm rα-1 mitigation by design).
  - sign_in_copy_single_string: |
      Sally Deliverable 3 (operator-approved 2026-05-25): single
      "Zaloguj się" / "Sign in" copy for all anonymous recipient
      states (B1/B2/B3/B4). Audience-targeted variants ("Have an
      account? Sign in") implies upselling and clashes with
      friends-and-family tone. Notion / GitHub precedent.
  - info_bar_dismissal_session_storage: |
      Sally Decision 3 (operator-approved 2026-05-25):
      `sessionStorage` key pattern `share-context-dismissed:<modelId>`.
      Per-model + per-session granularity. Next session re-shows
      (assumes user may have forgotten the context). Operator may
      downgrade to `localStorage` in future iteration if telemetry
      shows recipients dismissing repeatedly.
  - phase_b_anonymous_content_parity_deferred: |
      Operator 2026-05-25: anonymous share-view CONTENT parity is
      Phase B work, NOT in Init 18 scope. Tracked as future-initiative
      candidate (would require full reversal — not carve-out — of
      terminus policy + its own brainstorm pass for security/NFR10
      implications). Registered in this SCP § §6.3 as task #4 for
      tracking; no Init 18 story files address it.
recon_subagents_completed: []  # all pre-enumeration done by Claude main session via brainstorming + Sally UX + code grep — no subagent dispatch needed
operator_blockers: []  # none at SCP draft time; Init 17 closed 2026-05-24, no outstanding deploy/verify gates blocking Init 18 start
---

# Sprint Change Proposal — Initiative 18 (Share-Flow Membership-Path Completion, Phase A)

## Section 1 — Issue Summary

### 1.1 Problem statement

The `/share/<token>` feature shipped through Init 6 (share-link
generation) and Init 12 (anonymous share-view content parity with
catalog detail) was designed under an implicit assumption: the recipient
is anonymous (has no portal account). This assumption broke down
post-Init-12 once members started receiving share links from other
members. The system has at least **three distinct recipient states** for
any `/share/<token>` request:

1. **B1/B2** — anonymous (never-visited OR visited-before; system cannot
   reliably distinguish via cookies).
2. **B3/B4** — has account, NOT logged in this browser/session (OR
   logged in a different browser/device; cookies are browser-scoped, so
   B3 and B4 are indistinguishable from the request layer).
3. **B5** — has account, ACTIVE session this browser (detectable via
   the portal session cookie).

Today, every `/share/<token>` request renders the same anonymous
share-view (C1) regardless of recipient state, because the share endpoint
does not consult the session at all. The degraded case is **B5 (active
member receiving a share link from another member)** — they get the
minimal anonymous view instead of their canonical full member experience,
even though they're entitled to it. **B3/B4** (absentee-member) is also
suboptimal: they get the anonymous view with no signal that signing in
would unlock more.

### 1.2 Issue category

**New requirement emerged from feature-inception use-case-enumeration
gap.** Not a bug per se; the existing share-view is correct for B1/B2/B6
recipients and was the only modeled case at inception. The new
requirement is membership-path completion: recognize B3/B4 (provide
affordance) and B5 (provide canonical experience) without altering
anonymous behavior.

### 1.3 Evidence

- **Operator observation 2026-05-24:** real-world usage post-Init-12.
- **Brainstorming session 2026-05-25-0030** (`_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md`):
  4 phases / 23 generated ideas. Phase 1 (Decision Tree Mapping)
  enumerated sender intent × recipient state × system action; Phase 2
  (What-If + Reverse Brainstorming) stress-tested edge cases (α-1
  through α-6, x-1 through x-8, rα-1 through rα-5); Phase 3
  (Cross-Pollination) transferred patterns from Nextcloud / Pixieset /
  iCloud / Google Docs / Notion / Figma / GitHub / Twitter / Spotify;
  Phase 4 synthesized into 3 render modes + 1 deferred (B7).
- **Sally UX recommendation** (`_bmad-output/ux/share-flow-membership-path-ux.md`):
  3 deliverables (placement / B5 enrich-in-place / copy) with
  alternatives evaluated, ASCII mockups, Tailwind classes, i18n keys,
  and code-grounded architectural notes.
- **Code-grounded confirmation 2026-05-25** of architectural facts:
  share route `apps/web/src/routes/share/$token.tsx`; AppShell bypass
  via `_PUBLIC_PATHS` + `/share/` prefix in
  `apps/web/src/shell/AppShell.tsx`; existing TopBar wires
  `ThemeToggle + LangToggle + UserMenu`; existing `member_router.py`
  precedent at `/api/me/share-links` prefix (separate from public
  `/api/share` to preserve credentialless contract).

### 1.4 Why this surfaces now (not at Init 12 close)

Init 12 explicitly capped at anonymous-content-parity per
[[feedback_share_view_scope_boundary]] terminus policy. Member-receiving
share-link was outside the original scope. The 2026-05-24 surfacing is
the canonical
[[feedback_feature_proposal_use_case_enumeration]] precedent —
sender/recipient/state axes should have been enumerated at feature
INCEPTION (Init 0 / Init 6), not post-ship. Init 18 is the corrective
sweep; the feedback memory has been carrying this precedent since
2026-05-24 already.

---

## Section 2 — Impact Analysis

### 2.1 Epic Impact (existing epics)

**No existing epic is invalidated or scope-modified.** Init 12 (Epic 18+
in `epics.md`) shipped its anonymous-content-parity contract; Init 18
work is additive on a separate render branch (B5) + chrome additions
that don't touch anonymous CONTENT. Init 17 (E26+E27+E28+S29.1) closed
2026-05-24 — no overlap.

**One existing epic reaffirmed:** Init 12's Decision Q/R/S/T security
contract on the public `/api/share/<token>/*` family stays UNTOUCHED.
The new authenticated resolve branch lives under a separate prefix
(`/api/me/share-links/<token>/resolve`) per Decision AA — same pattern
as the existing `member_router.py` at `/api/me/share-links` (Story 6.5
precedent).

### 2.2 New Epic — E30 (Share-Flow Membership-Path Completion)

Initiative 18 introduces **one new epic** containing **three stories**:

- **E30 Story 30.1** — Backend authenticated share-resolve endpoint +
  frontend return-URL flow plumbing.
- **E30 Story 30.2** — Frontend conditional render at `/share/<token>` +
  `MemberShareView` component + dismissible info-bar.
- **E30 Story 30.3** — Frontend share-view chrome additions (Sign in
  button + LangToggle + ThemeToggle).

Single-epic shape is appropriate (3 cohesive stories on a single
user-visible flow; matches Init 9 Epic 14 precedent of "small initiative
= single epic"). Stories 30.1 + 30.3 are independent; Story 30.2 depends
on 30.1 (needs the endpoint to resolve model_id).

### 2.3 Artifact Conflict Analysis

| Artifact | Section | Conflict? | Update needed |
|---|---|---|---|
| `prd.md` | New § Initiative 18 H2 | None | EXTEND — add Init 18 section with FR18-* + NFR18-* requirements |
| `architecture.md` | New § Initiative 18 H2 | None | EXTEND — add Init 18 section with Decisions AA + AB + AC |
| `epics.md` | New § Initiative 18 H2 + Epic E30 | None | EXTEND — add Init 18 + E30 with 3 story-stubs |
| `sprint-status.yaml` | New entries `epic-30` + `30-1-*` + `30-2-*` + `30-3-*` | None | EXTEND — append new entries, status `backlog`; flip `epic-30` to `in-progress` when first story is created |
| `apps/web/src/routes/share/$token.tsx` | Add `useAuth()` branch | Existing code: explicit comment "WITHOUT consulting auth" at line 4 | MODIFY — replace the unconditional anonymous render with a `useAuth()`-gated split (B5 → `MemberShareView`, anonymous → existing) |
| `apps/web/src/shell/AppShell.tsx` | `_PUBLIC_PATHS` + `isSharePath` bypass | Existing code: line 60 `if (isSharePath) return <>{children}</>;` unconditionally bypasses TopBar+ModuleRail for `/share/*` | MODIFY — conditional bypass: bypass only when caller is anonymous OR auth is loading; render full chrome when caller is authenticated (Decision AB) |
| `apps/api/app/modules/share/member_router.py` | New endpoint | Existing module: `/api/me/share-links` prefix, currently hosts member's own-share-link listing | EXTEND — add new endpoint `GET /api/me/share-links/<token>/resolve` returning `{model_id, access}` for authenticated callers |
| `apps/api/app/modules/share/router.py` | Public bypass family | NFR10 contract (credentialless `/api/share/<token>/*`) | NO CHANGE — public family stays untouched (Decision AA) |
| `apps/web/src/locales/en.json` + `pl.json` | 5 new i18n keys | None | EXTEND — add `share.view.signin_cta` + `share.view.signin_aria` + `share.member_context.banner` + `share.member_context.open_in_catalog` + `share.member_context.dismiss_aria` per Sally Deliverable 3 |
| `apps/web/tests/visual/*.spec.ts` | New baselines | None | EXTEND — add `share-anonymous-with-signin.spec.ts` (replaces existing share visual baseline regen) + `share-member-enriched.spec.ts` (new) + `share-member-enriched-dismissed.spec.ts` (new); all × 4 projects per project-context.md mandate |
| `apps/api/tests/test_share_member_resolve.py` | New test file | None | CREATE — pytest cases for resolve endpoint: 200 auth happy path, 401 anonymous, 404 invalid-token, 404 expired-token (uniform per token-status-enumeration protection), revoked-token uniformity, deactivated-user case |
| `_PUBLIC_ROUTES` (backend) | Auth allowlist | Existing list per FR6-AUTH-2 + procedural SCP gate | NO CHANGE — new endpoint lives under `/api/me/share-links` which is NOT public; uses standard `current_user` dep |
| `~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_share_view_scope_boundary.md` | Carve-out section | Memory already amended 2026-05-25 BEFORE this SCP | DONE — separate edit completed before SCP draft per operator brief |
| `_bmad-output/triage-backlog.md` | Phase B future-initiative candidate | None | EXTEND — add a "future-initiatives" entry for Phase B (anonymous CONTENT parity) — Init 18 itself files no new TB IDs |

### 2.4 Technical Impact

**Backend:**

- New endpoint adds ~80 LOC to `apps/api/app/modules/share/member_router.py`
  (existing module, single-function addition) + new test file
  ~150 LOC.
- Zero migrations (no schema change).
- Zero new dependencies.
- Zero changes to `_PUBLIC_ROUTES`, public `/api/share/<token>/*`
  endpoints, CSRF middleware, rate-limit scopes, audit registry.
- No new audit-action emission (resolve is read-only; mirror `share`
  read-pattern which does not audit per Init 6 convention).

**Frontend:**

- `apps/web/src/routes/share/$token.tsx`: split into conditional render
  branches; existing anonymous render extracted into named component
  (or kept inline). Net ~30 LOC change to the route file + new
  `MemberShareView.tsx` component ~150 LOC (wraps catalog detail
  component tree + info-bar).
- `apps/web/src/shell/AppShell.tsx`: bypass condition gains
  `&& !auth.isAuthenticated` guard. ~5 LOC change.
- New `ShareMemberContextInfoBar.tsx` component (~80 LOC).
- New `SignInButton.tsx` component (~40 LOC).
- Share-view header gains `<ThemeToggle />`, `<LangToggle />`,
  `<SignInButton />` in a right-aligned control group. ~10 LOC modification
  to the existing `<header>` in `$token.tsx` or extracted into a new
  `ShareHeader.tsx` component.
- 5 new i18n keys per locale (en + pl).
- 3 new Playwright visual baseline specs × 4 projects = 12 new PNGs
  bundled per-story per [[feedback_frontend_visual_verification]] +
  Story 5.13 Baseline Acceptance Gate.
- Existing `share/$token.test.tsx` Vitest file gains coverage for the
  conditional render branch.

**Infra:**

- Zero infra changes. Standard deploy.sh post-merge per
  [[feedback_auto_deploy_dev]].
- Zero env-var additions.
- Zero nginx changes.

---

## Section 3 — Recommended Approach

### 3.1 Path Forward — Option 1 (Direct Adjustment)

**Selected: Direct Adjustment / Hybrid.**

- **Direct Adjustment** in the sense that no existing epic is being
  rolled back, no shipped scope is being reversed, and the MVP (as of
  Init 12 close) is not being redefined.
- **Hybrid** in the sense that this is also a **new epic addition**
  (E30) within an existing PRD scope — the membership-path completion
  is a natural extension of Init 5 (auth + member chrome) + Init 6
  (anonymous share view) + Init 12 (share-view content parity), not a
  pivot.

**Effort estimate:** Medium — 3 stories, ~2-3 commits per story
(implementation + Codex round-1 fix-up if needed + visual baseline regen
bundle).
**Risk level:** Low — boring-tech fix-shape (new endpoint following
existing member_router.py precedent; new component wrapping existing
catalog detail; chrome additions reusing existing toggle components +
new SignInButton); zero new dependencies; zero infra change; well-scoped
single-Phase delivery.

### 3.2 Options not selected

- **Option 2 (Potential Rollback):** N/A — no recently-completed work to
  roll back. Init 17 closed cleanly; Init 12 anonymous-content-parity is
  the correct contract for B1/B2/B6 recipients and stays as-is.
- **Option 3 (PRD MVP Review):** N/A — MVP is not affected. Init 12
  anonymous parity remains the MVP for B1/B2/B6; Init 18 is a scope
  EXTENSION addressing the new requirement, not a scope reduction.

### 3.3 Phase A vs Phase B split (rationale)

**Phase A (this SCP):** membership-path completion via chrome additions
+ B5 enrich-in-place. Three stories, single-Phase delivery.

**Phase B (deferred, tracked as future-initiative candidate):**
anonymous share-view CONTENT parity — description placement parity with
catalog detail, multi-STL listing parity, fullscreen 3D viewer for
anonymous recipients. Deferred because:

1. Would require **full reversal** (not carve-out) of
   [[feedback_share_view_scope_boundary]] terminus policy.
2. Would need its own brainstorm pass for security implications
   (anonymous viewer load, NFR10 throughput cap reach, share-link
   propagation risk via richer surface).
3. No operator-observed pain point for B1/B2 recipients today;
   speculative growth-class work.
4. Phase A delivers the high-value B5 fix immediately without coupling
   to the speculative Phase B work.

**Phase B is NOT cancelled** — it's a future-initiative candidate. If
operator observes B1/B2 recipients hitting content-parity gaps in the
wild (HAR-evidence or direct user feedback), Phase B can be opened as
its own initiative with its own brainstorm + SCP. Until then, no
Init 18 story addresses it.

---

## Section 4 — Detailed Change Proposals

### 4.1 PRD extension (`prd.md` § Initiative 18)

**OLD:** (file ends after Initiative 17 section)

**NEW:** (append at bottom)

```markdown
## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Source SCP:
`sprint-change-proposal-2026-05-25-init18.md` (status `draft-pending-operator-approval`).
Init 18 = post-ship use-case-enumeration-gap correction sweep: the
`/share/<token>` feature shipped under an implicit anonymous-only
recipient assumption. Real recipient population includes
member-with-active-session (B5) who today gets the degraded anonymous
view. Init 18 completes the membership-path decision tree without
touching anonymous share-view CONTENT (per
[[feedback_share_view_scope_boundary]] terminus policy, amended 2026-05-25
with explicit chrome+enrich-in-place carve-out). Single epic E30, three
stories, all P2 (UX-gap, not security/data-integrity class). Phase B
(anonymous CONTENT parity) deferred as future-initiative candidate.

### Overview

Brainstorming session 2026-05-25-0030 + Sally UX recommendation produced
3 render modes for `/share/<token>`:

1. **Anonymous share-view** (B1/B2/B3/B4/B6 — engineering-collapse:
   "session cookie absent OR session cookie invalid"): existing
   share-view, UNCHANGED CONTENT, with new chrome additions
   (LangToggle + ThemeToggle + Sign in button).
2. **Enriched member share-view** (B5 — engineering: "session cookie
   valid + user has access to model"): canonical catalog detail UI at
   `/share/<token>` URL, full member chrome (TopBar + ModuleRail),
   plus dismissible info-bar pointing at `/catalog/$id`.
3. **Request-access page** (B7 — future, granular sharing not yet
   implemented): deferred, no story in Init 18.

### Functional Requirements

- **FR18-SHARE-RESOLVE-1**: New authenticated endpoint
  `GET /api/me/share-links/<token>/resolve` returns
  `{model_id: UUID, access: "granted"}` HTTP 200 for valid token +
  authenticated caller with access to model. **Verifiable:** pytest
  RESOLVE-1 (happy path 200), RESOLVE-2 (401 unauthenticated), RESOLVE-3
  (404 invalid token), RESOLVE-4 (404 expired token, uniform with
  RESOLVE-3 per token-status-enumeration protection), RESOLVE-5 (404
  revoked token, uniform).
- **FR18-SHARE-RESOLVE-2**: The new endpoint MUST NOT change the
  existing `/api/share/<token>/*` public family (NFR10 credentialless
  contract preservation, per [[feedback_share_view_scope_boundary]]
  amended carve-out language). **Verifiable:** pytest CONTRACT-1 (no
  `Depends(current_user)` added to any `/api/share/<token>/*` route
  via grep + endpoint dep introspection).
- **FR18-FE-CONDITIONAL-RENDER-1**: `/share/<token>` route renders
  `MemberShareView` when `useAuth().isAuthenticated === true`,
  `AnonymousShareView` (current behavior) otherwise. **Verifiable:**
  vitest CR-1 + CR-2 + Playwright `share-anonymous-with-signin.spec.ts`
  + `share-member-enriched.spec.ts`.
- **FR18-MEMBER-SHARE-VIEW-1**: `MemberShareView` calls the resolve
  endpoint to obtain `model_id`, then renders the canonical
  `/catalog/$id` component tree (ModelHero + ModelGallery + STL list +
  description + member actions) wrapped in AppShell + TopBar +
  ModuleRail. URL stays `/share/<token>` (no redirect; brainstorm
  rα-1 mitigation by design). **Verifiable:** Playwright
  `share-member-enriched.spec.ts` × 4 projects compares
  `/share/<token>` (auth) vs `/catalog/$id` (auth) — identical except
  for info-bar presence.
- **FR18-INFO-BAR-1**: Dismissible info-bar at top of main content
  area: "Otworzyłeś ten model z linku udostępnionego. [Otwórz w
  katalogu]". Dismissal state in `sessionStorage` keyed
  `share-context-dismissed:<modelId>`. **Verifiable:** vitest IB-1
  (renders on first visit), IB-2 (hidden after dismiss), IB-3 (re-shows
  for different `<modelId>`), IB-4 (re-shows in new session).
- **FR18-RETURN-URL-1**: Sign in button navigates to
  `/login?next=/share/<token>` (using existing `next` query param from
  Story 11.3 / AppShell anonymous-redirect convention). Post-login
  navigation honors `next` per existing `/login` route handling.
  **Verifiable:** Playwright RU-1 (Sign in click → URL contains
  `next=%2Fshare%2F...`); existing login tests already verify `next`
  honoring (no new test needed there).
- **FR18-CHROME-ADDITIONS-1**: Share-view header gains
  `<ThemeToggle />` + `<LangToggle />` + `<SignInButton />` in a
  right-aligned control group, mirroring TopBar order. Desktop ≥ 640px:
  single row with banner text. Mobile < 640px: Sign in button wraps
  below brand+banner; toggles stay right-aligned icon-only.
  **Verifiable:** Playwright `share-anonymous-with-signin.spec.ts` × 4
  projects (desktop-light/dark + mobile-light/dark).

### Non-Functional Requirements

- **NFR18-SHARE-ANON-CONTRACT-1**: NFR10 credentialless contract on
  `/api/share/<token>/*` MUST stay intact. New auth-bearing endpoint
  lives under separate prefix `/api/me/share-links/<token>/resolve`.
  Pre-merge grep invariant: `Depends(current_user)` MUST NOT appear in
  `apps/api/app/modules/share/router.py`. **Verifiable:** AC-grep in
  Story 30.1 pre-merge invariants.
- **NFR18-TOKEN-ENUMERATION-1**: Resolve endpoint MUST return uniform
  404 for invalid / expired / revoked tokens (no distinct error codes
  that would leak token-state to a brute-force probe). Same convention
  as Init 6 Story 6.4 invite token contract. **Verifiable:** pytest
  RESOLVE-3 / -4 / -5 all assert identical response body and headers.
- **NFR18-VISUAL-VERIFICATION-1**: All three stories carry visual
  baseline regen per [[feedback_frontend_visual_verification]] + Story
  5.13 Baseline Acceptance Gate. New baselines bundled in same commit
  as the producing change; reviewer sign-off per FR13 commit-message
  rule.
- **NFR18-I18N-PARITY-1**: 5 new i18n keys MUST appear in BOTH
  `en.json` and `pl.json` (project-context.md i18n rule). Polish
  diacritics correct. Pre-merge grep invariant: every new key present
  in both files with non-empty value.
- **NFR18-DETERMINISM-1**: Carries forward Init 10-17 determinism
  contract. Vitest + pytest 3× consecutive identical pass counts after
  each story merge.

### Decisions

- **Decision AA** (architecture): Authenticated share-resolve endpoint
  prefix — `/api/me/share-links/<token>/resolve`, NOT
  `/api/share/<token>/resolve`. Preserves NFR10 credentialless
  contract on existing public family. See `architecture.md` §
  Initiative 18 Decision AA.
- **Decision AB** (architecture): `/share/*` AppShell chrome bypass
  policy — conditional based on `useAuth()` result. Anonymous +
  loading → bypass (existing minimal header); authenticated → full
  AppShell (TopBar + ModuleRail), enabling Variant γ enrich-in-place.
  See `architecture.md` § Initiative 18 Decision AB.
- **Decision AC** (UX): Info-bar dismissal persistence —
  `sessionStorage` per-modelId (Sally Decision 3, operator-approved
  2026-05-25). See `architecture.md` § Initiative 18 Decision AC.

### Out of scope (intentional)

- **Phase B (anonymous CONTENT parity)** — description placement
  parity, multi-STL listing parity, fullscreen 3D viewer for
  anonymous. Future-initiative candidate; would require full reversal
  of terminus policy + own brainstorm pass.
- **B7 future granular sharing** ("request access" page) — defer until
  granular-sharing feature exists.
- **B6 disabled-account handling beyond fall-through to anonymous** —
  defer until disabled-account usage data exists.
- **Multi-tab race / session-expiry-mid-view / mid-session account
  creation** (brainstorm α-3, α-4, α-6) — handle ad-hoc per operator's
  Phase 2 decision.
- **Cross-cutting edge cases x-1 through x-8** (history-leak, OCR-typed
  URL, group-chat propagation, bot crawling, phishing, link
  revocation mid-view, dual-link from two senders, WebView session
  isolation) — handle ad-hoc.
- **Multi-button SHARE / intent declaration at link-generation time**
  (Path β, killed at Brainstorm Phase 1).
- **Self-serve registration CTA on share-view** (C5, ruled out).
- **Native-app handoff** (C7, ruled out).
- **Action-bridge UI** (C8, covered by portal-native flows).
- **Audit emission on resolve endpoint** — read-only operation,
  mirrors `share` read-pattern (no audit per Init 6 convention). If
  operator later wants audit for "who-resolved-what" telemetry, it's a
  follow-up TB.

### Cross-references

- Predecessor initiative: Initiative 17 — closed 2026-05-24 (aggregate
  retro at `init-17-retro-2026-05-24.md`).
- Source SCP: `sprint-change-proposal-2026-05-25-init18.md`.
- Architecture extension: `architecture.md` § Initiative 18 (Decisions
  AA + AB + AC).
- Epics extension: `epics.md` § Initiative 18 (Epic E30 + Stories 30.1
  + 30.2 + 30.3).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
  § epic-30 / 30-1-* / 30-2-* / 30-3-*.
- Brainstorm input: `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md`.
- UX input: `_bmad-output/ux/share-flow-membership-path-ux.md`.
- Memory entries: [[feedback_share_view_scope_boundary]] (amended
  2026-05-25 with carve-out), [[feedback_feature_proposal_use_case_enumeration]]
  (this initiative is the canonical correction precedent),
  [[feedback_itcm_autonomous_mode]], [[feedback_default_to_bmad_workflow]],
  [[feedback_codex_model_routing]] (gpt-5.4-mini for FE stories,
  gpt-5.5 for Story 30.1 due to NFR-SECURITY adjacency per
  [[feedback_security_vector_enumeration]]),
  [[feedback_frontend_visual_verification]],
  [[feedback_pre_merge_gate_checklist]],
  [[feedback_auth_boundary_contract_audit]] (Story 30.1 touches auth
  boundary — new authenticated endpoint adjacent to public bypass
  family).
- Triage cross-reference: zero NEW TB filings by Init 18 (gap was
  surfaced 2026-05-24 and went straight to brainstorming → UX →
  correct-course; no intermediate triage step needed). Phase B
  registered in `triage-backlog.md` as future-initiative candidate.
```

### 4.2 Architecture extension (`architecture.md` § Initiative 18)

**OLD:** (file ends after Initiative 17 § Decision Z)

**NEW:** (append at bottom)

```markdown
## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Source SCP:
`sprint-change-proposal-2026-05-25-init18.md`. Init 18 introduces
three architectural decisions on the share-flow recipient-state routing.

### Decision AA — Authenticated share-resolve endpoint placement

**Decision:** the new authenticated branch lives at
`GET /api/me/share-links/<token>/resolve`, NOT
`GET /api/share/<token>/resolve`.

**Implementation:** add the endpoint to existing
`apps/api/app/modules/share/member_router.py` (router prefix
`/api/me/share-links` per Init 6 Story 6.5 precedent). The endpoint
uses standard `Depends(current_user)` auth dep; no anonymous bypass.

**Why this prefix (not `/api/share/<token>/...`):**

- [[feedback_share_view_scope_boundary]] amended carve-out 2026-05-25
  preserves NFR10 credentialless contract on existing
  `/api/share/<token>/*` family. Adding ANY auth-bearing endpoint
  under that prefix risks future maintainers reflexively adding
  `Depends(current_user)` to a public route (Init 6 / Init 12 lessons:
  the public-bypass pattern is fragile under contributor pressure).
- `member_router.py` at `/api/me/share-links` already establishes the
  "authenticated operations adjacent to share-tokens" pattern.
  Extending it to host `<token>/resolve` is the natural placement.
- Frontend pairing is clean: `MemberShareView` calls
  `api("/api/me/share-links/<token>/resolve")`; anonymous render
  continues calling existing `/api/share/<token>` endpoints. Two URL
  families = two clearly-separated trust zones.

**Token-status-enumeration protection** (NFR18-TOKEN-ENUMERATION-1):
the new endpoint returns uniform 404 for invalid / expired / revoked
tokens (same convention as Init 6 Story 6.4 invite-token validation).
The resolve endpoint does NOT distinguish "token never existed" from
"token existed but expired/revoked" in the response — uniform 404
prevents a brute-force enumeration probe from extracting token-state.
For tokens that DO resolve, the endpoint returns
`{model_id: UUID, access: "granted"}` — `access` field is forward-compat
for B7 ("granted" / "request_needed").

### Decision AB — `/share/*` AppShell chrome bypass policy

**Decision:** `AppShell.tsx` `isSharePath` bypass becomes conditional:

- **Anonymous OR auth-loading** → bypass (existing behavior; minimal
  share-view header rendered by route component itself).
- **Authenticated** → render full AppShell (TopBar + ModuleRail),
  enabling Variant γ enrich-in-place at `/share/<token>`.

**Implementation sketch** (Story 30.2):

```tsx
// AppShell.tsx
const isSharePath = pathname.startsWith("/share/");

// Decision AB: bypass share path ONLY when the caller is anonymous.
// Authenticated callers on /share/<token> get full chrome (Variant γ
// enrich-in-place) per Init 18 FR18-MEMBER-SHARE-VIEW-1.
const shouldBypassForShare = isSharePath && !auth.isAuthenticated;

if (shouldBypassForShare) {
  return <>{children}</>;
}
```

The auth-loading state (`auth.isLoading === true`) continues to render
the spinner per existing behavior (line 73-79 of AppShell.tsx); the
bypass evaluation runs after loading resolves, preventing a chrome
flash during the brief auth fetch.

**Why conditional bypass (not unconditional):**

- Variant γ enrich-in-place (operator + Sally decision) requires the
  full member chrome to render around the catalog detail content. An
  unconditional bypass would force `MemberShareView` to re-implement
  TopBar + ModuleRail inside the route component, which is fragile
  (chrome drift, prop duplication, dark-mode token drift).
- Anonymous render continues to bypass (zero regression for
  B1/B2/B3/B4/B6 recipients).

### Decision AC — Info-bar dismissal persistence

**Decision:** `sessionStorage` key pattern
`share-context-dismissed:<modelId>`. Per-model + per-session
granularity. Next session re-shows (assumes user may have forgotten
context).

**Implementation:** `ShareMemberContextInfoBar.tsx` component reads
`sessionStorage.getItem("share-context-dismissed:" + modelId)` on
mount; if present (any truthy value), suppresses render. Close button
sets `sessionStorage.setItem("share-context-dismissed:" + modelId,
"1")`.

**Why sessionStorage (not localStorage):**

- Sally pick + operator-approved 2026-05-25 (Sally UX rec Decision 3).
- Re-showing per session is less surprising than "forever dismissed" —
  recipient may genuinely forget the share-link context after a
  multi-day gap.
- Per-modelId scoping prevents one dismiss from silencing the info-bar
  for unrelated share links the same recipient receives later.
- Operator may downgrade to localStorage in a future iteration if
  telemetry shows recipients dismissing repeatedly within a session.

**Edge case — sessionStorage unavailable** (private browsing strict
mode, embedded WebView, etc.): the info-bar renders on every mount
(fail-open, never silently swallows the affordance). The dismiss
button still works in-memory for the lifetime of the component
instance.

### Cross-references

- PRD: `prd.md` § Initiative 18 (FR18-* + NFR18-* link back to Decisions
  AA + AB + AC).
- Epics: `epics.md` § Initiative 18 (Epic E30 Story 30.1 implements
  Decision AA; Story 30.2 implements Decisions AB + AC; Story 30.3
  implements chrome additions independent of the three decisions).
- SCP: `sprint-change-proposal-2026-05-25-init18.md` § §4.
- Memory entries informing decisions: [[feedback_share_view_scope_boundary]]
  (amended carve-out language drove Decision AA's prefix separation),
  [[feedback_auth_boundary_contract_audit]] (Decision AA prefix
  separation is the canonical audit-mandated boundary-preservation
  shape), [[feedback_security_vector_enumeration]] (Story 30.1 §
  Threat vectors enumerated MUST list: token-enumeration probe via
  resolve endpoint, double-resolve via stale session, CSRF on resolve
  endpoint (read-only GET — not applicable, but document the
  reasoning), cross-tenant access via stale member access).
```

### 4.3 Epics extension (`epics.md` § Initiative 18 + Epic E30)

**OLD:** (file ends after Standalone Story S29.1 section)

**NEW:** (append at bottom)

```markdown
## Initiative 18 — Share-Flow Membership-Path Completion (Phase A)

**Status:** 🚧 planning (started 2026-05-25). Maintainer: Ezop. Source
SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-25-init18.md`
(status `draft-pending-operator-approval`). Predecessor Init 17 closed
2026-05-24 (aggregate retro at `init-17-retro-2026-05-24.md`). Init 18
is a **focused post-ship use-case-enumeration-gap correction sweep**:
one new epic E30 with three stories closing the membership-path
decision tree at `/share/<token>` for B5 (active member receiving
share link from another member) without touching anonymous share-view
CONTENT (per [[feedback_share_view_scope_boundary]] carve-out 2026-05-25).
Phase B (anonymous CONTENT parity) deferred as future-initiative
candidate.

### Overview

Brainstorming session 2026-05-25-0030 + Sally UX recommendation
(`share-flow-membership-path-ux.md`) produced 3 render modes for
`/share/<token>`: (1) anonymous (B1/B2/B3/B4/B6) — unchanged content,
new chrome (Sign in + Lang + Theme toggles); (2) enriched member view
(B5) — canonical catalog detail UI + dismissible info-bar; (3)
request-access page (B7) — deferred. All three operator decisions
(Sign in carve-out / Lang+Theme toggles / info-bar dismissal scope)
resolved 2026-05-25 before correct-course began. Single epic, three
stories, all P2.

### Functional Requirements (compact)

(See `prd.md` § Initiative 18 for full FR text; summary:)

- **FR18-SHARE-RESOLVE-1**: new authenticated endpoint
  `GET /api/me/share-links/<token>/resolve`.
- **FR18-SHARE-RESOLVE-2**: existing `/api/share/<token>/*` public
  family stays untouched (NFR10 contract preservation).
- **FR18-FE-CONDITIONAL-RENDER-1**: `/share/<token>` route splits on
  `useAuth()`.
- **FR18-MEMBER-SHARE-VIEW-1**: `MemberShareView` renders canonical
  catalog detail UI at share URL.
- **FR18-INFO-BAR-1**: dismissible info-bar with sessionStorage
  persistence per modelId.
- **FR18-RETURN-URL-1**: Sign in navigates to
  `/login?next=/share/<token>` via existing `next` convention.
- **FR18-CHROME-ADDITIONS-1**: share-view header gains
  ThemeToggle + LangToggle + SignInButton (right-aligned, mirrors
  TopBar order).

### Non-Functional Requirements

- **NFR18-SHARE-ANON-CONTRACT-1**: NFR10 credentialless contract
  preservation (pre-merge grep invariant).
- **NFR18-TOKEN-ENUMERATION-1**: resolve endpoint uniform 404 for
  invalid/expired/revoked.
- **NFR18-VISUAL-VERIFICATION-1**: Stories 30.2 + 30.3 carry visual
  baseline regen per [[feedback_frontend_visual_verification]].
- **NFR18-I18N-PARITY-1**: 5 new i18n keys in BOTH en.json + pl.json
  (Polish diacritics).
- **NFR18-DETERMINISM-1**: vitest + pytest 3× consecutive identical
  pass counts after each story merge.

### Decisions

- **Decision AA** (architecture): authenticated share-resolve endpoint
  at `/api/me/share-links/<token>/resolve` (separate prefix from
  public `/api/share/<token>/*` family). See `architecture.md` §
  Initiative 18 Decision AA.
- **Decision AB** (architecture): `/share/*` AppShell chrome bypass
  conditional on `useAuth()`. See `architecture.md` § Initiative 18
  Decision AB.
- **Decision AC** (UX): info-bar dismissal `sessionStorage` per
  modelId. See `architecture.md` § Initiative 18 Decision AC.

### Out of scope (intentional)

- Phase B (anonymous CONTENT parity) — future-initiative candidate.
- B7 request-access page — defer until granular sharing exists.
- B6 disabled-account richer handling — defer until usage data exists.
- Multi-tab race / session-expiry-mid-view / mid-session account
  creation — handle ad-hoc.
- Cross-cutting edge cases x-1 through x-8 — handle ad-hoc.
- Path β multi-button SHARE / intent declaration — killed Brainstorm
  Phase 1.
- Audit emission on resolve endpoint (deferred to follow-up TB if
  operator wants telemetry).

### Cross-references

- Predecessor: Initiative 17 — closed 2026-05-24.
- Source SCP: `sprint-change-proposal-2026-05-25-init18.md`.
- PRD: `prd.md` § Initiative 18 (FR18-* + NFR18-*).
- Architecture: `architecture.md` § Initiative 18 (Decisions AA + AB +
  AC).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
  § epic-30 / 30-1 / 30-2 / 30-3.
- Brainstorm: `_bmad-output/brainstorming/brainstorming-session-2026-05-25-0030.md`.
- UX: `_bmad-output/ux/share-flow-membership-path-ux.md`.
- Memory entries: [[feedback_share_view_scope_boundary]] (amended
  carve-out), [[feedback_feature_proposal_use_case_enumeration]]
  (canonical correction precedent),
  [[feedback_codex_model_routing]] (Story 30.1 → gpt-5.5; Stories 30.2 +
  30.3 → gpt-5.4-mini), [[feedback_auth_boundary_contract_audit]]
  (Story 30.1 hot-spot), [[feedback_security_vector_enumeration]]
  (Story 30.1 § Threat vectors enumerated),
  [[feedback_frontend_visual_verification]] (Stories 30.2 + 30.3),
  [[feedback_pre_merge_gate_checklist]] (all 3 stories), [[feedback_itcm_autonomous_mode]],
  [[feedback_default_to_bmad_workflow]].

#### Epic E30 — Share-Flow Membership-Path Completion

##### Story 30.1 — Authenticated share-resolve endpoint + return-URL plumbing
(FR18-SHARE-RESOLVE-1, FR18-SHARE-RESOLVE-2, FR18-RETURN-URL-1, NFR18-SHARE-ANON-CONTRACT-1, NFR18-TOKEN-ENUMERATION-1)

**Realizes:** FR18-SHARE-RESOLVE-1 + FR18-SHARE-RESOLVE-2 +
FR18-RETURN-URL-1 (frontend plumbing portion). **Architectural anchor:**
Decision AA. **Codex tag:** `gpt-5.5` (NFR-SECURITY adjacency per
[[feedback_security_vector_enumeration]] + [[feedback_auth_boundary_contract_audit]];
new authenticated endpoint sits adjacent to public credentialless
bypass family — pre-merge codex review is the operational
boundary-preservation gate).

Backend: `apps/api/app/modules/share/member_router.py` adds new
endpoint `GET /api/me/share-links/<token>/resolve` returning
`ShareResolveResponse(model_id: UUID, access: Literal["granted"])`
HTTP 200 for valid token + authenticated caller. Implementation:
delegate to `ShareService.resolve(token)` (NEW service method that
reads from existing share-token storage; returns model_id or raises
`ShareTokenInvalid` for invalid/expired/revoked; uniform exception
surfaces as 404). Future B7 hook: `access` field is forward-compat
(`Literal["granted"]` today; future `Literal["granted", "request_needed"]`
when granular sharing lands).

`apps/api/app/modules/share/service.py`: add `resolve(token: str) -> UUID`
method (or `ShareResolveResult` dataclass with `model_id` for
forward-compat). MUST mirror existing `validate_active` / `get_by_token`
storage-read pattern; MUST NOT add any auth dep at service layer.

Frontend (return-URL plumbing — minor): `apps/web/src/routes/login.tsx`
(or wherever login post-success navigation is handled) verify that the
existing `next` query-param convention from AppShell anonymous-redirect
(Story 11.3 / commit 64447ff) honors arbitrary `/share/<token>` paths.
If the existing handler already accepts any relative path starting with
`/`, no changes needed — confirm via vitest RU-1. If it whitelists
specific path prefixes (security-defensive open-redirect prevention),
extend whitelist to include `/share/` prefix. Document the relative-path
+ same-origin assertion in Story 30.1 spec § Threat vectors.

**Pre-merge invariants (AC enforcement):**

1. `grep -rE "Depends\((get_)?current_(user|admin)\)" apps/api/app/modules/share/router.py`
   returns ZERO matches (NFR10 credentialless contract preserved).
2. Resolve endpoint dep tree includes `current_user` (positive
   invariant via FastAPI route introspection in pytest).
3. Token-state-enumeration grep: response bodies for RESOLVE-3 / -4 /
   -5 are byte-identical (uniform 404).
4. `ShareResolveResponse` model has no field named `expires_at` /
   `revoked_at` / `created_at` (no token-state leakage in 200
   response body).
5. Return-URL handler accepts `/share/<token>` (vitest RU-1) AND
   rejects absolute URLs / external schemes (vitest RU-2 negative).

**Test target counts:** backend baseline + ~8 new (RESOLVE-1 through
-5 + CONTRACT-1 + dep-tree + service-layer-unit); vitest baseline + ~2
new (RU-1, RU-2). NO new visual baselines for Story 30.1 (pure
backend + login plumbing).

**Out of scope:** audit emission on resolve (deferred); resolve
endpoint paginated list (single-token resolve only); rate-limit on
resolve (inherits global auth-scope rate-limit; no per-token
throttling — would require new bucket key, defer until needed); B7
"access_needed" branch (forward-compat field present, implementation
deferred).

##### Story 30.2 — Frontend conditional render + `MemberShareView` + info-bar
(FR18-FE-CONDITIONAL-RENDER-1, FR18-MEMBER-SHARE-VIEW-1, FR18-INFO-BAR-1, NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1)

**Realizes:** FR18-FE-CONDITIONAL-RENDER-1 + FR18-MEMBER-SHARE-VIEW-1
+ FR18-INFO-BAR-1. **Architectural anchors:** Decisions AB + AC.
**Codex tag:** `gpt-5.4-mini` (FE composition + new component, no
security class).

**Depends on:** Story 30.1 (needs resolve endpoint to obtain
`model_id` from token).

Frontend route (`apps/web/src/routes/share/$token.tsx`): replace the
unconditional anonymous render with `useAuth()`-gated split. Sketch:

```tsx
function ShareTokenRoute() {
  const { token } = Route.useParams();
  const { user } = useAuth();
  if (user !== null) {
    return <MemberShareView token={token} />;
  }
  return <AnonymousShareView token={token} />;  // existing path, extracted
}
```

Existing inline anonymous render extracted into named
`AnonymousShareView` component within the same file (no behavior
change; just refactor for the split).

AppShell change (`apps/web/src/shell/AppShell.tsx`): bypass condition
gains `&& !auth.isAuthenticated` guard per Decision AB. Add explanatory
comment referencing Init 18 Decision AB + FR18-MEMBER-SHARE-VIEW-1.

New component `apps/web/src/modules/catalog/components/MemberShareView.tsx`
(or under `apps/web/src/routes/share/` — colocate decision in spec):

- Calls `useShareResolve(token)` hook (new) that wraps
  `api("/api/me/share-links/<token>/resolve")` in a `useQuery` with
  query-key `["share", "resolve", token]`.
- On success, renders the canonical catalog detail component tree
  with `model_id` (reuse existing `CatalogDetail` / `ModelHero` /
  `ModelGallery` / STL list / description components from
  `apps/web/src/modules/catalog/`).
- On 404, renders an explicit "token invalid or expired" message
  (re-uses anonymous share-view's existing token-invalid copy +
  Sign in CTA).
- On 401 (defensive — shouldn't happen if AppShell gating is right):
  triggers AuthContext refresh + falls back to AnonymousShareView.
- Renders `<ShareMemberContextInfoBar modelId={data.model_id} />` at
  top of main content area.

New component `apps/web/src/routes/share/ShareMemberContextInfoBar.tsx`
(or `apps/web/src/ui/custom/ShareMemberContextInfoBar.tsx`):

- shadcn `Alert` primitive (`variant="default"`).
- Tailwind: `mb-4 flex items-center justify-between gap-3 rounded-md
  border border-border bg-muted/50 px-3 py-2 text-sm`.
- Icon: `Info` from `lucide-react` `size-4` muted-foreground.
- Action: `<Link to="/catalog/$id" params={{ id: modelId }}>` —
  TanStack Router-typed.
- Dismiss: close button right-side; sessionStorage key
  `share-context-dismissed:<modelId>` per Decision AC; safe-fallback
  for unavailable sessionStorage (always-render + in-memory dismiss
  for lifetime of component).

New i18n keys (Story 30.2 owns these 3):

- `share.member_context.banner`: "Otworzyłeś ten model z linku
  udostępnionego." / "You opened this model from a shared link."
- `share.member_context.open_in_catalog`: "Otwórz w katalogu" / "Open
  in catalog".
- `share.member_context.dismiss_aria`: "Zamknij informację" /
  "Dismiss notice".

(Story 30.3 owns the remaining 2: `share.view.signin_cta` +
`share.view.signin_aria`.)

**Test target counts:**

- Vitest: baseline + ~6 new (CR-1 anonymous render, CR-2 authenticated
  render, IB-1 renders on first visit, IB-2 hidden after dismiss, IB-3
  re-shows for different modelId, IB-4 re-shows new session — IB-4 via
  sessionStorage.clear() mock).
- Visual (Playwright): NEW spec
  `apps/web/tests/visual/share-member-enriched.spec.ts` × 4 projects
  (desktop-light, desktop-dark, mobile-light, mobile-dark) = 4
  baseline PNGs covering enriched render with info-bar visible.
  Second NEW spec `share-member-enriched-dismissed.spec.ts` × 4
  projects = 4 baseline PNGs covering enriched render with info-bar
  dismissed via sessionStorage pre-seed. Total: 8 new baselines bundled
  in same commit per FR13 Baseline Acceptance Gate.

**Pre-merge invariants:**

1. `useAuth()` import + branching present in `share/$token.tsx`.
2. AppShell `isSharePath` bypass condition includes
   `!auth.isAuthenticated` guard.
3. `MemberShareView` calls `api("/api/me/share-links/<token>/resolve")`
   exactly once per token (memoized via `useQuery`).
4. `ShareMemberContextInfoBar` reads sessionStorage on mount with key
   pattern `share-context-dismissed:<modelId>`.
5. 3 new i18n keys present in BOTH en.json + pl.json with non-empty
   values (`grep -E "share\.member_context\.(banner|open_in_catalog|dismiss_aria)"`).
6. Visual baselines for 2 new specs × 4 projects = 8 PNGs staged in
   commit; `baseline-reviewed:` sign-off line present in commit
   message per FR13.

**Out of scope:** comments / member actions / advanced metadata
blocks beyond what `/catalog/$id` already renders (no NEW catalog
features in Story 30.2 — pure render reuse); permission-check edge
case for member-without-model-access (deferred to B7 follow-up if it
materializes; today all members have access to all models).

##### Story 30.3 — Frontend share-view chrome additions (Sign in + LangToggle + ThemeToggle)
(FR18-CHROME-ADDITIONS-1, FR18-RETURN-URL-1 (Sign in click portion), NFR18-VISUAL-VERIFICATION-1, NFR18-I18N-PARITY-1)

**Realizes:** FR18-CHROME-ADDITIONS-1 + FR18-RETURN-URL-1 (Sign in
click navigation portion; backend handler portion lives in Story
30.1). **Codex tag:** `gpt-5.4-mini` (CSS + new component, no
security class).

**Independent of:** Stories 30.1 + 30.2 — can land in parallel.

Frontend (`apps/web/src/routes/share/$token.tsx` header section, OR
new `apps/web/src/routes/share/ShareHeader.tsx` extracted component —
spec authoring decision):

Existing minimal header:

```tsx
<header className="...">
  <span className="font-semibold">Portal 3D</span>
  <span className="...">Oglądasz udostępniony model</span>
</header>
```

Becomes:

```tsx
<header className="...">
  <div className="flex items-center gap-3">
    <span className="font-semibold">Portal 3D</span>
    <span className="...">{t("share.view.banner")}</span>
  </div>
  <div className="flex items-center gap-2">
    <ThemeToggle />
    <LangToggle />
    <SignInButton token={token} />
  </div>
</header>
```

Right-side control order MUST mirror member TopBar
(`ThemeToggle + LangToggle + UserMenu/SignInButton` — UserMenu and
SignInButton occupy the same slot semantically). Existing banner
text remains (Sally Deliverable 1 rationale: combine, don't replace).

New component `apps/web/src/routes/share/SignInButton.tsx` (or
`apps/web/src/ui/custom/SignInButton.tsx`):

```tsx
export function SignInButton({ token }: { token: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => void navigate({ to: "/login", search: { next: `/share/${token}` }, replace: false })}
      aria-label={t("share.view.signin_aria")}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <LogIn className="size-4" />
      {t("share.view.signin_cta")}
    </button>
  );
}
```

Responsive (mobile < 640px): the right-side control group wraps below
brand+banner row; OR toggles stay icon-only on mobile (Sally
Deliverable 1 sketch — final decision: spec author picks the cleaner
shape based on actual viewport behavior, document the choice in Story
30.3 spec). Mobile layout MUST not regress today's banner visibility.

New i18n keys (Story 30.3 owns these 2):

- `share.view.signin_cta`: "Zaloguj się" / "Sign in".
- `share.view.signin_aria`: "Zaloguj się, aby zobaczyć więcej opcji" /
  "Sign in to access more options".

**Test target counts:**

- Vitest: baseline + ~3 new (CHROME-1 Sign in click navigates to
  `/login?next=...`, CHROME-2 LangToggle present, CHROME-3 ThemeToggle
  present).
- Visual (Playwright): EXISTING spec
  `apps/web/tests/visual/share-anonymous.spec.ts` (if present) gets
  baselines REGENERATED to include the new chrome; OR new spec
  `share-anonymous-with-signin.spec.ts` × 4 projects = 4 new baseline
  PNGs (spec authoring decides). Either way: 4 baseline PNGs covering
  anonymous render with new chrome. Per [[feedback_share_view_scope_boundary]]
  amended carve-out: visual baseline regen for membership-path chrome
  is warranted (NOT operator-manual-verify); contrast with anonymous
  CONTENT changes which would still require operator manual verify.

**Pre-merge invariants:**

1. Share-view header contains `<ThemeToggle />` + `<LangToggle />` +
   `<SignInButton />` (grep + DOM-assert in vitest).
2. Right-side control order matches member TopBar (ThemeToggle first,
   LangToggle second, SignInButton/UserMenu third).
3. SignInButton onClick navigates with `search: { next: "/share/<token>" }`
   (vitest CHROME-1).
4. 2 new i18n keys present in BOTH en.json + pl.json.
5. Mobile layout doesn't crop the banner text (visual baseline regen
   per [[feedback_frontend_visual_verification]]).
6. Baseline-reviewed sign-off line per FR13 for the 4 regenerated /
   newly-created PNGs.

**Out of scope:** A/B test of Sign in button placement (Sally
Deliverable 1 alternatives — operator-locked Option (a) right-aligned
combined-with-banner); SignInButton color/variant experimentation
(Tailwind classes locked per Sally Deliverable 1 visual spec);
Sign in copy variants ("Have an account? Sign in" etc. — Sally
Deliverable 3 locked single string).

#### Standalone stories — none for Init 18

(No standalone stories outside Epic E30 in Init 18 scope.)
```

### 4.4 Sprint-status extension (`sprint-status.yaml`)

**OLD:** (file ends after `29-1-init-11-15-h2-backfill: done` entry at
line 445)

**NEW:** (append at bottom)

```yaml
  # ─── Epic 30: Share-Flow Membership-Path Completion (Initiative 18) ───
  # Added 2026-05-25 by sprint-change-proposal-2026-05-25-init18.md § §4.3.
  # Closes the post-Init-12 use-case-enumeration gap (member receiving
  # share link from another member got degraded anonymous view).
  # All 3 stories under [[feedback_share_view_scope_boundary]] amended
  # carve-out (membership-path completion, NOT anonymous content
  # enrichment). Codex routing: 30.1 → gpt-5.5 (NFR-SECURITY adjacency
  # to public bypass family); 30.2 + 30.3 → gpt-5.4-mini (FE composition).
  epic-30: backlog
  30-1-share-resolve-endpoint-return-url: backlog   # Backend: GET /api/me/share-links/<token>/resolve + return-URL handler verification. Realizes FR18-SHARE-RESOLVE-1+2, FR18-RETURN-URL-1 (FE plumbing portion). Anchors Decision AA. Codex gpt-5.5. Pre-merge invariants: 5 (anon contract grep, dep-tree, uniform 404, no token-state in response, return-URL whitelist).
  30-2-conditional-render-member-share-view-info-bar: backlog   # Frontend: useAuth() split at /share/<token> + MemberShareView component + dismissible info-bar. Realizes FR18-FE-CONDITIONAL-RENDER-1, FR18-MEMBER-SHARE-VIEW-1, FR18-INFO-BAR-1. Anchors Decisions AB + AC. Codex gpt-5.4-mini. Depends on 30.1.
  30-3-share-view-chrome-additions: backlog   # Frontend: share-view header gains ThemeToggle + LangToggle + SignInButton. Realizes FR18-CHROME-ADDITIONS-1, FR18-RETURN-URL-1 (Sign in click portion). Codex gpt-5.4-mini. Independent of 30.1 + 30.2.
  epic-30-retrospective: optional
```

When the first story (likely 30.1 or 30.3 — both can start in
parallel) is created via `bmad-create-story`, the
`bmad-create-story` skill will automatically flip `epic-30: backlog →
in-progress` per skill convention.

### 4.5 Triage-backlog extension (`triage-backlog.md`)

**OLD:** (existing structure)

**NEW:** (add a "Future Initiatives" entry — or extend if section
exists)

```markdown
### Phase B — Anonymous share-view CONTENT parity (future-initiative candidate)

**Status:** future-initiative candidate (NOT a TB ID; not actionable
within Init 18). Filed 2026-05-25 as part of Init 18 SCP §3.3.

**Scope:** description placement parity with `/catalog/$id`, multi-STL
listing parity, fullscreen 3D viewer for anonymous recipients.

**Why not in Init 18:** would require full reversal (not carve-out) of
[[feedback_share_view_scope_boundary]] terminus policy + its own
brainstorm pass for security/NFR10 implications.

**Trigger to promote:** operator observes B1/B2 recipients hitting
content-parity gaps in the wild (HAR-evidence or direct user
feedback). Until then, no story addresses Phase B.

**Predecessor:** Init 18 (membership-path completion Phase A).
```

(If `triage-backlog.md` doesn't have a "Future Initiatives" section
yet, the spec author for Story 30.1 OR the close-out housekeeping pass
for Init 18 adds the section header alongside this entry.)

---

## Section 5 — Implementation Handoff

### 5.1 Scope classification

**Moderate.** One new initiative, one new epic, three stories, single
Phase A delivery. No PRD MVP redefine; no architecture re-platforming;
no migration; no infra change. Handoff target:
**Product Owner / Developer agents** (per workflow rules § "Moderate
scope").

### 5.2 Recipients and responsibilities

- **Operator (Ezop):** approve this SCP. Once approved, ITCM autonomous
  mode kicks in for execution.
- **`bmad-create-story` skill (Claude main session, ITCM):** generate
  Story 30.1 spec first (it's the dependency); then Story 30.3
  (parallelable); then Story 30.2 (depends on 30.1). All three specs
  follow Init 17 precedent shape (binding implementation skeletons +
  numbered tasks + pre-merge invariants + named tests).
- **`bmad-dev-story` skill (Claude main session, ITCM, autonomous):**
  implement each story per spec. Codex routing per
  [[feedback_codex_model_routing]]:
  - Story 30.1 → `gpt-5.5` (NFR-SECURITY adjacency).
  - Stories 30.2 + 30.3 → `gpt-5.4-mini` (routine FE work).
- **Operator (Ezop):** post-merge real-world verification on `.190`
  per [[feedback_frontend_visual_verification]] + [[feedback_auto_deploy_dev]]
  (auto-deploy fires after every code merge to main; doc-only commits
  skip).
- **`bmad-retrospective` skill (optional):** Init 18 retro post-close
  for lessons-learned harvest. Single-epic init may not warrant a
  formal retro; operator flips `epic-30-retrospective` from `optional`
  → `done` if running it.

### 5.3 Success criteria

- All 3 stories shipped with status `done` in sprint-status.yaml.
- Pre-merge invariants (16 total across the 3 stories) all green.
- Real-world verification on `.190` confirms:
  - Anonymous recipient sees existing share-view + new Sign in / Lang
    / Theme controls in header (Story 30.3).
  - Member recipient (Ezop logged in) opening a share link to a model
    sees full catalog detail UI + dismissible info-bar; URL stays
    `/share/<token>` (Story 30.2).
  - Sign in click on share-view navigates to `/login?next=/share/<token>`
    and post-login lands the user back on `/share/<token>` (Story
    30.1 + 30.3 together).
- NFR10 credentialless contract on `/api/share/<token>/*` family
  intact (grep invariant green; Story 30.1).
- Visual baselines for 8-12 new PNGs (Stories 30.2 + 30.3) reviewed
  and signed off per FR13.

### 5.4 Estimated wall-clock + budget

Per Init 17 precedent (7 stories ~3h backend Codex budget + ~5h
total): Init 18 with 3 stories should fit comfortably in **~2-3h Codex
budget + 1h Claude main session orchestration**. Family-time AFK
clause per [[feedback_autonomous_sleep_on_budget]] may extend
wall-clock; budget-wise well under 5h cap.

---

## Section 6 — Final Review

### 6.1 Pre-existing-issue triage (per [[feedback_preexisting_issue_threshold]])

None flagged during Init 18 planning. Brainstorm + Sally UX
recommendation surfaced edge cases (α-3 / α-4 / α-6 / x-1 through x-8 /
rα-1 through rα-5) but all are deferred to ad-hoc handling per Phase 4
operator decision; no recurring-issue pattern across 3 stories OR ≥5×
session repetition that would trigger the threshold.

### 6.2 Phase B tracking (per operator brief task #4)

Phase B (anonymous CONTENT parity) registered in `triage-backlog.md`
as future-initiative candidate per §4.5 of this SCP. Promotion
trigger: operator-observed B1/B2 content-parity gap with HAR-evidence
or direct user feedback. Until then, no story addresses Phase B; no
Init 18 work touches anonymous CONTENT.

### 6.3 Memory amendment (per operator brief task #1)

**DONE 2026-05-25** before SCP draft began. File
`~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_share_view_scope_boundary.md`
amended with explicit "Carve-out (2026-05-25)" section preserving
terminus on anonymous CONTENT while permitting Sign in + Lang +
Theme toggles in chrome AND B5 enrich-in-place render. Memory now
explicitly references Init 18 as the canonical correction precedent
for the use-case-enumeration gap surfaced 2026-05-24.

### 6.4 Operator approval gate

This SCP requires **explicit operator approval** before
`bmad-create-story` is invoked for Story 30.1. Approval is the trigger
for ITCM autonomous mode (per [[feedback_itcm_autonomous_mode]]) to
take over execution. Approval mechanism: operator reply to this SCP
draft with "Approve" / "Approve + autonomous" / similar; OR operator
edits to refine specific decisions before approving; OR operator
rejects with reason → revise SCP.

### 6.5 Open question for operator (optional, non-blocking)

The `business_decisions_aligned_pre_scp` section in the YAML frontmatter
captures 6 alignment items, all locked. There are NO open questions for
operator at SCP draft time. If operator wants to revise any of the
6 alignment items before approval, please flag specifically which item
+ which alternative.

**One soft question** (operator may answer or skip):
**Should Init 18 spec authoring start immediately on approval, or wait for
an explicit "go" signal?** Default behavior (per
[[feedback_itcm_autonomous_mode]] + [[feedback_default_to_bmad_workflow]])
is **immediate start on approval** — soft confirmation request only
because Init 18 is the first initiative after Init 17 close + this is a
business-alignment-phase artifact (vs. Init 17 which was a follow-up
sweep with standing autonomous approval carried forward).
