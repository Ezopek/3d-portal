---
title: "Product Brief: 3d-portal — Public Registration & User Account Management (Initiative 5)"
type: product-brief
initiative: 5
status: complete
created: 2026-05-18
last_updated: 2026-05-18
author: Ezop (operator) + Claude (BMAD planning chain)
mode: guided
revision_notes: |
  v2 (2026-05-18) — adversarial review pass applied. Fixed P0×2 (gate authority +
  max accepted-Medium cap; member share-link amplifier in Epic 5.4 threat model)
  + P1×3 (admin-issued reset link OOB delivery + lost-2FA-AND-recovery-codes
  workflow; SC#5 concretized to artifact + environment + drill content;
  cross-repo cutover smoke matrix) + P2×1 (invite hygiene operator-manual
  statement + bulk-user-deactivate DB-direct in v1).
related_artifacts:
  - product-brief-3d-portal-user-accounts-distillate.md  # produced at finalize, if requested
  - prd.md (to be extended with `## Initiative 5` section)
  - architecture.md (to be extended with `## Initiative 5` section)
  - epics.md (Epics 5.1 — 5.5; numbering convention finalized at PRD time)
---

# Product Brief: Public Registration & User Account Management

## Executive Summary

3d-portal today admits exactly two principals: `admin` (Michał) and `agent` (the AI service account). All household browse access is gated at the edge by nginx IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`, covering homelab LAN + VPN); there is no notion of a per-person login for anyone who is not Michał. The portal already ships with a `member` role in the User enum (`apps/api/app/core/db/models/_enums.py:10-13`), a complete cookie+JWT auth stack (`portal_access` 10min + `portal_refresh` 30d with family rotation, CSRF via `X-Portal-Client: web`), an audit log with first-class auth-event taxonomy, and a Redis-backed share-token implementation that is the perfect template for invite tokens — but no path for a person who is not Michał to obtain an account.

Initiative 5 closes that gap. It opens the portal to a curated friends-and-family circle via invite-link registration (single-use tokens with operator-chosen TTL, pre-bound role, audit trail), adds optional TOTP 2FA with mandatory recovery codes, ships an admin panel for user + invite lifecycle management, and — gated by a hard pre-cutover security audit — drops the nginx edge gate so the portal authenticates itself rather than relying on the homelab network perimeter. The agent role is preserved exactly. The admin role is preserved exactly. The new surface is one role (`member`), one registration flow, one 2FA enrollment flow, one admin panel, one network-perimeter cutover.

The work is bounded to five sequenced epics. Three are feature-build (5.1 member + invite, 5.2 2FA, 5.3 admin panel). One is a defensive gate (5.4 security hardening — the load-bearing epic, blocks 5.5). One is the cutover itself (5.5, atomic). No epic touches share-token storage, content ingestion, or the render pipeline. Initiative 0 (foundation) and Initiative 2 (agent runbook) continue to function unchanged.

## The Problem

**Current state.** The portal serves a single household. Everyone who needs to browse the catalog either (a) is on the home LAN and falls inside the nginx IP allowlist, or (b) uses Michał's admin login. Neither path works for a friend who is outside the household network and wants to look at curated models without Michał manually screen-sharing or exporting STLs. The two coping mechanisms today — sending a portal screenshot in Messenger, or generating a one-off `/share/<token>` link per model — both shift the discovery burden onto Michał and leave the recipient with no persistent "place to come back to."

**Why a per-account system, not just more share links.** Share-tokens are point-to-point and TTL-bound — perfect for "look at this one model" but actively wrong for "browse my collection, come back next week, send me a print request." Stretching share-tokens to cover persistent access multiplies the operator's link-management overhead and grants every URL recipient ambient permission to anyone they forward the link to.

**Why now.** The downstream `member-print-requests` capability (real intent confirmed in `prd.md` 2026-05-15, currently parked) cannot ship until a per-user identity model exists. Initiative 5 is the gate. Every future capability that needs "who asked for this" — print requests, per-user prints log, favorites, comments — is blocked until member accounts exist.

**What we are NOT solving.** This initiative is not a public portal launch. The first wave is explicitly friends-and-family — ~10-20 people realistically in the first 90 days. The portal remains gated; invite-only registration replaces IP allowlist as the gate, not as a removal of the gate.

## The Solution

Five sequenced epics under one initiative. Each is a discrete BMAD epic with its own stories and acceptance criteria; the sequencing is the load-bearing structure (5.4 is a hard gate before 5.5).

**Epic 5.1 — Member role + invite-based registration.** FastAPI + DB + UI for the core flow: admin generates a single-use invite link (TTL preset 1d/3d/7d/30d + custom, pre-bound role default `member`, 256-bit `secrets.token_urlsafe(32)`); recipient lands on `/register?token=<token>`, supplies email + password (zxcvbn ≥3, ≥12 chars), gets the pre-bound role. Token storage mirrors the share-token pattern (Redis primary at `invite:token:{token}` for active/TTL/revoke, DB row in a new `invite_tokens` table for audit history). Member role gains: catalog browse + 3D viewer + share-link generation. Member does NOT get: audit log read, agent-runbook access, admin endpoints. Auth events extend AuditLog: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`.

**Epic 5.2 — 2FA TOTP + recovery codes.** TOTP enrollment via `pyotp` + QR display (manual secret fallback). At enrollment, 8 single-use recovery codes are generated, shown once, hashed at rest. Optional by default; enforced per-role via a `enforce_2fa_for_roles: list[Role]` config flag (default `[]`, agent role must never be in this list); admin can force-enroll any individual user via the admin panel. Login flow extends with a second-factor step when the user has TOTP enabled. Recovery code consumption is one-way and audit-logged.

**Epic 5.3 — Admin panel: users + invites.** Two tabs in the existing admin UI: **Users** (list with email, role, created_at, last_active_at, 2FA-enabled flag, is_active; actions: change role, force-2FA-enrollment, reset password via one-time link, deactivate via `is_active=False`, force logout-all) and **Invites** (list with status active/used/expired/revoked, generated_by, used_by, used_at, used_from_ip; actions: generate new invite + revoke active invite). All admin actions audit-logged via the existing `record_event()` helper.

**Epic 5.4 — Security hardening pre-cutover (HARD GATE blocking 5.5).** Formal pre-cutover audit. Tooling stack: `bandit` (Python SAST), `semgrep` (multi-lang with OWASP top-10 rulesets), `pip-audit` + `npm audit`/`osv-scanner` (deps), OWASP ZAP active scan against `.190`, `codex review` on the new auth/invite/2fa modules. Scenario coverage: invite-token brute force (must hit rate-limit before exhausting entropy of 32-byte token by a margin of ≥10⁶), refresh-token replay against the family rotation logic, CSRF/JWT tampering, IDOR on every admin endpoint, **rate-limit verification on `/api/auth/login`, `/api/auth/refresh`, and `/api/auth/register?token=`** (operator explicit raise — concern: brute-force exposure post-LAN-whitelist-drop), and **share-token abuse from a compromised-or-malicious member account** (rate-limit + volume cap on `/api/share/*` POST per-member; member-amplified public-link distribution is the asymmetric risk introduced by Epic 5.1's permission expansion — see Working Assumptions). Every finding triages to fix-before-cutover OR explicit-defer-with-mitigation. Gate condition: zero open Critical/High findings; Medium findings either fixed or mitigated with documented compensating control, with a max-accepted-Medium cap and signing authority defined in Working Assumptions.

**Epic 5.5 — Edge cutover.** Atomic switch: drop nginx basic-auth AND IP allowlist in the same change. Touch is in the sibling repo `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (the live config is NOT in `3d-portal`). Portal authenticates itself via FastAPI middleware/route guards; nginx becomes a thin reverse proxy + TLS terminator + share-bypass rewrite. The `/share/*` and `/agent-runbook` paths continue to skip portal auth (already designed). Rollback path: revert the single config commit + `nginx -s reload`. Estimated cutover window: 5 minutes including rollback test.

## What Makes This Different

- **Building on a thick existing baseline, not greenfield.** Cookie+JWT auth, family-based refresh rotation with reuse detection, CSRF middleware, AuditLog with `record_event()` helper, share-token Redis pattern, password hashing, role enum (with `member` already enumerated) all ship today. Initiative 5 is mostly additive: new `invite_tokens` table, 2FA columns + recovery_codes table, two new admin pages, ~14 new audit-log actions, one nginx config change. Estimated diff: ~3-4 Alembic migrations, ~6 new modules in `apps/api/app/modules/`, ~4 new React routes/pages, ~1 sibling-repo config edit.
- **The cutover is the smallest change in the initiative.** Drop two nginx directives; portal auth was already there. The bulk of the work is the security audit that lets us trust the cutover, not the cutover itself.
- **Member's permission expansion is one bit.** `member` can generate `/share/<token>` links. That is the only permission member gains above today's anonymous-LAN-browser. No per-model ACL, no team accounts, no messaging, no comments. The simplicity is the moat.
- **The agent role is sacrosanct.** Initiative 2's runbook + cookie+password agent flow is unchanged. The agent service account does NOT get 2FA forced. Migration of existing `admin` (Michał) and `agent` (AI) rows is null-op: schema additions only, no data rewrite.
- **Security audit is an epic, not a story.** Per `feedback_default_to_bmad_workflow.md`: multi-PR security batches from review docs are epics in disguise. Epic 5.4 is one epic with a hard-gate exit criterion, not a cleanup pass piggybacked onto Epic 5.5.
- **The audit cost is paid before the network perimeter drops, not after.** Operator's banking-IT instinct prioritizes account-takeover and infra-leak as top-feared failures. The audit gate ensures the public DDNS surface is hardened before basic-auth and the IP allowlist come off.

## Who This Serves

**Primary: Ezop (operator).** Per Q3 framing: "first targetem portalu jestem ja ostatecznie." The win is not external user count — it is reducing operator-side friction of "show this model to my brother" from "screenshot + Messenger" to "I sent him an invite once; he checks the catalog whenever, comes back with concrete links." Success is leading-indicator (people log in, people send requests), not output-metric (DAU/MAU). The operator is honest about this — friends/family may simply not engage, and the portal still has to be a daily-driver curation engine for Michał regardless.

**Secondary: Friends-and-family (~10-20 people realistically in the first 90 days).** Curated trust circle. Their value (per Q2): a central place where they see models that Michał can print for them, can return to it, can send Michał concrete links to specific curated models. Later, when print-requests ships, the same portal becomes the request channel — replacing Messenger threads with structured asks.

**Preserved exactly as-is: agent (AI service account).** Continues ingesting models via `/api/admin/models`. Continues using cookie+password flow. Does not get 2FA enforced. Does not see the new admin panel from a permission standpoint. Auth flow unchanged.

**Explicitly NOT served in v1:** wider hobby-print community (Reddit/Discord), public read-only browsers, federated identities (Authentik OIDC), team/group accounts, per-model ACL recipients, user-to-user messaging. These all remain on the long-tail roadmap; Initiative 5 deliberately does not pre-build for them.

## Success Criteria

Leading-indicator-first, observable from the admin panel itself. Per Q3 framing, success is operator-side reduction-of-friction, not external engagement metrics.

1. **First-wave activation:** within 30 days of cutover (5.5 close), at least 5 invites generated, at least 3 invites consumed, at least 2 distinct member users with non-null `last_active_at` updated in the last 7 days. (Floor, not stretch.)
2. **Admin panel handles routine ops without DB poking.** All four core admin actions (generate invite, revoke invite, change user role, reset user password) are exercised through the panel UI at least once in the first 30 days; zero panel-triggered operations require SQL inspection to complete.
3. **Zero account-takeover incidents in the first 90 days.** No `auth.refresh.reuse_detected` events for non-attacking causes (UA churn excluded via existing 30s grace); no `auth.login.fail` patterns matching credential-stuffing (≥10 failures from one IP across ≥3 emails within 5 min).
4. **Epic 5.4 audit produces a clean cutover artifact.** Pre-cutover audit report at `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md` shows zero open Critical/High findings at the moment of 5.5 deployment. Every Medium has documented disposition (fixed / mitigated / accepted-with-rationale).
5. **2FA enrollment + recovery-code path is drill-verified against `.190`.** Epic 5.2 ships with a documented end-to-end recovery-code drill artifact at `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-MM-DD.md`, executed against the deployed `.190` instance (NOT against CI fixtures). The drill steps: enroll a test user → log out → log in with TOTP → consume a recovery code in place of TOTP → regenerate recovery codes → disable TOTP → verify normal login still works. Artifact captures timestamps, request IDs, and AuditLog row deltas. First-wave adoption by real members is intentionally NOT an SC — operator-side framing per Q3 ("path works, not adoption").
6. **Rate-limit holds the line on `/api/auth/login`.** Post-cutover, the endpoint rejects ≥5 rapid failures from one IP within 60 seconds with HTTP 429. Verified by `siege`/`hey` benchmark in the audit, reproducible on demand.

## Scope

**In:**
- New `invite_tokens` DB table + Redis-fronted storage + admin endpoints + UI for generate/list/revoke.
- New `/register?token=<token>` public route + form (email, password with zxcvbn ≥3 ≥12-char check, token validation).
- New `member` role permission scope: catalog browse, viewer, share-link generate. Member-blocked: admin/*, agent-runbook, audit log read.
- Extension of `current_admin` dependency family with a `current_member_or_admin` variant for shared resources; share-router auth expanded from `admin`-only to `{admin, member}`.
- 2FA columns on `users` table (`totp_secret`, `totp_enabled_at`); recovery-codes table; 2FA enrollment route + UI (QR + manual secret); `enforce_2fa_for_roles` config flag.
- Admin panel: Users tab + Invites tab; React routes under `apps/web/src/modules/admin/`.
- `is_active: bool` soft-delete column on `users` + `last_active_at: datetime` column (throttled write ≤1/5min).
- Rate-limit middleware on `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`. Tunable thresholds in config. Redis-backed sliding-window (architecture decision at PRD time).
- Security audit tooling: bandit, semgrep, pip-audit, npm/osv-scanner, OWASP ZAP, codex review. Outputs as artifacts in `_bmad-output/implementation-artifacts/`.
- Nginx edge cutover: edit `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (sibling repo) — drop `auth_basic` + IP allowlist; preserve share bypass + agent-runbook bypass. Atomic single commit + reload.
- New audit-log actions added to `KNOWN_ENTITY_TYPES`: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`, `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`, `auth.password.reset.initiated`, `auth.password.reset.completed`, `user.deactivated`, `user.reactivated`, `user.role_changed`, `user.force_logout`.

**Out (explicit non-goals — all confirmed by operator at elicitation Q5):**
- Social login (Google/GitHub/etc.) — native accounts only.
- OIDC/SSO federation (Authentik in homelab) — `member-print-requests` initiative may revisit.
- Per-model ACL (member X sees subset of catalog) — all-or-nothing access for `member` role.
- Team/group accounts.
- User-to-user messaging.
- Public read-only browse mode — portal stays gated by login; `/share/*` is the only escape hatch.
- Self-service password reset via email — blocked on self-hosted mail server (separate future initiative).
- Email deliverability verification — RFC format validation only.
- Webhook/event push to external systems on auth events.
- Multi-tenant. (One household, one SoT, one admin, multiple members.)

## Vision

**Initiative 5 close (target: 4-6 weeks total, 5 epics back-to-back).** Portal is invite-gated. First wave (~5-10 people) onboarded. Admin panel is operator's daily-driver for user ops. Nginx is a thin TLS + proxy + share-bypass layer.

**+90 days post-cutover.** Per Q3 framing — first-wave members either engage (login signal + ad-hoc print requests via Messenger as a placeholder channel) or they don't (also acceptable; operator-side win still holds). 2FA path proven through ≥1 enrollment OR ≥1 force-enroll OR ≥1 recovery-code drill.

**+6 months / Initiative 6 candidate.** `member-print-requests` unblocked — every print request is now `request.user_id` not "Michał has to remember whose Messenger thread this came from." Per-user prints log becomes feasible. Per-user favorites tag becomes feasible.

**+12 months (vision, not commitment).** Self-hosted mail server arrives → self-service password reset → email deliverability checks → possibly widening the first-wave from friends-and-family to a moderated hobby-print community. Each step is its own initiative; Initiative 5 deliberately stops at the friends-and-family threshold.

The vision is intentionally cautious. The portal is one operator's curation engine. Growth is opt-in by the operator, not by the platform.

---

## Working assumptions (challenged during discovery; surviving into PRD)

- **Member's share-generation permission is a new permission expansion.** Today share creation is admin-only (`apps/api/app/modules/share/admin_router.py`). Initiative 5 extends share creation to `{admin, member}`. This is a deliberate scope-in per Q1/Q2 framing (members forwarding curated catalog links to Michał + to each other).
- **Existing admin (Michał) and agent (AI) rows are preserved with null-op migration.** Schema additions only (new nullable columns + new tables). No data rewrite. Existing JWT cookie auth flow remains the primary login path; 2FA is opt-in additive.
- **The live nginx config is in a sibling repo** (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`). Epic 5.5 touches that repo, not `3d-portal`. Sprint planning must reflect the cross-repo coordination (rollback story spans two repos).
- **Rate-limit middleware is a hard requirement for cutover** (operator explicit raise at Q4). Audit Epic 5.4 must verify rate-limit on at least `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`. Implementation likely uses a Redis-backed sliding-window in middleware (`apps/api/app/core/auth/ratelimit.py`).
- **Soft-delete is the user-deletion model.** `is_active=False` + audit trail kept. Hard-delete is not exposed in the panel; available via DB only for GDPR-right-to-be-forgotten, with care for FK integrity (`audit_log.actor_user_id`, `refresh_tokens.user_id`).
- **`last_active_at` write is throttled to ≤1/5min per user** to avoid SQLite write churn. Updates happen in middleware on authenticated requests; the throttle is operationally invisible to the user.
- **2FA enforcement is a config flag, not a UI toggle.** `enforce_2fa_for_roles: list[Role]` in `apps/api/app/core/config.py`; admin can also force-enroll any individual user via the panel (per-user override). The `agent` role must never appear in `enforce_2fa_for_roles` — it is a service account.
- **Invite-token storage is dual-backed.** Redis is the source of truth for active/TTL/revoke (mirrors share-token pattern, fast); a row in the new `invite_tokens` DB table is written at generation time for audit history (who generated, when, role, expiry) and updated at use time (used_by, used_at, used_from_ip). The DB row outlives the Redis TTL — used invites are visible in the panel forever.
- **Failure to pass Epic 5.4 means Epic 5.5 does not happen.** No "yolo cutover" override. If audit finds an unfixable Critical, the cutover is parked and the issue is triaged to a fix-sprint before 5.5 runs.
- **Epic 5.4 gate authority and Medium-disposition cap.** The operator is both auditor and gate-keeper (single-operator project), which creates a self-attestation risk. Mitigation: every Medium disposition (fixed / mitigated / accepted-with-rationale) requires a documented second-opinion artifact from `codex review --commit <SHA>` against the relevant patch, OR — for "accepted-with-rationale" specifically — explicit countersignature in the audit report. **Hard cap: no more than 3 "accepted-with-rationale" Mediums across the entire Epic 5.4 audit; the 4th forces the gate to auto-fail and triggers a fix sprint.** Critical and High dispositions have no "accepted" path; fixed-or-bust.
- **Member share-link generation is a deliberate amplification surface.** Once Epic 5.1 expands `/api/share/*` POST to `{admin, member}`, a single compromised member can mint unlimited auth-bypassing public URLs to the operator's catalog. Mitigation in Epic 5.4 audit scope: per-member rate-limit + daily volume cap on share-token creation (architecture decision at PRD time; suggested floor: ≤20 share-tokens/member/day, soft-fail at 50% threshold with operator alert). Compromised-member detection lives in AuditLog query (`auth.refresh.reuse_detected` for the actor + share-creation burst correlation).
- **Admin-issued password reset link is delivered out-of-band by the operator** — same channel as the original invite (SMS / Messenger / mail-from-personal-account). The "one-time reset link" generated in Epic 5.3 is functionally identical in shape to an invite token (single-use, short TTL, Redis-fronted). When self-hosted mail server lands (separate future initiative), this path becomes self-service via mail; until then, every reset is a manual operator action.
- **Full account lockout recovery workflow (lost 2FA AND lost recovery codes).** Resolved entirely through the admin panel: operator force-disables 2FA on the user's account (audit event `auth.totp.disabled` with `actor != target` flag), then issues a one-time password-reset link. No mail-server dependency. Documented in Epic 5.3 acceptance criteria.
- **Cross-repo cutover smoke matrix.** Epic 5.5 nginx config edit lives in sibling repo `~/repos/configs/nginx/3d.ezop.ddns.net.conf` and bypasses `3d-portal`'s `deploy.sh` skip-gate logic (gitignored `infra/.last-deploy-sha`). The cutover MUST be followed immediately by a 4-scenario post-reload smoke check against `.190`: (1) anonymous GET `/share/<token>` returns 200, (2) agent service account POST `/api/admin/models` (cookie+password) returns 201, (3) member login returns 200 + `portal_access` cookie set, (4) admin login returns 200 + admin scope verified. Rollback if any of the four regress. Smoke checklist is part of Epic 5.5 acceptance criteria, not a PRD-time addendum.
- **Invite-token hygiene is operator-manual in v1.** No automated stale-invite cleanup; orphan invites (generated, never sent) live in Redis until natural TTL expiry. Operator-side hygiene is via the Invites tab in Epic 5.3 (filter by status / age / not-yet-used). No bulk-invite-revoke action in v1 admin panel — DB-direct only if needed.
- **Bulk user deactivation is DB-direct in v1.** Admin panel ships single-user `is_active=False` toggle in Epic 5.3; if a friend-group falls out of trust and 10+ users need disabling at once, that is a DB script, not a panel action. Deferred to a future admin-panel-v2 if pattern recurs.
- **Epic numbering convention is a PRD-time decision.** Either continue the existing flat scheme (Init 5 epics would be 6-10) or adopt dotted-by-initiative (5.1-5.5). The brief uses the dotted convention as working labels.

## Stakeholders consulted

- **Ezop (operator)** — locked all five top-level decisions (edge gate drop, role taxonomy, invite mechanics, 2FA approach, atomic cutover), and supplied the persona (friends-and-family), aha-moment (curated browse + return-with-link, future in-portal print-request channel), success-stance (operator-side friction reduction; honest about engagement uncertainty), and top failure fears (account takeover + brute force + infra leak + explicit rate-limit raise) in the 2026-05-18 elicitation pass.
- **Existing BMAD artifacts:** `_bmad-output/planning-artifacts/prd.md` (Initiative 0/1/2/3 baselines), `_bmad-output/planning-artifacts/architecture.md` (auth + share-token + audit-log decisions), `_bmad-output/project-context.md` (auth conventions), `AGENTS.md` (deploy contract).
- **Code recon (apps/api):** `app/core/db/models/_user.py`, `_enums.py`, `_audit.py`, `_auth.py`; `app/core/auth/` (cookies, csrf, jwt, refresh, dependencies); `app/modules/auth/router.py`; `app/modules/share/{service.py, models.py}`; latest migration `0011`.
- **Code recon (apps/web):** `src/routes/login.tsx`, `src/shell/{AuthContext.tsx, AuthGate.tsx}`, `src/lib/{api.ts, refresh.ts}`.
- **Edge infra (sibling repo):** `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (live) and `infra/nginx-180/.archived/3d-portal.conf.pre-IP-allowlist` (pre-allowlist snapshot in this repo).
- **Memory:** `feedback_default_to_bmad_workflow.md`, `feedback_brief_autonomous_skip_elicitation.md`, `feedback_invoke_codex_directly.md`, `user_role.md`, `feedback_collaboration_division.md`.

## Next step

Route to `bmad-create-prd` for PRD extension into `_bmad-output/planning-artifacts/prd.md` under new `## Initiative 5` H2 section. PRD focus: FRs/NFRs per epic (5.1-5.5), explicit acceptance criteria per epic, security-audit scope detail under 5.4 (tooling invocations + scenario list + gate condition), cross-repo cutover checklist under 5.5. Architecture extension follows as `bmad-create-architecture` — decisions to nail: invite-token schema (Redis vs DB write strategy), 2FA column shape on `users` table, recovery codes table schema, rate-limit middleware strategy (Redis sliding window vs token bucket vs leaky bucket), nginx config diff with rollback artifact.
