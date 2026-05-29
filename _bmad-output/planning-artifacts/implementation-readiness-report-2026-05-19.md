---
project: 3d-portal
date: 2026-05-19
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
status: needs_work_before_implementation
documentsIncluded:
  prd: _bmad-output/planning-artifacts/prd.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics: _bmad-output/planning-artifacts/epics.md
  ux: null
requirementsExtracted:
  functional_total: 111
  nonfunctional_total: 70
  active_scope:
    initiative: 5
    functional_total: 24
    nonfunctional_total: 12
---

# Implementation Readiness Assessment Report

**Date:** 2026-05-19
**Project:** 3d-portal

## Step 1: Document Discovery

### Document Inventory

#### PRD Files Found

**Whole Documents:**
- `prd.md` (164811 bytes, modified 2026-05-18 23:25)

**Sharded Documents:**
- None found

#### Architecture Files Found

**Whole Documents:**
- `architecture.md` (170201 bytes, modified 2026-05-18 23:58)

**Sharded Documents:**
- None found

#### Epics & Stories Files Found

**Whole Documents:**
- `epics.md` (235442 bytes, modified 2026-05-19 00:30)

**Sharded Documents:**
- None found

#### UX Design Files Found

**Whole Documents:**
- None found

**Sharded Documents:**
- None found

### Discovery Issues

- No duplicate whole/sharded document formats found.
- Warning: no dedicated UX design document found; UX alignment will be assessed from PRD, Architecture, and Epics content.

### Documents Selected for Assessment

- PRD: `_bmad-output/planning-artifacts/prd.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epics and Stories: `_bmad-output/planning-artifacts/epics.md`
- UX Design: none

## Step 2: PRD Analysis

### PRD Read Coverage

The whole PRD was read from `_bmad-output/planning-artifacts/prd.md` (1258 lines). The document is a living, multi-initiative PRD. Initiatives 0-3 are shipped baseline/history; Initiative 5 is the active planning scope for implementation readiness.

### Functional Requirements

Total functional requirements extracted: **111**.

| Initiative | Status | FR Count | Requirement ID Families |
|---|---:|---:|---|
| Initiative 0 — Product Foundation | shipped retrospective | 29 | `FR0-CAT-*`, `FR0-ADM-*`, `FR0-SHARE-*`, `FR0-AUTH-*`, `FR0-SOT-*`, `FR0-RUN-*`, `FR0-RND-*` |
| Initiative 1 — Useful GlitchTip Delta | shipped | 30 | `FR1`-`FR30` in Initiative 1 context |
| Initiative 2 — Agent Runbook + Legacy SoT Triage | shipped | 11 | `FR1`-`FR11` in Initiative 2 context |
| Initiative 3 — UI Theme Compliance & Visual Regression Hardening | shipped | 17 | `FR1`-`FR17` in Initiative 3 context |
| Initiative 5 — Public Registration & User Account Management | planning | 24 | `FR5-INVITE-*`, `FR5-REGISTER-*`, `FR5-MEMBER-*`, `FR5-2FA-*`, `FR5-ADMIN-*`, `FR5-AUDIT-*`, `FR5-RATELIMIT-*`, `FR5-CUTOVER-*` |

#### Active-Scope Functional Requirements: Initiative 5

- **FR5-INVITE-1: Admin can generate single-use invite tokens.** TTL presets `1d / 3d / 7d / 30d` plus a custom-TTL input; pre-bound role default `member`; entropy 256 bits via `secrets.token_urlsafe(32)`. Storage is dual-backed: Redis at `invite:token:{token}` (active state + TTL + revoke) and a row in the new `invite_tokens` table (audit history outliving the Redis TTL). Audit event: `auth.invite.generated`. Verifiable: an admin-generated token has 32-byte entropy; the matching DB row exists with `generated_by`, `generated_at`, `role`, `ttl_seconds` populated.
- **FR5-INVITE-2: Admin can list active and historical invites.** The Invites tab in the admin panel filters by status (`active` / `used` / `expired` / `revoked`) and exposes per-row metadata: `generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`. Verifiable: filter applied; the row count and per-row metadata match the DB state.
- **FR5-INVITE-3: Admin can revoke an active unused invite token.** Revocation is immediate (Redis key deletion + DB row update with `revoked_at`). Audit event: `auth.invite.revoked`. A revoked-but-still-shown-in-the-list token must not be consumable. Verifiable: `POST /api/admin/invites/{id}/revoke` followed by `GET /register?token=<that-token>` returns HTTP 410 Gone.
- **FR5-INVITE-4: A used invite token is single-use; replay attempts fail closed.** Consumption deletes the Redis key and updates the DB row with `used_by` + `used_at` + `used_from_ip`. A second consumption attempt, regardless of source IP, returns HTTP 410 Gone, emits `auth.register.fail` with reason `token_consumed`, and never creates a duplicate user.
- **FR5-REGISTER-1: Public `/register?token=<token>` route accepts a valid unused invite token.** Token validation: Redis lookup; on miss -> HTTP 404 + audit event `auth.register.fail` with reason `token_invalid`. This route is the only public-write surface introduced by Initiative 5.
- **FR5-REGISTER-2: Registration form captures email + password and enforces strength.** Email format is RFC syntax only; no deliverability verification, DNS, or MX check. Password requires zxcvbn score >=3 and length >=12 characters; failures return HTTP 422 with the failing rule cited.
- **FR5-REGISTER-3: Successful registration creates a user account with the invite-bound role and issues the standard cookie pair.** Role matches invite pre-bound role. Invite is marked consumed. Response sets `portal_access` (10min) and `portal_refresh` (30d) cookies. Audit event: `auth.register.success`.
- **FR5-MEMBER-1: `member` role grants browse + viewer + share-link generation.** Permitted: read-only `/api/catalog/*` and `/api/sot/*` GET endpoints, 3D viewer routes, and `POST /api/share/*` to mint share tokens. Share-router auth dependency expands from `current_admin` to `current_member_or_admin`.
- **FR5-MEMBER-2: `member` role is denied all admin and audit surfaces.** Denied: `/api/admin/*`, `/api/audit/*`, and `/agent-runbook` operations requiring admin scope. Existing `current_admin` remains admin-only. New `current_member_or_admin` applies to the share-router only.
- **FR5-MEMBER-3: Member-generated share tokens are subject to per-member rate-limit and daily volume cap.** Architectural floor: <=20 share tokens per member per day; soft-fail alert at 50%; hard-fail HTTP 429 at 100%. Cap is configurable in `apps/api/app/core/config.py`.
- **FR5-2FA-1: User can enroll TOTP 2FA with mandatory recovery codes generated at enrollment.** `/settings/2fa` displays QR code and manual secret fallback. Secret persists encrypted at rest in `users.totp_secret`; timestamp in `users.totp_enabled_at`. Eight single-use recovery codes are displayed once and stored hashed. Audit event: `auth.totp.enrolled`.
- **FR5-2FA-2: Login flow extends with a second-factor step for users with TOTP enabled.** Valid email + password returns partial-auth state without `portal_access`; second step accepts current 6-digit TOTP or recovery code. Recovery-code consumption is one-way and emits `auth.recovery_code.used`. Wrong factor returns 401; correct factor returns 200 + cookies.
- **FR5-2FA-3: 2FA enforcement is per-role via a config flag with the `agent` role explicitly excluded.** `enforce_2fa_for_roles: list[Role]` defaults to `[]`. If `Role.agent` appears, the app must refuse to boot with a clear error. Admin can also force-enroll individual users.
- **FR5-2FA-4: User can regenerate recovery codes and disable TOTP from `/settings/2fa`.** Regeneration invalidates previous unconsumed codes and shows a new batch once. Disabling clears `totp_enabled_at`, invalidates unused recovery codes, emits `auth.totp.disabled`, and requires re-authentication.
- **FR5-ADMIN-1: Admin panel has two new tabs: `/admin/users` and `/admin/invites`.** Users columns: `email`, `role`, `created_at`, `last_active_at`, `totp_enabled`, `is_active`. Invites tab lists invites per `FR5-INVITE-2`. Both paginate at existing admin-list default.
- **FR5-ADMIN-2: Per-user actions are available from the Users tab and emit matching audit events.** Actions: change role, force 2FA enrollment, issue password reset link, deactivate/reactivate, and force logout-all-sessions. Each action must produce the documented audit row with correct actor/target pair.
- **FR5-ADMIN-3: Admin-issued password reset link is functionally an invite token; delivery is out-of-band.** Single-use, short TTL, Redis-fronted at `invite:reset:{token}`. Initiation emits `auth.password.reset.initiated`; consumption via `/reset-password?token=<token>` emits `auth.password.reset.completed`. Lost-2FA recovery path is force-disable 2FA, then issue reset link.
- **FR5-ADMIN-4: Bulk user operations are deliberately not in the v1 panel UI.** Panel ships single-user actions only. Multi-user disable/role-change remains DB-direct script territory unless the pattern recurs.
- **FR5-AUDIT-1: 16 new audit-log actions are registered in `KNOWN_ENTITY_TYPES` and emitted via `record_event()`.** Actions: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`, `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`, `auth.password.reset.initiated`, `auth.password.reset.completed`, `user.deactivated`, `user.reactivated`, `user.role_changed`, `user.force_logout`. Events include `actor_user_id`, `target_user_id` where distinct, `request_id`, and `ip`.
- **FR5-RATELIMIT-1: Rate-limit middleware applies to `/api/auth/login`, `/api/auth/refresh`, and `/api/auth/register?token=`.** Thresholds are tunable in config. Strategy: Redis-backed sliding window. Default login policy: >=5 failures from one IP within 60 seconds returns HTTP 429. Registration brute-force threshold must preserve a >=10^6 margin against 256-bit token entropy.
- **FR5-RATELIMIT-2: Per-member share-token creation cap is implemented in the same middleware family.** Key is per-member-per-day. Soft-fail alert emits a tagged log entry visible through GlitchTip; hard-fail returns HTTP 429.
- **FR5-CUTOVER-1: The nginx edge configuration at `~/repos/configs/nginx/3d.ezop.ddns.net.conf` is edited atomically in a single commit.** The edit drops both `auth_basic` and the IP allowlist in the same commit. `/share/*` and `/agent-runbook` bypass rules are preserved unchanged. Config diff is captured in architecture Decision K.
- **FR5-CUTOVER-2: The cutover is followed immediately by a 4-scenario post-reload smoke matrix executed against `.190`.** Scenarios: anonymous share token returns 200; agent service account `POST /api/admin/models` returns 201; member login returns 200 + access cookie; admin login returns 200 + admin scope verified. Output goes to `_bmad-output/implementation-artifacts/cutover-smoke-2026-MM-DD.md`.
- **FR5-CUTOVER-3: Rollback is single-command and must complete in <=30 seconds.** Rollback path: `git revert <cutover-sha>` in sibling repo + `nginx -s reload` on `.180`. Epic 10 acceptance includes rollback drill and smoke re-run.

### Non-Functional Requirements

Total non-functional requirements extracted: **70**.

| Initiative | Status | NFR Count | Requirement Families |
|---|---:|---:|---|
| Initiative 0 — Product Foundation | shipped retrospective | 24 | `NFR0-PERF-*`, `NFR0-SEC-*`, `NFR0-REL-*`, `NFR0-INT-*`, `NFR0-OBS-*`, `NFR0-MAINT-*` |
| Initiative 1 — Useful GlitchTip Delta | shipped | 17 | `NFR-P*`, `NFR-S*`, `NFR-R*`, `NFR-I*` in Initiative 1 context |
| Initiative 2 — Agent Runbook + Legacy SoT Triage | shipped | 8 | `NFR1`-`NFR8` in Initiative 2 context |
| Initiative 3 — UI Theme Compliance & Visual Regression Hardening | shipped | 9 | `NFR1`-`NFR9` in Initiative 3 context |
| Initiative 5 — Public Registration & User Account Management | planning | 12 | `NFR5-SEC-*`, `NFR5-PERF-*`, `NFR5-AUDIT-*`, `NFR5-CROSS-REPO-*`, `NFR5-INT-*`, `NFR5-OBS-*` |

#### Active-Scope Non-Functional Requirements: Initiative 5

- **NFR5-SEC-1: E9 audit gate condition.** E9 is the hard gate before E10. Gate condition: zero open Critical/High findings and at most 3 accepted-with-rationale Medium findings; the 4th Medium forces auto-fail and a fix sprint. Audit tooling: `bandit`, `semgrep`, `pip-audit`, `npm audit`/`osv-scanner`, OWASP ZAP, and `codex review`.
- **NFR5-SEC-2: Single-operator self-attestation mitigation.** Every Medium disposition requires a documented second-opinion artifact from `codex review --commit <SHA>`. Accepted-with-rationale requires an explicit countersignature line in the audit report.
- **NFR5-SEC-3: Audit scenario coverage matrix.** E9 must cover invite-token brute force, refresh-token replay, CSRF/JWT tampering on every mutating endpoint, IDOR scan on every admin endpoint, auth/register/refresh rate-limit verification, and member share-link amplification.
- **NFR5-PERF-1: `last_active_at` write is throttled to <=1 per 5 minutes per user.** Updates fire in auth middleware on authenticated requests and are backed by in-memory + Redis last-write timestamp.
- **NFR5-PERF-2: Edge cutover window is <=5 minutes.** Includes post-reload smoke matrix and rollback drill. Rollback itself must complete in <=30 seconds.
- **NFR5-AUDIT-1: Every Initiative 5 audit action is emitted via `record_event()`; no parallel logging surface.** The 16 actions in `FR5-AUDIT-1` are the complete Init 5 audit surface.
- **NFR5-CROSS-REPO-1: Epic 10 nginx edit bypasses `3d-portal` deploy skip-gate.** The edge edit lives in sibling repo `~/repos/configs`; a closing reference commit in `3d-portal` records the cutover date in this repo's deploy history.
- **NFR5-CROSS-REPO-2: Epic 10 rollback story spans both repos.** Acceptance includes revert/reload in sibling repo, smoke matrix, and revert-the-revert if original smoke passed.
- **NFR5-INT-1: The `agent` role is preserved exactly.** Agent flow at `POST /api/admin/models` is unchanged; `agent` must never appear in `enforce_2fa_for_roles`; existing `admin` and `agent` rows migrate as null-op. `/agent-runbook` continues to bypass portal auth after cutover.
- **NFR5-INT-2: `/share/*` location bypass is preserved across cutover.** Share tokens remain anonymous-accessible per TTL; share and agent-runbook bypasses are preserved in nginx diff and smoke matrix.
- **NFR5-OBS-1: All new auth events produce GlitchTip-visible structured log entries.** Registration, invite, 2FA, recovery-code, password reset, and relevant fail events use existing JSON logging with namespaced loggers.
- **NFR5-OBS-2: Initiative 5 produces two named drill artifacts.** `2fa-recovery-drill-2026-MM-DD.md` for Epic 7 and `cutover-smoke-2026-MM-DD.md` for Epic 10.

### Additional Requirements

- The product is single-household and non-multi-tenant forever; multi-tenant is a hard exclusion.
- Initiative 5 replaces network-perimeter trust with invite-gated portal auth, but registration remains gated by invite tokens. There is no public read-only browse mode.
- Explicit non-goals: social login, OIDC/SSO, per-model ACLs, team/group accounts, user-to-user messaging, email self-service password reset, email deliverability checks, auth event webhooks, and multi-tenant mode.
- Existing cookie auth, refresh-token family rotation, CSRF header (`X-Portal-Client: web`), audit log helper, share-token pattern, and agent service account are baseline invariants.
- E9 security audit is a hard gate with no bypass before E10 edge cutover.
- E10 requires cross-repo coordination with `~/repos/configs` and rollback drill evidence.
- No dedicated UX document was found; UX expectations are embedded in PRD, Architecture, Epics, and existing frontend conventions.

### PRD Completeness Assessment

The PRD is complete enough for traceability validation. Initiative 5 has explicit FR/NFR identifiers, verifiable acceptance language, clear non-goals, hard security gates, cross-repo cutover constraints, and preserved baseline invariants. Main readiness risks to validate in later steps are not PRD absence but alignment risks: architecture/epics must preserve the hard audit gate, cross-repo rollback drill, member permission boundary, 2FA/agent exclusion invariant, and invite-token dual-backed storage model.

## Step 3: Epic Coverage Validation

### Epics Read Coverage

The whole epics document was read from `_bmad-output/planning-artifacts/epics.md` (1986 lines). It contains a project-global initiatives ledger with Initiative 0 retrospective E0, shipped Initiatives 1-3 (E1-E5), and active Initiative 5 planning scope (E6-E10).

### Epic FR Coverage Extracted

| Initiative | PRD FR Count | Epic Coverage Extracted | Coverage Mode |
|---|---:|---:|---|
| Initiative 0 | 29 | 29 | Retrospective E0 ledger points to shipped code + v1 design/plan; no new stories recreated |
| Initiative 1 | 30 | 30 | Explicit FR Coverage Map maps FR1-FR30 to E1-E3 |
| Initiative 2 | 11 | 11 | Epic 4 coverage statement maps FR1-FR11 to E4; story sections provide implementation scope |
| Initiative 3 | 17 | 17 | Epic 5 coverage statement maps FR1-FR17 to E5; story sections provide implementation scope |
| Initiative 5 | 24 | 24 | Explicit FR↔Epic coverage matrix maps all FR5-* to E6-E10 |

### Coverage Matrix

#### Initiative 5 Active-Scope FR Coverage

| FR Number | PRD Requirement | Epic Coverage | Status |
|---|---|---|---|
| FR5-INVITE-1 | Admin can generate single-use invite tokens with TTL and dual-backed Redis + DB storage | E6 stories 6.1, 6.2, 6.3 | Covered |
| FR5-INVITE-2 | Admin can list active and historical invites | E6 story 6.3; E8 story 8.6 | Covered |
| FR5-INVITE-3 | Admin can revoke active invite; revoked token not consumable | E6 stories 6.2, 6.3; E8 story 8.6 | Covered |
| FR5-INVITE-4 | Used invite token is single-use; replay fails closed | E6 story 6.2 | Covered |
| FR5-REGISTER-1 | Public `/register?token=` accepts valid unused token; invalid token fails with audit | E6 story 6.4 | Covered |
| FR5-REGISTER-2 | Registration captures email/password and enforces password strength | E6 story 6.4 | Covered |
| FR5-REGISTER-3 | Successful registration creates invite-bound user and standard cookies | E6 story 6.4 | Covered |
| FR5-MEMBER-1 | Member role grants browse, viewer, and share-link generation | E6 story 6.5 | Covered |
| FR5-MEMBER-2 | Member denied all admin and audit surfaces | E6 story 6.5 | Covered |
| FR5-MEMBER-3 | Member share-token rate limit and daily cap | E6 story 6.7; E9 story 9.2 audit verification | Covered |
| FR5-2FA-1 | User enrolls TOTP with mandatory recovery codes | E7 stories 7.1, 7.2 | Covered |
| FR5-2FA-2 | Login extends with second-factor step | E7 story 7.3 | Covered |
| FR5-2FA-3 | 2FA enforcement config excludes agent role fail-fast | E7 story 7.4 | Covered |
| FR5-2FA-4 | User regenerates recovery codes and disables TOTP | E7 story 7.5 | Covered |
| FR5-ADMIN-1 | Admin panel adds `/admin/users` and `/admin/invites` tabs | E8 stories 8.2, 8.6 | Covered |
| FR5-ADMIN-2 | Per-user admin actions emit matching audit events | E8 stories 8.3, 8.4 | Covered |
| FR5-ADMIN-3 | Admin-issued password reset link mirrors invite-token shape | E8 story 8.5 | Covered |
| FR5-ADMIN-4 | Bulk user operations deliberately not in v1 panel UI | Deliberate exclusion documented in Initiative 5 FR matrix and Epic 8 scope | Covered as non-implementation constraint; strengthen in story AC later |
| FR5-AUDIT-1 | 16 audit-log actions emitted via existing `record_event()` | Cross-cuts E6, E7, E8 | Covered |
| FR5-RATELIMIT-1 | Rate-limit middleware for login, refresh, register | E6 story 6.6; E9 story 9.2 audit verification | Covered |
| FR5-RATELIMIT-2 | Per-member share-token cap in rate-limit family | E6 story 6.7; E9 story 9.2 audit verification | Covered |
| FR5-CUTOVER-1 | Atomic sibling nginx edit drops `auth_basic` + IP allowlist | E10 stories 10.2, 10.3 | Covered |
| FR5-CUTOVER-2 | Four-scenario post-reload smoke matrix | E10 stories 10.1, 10.3 | Covered |
| FR5-CUTOVER-3 | Single-command rollback within <=30 seconds, drill required | E10 story 10.3 | Covered |

#### Cross-Initiative Coverage Notes

- Initiative 0 is deliberately retrospective. Its FR0-* requirements are covered by E0 ledger references to shipped code, `docs/design/2026-04-29-portal-design.md`, and `docs/plans/2026-04-29-portal-v1-implementation.md`, not by recreated story acceptance criteria.
- Initiative 1 has the strongest historical traceability: explicit FR1-FR30 coverage map plus NFR/AR mapping into E1-E3.
- Initiative 2 and Initiative 3 use pointer-style requirements inventories plus explicit `Coverage: 11/11` and `Coverage: 17/17` statements, with detailed story sections below. This is acceptable for shipped history, but not the preferred shape for new planning.
- Initiative 5 uses the preferred forward-looking shape: explicit FR↔Epic matrix, NFR↔Epic matrix, epic list, story list, gate dependencies, and architecture decision anchors.
- Unprefixed FR labels are reused across Initiatives 1-3 (`FR1`, `FR2`, etc.). Traceability is safe only when namespaced by initiative. Initiative 5 avoids this by using `FR5-*`.

### Missing Requirements

No PRD functional requirement is completely missing from the epics document.

Two coverage-strength observations should be carried forward:

- **FR5-ADMIN-4 is covered as a deliberate exclusion, not a story.** This is not a missing implementation requirement, but when Story 8.2 / 8.3 is created, add a negative acceptance check that the Users panel exposes no bulk controls (`select all`, bulk role change, bulk disable).
- **Historical Initiatives 0/2/3 use pointer/coverage-statement traceability.** This is acceptable for shipped baseline, but new forward-looking initiatives should continue the Initiative 5 explicit matrix pattern.

### Coverage Statistics

- Total PRD FRs: 111
- FRs covered in epics: 111
- Coverage percentage: 100%
- Active Initiative 5 PRD FRs: 24
- Active Initiative 5 FRs covered in epics: 24
- Active Initiative 5 coverage percentage: 100%

## Step 4: UX Alignment Assessment

### UX Document Status

Dedicated UX document: **Not found**.

Searches performed:

- `_bmad-output/planning-artifacts/*ux*.md`: no matches
- `_bmad-output/planning-artifacts/*ux*/index.md`: no matches
- UI/UX terms were found inside PRD, Architecture, and Epics.

### UX Implied Assessment

UX is clearly implied. Initiative 5 is a user-facing web-app change with:

- Public `/register?token=<token>` route and registration form.
- `/settings/2fa` enrollment, TOTP verify, recovery-code display, recovery-code regeneration, and disable-2FA flows.
- Login partial-auth second-factor screen.
- Public `/reset-password?token=<token>` route.
- Admin `/admin/users` and `/admin/invites` tabs with paginated tables, filters, modals, copy-friendly invite/reset links, and per-row action menus.
- Visual regression and axe contrast expectations inherited from Initiative 3.

### Alignment Findings

| Area | PRD Need | Architecture / Epics Support | Status |
|---|---|---|---|
| Registration | Public invite-token form with invalid/consumed/weak-password states | Architecture Decisions A/B define token semantics; Epic story 6.4 defines React route, API, error states, redirect, and visual baselines | Aligned |
| Member permissions | Member can browse/view/mint share token, but not admin/audit | Architecture Decision C provides route allowlist and `current_member_or_admin`; Epic story 6.5 tests allow/deny paths | Aligned |
| 2FA enrollment | QR/manual secret, one-time recovery-code display, no redisplay | Architecture Decisions D/E define secret/recovery-code model; Epic story 7.2 defines `/settings/2fa` UI and one-time display | Aligned |
| 2FA login | Partial-auth flow before cookie issue | Architecture Decision F covers enforcement; Epic story 7.3 defines frontend second-factor prompt | Aligned |
| Recovery-code lifecycle | Regenerate/disable with re-auth | Architecture Decision E supports lifecycle; Epic story 7.5 defines UI panel + re-auth modal | Aligned |
| Admin users/invites | Two tabs, columns, pagination, filters, per-row actions | Architecture Decisions A/B/I support data; Epic stories 8.2, 8.3, 8.4, 8.6 define React routes and states | Aligned |
| Reset password | Admin-issued reset link, public reset route, password strength gates | Architecture reuses token shape; Epic story 8.5 defines reset route and form | Aligned |
| Visual quality | UI changes must ship with baselines; axe contrast active | Initiative 3 baseline gates exist; Epic stories call out visual-regression baselines for new routes | Aligned |
| Edge cutover UX | After nginx cutover, anonymous catalog should challenge at portal auth, share remains public | Architecture Decision K and Epic 10 smoke matrix verify share bypass, member/admin/agent auth paths | Aligned |

### Alignment Issues

- **Warning: no dedicated UX artifact exists despite multiple new UI flows.** The PRD and epics carry enough UI behavior to proceed, but there is no single UX document for screen inventory, state matrix, or form copy.
- **Warning: architecture is backend/security-heavy and does not provide a compact frontend route/component map.** Epics fill the gap by naming routes/components, but implementation stories should preserve this detail when generated.
- **Coverage-strength item: `FR5-ADMIN-4` needs a negative UI check.** Epics mark bulk user operations as deliberate exclusion, but Story 8.2 or 8.3 should explicitly verify no bulk controls are exposed.

### Warnings

- Missing UX doc is a **readiness warning, not a blocker**, because the active Initiative 5 UI requirements are embedded in PRD + Epics and supported by Architecture decisions.
- When creating executable stories, include explicit UI state acceptance criteria for: invalid invite, consumed invite, expired invite, weak password, email already taken, partial-auth TOTP required, wrong TOTP, recovery-code consumed, no recovery codes remaining, reset-token invalid/expired, inactive user, and member/admin permission denial.
- Ensure all new visible copy is added to `apps/web/src/locales/en.json` and `pl.json`; this is not a UX-doc issue but is an implementation constraint from project context.

## Step 5: Epic Quality Review

### Review Scope

Reviewed all epics in `_bmad-output/planning-artifacts/epics.md`, with emphasis on the active Initiative 5 forward-looking scope (E6-E10). Initiative 0 is retrospective and explicitly marked as a non-template exception; Initiatives 1-3 are shipped history and were reviewed for structural lessons rather than readiness blockers.

### Best-Practice Checklist Summary

| Epic | User Value | Independent From Future Epics | Story Dependencies | Story Sizing | AC Quality | Traceability |
|---|---|---|---|---|---|---|
| E0 | Exception: retrospective technical ledger | N/A | N/A | N/A | N/A | Pointer-based |
| E1-E3 | Pass | Pass | Pass | Historical | Historical | Strong explicit matrix |
| E4 | Pass | Pass | Pass | Historical | Historical | Pointer + status table |
| E5 | Pass | Pass | Historical issue documented and corrected by forward principles | Historical | Historical | Pointer + status table |
| E6 | Pass | Pass | Pass | Mixed; several technical/enabling stories | Planning-level AC | Strong |
| E7 | Pass | Pass | Pass | Mixed; 7.1 technical/enabling | Planning-level AC | Strong |
| E8 | Pass | Pass | Mostly pass; one ambiguity in 8.5 | Mixed; 8.5 may be large | Planning-level AC | Strong |
| E9 | Process/gate epic, justified exception | Pass; blocks E10 by design | Pass | 9.2 may be large | Planning-level AC | Strong |
| E10 | Pass | Requires E9 gate by design | Pass | Operationally high-risk but bounded | Planning-level AC | Strong |

### Critical Violations

None found.

No forward dependency breaks the Initiative 5 sequence. E6 → E7 → E8 → E9 → E10 is explicit, and E10's dependency on E9 audit PASS is intentional and load-bearing.

### Major Issues

#### M1 — Initiative 5 story sections are not executable story specs yet

**Evidence:** Story sections use "Acceptance check shape" bullets rather than full Given/When/Then acceptance criteria. The epics section itself says granular per-step acceptance criteria are deferred to `bmad-create-story`.

**Impact:** Implementation should not start directly from `epics.md`; otherwise agents will fill in edge cases ad hoc, especially around UI states and auth/security failure modes.

**Recommendation:** Treat E6-E10 as sprint-planning-ready, not dev-ready. Before implementation, run `bmad-create-story` per story and expand ACs into testable Given/When/Then format.

#### M2 — Several Initiative 5 stories are technical/enabling rather than user-value stories

**Examples:**

- Story 6.1 — Alembic migration `0012_invite_tokens` + invite-token primitives.
- Story 7.1 — Alembic migration `0013_users_2fa_columns` + recovery-codes table + Fernet key plumbing.
- Story 8.1 — Alembic migration `0014_users_is_active_last_active` + `LastActiveMiddleware`.
- Story 9.1 — audit tooling install + baseline run.
- Story 10.1 — fixture seeding + `cutover-smoke.sh` authoring.

**Impact:** These are valid brownfield enabling slices, but they violate the pure "each story delivers direct user value" ideal. If executed as independent user stories, reviews may falsely treat them as complete product increments.

**Recommendation:** When creating executable story files, either merge pure migrations into the first user-visible story that consumes them, or explicitly label them as enabling stories with a clear downstream user outcome and immediate verification command. Do not let them become unreviewed "technical setup" sinkholes.

#### M3 — E9 is a process/gate epic, not direct product value

**Evidence:** E9 title and goal are "Security audit — HARD GATE"; it produces audit artifacts and blocks E10, rather than exposing a user-facing capability.

**Impact:** This is a best-practice exception. It is justified by the planned auth boundary cutover and by the PRD's explicit "audit is an epic" stance, but future agents may cargo-cult "audit epic" for lower-risk work.

**Recommendation:** Keep E9 as-is for Initiative 5 because it is a deliberate security hard gate before public exposure. Add a short note in final readiness that E9 is an approved exception, not a pattern for ordinary feature work.

#### M4 — Story 8.5 has an ambiguous dependency around admin-disabled 2FA recovery

**Evidence:** Story 8.5 says the lost-2FA path uses "operator force-disables 2FA... note this is a NEW use case for the existing 7.5 disable endpoint; admin invocation already supported via the existing `current_admin` dependency on a planned admin-disable path or surfaced via 8.5 link path."

**Impact:** "Already supported" vs "planned admin-disable path" is ambiguous. This can cause implementation drift in the admin lockout-recovery flow.

**Recommendation:** In the executable story for 8.5, explicitly decide where admin force-disable-2FA lives: a dedicated admin endpoint/action in 8.5, or a separate story before 8.5. Do not leave it to implementation discretion.

#### M5 — Story 9.2 is broad enough to split if audit execution expands

**Evidence:** Story 9.2 covers six security scenarios: invite brute force, refresh replay, CSRF/JWT tampering, IDOR, rate-limit benchmark, and member share amplification.

**Impact:** It is coherent as an audit scenario batch, but if any scenario produces findings, the story can balloon into a fix sprint inside the audit story.

**Recommendation:** Keep 9.2 as an audit-execution story, but if any scenario fails, create separate fix stories via BMAD correct-course / follow-up sprint rather than expanding 9.2.

### Minor Concerns

#### m1 — FR5-ADMIN-4 needs a negative UI acceptance check

FR5-ADMIN-4 is covered as a deliberate exclusion, but no story acceptance bullet currently says the panel must expose no bulk controls. Add this to Story 8.2 or 8.3.

#### m2 — Initiative 5 lacks a compact frontend route/component map

PRD and epics name routes/components, but architecture focuses on backend/security decisions. For executable stories, include exact frontend module placement, i18n keys, and visual test names.

#### m3 — Historical sections reuse plain `FR1`, `FR2` labels

Initiatives 1-3 reuse local FR numbering. This is safe only with initiative context. New work should continue the `FR5-*` prefixed pattern.

### Dependency Analysis

No forward dependencies were found in the active Initiative 5 sequence:

- E6 stories progress from storage/service to endpoints/UI, permissions, and rate-limits.
- E7 stories progress from schema/keying to enrollment, login verify, enforcement, recovery lifecycle, and drill.
- E8 depends on E6/E7 where appropriate and progresses from user columns/list to actions and invite UI.
- E9 depends on E6-E8 by design and blocks E10.
- E10 progresses from fixtures/smoke script to sibling nginx commit, cutover execution/rollback drill, and closing operations commit.

Database/entity creation timing is appropriate: tables/columns are introduced at first need (`0012` invite tokens, `0013` 2FA/recovery codes, `0014` user active/last-active). There is no "create all tables upfront" anti-pattern.

### Quality Recommendations

1. Run `bmad-create-story` before dev starts; do not implement directly from `epics.md`.
2. Expand every Initiative 5 story into Given/When/Then ACs, especially failure states and security boundaries.
3. Merge or clearly label technical enabling stories so user value remains visible.
4. Add a negative no-bulk-controls check for `FR5-ADMIN-4`.
5. Resolve the admin force-disable-2FA path before or inside Story 8.5.
6. Keep E9 as an explicitly approved security exception, and split fix work out of E9 if findings appear.

## Summary and Recommendations

### Overall Readiness Status

**NEEDS WORK before direct implementation. READY for sprint planning / story creation.**

The planning artifacts are strong enough to proceed to the next BMAD planning stage, but they are not yet executable implementation stories. The key distinction:

- PRD / Architecture / Epics alignment: **ready**
- FR coverage: **ready** (111/111 total; Initiative 5 24/24)
- UX documentation: **warning, acceptable with story-level state expansion**
- Epic/story quality for implementation: **needs work** because Initiative 5 story sections are planning-level and must be expanded through `bmad-create-story`

### Critical Issues Requiring Immediate Action

No critical blockers were found.

### Issues Requiring Attention Before Implementation

1. Initiative 5 stories are not executable story specs yet; they need Given/When/Then ACs through `bmad-create-story`.
2. Technical/enabling stories need explicit downstream user value or should be folded into user-facing stories.
3. Story 8.5 has an ambiguous admin force-disable-2FA path that must be resolved before that story is implemented.
4. Story 9.2 should stay audit-only; any failed audit scenario must create fix stories rather than expanding the audit story.
5. Missing UX document means UI state coverage must be added at story-creation time.
6. `FR5-ADMIN-4` needs a negative UI acceptance check: no bulk controls exposed in the Users panel.

### Recommended Next Steps

1. Proceed to `bmad-sprint-planning` to create/update sprint status for E6-E10.
2. Before any dev work, run `bmad-create-story` for the first implementation story and expand acceptance criteria into full Given/When/Then.
3. Add a story-creation checklist for Initiative 5 UI stories: route placement, component placement, i18n keys, visual spec/baseline requirements, and every error/empty/loading state.
4. Resolve the Story 8.5 force-disable-2FA ambiguity in the story file, not during implementation.
5. Preserve E9 as a hard-gate security exception and keep the no-bypass rule intact.
6. Carry the `FR5-ADMIN-4` negative check into Story 8.2 or Story 8.3.

### Final Note

This assessment identified **0 critical blockers**, **5 major issues**, and **3 minor concerns** across four categories: document discovery, requirements coverage, UX alignment, and epic/story quality. The artifacts are aligned enough for sprint planning, but direct implementation should wait until executable story files exist.

**Assessor:** Codex, using `bmad-check-implementation-readiness`
**Assessment date:** 2026-05-19
