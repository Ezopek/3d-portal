# Security Audit Re-run — Initiative 6 / Story 11.5 — 2026-05-21

**Auditor:** Ezop (single-operator self-attestation per NFR5-SEC-2 mirrored for Initiative 6 as NFR6-SEC-2)
**Subject:** 3d-portal Initiative 6 deliverables (Stories 11.1 + 11.2 + 11.3 + 11.4) deployed at `https://3d.ezop.ddns.net` + `http://192.168.2.190:8090` (LAN)
**Git HEAD at scan:** `c5724b1` (post Story 11.4 ff-merge to main; release `0.1.0+c5724b1` deployed to `.190`)
**Predecessor audit:** `security-audit-2026-05-20.md` (Init 5 Story 9.4 PASS + Supplemental High-002 OPEN-after-revert)
**Audit window valid through:** 2026-06-20 (30 days) or until next significant deploy, whichever first

---

## 1. Scope of re-run

This audit is the Initiative 6 Story 11.5 re-execution of the six-scenario matrix
with **Scenario 4 reworked** from its pre-Init-6 scope ("IDOR scan on
`/api/admin/*` via member principal") to the new Initiative 6 scope ("auth-boundary
probe on ALL `/api/*` routes"). The pre-Init-6 scenario missed the read-side
`/api/sot/*` surface that the Story 10.3 cutover exposed externally — proximate
root cause of supplemental finding High-002 dated 2026-05-20.

**Scenarios re-executed:**
- **Scenario 4** (REWORKED): auth-boundary probe on every `/api/*` route via
  `/api/openapi.json` enumeration. Each route probed anonymous (no cookies)
  and per Initiative 6 default-deny posture must return 401/403 UNLESS
  enumerated in `_PUBLIC_ROUTES` allowlist (`apps/api/app/main.py`).

**Scenarios NOT re-executed (Init 5 evidence carried forward):**
- Scenario 1 (invite-token brute force), Scenario 2 (refresh-token replay),
  Scenario 3 (CSRF + JWT tampering), Scenario 5 (login rate-limit), Scenario 6
  (member share-link amplification). Init 5 audit `security-audit-2026-05-20.md`
  PASS verdict carries forward — these surfaces are unaffected by Stories
  11.1-11.4 (no auth-stack changes; only enforcement-side hardening of the
  drift gap).

## 2. Initiative 6 commits covered

| Story | Patch SHA | Description |
|---|---|---|
| 11.1 | `9a00562` + `8e52519` | Backend default-deny gating on SoT GET endpoints (`current_user` Depends) + Codex P1+P2 fix-up (hydrate cookie auth + ruff) |
| 11.2 | `3d69dfe` + `e2e3945` + `f9f0e26` + `b8a5882` | Share-scoped asset endpoint (Decision N hardened-(a)) + 3 Codex fix-up rounds (audit token-resolve fail + client-IP via `_client_ip` + ETag suppression retirement) |
| 11.3 | `293cef3` + `df62e1f` + `f37d4fb` + `8b2d44e` | Frontend shell-level AuthGate (Decision O) + Codex P1+P2 fix-up rounds (admin-by-default visual fixture + single-encode next param + consumer decodeURIComponent removal) |
| 11.4 | `c5724b1` | Route enforcement gate pytest (Decision M) + `_PUBLIC_ROUTES` constant + 3 mechanical tests |

## 3. Scenario 4 — Auth-boundary probe (Story 11.5 reworked)

Source: `_bmad-output/implementation-artifacts/audit-raw/2026-05-21/scenario-4-anon-probe.txt`
Reproducer: `_bmad-output/implementation-artifacts/audit-raw/2026-05-21/scenario-4-reproducer.sh`

**Methodology:**
1. Fetch `/api/openapi.json` from the deployed `.190` instance.
2. Enumerate every `/api/*` path × method (skip `HEAD`).
3. Substitute path templates with bogus UUID/token values.
4. Probe each route as anonymous (no cookies, no `X-Portal-Client` header).
5. Verdict per route:
   - **PASS** if `_PUBLIC_ROUTES` member: any non-5xx code is acceptable (typically 200/400/422 for valid-shape anonymous calls).
   - **PASS** if NOT `_PUBLIC_ROUTES` member: status code MUST be 401 or 403.
   - **FAIL** otherwise (would indicate the High-002 regression class).

**Result:** **69/69 PASS, 0 FAIL.**

Sample of the per-route output (full table in raw artifact):

```
GET     /api/health                                                 anon=200 expected=public    PASS
POST    /api/auth/login                                             anon=403 expected=public    PASS
GET     /api/auth/me                                                anon=401 expected=protected PASS
GET     /api/auth/sessions                                          anon=401 expected=protected PASS
POST    /api/auth/2fa/verify                                        anon=403 expected=public    PASS
GET     /api/admin/invites                                          anon=401 expected=protected PASS
POST    /api/admin/invites                                          anon=403 expected=protected PASS
PATCH   /api/admin/users/{user_id}                                  anon=403 expected=protected PASS
GET     /api/categories                                             anon=401 expected=protected PASS
GET     /api/tags                                                   anon=401 expected=protected PASS
GET     /api/models                                                 anon=401 expected=protected PASS
GET     /api/models/{model_id}                                      anon=401 expected=protected PASS
GET     /api/models/{model_id}/files                                anon=401 expected=protected PASS
GET     /api/models/{model_id}/files/{file_id}/content              anon=401 expected=protected PASS
GET     /api/share/{token}                                          anon=404 expected=public    PASS
GET     /api/share/{token}/files/{file_id}/content                  anon=404 expected=public    PASS
... [69 rows total]
```

**Key verifications:**
- `/api/categories`, `/api/tags`, `/api/models`, `/api/models/{id}`, `/api/models/{id}/files`,
  `/api/models/{id}/files/{file_id}/content` ALL return 401 anonymously
  (Story 11.1 default-deny posture confirmed end-to-end). This is the
  property that supplemental finding High-002 demanded.
- `/api/share/{token}` + `/api/share/{token}/files/{file_id}/content` return
  404 anonymously with the bogus token (Story 11.2 token-resolve-failed
  uniform 404 + no enumeration oracle).
- `/api/auth/*` POST endpoints return 403 anonymously (CSRF-missing; the
  endpoints themselves are anonymous-allowed by `_PUBLIC_ROUTES` but the
  CSRF middleware enforces `X-Portal-Client` header presence before
  reaching the handler — verdict reads "public" + 403 = PASS because the
  CSRF rejection is intentional defense-in-depth).

**Scope filter:** `/agent-runbook` is explicitly excluded — it is a non-`/api/*`
path served via nginx-level bypass per NFR5-INT-1 Decision K (Init 5
preserved-across-cutover surface), outside the Initiative 6 `/api/*` auth
contract.

## 4. Route enforcement gate (Story 11.4 / Decision M)

Source: `apps/api/tests/test_route_enforcement_gate.py`

**Methodology:** static CI-gating test iterating `app.routes`. 3 assertions:
1. `test_every_api_route_has_auth_depends_or_is_in_public_allowlist`: every
   `/api/*` route has either an auth `Depends(current_*)` parameter OR is
   listed in `_PUBLIC_ROUTES`. Mechanical drift detection.
2. `test_public_routes_allowlist_matches_actual_route_table`: no stale
   entries in `_PUBLIC_ROUTES` (would mask future drift).
3. `test_no_unrecognized_auth_dep_in_route_table`: defense against silent
   `_current_*` auth-dependency expansion.

**Result:** **3/3 PASS in 0.23s** (NFR6-PERF-1 <1s satisfied).

This test is now CI-blocking. Any future commit that adds a `/api/*` route
without auth Depends AND without an `_PUBLIC_ROUTES` entry fails the test
with a specific message naming the violating route. The High-002 drift class
(architecture intent vs shipped code mismatch) cannot recur silently.

## 5. Findings disposition

**Totals:** 0 Critical / 0 High / 0 Medium / 0 Low surfaced by Story 11.5
re-execution.

| ID | Source | Severity | Title | Disposition |
|----|--------|----------|-------|-------------|
| — | scenario-4 reworked | — | (no findings) | n/a |
| — | route enforcement gate | — | (no findings) | n/a |

**Carry-forward observations (NOT findings):**
- **Doc-drift on architecture.md Decision N "no ETag" claim.** Story 11.2 ship
  result retired the "no validators" variant of Decision N (Codex round 3
  surfaced Range+If-Range KeyError trade-off). Architecture.md still asserts
  "no ETag" in the Decision N inline block; doc-drift item carried forward
  to Story 11.7 closing pass (architecture.md text alignment to shipped
  implementation).
- **Pre-existing test isolation pollution.** `test_hydrate_local_tree.py::test_hydrate_creates_local_tree`
  fails when batched with `test_sot_model_file_content.py` due to DB state
  pollution (FAKE_STL_PAYLOAD_AAA seed leaks into hydrate-iterated `/api/models`
  listing). Verified pre-existing via git-stash on pre-Story-11.1 codebase.
  Init 5 retro doc-drift #8 class — not introduced by Initiative 6; not a
  finding here. Carry-forward to a dedicated test-isolation cleanup story.
- **Pre-existing frontend vitest failures.** 18 vitest failures across
  `modules/admin/{InvitesPage, GenerateInviteModal, InviteTokenDisplayModal,
  ResetLinkDisplayModal, UsersPage}` test files — verified pre-existing via
  git-stash on pre-Story-11.3 codebase. Init 5 retro doc-drift class. Not
  introduced by Initiative 6.

## 6. Gate-condition decision (NFR6-SEC-1 mirror of NFR5-SEC-1)

> **E11 cleared to proceed to Stories 11.6 + 11.7** — gate condition PASS:
> zero open Critical/High findings; 0/3 accepted-rationale Mediums (full
> margin); 69/69 auth-boundary probe PASS; 3/3 route enforcement test PASS;
> audit complete on 2026-05-21.

NFR6-SEC-2 (per-Medium codex review countersignature) — N/A this audit
(zero Mediums surfaced). The Initiative 6 pre-merge codex review chain on
Stories 11.1 / 11.2 / 11.3 (10 total iteration logs at
`_bmad-output/implementation-artifacts/codex-review-11-{1,2,3}-*.log`) is
the procedural-side compensating control for the auth-boundary commit
class, mirroring NFR5-SEC-2 spirit one story-cycle earlier.

## 7. Reproduce

```bash
# Standalone anonymous probe (Story 11.5 minimal reproducer; runs against
# any /api/openapi.json + LAN endpoint without test fixtures).
bash _bmad-output/implementation-artifacts/audit-raw/2026-05-21/scenario-4-reproducer.sh

# Full Scenario 4 via integrated six-scenario harness (requires audit
# fixtures + member cookies; aligned with Init 5 NFR5-SEC-3 reproduction
# pattern):
bash infra/scripts/audit-six-scenarios.sh scenario-4

# Route enforcement gate (CI-blocking unit test):
cd apps/api && timeout 60 uv run pytest tests/test_route_enforcement_gate.py
```

## 8. Audit window + next-cutover gate

This audit is valid for 30 days OR until next significant deploy, whichever
first. Stories 11.6 + 11.7 ship within the window — they don't invalidate
this audit because:
- Story 11.6 extends `cutover-smoke.sh` with an external-host probe; it
  doesn't change the `/api/*` route table or auth contract.
- Story 11.7 reverts sibling configs `70cb5ba` (temporary IP allowlist on
  `.180` nginx); it changes the EDGE posture, not the application auth.
  Post-Story-11.7 the external probe (via Story 11.6 mechanism) MUST
  re-verify the property that this audit asserts: anonymous external →
  401 on every `/api/*` route except `_PUBLIC_ROUTES`. That verification
  IS the close-out gate for Initiative 6.

---

*Audit signed off: 2026-05-21 by Ezop (single-operator self-attestation;
NFR6-SEC-1 + NFR6-SEC-2 compensating controls satisfied; codex pre-merge
review chain on auth-boundary commits captured at `codex-review-11-{1,2,3}-*.log`).
Sprint-status flip: `11-5-audit-rerun-scenario-4-extended: in-progress → done`.
E11 cleared to proceed to Story 11.6.*
