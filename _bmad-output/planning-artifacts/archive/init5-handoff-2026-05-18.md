---
type: bmad-handoff
created: 2026-05-18
status: ready-for-next-session
context: Initiative 5 planning was started using non-vanilla BMAD pattern (direct H2 append to prd.md + architecture.md). Reverted 2026-05-18 to align with vanilla BMAD-first principle. Decisions are preserved in source artifacts; next session starts fresh with `bmad-correct-course`.
---

# Initiative 5 — Public Registration & User Account Management — Handoff

## Why this handoff exists

The 2026-05-18 BMAD planning session for Initiative 5 (user accounts + invites + 2FA + admin panel + edge cutover) drifted from vanilla BMAD methodology:

- Reached for `bmad-create-prd` on a finished `prd.md` (skill protested, agent routed-around to `bmad-edit-prd` without consulting operator)
- Followed the non-vanilla `## Initiative N` H2-section-append pattern entrenched in `prd.md` / `architecture.md` from prior initiatives without questioning it
- Edited `architecture.md` directly (no `bmad-edit-architecture` skill exists; vanilla path is `bmad-correct-course` → rerun `bmad-create-architecture`)
- Never called `bmad-help` (the canonical "where do I start?" skill)
- Never considered `bmad-correct-course` (the canonical post-ship evolution entry point)

Operator caught the drift mid-flow. Decision: revert non-vanilla additions, capture work in this handoff, restart cleanly in next session using vanilla skill flow.

## Current state (as of 2026-05-18 end-of-session)

**Preserved (source-of-truth for all Initiative 5 decisions):**

- `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines, v2 with adversarial review pass applied)
- `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5,688 tokens, LLM-optimized compressed brief; downstream BMAD chain input)

**Reverted (non-vanilla additions removed):**

- `prd.md` — restored to 1058 lines (was 1251 lines with Init 5 H2 section appended). Frontmatter `initiatives:` array no longer contains Init 5 entry. Initiatives Index table no longer contains Init 5 row.
- `architecture.md` — restored to 1392 lines (was 1957 lines with Init 5 H2 section appended). Same frontmatter + index revert.

Verification: `grep -c "Initiative 5\|id: 5" prd.md architecture.md` returns `0:0`.

**Process artifacts saved:**

- `~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_vanilla_bmad_first.md` — principle memory
- `~/.claude/projects/-home-ezop-repos-3d-portal/memory/feedback_bmad_skill_discovery_checklist.md` — 4-step checklist memory
- `MEMORY.md` updated with both new entries
- `AGENTS.md` § "Workflow expectations" extended with new "BMAD vanilla-first" subsection (vanilla-first principle + skill discovery checklist + brownfield routing through `bmad-correct-course`)

**Implementation status:** nothing implemented. All Init 5 work to date is in planning/design artifacts only. Zero code commits, zero migrations, zero new modules.

## What was decided (preserved in brief + distillate)

These are the locked decisions that the next session's `bmad-correct-course` should treat as binding inputs, NOT re-elicit:

### Scope shape
- Five sequenced epics: 5.1 invite + member role; 5.2 TOTP 2FA + recovery codes; 5.3 admin panel; 5.4 security audit (hard gate); 5.5 atomic edge cutover (dropping nginx basic-auth + IP allowlist).
- Epic 5.4 hard-gates Epic 5.5 (zero open Critical/High; ≤3 accepted-with-rationale Mediums each with `codex review --commit <SHA>` countersignature).
- First wave: friends-and-family ~10-20 people in first 90 days. NOT a public launch.

### Operator-locked decisions (brief v2 Q1-Q5 elicitation + adversarial review pass)
- Native accounts only (no OIDC/social/federation in Init 5).
- 3 roles: `admin`, `member`, `agent`. Member gains exactly one new permission bit beyond anon-LAN-browse: share-link generation.
- Invite tokens: single-use, configurable TTL preset (1d/3d/7d/30d + custom), pre-bound role, 256-bit `secrets.token_urlsafe(32)`, dual-backed Redis primary + DB row for audit history, token plaintext NEVER stored in DB.
- 2FA TOTP via `pyotp` + `qrcode`, optional by default, config-driven per-role enforcement via `enforce_2fa_for_roles: list[Role]` flag (must reject `agent` role). 8 mandatory recovery codes, bcrypt-hashed, shown once at enrollment.
- Password policy: `zxcvbn-python` score ≥3, min 12 chars.
- Admin-only password reset via OOB-delivered one-time link (no mail server until separate future initiative).
- Edge cutover: atomic single sibling-repo commit (`~/repos/configs/nginx/3d.ezop.ddns.net.conf`), dropping `auth_basic` + IP allowlist together. 4-scenario post-reload smoke matrix.
- Security audit tooling: bandit + semgrep (OWASP-top-10) + pip-audit + npm audit / osv-scanner + OWASP ZAP active scan + codex review per commit on new modules.
- Out-of-scope (operator-confirmed Q5, non-negotiable): social login, OIDC federation, per-model ACL, team accounts, user-to-user messaging in portal, public read-only browse mode, self-service email password reset, email deliverability verification, webhook push, multi-tenant.

### Architecture decisions (sketched but should be re-derived through vanilla `bmad-create-architecture` flow when CC routes there)

The previous session designed 11 architecture decisions (A-K) plus 3 deferred (L-N). These are in the (since-reverted) Initiative 5 H2 section of `architecture.md` but ALSO captured succinctly in the brief's "Working Assumptions" + distillate's relevant sections. Highlights to surface during the vanilla `bmad-create-architecture` flow:

- Invite storage write order: DB-first then Redis SET (fail-safe = orphan inert DB row, NOT orphan public-facing token).
- Recovery codes table with `generation_batch` UUID for atomic regen + partial index `WHERE consumed_at IS NULL`.
- Rate-limit strategy: Redis sliding-window log (sorted set + pipelined ZADD/ZREMRANGEBYSCORE/ZCARD).
- `_require_roles(*allowed: Role)` factory pattern for FastAPI dependencies (replaces hand-rolled per-role functions).
- Member share-token cap: 5/5min burst + 20/24h hard cap, soft-fail at 10/24h with `auth.ratelimit.softfail` audit row.
- Migration sequencing: 3 separate Alembic migrations (0012 invite_tokens / 0013 users 2FA + recovery_codes / 0014 users lifecycle + password_reset_tokens) matching epic boundaries for rollback granularity.
- `enforce_2fa_for_roles` validated via Pydantic `field_validator` rejecting `Role.agent` at API startup (fail-fast).
- 18 new `KNOWN_ENTITY_TYPES` audit-log actions inserted alphabetically into `apps/api/app/core/audit.py`.

(These should NOT be re-elicited from scratch in next session. The brief Working Assumptions section + the reverted-but-recoverable git history of the deleted `## Initiative 5` H2 sections preserves the full reasoning. Use `git show <revert-commit>^:_bmad-output/planning-artifacts/architecture.md` to retrieve verbatim text if needed.)

## Next session — restart procedure

**Pre-flight (mandatory, in order):**

1. **Session-start `bmad-help` call** — per `AGENTS.md` § "Workflow expectations" first bullet, this is per-session mandatory regardless of task. Run it BEFORE reading anything else. Initial context for the call: "Resuming Initiative 5 user-accounts feature; brief + distillate exist; previous planning session was reverted for vanilla-BMAD non-compliance; where do I start?"
2. Read `AGENTS.md` § "Workflow expectations" → "BMAD vanilla-first" subsection.
3. Read `MEMORY.md` entries `feedback_vanilla_bmad_first` + `feedback_bmad_skill_discovery_checklist`.
4. Read this handoff doc fully.

**Skill flow (vanilla):**

1. **`bmad-help`** — already done in pre-flight step 1. The session has TWO scope questions to surface to `bmad-help` together (they are related):
   - **(a) Non-vanilla docs cleanup**: operator decision from end-of-2026-05-18 session — *"pozbywamy się długu w postaci non-vanilla/custom docs/artifacts przystosowując repo w pełni do vanilla BMAD"*. Concretely this means retro-migrating `## Initiative 0/1/2/3` H2 sections in monolithic `prd.md` + `architecture.md` to vanilla per-feature files (`prd-foundation.md`, `prd-glitchtip.md`, `prd-agent-runbook.md`, `prd-ui-theme.md` + same for architecture), plus updating cross-references, plus `epics.md` and `sprint-status.yaml` if they have multi-init structure too.
   - **(b) Initiative 5 planning route**: clean vanilla path for user-accounts feature using brief + distillate as inputs.
   - Expected `bmad-help` recommendation given both scope questions: route through `bmad-correct-course` — it's the canonical entry for both cleanup decisions and post-ship feature additions, and combining them in one CC pass means the cleanup result informs Init 5's doc shape decision.
   - If `bmad-help` recommends something else, surface that to operator before proceeding.
2. **`bmad-correct-course`** with inputs:
   - `product-brief-3d-portal-user-accounts.md`
   - `product-brief-3d-portal-user-accounts-distillate.md`
   - This handoff doc
   - Existing `prd.md` + `architecture.md` for state context
   - Output: change proposal recommending the route (likely options: new per-feature PRD file `prd-user-accounts.md` + new per-feature `architecture-user-accounts.md`, OR `bmad-edit-prd` modifying existing prd.md sections rather than appending, OR full rerun of `bmad-create-prd` producing a fresh `prd-v2.md`).
3. **Execute CC routing recommendations** using vanilla skills cleanly. Do NOT default to the H2-append pattern.

**Hard rules for next session:**

- If at any point a skill protests (e.g. `bmad-create-prd` detects finished workflow), STOP and consult operator. Do not route-around silently.
- If the temptation arises to add `## Initiative 5` H2 section to existing `prd.md` / `architecture.md`, STOP — that is the legacy non-vanilla pattern being reverted in this handoff.
- All Initiative 5 content decisions are LOCKED (see above). Next session re-derives the SHAPE (where decisions live in the doc tree) per vanilla skill recommendations, NOT the CONTENT.

## Open questions to surface to operator at next-session start

(Surface BEFORE running CC; let operator decide so CC has unambiguous input.)

1. **Cleanup of legacy non-vanilla state IS in scope for next session** (operator decision end-of-2026-05-18 session, after the AGENTS.md vanilla-first commit landed): retro-migrate `## Initiative 0/1/2/3` H2 sections out of monolithic `prd.md` + `architecture.md` to per-feature vanilla files. **NOT optional anymore** — earlier deferred-stance was overridden. CC should propose the migration shape (one-shot full migration vs incremental per-initiative); operator will pick the approach in the change proposal review.
2. **Doc shape preference** — if CC offers multiple routes (new per-feature PRD file vs `bmad-edit-prd` on existing prd.md), operator should choose based on (a) how much they value single-doc locality vs vanilla file-per-feature, (b) downstream agent ergonomics for cross-init referencing.
3. **Budget context** — at handoff time: 5h 15%, 7d 11%, reset in 3h53m. Next session likely fresh window. CC + vanilla skill execution likely needs 30-60min of focused operator interaction.

## Related artifacts

- Brief: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts.md` (213 lines, v2)
- Distillate: `_bmad-output/planning-artifacts/product-brief-3d-portal-user-accounts-distillate.md` (~5,688 tokens)
- Memory: `feedback_vanilla_bmad_first.md`, `feedback_bmad_skill_discovery_checklist.md`
- AGENTS.md: § "Workflow expectations" → "BMAD vanilla-first" subsection (new 2026-05-18)
- Git history: NONE. `_bmad-output/` is gitignored (see `.gitignore:65`). The Init 5 additions to `prd.md` (193 lines) + `architecture.md` (565 lines) never reached git and are now permanently gone from the working tree. The brief + distillate are the authoritative source of truth for all locked decisions. The 23 FRs + 12 NFRs + 11 architecture decisions can be re-derived from those two artifacts during the next-session vanilla CC flow.
