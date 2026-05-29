# Initiative 5 — Public Registration & User Account Management

<!-- DERIVED FILE — generated 2026-05-19T00:38:18Z for bmad-story-automator parse-epic compatibility.
     Source-of-truth: ../epics.md § Initiative 5. Do not edit by hand. -->

## Initiative 5 — Public Registration & User Account Management

**Status:** 🚧 planning (started 2026-05-18). Maintainer: Ezop. Source brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (v2, 213 lines, adversarial review applied: P0×2 + P1×3 + P2×1 fixed) + distillate sibling (~5688 tokens, LLM-optimized). Source CC proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Source PRD section: `prd.md` § "Initiative 5" (lines 1065-1258 — 24 FRs across 8 prefix groups + 12 NFRs across 6 categories). Source architecture section: `architecture.md` § "Initiative 5" (lines 1399-1767 — Decisions A–K in-scope; L–N deferred). Sequenced into five epics: **E6** (Member role + invite-based registration) → **E7** (TOTP 2FA + recovery codes) → **E8** (Admin panel: users + invites) → **E9** (Security audit — **HARD GATE** blocking E10) → **E10** (Edge cutover — atomic).

**Brief working-label mapping.** The source brief uses dotted notation `5.1`–`5.5` as working labels. These map 1:1 onto project-global epic IDs per CC §3.4 vanilla-alignment correction (vanilla `epics-template.md` `{{N}}` unique-in-file constraint preserved via project-global numbering, continuing E1–E3 / E4 / E5 from Init 1/2/3): brief `5.1` → **E6**, `5.2` → **E7**, `5.3` → **E8**, `5.4` → **E9**, `5.5` → **E10**. Story IDs follow `<global-epic-id>.<local-story-num>` (e.g. `Story 6.1`, `7.3`, `10.2`). The dotted brief labels are PRD-time historical artifacts; from this section forward only the global IDs are used.

**Init 0 + Init 2 are unchanged.** Initiative 5 is purely additive on the brownfield base. The Init 0 cookie+JWT auth stack stays exactly as it ships (`portal_access` 10min + `portal_refresh` 30d family rotation, CSRF via `X-Portal-Client: web`). The Init 0 share-token Redis pattern stays as the template for invite tokens (Decision A mirrors `apps/api/app/modules/share/service.py` deliberately). The Init 0 audit-log surface gains 16 new action names (enumerated in FR5-AUDIT-1) but no contract changes — same `record_event()` helper, same `KNOWN_ENTITY_TYPES` registry, same `/api/admin/audit` query path. The `agent` service account (Init 2) is preserved exactly: cookie+password flow unchanged, no 2FA forced ever (FR5-2FA-3 fail-fast startup check on `Role.agent in enforce_2fa_for_roles`), `/agent-runbook` nginx bypass preserved across the Epic 10 cutover (NFR5-INT-1 + Decision K). The `admin` role is preserved exactly — `current_admin` stays admin-only.

**Header levels** per CC §3.4 (deeper nesting than Init 1/2/3 to encapsulate five epics under a single initiative): `## Initiative 5` (H2) → `### Overview / Requirements Inventory / Epic List / Cross-references` (H3) → `#### Epic N` (H4) → `##### Story N.M` (H5).

### Overview

3d-portal today admits exactly two principals: `admin` (Michał) and `agent` (the AI service account). Catalog browse is gated at the nginx edge via IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`, covering homelab LAN + VPN); there is no per-person login path for friends-and-family. The `member` role is already enumerated in `apps/api/app/core/db/models/_enums.py` (Init 0 baseline) but is unreachable — no registration flow, no admin UI for invite issuance, no 2FA infrastructure, and the network perimeter is still load-bearing for trust.

Initiative 5 closes that gap in five sequenced epics. **E6** wires the core flow: admin generates a single-use invite link with operator-chosen TTL and pre-bound role, recipient lands on `/register?token=<token>`, supplies email + password (zxcvbn ≥3 ≥12-char gate), and the resulting `member` account gains catalog browse + 3D viewer + share-link generation via the share-router auth expansion. E6 also ships the cross-cutting rate-limit middleware (Redis sliding-window over sorted set) for `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register?token=`, and the per-member share-token cap. **E7** adds optional second-factor TOTP with mandatory eight single-use recovery codes; enforcement is per-role via `enforce_2fa_for_roles: list[Role]` with the `agent` role explicitly excluded by fail-fast startup validation. E7 closes with an end-to-end recovery-code drill against `.190` captured as `2fa-recovery-drill-YYYY-MM-DD.md`. **E8** ships two new admin tabs (`/admin/users`, `/admin/invites`) on the existing admin module, soft-delete + `last_active_at` infrastructure with Redis `SET NX EX 300` write throttle, per-user actions (change role, deactivate / reactivate, force logout-all-sessions, force-2FA-enrollment, issue password reset), and the invite list/revoke surface. **E9** is the **HARD GATE** before E10 — formal pre-cutover audit with `bandit` + `semgrep` + `pip-audit` + `npm audit`/`osv-scanner` + OWASP ZAP active scan + `codex review` countersignature for each Medium disposition. Gate condition (NFR5-SEC-1): zero open Critical/High findings; at most three "accepted-with-rationale" Medium findings (the fourth forces auto-fail and triggers a fix sprint). **E10** is the atomic single-commit nginx edit in the sibling configs repo dropping both `auth_basic` and the IP allowlist, plus a four-scenario post-reload smoke matrix and a verified rollback drill before close-out.

The work is bounded. The cutover itself is the smallest change in the initiative — drop two nginx directives. The bulk of the effort is the audit that lets the portal trust the cutover, not the cutover itself. Each Story below cites one or more concrete FR5-* / NFR5-* requirement IDs from `prd.md` § Initiative 5 and one or more architecture Decision letters (A–K) from `architecture.md` § Initiative 5 as the binding architectural anchor. Granular per-step acceptance criteria (Given/When/Then prose) are deferred to `bmad-create-story` skill at story-execution time (Sesja G+ per CC §4.3); this section's acceptance bullets are the high-level capability checks per story, sufficient for sprint-planning intake.

**Out-of-scope reminders carried from brief Q5 + PRD § "Out" + architecture Decisions L–N (deferred):** no social login, no OIDC/SSO federation, no per-model ACL, no team/group accounts, no user-to-user messaging, no public read-only browse mode, no self-service mail-based password reset (blocked on self-hosted mail server initiative), no email deliverability verification (RFC format only), no webhook push to external systems, no multi-tenant. Admin-issued password reset link (FR5-ADMIN-3) is the only reset path in v1; delivery is out-of-band by the operator. FR5-ADMIN-4 (bulk user operations in panel UI) is a deliberate exclusion documented in architecture.md Decision-adjacent narrative — single-user actions only; bulk needs go through DB-direct scripts.

### Requirements Inventory

#### FR↔Epic coverage matrix

Each functional requirement from `prd.md` § "Initiative 5" Functional Requirements maps to one or more epics here. The "Architectural anchor" column cites the Decision letter(s) from `architecture.md` § "Initiative 5" that the realizing Story bases its implementation on.

| Requirement | Brief description | Realizing Epic(s) | Architectural anchor |
|---|---|---|---|
| FR5-INVITE-1 | Admin generates single-use 256-bit invite tokens with TTL preset + custom; dual-backed Redis + DB | E6 (6.1, 6.2, 6.3) | Decisions A, B |
| FR5-INVITE-2 | Admin lists active + historical invites with per-row metadata + status filter | E6 (6.3), E8 (8.6) | Decisions A, B |
| FR5-INVITE-3 | Admin revokes active invite; revoked-but-listed token MUST be unconsumable (HTTP 410) | E6 (6.2, 6.3), E8 (8.6) | Decisions A, B |
| FR5-INVITE-4 | Single-use semantics; replay attempts fail closed with HTTP 410 + `auth.register.fail` reason `token_consumed` | E6 (6.2) | Decisions A, B |
| FR5-REGISTER-1 | Public `/register?token=` accepts valid unused token; invalid → HTTP 404 + audit `auth.register.fail` reason `token_invalid` | E6 (6.4) | Decisions A, B |
| FR5-REGISTER-2 | Form captures email (RFC syntax) + password (zxcvbn ≥3, length ≥12); failure HTTP 422 with failing-rule body | E6 (6.4) | Decisions A, B |
| FR5-REGISTER-3 | Successful registration creates user with invite-bound role; issues `portal_access` + `portal_refresh` cookies; audit `auth.register.success` | E6 (6.4) | Decisions A, B, C |
| FR5-MEMBER-1 | `member` role grants browse + viewer + `POST /api/share/`; share-router expands to `current_member_or_admin` | E6 (6.5) | Decision C |
| FR5-MEMBER-2 | `member` denied all `/api/admin/*` + `/api/audit/*`; `current_admin` stays admin-only | E6 (6.5) | Decision C |
| FR5-MEMBER-3 | Per-member share-token rate-limit + daily cap (≤20/day hard, 50% soft-alert) | E6 (6.7), E9 (9.2 audit verify) | Decisions G, H |
| FR5-2FA-1 | TOTP enrollment with QR + manual secret; 8 single-use recovery codes generated once + stored hashed | E7 (7.1, 7.2) | Decisions D, E |
| FR5-2FA-2 | Login flow extends with second-factor step for users with `totp_enabled_at IS NOT NULL`; accepts TOTP or recovery code | E7 (7.3) | Decisions D, E |
| FR5-2FA-3 | `enforce_2fa_for_roles: list[Role]` config; `Role.agent` triggers fail-fast startup `RuntimeError` | E7 (7.4) | Decision F |
| FR5-2FA-4 | Regenerate recovery codes (invalidates prior batch) + disable TOTP (clears `totp_enabled_at` + invalidates unused codes); both require re-auth | E7 (7.5) | Decision E |
| FR5-ADMIN-1 | Two admin tabs `/admin/users` + `/admin/invites` with paginated lists and documented column sets | E8 (8.2, 8.6) | Decisions I (users tab columns), A (invites tab columns) |
| FR5-ADMIN-2 | Per-user actions: change role, force 2FA, deactivate, reactivate, force logout-all-sessions; each emits matching audit row | E8 (8.3, 8.4) | Decisions I (soft-delete + force-logout), F (force-2FA per-user override) |
| FR5-ADMIN-3 | Admin-issued password-reset link mirrors invite-token shape; Redis `invite:reset:{token}`; out-of-band delivery | E8 (8.5) | Decisions A, B (token shape reuse) |
| FR5-ADMIN-4 | Bulk user ops deliberately NOT in v1 panel UI (single-user only); DB-direct scripts for bulk | Negative AC enforced in E8 (8.2 Users tab — Playwright snapshot test asserts absence of bulk-select / bulk-action selectors); deliberate exclusion also documented in architecture.md narrative | none (architectural decision; negative AC anchored in 8.2) |
| FR5-AUDIT-1 | 16 new `KNOWN_ENTITY_TYPES` actions emitted via existing `record_event()` — no parallel logging surface | E6 (6.1, 6.3, 6.4) + E7 (7.2, 7.3, 7.5) + E8 (8.3, 8.4, 8.5) | cross-cuts; uses Init 0 audit-log baseline contract |
| FR5-RATELIMIT-1 | Rate-limit middleware on `/api/auth/login` + `/api/auth/refresh` + `/api/auth/register?token=`; Redis sliding-window | E6 (6.6), E9 (9.2 audit verify) | Decision G |
| FR5-RATELIMIT-2 | Per-member share-token creation cap; soft-alert log at 50%, hard-fail HTTP 429 at 100% | E6 (6.7), E9 (9.2 audit verify) | Decisions G, H |
| FR5-CUTOVER-1 | Atomic single-commit nginx edit dropping `auth_basic` + IP allowlist; preserves share + agent-runbook bypasses | E10 (10.2, 10.3) | Decision K |
| FR5-CUTOVER-2 | Four-scenario post-reload smoke matrix executed against `.190`; per-scenario timestamps + request IDs + audit deltas | E10 (10.1, 10.3) | Decision J |
| FR5-CUTOVER-3 | Verified rollback drill (≤30s end-to-end) before cutover considered closed; any smoke regression triggers immediate rollback | E10 (10.3) | Decision K |

**Coverage:** 24/24 FRs mapped. FR5-ADMIN-4 (bulk-ops deliberate exclusion) and FR5-AUDIT-1 (cross-cutting audit registration) are not single-story-anchored by design — see column notes.

#### NFR↔Epic coverage matrix

| Requirement | Brief description | Realizing Epic(s) | Architectural anchor |
|---|---|---|---|
| NFR5-SEC-1 | E9 audit HARD GATE: zero open Critical/High; ≤3 accepted-rationale Mediums; 4th forces auto-fail + fix sprint | E9 (9.1, 9.2, 9.4) | Decisions G, H (verification surface); audit report shape per FR5-CUTOVER-2 artifact format precedent |
| NFR5-SEC-2 | Per-Medium disposition requires `codex review --commit <SHA>` countersignature in audit report | E9 (9.3) | none (process control) |
| NFR5-SEC-3 | Six-scenario audit coverage matrix: invite brute, refresh replay, CSRF/JWT, IDOR, rate-limit verify, member share amplification | E9 (9.2) | Decisions G, H |
| NFR5-PERF-1 | `last_active_at` write throttled ≤1/5min/user via Redis `SET NX EX 300` | E8 (8.1) | Decision I |
| NFR5-PERF-2 | Edge cutover window ≤5 minutes including smoke + rollback drill; rollback path ≤30 seconds | E10 (10.3) | Decision K |
| NFR5-AUDIT-1 | Every Init 5 audit action emitted via `record_event()` — no parallel logging surface | cross-cuts E6/E7/E8 (every audit-row-emitting story) | Init 0 audit baseline contract |
| NFR5-CROSS-REPO-1 | Epic 10 nginx edit bypasses `3d-portal` `deploy.sh` skip-gate (sibling repo has no `.last-deploy-sha`); closing `docs/operations.md` cutover-date commit records cutover in `3d-portal` deploy history | E10 (10.4) | Decision K |
| NFR5-CROSS-REPO-2 | Rollback story spans both repos (`git revert` in sibling + `nginx -s reload` on `.180` + smoke re-run + revert-the-revert + reload + smoke re-run); sprint plan reflects cross-repo tasks | E10 (10.3) | Decision K |
| NFR5-INT-1 | `agent` role preserved exactly: cookie+password flow unchanged; `Role.agent` MUST NEVER appear in `enforce_2fa_for_roles`; `/agent-runbook` bypass preserved across cutover | E7 (7.4, startup check) + E10 (10.3, smoke scenario 2 + nginx bypass preservation) | Decisions F, K |
| NFR5-INT-2 | `/share/*` location bypass preserved across cutover; share-token TTL + revoke semantics unchanged from Init 0 | E10 (10.3, smoke scenario 1 + nginx bypass preservation) | Decision K |
| NFR5-OBS-1 | All new auth events produce GlitchTip-visible structured log entries via `JsonFormatter` with namespaced loggers (`app.auth.invite`, `app.auth.totp`, `app.auth.register`, `app.admin.users`); counter-shaped events for `*.fail` queryable in dashboard | cross-cuts E6/E7/E8/E9/E10 (every audit-row-emitting story; rate-limit soft-alert log) | Init 1 GlitchTip baseline + Decisions G, H |
| NFR5-OBS-2 | Two named drill artifacts under `_bmad-output/implementation-artifacts/`: `2fa-recovery-drill-YYYY-MM-DD.md` (E7 close) + `cutover-smoke-YYYY-MM-DD.md` (E10 close) | E7 (7.6), E10 (10.3) | Decisions E, J, K |

**Coverage:** 12/12 NFRs mapped. NFR5-AUDIT-1 and NFR5-OBS-1 are cross-cutting and have no single-story anchor by design — the property is preserved by every audit-row-emitting story routing through `record_event()` and the existing namespaced-logger pattern.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E6 | Member role + invite-based registration | 7 (6.1–6.7) | Medium | Medium | FR5-INVITE-1..4, FR5-REGISTER-1..3, FR5-MEMBER-1..3, FR5-RATELIMIT-1..2 (foundation), FR5-AUDIT-1 (E6 subset: 4 actions) | none (entry epic) |
| E7 | TOTP 2FA + recovery codes | 6 (7.1–7.6) | Medium | Medium | FR5-2FA-1..4, NFR5-INT-1 (agent fail-fast), NFR5-OBS-2 (2fa-recovery-drill artifact), FR5-AUDIT-1 (E7 subset: 5 actions) | E6 complete |
| E8 | Admin panel: users + invites | 6 (8.1–8.6) | Medium | Low | FR5-ADMIN-1..3, NFR5-PERF-1, FR5-AUDIT-1 (E8 subset: 7 actions including admin reuse of E6 invite revoke) | E6 + E7 complete |
| E9 | Security audit — **HARD GATE** blocking E10 | 4 (9.1–9.4) | High | **High** | NFR5-SEC-1..3, audit verification of FR5-RATELIMIT-1..2 + FR5-MEMBER-3 | E6 + E7 + E8 complete |
| E10 | Edge cutover (atomic) | 4 (10.1–10.4) | Low | **High** | FR5-CUTOVER-1..3, NFR5-PERF-2, NFR5-CROSS-REPO-1..2, NFR5-INT-1..2, NFR5-OBS-2 (cutover-smoke artifact) | **E9 audit PASS (NFR5-SEC-1 gate condition: zero open Critical/High, ≤3 accepted-rationale Mediums)** |

**Total:** 27 stories planned (within CC §4.4 estimate floor 25, ceiling 35). Effort total estimated at 4–6 weeks back-to-back per brief Vision section.

**Sequencing:** E6 → E7 → E8 → **E9 (HARD GATE)** → E10. E10 is contractually blocked on E9 audit PASS — no "yolo cutover" override path is documented anywhere. If E9 audit produces a 4th Medium or any open Critical/High, E10 is parked and a fix sprint is triaged before the cutover unlocks. The HARD GATE is structural, not procedural — there is no `--force` flag in any cutover script.

## Epic 6: Member role + invite-based registration

**Goal.** Wire the end-to-end core flow from "admin generates invite link" → "operator delivers link out-of-band" → "recipient lands on `/register?token=...`" → "server validates token + email + password strength + creates user with invite-bound role + issues cookie pair" → "member can browse catalog and mint share tokens". Also ship the cross-cutting rate-limit middleware (Redis sliding-window) that the E9 audit will verify and the per-member share-token cap that closes the share-link-amplification surface flagged in brief Q3.

**Acceptance gate.** End-to-end happy path drilled on `.190`: invite generated by admin via Story 6.3 endpoint → consumed via Story 6.4 register flow → resulting member-cookie-authenticated `POST /api/share/` returns 201 (Story 6.5 permission expansion) → rate-limit middleware (Story 6.6) rejects 6th failed login from one IP within 60s with HTTP 429 → per-member share cap (Story 6.7) returns HTTP 429 on the 21st share creation in a UTC day. All E6 audit actions (`auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success`, `auth.register.fail`) visible via `/api/admin/audit` with correct actor + target.

**FRs realized:** FR5-INVITE-1, FR5-INVITE-2 (admin endpoints subset; Invites tab UI is E8.6), FR5-INVITE-3, FR5-INVITE-4, FR5-REGISTER-1..3, FR5-MEMBER-1..3, FR5-RATELIMIT-1..2, FR5-AUDIT-1 (E6 subset: 5 actions).

**Architectural anchors:** Decisions A (invite-token dual-backed storage), B (invite-token shape + Alembic 0012), C (member permission scope diff + `current_member_or_admin` dependency), G (rate-limit middleware), H (per-member share cap).

**Blocked by:** none. Entry epic for Initiative 5.

### Story 6.1: Alembic migration `0012_invite_tokens` + invite-token primitives

**Realizes:** FR5-INVITE-1, FR5-INVITE-4, FR5-AUDIT-1 (`auth.invite.*` action names registered in `KNOWN_ENTITY_TYPES`).
**Architectural anchor:** Decisions A, B (table schema per Decision B column table + indexes + TTL preset enum).
**Depends on:** none (E6 entry story).

Acceptance check shape:

- `apps/api/alembic/versions/0012_invite_tokens.py` exists with the column set + indexes specified in `architecture.md` § Initiative 5 Decision B; `alembic upgrade head` and `alembic downgrade -1` both succeed on a fresh SQLite test DB.
- `apps/api/app/modules/invite/models.py` exports `InviteTTLPreset(IntEnum)` (1d / 3d / 7d / 30d values) + `InviteToken` SQLModel + a `hash_token(token: str) -> str` SHA-256 helper.
- 4 new audit action names registered in `KNOWN_ENTITY_TYPES`: `auth.invite.generated`, `auth.invite.used`, `auth.invite.revoked`, `auth.register.success` (the 5th E6 audit action `auth.register.fail` is added in 6.4 with the public route).
- Logger filter in `apps/api/app/core/logging.py` redacts query-string `token=` values and POST-body `token` fields from JSON log records (verifiable: a manually-constructed log record containing `token=abc` emits with `token=<redacted>`).

### Story 6.2: `apps/api/app/modules/invite/service.py` dual-backed write/read/revoke/consume

**Realizes:** FR5-INVITE-1 (entropy at write), FR5-INVITE-3 (immediate revoke), FR5-INVITE-4 (single-use consume + replay-fails-closed).
**Architectural anchor:** Decisions A, B.
**Depends on:** 6.1 (table + helpers).

Acceptance check shape:

- `generate_invite(role, ttl_seconds, generated_by_user_id) -> tuple[token_cleartext, InviteToken]` writes the DB row first, then Redis key (`invite:token:{token}` with `EXPIRE` matching `ttl_seconds`); failure mid-sequence does not leave a dangling Redis key without a DB row.
- `validate_active(token) -> InviteToken | None` checks Redis first (O(1)), returns `None` on miss without touching the DB.
- `consume(token, used_by_user_id, used_from_ip) -> InviteToken` is atomic: validate-in-Redis → DB update with `used_by_user_id` + `used_at` + `used_from_ip` → DEL Redis key. Failure between DB update and DEL is the rare edge case — Redis TTL still expires naturally; the DB row reflects authoritative "used" state.
- `revoke(invite_id) -> None` deletes the Redis key (`DEL`) and sets `revoked_at` on the DB row in one transaction.
- Replay path: second `consume()` on the same token returns `None` from `validate_active()` after the first consume completed (Redis key gone); caller raises HTTP 410 with reason `token_consumed`.

### Story 6.3: Admin endpoints: generate / list / revoke

**Realizes:** FR5-INVITE-1, FR5-INVITE-2 (server endpoint with status filter), FR5-INVITE-3, FR5-AUDIT-1 (`auth.invite.generated`, `auth.invite.revoked`).
**Architectural anchor:** Decisions A, B.
**Depends on:** 6.2 (service layer).

Acceptance check shape:

- `POST /api/admin/invites` accepts `{role, ttl_seconds | ttl_preset, custom_ttl_seconds?}` from admin-authenticated request; returns `{invite_id, token, registration_url, role, ttl_seconds, expires_at}` (cleartext token surfaces ONCE in this response only). Audit `auth.invite.generated` emitted with `actor_user_id`, `target_user_id=null`, `request_id`.
- `GET /api/admin/invites?status=active|used|expired|revoked&page=N&page_size=M` returns paginated rows with per-row metadata (`generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`); never includes cleartext token.
- `POST /api/admin/invites/{id}/revoke` calls service `revoke()`; subsequent `GET /register?token=<that-token>` returns HTTP 410 Gone. Audit `auth.invite.revoked` emitted.
- All three endpoints require `current_admin` dependency; member-authenticated requests return 403.
- Endpoints follow Init 0 admin-router conventions (filename layout, error envelope, X-Portal-Client CSRF check).

### Story 6.4: Public `/api/auth/register?token=` + `/register` UI

**Realizes:** FR5-REGISTER-1, FR5-REGISTER-2, FR5-REGISTER-3, FR5-AUDIT-1 (`auth.register.success`, `auth.register.fail` reasons `token_invalid` / `token_consumed` / `weak_password`).
**Architectural anchor:** Decisions A, B (token consumption flow), C (cookie issuance reuses Init 0 auth contract).
**Depends on:** 6.2 (consume flow).

Acceptance check shape:

- `POST /api/auth/register` accepts `{token, email, password}`; runs the validation chain: token Redis lookup (miss → HTTP 404 + `auth.register.fail` reason `token_invalid`); email RFC syntax (no DNS/MX); password zxcvbn score ≥3 AND length ≥12 (fail → HTTP 422 + body identifies failing rule + `auth.register.fail` reason `weak_password`); existing user with that email → HTTP 409 + `auth.register.fail` reason `email_taken`.
- On all-checks-pass: create user with `role` from invite + hashed password (existing bcrypt path) → consume invite (6.2 atomic flow) → issue `portal_access` (10min) + `portal_refresh` (30d) cookies via existing Init 0 `auth/cookies.py` helpers → emit `auth.register.success`.
- `apps/web/src/modules/auth/RegisterPage.tsx` React route at `/register` reads `?token=` query param, posts the form, redirects to `/catalog` on 201, surfaces the 422 failing-rule body inline below the password field on validation failure, surfaces 404 + 410 as full-page error states (invalid / consumed token).
- Public route is rate-limited via Story 6.6 middleware (`register` scope, 3 attempts / 60s per IP).
- Visual-regression baselines for `/register` page added in same commit (matches `feedback_docs_hygiene.md` no-red-state rule from Init 3 Principle 3).

### Story 6.5: Member permission expansion: `current_member_or_admin` dependency + share-router auth diff

**Realizes:** FR5-MEMBER-1, FR5-MEMBER-2.
**Architectural anchor:** Decision C (binding per-route allowlist table).
**Depends on:** 6.4 (member accounts exist).

Acceptance check shape:

- `apps/api/app/core/auth/dependencies.py` exports `current_member_or_admin` (raises 403 for `Role.agent` and any other non-listed role).
- `apps/api/app/modules/share/admin_router.py` route `POST /api/share/` decorator switches from `current_admin` to `current_member_or_admin` (one-line dependency swap); every other share-router route + every `/api/admin/*` route + `/api/audit/*` read endpoint stays on `current_admin`.
- `apps/api/tests/conftest.py` adds `member_user_cookies` fixture analogous to existing `admin_user_cookies`.
- Integration tests cover both directions: member POST `/api/share/` → 201 with fresh share token; member GET `/api/admin/users` → 403; admin POST `/api/share/` → 201 (unchanged); anonymous POST `/api/share/` → 401 (unchanged).

### Story 6.6: Rate-limit middleware `apps/api/app/core/auth/ratelimit.py` for login / refresh / register

**Realizes:** FR5-RATELIMIT-1 (3 scopes), NFR5-SEC-3 (foundation for E9 audit scenario coverage of these 3 scopes).
**Architectural anchor:** Decision G (sliding-window over Redis sorted set + middleware-placement contract + key shapes + tunable thresholds).
**Depends on:** 6.4 (register endpoint to rate-limit).

Acceptance check shape:

- New file `apps/api/app/core/auth/ratelimit.py` exporting `RateLimitMiddleware(app, scope, key_fn, window_seconds, threshold)` per Decision G one-pipelined-call shape (`ZREMRANGEBYSCORE` + `ZADD` + `EXPIRE` + `ZCARD` via `MULTI/EXEC`).
- Three middleware instances mounted in `apps/api/app/main.py` factory **AFTER CORS, AFTER CSRF check, BEFORE auth dependency resolution** (placement matters — see Decision G rationale).
- Default thresholds from `apps/api/app/core/config.py`: `login` 5 failures / 60s per IP; `refresh` 10 attempts / 60s per IP; `register` 3 attempts / 60s per IP. All four `*_window_seconds` + `*_threshold` Pydantic Settings keys tunable.
- Failure mode: Redis unreachable → middleware logs `WARNING app.auth.ratelimit redis_unavailable scope=<scope>` and ALLOWS the request (matches Init 0 share-token fail-soft semantics; GlitchTip captures the warning per NFR5-OBS-1).
- Unit tests use `fakeredis`; integration test against `.190` Redis verifies 6th call from one IP returns HTTP 429 with `Retry-After` header.

### Story 6.7: Per-member share-token cap (extension of 6.6 middleware to `share` scope + soft-alert)

**Realizes:** FR5-MEMBER-3, FR5-RATELIMIT-2.
**Architectural anchor:** Decisions G (middleware reuse with `share` scope), H (cap key + soft/hard thresholds + admin exemption + scope binding to `POST /api/share/` only).
**Depends on:** 6.5 (member role expansion to `POST /api/share/`), 6.6 (middleware base).

Acceptance check shape:

- Fourth middleware instance mounted with scope `share`, key `ratelimit:share:user:{user_id}:day:{YYYY-MM-DD}` (UTC), window `86400s`, threshold `20` creations.
- Soft-alert at 10 creations (50% threshold) emits structured log `app.share.ratelimit.soft_alert {user_id, role, count, threshold, window_end}` visible in GlitchTip per NFR5-OBS-1.
- Hard-fail at 21st creation returns HTTP 429 with `Retry-After: <seconds-until-UTC-midnight>` header.
- Admin exemption: `if request.state.user.role == Role.admin: return await call_next(request)` short-circuit at top of `share` middleware. Verified by scripted test: admin 21st share returns 201; member 21st share returns 429.
- Cap applies ONLY to `POST /api/share/`. `DELETE /api/share/{id}` (admin-only) and `GET /api/share/{token}` (anonymous consumption) untouched.
- E9 audit scenario coverage (Story 9.2 scenario 6) verifies both soft-alert log emission AND hard-fail behavior on the same member account.

## Epic 7: TOTP 2FA + recovery codes

**Goal.** Add optional second-factor authentication with eight mandatory single-use recovery codes generated once at enrollment; allow per-role enforcement via a config flag with the `agent` role explicitly excluded by fail-fast startup validation; close with a documented end-to-end recovery-code drill against `.190` capturing AuditLog row deltas.

**Acceptance gate.** Test user enrolls TOTP via Story 7.2 panel → logs out → logs back in via Story 7.3 partial-auth path with a fresh TOTP code → logs out → logs back in consuming a recovery code → regenerates recovery codes via Story 7.5 → disables TOTP via Story 7.5 → logs back in with password-only → drill artifact `2fa-recovery-drill-YYYY-MM-DD.md` (NFR5-OBS-2 first slot) committed under `_bmad-output/implementation-artifacts/` with per-step timestamps + request IDs + audit row references. Startup-fail test for `Role.agent in enforce_2fa_for_roles` passes (Story 7.4).

**FRs realized:** FR5-2FA-1..4, NFR5-INT-1 (agent fail-fast startup), NFR5-OBS-2 first artifact, FR5-AUDIT-1 (E7 subset: `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`).

**Architectural anchors:** Decisions D (`users.totp_secret` Fernet + `totp_enabled_at`), E (`recovery_codes` table + bcrypt-at-rest + batch grouping), F (`enforce_2fa_for_roles` config flag + lifespan-startup fail-fast).

**Blocked by:** E6 complete (member accounts exist as 2FA-enrolling subjects).

### Story 7.1: Alembic migration `0013_users_2fa_columns` + recovery-codes table + Fernet key plumbing

**Realizes:** FR5-2FA-1 (table foundation), FR5-AUDIT-1 (5 E7 action names registered in `KNOWN_ENTITY_TYPES`).
**Architectural anchor:** Decisions D (users column additions + Fernet key), E (recovery_codes table + indexes).
**Depends on:** 6.1 (Alembic chain continuity).

Acceptance check shape:

- `apps/api/alembic/versions/0013_users_2fa_columns.py` adds `users.totp_secret VARCHAR(255) NULL` + `users.totp_enabled_at DATETIME NULL` + `recovery_codes` table per Decision E column spec + 2 indexes; existing `admin` + `agent` rows verified NULL-default (NFR5-INT-1 null-op migration semantics).
- `TOTP_FERNET_KEY: str` added to `apps/api/app/core/config.py` Pydantic Settings; absence raises `RuntimeError` at startup (fail-fast — no unconfigured deployment can accidentally store plaintext secrets).
- `infra/env.example` adds `TOTP_FERNET_KEY=<generate-with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">` documentation line.
- `apps/api/tests/conftest.py` adds `TOTP_FERNET_KEY` test override (deterministic test key).
- 5 new audit action names registered in `KNOWN_ENTITY_TYPES`: `auth.totp.enrolled`, `auth.totp.disabled`, `auth.totp.verify.success`, `auth.totp.verify.fail`, `auth.recovery_code.used`.

### Story 7.2: TOTP enrollment endpoint + UI (`POST /api/auth/2fa/enroll` + confirm + `/settings/2fa`)

**Realizes:** FR5-2FA-1.
**Architectural anchor:** Decisions D (Fernet encryption boundary + serializer omit of `totp_secret`), E (8 recovery codes batch generation).
**Depends on:** 7.1 (migration + Fernet key).

Acceptance check shape:

- `POST /api/auth/2fa/enroll` (authenticated, any role except agent) generates a pyotp secret + provisioning URI; returns `{qr_svg, manual_secret, enrollment_token}` (enrollment_token Redis-stashed 10min to bridge enroll → confirm).
- `POST /api/auth/2fa/enroll/confirm {enrollment_token, code}` verifies the 6-digit code, persists `totp_secret` Fernet-encrypted in `users.totp_secret`, sets `totp_enabled_at = NOW()`, generates 8 fresh recovery codes (`secrets.token_hex(4)`, 32 bits each) with shared `batch_id`, stores them bcrypt-hashed in `recovery_codes`, returns the 8 cleartext codes ONCE in the response body. Audit `auth.totp.enrolled` emitted with `actor_user_id == target_user_id`.
- `apps/web/src/modules/auth/Settings2faPage.tsx` React route at `/settings/2fa` walks the enroll flow: QR scan / manual entry → confirm code → display cleartext recovery codes with download-as-txt + clipboard-copy buttons + "I have saved these" confirmation modal that gates the page from advancing.
- Subsequent `GET /settings/2fa` page loads return only batch metadata (`{batch_id, generated_at, codes_remaining}`) — cleartext codes are unrecoverable per Decision E "display ONCE" property.
- `apps/api/app/core/db/serializers.py` explicitly omits `totp_secret` from any `users` row serialization (verified by scripted test against `/api/auth/me` response shape).

### Story 7.3: Login flow extension: partial-auth + TOTP / recovery-code verify step

**Realizes:** FR5-2FA-2.
**Architectural anchor:** Decisions D (decrypt-on-verify boundary), E (recovery code consumption iteration + bcrypt check).
**Depends on:** 7.2 (users can enroll).

Acceptance check shape:

- `POST /api/auth/login` for users with `totp_enabled_at IS NOT NULL` returns HTTP 200 + body `{partial_auth: true, totp_required: true, partial_token}` (NO `portal_access` cookie set); `partial_token` Redis-stashed 5min.
- `POST /api/auth/2fa/verify {partial_token, code}` accepts either a current 6-digit TOTP code OR an 8-char recovery code: validate-via-Fernet-decrypt for TOTP; iterate active batch (where `invalidated_at IS NULL`) calling `bcrypt.checkpw()` for recovery codes — first match sets `used_at` and emits `auth.recovery_code.used`. Success: issues `portal_access` + `portal_refresh` cookies + emits `auth.totp.verify.success`. Failure: HTTP 401 + `auth.totp.verify.fail`.
- Frontend `AuthGate` + `LoginPage` extended to detect `partial_auth` response and prompt for second-factor input; UI flow accepts either input type without an explicit switch (regex-distinguish TOTP `^\d{6}$` vs recovery code `^[0-9a-f]{8}$`).
- Story 6.6 login rate-limit (5 failures / 60s per IP) is unaffected — second-factor failures count against the same `login` scope key (defense in depth: brute-forcing the second factor still trips the IP rate-limit).
- Visual-regression baselines for the second-factor prompt screen added in same commit.

### Story 7.4: `enforce_2fa_for_roles` config + lifespan-startup fail-fast + middleware enforcement

**Realizes:** FR5-2FA-3, NFR5-INT-1 (agent fail-fast).
**Architectural anchor:** Decision F.
**Depends on:** 7.3 (login flow has 2FA path to enforce).

Acceptance check shape:

- `apps/api/app/core/config.py` adds `enforce_2fa_for_roles: list[Role] = Field(default_factory=list)`.
- `apps/api/app/main.py` lifespan-startup runs BEFORE Redis connection + BEFORE any route mount: `if Role.agent in settings.enforce_2fa_for_roles: raise RuntimeError(...)` with the verbatim error message from Decision F. Verified by `apps/api/tests/test_config.py::test_agent_role_in_enforce_2fa_raises`.
- `apps/api/app/core/auth/middleware.py` adds post-login pre-cookie-issue check: `if user.role in settings.enforce_2fa_for_roles and user.totp_enabled_at is None: return partial_auth_response_forcing_enrollment(user)` — frontend lands on `/settings/2fa` enrollment screen before any other route works for that user.
- Per-user override path (Decision F cascading) — admin force-enrollment endpoint (E8 Story 8.4) sets `totp_enabled_at` directly independent of config flag.
- `infra/env.example` documents `ENFORCE_2FA_FOR_ROLES=` (empty default; comma-separated role names; agent forbidden).

### Story 7.5: Regenerate recovery codes + disable TOTP from `/settings/2fa`

**Realizes:** FR5-2FA-4.
**Architectural anchor:** Decision E (batch invalidation + audit lifecycle columns).
**Depends on:** 7.2 (enrollment exists), 7.3 (verify path for re-auth).

Acceptance check shape:

- `POST /api/auth/2fa/recovery-codes/regenerate` requires re-auth body `{password, totp_code}` (verified against Story 7.3 verify primitives) before action; UPDATEs prior batch `invalidated_at = NOW() WHERE user_id = ? AND invalidated_at IS NULL` → INSERTs 8 fresh codes with new `batch_id` → returns cleartext codes ONCE in response body.
- `POST /api/auth/2fa/disable` requires re-auth body `{password, totp_code}`; clears `users.totp_enabled_at = NULL`, invalidates all `recovery_codes` rows for the user (`invalidated_at = NOW() WHERE invalidated_at IS NULL`), emits `auth.totp.disabled` with `actor == target`. Note: `users.totp_secret` is intentionally retained as Fernet ciphertext — disable does not delete the secret column, only clears the timestamp; rationale: enables future "I re-enrolled with the same authenticator app" path without secret rotation (low-priority optimization).
- Post-disable login flow returns to single-factor (Story 7.3 partial-auth path no longer triggers since `totp_enabled_at IS NULL`).
- UI panel at `/settings/2fa` exposes both actions behind a re-auth modal (password + current TOTP).

### Story 7.6: End-to-end recovery-code drill against `.190` + artifact authoring

**Realizes:** NFR5-OBS-2 first artifact slot.
**Architectural anchor:** Decision E (recovery codes lifecycle as drill subject).
**Depends on:** 7.2 + 7.3 + 7.5 (full 2FA lifecycle in place).

Acceptance check shape:

- Drill executed against deployed `.190` (NOT against CI fixtures or local dev — per brief Success Criterion #5 verbatim). Test-member account used as drill subject (seeded out-of-band ahead of drill).
- Drill steps captured with timestamps + request IDs + AuditLog row references: (1) enroll test user via `/settings/2fa` → confirm cleartext recovery codes saved out-of-band; (2) log out; (3) log in supplying password + TOTP from authenticator app → verify `auth.totp.verify.success` row; (4) log out; (5) log in supplying password + recovery code (1 of 8) → verify `auth.recovery_code.used` row + `auth.totp.verify.success` row; (6) regenerate recovery codes from `/settings/2fa` → verify prior batch `invalidated_at` populated, new batch displayed once; (7) disable TOTP → verify `auth.totp.disabled` row + `totp_enabled_at IS NULL`; (8) log in with password-only → verify normal single-factor flow restored.
- Artifact written to `_bmad-output/implementation-artifacts/2fa-recovery-drill-YYYY-MM-DD.md` (gitignored per `feedback_local_only_docs.md`); committed locally only.
- Artifact format mirrors the Init 1 verify-symbolication artifact shape (operator pattern familiarity from Init 1 Decision K precedent).
- Artifact serves as Epic 7 acceptance gate evidence — Epic 7 is not considered closed until the drill artifact lands.

## Epic 8: Admin panel: users + invites

**Goal.** Ship two new admin tabs (`/admin/users`, `/admin/invites`) on the existing admin module, soft-delete + `last_active_at` infrastructure (Redis `SET NX EX 300` throttle so SQLite writes stay at ≤1/5min/user), and the per-user action surface (change role, deactivate / reactivate, force logout-all-sessions, force-2FA-enrollment, issue password reset). Operator daily-driver path: zero panel-triggered operations require SQL inspection (brief Success Criterion #2).

**Acceptance gate.** All four brief-defined routine operator actions exercised via the panel UI on `.190`: generate invite (via E6 Story 6.3 endpoint surfaced via Invites tab in 8.6), revoke invite (via 8.6 panel button), change user role (via 8.3), reset user password (via 8.5). Plus the soft-delete + reactivate cycle (8.3), force-logout-all-sessions (8.3), force-2FA-enrollment (8.4) all panel-driven. Audit row visible for every panel action with correct `actor_user_id` / `target_user_id` pair.

**FRs realized:** FR5-ADMIN-1..3 (FR5-ADMIN-4 is the deliberate exclusion — no story), NFR5-PERF-1, FR5-AUDIT-1 (E8 subset: 7 action names — `user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`, `auth.totp.enrolled` actor!=target, `auth.password.reset.initiated`, `auth.password.reset.completed`).

**Architectural anchors:** Decisions A + B (admin-issued password-reset link reuses invite-token shape), F (force-2FA per-user override surface), I (soft-delete + `last_active_at` throttle).

**Blocked by:** E6 complete (member accounts exist as panel subjects), E7 complete (force-2FA action needs 2FA enrollment infrastructure).

### Story 8.1: Alembic migration `0014_users_is_active_last_active` + `LastActiveMiddleware`

**Realizes:** NFR5-PERF-1, FR5-AUDIT-1 (E8 action names registered).
**Architectural anchor:** Decision I.
**Depends on:** 7.1 (Alembic chain continuity).

Acceptance check shape:

- `apps/api/alembic/versions/0014_users_is_active_last_active.py` adds `users.is_active BOOLEAN NOT NULL DEFAULT TRUE` (backfill existing rows TRUE) + `users.last_active_at DATETIME NULL`; verified that Init 0 + Init 2 existing `admin` + `agent` rows backfill to `is_active = TRUE`.
- `apps/api/app/core/auth/middleware.py` adds `LastActiveMiddleware` per Decision I implementation: `SET NX EX 300` atomic Redis call gates DB write to ≤1/5min/user; runs after auth dependency resolution on authenticated requests only.
- 7 E8 audit action names registered in `KNOWN_ENTITY_TYPES`: `user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`, `auth.password.reset.initiated`, `auth.password.reset.completed` (the 7th, `auth.totp.enrolled` with actor!=target, was registered in 7.1; 8.4 emits it).
- Scripted test: 50 authenticated requests from one user within 1 minute produce exactly 1 `UPDATE users SET last_active_at` (verified via `apps/api/tests/integration/test_last_active_throttle.py` against fakeredis).

### Story 8.2: Admin Users tab (`/admin/users` route + `GET /api/admin/users` paginated list)

**Realizes:** FR5-ADMIN-1.
**Architectural anchor:** Decision I (`is_active` + `last_active_at` are panel-visible columns).
**Depends on:** 8.1 (columns exist to display).

Acceptance check shape:

- `GET /api/admin/users?page=N&page_size=M&search=<email-substring>` returns paginated rows with columns `{id, email, role, created_at, last_active_at, totp_enabled (derived: totp_enabled_at IS NOT NULL), is_active}`; requires `current_admin`.
- `apps/web/src/modules/admin/UsersPage.tsx` React route at `/admin/users` renders the paginated table with column sort (email, role, created_at, last_active_at) + search input + page-size selector.
- Pagination defaults match existing admin-list defaults (Init 0 pattern: 25 rows per page).
- Visual-regression baselines for `/admin/users` empty / one-row / many-row states added in same commit.
- **Negative AC (FR5-ADMIN-4 enforcement):** the Users tab UI exposes NO `select all` checkbox column header, NO row-level multi-select checkboxes, NO bulk-action menu (`Bulk role change`, `Bulk disable`, etc.); the per-row action menu shipped in Story 8.3 is the ONLY action surface. Verifiable: a Playwright snapshot test asserts the absence of bulk-select / bulk-action selectors. The deliberate exclusion is recorded so future agents (UI redesigns, panel-v2 considerations) do not infer missing bulk CRUD as a defect.

### Story 8.3: Per-user actions: change role, deactivate / reactivate, force logout-all-sessions

**Realizes:** FR5-ADMIN-2 (subset), FR5-AUDIT-1 (`user.role_changed`, `user.deactivated`, `user.reactivated`, `user.force_logout`).
**Architectural anchor:** Decision I (soft-delete + force-logout via existing refresh-token family invalidation).
**Depends on:** 8.2 (users tab UI), 8.1 (`is_active` column).

Acceptance check shape:

- `PATCH /api/admin/users/{id}` accepts `{role?, is_active?}` mutations; per-mutation emits one audit row (`user.role_changed` if role changed; `user.deactivated` if `is_active false`; `user.reactivated` if `is_active true→true-after-false` — verified by reading prior value). All emit with `actor_user_id == admin.id`, `target_user_id == path-id`.
- `POST /api/admin/users/{id}/force-logout` invokes existing `apps/api/app/modules/auth/sessions/service.py` revoke-all helper to invalidate every refresh-token family for the target user → emits `user.force_logout`. After ≤10 minutes the target's access token expires and they are fully logged out (per Decision I "JWT-based requests stay valid until natural expiry").
- Deactivation behavior verified end-to-end: target user with `is_active = FALSE` attempting `POST /api/auth/refresh` returns HTTP 401 + emits `auth.login.fail` reason `account_deactivated` + invalidates the refresh-token family (matches Init 0 reuse-detection invalidation pattern).
- UI on Users tab: per-row action menu with "Change role" / "Deactivate" / "Reactivate" / "Force logout all sessions"; each gated by a confirmation modal.

### Story 8.4: Admin 2FA overrides per-user: force-enrollment + force-disable (lockout recovery)

**Realizes:** FR5-ADMIN-2 (subset — both force-enrollment and force-disable per `actor != target` audit shape), FR5-AUDIT-1 (`auth.totp.enrolled` with `actor != target` + `auth.totp.disabled` with `actor != target`).
**Architectural anchor:** Decision F (per-user override path independent of `enforce_2fa_for_roles` config flag — applies to BOTH directions: force-enroll and force-disable).
**Depends on:** 7.4 (config-flag enforcement path exists; per-user override wired into same middleware check), 7.5 (user-side disable-TOTP endpoint exists; this Story adds the admin-side mirror with different auth contract — admin actor instead of user actor, no user-password+TOTP re-auth requirement since the lockout-recovery scenario implies the user CANNOT supply those).
**Depended on by:** 8.5 (admin-issued password-reset link references this Story's force-disable-2FA endpoint as Step 1 of the lost-2FA-AND-lost-recovery-codes recovery flow).

Acceptance check shape:

- **Force-2FA-enrollment endpoint:** `POST /api/admin/users/{id}/force-2fa-enrollment` flags the target user for mandatory-enrollment-on-next-login (implementation: set a `users.force_2fa_enrollment BOOLEAN` flag — added in this story as a minor column addition reusing the 0014 migration or a new tiny 0015 migration per implementer's call; or alternatively reuse Decision F middleware path by checking the target's user record at login and routing to `/settings/2fa`). Audit `auth.totp.enrolled` with `actor_user_id == admin.id`, `target_user_id != actor_user_id`, plus a `force_enrolled: true` extra field in the audit payload. On next login, target lands on `/settings/2fa` enrollment screen before any other route works (same path as Decision F config-flag enforcement). After target completes enrollment, the flag is cleared automatically (one-shot).
- **Force-disable-2FA endpoint (lockout recovery):** `POST /api/admin/users/{id}/force-disable-2fa` clears `users.totp_enabled_at = NULL` for the target user, invalidates all `recovery_codes` rows for that user (`invalidated_at = NOW() WHERE invalidated_at IS NULL`), emits `auth.totp.disabled` with `actor_user_id == admin.id`, `target_user_id != actor_user_id`, plus an `admin_override: true` extra field in the audit payload. Requires `current_admin` only — does NOT require the target user's password + current TOTP (the user-side 7.5 disable endpoint requires those for self-disable; this admin-side endpoint is the lockout-recovery mirror that bypasses re-auth precisely because the user is presumed locked out). `users.totp_secret` Fernet ciphertext is retained (matches Story 7.5 retention policy).
- **UI on Users tab:** two per-row action menu entries:
  - "Force 2FA enrollment" — enabled only when target's `totp_enabled = false`.
  - "Force-disable 2FA (lockout recovery)" — enabled only when target's `totp_enabled = true`; gated by a confirmation modal explaining the recovery context + recommending immediate password-reset issuance (Story 8.5) as the typical follow-up step.
- **Force-disable endpoint is NOT rate-limited beyond standard admin rate-limit budget** — it is an operator-triggered low-frequency action, not a public surface.
- **Audit traceability:** both endpoints emit audit rows queryable via `/api/admin/audit?action=auth.totp.enrolled&force_enrolled=true` (force-enrollment view) and `/api/admin/audit?action=auth.totp.disabled&admin_override=true` (force-disable view).

### Story 8.5: Admin-issued password-reset link

**Realizes:** FR5-ADMIN-3, FR5-AUDIT-1 (`auth.password.reset.initiated`, `auth.password.reset.completed`).
**Architectural anchor:** Decisions A + B (token shape reuse — Redis-fronted single-use opaque token), I (lost-2FA-AND-lost-recovery-codes recovery path: admin force-disables 2FA via Story 8.4 endpoint first, then issues reset via this Story).
**Depends on:** 6.2 (invite-token service primitives generalize to reset tokens), 8.3 (admin user-actions UI), 8.4 (force-disable-2FA endpoint exists as Step 1 of lost-2FA recovery flow — concrete endpoint, not "planned").

Acceptance check shape:

- `POST /api/admin/users/{id}/password-reset` mints a single-use 256-bit opaque token; stores at Redis key `invite:reset:{token}` (TTL default 1h configurable via `PASSWORD_RESET_TTL_SECONDS` Pydantic Settings field) with value `{user_id, generated_by, generated_at}`. NO DB-row audit history is needed at the password-reset-link tier — `auth.password.reset.initiated` audit row captures issuance; `auth.password.reset.completed` captures consumption. Returns `{reset_url}` to admin (one-time display, mirrors invite-token UX).
- Public `POST /api/auth/password-reset?token=<token>` consumption endpoint accepts `{token, new_password}`; runs zxcvbn ≥3 ≥12-char check (same gate as registration); on success updates `users.password_hash` + emits `auth.password.reset.completed` + DELs Redis key (single-use semantics).
- `apps/web/src/modules/auth/ResetPasswordPage.tsx` React route at `/reset-password` mirrors `/register` form's password-strength gates.
- **Lost-2FA-AND-lost-recovery-codes recovery flow (two explicit steps):** Step 1 — operator invokes Story 8.4 `POST /api/admin/users/{id}/force-disable-2fa` endpoint, audit `auth.totp.disabled` with `actor != target` + `admin_override: true`. Step 2 — operator invokes this Story's `POST /api/admin/users/{id}/password-reset` endpoint, audit `auth.password.reset.initiated`. The two-step flow is documented in `docs/operations.md` (operator runbook section authored in Story 10.4 closing commit) with explicit endpoint references rather than the previously-ambiguous "via existing 7.5 / planned admin-disable" phrasing.
- Endpoint rate-limited via Story 6.6 middleware (`register` scope shared — 3 attempts / 60s per IP; reset and register share the public-write rate-limit budget by design).

### Story 8.6: Admin Invites tab (`/admin/invites` route + status filter UI)

**Realizes:** FR5-ADMIN-1, FR5-INVITE-2 (UI surface on top of 6.3 endpoint), FR5-INVITE-3 (panel revoke button calls 6.3 revoke endpoint).
**Architectural anchor:** Decisions A + B (DB row metadata surfaced in UI).
**Depends on:** 6.3 (admin invite endpoints).

Acceptance check shape:

- `apps/web/src/modules/admin/InvitesPage.tsx` React route at `/admin/invites` calls `GET /api/admin/invites?status=...` from 6.3; renders paginated table with `status` filter dropdown (active / used / expired / revoked / all) + per-row metadata columns (`generated_by`, `generated_at`, `role`, `ttl_seconds`, `used_by`, `used_at`, `used_from_ip`, `revoked_at`).
- "Generate invite" button opens a modal collecting `{role, ttl_preset | custom_ttl_seconds}` → calls 6.3 `POST /api/admin/invites` → displays the cleartext token + `registration_url` in a copy-friendly one-time modal (matches Decision B "cleartext token surfaces ONCE" property).
- Per-row "Revoke" button (active invites only) calls 6.3 `POST /api/admin/invites/{id}/revoke` → row transitions to `revoked` state.
- Visual-regression baselines for empty / mixed-status / generate-modal / revoke-confirm states added in same commit.

## Epic 9: Security audit (HARD GATE — blocks E10)

**Goal.** Pre-cutover audit using `bandit` + `semgrep` + `pip-audit` + `npm audit` / `osv-scanner` + OWASP ZAP active scan against `.190` + `codex review` countersignature for each Medium disposition. Produce a signed-off audit report at `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` meeting the NFR5-SEC-1 gate condition: zero open Critical/High findings; at most three "accepted-with-rationale" Medium findings; the fourth forces auto-fail and triggers a fix sprint.

**Acceptance gate.** **HARD GATE for E10.** Audit report signed off with explicit gate-condition decision line: either "E10 cleared to proceed" (PASS) or "E10 blocked, fix sprint required" with the list of triaging issues. There is NO bypass flag, NO override path, NO `--force` flag in any cutover script. If the audit fails, the cutover is parked and the failing findings triage into a fix sprint before the audit reruns and the gate re-evaluates. Critical and High findings have NO "accepted" disposition path — fixed-or-bust. Mediums get max-3 cap; the 4th is auto-fail.

**FRs / NFRs realized:** NFR5-SEC-1, NFR5-SEC-2, NFR5-SEC-3 (six-scenario coverage matrix); audit verification of FR5-RATELIMIT-1 + FR5-RATELIMIT-2 + FR5-MEMBER-3 (Story 6.6 / 6.7 / 8.x outputs are verified-under-load here, not first-implemented).

**Architectural anchors:** Decisions G + H provide the rate-limit middleware and per-member share cap as the audit subjects under NFR5-SEC-3 scenarios 5 + 6; the rest of the audit scope (scenarios 1–4) covers the cookie+JWT + CSRF + admin/IDOR surfaces from Init 0 baseline, with the auth-surface additions from E6 + E7 + E8 layered on top.

**Blocked by:** E6 + E7 + E8 complete (audit subjects exist).

**Critical property (encoded in this section as a load-bearing structural reminder for future agents):** E9 is an epic, NOT a story tacked onto the cutover. Multi-PR security batches from review docs are epics in disguise (per `feedback_default_to_bmad_workflow.md`). The sequencing — pay the audit cost before the LAN whitelist drops, not after — is the operator's banking-IT instinct encoded as a planning structure (brief §"What Makes This Special" property #2).

### Story 9.1: Audit tooling install + run baseline

**Realizes:** NFR5-SEC-1 (tooling foundation).
**Architectural anchor:** none (process / tooling).
**Depends on:** E6 + E7 + E8 complete.

Acceptance check shape:

- `bandit -r apps/api workers/render` runs clean (zero Critical / zero High; Medium-or-below allowed pending Story 9.3 disposition). Output saved as `_bmad-output/implementation-artifacts/audit-raw/bandit-YYYY-MM-DD.txt` (gitignored).
- `semgrep --config auto --config p/owasp-top-ten apps/api apps/web workers/render` runs; output saved as `audit-raw/semgrep-YYYY-MM-DD.json`.
- `pip-audit` (against `apps/api/pyproject.toml` + `workers/render/pyproject.toml`) + `npm audit --audit-level=moderate` (against `apps/web/package.json`) — outputs saved.
- OWASP ZAP active scan against `https://3d.ezop.ddns.net` post-deploy (with seeded test-member account + admin account credentials provided via authenticated-scan policy file). Output: `audit-raw/zap-YYYY-MM-DD.html`.
- All raw outputs aggregated into a single "Tools run summary" table in the audit report skeleton (created in Story 9.4).

### Story 9.2: Six-scenario audit coverage execution

**Realizes:** NFR5-SEC-3, audit verification of FR5-RATELIMIT-1 + FR5-RATELIMIT-2 + FR5-MEMBER-3.
**Architectural anchor:** Decisions G (rate-limit verification target), H (per-member share cap verification target).
**Depends on:** 9.1 (tooling installed).

Acceptance check shape — six scenarios per NFR5-SEC-3 + brief working assumptions, each producing a PASS / FAIL / MITIGATED row in the audit report with reproducer command preserved:

1. **Invite-token brute force:** scripted ≥10⁶-attempt loop against `POST /api/auth/register?token=<varying>` — Story 6.6 `register` rate-limit (3 attempts / 60s per IP) MUST reject before 256-bit entropy depletion by ≥10⁶ margin (trivially satisfied: 3 attempts × 60s per IP × 1 IP = 3 attempts per minute = ~4.3 attempts/day ≪ 256-bit search space). PASS criterion: HTTP 429 returned on 4th attempt within 60s.
2. **Refresh-token replay:** scripted replay of a recently-rotated `portal_refresh` against `POST /api/auth/refresh` — Init 0 family-rotation reuse-detection MUST trigger `auth.refresh.reuse_detected` and invalidate the entire family. PASS criterion: audit row emitted + subsequent refresh attempts on any token in the family return HTTP 401.
3. **CSRF / JWT tampering:** for each mutating endpoint introduced in E6 + E7 + E8, verify CSRF middleware rejects requests without `X-Portal-Client: web` header (HTTP 403 reason `csrf_missing`); for each cookie-issuing endpoint, verify a tampered JWT (re-signed or expired) returns HTTP 401. PASS criterion: 0 mutating endpoints accept a tampered/CSRF-stripped request.
4. **IDOR scan on `/api/admin/*`:** for each admin endpoint introduced in E6 + E8 (invite gen/list/revoke, user PATCH, user force-logout, force-2fa, password-reset), verify a member-authenticated request returns HTTP 403 (matches Decision C per-route allowlist). PASS criterion: 0 admin endpoints reachable by a member-role principal.
5. **Rate-limit verification on `/api/auth/login`:** `siege`/`hey` benchmark from one IP at 6+ failures/60s MUST trip HTTP 429 (matches Success Criterion #6 verbatim). PASS criterion: HTTP 429 returned on 6th call.
6. **Member share-link amplification (FR5-MEMBER-3):** scripted 21-share-creation burst from one member account — soft-alert log MUST emit at the 10th creation; hard-fail HTTP 429 MUST return on the 21st creation. PASS criterion: both signals observed.

Each scenario emits a reproducer command preserved as `audit-raw/scenario-N-reproducer.sh` so any subsequent audit can re-run the same verification.

### Story 9.3: Codex review countersignature per Medium disposition

**Realizes:** NFR5-SEC-2.
**Architectural anchor:** none (process control on top of `feedback_invoke_codex_directly.md`).
**Depends on:** 9.1 + 9.2 produced a Medium-findings list.

Acceptance check shape:

- For each Medium finding from 9.1 + 9.2, the disposition (`fixed` / `mitigated` / `accepted-with-rationale`) is documented in the audit report draft with the relevant patch SHA + a `codex review --commit <SHA>` invocation against that patch.
- The `codex review` output is captured (per `feedback_codex_review_invocation.md` — mode flag standalone OR `cat prompt.md | codex exec --sandbox read-only -`) and a one-line summary cited in the disposition row.
- "Accepted-with-rationale" Medium findings specifically get an explicit countersignature line in the audit report: `countersigned: codex review SHA=<commit>, date=<YYYY-MM-DD>` per NFR5-SEC-2 verbatim.
- Self-attestation mitigation rationale (operator is both auditor and gate-keeper) is documented in the audit report Methodology section as the compensating control alongside the max-3-Mediums cap.

### Story 9.4: Audit report authoring + gate-condition sign-off

**Realizes:** NFR5-SEC-1 (gate sign-off), FR5-AUDIT-1 (no new audit actions — the audit report itself is the artifact, not a `record_event` row).
**Architectural anchor:** none (output artifact); format mirrors Init 1 verify-symbolication / 2fa-recovery-drill artifact precedents for operator familiarity.
**Depends on:** 9.1 + 9.2 + 9.3 complete.

Acceptance check shape:

- `_bmad-output/implementation-artifacts/security-audit-YYYY-MM-DD.md` authored with: Title + Date + Auditor + Methodology section (citing tooling stack from 9.1, scenario coverage from 9.2, codex countersignature pattern from 9.3, single-operator self-attestation mitigation from NFR5-SEC-2) + Tools run summary table + Six-scenario coverage table (PASS / FAIL / MITIGATED per scenario) + Findings disposition table (one row per finding: severity / source / disposition / patch SHA / codex countersignature SHA where applicable) + Explicit Gate-condition decision line.
- Gate-condition decision line is one of: (a) `**E10 cleared to proceed** — gate condition PASS: zero open Critical/High findings; N accepted-rationale Mediums (N ≤ 3); audit complete on YYYY-MM-DD`, OR (b) `**E10 blocked, fix sprint required** — gate condition FAIL: <reason: M open Criticals OR P open Highs OR Q accepted-rationale Mediums (Q ≥ 4)>; triaging the following findings: <list>; audit reruns after fix sprint`.
- On PASS: E10 stories unblock per sequencing.
- On FAIL: the failing findings are triaged into a fix sprint (likely new E9.x or carry-over E9.x stories created via CC re-invocation per AGENTS.md vanilla-first subsection — NOT a procedural drift; CC is canonical for post-ship scope change including "this audit failed, what now"); audit reruns AFTER fix sprint closes; this Story is not considered closed until a PASS decision is signed off.
- Artifact committed to local `_bmad-output/` only (gitignored per `feedback_local_only_docs.md`).

## Epic 10: Edge cutover (atomic)

**Goal.** Atomic single-commit edit in the sibling nginx config repo (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`) dropping both `auth_basic` and the IP allowlist; preserve share + agent-runbook bypasses; execute a four-scenario post-reload smoke matrix against `.190`; execute a verified rollback drill (≤30s end-to-end) before the cutover is considered closed; close with a non-skip-prefixed commit in `3d-portal` (`docs/operations.md` cutover-date update) recording the cutover within `3d-portal` deploy history.

**Acceptance gate.** All four smoke scenarios PASS post-reload; rollback drill PASS (revert + reload + smoke re-run all-PASS, revert-the-revert + reload + smoke re-run all-PASS); closing commit landed; Initiative 5 considered complete here. **Strictly blocked by E9 audit PASS (NFR5-SEC-1 gate condition).** If at any point during execution a smoke scenario regresses post-reload, the rollback sequence executes immediately per Decision K (≤30s end-to-end).

**FRs / NFRs realized:** FR5-CUTOVER-1..3, NFR5-PERF-2, NFR5-CROSS-REPO-1..2, NFR5-INT-1..2 (verified through smoke scenarios + nginx-bypass preservation), NFR5-OBS-2 second artifact slot (`cutover-smoke-YYYY-MM-DD.md`).

**Architectural anchors:** Decisions J (smoke matrix definition + 4 scenarios + artifact format), K (nginx config diff + atomic single-commit + rollback sequence + pre-flight `nginx -t` gate + commit-message conventions + cross-repo skip-gate cascade).

**Blocked by:** **E9 audit PASS (NFR5-SEC-1 gate condition).** No bypass.

### Story 10.1: Pre-cutover fixture seeding + `cutover-smoke.sh` authoring

**Realizes:** FR5-CUTOVER-2 (smoke script foundation), NFR5-OBS-2 (artifact format).
**Architectural anchor:** Decision J (4-scenario table + artifact shape).
**Depends on:** E6 + E7 + E8 complete (test fixtures depend on member registration + invite generation surfaces); E9 audit PASS confirmed before this story starts.

Acceptance check shape:

- Three test fixtures seeded ≥24h before the cutover commit:
  - test-member account registered via panel-issued invite (E8 Story 8.6 generate-invite flow).
  - hourly cron-refreshed share-token (preserves through cutover; cron in `infra/scripts/cutover-share-token-refresh.sh` runs hourly on dev box; share token URL recorded for scenario 1).
  - minimal STL fixture (3KB sample model) added to fixture storage for agent POST scenario 2.
- `infra/scripts/cutover-smoke.sh` authored with: `set -euo pipefail` + dependency check (`jq curl`) + 4 sequential scenarios per Decision J table + per-scenario `http_code` + `request_id` + audit-row-delta capture + ANSI-colored PASS / FAIL output to stdout + stderr-narrative for errors + 30s wall-clock total budget + `--help` flag printing usage. Bash conventions match Init 1 § AR12.
- Smoke output template documents the artifact format (Markdown table with scenario / expected / actual / status / timestamp / request_id / audit delta columns) + Rollback drill timing block.
- Pre-flight script `infra/scripts/cutover-preflight.sh` (optional, operator-run before cutover) verifies all three fixtures are live and the smoke script self-test passes.

### Story 10.2: Sibling nginx commit authoring + pre-flight `nginx -t` gate

**Realizes:** FR5-CUTOVER-1.
**Architectural anchor:** Decision K (concrete diff + commit-message convention + pre-flight gate).
**Depends on:** 10.1 (smoke script ready to verify the cutover).

Acceptance check shape:

- Edit to `~/repos/configs/nginx/3d.ezop.ddns.net.conf` matches the Decision K concrete diff exactly: drop server-level `auth_basic "3d-portal"` + `auth_basic_user_file /etc/nginx/.htpasswd-portal` + `allow 192.168.2.0/24` + `allow 10.8.0.0/24` + `deny all`; drop per-location `auth_basic off;` + `allow all;` in both `location /share/` and `location /agent-runbook` (they become redundant once the server-level block is gone). The `proxy_pass` + `proxy_set_header` lines in every location block stay untouched.
- Sibling repo commit message: `feat(nginx): drop auth_basic + IP allowlist for 3d-portal cutover`. Conventional-commit `feat(nginx)` matches sibling repo style. Body references `3d-portal` issue + cutover artifact path + Decision K cross-reference.
- Pre-flight gate: `ssh .180 'sudo nginx -t'` MUST PASS BEFORE `git push origin main` in sibling repo. If `nginx -t` fails, the cutover is aborted before reload — no traffic disruption.
- The commit is NOT pushed in this story — Story 10.2 produces the commit locally + verifies syntax; Story 10.3 pushes + reloads + smokes atomically.

### Story 10.3: Atomic cutover execution + 4-scenario smoke run + rollback drill

**Realizes:** FR5-CUTOVER-2, FR5-CUTOVER-3, NFR5-PERF-2, NFR5-INT-1 (smoke scenario 2 verifies agent ingestion unchanged + nginx bypass preserved), NFR5-INT-2 (smoke scenario 1 verifies share bypass preserved), NFR5-CROSS-REPO-2 (rollback drill spans both repos), NFR5-OBS-2 (cutover-smoke artifact written).
**Architectural anchor:** Decisions J, K (executable rollback sequence).
**Depends on:** 10.2 (commit ready + nginx -t passing locally on .180), 10.1 (smoke script + fixtures ready).

Acceptance check shape:

- Cutover sequence (sequential, total ≤5 minutes per NFR5-PERF-2):
  1. `git push origin main` in sibling repo (`~/repos/configs/`).
  2. `ssh .180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'` — `nginx -t` MUST PASS again on the freshly-pulled commit; reload executes atomically.
  3. `bash infra/scripts/cutover-smoke.sh` against `https://3d.ezop.ddns.net` — all 4 Decision J scenarios MUST PASS within ≤30s total wall-clock.
  4. Rollback drill: `cd ~/repos/configs && git revert <cutover-sha> --no-edit && git push origin main` → `ssh .180 'cd ~/configs && git pull && sudo nginx -t && sudo nginx -s reload'` → re-run smoke script → all 4 PASS confirms rollback works → `git revert <revert-sha> --no-edit && git push origin main` → `ssh .180` reload → re-run smoke script → all 4 PASS confirms re-apply works.
- Any FAIL in step 3 triggers immediate rollback per the same Decision K sequence (≤30s end-to-end) without proceeding to step 4 drill.
- Cutover-smoke artifact `_bmad-output/implementation-artifacts/cutover-smoke-YYYY-MM-DD.md` (NFR5-OBS-2 second slot) captures: per-scenario timestamps + request IDs + audit-row deltas (from scenarios 2, 3, 4 audit emissions) + rollback drill timing block (revert-reload-smoke-revert-reload-smoke total wall-clock) + cutover commit SHA + revert commit SHA + revert-the-revert commit SHA.
- Artifact committed to local `_bmad-output/` only (gitignored).

### Story 10.4: Closing `docs/operations.md` cutover-date commit in `3d-portal`

**Realizes:** NFR5-CROSS-REPO-1 (records cutover in `3d-portal` deploy history; bypasses `deploy.sh` skip-gate via non-skip prefix).
**Architectural anchor:** Decision K (cascading note on deploy-history closing commit).
**Depends on:** 10.3 (cutover landed and stable).

Acceptance check shape:

- Edit to `docs/operations.md` adds a new section describing the post-cutover portal-self-auth posture: nginx is now a thin TLS terminator + share-bypass rewrite layer; portal authenticates itself via cookie+JWT; `member` role is invite-only via admin panel; 2FA enforcement is per-role config-flag-driven with `agent` role permanently excluded; rate-limit middleware protects the login / refresh / register / share surfaces; cross-references to `security-audit-YYYY-MM-DD.md` + `cutover-smoke-YYYY-MM-DD.md` + `2fa-recovery-drill-YYYY-MM-DD.md`.
- Commit message: `feat(infra): record edge cutover date 2026-MM-DD` (Conventional Commits `feat(infra)` — NON-skip-prefix per `bf919c2`/`0745209` skip-gate; the commit fires `deploy.sh` and records the cutover SHA in `infra/.last-deploy-sha`, surfacing the cutover within `3d-portal` deploy history per Decision K cascading note + `feedback_auto_deploy_dev.md` deploy invariant).
- Commit body references the sibling cutover commit SHA + the cutover-smoke + security-audit artifact paths.
- Auto-deploy fires per `feedback_auto_deploy_dev.md`; deploy is null-op for application code (no code changed) but updates `infra/.last-deploy-sha` to anchor future deploy-gate behavior at the post-cutover SHA.
- Initiative 5 considered complete at the merge of this commit. Retrospective (`bmad-retrospective`) scheduled as the next session per CC §5.2 handoff plan.

### Cross-references

- **Brief v2** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines; adversarial-review applied: P0×2 + P1×3 + P2×1 fixed). Binding content source for FR / NFR shape + working assumptions + Success Criteria + Vision trajectory.
- **Brief distillate** — `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5688 tokens, LLM-optimized).
- **Sprint Change Proposal** — `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-18-init5.md` (status `approved`, 2026-05-18). Doc-shape (single-file H2-append per §3.3 + §4.1), epic numbering (global E6-E10 per §3.4), per-artifact content outline (§4.2 2C governs this section), per-epic effort + risk estimates (§4.4), hard rules carried forward (§5.6).
- **PRD § Initiative 5** — `prd.md` lines 1065-1258 (24 FRs across 8 prefix groups + 12 NFRs across 6 categories). Each Story above cites one or more FR5-* / NFR5-* IDs the Story realizes. Forward reference from PRD: FR5-RATELIMIT-1 → Decision G → Story 6.6; FR5-CUTOVER-1 → Decision K → Stories 10.2 + 10.3.
- **Architecture § Initiative 5** — `architecture.md` lines 1399-1767 (Decisions A–K in-scope; L–N deferred). Each Story above cites one or more Decision letters as its architectural anchor. Forward references in architecture.md to this section: each Decision's "Cascading" note points to the realizing epic / story scope.
- **Sprint status** — `_bmad-output/implementation-artifacts/sprint-status.yaml` — to be extended in Session F via `bmad-sprint-planning` with `epic-6` ... `epic-10` keys + 27 per-story entries (status `backlog` on creation; status transitions per Init 0/1/2/3 precedent).
- **Implementation Readiness check** — to be authored in Session E via `bmad-check-implementation-readiness` (gates Session F sprint-planning); covers PRD ↔ UX ↔ Architecture ↔ Epics alignment across all five initiatives (Init 0/1/2/3 + Init 5; Init 4 reverted per `bf919c2`).
- **Init 0 baseline anchors:** auth stack (Init 0 § Auth module + `apps/api/app/core/auth/`), share-token Redis pattern (Init 0 § Share module + `apps/api/app/modules/share/`), audit log (Init 0 § Admin module + `apps/api/app/core/audit/` + `KNOWN_ENTITY_TYPES` registry), role enum (`apps/api/app/core/db/models/_enums.py:10-13` — `member` already enumerated). Init 5 is purely additive on these anchors; no Init 0 contract changes.
- **Init 1 baseline anchors:** GlitchTip plumbing (`apps/web/src/instrument.ts` + `JsonFormatter`) — NFR5-OBS-1 reuses this surface for all Init 5 namespaced loggers (`app.auth.invite`, `app.auth.totp`, `app.auth.register`, `app.admin.users`, `app.share.ratelimit.soft_alert`); bash script conventions (Init 1 § AR12) — Stories 7.6, 9.x, 10.1, 10.3 cutover-smoke + drill scripts follow this pattern.
- **Init 2 baseline anchors:** `agent` service account contract — NFR5-INT-1 preserves this exactly (Stories 7.4 startup fail-fast + 10.3 smoke scenario 2 + 10.3 nginx-bypass preservation).
- **Init 3 baseline anchors:** visual-regression matrix (4 projects: desktop-light / desktop-dark / mobile-light / mobile-dark) + Init 3 Principle 3 (UI changes ship with own baseline updates in same commit) — Stories 6.4, 7.2, 7.3, 8.2, 8.3, 8.4, 8.5, 8.6 each note "visual-regression baselines added in same commit"; axe-contrast scans active per Init 3 ESLint + Stylelint integration extend automatically to new admin pages + register / 2FA / reset-password screens.
- **Memory entries informing decisions:** `feedback_default_to_bmad_workflow.md` (E9 as epic-not-story discipline; multi-PR security batches are epics in disguise), `feedback_auto_deploy_dev.md` (Story 10.4 closing commit deploy invariant), `feedback_vanilla_bmad_first.md` v2 (monolithic H2-append pattern justification for this manual edit per `bmad-edit-epics` no-skill path), `feedback_bmad_skill_discovery_checklist.md` (session-start `bmad-help` confirmed manual edit canonical), `feedback_invoke_codex_directly.md` (Story 9.3 codex review countersignature mechanism), `feedback_local_only_docs.md` (drill + smoke + audit artifacts gitignored per `_bmad-output/` convention), `feedback_collaboration_division.md` (operator-driven content decisions encoded as locked Brief + PRD + Architecture inputs to this section; agent does NOT re-elicit closed decisions).
- **Out-of-scope reminders (Decisions L–N deferred + brief Q5 + PRD § "Out"):** self-service mail-based password reset (Decision L; blocked on self-hosted mail server initiative), OIDC/SSO federation (Decision M; brief Q5 confirmed non-goal), per-model ACL (Decision N; brief Q5 confirmed non-goal), social login, team accounts, user-to-user messaging, public read-only browse, email deliverability verification, webhook push, multi-tenant. Future initiatives may revisit (see Decision-letter "Where it goes" pointers in architecture.md).
