---
title: "Sprint Change Proposal — Initiative 6 (Post-Cutover Default-Deny Auth Posture)"
type: sprint-change-proposal
initiative_scope: 6
status: done
approved_by: Ezop
approved_at: 2026-05-20
approved_via: one-word Polish "Approve" response after batch-presented full draft review (mode noted in mode field above)
shipped_at: 2026-05-21
shipped_via: 7 stories (11.1-11.7) shipped autonomously in Sesja BA + BB; all 5 cutover-smoke scenarios PASS post Story 11.7 sibling rollback; audit gate condition PASS at security-audit-2026-05-21.md
closing_commit: TBD (docs/operations.md update commit on main fires the closing deploy)
created: 2026-05-20
last_updated: 2026-05-20
author: Claude (BMAD bmad-correct-course skill, vanilla-aligned, ITCM autonomous mode) + Ezop (operator business alignment + approval)
mode: batch-presented (operator-pragmatic variant of BMAD Incremental — full draft surfaced once, operator feedback consolidated)
change_scope_classification: major
related_artifacts:
  - security-audit-2026-05-20.md                # supplemental High-002 finding (open after revert)
  - codex-review-64447ff-2026-05-20.md          # P1×2 + P2 verbatim, input to design
  - initiative-5-retro-2026-05-20.md            # doc-drift batch items #1-3 + cognitive-pattern context
  - prd.md                                      # to be extended (Initiative 6 section)
  - architecture.md                             # to be extended (Initiative 6 section + Decision C clarifying note)
  - epics.md                                    # to be extended (Initiative 6 H2 + ~7 stories)
  - implementation-artifacts/sprint-status.yaml # to be extended (Session F)
  - sprint-change-proposal-2026-05-18-init5.md  # predecessor; this SCP follows the same Initiative-N pattern
supersedes: none
superseded_by: none
predecessor_initiative: 5
---

# Sprint Change Proposal — Initiative 6 (Post-Cutover Default-Deny Auth Posture)

## Section 1 — Issue Summary

### 1.1 Problem statement

Initiative 5 structurally closed on 2026-05-20 with 27/27 stories shipped, NFR5-SEC-1 HARD GATE PASS (0/3 accepted-rationale Mediums), and a verified rollback drill. The cutover (Story 10.3, sibling configs commit `5a95b23`) removed the nginx server-level IP allowlist that had been load-bearing for `/api/*` read-side auth gating.

Within ~5 hours of Init 5 retro close-out (`2429157`, 2026-05-20 ~17:25 UTC), the operator surfaced anonymous external access to `/api/categories` on `https://3d.ezop.ddns.net` returning the full private category tree + per-category model counts. Verified pre-fix: all six SoT read endpoints in `apps/api/app/modules/sot/router.py` (`/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, `/api/models/{id}/files/{file_id}/content`) were `Public, unauthenticated` in code; nginx was the actual gate; the cutover removed that gate; the application-level auth contract had never been implemented despite explicit architecture intent.

A hot-fix attempt landed at `64447ff` (2026-05-20T19:10Z) adding `current_member_or_admin` Depends on all six SoT GET handlers + wrapping `/catalog/*` frontend routes in `<AuthGate>`. Codex review (`codex-review-64447ff-2026-05-20.md`) caught 2×P1 + 1×P2 regressions:

- **P1 (share-asset):** `apps/api/app/modules/share/router.py:55,59,70` emits URLs pointing at `/api/models/{m}/files/{f}/content` for anonymous share-recipients fetching thumbnails + STL. The hot-fix gated those URLs → share links broken externally.
- **P1 (agent service-account):** `apps/api/scripts/hydrate_local_tree.py:179,283,324` pre-flights `/api/categories` + `/api/models?external_url=...` for agent-runbook ingestion. `current_member_or_admin` rejects the `agent` role → NFR5-INT-1 (agent integration contract) violated.
- **P2 (AuthGate `next` query param):** `apps/web/src/shell/AuthGate.tsx:8,13` destructures `search` from TanStack Router's `useLocation()`. TanStack `ParsedLocation.search` is a parsed **object** (`TSearchObj`), not a string; the template-literal `` `?${search}` `` coerces the object to `"[object Object]"`. Visible to anon users on `/catalog` as `next=%5Bobject%20Object%5D` in the redirect URL + JS console error "can't convert s to string".

The hot-fix was reverted at `be43b92` (2026-05-20 ~22:00 UTC). To restore the external-anonymous → 403 property without breaking share recipients or agent ingestion, the operator temporarily re-locked the edge via nginx IP allowlist on the sibling configs repo (`~/repos/configs/` commit `70cb5ba` "feat(nginx): temporary edge re-lock for 3d-portal post-cutover rollback"), deployed to `.180`. This is a tactical recovery, not a strategic posture — the cutover's primary product property ("portal authenticates itself, no perimeter trust") is now suspended pending this initiative.

### 1.2 Issue categorization

Per CC checklist §1.2: **Misunderstanding of original requirements** (drift between architecture.md Decision C explicit per-route table and shipped sot/router.py code intent) **+ failed approach requiring different solution** (hot-fix 64447ff added wrong dependency on wrong endpoint without re-deriving the affected flow contract). This is NOT a new requirement from stakeholders — the architectural intent already specified `current_user` for `/api/sot/*` and `/api/catalog/*` (architecture.md:1489-1490); what was missing is enforcement (drift between table and code) + endpoint-contract redesign for share-asset (anonymous bypass via share-token scope) + frontend topology shift (shell-level AuthGate vs per-route).

### 1.3 Evidence

All binding inputs are confirmed present, loaded, and cross-referenced:

- **Supplemental finding:** `_bmad-output/implementation-artifacts/security-audit-2026-05-20.md` § "Supplemental finding — High-002" (18.5 KB). Status: **open after revert** — original verdict `2026-05-20T19:11Z post-64447ff` was INVALIDATED by `be43b92`.
- **Codex P1+P2 review:** `_bmad-output/implementation-artifacts/codex-review-64447ff-2026-05-20.md` (1 MB transcript). The 2×P1 + 1×P2 findings are verbatim inputs to the new design.
- **Init 5 retro:** `_bmad-output/implementation-artifacts/initiative-5-retro-2026-05-20.md` § "Doc-drift batch" items #1-3 reference this gap pre-discovery. This SCP folds those items into Initiative 6's scope.
- **PRD § Initiative 5** lines 1065-1258 — FR5-MEMBER-1 verbatim "`member` role grants browse" + the implied authentication baseline.
- **Architecture.md § Initiative 5** lines 1399-1735 — Decision C per-route table (1489-1490 specifies `current_user` for `/api/sot/*` + `/api/catalog/*`); Decision K nginx cutover diff (1666-1709) presumed app-level auth was in place.
- **Code-level state (verified 2026-05-20 post-revert):**
  - `apps/api/app/modules/sot/router.py:38-100` — six GET endpoints, NO `Depends` for auth on any of them.
  - `apps/api/app/modules/share/router.py:55,59,70` — anonymous share-resolve emits `/api/models/{m}/files/{f}/content` URLs.
  - `apps/web/src/shell/AppShell.tsx:10-12` — already has `/share/*` shell bypass; lacks shell-level AuthGate for everything else.
  - `apps/web/src/shell/AuthGate.tsx:8,13` — confirmed P2 bug (object coercion in template literal).
- **TanStack Router source-of-truth:** `apps/web/node_modules/@tanstack/router-core/src/location.ts:3-52` confirms `ParsedLocation.search: TSearchObj` (object) and `searchStr: string` (string with leading `?`). The fix surface is one-line.
- **Commits:** `64447ff` (hot-fix), `be43b92` (revert), `cb610f3` (supplemental audit note), `2429157` (Init 5 retro), `7e5aea0` (Init 5 cutover closing commit), and sibling configs `70cb5ba` (temporary IP allowlist restoration).

Halt-conditions per CC checklist §1: trigger clear ✓, evidence sufficient ✓.

### 1.4 Production state at SCP creation time (2026-05-20)

| Surface | Before Init 5 cutover | Post-cutover (Story 10.3) | Hot-fix 64447ff | Post-revert + sibling 70cb5ba (current) | Initiative 6 target |
|---|---|---|---|---|---|
| External anonymous → `/api/categories` | 403 (nginx allowlist deny) | **200 (privacy regression)** | 401 | 403 (sibling re-lock) | **401 (portal auth-gated, nginx allowlist GONE again)** |
| LAN anonymous → `/api/categories` | 200 | 200 | 401 | 200 (sibling re-lock still allows LAN) | **401 (LAN no longer carries trust)** |
| External anonymous → `/share/{token}` resolve | 200 (anonymous nginx bypass) | 200 | 200 | 200 (sibling preserves /share bypass) | **200 (unchanged contract)** |
| External anonymous → share-resolve emitted asset URL `/api/models/{m}/files/{f}/content` | 200 (nginx bypass via `/share/*` location override that doesn't quite cover `/api/models/...`; actually broken pre-cutover too, masked by LAN testing only) | 200 (briefly worked anonymously across all routes) | **401 (P1 regression)** | 200 only on LAN; **broken externally (accepted trade-off)** | **200 via NEW share-scoped asset endpoint** |
| Agent service-account → `/api/categories` (LAN, cookie-authenticated) | 200 | 200 | **403 (current_member_or_admin blocks agent — P1)** | 200 | **200 (current_user accepts agent)** |
| Admin/member login → catalog browse (External, cookie-authenticated) | 200 (post-Init-5 design) | 200 | 200 | 200 | **200 (unchanged contract — what Init 5 promised)** |

Externally, share recipients are currently broken (the operator-accepted trade-off pending this SCP's ship). The sibling configs IP allowlist (`70cb5ba`) stays in place until Initiative 6 ships final audit + drill, then is reverted (last story of Initiative 6).

---

## Section 2 — Impact Analysis

### 2.1 Epic impact

| Epic state | Count | Detail |
|---|---|---|
| Init 5 epics SHIPPED + retro-closed | 5 | E6, E7, E8, E9, E10 — all `done`, retro complete `2429157`. **No retroactive modification** — Init 5 audit trail stays intact. |
| To add | 1 initiative × ~7 stories (1 epic — see §3.3 decision) | Initiative 6: post-cutover default-deny auth. Single epic E11 with 7 stories (no sub-epic split). |
| To modify | 0 | Init 5 retro-closure is a structural milestone — modifying its scope retroactively would invalidate the NFR5-SEC-1 HARD GATE PASS audit trail. |
| To remove | 0 | None. |

### 2.2 Story impact

- **Init 5 stories shipped:** untouched. Story 9.2 (six-scenario audit) and Story 10.3 (atomic cutover) get retroactive annotations in this SCP's retrospective section as **scope-incomplete-not-defective** — they passed their stated acceptance criteria; the criteria themselves were incomplete (scope §6.5).
- **New stories (Initiative 6, E11.1–E11.7):** see §4.3 for full text. Sequencing: 11.1 (backend default-deny gating + agent contract) → 11.2 (share-asset endpoint) → 11.3 (frontend shell-level AuthGate + AuthGate P2 fix) → 11.4 (route enforcement gate — pytest enumeration) → 11.5 (audit re-run, six-scenario matrix extension covering ALL `/api/*`) → 11.6 (cutover-smoke automation: public-IP probe from non-LAN host) → 11.7 (sibling nginx allowlist rollback + final operations.md cutover-date update).

### 2.3 Artifact conflicts (CC checklist §3)

| Artifact | Conflict | Resolution |
|---|---|---|
| `prd.md` § Initiative 5 lines 1180-1182 (FR5-MEMBER-1 + FR5-MEMBER-2) | "`member` role grants browse" wording implies member-minimum requirement; architecture explicitly intended `current_user` (any authenticated incl. agent) | Add clarifying note in PRD FR5-MEMBER-1 + add Initiative 6 FRs for default-deny posture, signed-share-asset, route enforcement gate, shell-level AuthGate. NOT a contract change — implementation drift correction. |
| `architecture.md` § Initiative 5 Decision C lines 1458-1493 (per-route allowlist table) | Table correctly specifies `current_user` for `/api/sot/*` + `/api/catalog/*` but code shipped without that dependency. Drift was invisible because nginx perimeter masked it. | Add clarifying note in Decision C that the table is **default-deny + explicit anonymous-allow allowlist** (vs ambiguous "per-route allowlist"). Add Initiative 6 Decisions M–O (numbering local to Init 6 per §3.4 H2-append convention): default-deny route enforcement mechanism, share-scoped asset endpoint design, frontend shell-level AuthGate topology. |
| `architecture.md` § Initiative 5 Decision K lines 1662-1735 (nginx cutover diff) | Decision K assumes app-level auth was in place pre-cutover; that assumption was implicit and unverified. | Add retrospective annotation; no Decision K text changes (the diff itself was correct given the audit's signed-off premises). |
| `epics.md` § Initiative 5 lines 1445-1991 (Init 5 epic + story list) | No conflict; retro-closed. | Append `## Initiative 6` H2 with one epic + 7 stories. Project-global epic numbering continues at E11 per `project-context.md` § "Workflow source of truth". |
| `apps/api/app/modules/sot/router.py:38-100` | All 6 GET endpoints currently `Public, unauthenticated`; need `current_user` | Story 11.1 implements Decision C's stated intent (use `current_user`, not `current_member_or_admin`). |
| `apps/api/app/modules/share/router.py:55,59,70` | Emits `/api/models/{m}/files/{f}/content` URLs anonymous share-recipients can't access post-default-deny | Story 11.2 implements new share-scoped asset endpoint + refactors share-router to emit share-scoped URLs. |
| `apps/web/src/shell/AuthGate.tsx:8,13` | `useLocation().search` is object, not string; produces `next=[object Object]` | Story 11.3 fixes (use `searchStr` from `ParsedLocation`). |
| `apps/web/src/shell/AppShell.tsx:10-12` | Has share bypass but no shell-level AuthGate; module rail + topbar render for anonymous users | Story 11.3 hoists AuthGate to shell level + adds explicit public-path allowlist. |
| `apps/api/tests/test_*.py` | No mechanical route-enumeration test exists; drift undetectable in CI | Story 11.4 adds pytest enumeration of FastAPI routes + assertion that each `/api/*` route has either an auth Depends OR appears in explicit `_PUBLIC_ROUTES` allowlist. |
| `infra/scripts/audit-six-scenarios.sh` | Scenario 4 IDOR scope = `/api/admin/*` only | Story 11.5 extends Scenario 4 to enumerate ALL `/api/*` routes (read + mutating). |
| `infra/scripts/cutover-smoke.sh` | No external-host probe; AC5 of Story 10.3 deferred to operator manual verification | Story 11.6 automates external-host probe (e.g. via curl from a non-LAN host or CI runner). |
| `~/repos/configs/nginx/3d.ezop.ddns.net.conf` (sibling) | Currently has temporary IP allowlist (`70cb5ba`); needs final revert | Story 11.7 reverts allowlist + records cutover-date update in `docs/operations.md`. |
| `docs/operations.md` § "Public read" lines 353-355 | Documents `/api/categories`, `/api/tags`, etc. as "Public read" — stale post-Init 5 design + Init 6 default-deny | Story 11.7 updates wording to reflect new contract. |

### 2.4 Technical impact

**Backend (apps/api):**
- New file: `apps/api/app/modules/share/asset_router.py` (or extend existing `share/router.py`) — share-scoped asset endpoint per Initiative 6 Decision N (see §3.3).
- Modify: `apps/api/app/modules/sot/router.py` — add `current_user` Depends to all 6 GET endpoints.
- Modify: `apps/api/app/modules/share/router.py` — emit share-scoped asset URLs instead of `/api/models/...` URLs.
- New file: `apps/api/tests/test_route_enforcement_gate.py` — mechanical enumeration test.
- New `_PUBLIC_ROUTES` constant in `apps/api/app/main.py` (or `app/core/auth/dependencies.py`) — explicit allowlist enumerated.
- Migration: no Alembic migration needed (no schema changes).

**Frontend (apps/web):**
- Modify: `apps/web/src/shell/AppShell.tsx` — hoist AuthGate logic to shell level + explicit public-path list.
- Modify: `apps/web/src/shell/AuthGate.tsx` — fix `searchStr` usage (P2 fix).
- Remove: per-route `<AuthGate>` wrappers (if any exist post-Init 5 from Story 8.2 admin panel routes; these become redundant once shell-level gate is in place).
- New module: `apps/web/src/shell/LoginRedirect.tsx` (or repurpose existing login route) — what anonymous users see at shell-level when they hit a protected path. Likely just a TanStack Router redirect to `/login?next=...`.

**Infra:**
- Modify: `infra/scripts/audit-six-scenarios.sh` — Scenario 4 expansion.
- Modify (or new): `infra/scripts/cutover-smoke.sh` — external-host probe.
- Sibling repo (`~/repos/configs/`): final revert of `70cb5ba` (temporary IP allowlist) — covered by Story 11.7.

**Docs:**
- `docs/operations.md` — update Public Read paragraph.
- `AGENTS.md` (vendor-neutral) — add line about route enforcement gate as part of audit/security discipline.
- `_bmad-output/project-context.md` — incorporates route enforcement test as a new project-context rule (post-Story-11.4 if applicable).

**No worker (workers/render/) changes. No 3D viewer changes. No DB schema changes.**

---

## Section 3 — Recommended Approach (CC checklist §4)

### 3.1 Path forward evaluation

| Option | Viable? | Effort | Risk | Rationale |
|---|---|---|---|---|
| **Option 1 — Direct Adjustment** (new Initiative 6, single epic E11 with 7 stories) | **Yes** | Medium (3-5 days autonomous) | Medium (security-boundary work; codex review pre-merge) | Implements what Decision C already specified; adds enforcement gate + endpoint redesign for share; no Init 5 rollback needed. |
| Option 2 — Rollback (revert Init 5 cutover entirely) | **No** | High | High | Discards 27 stories of shipped work; doesn't address the root cause (drift between intent and code); operator already restored partial trust via sibling 70cb5ba allowlist (which is a localized rollback, not strategic). |
| Option 3 — PRD MVP Review (re-scope Init 5) | **No** | High | High | MVP scope was correct; the issue is implementation drift + endpoint redesign for share, neither of which changes the MVP definition. |
| Hybrid — Option 1 + targeted PRD reword | Partially overlaps Option 1 | — | — | Folded into Option 1 (the PRD reword is one of the §4.1 edits). Not a distinct option. |

### 3.2 Selected approach: **Option 1 — Direct Adjustment via Initiative 6**

**Justification:**

1. **Architecture is mostly right; implementation drifted.** Decision C linia 1489-1490 explicitly specifies `current_user` for `/api/sot/*` + `/api/catalog/*`. The fix is to **implement what's written**, not rewrite. This makes Option 1 the smallest deviation from the existing planning chain.
2. **Hot-fix 64447ff failed precisely because it skipped re-derivation.** The cognitive pattern was "fix the visible leak (anonymous external read) without re-deriving the auth contract for every affected flow (share-recipient, agent service-account)". Initiative 6 corrects this by **explicit enumeration**: route enforcement gate (Story 11.4) makes every `/api/*` route's auth posture mechanical-detectable; share-scoped asset endpoint (Story 11.2) makes the anonymous-bypass surface explicit at the URL level (`/api/share/...` prefix).
3. **Sibling 70cb5ba is a tactical recovery, not a strategic posture.** The IP allowlist must come off when Initiative 6 ships — it has been the proximate cause of one full initiative (Init 5 entire scope was about getting rid of it) and reinstating it permanently would erase that work. Initiative 6 closes with Story 11.7 reverting the temporary allowlist.
4. **Operator-aligned non-negotiables (briefing 2026-05-20):** all `/api/*` default-deny; `/api/health` moved to LAN-only nginx listener; no anonymous `/api/telemetry`. These are inputs to Initiative 6, not subjects of dialog (operator-confirmed twice, including the follow-up "best practice" exchange where I recommended docker healthcheck + container-level health and operator confirmed).
5. **BMAD vanilla-first discipline:** any post-ship scope change routes through `bmad-correct-course` (this skill), not direct edits. Initiative 6 IS a post-ship scope change. Skipping this CC would be the same anti-pattern Init 5 retro flagged in `feedback_default_to_bmad_workflow.md`.

### 3.3 Locked decisions (Initiative 6 scope inputs)

Operator-confirmed (briefing 2026-05-20 ~22:30 + best-practice follow-up):

- **D-LOCK-1:** Whole portal default-deny on `/api/*` is non-negotiable.
- **D-LOCK-2:** Anonymous-allowed surfaces are EXACTLY: `/api/auth/*` (login / refresh / register?token= / 2fa enrollment-pre-cookie / password-reset consume) + `/api/share/{token}` (resolve) + share-scoped asset endpoint per §3.4 Decision N + `/api/csrf-token` if it exists (TBD during Story 11.1). All other `/api/*` routes require authenticated user.
- **D-LOCK-3:** `/api/health` is NOT part of public `/api/*` surface post-Initiative 6. Health monitoring moves to `127.0.0.1` LAN listener via nginx OR docker healthcheck directly. `apps/api/app/main.py` may still expose `/api/health` for LAN reachability checks; nginx must NOT proxy it through external `3d.ezop.ddns.net` location. (Implementation decision local to Story 11.7 nginx cleanup.)
- **D-LOCK-4:** NO anonymous `/api/telemetry` endpoint. Observability for anonymous user errors (login failures, JS crashes) flows through three orthogonal channels: backend access logs + structlog (`auth.login.fail` events), rate-limit middleware (per-IP `auth.login` counters from Init 5 Story 6.6), and Glitchtip direct frontend reporting (no portal proxy).
- **D-LOCK-5:** Frontend AuthGate at SHELL level, not per-route. Anonymous user sees ONLY login surface (no ModuleRail, no TopBar, no "Coming soon" stubs).

Operator-delegated to ITCM (per `feedback_itcm_autonomous_mode.md` autonomous mode):

- All Initiative 6 procedural calls (skill chain, mode selection, Codex grilling cadence, edit batching).
- All within-scope technical trade-offs unless they're load-bearing security boundary decisions (then Codex peer-grilling per Init 5 NFR5-SEC-2 pattern).

### 3.4 Trade-off resolution (ITCM-owned, Codex peer-grilling for load-bearing security)

Three trade-offs that operator listed as "open for Stage-3 dialog" in the SCP brief. All three resolved here per ITCM-autonomous-mode discipline; one (share-asset endpoint) gets Codex peer-grilling because it's a load-bearing security boundary decision (precedent: Init 5 NFR5-SEC-2 mandates Codex countersignature for security-boundary decisions).

#### 3.4.1 Trade-off A — Agent service-account auth contract

**Resolved without Codex grill (architecture already answered).** Architecture.md Decision C linia 1489-1490 specifies `current_user` for `/api/sot/*`. `current_user` accepts any authenticated principal: admin + member + **agent** (the `agent` role is in `_enums.py:10-13` and Init 0/2 cookie-password flow is the existing agent auth path). The hot-fix 64447ff chose `current_member_or_admin` and that's what blocked the agent — wrong dependency.

Resolution: Story 11.1 uses `current_user` (not `current_member_or_admin`) on all six SoT GET endpoints. Story 11.1 acceptance criterion includes a smoke test asserting `agent` cookie can reach `/api/categories` returning 200. No new dependency variant needed.

#### 3.4.2 Trade-off B — Share-scoped asset endpoint design (Decision N) — **CODEX PEER-GRILLING APPLIED**

This is a load-bearing security boundary. Four candidate designs evaluated; Codex `exec` invoked 2026-05-20 ~22:50 with adversarial-review prompt covering all four options + my recommended (a) path-segment token. Codex verdict: **my recommendation (a) is directionally right but RAW (a) is broken; ship Codex's "option (e) — hardened (a)" instead.**

**Codex verdict verbatim (one-line summary):** "Your recommendation is directionally right, but raw (a) still leaks bearer tokens in logs and over-grants same-model files unless you harden the contract."

**Six hardenings Codex flagged on raw (a) — ALL adopted into Decision N:**

1. **Over-granting same-model files.** `ModelFileKind` enum (`apps/api/app/core/db/models/_enums.py:34-39`) has 5 values: `stl, image, print, source, archive_3mf`. Share-resolve currently surfaces only `image | print | stl` (`share/router.py:52,65`). A scope-check that says "file belongs to model" would expose `source` (e.g. raw .blend) + `archive_3mf` which were NEVER intended for share recipients. **Fix:** scope query MUST include `ModelFile.kind.in_([image, print, stl])` filter, OR restrict tighter to the exact asset set emitted by `/api/share/{token}` resolve.

2. **Path-bearer token leaks to logs.** Current redaction (`apps/api/app/core/logging.py:14`) regex `\btoken=[^&\s"']+` matches `token=<value>` in query strings only — NOT `/api/share/<token>/...` path segments. Token-in-path will leak to nginx access logs, OTel span attributes, app `_LOG.info(...)` calls, Sentry/GlitchTip error events, browser history. **Fix:** extend redaction with second regex matching `/share/<bearer>/...` (and `/api/share/<bearer>/...`) path patterns; tested with negative cases in Story 11.2.

3. **Cache-Control revoke bypass.** Existing content endpoint (`sot/router.py:212`) returns `Cache-Control: private, max-age=300`. Share-asset response inheriting that header means revoked tokens can serve cached content for up to 300s post-revoke from intermediate caches / browser cache. **Fix:** share-asset response uses `Cache-Control: no-store` (or at minimum `max-age=0, must-revalidate`).

4. **ETag/304 short-circuit hazard.** Existing content endpoint short-circuits on ETag-match with 304 BEFORE running any auth/scope check. Order matters: share-asset MUST run token-resolve + scope-check BEFORE checking ETag, or revoked tokens 304-pass cached responses past revoke. **Fix:** scope-check first, ETag second.

5. **Audit emits clear token.** Existing share-create audit (`share/admin_router.py:42`) stores clear token in `after` field. Replicating that pattern for share-asset fetch would multiply the token-leak surface. **Fix:** share-asset audit row uses `target_token_hash = sha256(token).hexdigest()`, never clear token.

6. **Repo drift in my own SCP write-up.** Codex caught two factual errors I made in §1.4 + §3.4.2 above pre-Codex draft: (a) token entropy is `secrets.token_urlsafe(24)` (24 bytes / 192 bits / 32-char output) per `share/service.py:22`, NOT 32 bytes / 256 bits / 43-char as I had written; (b) **there is NO `share_tokens` DB table** — only Redis at `share:token:{token}` + audit-log emission. My claim that revoke "inherits from existing share-token row update" was incorrect; revoke is Redis DEL + audit-log emission only. **Fix:** drift corrections inlined here; Story 11.2 acceptance includes verification that share-service token entropy assumption matches reality (24 bytes is sufficient for friends-and-family scope per Init 0 baseline, NOT widened to 32 bytes — that's a separate decision out of Initiative 6 scope).

**Final design — hardened (a):**

```
GET /api/share/{token}/files/{file_id}/content?download=0
```

(Path shape stays `/files/` for consistency with `share/router.py:55,59,70` URL emission convention; Codex proposed `/assets/` in option (e) but the rename has no security relevance and would create a transient URL-shape inconsistency between resolve emission and consumption.)

Implementation guarantees (binding for Story 11.2):

```python
# apps/api/app/modules/share/router.py — Initiative 6 Story 11.2
@router.get("/{token}/files/{file_id}/content")
async def get_share_asset(
    token: str,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
) -> Response:
    # 1. Token resolve — Redis primary; fail-closed if Redis unreachable
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        # Uniform 404 — do NOT distinguish "invalid token" / "expired" / "revoked" externally
        # (avoid timing-distinguishable response that leaks token-state oracle)
        raise HTTPException(404, "Share asset not found")

    # 2. Scope-check BEFORE ETag — runs against DB
    file_row = session.exec(
        select(ModelFile)
        .join(Model, Model.id == ModelFile.model_id)
        .where(
            ModelFile.id == file_id,
            ModelFile.model_id == record.model_id,
            ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print, ModelFileKind.stl]),
            Model.deleted_at.is_(None),  # soft-deleted models return 404
        )
    ).first()
    if file_row is None:
        # Uniform 404 — do NOT distinguish "wrong model" / "wrong kind" / "missing file" externally
        raise HTTPException(404, "Share asset not found")

    # 3. Audit emission BEFORE serving (audit captures the access intent regardless of disk outcome)
    record_event(
        session,
        action="share.asset.fetched",
        actor_user_id=None,
        target_token_hash=hashlib.sha256(token.encode()).hexdigest(),  # NEVER clear token
        target_model_id=record.model_id,
        target_file_id=file_id,
        target_file_kind=file_row.kind.value,
        ip=request.client.host if request.client else None,
    )

    # 4. Serve content with Cache-Control: no-store (prevents post-revoke cached serving)
    return _serve_file_content(
        file_row,
        download=download,
        cache_control="no-store",  # override default "private, max-age=300"
    )
```

(Path-traversal protection inherits from existing `_serve_file_content` helper — no new disk-path code.)

**Rejected alternatives (Codex verdicts verbatim):**

- (b) Query-param `share_token=` on `/api/models/...` — *"recreates the dangerous dual-mode endpoint... exactly the kind of contract blending that caused 64447ff."*
- (c) HMAC-signed URLs — *"poor. It still hangs anonymous access off `/api/models/.../content`, so the route's public surface is not obvious."*
- (d) Per-asset Redis signature — *"mixed. `/api/asset/*` is visibly public only if the allowlist and docs say so. It is less self-explanatory than `/api/share/{token}/files/...`."*

**Cognitive pattern property (Codex's evaluation):** *"A separate `/api/share/*` route makes the anonymous contract visible and would have prevented the exact 64447ff break where share assets depended on `/api/models/.../content`. It only catches the failure if tests assert that share-resolve emits share-scoped URLs and that those URLs fetch anonymously. Path shape is a cue, not a proof."* — adopted into Story 11.2 acceptance criteria explicit assertion.

**Full Codex transcript:** `/tmp/claude-1000/-home-ezop-repos-3d-portal/5d6e0d63-f070-483d-be33-eaa993eaaebf/tasks/b6iijlo4m.output` (saved at SCP creation time; will be copied to `_bmad-output/implementation-artifacts/codex-design-grill-share-asset-2026-05-20.md` at SCP approval time per NFR5-SEC-2 mirror).

#### 3.4.3 Trade-off C — Architecture.md Decision C reword strategy

**Resolved without Codex grill (procedural choice, low security stakes).** Two paths considered:

- **Edit-in-place:** add clarifying note to Decision C explaining the table is default-deny + explicit anonymous-allow; do NOT change the table contents (they're already correct).
- **New Decision superseding C:** preserves git/doc history trail; but Decision C wording in the table is correct, so supersession would be misleading (it's not actually superseded, just clarified).

**Choice:** edit-in-place + add Initiative 6 Decisions M, N, O (numbering local to Init 6 per `## Initiative 6` H2-append convention from `feedback_vanilla_bmad_first.md`):
- **Decision M (Init 6):** Default-deny route enforcement mechanism — pytest enumeration + `_PUBLIC_ROUTES` allowlist constant + CI gate.
- **Decision N (Init 6):** Share-scoped asset endpoint contract — option (a) per §3.4.2, pending Codex verdict.
- **Decision O (Init 6):** Frontend shell-level AuthGate topology — single source of auth state in AppShell, public-path allowlist, removal of per-route wrappers.

Decision C clarifying note: appended in same H4 block per `feedback_vanilla_bmad_first.md` H2-append convention, with `<!-- Initiative 6 clarification 2026-05-20 -->` marker.

#### 3.4.4 Trade-off D (additional, ITCM-surfaced) — Initiative 6 scope boundary

Operator brief listed "where to draw line between 'ship auth-gate redesign' and 'fold in audit re-run + nginx rollback' (one initiative or two)". Resolved: **one initiative, single epic**. Reasoning:

- The audit re-run (Story 11.5) is GATE for the nginx rollback (Story 11.7); separating them into two initiatives forces a multi-initiative coordination overhead with no clear product value.
- Init 5 was 5 epics × 27 stories — Initiative 6 at 7 stories is below the threshold where single-epic is unwieldy.
- Operator-confirmed "one initiative" scope when given two options for non-negotiable framing (D-LOCK-1 covers full posture).

**Naming:** Initiative 6 has a single epic E11 — "Post-Cutover Default-Deny Auth Posture" — with 7 stories (11.1–11.7).

---

## Section 4 — Detailed Change Proposals

Edits below are presented per artifact. Format: **artifact path** → OLD (verbatim or anchor) → NEW → rationale. Mode is **batch-presented** (operator-pragmatic variant of BMAD Incremental — full draft surfaced once, operator feedback consolidated).

### 4.1 PRD edits (`_bmad-output/planning-artifacts/prd.md`)

#### 4.1.1 PRD edit — FR5-MEMBER-1 clarifying note (lines 1180-1182)

**OLD (verbatim, line 1180):**

> - **FR5-MEMBER-1: `member` role grants browse + viewer + share-link generation.** Permitted: read-only `/api/catalog/*` and `/api/sot/*` GET endpoints; the 3D viewer routes; `POST /api/share/*` to mint share tokens. The share-router auth dependency expands from `current_admin` to `current_member_or_admin` (FR5-MEMBER-2 codifies the new dependency name). **Verifiable:** a member-authenticated `POST /api/share/` returns 201 with a fresh share token; the same request as an unauthenticated user returns 401.

**NEW (verbatim replacement, lines 1180-1183):**

> - **FR5-MEMBER-1: `member` role is the third principal that browses authenticated catalog content; share-router minting expands from admin-only to member-or-admin.** Catalog browse (`/api/catalog/*`, `/api/sot/*` GET) is available to any authenticated principal (admin, member, agent) per architecture.md § Initiative 5 Decision C per-route allowlist table — **`member` is an addition to the eligible set, not a new minimum**. The share-router minting endpoint (`POST /api/admin/share`) expands its dependency from `current_admin` to `current_member_or_admin` (FR5-MEMBER-2 codifies the new dependency name). **Verifiable:** a member-authenticated `POST /api/admin/share` returns 201 with a fresh share token; the same request as an unauthenticated user returns 401; an agent-authenticated `GET /api/categories` returns 200 (NFR5-INT-1 preserved). <!-- Initiative 6 clarification 2026-05-20: original wording "`member` role grants browse" was ambiguous and read as member-minimum; the architecture intent (Decision C table) was always "any authenticated user". Implementation drift in sot/router.py shipping `Public, unauthenticated` was masked by nginx allowlist pre-cutover (see Initiative 6 retro). -->

**Rationale:** removes the ambiguity that contributed to the hot-fix 64447ff misreading; makes explicit that agent role is in scope; in-line comment makes the drift correction discoverable for future agents.

#### 4.1.2 PRD edit — append new section `## Initiative 6` after Init 5 closing (line ~1259)

**OLD:** (Init 5 ends at line 1257 with Cross-references; nothing follows in PRD yet.)

**NEW (append H2 block after line 1258):**

```markdown
## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md` (status `draft` until operator approval).
Predecessor Initiative 5 closed `7e5aea0` (cutover) + `2429157` (retro). Initiative 6 is **bug-fix-scope-expansion** triggered by Story 9.2 audit scope miss (read-side `/api/*` not probed) + Story 10.3 cutover removing the nginx allowlist that had been load-bearing for app-level auth gating. Source artifacts: `security-audit-2026-05-20.md` § Supplemental High-002 + `codex-review-64447ff-2026-05-20.md` (P1×2 + P2) + Init 5 retro doc-drift items #1-3.

### Overview

Initiative 5 cutover (Story 10.3, sibling configs `5a95b23`) removed the nginx IP allowlist. The architecture intent (Decision C linia 1489-1490) had always specified `current_user` for `/api/sot/*` + `/api/catalog/*`, but implementation in `apps/api/app/modules/sot/router.py` had shipped without that dependency — drift masked by the nginx perimeter. Post-cutover, anonymous external read access to the operator's private catalog metadata was a real privacy regression. Hot-fix attempt `64447ff` was reverted at `be43b92` after Codex P1×2 review caught share-recipient + agent-service-account regressions.

Initiative 6 closes the gap with a **single epic E11** of 7 stories, structured around the operator-aligned non-negotiable D-LOCK-1: all `/api/*` default-deny; explicit allowlist for `/api/auth/*` + `/api/share/{token}*` (resolve + share-scoped asset endpoint); `/api/health` moved to LAN-only. Mechanical enforcement (Story 11.4 pytest enumeration) prevents drift recurrence. Frontend shell-level AuthGate (Story 11.3) ensures anonymous users see only the login surface.

### Functional Requirements

- **FR6-AUTH-1: Default-deny posture on `/api/*` is mechanically enforced.** Every FastAPI route registered with `prefix="/api"` MUST have an explicit auth dependency (`current_user`, `current_member_or_admin`, `current_admin`, or one of the future variants) OR appear in the `_PUBLIC_ROUTES` allowlist constant in `apps/api/app/main.py`. A pytest enumeration test (`apps/api/tests/test_route_enforcement_gate.py`) asserts this property and fails CI on drift. **Verifiable:** the test runs in <1s; adding a new `/api/*` route without auth dep AND without allowlist entry fails the test with a specific error naming the route.
- **FR6-AUTH-2: Anonymous-allowed `/api/*` surface is exactly enumerated.** The `_PUBLIC_ROUTES` allowlist contains: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/register`, `/api/auth/totp/verify`, `/api/auth/password-reset/consume`, `/api/share/{token}` (resolve), `/api/share/{token}/files/{file_id}/content` (share-scoped asset), `/api/csrf-token` (if exists; TBD Story 11.1). Any addition to this list requires a Sprint Change Proposal — it cannot be added in a single story. **Verifiable:** the allowlist constant has exactly these entries and matches the production FastAPI route table.
- **FR6-SHARE-1: Anonymous share-recipients access thumbnails + STL binary via share-scoped asset endpoint.** New endpoint `GET /api/share/{token}/files/{file_id}/content` validates token via existing `ShareService.resolve(token)`, checks `file_id` belongs to the resolved model's files, and serves binary content. Anonymous-allowed (no auth Depends). Share-router refactored to emit `/api/share/{token}/files/{fid}/content` URLs instead of `/api/models/{m}/files/{f}/content`. **Verifiable:** anonymous `GET /api/share/{valid-token}/files/{valid-file-id}/content` returns 200 with the file body; same request with mismatched `file_id` (file belongs to a different model) returns 404; same request with revoked token returns 410.
- **FR6-SHELL-1: Frontend AuthGate operates at shell level; anonymous users see only the login surface.** `AppShell.tsx` evaluates authentication state ONCE at shell mount. If `pathname` is in `_PUBLIC_PATHS` (login, register, reset-password, share, share-recipient consumption) → render bare children. Else if authenticated → render full shell (ModuleRail + TopBar + children). Else → redirect to `/login?next=<currentPath>`. Module rail, top bar, and "Coming soon" stubs (Kolejka, Filamenty, etc.) DO NOT render for anonymous users. **Verifiable:** anonymous user navigating to `/`, `/catalog`, or any module slot is redirected to `/login?next=...`; module rail is absent from DOM at the redirect target.
- **FR6-SHELL-2: AuthGate `next` query parameter uses `searchStr` from TanStack ParsedLocation.** `AppShell.tsx` (or remaining shell-level AuthGate logic) reads `searchStr` (string with leading `?`) from `useLocation()`, NOT the parsed `search` object. The `next` redirect URL preserves the original search string. **Verifiable:** anonymous user at `/catalog?category_id=xyz` is redirected to `/login?next=%2Fcatalog%3Fcategory_id%3Dxyz` (URL-encoded original path + searchStr); no `[object Object]` artifacts.
- **FR6-AGENT-1: Agent service-account ingestion preserved.** `apps/api/scripts/hydrate_local_tree.py` continues to pre-flight `/api/categories` + `/api/models?external_url=...` using its existing cookie auth flow (Init 2 baseline). Story 11.1 uses `current_user` (not `current_member_or_admin`) on SoT GET endpoints, which accepts the `agent` role. **Verifiable:** scripted agent login + `GET /api/categories` returns 200; the agent runbook flow end-to-end completes without HTTP 403 on any SoT endpoint.
- **FR6-AUDIT-RERUN-1: Six-scenario audit Scenario 4 (IDOR) target list expands to ALL `/api/*` endpoints.** `infra/scripts/audit-six-scenarios.sh` Scenario 4 enumerates the live FastAPI route table (via `/api/openapi.json` or equivalent), iterates each route as anonymous + as `member`-authenticated, asserts expected response codes (anonymous → 401 except `_PUBLIC_ROUTES`; member → 200/201/403 per route's posture). **Verifiable:** Scenario 4 output includes per-route status; any `/api/*` route returning 200 anonymously that is not in `_PUBLIC_ROUTES` fails the scenario.
- **FR6-CUTOVER-PROBE-1: Cutover-smoke matrix includes automated external-host probe.** `infra/scripts/cutover-smoke.sh` extends with a fifth scenario calling `curl -fsS -o /dev/null -w "%{http_code}" https://3d.ezop.ddns.net/api/categories` from a non-LAN source (CI runner, public VPS, or operator's mobile data network). Expected: 401. **Verifiable:** scenario fails the smoke run if external host returns 200.

### Non-Functional Requirements

- **NFR6-SEC-1: Initiative 6 inherits Init 5 NFR5-SEC-1 audit gate condition.** Story 11.5 audit re-run gate-condition: zero open Critical/High findings; ≤3 accepted-rationale Mediums; 4th forces auto-fail. This is a re-execution of the six-scenario audit with extended Scenario 4, NOT a new audit format.
- **NFR6-SEC-2: Per-Medium codex review countersignature inherits from NFR5-SEC-2.** Same compensating control for single-operator self-attestation.
- **NFR6-SEC-3: Pre-merge codex review for auth-boundary stories.** Stories 11.1, 11.2, 11.3 (auth boundary contracts) get codex review BEFORE merge to main — not after — to catch the same cognitive-pattern miss that produced hot-fix 64447ff. Documented in `docs/operations.md` post-Initiative 6 close.
- **NFR6-PERF-1: Route enforcement test (`test_route_enforcement_gate.py`) runs in <1 second.** Mechanical enumeration; no DB hit; pure FastAPI route-table introspection.
- **NFR6-INT-1: NFR5-INT-1 + NFR5-INT-2 preserved exactly.** Agent service-account flow (cookie+password, `agent` role) and `/share/{token}` anonymous bypass both continue to work. Verified by Story 11.5 audit Scenario 2 (agent ingestion) + Scenario 1 (share bypass) reproducers.
- **NFR6-CROSS-REPO-1: Sibling configs rollback story spans both repos.** Story 11.7 reverts sibling `70cb5ba` (temporary IP allowlist) + records cutover-date update in `docs/operations.md` (`3d-portal`). Mirrors NFR5-CROSS-REPO-1 mechanism.
- **NFR6-OBS-1: New audit-row contract for share-scoped asset endpoint.** Each successful binary fetch via `/api/share/{token}/files/{file_id}/content` emits `share.asset.fetched` audit event with `actor=null`, `target_token={token-hash}`, `target_model_id={uuid}`, `target_file_id={uuid}`, `ip={remote-ip}`. Failed lookups (token invalid, file out-of-scope) emit `share.asset.fail` with reason field.

### Cross-references

- Predecessor: Initiative 5 (Public Registration & User Account Management) — closed 2026-05-20 `7e5aea0` + retro `2429157`.
- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md` (this file).
- Source artifacts (problem evidence): `security-audit-2026-05-20.md` § Supplemental High-002; `codex-review-64447ff-2026-05-20.md` § P1+P2 findings; `initiative-5-retro-2026-05-20.md` § Doc-drift batch items #1-3.
- Architecture extension: `architecture.md` § Initiative 6 (Decisions M, N, O) — to be authored in Session B (manual edit per CC convention).
- Epics extension: `epics.md` § Initiative 6 (single Epic E11 with 7 stories) — to be authored in Session C.
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — to be extended in Session D via `bmad-sprint-planning` (epic-11 + per-story entries status `backlog`).
```

**Rationale:** monolithic H2-append convention per `project-context.md` § "BMAD planning artifacts" + `feedback_vanilla_bmad_first.md` v2; eight FRs + seven NFRs are minimum-viable to characterize Initiative 6's contract surface; cross-references make the SCP-PRD-Architecture-Epics chain navigable.

### 4.2 Architecture edits (`_bmad-output/planning-artifacts/architecture.md`)

#### 4.2.1 Architecture edit — Decision C clarifying note (after line 1493)

**OLD:** (Decision C ends at line 1493 with the "Cascading" paragraph mentioning Story 6.5 commit `a58c4b6`.)

**NEW (append at end of Decision C's H4 block, before "Decision D"):**

```markdown
<!-- Initiative 6 clarification 2026-05-20 — added by sprint-change-proposal-2026-05-20-post-cutover-auth.md §4.2.1 -->

**Initiative 6 clarification:** The per-route table above is **default-deny + explicit anonymous-allow allowlist**, NOT "per-route allow-with-named-dependency". Read it as: every `/api/*` route requires an explicit `current_*` Depends UNLESS the route appears in the table with `anonymous` in the "After" column. This property was implicit in the original Init 5 Decision C wording and was the proximate root cause of supplemental finding High-002 (post-cutover audit miss 2026-05-20): the implementation in `apps/api/app/modules/sot/router.py` shipped without the `current_user` Depends that this table specified, and the nginx perimeter masked the drift on the live deploy.

Initiative 6 adds:

- **Decision M (Init 6):** Mechanical route enforcement test (`apps/api/tests/test_route_enforcement_gate.py`) iterating the FastAPI route table and asserting each `/api/*` route either has an auth Depends OR appears in `_PUBLIC_ROUTES` allowlist constant. This is the structural fix for the drift class.
- **Decision N (Init 6):** Share-scoped asset endpoint `GET /api/share/{token}/files/{file_id}/content` replacing the implicit anonymous bypass via nginx for `/api/models/{m}/files/{f}/content` URLs that share-resolve emitted.
- **Decision O (Init 6):** Frontend shell-level AuthGate in `AppShell.tsx` replacing per-route `<AuthGate>` wrappers; anonymous user surface is the login screen only.

See § Initiative 6 (below) for the full Decisions M–O text.
```

**Rationale:** preserves audit trail (Decision C text untouched; clarification is explicitly marked); makes the drift class discoverable for future agents reading Decision C in isolation; links forward to Initiative 6.

#### 4.2.2 Architecture edit — append new section `## Initiative 6` after Init 5 closing (after line 1775)

**OLD:** (Init 5 Cross-references end at line 1775; nothing follows.)

**NEW (append H2 block):**

```markdown
## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Brownfield bug-fix-scope-expansion on Init 0/5 auth surface. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md`. Source PRD section: `prd.md` § "Initiative 6" (FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + 7 NFRs). Single Epic E11 with 7 stories.

### Overview

Initiative 5 shipped a default-deny posture in Architecture (Decision C per-route allowlist table specified `current_user` for read-side endpoints) but implementation in `apps/api/app/modules/sot/router.py` shipped without that dependency. Pre-cutover nginx IP allowlist masked the drift. Story 10.3 cutover (sibling configs `5a95b23`) removed the allowlist, exposing the drift externally. Hot-fix `64447ff` was reverted at `be43b92` after Codex P1×2 review caught share-recipient + agent regressions.

Initiative 6 fixes the gap with mechanical enforcement: a pytest enumeration test prevents the drift class from recurring; a share-scoped asset endpoint replaces the implicit `/api/models/{m}/files/{f}/content` anonymous bypass; the frontend shell-level AuthGate makes the auth posture explicit in topology. The bulk of the technical work is enforcement and topology — the auth contract itself is already correctly specified in Init 5 Decision C.

### Decisions In-Scope (M–O)

#### Decision M — Default-deny route enforcement mechanism

- **Realizes:** FR6-AUTH-1, FR6-AUTH-2.
- **Choice:** pytest enumeration test at `apps/api/tests/test_route_enforcement_gate.py` iterates `app.routes` (FastAPI's exposed route table), filters routes with path starting `/api/`, asserts each route's endpoint callable has at least one parameter with a `Depends(current_user | current_member_or_admin | current_admin | ...)` default value OR the route path matches an entry in `_PUBLIC_ROUTES` allowlist. Allowlist is a tuple-of-strings constant in `apps/api/app/main.py` enumerated explicitly:

```python
# apps/api/app/main.py — Initiative 6 Decision M
_PUBLIC_ROUTES: tuple[str, ...] = (
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/register",
    "/api/auth/totp/verify",  # partial-auth step for users mid-2FA-login
    "/api/auth/password-reset/consume",
    "/api/share/{token}",  # resolve
    "/api/share/{token}/files/{file_id}/content",  # share-scoped asset (Decision N)
    "/api/csrf-token",  # if exists, TBD Story 11.1
)
```

The test fails CI on drift with a message like:
```
FAILED: route /api/categories has no auth Depends and is not in _PUBLIC_ROUTES
```
- **Alternatives rejected:** mypy plugin (over-engineering; route table is runtime-introspectable); FastAPI middleware introspecting Depends on first request (delays drift detection to runtime; CI doesn't catch); nginx-level route prefix list (couples app-level auth contract to edge config — exactly the failure mode of Init 5).
- **Rationale:** mechanical, runs in <1s, drift becomes a CI fail not a production privacy regression. The allowlist itself is a single source of truth for "what is anonymous".
- **Cascading:** allowlist updates require a Sprint Change Proposal (FR6-AUTH-2) — this is the procedural gate that catches "let's just add one more public route" creep.

#### Decision N — Share-scoped asset endpoint (hardened per Codex peer-grill 2026-05-20)

- **Realizes:** FR6-SHARE-1, NFR6-OBS-1.
- **Choice:** new endpoint at `GET /api/share/{token}/files/{file_id}/content` in `apps/api/app/modules/share/router.py`. Implementation contract (all six guarantees binding for Story 11.2 — Codex peer-grill 2026-05-20 surfaced and hardened each one; see SCP §3.4.2 for verbatim verdict):

```python
# apps/api/app/modules/share/router.py — Initiative 6 Story 11.2
import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlmodel import Session, select

from app.core.audit import record_event
from app.core.db.models import Model, ModelFile, ModelFileKind
from app.core.db.session import get_session
from app.modules.share.service import ShareService


@router.get("/{token}/files/{file_id}/content")
async def get_share_asset(
    token: str,
    file_id: uuid.UUID,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    download: bool = False,
) -> Response:
    # 1. Token resolve (Redis primary). Uniform 404 on miss — do NOT distinguish
    #    "invalid token" / "expired" / "revoked" externally (timing-distinguishable
    #    responses leak token-state oracle).
    service = ShareService(redis=request.app.state.redis.get())
    record = await service.resolve(token)
    if record is None:
        raise HTTPException(404, "Share asset not found")

    # 2. Scope-check BEFORE ETag handling. Scope query MUST include the kind
    #    filter — without it, share for model A would expose `source` (raw .blend)
    #    + `archive_3mf` files that share-resolve NEVER surfaced. Soft-deleted
    #    models return 404 (no leak via Model.deleted_at IS NOT NULL).
    file_row = session.exec(
        select(ModelFile)
        .join(Model, Model.id == ModelFile.model_id)
        .where(
            ModelFile.id == file_id,
            ModelFile.model_id == record.model_id,
            ModelFile.kind.in_([ModelFileKind.image, ModelFileKind.print, ModelFileKind.stl]),
            Model.deleted_at.is_(None),
        )
    ).first()
    if file_row is None:
        # Uniform 404 — wrong model / wrong kind / missing file / soft-deleted model
        # all produce the same response shape (no IDOR enumeration leak).
        raise HTTPException(404, "Share asset not found")

    # 3. Audit emission BEFORE serving. Captures access intent regardless of disk
    #    outcome. token_hash = sha256(token), NEVER clear token.
    record_event(
        session,
        action="share.asset.fetched",
        actor_user_id=None,
        target_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        target_model_id=record.model_id,
        target_file_id=file_id,
        target_file_kind=file_row.kind.value,
        ip=request.client.host if request.client else None,
    )

    # 4. Serve content with Cache-Control: no-store (override default
    #    "private, max-age=300" from sot/router.py:212; prevents revoked tokens
    #    from serving cached content for up to 300s post-revoke).
    return _serve_file_content(
        file_row,
        download=download,
        cache_control="no-store",
    )
```

`share-router.py` refactor — share-resolve handler emits share-scoped URLs:
- Line 55: `images = [f"/api/share/{token}/files/{fid}/content" for fid in image_files]`
- Line 59: `thumbnail_url = f"/api/share/{token}/files/{model.thumbnail_file_id}/content"`
- Line 70: `stl_url = f"/api/share/{token}/files/{stl_row}/content?download=1"`

`apps/api/app/core/logging.py` MUST extend token redaction regex — current pattern `_TOKEN_URL_REGEX = re.compile(r"\btoken=[^&\s\"']+")` (line 14) matches only query-string tokens; share-asset endpoint exposes token in URL path, so add a second pattern matching `/share/<bearer>/...` (token segment between two slashes after `/share/` or `/api/share/`). Negative-test in Story 11.2: a log record containing `/api/share/abc123/files/.../content` emits with `/api/share/<redacted>/files/.../content`.

- **Alternatives rejected:** see SCP §3.4.2 — (b) query-param `share_token=`; (c) HMAC-signed URLs; (d) per-asset Redis signature. All rejected for reasons documented there with Codex's verbatim verdicts.
- **Rationale:** mirrors `/api/share/{token}` resolve namespace (single anonymous-allowed prefix); scope check + kind filter + soft-delete filter in one DB join; revoke semantics inherit from share-token Redis DEL (no orphan signed URLs to track separately); audit emission uses token hash not clear token; Cache-Control `no-store` prevents post-revoke cached serving; ETag NOT applied to share-asset response (premature ETag-match short-circuit would bypass scope check).
- **Cascading:** `/api/models/{m}/files/{f}/content` endpoint becomes `current_user`-gated via Story 11.1 (no more anonymous access via that path). Share recipients are routed exclusively through `/api/share/...` prefix. Logging redaction extension is a shared-codebase change; pre-merge codex review (NFR6-SEC-3) verifies the regex doesn't over-redact legitimate `/share-something-else/` URL substrings.

#### Decision O — Frontend shell-level AuthGate topology

- **Realizes:** FR6-SHELL-1, FR6-SHELL-2.
- **Choice:** `apps/web/src/shell/AppShell.tsx` evaluates authentication state at mount time. Shape:

```tsx
const _PUBLIC_PATHS = new Set([
  "/login", "/register", "/reset-password", // anonymous routes from Init 5
  // /share/* handled separately because share path is dynamic
]);

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const { pathname, searchStr } = useLocation();

  // 1. Share path bypass (anonymous, already existed Init 0; preserved)
  if (pathname.startsWith("/share/")) {
    return <>{children}</>;
  }

  // 2. Public path bypass (login / register / reset-password — anonymous-allowed)
  if (_PUBLIC_PATHS.has(pathname)) {
    return <>{children}</>;
  }

  // 3. Auth loading state
  if (auth.isLoading) {
    return <LoadingScreen />;  // spinner; no shell chrome
  }

  // 4. Unauthenticated → redirect to login
  if (!auth.isAuthenticated) {
    const next = encodeURIComponent(pathname + searchStr);
    void router.navigate({ to: "/login", search: { next }, replace: true });
    return null;  // brief blank during navigation
  }

  // 5. Authenticated → full shell
  return (
    <div className="flex min-h-screen">
      <ModuleRail />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 pb-16 lg:pb-0">{children}</main>
      </div>
    </div>
  );
}
```

Per-route `<AuthGate>` wrappers (`apps/web/src/routes/catalog/*.tsx` if any exist from Init 5 admin panel) are removed — single source of auth state in shell.

- **Alternatives rejected:** keep per-route `<AuthGate>` (every new module reinvents auth check; multiplies surfaces for the kind of bug 64447ff P2 introduced); TanStack Router `beforeLoad` route guard (couples auth state to TanStack lifecycle in a way that's harder to test); React Suspense-based gating (over-engineering for boolean auth check).
- **Rationale:** single source of truth for auth-vs-anonymous decision; explicit public-path allowlist mirrors backend `_PUBLIC_ROUTES`; ModuleRail + TopBar absent from DOM for anonymous users (operator-aligned UX requirement D-LOCK-5); the `searchStr` fix (P2 from 64447ff codex review) is local to this implementation.
- **Cascading:** AuthGate.tsx remains as a thin wrapper component for legacy callers (if any), but its impl uses `searchStr` not `search`. The component may eventually be deleted in a future cleanup pass once all callers route through shell-level gating.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md` (this file's parent).
- PRD section: `prd.md` § Initiative 6 (FR6-* + NFR6-*).
- Epics section: `epics.md` § Initiative 6 (Epic E11 + Stories 11.1–11.7).
- Init 5 Decision C clarifying note (above, lines ~1494-1510).
- Memory entries informing decisions: `feedback_invoke_codex_directly.md` (Codex peer-grilling for share-asset trade-off), `feedback_itcm_autonomous_mode.md` (ITCM-owned procedural calls in Initiative 6), `feedback_vanilla_bmad_first.md` v2 (monolithic H2-append for this section).
```

**Rationale:** matches the architecture.md Initiative-N H2-append pattern from Init 5 (lines 1399-1775); three Decisions M/N/O are the minimum-viable architectural scope to characterize Initiative 6; explicit code snippets in N + O make the implementation contract reviewable now rather than at story-execution time.

### 4.3 Epics edits (`_bmad-output/planning-artifacts/epics.md`)

#### 4.3.1 Epics edit — append new section `## Initiative 6` after Init 5 closing (after line 1991)

**OLD:** (Init 5 Cross-references end at line 1991; nothing follows.)

**NEW (append H2 block):**

```markdown
## Initiative 6 — Post-Cutover Default-Deny Auth Posture

**Status:** 🚧 planning (started 2026-05-20). Maintainer: Ezop. Source SCP: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-20-post-cutover-auth.md`. Source PRD section: `prd.md` § "Initiative 6" (FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + 7 NFRs). Source architecture section: `architecture.md` § "Initiative 6" (Decisions M, N, O). Single Epic E11 with 7 stories.

**Init 5 unchanged.** Initiative 6 is purely additive — drift correction + endpoint redesign for share + frontend topology shift. No Init 5 epic retro-modification; Init 5 retro stays closed at `2429157`. Initiative 6's relationship to Init 5 is `bug-fix-scope-expansion`, not `supersession`.

### Overview

Single epic E11. Sequence: 11.1 (backend default-deny gating + agent contract) → 11.2 (share-scoped asset endpoint + share-router refactor) → 11.3 (frontend shell-level AuthGate + P2 `searchStr` fix) → 11.4 (route enforcement gate — pytest enumeration + `_PUBLIC_ROUTES` allowlist constant) → 11.5 (audit re-run with Scenario 4 extended to ALL `/api/*`) → 11.6 (cutover-smoke automation: external-host probe) → 11.7 (sibling nginx allowlist rollback + `docs/operations.md` cutover-date update). Stories 11.5 + 11.6 are GATE before Story 11.7 — audit + drill must PASS before the sibling allowlist comes off.

**Audit gate condition (NFR6-SEC-1):** identical to Init 5 NFR5-SEC-1 — zero open Critical/High; ≤3 accepted-rationale Mediums; 4th forces auto-fail + fix sprint. **Pre-merge codex review (NFR6-SEC-3) for Stories 11.1, 11.2, 11.3** — auth-boundary contracts get peer review BEFORE merge to catch the cognitive pattern that produced hot-fix 64447ff.

### Epic List

| Epic | Name | Stories | Effort | Risk | FRs covered | Gate dependency |
|---|---|---|---|---|---|---|
| E11 | Post-cutover default-deny auth posture | 7 (11.1–11.7) | Medium | **High** (security boundary; pre-merge codex review on 11.1, 11.2, 11.3) | FR6-AUTH-1..2, FR6-SHARE-1, FR6-SHELL-1..2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1 + NFR6-SEC-1..3, NFR6-PERF-1, NFR6-INT-1, NFR6-CROSS-REPO-1, NFR6-OBS-1 | none (entry epic) |

**Total: 7 stories** planned. Effort: 3–5 days back-to-back autonomous execution (mirrors Init 5 Story 10.x rate at ~1 story/4-8h with codex review intercept).

### Epic 11 — Post-cutover default-deny auth posture

**Goal.** Implement what Init 5 Decision C already specified (default-deny `/api/*` with explicit anonymous allowlist), add mechanical enforcement so the drift class cannot recur, redesign share-asset URL contract to make anonymous bypass explicit at the URL prefix level, hoist frontend AuthGate to shell level so anonymous users see only the login surface, re-run audit with Scenario 4 covering ALL `/api/*` (not just `/api/admin/*`), automate the external-host probe that Story 10.3 deferred to operator manual verification, and roll back the temporary sibling nginx allowlist (`70cb5ba`) once audit + drill PASS.

**Acceptance gate.** End-to-end drill on `.190`:
1. `curl https://3d.ezop.ddns.net/api/categories` from non-LAN host → 401 (was 200 pre-Init-6).
2. `curl https://3d.ezop.ddns.net/api/share/{valid-token}/files/{valid-file-id}/content` from non-LAN host → 200 with file body.
3. Agent service-account `hydrate_local_tree.py` runbook end-to-end completes without 403 on any pre-flight call.
4. Anonymous user navigating to `https://3d.ezop.ddns.net/` is redirected to `/login?next=%2F` (no module rail, no top bar).
5. Story 11.5 audit produces fresh `security-audit-2026-MM-DD.md` with Scenario 4 covering enumerated routes, gate-condition PASS.
6. Story 11.7 sibling configs revert deployed, `nginx -s reload` smoke verified — external anonymous still 401 (now via portal auth, not nginx allowlist).

**Pre-merge codex review (NFR6-SEC-3):** Stories 11.1, 11.2, 11.3 cannot merge until `codex review --commit <SHA>` returns no P1 findings or P1 findings are addressed in follow-up commits. Story 11.4, 11.5, 11.6, 11.7 follow standard post-merge codex review pattern.

**FRs realized:** FR6-AUTH-1, FR6-AUTH-2, FR6-SHARE-1, FR6-SHELL-1, FR6-SHELL-2, FR6-AGENT-1, FR6-AUDIT-RERUN-1, FR6-CUTOVER-PROBE-1.

**Architectural anchors:** Decisions M, N, O. Init 5 Decision C clarifying note (architecture.md ~line 1494) is the bridge between Init 5 intent and Init 6 enforcement.

**Blocked by:** none. Operator-confirmed business intent + non-negotiable D-LOCKs (D-LOCK-1..5 per SCP §3.3).

##### Story 11.1 — Backend default-deny gating on SoT + agent contract preserved

**Realizes:** FR6-AUTH-1 (partial; gating clauses), FR6-AGENT-1, NFR6-INT-1.
**Architectural anchor:** Decision M (partial — non-test side of gating); Init 5 Decision C verbatim (implement what's specified).
**Depends on:** none (E11 entry story).
**Pre-merge codex review:** REQUIRED.

Acceptance check shape:

- `apps/api/app/modules/sot/router.py`: all 6 GET endpoints get `_user_id: uuid.UUID = current_user` (NOT `current_member_or_admin` — that was the hot-fix 64447ff bug). Endpoint description text updated to "Requires authenticated user (any role). Initiative 6 default-deny posture; see architecture.md § Initiative 6 Decision M for `_PUBLIC_ROUTES` allowlist."
- `apps/api/tests/test_sot_*.py`: scenarios added for anonymous → 401, member → 200, admin → 200, **agent → 200** (NFR6-INT-1 verification). The agent-200 case is the explicit regression test for hot-fix 64447ff's P1-2.
- `apps/api/tests/test_hydrate_local_tree.py`: pre-set cookie auth on TestClient before `run_hydrate()` invocation (mirrors the test-fix attempted in 64447ff, but with `current_user` semantics → agent cookie path works without role-blocking).
- `infra/scripts/audit-six-scenarios.sh` Scenario 2 (agent ingestion): reproduces post-fix that agent cookie reaches `/api/categories` returning 200. No P1-2 regression.

##### Story 11.2 — Share-scoped asset endpoint + share-router refactor (HARDENED per Codex peer-grill)

**Realizes:** FR6-SHARE-1, NFR6-OBS-1, NFR6-INT-1 (share bypass preservation).
**Architectural anchor:** Decision N (hardened — see SCP §3.4.2 + §4.2.2 for the six Codex hardenings).
**Depends on:** 11.1 (default-deny lays the ground; share-scoped asset endpoint is the explicit anonymous bypass).
**Pre-merge codex review:** REQUIRED (NFR6-SEC-3).

Acceptance check shape:

**Implementation:**

- New route `GET /api/share/{token}/files/{file_id}/content` in `apps/api/app/modules/share/router.py` per Decision N implementation block (verbatim or near-verbatim, all 6 hardenings honored).
- `share-router.py` resolve handler refactored: lines 55, 59, 70 emit `/api/share/{token}/files/{fid}/content` URLs instead of `/api/models/{m}/files/{f}/content`.
- New audit event `share.asset.fetched` emitted on successful fetch with `target_token_hash` (sha256 hex), `target_model_id`, `target_file_id`, `target_file_kind`, `ip` fields. **Token-hash, NEVER clear token.**
- `apps/api/app/core/logging.py`: token-redaction regex extended to match `/api/share/<token>/...` path segments. Negative test: log record containing `/api/share/abc123/files/x/content` emits with `/api/share/<redacted>/files/x/content`.
- `_serve_file_content` helper extended with `cache_control` parameter (or new sibling helper); share-asset response uses `Cache-Control: no-store`.

**Test coverage — share-asset IDOR matrix (Codex-required, verbatim):**

- `apps/api/tests/test_share_asset.py` test functions:
  1. `test_anon_valid_token_valid_file_returns_200` — token A + file A (kind=image) returns 200 with file body
  2. `test_anon_valid_token_wrong_model_file_returns_404` — token A + file B (file from model B, different from token-bound model A) returns 404 (NOT 403 — uniform error shape)
  3. `test_anon_valid_token_non_shareable_kind_returns_404` — token A + file C (file from model A, but kind=`source` or `archive_3mf`) returns 404
  4. `test_anon_revoked_token_returns_404` — token revoked via existing revoke flow; subsequent fetch returns 404
  5. `test_anon_expired_token_returns_404` — token past Redis TTL; subsequent fetch returns 404
  6. `test_anon_soft_deleted_model_returns_404` — model.deleted_at IS NOT NULL; subsequent fetch returns 404
  7. `test_anon_garbage_token_returns_404` — request with non-existent token returns 404 (no timing oracle vs valid-token-wrong-file)
  8. `test_audit_row_present_on_success` — successful fetch emits `share.asset.fetched` with `target_token_hash = sha256(token).hexdigest()`, clear token absent from audit payload
  9. `test_audit_row_present_on_fail` — failed fetch (any of #2-#7) emits `share.asset.fail` with reason field (audit row has fail-reason but NO clear-token disclosure)
  10. `test_cache_control_no_store` — successful response includes `Cache-Control: no-store` header
  11. `test_etag_not_used_for_share_asset` — share-asset endpoint does NOT emit ETag header (would short-circuit scope check on 304 path)
  12. `test_logging_redaction_path_token` — log record containing path-with-token emits with token segment replaced by `<redacted>`

**Cross-validation tests (against Story 11.1 default-deny posture):**

- `test_authenticated_member_models_files_content_returns_200` — proves `/api/models/{m}/files/{f}/content` still works for authenticated principal (Story 11.1's scope; verified here to ensure cross-flow consistency)
- `test_anon_models_files_content_returns_401` — proves `/api/models/...` is 401 anonymous post-Initiative 6 (no leak through legacy URL)
- `test_share_resolve_emits_share_scoped_urls` — calls `GET /api/share/{valid-token}` and asserts each `images`, `thumbnail_url`, `stl_url` returned URL starts with `/api/share/`, NOT `/api/models/`. **This is the test that would have caught hot-fix 64447ff at code-review time** had it existed (Codex's cognitive-pattern-property check, §3.4.2).

**Frontend changes:**

- `apps/web/src/modules/share/...` (TBD module-name during Story 11.2; possibly `apps/web/src/routes/share/$token.tsx`): consumes new share-scoped URLs returned by share-resolve API. No URL-shape assumption in frontend — relies on backend-returned strings.
- Visual regression test: anonymous share-recipient view at `/share/{token}` renders thumbnail + 3D viewer correctly with new URLs (4-project matrix per project-context.md).

##### Story 11.3 — Frontend shell-level AuthGate + P2 `searchStr` fix

**Realizes:** FR6-SHELL-1, FR6-SHELL-2.
**Architectural anchor:** Decision O.
**Depends on:** 11.1 (backend default-deny in place; frontend redirect on 401 is the UX surface).
**Pre-merge codex review:** REQUIRED.

Acceptance check shape:

- `apps/web/src/shell/AppShell.tsx` implements the Decision O code block (verbatim or near-verbatim).
- `apps/web/src/shell/AuthGate.tsx`: `searchStr` (not `search`) used when constructing `next` URL. Component may remain as a thin wrapper for legacy callers OR be deleted if no caller remains post-refactor.
- Per-route `<AuthGate>` wrappers removed from `apps/web/src/routes/*.tsx` (audit grep confirms no remaining usage after refactor).
- Anonymous user visiting `https://3d.ezop.ddns.net/catalog?category_id=xyz` is redirected to `https://3d.ezop.ddns.net/login?next=%2Fcatalog%3Fcategory_id%3Dxyz` — URL-encoded, no `[object Object]` artifacts.
- `apps/web/tests/visual/anon-login-only.spec.ts`: visual regression test — anonymous user at `/`, `/catalog`, `/admin/users`, `/profile` all render the login page only (no ModuleRail, no TopBar). 4-project matrix (desktop-light/dark, mobile-light/dark) per project-context.md UI testing rules.
- `apps/web/src/locales/{en,pl}.json`: any new i18n keys for the login surface added to both.

##### Story 11.4 — Route enforcement gate (pytest enumeration + `_PUBLIC_ROUTES` allowlist)

**Realizes:** FR6-AUTH-1, FR6-AUTH-2, NFR6-PERF-1.
**Architectural anchor:** Decision M.
**Depends on:** 11.1, 11.2 (the routes whose auth posture the test asserts are in place).

Acceptance check shape:

- `apps/api/app/main.py` (or `apps/api/app/core/auth/dependencies.py`): `_PUBLIC_ROUTES` constant defined per Decision M code block.
- `apps/api/tests/test_route_enforcement_gate.py`: iterates `app.routes`, filters `/api/`-prefixed routes, asserts each route's endpoint signature contains at least one parameter with `Depends(current_*)` default OR matches `_PUBLIC_ROUTES`. Test runs in <1s (NFR6-PERF-1). Test failure message names the offending route specifically.
- Add deliberate negative-test story-internal verification: temporarily remove `current_user` from one SoT GET handler → run pytest → assert the enforcement test fails with the expected message. Then restore.
- `docs/operations.md` documents the test in the testing checklist section.

##### Story 11.5 — Audit re-run with Scenario 4 extended to ALL `/api/*`

**Realizes:** FR6-AUDIT-RERUN-1, NFR6-SEC-1, NFR6-SEC-2.
**Architectural anchor:** none (audit tooling — re-execution of Init 5 NFR5-SEC-1 process).
**Depends on:** 11.1, 11.2, 11.3, 11.4 (the auth contract that the audit asserts has shipped; the enforcement test must exist for cross-validation).

Acceptance check shape:

- `infra/scripts/audit-six-scenarios.sh` Scenario 4 reworked: enumerates `/api/openapi.json` route table (or equivalent), iterates each route as anonymous (expected: 401 except `_PUBLIC_ROUTES` → 200/400/422 per route shape) + as `member`-authenticated (expected: 200/201/403 per route's posture). Scenario 4 output is a per-route status table.
- Audit re-run produces `security-audit-2026-MM-DD.md` (new date — likely 2026-05-22 or later) with gate-condition section verbatim mirroring Init 5 NFR5-SEC-1 shape: zero open Critical/High, ≤3 accepted-rationale Mediums, 4th forces auto-fail.
- Per-Medium codex review countersignature per NFR6-SEC-2 (mirrors NFR5-SEC-2). Stories 11.1, 11.2, 11.3 commits cited in the audit's "Patch SHA" column (these are the new commits the audit covers).
- Gate condition PASS → unlocks 11.6 + 11.7.

##### Story 11.6 — Cutover-smoke automation: external-host probe

**Realizes:** FR6-CUTOVER-PROBE-1.
**Architectural anchor:** none (smoke script extension; mirrors Init 5 Decision J).
**Depends on:** 11.5 (audit-passed deployed state to probe).

Acceptance check shape:

- `infra/scripts/cutover-smoke.sh` extends with Scenario 5: `curl -fsS -o /dev/null -w "%{http_code}" https://3d.ezop.ddns.net/api/categories` from a non-LAN source. Source TBD: CI runner (if GitHub Actions ever lands), public VPS (operator already has one for monitoring), or mobile-data network on operator's laptop tether (one-shot verification).
- Scenario 5 expected: 401. Fails the smoke run if external host returns 200.
- Updated `cutover-smoke-YYYY-MM-DD.md` artifact format includes Scenario 5 row.
- Story documents the choice of external-host source in `docs/operations.md`.

##### Story 11.7 — Sibling nginx allowlist rollback + closing cutover-date update

**Realizes:** NFR6-CROSS-REPO-1, completes Initiative 6.
**Architectural anchor:** Init 5 Decision K rollback shape (this story is the analogue revert).
**Depends on:** 11.5 (audit PASS), 11.6 (external-host probe PASS).

Acceptance check shape:

- `~/repos/configs/` sibling repo: revert commit `70cb5ba` (temporary IP allowlist) via `git revert 70cb5ba`. Verify pre-deploy with `sudo nginx -t` on `.180`. Deploy via sibling repo's `sync.sh` (or equivalent — same mechanism as Init 5 Story 10.3 cutover sibling deploy).
- `nginx -s reload` on `.180`.
- Re-execute `infra/scripts/cutover-smoke.sh` (now including Scenario 5 from 11.6). All 5 scenarios PASS.
- `docs/operations.md`: cutover-date paragraph updates from `2026-05-20` (Init 5 cutover) to also reference `2026-MM-DD` (Initiative 6 final cutover). Non-skip-prefixed commit message (`feat(infra): record Initiative 6 cutover date 2026-MM-DD`) to fire `deploy.sh` and advance `infra/.last-deploy-sha`. This is the Init 5 NFR5-CROSS-REPO-1 mirror for Initiative 6.
- Update Sprint Change Proposal status: `draft` → `done` in YAML frontmatter; `Initiative 6 COMPLETE` line appended.
- Retrospective story spawned in fresh context (`bmad-retrospective` skill) for Initiative 6 close-out.

### Cross-references

- Source SCP: `sprint-change-proposal-2026-05-20-post-cutover-auth.md`.
- PRD section: `prd.md` § Initiative 6.
- Architecture section: `architecture.md` § Initiative 6 (Decisions M, N, O).
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml` — extended in Session D via `bmad-sprint-planning` (epic-11 + 11.1–11.7 status `backlog`).
- Predecessor: Initiative 5 (Public Registration & User Account Management) — closed 2026-05-20 `7e5aea0` + retro `2429157`.
- Codex peer-grilling pattern: see `feedback_invoke_codex_directly.md` + Init 5 NFR5-SEC-2 (mandatory for security-boundary stories per NFR6-SEC-3).
- Production state checkpoints: SCP §1.4 production state table.
```

**Rationale:** 7 stories deeply specified at acceptance-check-shape level (sufficient input for `bmad-create-story` skill at execution time); story numbering follows project-global convention (E11.1–E11.7) per `project-context.md`; pre-merge codex review constraint on 11.1, 11.2, 11.3 is the structural lesson from hot-fix 64447ff.

### 4.4 Other artifact edits

#### 4.4.1 `docs/operations.md` § "Public read" lines 353-355

**OLD (verbatim):**

> - **Public read** (`/api/categories`, `/api/tags`, `/api/models`,
>   `/api/models/{id}`, `/api/models/{id}/files`,
>   `/api/models/{id}/files/{id}/content`) — serves real DB-backed data.

**NEW (Initiative 6 Story 11.7 commit):**

> - **Authenticated read** (`/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`, `/api/models/{id}/files/{id}/content`) — requires `current_user` (any authenticated role: admin / member / agent). Post-Initiative 6 default-deny posture (architecture.md § Initiative 6 Decision M).
> - **Anonymous read** (`/api/share/{token}` resolve + `/api/share/{token}/files/{file_id}/content` share-scoped asset) — share-token-scoped, anonymous, no portal auth. Post-Initiative 6 share-scoped endpoint pattern (architecture.md § Initiative 6 Decision N).

**Rationale:** factual update reflecting post-Initiative 6 contract; structure is two bullets (authenticated + anonymous) mirroring the new `_PUBLIC_ROUTES` allowlist split.

#### 4.4.2 `AGENTS.md` (project root) — add post-merge codex pattern + route enforcement test reference

Defer to Story 11.7 close-out — non-blocking for SCP approval. Wording to be authored at that time.

#### 4.4.3 `_bmad-output/project-context.md` — add route enforcement test rule

Defer to Story 11.4 + 11.7 close-out — non-blocking. New project-context rule under § Testing Rules § Backend:

> - **Route enforcement gate is CI-blocking.** `apps/api/tests/test_route_enforcement_gate.py` iterates `app.routes`, asserts every `/api/*` route has either an auth `Depends(current_*)` or appears in `apps/api/app/main.py:_PUBLIC_ROUTES` allowlist. New routes ship with explicit auth posture; drift fails CI. Adding a public route requires a Sprint Change Proposal.

---

## Section 5 — Implementation Handoff

### 5.1 Change scope classification

**Major.** Per CC §5 classification rules:

- Adds new initiative (Initiative 6) → not Minor (single-story).
- Touches PRD + Architecture + Epics + 4 code files + 2 test files + 1 docs file + 1 sibling repo → not Moderate (single-artifact).
- Multi-PR (7 stories across backend + frontend + infra + audit) — classic Major scope.

### 5.2 Handoff recipients (CC §5.5)

| Recipient | Responsibilities |
|---|---|
| **Operator (Ezop)** | (a) Review + approve this SCP. (b) After approval: status check on sibling configs `70cb5ba` (verify still deployed). (c) Final Story 11.5 audit gate sign-off (single-operator self-attestation per NFR6-SEC-1 — same shape as NFR5-SEC-1). (d) Initiative 6 retro sign-off. |
| **Claude (ITCM autonomous mode)** | (a) After approval: extend `prd.md` + `architecture.md` + `epics.md` per §4 edit proposals. (b) Run `bmad-sprint-planning` (or extend sprint-status.yaml manually if planning artifact unchanged shape since Init 5). (c) Execute Stories 11.1–11.7 in sequence via story-automator (`bmad-story-automator`) or per-story `bmad-create-story` + `bmad-dev-story` cycle. (d) Pre-merge codex review on 11.1, 11.2, 11.3 (NFR6-SEC-3). (e) Auto-deploy after each non-doc commit per `feedback_auto_deploy_dev.md`. (f) Initiative 6 retrospective at close-out. |
| **Codex (peer reviewer)** | (a) Pre-merge review for Stories 11.1, 11.2, 11.3 (auth-boundary). (b) Per-Medium countersignature for Story 11.5 audit re-run (NFR6-SEC-2 mirror). (c) Background peer-grill for share-asset trade-off (§3.4.2 — in flight at SCP creation time, output integrated when complete). |

### 5.3 Success criteria for Initiative 6

1. External anonymous `curl https://3d.ezop.ddns.net/api/categories` returns 401 (with sibling `70cb5ba` reverted — i.e., portal-auth enforced, not nginx allowlist).
2. External anonymous `curl https://3d.ezop.ddns.net/api/share/{valid-token}/files/{valid-file-id}/content` returns 200 with file body.
3. Agent service-account `hydrate_local_tree.py` runbook completes end-to-end without 403 on any pre-flight or content fetch.
4. Anonymous browser at `https://3d.ezop.ddns.net/` is redirected to `/login?next=%2F` — no module rail, no top bar.
5. `apps/api/tests/test_route_enforcement_gate.py` is CI-blocking.
6. Story 11.5 audit gate condition PASS (zero open Critical/High; ≤3 accepted Mediums).
7. Story 11.7 sibling `70cb5ba` reverted, deployed, smoke PASS, cutover-date recorded in `docs/operations.md`.

### 5.4 Out of scope for Initiative 6 (and why)

- **Self-service mail-based password reset** (Init 5 Decision L deferred; still deferred).
- **OIDC/SSO federation** (Init 5 Decision M deferred; still deferred).
- **Per-model ACL** (Init 5 Decision N deferred; still deferred).
- **Postgres migration** (Init 0 baseline note; not Init 6 scope).
- **Init 5 retro doc-drift items #4-50** — only items #1-3 (which describe this gap) are folded into Initiative 6. Other drift items go to a separate `bmad-correct-course` session OR get filed as triage backlog per `feedback_preexisting_issue_threshold.md`.
- **GlitchTip dashboard for `share.asset.fetched` / `share.asset.fail`** — observability event is emitted per NFR6-OBS-1, but dedicated dashboard view is deferred to Initiative 7 if member-share-fraud becomes a real signal source.

### 5.5 Hard rules carried forward (binding for all Initiative 6 stories)

- BMAD vanilla-first stays in force per `feedback_vanilla_bmad_first.md` v2.
- ITCM autonomous mode stays in force per `feedback_itcm_autonomous_mode.md` (procedural calls owned by Claude; operator surfaces ONLY for product blockers or initiative completion).
- Pytest commands wrapped in `timeout 600 uv run pytest ...` per `feedback_pytest_timeout.md`.
- Pre-merge codex review on Stories 11.1, 11.2, 11.3 per NFR6-SEC-3 (lesson from 64447ff).
- Auto-deploy after every non-doc code/infra commit per `feedback_auto_deploy_dev.md`.
- Conversation Polish with operator; committed artifacts English per `feedback_collaboration_division.md`.
- Memory feedback at retro per `feedback_default_to_bmad_workflow.md`.

---

## Section 6 — Retrospective findings (peer-grilling Claude ↔ Codex, no operator-grilling)

Per operator brief: *"Ostry grilling - ale to Wy grillujcie siebie wzajemnie :P  Bo całą implementacją zajmowaliście się Wy."* This section grills the cognitive patterns that produced the High-002 audit miss + hot-fix 64447ff regression. No operator blame; both audit + hot-fix were authored under ITCM autonomous mode (Claude) with Codex peer review (Codex caught the hot-fix regressions; missed the audit scope gap).

### 6.1 Finding R1 — Why Story 9.2 audit didn't probe `/api/*` (read + Coming-soon slots)

**Root cause:** Story 9.2 acceptance criterion defined Scenario 4 as "IDOR scan on every admin endpoint" — the scope was set as `/api/admin/*` (mutating + admin-only-tier). The author (Claude, autonomous mode) read "IDOR" as "Insecure Direct Object Reference attack on mutating endpoints where role-based auth is the load-bearing control". This was the **textbook IDOR definition**, applied correctly — but Scenario 4 was the ONLY scenario probing route-level auth, and no other scenario picked up the read-side coverage.

**Cognitive pattern:** "audit scope inheritance from textbook scenario definitions". The six-scenario matrix (NFR5-SEC-3) was derived from threat modelling textbooks where IDOR is mutating-endpoint-focused. Read-side public endpoints don't fit "IDOR" — but they DO fit "broken access control" (OWASP Top 10 A01). The matrix didn't enumerate A01 as a separate scenario; A01 was implicitly distributed across multiple scenarios (CSRF + IDOR + admin protection). Read-side breakage fell through the gaps.

**Structural fix in Initiative 6:** Story 11.5 expands Scenario 4 to enumerate the FastAPI route table programmatically. The audit doesn't ASK "is this admin endpoint IDOR-vulnerable?" — it asks "is this `/api/*` endpoint authenticated?" for every route. This is the mechanical version of A01 coverage; eliminates the textbook-scenario blind spot.

**Cognitive failure mode preserved (anti-pattern to remember):** "if the threat model textbook didn't enumerate this attack class, the audit won't catch it". The fix is mechanical enumeration of the surface, not better textbook taxonomy.

### 6.2 Finding R2 — Why frontend AuthGate was per-route instead of shell-level

**Root cause:** Init 5 Stories 8.2 (admin Users tab) + 8.6 (admin Invites tab) wrapped their route components in `<AuthGate>` because that's what the existing pattern showed (`apps/web/src/shell/AuthGate.tsx` was already in the codebase from Init 0 baseline). The pattern was a per-route wrap — and stories followed the pattern. Nobody asked "should this gate be at shell level?"

**Cognitive pattern:** "follow the existing pattern even when the pattern was minimal for a different scope". `<AuthGate>` was sufficient when only a few admin routes needed gating; it was the wrong primitive once "everything except a small allowlist" became the rule. The pattern carried inertia past its useful range.

**Structural fix in Initiative 6:** Story 11.3 hoists AuthGate to shell level (Decision O code block). Per-route wrappers are removed. Shell-level gate with explicit `_PUBLIC_PATHS` allowlist mirrors the backend `_PUBLIC_ROUTES` allowlist — same posture on both sides.

**Cognitive failure mode preserved:** "the existing primitive will keep working as the scope grows". The fix is to re-derive the primitive when the scope flips from "opt-in protected" to "opt-in public".

### 6.3 Finding R3 — Is architecture.md Decision C "per-route allowlist" wrong default post-cutover?

**Verdict: NO, Decision C was correct in spirit; the wording was ambiguous.** The per-route table (architecture.md:1489-1490) specified `current_user` for `/api/sot/*` + `/api/catalog/*`. If the implementation had matched the table, there would have been no audit miss — the nginx allowlist would have been redundant defense, not the load-bearing gate. The drift was an implementation failure, not a design failure.

**However:** the Decision C wording "per-route allowlist" was ambiguous — it read as "enumerate routes that need auth" (opt-in protected) when the intent was "enumerate routes that are anonymous" (opt-in public). Initiative 6 §4.2.1 adds a clarifying note making the default-deny + explicit-anonymous-allow framing explicit.

**Cognitive pattern (different from R1/R2):** **"correct architecture text + drifting implementation = silent failure"**. Without mechanical enforcement, the table is documentation that anyone can ignore. Story 11.4 makes the table enforceable — the pytest enumeration test IS Decision C's per-route table executable form.

**Structural fix in Initiative 6:** Decision M (route enforcement test). The drift cannot recur because the test fails CI on it.

### 6.4 Finding R4 — Other audit-time assumptions about pre-cutover network perimeter that remained unverified

Auditing for completeness — what other implicit assumptions piggy-backed on "nginx is the gate"?

| Implicit assumption | Verified by Story 9.x? | Status |
|---|---|---|
| `/api/sot/*` GET requires auth | NO (Scenario 4 read-side gap) | **fixed by Initiative 6 Story 11.5** |
| `/api/health` is LAN-only | NO (not in scope of any Scenario) | **flagged for Story 11.7 nginx-cleanup pass** (D-LOCK-3) |
| `/agent-runbook` bypass only serves anonymous | implicitly via Scenario 2 (agent ingestion) — agent has cookie auth, so test covers cookie path not the anonymous side | reasonably covered; agent-runbook bypass is a single-purpose endpoint, low drift risk |
| Internal RPCs (none currently exist) would be LAN-only | N/A (no such RPCs) | non-issue today |
| Static assets (`apps/web/dist/`) are CDN-cache-safe | not in scope of any audit Scenario | low-priority; deferred unless a CDN is introduced |

Initiative 6 catches the `/api/sot/*` + `/api/health` items. Other items low-risk or non-issue.

### 6.5 Finding R5 — Cognitive pattern: why Codex caught what autonomous ITCM (parent context) missed (TWICE)

**Verbatim from operator brief:** *"Why did Codex P1 review of 64447ff catch share + agent regression that the autonomous ITCM (parent context) missed — what cognitive pattern produces 'fix the visible leak without re-deriving auth contract for every affected flow'?"*

**Observation — the pattern repeated during THIS SCP's own drafting (2026-05-20).** Codex peer-grill on Decision N's raw (a) design (§3.4.2) caught:

1. **Same class of contract-blindness:** my raw (a) scope-check ("`file_id` belongs to `model_id`") would have over-granted `source` (raw .blend) + `archive_3mf` files — kinds that share-resolve NEVER surfaces. I had not enumerated `ModelFileKind` against the actual share-resolve URL emission code at `share/router.py:52,65` before writing the recommendation. This is **exactly** the cognitive failure from 64447ff: localized fix without re-derivation of the contract surface.
2. **Repo drift in my own SCP write-up:** I wrote "256-bit / 32-byte tokens + DB-backed share_tokens table". Reality (verified post-Codex): `secrets.token_urlsafe(24)` = 192 bits at `share/service.py:22`; no DB table — Redis only + AuditLog emission. My recommendation rationale leaned on properties that did not exist in the code. Codex caught it by READING the file.

**Cognitive pattern observed (now with TWO data points):** ITCM-Claude under autonomous-mode pressure pattern-matches to "what's the smallest patch that addresses the signal?" and SKIPS the enumeration step ("which other flows traverse this surface?" + "what does the code actually say?"). The framing is **"fix the visible thing"**, not **"audit the contract surface around the visible thing"**. Codex doesn't have the same fix-now pressure and asks the enumeration question routinely.

**Structural fix in Initiative 6:** NFR6-SEC-3 mandates pre-merge codex review on auth-boundary stories (11.1, 11.2, 11.3). This is the procedural fix — Codex catches what parent-context ITCM misses. The discipline becomes: any commit touching auth Depends, csrf middleware, `_PUBLIC_ROUTES` allowlist, or share-token-scoped endpoints gets codex review BEFORE merge. Post-merge codex review (Init 5 NFR5-SEC-2 pattern) is too late for the auth-boundary class — by then the bad fix is live.

**Behavioral fix in Initiative 6 — ITCM frame-shift before drafting:** before drafting any auth-boundary commit AND before drafting any SCP recommendation that references existing code behavior, ITCM-Claude must execute an **explicit enumeration phase**:
- For code commits: `grep -rn` for the endpoint URL pattern across the repo (`scripts/`, `infra/`, `apps/web/src/`, `apps/api/app/`) AND read every cross-file caller before drafting the diff.
- For SCP recommendations: open and READ the actual code being referenced (`share/service.py`, `_enums.py`, `logging.py` redaction, etc.) — do NOT rely on the SCP-author's recollection of how something is implemented.
- For both: explicit self-grill question **"if Codex reviewed this in 5 minutes, what would it say?"** — and if the answer isn't immediately clear, run the actual codex review.

The 64447ff + THIS-SCP-DRAFT post-mortem reveals ITCM has all the information needed; it just doesn't load it under autonomous-mode fix-now framing. The fix is the prompt-shift, not better tools.

**Memory feedback (to be written at Initiative 6 retro close, §7.1):**
- `feedback_auth_boundary_contract_audit.md` — every commit touching `current_*` or `_PUBLIC_ROUTES` triggers explicit "who else calls this surface?" cross-file enumeration before the diff is drafted. ITCM-self-grill before drafting, not before merging.
- Extension to `feedback_itcm_autonomous_mode.md` — "frame-shift before drafting" added to the discipline list. Before any auth-boundary code or SCP-recommendation drafting: explicit enumeration of (a) cross-file callers via grep, (b) actual current code state via read (not recollection), (c) Codex-counterfactual ("what would Codex say in 5 min?"). If the answer is unclear, fire codex.

### 6.6 Findings summary

| ID | Finding | Structural fix in Initiative 6 | Cognitive pattern memory |
|---|---|---|---|
| R1 | Story 9.2 Scenario 4 textbook-IDOR scope missed read-side | Story 11.5 enumerates routes mechanically | "textbook taxonomy ≠ surface coverage" |
| R2 | Per-route AuthGate carried over from minimal-scope baseline | Story 11.3 shell-level AuthGate + Decision O | "primitive inertia past its useful range" |
| R3 | Decision C wording ambiguous despite correct table contents | Story 11.4 makes table enforceable + clarifying note | "correct text + drifting impl = silent failure" |
| R4 | `/api/health` LAN-only implicit assumption unverified | Story 11.7 nginx cleanup includes health-endpoint LAN-only check | "implicit perimeter assumptions piggy-back" |
| R5 | ITCM "fix the leak" framing missed contract re-derivation | NFR6-SEC-3 pre-merge codex on auth-boundary + new memory `feedback_auth_boundary_contract_audit.md` | "framing determines coverage; switch frames before drafting" |

---

## Section 7 — Appendix

### 7.1 Memory updates to file at Initiative 6 close

Each is an entry in `_bmad-output/memory/` (Claude's local memory) — not committed:

- **NEW: `feedback_auth_boundary_contract_audit.md`** — explicit cross-file enumeration before drafting auth-boundary commits (per finding R5). Cross-references `feedback_itcm_autonomous_mode.md` (decision discipline carrying it) + `feedback_invoke_codex_directly.md` (codex pre-merge for the class).
- **NEW: `feedback_audit_scenario_mechanical_enumeration.md`** — when defining audit scenarios that probe route-level auth, the scenario MUST enumerate the live route table programmatically; do not hand-author route lists tied to a textbook attack class (per finding R1).
- **UPDATE: `feedback_itcm_autonomous_mode.md`** — already updated 2026-05-20 with anti-pattern catch (ceremonial procedural questions). One additional refinement at Initiative 6 retro: **"frame-shift before drafting"** — explicit self-grill on contract surface before touching auth-boundary code.
- **UPDATE: `feedback_vanilla_bmad_first.md` v2** — Initiative 6 is another data-point that monolithic `## Initiative N` H2-append pattern works for bug-fix-scope-expansion (not just new-feature initiatives).
- **TRIAGE-BACKLOG candidate:** Init 5 retro doc-drift items #4-50 (the ~47 items not folded into Initiative 6). Threshold check per `feedback_preexisting_issue_threshold.md` — TBD if individual items qualify for promotion.

### 7.2 Per-story effort + risk estimate

| Story | Effort | Risk | Codex pre-merge |
|---|---|---|---|
| 11.1 | S (2-3h) | Medium (security boundary; agent regression test mandatory) | REQUIRED |
| 11.2 | M (4-6h) | High (new public endpoint; IDOR scope-check correctness critical) | REQUIRED |
| 11.3 | M (4-6h) | Medium (frontend topology shift; visual regression test 4-project matrix per project-context.md) | REQUIRED |
| 11.4 | S (1-2h) | Low (mechanical enumeration test) | optional (post-merge OK) |
| 11.5 | M (3-5h) | Medium (audit re-run; codex per-Medium per NFR6-SEC-2) | optional (post-merge OK) |
| 11.6 | S (1-2h) | Low (smoke script extension) | optional (post-merge OK) |
| 11.7 | S (1-2h) | Medium (sibling repo rollback; smoke verification gate) | optional (post-merge OK) |

**Total:** 16-26h effort (~3-5 days back-to-back autonomous execution).

### 7.3 Operator approval

Approval form (CC §6.3):

```
APPROVED / REVISE / REJECT:  ____________________________

If REVISE: which sections need rework? ___________________
___________________________________________________________

Operator signature: ______________________________________
Date: 2026-05-20
```

Per CC checklist §6.3 halt-condition: "Must have explicit approval before implementing changes."

---

*Sprint Change Proposal authored 2026-05-20 by Claude (BMAD bmad-correct-course skill, ITCM autonomous mode) for operator Ezop review. Pending Codex peer-grill output (background, share-asset trade-off §3.4.2) will be integrated as inline footnote when complete.*
