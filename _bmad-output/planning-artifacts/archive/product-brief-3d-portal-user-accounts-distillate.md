---
type: bmad-distillate
sources:
  - "product-brief-3d-portal-user-accounts.md"
downstream_consumer: "bmad-create-prd → bmad-create-architecture → bmad-create-epics-and-stories"
created: 2026-05-18
token_estimate: 2450
parts: 1
---

## Core Concept
- Initiative 5: open 3d-portal beyond admin+agent to friends-and-family via invite-link registration, opt-in TOTP 2FA, admin panel for user/invite lifecycle, and hard-gated nginx edge cutover (drop IP allowlist + basic-auth)
- Five sequenced epics; 5.4 is hard gate before 5.5; agent role preserved exactly; admin role preserved exactly; new surface = one role (`member`), one registration flow, one 2FA flow, one admin panel, one network cutover
- Builds on thick existing baseline: cookie+JWT auth (`portal_access` 10min + `portal_refresh` 30d family rotation), CSRF via `X-Portal-Client: web`, AuditLog `record_event()`, share-token Redis pattern, role enum already includes `member` (`apps/api/app/core/db/models/_enums.py:10-13`)
- Estimated diff: ~3-4 Alembic migrations, ~6 new modules in `apps/api/app/modules/`, ~4 new React routes/pages, ~1 sibling-repo nginx config edit; 4-6 weeks total

## Problem
- Current state: nginx IP allowlist gates household at edge (`192.168.2.0/24` + `10.8.0.0/24`); only `admin` (Michał) + `agent` (AI) can log in; no path for off-network friend without screen-share or per-model `/share/<token>` link
- Coping today: Messenger screenshots; one-off share links — both shift discovery burden to operator, no persistent return-place for recipient
- Why not stretch share-tokens: point-to-point + TTL-bound; persistent access via share-tokens multiplies link-management overhead + grants ambient permission to any forward-recipient
- Why now: downstream `member-print-requests` capability (parked in `prd.md` 2026-05-15) blocked until per-user identity exists; every future "who asked" capability (favorites, comments, per-user prints log) gated on this
- Not solving: public portal launch; first wave is explicitly friends-and-family ~10-20 in first 90 days; portal stays gated, invite-only replaces IP allowlist as gate

## Epic 5.1 — Member role + invite-based registration
- FastAPI + DB + UI for core flow: admin generates single-use invite (TTL preset 1d/3d/7d/30d + custom, pre-bound role default `member`, 256-bit `secrets.token_urlsafe(32)`)
- Recipient lands `/register?token=<token>`, supplies email + password (zxcvbn ≥3, ≥12 chars), gets pre-bound role
- Token storage dual-backed: Redis primary at `invite:token:{token}` (active/TTL/revoke, mirrors share-token); DB row in new `invite_tokens` table for audit history (who generated, when, role, expiry; updated at use with used_by/used_at/used_from_ip); DB row outlives Redis TTL — used invites visible in panel forever
- Member role grants: catalog browse + 3D viewer + share-link generation
- Member blocked: audit log read, agent-runbook access, admin endpoints, `admin/*`
- Share-router auth expands from `admin`-only to `{admin, member}`; new `current_member_or_admin` dependency variant
- Audit events added: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`

## Epic 5.2 — 2FA TOTP + recovery codes
- TOTP enrollment via `pyotp` + QR display (manual secret fallback)
- At enrollment: 8 single-use recovery codes generated, shown once, hashed at rest
- Optional by default; enforced per-role via `enforce_2fa_for_roles: list[Role]` config flag in `apps/api/app/core/config.py` (default `[]`); admin can force-enroll individual user via admin panel
- `agent` role MUST never appear in `enforce_2fa_for_roles` — it is a service account
- Login flow extends with second-factor step when user has TOTP enabled
- Recovery code consumption one-way + audit-logged
- New `users` table columns `totp_secret`, `totp_enabled_at`; new recovery-codes table

## Epic 5.3 — Admin panel: users + invites
- Two tabs in existing admin UI; React routes under `apps/web/src/modules/admin/`
- Users tab: list with email, role, created_at, last_active_at, 2FA-enabled, is_active; actions: change role, force-2FA-enrollment, reset password via one-time link, deactivate via `is_active=False`, force logout-all
- Invites tab: list with status active/used/expired/revoked, generated_by, used_by, used_at, used_from_ip; actions: generate new invite + revoke active invite
- All admin actions audit-logged via `record_event()` helper
- `is_active: bool` soft-delete column + `last_active_at: datetime` column (throttled write ≤1/5min per user, middleware-driven)
- Admin-issued password reset link is functionally identical to invite token (single-use, short TTL, Redis-fronted); operator delivers out-of-band (SMS/Messenger/personal mail) until self-hosted mail server arrives
- Full account lockout recovery (lost 2FA AND recovery codes): operator force-disables 2FA via panel (audit `auth.totp.disabled` with `actor != target`), then issues reset link; no mail-server dependency; documented in Epic 5.3 acceptance criteria

## Epic 5.4 — Security hardening pre-cutover (HARD GATE blocking 5.5)
- Tooling: `bandit` (Python SAST), `semgrep` (multi-lang OWASP top-10 rulesets), `pip-audit` + `npm audit`/`osv-scanner` (deps), OWASP ZAP active scan against `.190`, `codex review` on new auth/invite/2fa modules
- Scenario coverage required (all six): invite-token brute force (must hit rate-limit before exhausting entropy of 32-byte token by margin ≥10⁶); refresh-token replay against family rotation; CSRF/JWT tampering; IDOR on every admin endpoint; rate-limit verification on `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=` (operator explicit raise); share-token abuse from compromised/malicious member account (rate-limit + volume cap on `/api/share/*` POST per-member)
- Member-amplified share-link distribution is asymmetric risk introduced by 5.1's permission expansion; mitigation: per-member rate-limit + daily volume cap on share-token creation; suggested floor ≤20 share-tokens/member/day with soft-fail at 50% threshold + operator alert; compromised-member detection via AuditLog correlation (`auth.refresh.reuse_detected` for actor + share-creation burst)
- Gate condition: zero open Critical/High findings at moment of 5.5 deployment; every Medium fixed OR mitigated with compensating control OR accepted-with-rationale
- Hard cap: max 3 "accepted-with-rationale" Mediums across entire Epic 5.4 audit; 4th forces gate auto-fail + triggers fix sprint; Critical and High have no "accepted" path — fixed-or-bust
- Signing authority: operator is both auditor + gatekeeper (single-operator project); mitigation = every Medium disposition requires `codex review --commit <SHA>` second-opinion artifact against patch; "accepted-with-rationale" specifically requires explicit countersignature in audit report
- Failure to pass 5.4 = no "yolo cutover" override; unfixable Critical parks the cutover and triages to fix-sprint before 5.5 runs

## Epic 5.5 — Edge cutover (atomic)
- Atomic switch: drop nginx basic-auth AND IP allowlist in same change
- Touch is in sibling repo `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (live config NOT in `3d-portal`)
- Portal authenticates itself via FastAPI middleware/route guards; nginx becomes thin reverse proxy + TLS terminator + share-bypass rewrite
- `/share/*` and `/agent-runbook` paths continue to skip portal auth (already designed)
- Rollback path: revert single config commit + `nginx -s reload`; estimated cutover window 5 min including rollback test
- Cross-repo coordination: rollback story spans two repos; bypasses `3d-portal`'s `deploy.sh` skip-gate logic (gitignored `infra/.last-deploy-sha`)
- Cutover MUST be followed immediately by 4-scenario post-reload smoke check against `.190`, part of 5.5 acceptance criteria (not PRD-time addendum): (1) anonymous GET `/share/<token>` returns 200; (2) agent service account POST `/api/admin/models` (cookie+password) returns 201; (3) member login returns 200 + `portal_access` cookie set; (4) admin login returns 200 + admin scope verified; rollback if any of four regress

## In-scope (operator-confirmed)
- New `invite_tokens` DB table + Redis-fronted storage + admin endpoints + UI for generate/list/revoke
- New `/register?token=<token>` public route + form (email, password zxcvbn ≥3 ≥12-char, token validation)
- New `member` role permission scope: catalog browse, viewer, share-link generate; member-blocked: `admin/*`, agent-runbook, audit log read
- Extension of `current_admin` dependency family with `current_member_or_admin` variant; share-router auth `{admin, member}`
- 2FA columns on `users` (`totp_secret`, `totp_enabled_at`); recovery-codes table; 2FA enrollment route + UI (QR + manual secret); `enforce_2fa_for_roles` config flag
- Admin panel Users tab + Invites tab; React routes under `apps/web/src/modules/admin/`
- `is_active: bool` soft-delete + `last_active_at: datetime` columns on `users` (throttled write ≤1/5min)
- Rate-limit middleware on `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=` with tunable thresholds in config; Redis-backed sliding-window (architecture decision at PRD time); likely `apps/api/app/core/auth/ratelimit.py`
- Security audit tooling outputs as artifacts under `_bmad-output/implementation-artifacts/`
- Nginx edge cutover edit in sibling repo: drop `auth_basic` + IP allowlist; preserve share bypass + agent-runbook bypass; atomic single commit + reload
- New audit-log actions added to `KNOWN_ENTITY_TYPES` (16 total): `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`, `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`, `auth.password.reset.initiated`, `auth.password.reset.completed`, `user.deactivated`, `user.reactivated`, `user.role_changed`, `user.force_logout`

## Out-of-scope (explicit non-goals, operator-confirmed Q5, non-negotiable)
- Social login (Google/GitHub/etc.) — native accounts only
- OIDC/SSO federation (Authentik in homelab) — `member-print-requests` initiative may revisit
- Per-model ACL (member X sees catalog subset) — all-or-nothing access for `member`
- Team/group accounts
- User-to-user messaging
- Public read-only browse mode — portal stays gated by login; `/share/*` is only escape hatch
- Self-service password reset via email — blocked on self-hosted mail server (separate future initiative)
- Email deliverability verification — RFC format validation only
- Webhook/event push to external systems on auth events
- Multi-tenant — one household, one SoT, one admin, multiple members

## Success Criteria (leading-indicator-first, admin-panel-observable)
- SC#1 First-wave activation: within 30 days of 5.5 close, ≥5 invites generated, ≥3 consumed, ≥2 distinct members with non-null `last_active_at` in last 7 days (floor, not stretch)
- SC#2 Admin panel handles routine ops without DB poking: all four core admin actions (generate invite, revoke invite, change user role, reset user password) exercised through panel UI ≥1× in first 30 days; zero panel-triggered operations require SQL inspection
- SC#3 Zero account-takeover incidents in first 90 days: no `auth.refresh.reuse_detected` for non-attacking causes (UA churn excluded via 30s grace); no `auth.login.fail` patterns matching credential-stuffing (≥10 failures from one IP across ≥3 emails within 5 min)
- SC#4 Epic 5.4 audit produces clean cutover artifact at `_bmad-output/implementation-artifacts/security-audit-2026-MM-DD.md` showing zero open Critical/High at moment of 5.5 deployment; every Medium has documented disposition (fixed/mitigated/accepted-with-rationale)
- SC#5 2FA enrollment + recovery-code path drill-verified against `.190`: artifact at `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-MM-DD.md`, executed against deployed `.190` (NOT CI fixtures); drill steps: enroll test user → log out → log in with TOTP → consume recovery code in place of TOTP → regenerate recovery codes → disable TOTP → verify normal login; artifact captures timestamps, request IDs, AuditLog row deltas; first-wave member adoption intentionally NOT an SC (operator-framing "path works, not adoption")
- SC#6 Rate-limit holds the line on `/api/auth/login`: post-cutover rejects ≥5 rapid failures from one IP within 60 seconds with HTTP 429; verified by `siege`/`hey` benchmark in audit, reproducible on demand

## Working Assumptions (load-bearing for PRD/arch)
- Member's share-generation permission is a new permission expansion: today share creation admin-only (`apps/api/app/modules/share/admin_router.py`); 5.1 extends to `{admin, member}`; deliberate scope-in per Q1/Q2
- Existing admin (Michał) + agent (AI) rows preserved with null-op migration: schema additions only (nullable columns + new tables), no data rewrite; existing JWT cookie auth remains primary login path; 2FA opt-in additive
- Live nginx config is in sibling repo `~/repos/configs/nginx/3d.ezop.ddns.net.conf`; Epic 5.5 touches that repo, not `3d-portal`; sprint planning must reflect cross-repo coordination (rollback story spans two repos)
- Rate-limit middleware is hard requirement for cutover (operator explicit raise Q4); audit 5.4 must verify rate-limit on at least `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`; implementation likely Redis-backed sliding-window in `apps/api/app/core/auth/ratelimit.py`
- Soft-delete is the user-deletion model: `is_active=False` + audit trail kept; hard-delete not exposed in panel; DB-only for GDPR right-to-be-forgotten with care for FK integrity (`audit_log.actor_user_id`, `refresh_tokens.user_id`)
- `last_active_at` write throttled ≤1/5min per user to avoid SQLite write churn; updates in middleware on authenticated requests; throttle operationally invisible
- 2FA enforcement is a config flag not UI toggle: `enforce_2fa_for_roles: list[Role]` in `apps/api/app/core/config.py`; admin can force-enroll individual user via panel (per-user override); `agent` role must never appear in `enforce_2fa_for_roles`
- Invite-token storage dual-backed: Redis source of truth for active/TTL/revoke (mirrors share-token, fast); row in `invite_tokens` DB table at generation for audit history, updated at use; DB row outlives Redis TTL
- Failure to pass 5.4 = 5.5 does not happen; no "yolo cutover" override; unfixable Critical parks cutover + triages to fix-sprint
- Epic 5.4 gate authority + Medium-disposition cap: operator is both auditor + gatekeeper (single-operator self-attestation risk); mitigation — every Medium disposition requires `codex review --commit <SHA>` second-opinion artifact OR explicit countersignature in audit report for "accepted-with-rationale"; hard cap: max 3 "accepted-with-rationale" Mediums entire audit; 4th forces gate auto-fail + fix sprint; Critical/High have no "accepted" path
- Member share-link generation is deliberate amplification surface; once 5.1 expands `/api/share/*` POST to `{admin, member}`, single compromised member can mint unlimited auth-bypassing public URLs; mitigation in 5.4 audit scope: per-member rate-limit + daily volume cap on share-token creation (architecture decision at PRD time; suggested floor ≤20/member/day, soft-fail at 50% threshold with operator alert); compromised-member detection in AuditLog query (`auth.refresh.reuse_detected` for actor + share-creation burst correlation)
- Admin-issued password reset link delivered out-of-band by operator (same channel as original invite: SMS/Messenger/personal mail); reset link functionally identical to invite token (single-use, short TTL, Redis-fronted); becomes self-service via mail when self-hosted mail server lands (separate future initiative)
- Full account lockout recovery (lost 2FA AND recovery codes): operator force-disables 2FA via panel (audit `auth.totp.disabled` with `actor != target` flag), then issues one-time reset link; no mail-server dependency; documented in 5.3 acceptance criteria
- Cross-repo cutover smoke matrix: 5.5 nginx edit lives in sibling repo, bypasses `3d-portal` `deploy.sh` skip-gate (gitignored `infra/.last-deploy-sha`); cutover MUST be followed immediately by 4-scenario post-reload smoke check against `.190`; smoke checklist is part of 5.5 acceptance criteria not PRD-time addendum
- Invite-token hygiene is operator-manual in v1: no automated stale-invite cleanup; orphan invites (generated never sent) live in Redis until natural TTL expiry; operator-side hygiene via Invites tab in 5.3 (filter by status/age/not-yet-used); no bulk-invite-revoke action in v1 panel — DB-direct only if needed
- Bulk user deactivation is DB-direct in v1: panel ships single-user `is_active=False` toggle in 5.3; if friend-group falls out of trust and 10+ users need disabling at once, that is DB script not panel action; deferred to admin-panel-v2 if pattern recurs
- Epic numbering convention is PRD-time decision: continue flat scheme (Init 5 epics 6-10) OR adopt dotted-by-initiative (5.1-5.5); brief uses dotted convention as working labels

## What Makes This Different
- Mostly additive on thick existing baseline: new `invite_tokens` table, 2FA columns + recovery_codes table, two new admin pages, ~16 new audit-log actions, one nginx config change
- Cutover is the smallest change in initiative: drop two nginx directives; portal auth was already there; bulk of work is the security audit
- Member's permission expansion is one bit: `member` can generate `/share/<token>` links — only permission gained above today's anonymous-LAN-browser; no per-model ACL, no team accounts, no messaging, no comments
- Agent role is sacrosanct: Initiative 2 runbook + cookie+password agent flow unchanged; agent does NOT get 2FA forced
- Security audit is an epic not a story: per `feedback_default_to_bmad_workflow.md` (multi-PR security batches from review docs are epics in disguise); 5.4 has hard-gate exit criterion
- Audit cost paid before network perimeter drops: operator banking-IT instinct prioritizes account-takeover + infra-leak as top-feared failures

## Personas
- Primary: Ezop (operator) — Q3 framing "first targetem portalu jestem ja ostatecznie"; win is operator-side friction reduction ("show this model to my brother" from screenshot+Messenger → "sent invite once; he checks catalog whenever, returns with concrete links"); success is leading-indicator (people log in, send requests) not output-metric (DAU/MAU); operator honest friends/family may simply not engage — portal still has to be daily-driver curation engine for Michał regardless
- Secondary: Friends-and-family ~10-20 people realistically in first 90 days; curated trust circle; value per Q2: central place to see models Michał can print, can return, can send concrete links to specific curated models; later print-requests channel replaces Messenger threads with structured asks
- Preserved exactly: agent (AI service account) — continues ingesting via `/api/admin/models`, continues cookie+password flow, no 2FA forced, no admin panel from permission standpoint, auth flow unchanged
- Explicitly NOT served v1: wider hobby-print community (Reddit/Discord), public read-only browsers, federated identities (Authentik OIDC), team/group accounts, per-model ACL recipients, user-to-user messaging — all on long-tail roadmap, deliberately not pre-built for
- Aha moment specifics: curated browse + return-with-link; future in-portal print-request channel (replaces Messenger threads with structured request shape)
- Top failure fears (operator banking-IT instinct): account takeover + brute force + infra leak; rate-limit raise was explicit at Q4

## Vision (milestones)
- Initiative 5 close (4-6 weeks total, 5 epics back-to-back): portal invite-gated; first wave ~5-10 onboarded; admin panel operator's daily-driver for user ops; nginx is thin TLS+proxy+share-bypass
- +90 days post-cutover: first-wave members either engage (login signal + ad-hoc print requests via Messenger placeholder) or they don't (also acceptable; operator-side win still holds); 2FA path proven through ≥1 enrollment OR ≥1 force-enroll OR ≥1 recovery-code drill
- +6 months / Initiative 6 candidate: `member-print-requests` unblocked — every print request is `request.user_id` not "Michał has to remember whose Messenger thread"; per-user prints log feasible; per-user favorites feasible
- +12 months (vision not commitment): self-hosted mail server → self-service password reset → email deliverability checks → possibly widen first-wave from friends-and-family to moderated hobby-print community; each step its own initiative; Initiative 5 deliberately stops at friends-and-family threshold
- Growth is opt-in by operator, not by platform

## Stakeholders + sources consulted
- Ezop (operator) locked all 5 top-level decisions (edge gate drop, role taxonomy, invite mechanics, 2FA approach, atomic cutover) + supplied persona, aha moment, success-stance, failure fears in 2026-05-18 elicitation pass
- BMAD artifacts: `_bmad-output/planning-artifacts/prd.md` (Init 0/1/2/3 baselines), `_bmad-output/planning-artifacts/architecture.md` (auth + share-token + audit-log decisions), `_bmad-output/project-context.md` (auth conventions), `AGENTS.md` (deploy contract)
- apps/api recon: `app/core/db/models/{_user.py,_enums.py,_audit.py,_auth.py}`; `app/core/auth/{cookies, csrf, jwt, refresh, dependencies}`; `app/modules/auth/router.py`; `app/modules/share/{service.py, models.py}`; latest migration `0011`
- apps/web recon: `src/routes/login.tsx`, `src/shell/{AuthContext.tsx, AuthGate.tsx}`, `src/lib/{api.ts, refresh.ts}`
- Edge infra (sibling repo): `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (live); `infra/nginx-180/.archived/3d-portal.conf.pre-IP-allowlist` (pre-allowlist snapshot in this repo)
- Memory: `feedback_default_to_bmad_workflow.md`, `feedback_brief_autonomous_skip_elicitation.md`, `feedback_invoke_codex_directly.md`, `user_role.md`, `feedback_collaboration_division.md`

## Next step
- Route to `bmad-create-prd` for PRD extension into `_bmad-output/planning-artifacts/prd.md` under new `## Initiative 5` H2
- PRD focus: FRs/NFRs per epic 5.1-5.5; explicit acceptance criteria per epic; security-audit scope detail under 5.4 (tooling invocations + scenario list + gate condition); cross-repo cutover checklist under 5.5
- Architecture extension follows via `bmad-create-architecture`; decisions to nail: invite-token schema (Redis vs DB write strategy), 2FA column shape on `users`, recovery codes table schema, rate-limit middleware strategy (Redis sliding window vs token bucket vs leaky bucket), nginx config diff with rollback artifact
