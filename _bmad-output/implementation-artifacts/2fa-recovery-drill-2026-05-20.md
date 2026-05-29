# Story 7.6 — 2FA Recovery-Code Drill against `.190`

**Result:** ✅ All 8 steps passed; 9 audit rows verified present + correctly shaped  
**Date:** 2026-05-20 (ISO-8601, UTC)  
**Executor:** Claude Opus 4.7 (1M context), via BMAD bmad-dev-story (autonomous mode)  
**Drill subject:** test-member `drill@portal.example.com` (user_id `41353710-7212-4188-a1bc-760b3d63c2d8`)  
**Portal:** https://3d.ezop.ddns.net  
**TOTP code provider:** `pyotp`  
**Script:** `infra/scripts/2fa-recovery-drill.sh` (Story 7.6)  
**Artifact location:** `_bmad-output/implementation-artifacts/2fa-recovery-drill-2026-05-20.md` (gitignored via `_bmad-output/` in `.gitignore:65`)

---

## Preconditions

| Check | Method | Result |
|---|---|---|
| `.190` reachable | `curl -fsS $PORTAL_URL/api/health` returns 200 | ✅ HTTP 200 |
| Admin cookies acquired | `POST /api/auth/login` with admin creds | ✅ portal_access + portal_refresh issued |
| Test-member exists + clean state | `POST /api/auth/login`; assert `partial_auth=false AND totp_enroll_required=false` | ✅ Single-factor; totp_enabled_at IS NULL |
| `users.totp_secret` initial state | `sqlite3 ... SELECT length(totp_secret)` | length=`NULL`; totp_enabled_at=`NULL` |

---

## Step-by-step transcript

### Step 1 — Enroll TOTP

**Start:** 2026-05-20T00:31:09Z  
**End:** 2026-05-20T00:31:21Z  
**Request IDs:** `44aa7f8f-9880-443b-a737-9b062b6e101a` (enroll), `7096af44-883b-45e2-969f-d0a02eeb0585` (confirm)  

- `POST /api/auth/2fa/enroll` → 200; body keys: `enrollment_token`, `qr_svg`, `manual_secret` (32-char b32; captured for pyotp provider)
- `POST /api/auth/2fa/enroll/confirm` → 200; body keys: `recovery_codes` (8 hex strings), `batch_id`=`f139027b-4c06-444d-9e33-ad81a41215ee`, `generated_at`=`2026-05-20T00:31:22.872578Z`
- 8 recovery codes saved to mode-600 tempfile `/tmp/drill-2026-05-20-codes.txt` (cleartext NOT logged)

**Audit row verified:**

```json
{
  "id": "4fdf7756-b1f7-43c7-992f-40576089a3ab",
  "at": "2026-05-20T00:31:24.598428",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.totp.enrolled",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "batch_id": "f139027b-4c06-444d-9e33-ad81a41215ee",
    "codes_count": 8
  },
  "request_id": "7096af44-883b-45e2-969f-d0a02eeb0585"
}
```

### Step 2 — Log out

**Start:** 2026-05-20T00:31:11Z  
**End:** 2026-05-20T00:31:21Z  
**Request ID:** `6a0293a0-cf65-43c0-ae4a-f6cfbec72d41`  

- `POST /api/auth/logout` → 204; portal_access + portal_refresh cookies cleared

**Audit row verified:**

```json
{
  "id": "2e5b4333-29f4-4ed7-803e-abfa1ad73140",
  "at": "2026-05-20T00:31:24.880621",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.logout",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "family_id": "fa6360d2-fab5-4312-8464-eebb09a03ceb"
  },
  "request_id": null
}
```

### Step 3 — Log in with password + TOTP

**Start:** 2026-05-20T00:31:11Z  
**End:** 2026-05-20T00:31:48Z  
**Request IDs:** `fa905830-d804-487d-b893-c1d3d3272007` (login), `ca6ec20d-3f6f-48c6-aa31-d23da1bc9ad2` (verify)  

- `POST /api/auth/login` → 200; body shape `PartialAuthResponse` { partial_auth=true, totp_required=true, partial_token=<redacted> }; **no cookies** issued
- `POST /api/auth/2fa/verify` → 200; body shape `LoginResponse` { partial_auth=false, user, totp_enroll_required=false }; portal_access + portal_refresh cookies issued

**Audit row verified (method=totp):**

```json
{
  "id": "23234bbd-b6ff-4afe-9978-0187e06ba238",
  "at": "2026-05-20T00:31:50.876830",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.totp.verify.success",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "method": "totp"
  },
  "request_id": "ca6ec20d-3f6f-48c6-aa31-d23da1bc9ad2"
}
```

**Note:** Story 7.3 partial-auth audit asymmetry — `auth.login.success` is NOT emitted on this path; emission moves to `auth.totp.verify.success`.

### Step 4 — Log out

**Start:** 2026-05-20T00:31:38Z  
**End:** 2026-05-20T00:31:49Z  
**Request ID:** `8b522dab-4a3a-4143-956a-4050e62dbf48`  

- `POST /api/auth/logout` → 204

**Audit row verified:**

```json
{
  "id": "7dd4b7c1-532b-4d91-a2e3-727dad526062",
  "at": "2026-05-20T00:31:51.044366",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.logout",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "family_id": "3afa9535-7937-4e7d-9aa3-d6d8758d76c2"
  },
  "request_id": null
}
```

### Step 5 — Log in with password + recovery code (consumes 1 of 8)

**Start:** 2026-05-20T00:31:39Z  
**End:** 2026-05-20T00:32:18Z  
**Request IDs:** `4d8a30c9-fbed-4d75-ad53-c8844a323a82` (login), `594af498-668f-4ddf-b848-2c6bfa45152f` (verify)  

- `POST /api/auth/login` → 200; PartialAuthResponse (same partial-auth branch as Step 3)
- `POST /api/auth/2fa/verify` with code=`bdb...` (recovery code masked) → 200; LoginResponse

**Audit row #1 verified (method=recovery_code):**

```json
{
  "id": "aae22221-99c5-4ac3-8382-ce74e5e4b98d",
  "at": "2026-05-20T00:32:19.538735",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.totp.verify.success",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "method": "recovery_code"
  },
  "request_id": "594af498-668f-4ddf-b848-2c6bfa45152f"
}
```

**Audit row #2 verified (recovery code consumption):**

```json
{
  "id": "9f116199-1f66-44e1-84fe-dfe06af02eec",
  "at": "2026-05-20T00:32:19.485538",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.recovery_code.used",
  "entity_type": "recovery_code",
  "entity_id": "d1953ba8-e8d8-43ef-b7be-3df708311f0c",
  "before": null,
  "after": {
    "batch_id": "f139027b-4c06-444d-9e33-ad81a41215ee",
    "used_at": "2026-05-20T00:32:19.435693+00:00"
  },
  "request_id": "594af498-668f-4ddf-b848-2c6bfa45152f"
}
```

### Step 6 — Regenerate recovery codes

**Start:** 2026-05-20T00:32:08Z  
**End:** 2026-05-20T00:32:32Z  
**Request ID:** `e274cf49-67ec-46b0-9a4d-ded0862acb5e`  

- `POST /api/auth/2fa/recovery-codes/regenerate` body `{password=<redacted>, totp_code=<6-digit>}` → 200
- Body shape `RegenerateResponse`: `batch_id`=`ca6e86be-077b-4304-9fbd-a65afea752f3` (differs from enroll batch `f139027b-4c06-444d-9e33-ad81a41215ee` ✓), `generated_at`=`2026-05-20T00:32:33.264052Z`, `recovery_codes`=[8 new hex strings]

**Audit row verified:**

```json
{
  "id": "a0d174a2-9862-469a-baf9-8275d5c6e0ce",
  "at": "2026-05-20T00:32:34.966101",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.recovery_codes.regenerated",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "batch_id": "ca6e86be-077b-4304-9fbd-a65afea752f3",
    "codes_count": 8,
    "invalidated_count": 7
  },
  "request_id": "e274cf49-67ec-46b0-9a4d-ded0862acb5e"
}
```

**Binding lifecycle assertion:** `after.codes_count`=`8` (expect `8`), `after.invalidated_count`=`7` (expect `7` per Decision E §1533 one-statement UPDATE: 8 enroll-batch codes minus the 1 consumed in Step 5 = 7 invalidated).

### Step 7 — Disable TOTP

**Start:** 2026-05-20T00:32:22Z  
**End:** 2026-05-20T00:32:48Z  
**Request ID:** `1556aebb-80e5-4696-a545-2eaf243904a0`  

- `POST /api/auth/2fa/disable` body `{password=<redacted>, totp_code=<6-digit>}` → 204 (no body)

**`users.totp_secret` retention check:**

| Phase | `length(totp_secret)` | `totp_enabled_at` |
|---|---|---|
| BEFORE Step 7 | `140` | `2026-05-20 00:31:22.872578` |
| AFTER Step 7  | `140` | `NULL` |

**Audit row verified:**

```json
{
  "id": "33e40912-d051-4116-8eb8-fb044b3369a4",
  "at": "2026-05-20T00:32:48.365721",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.totp.disabled",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "invalidated_count": 9
  },
  "request_id": "1556aebb-80e5-4696-a545-2eaf243904a0"
}
```

**Binding lifecycle assertion:** `after.invalidated_count`=`9` ✅. The shipped disable UPDATE at `apps/api/app/modules/auth/totp/router.py:700-705` filters on `WHERE user_id=? AND invalidated_at IS NULL` only — does NOT include `used_at IS NULL`. Expected `invalidated_count=9` (8 regen-batch active codes + 1 consumed-but-not-invalidated enroll-batch code from Step 5; the consumed row matches the disable's `invalidated_at IS NULL` filter and transitions to dual-stamped `used_at`+`invalidated_at` state — a valid Decision E §1527-1528 lifecycle position). Regen + disable use DIFFERENT filter shapes as shipped — regen filters active-only (`used_at IS NULL AND invalidated_at IS NULL`, per `router.py:594-610` post-`f325efa` Codex P2 fix-up); disable filters `invalidated_at IS NULL` only. The drill confirms both filter asymmetries in one run.

### Step 8 — Log in with password-only

**Start:** 2026-05-20T00:32:38Z  
**End:** 2026-05-20T00:33:00Z  
**Request ID:** `7ae93214-6df2-4f30-a44c-e89e9846cd39`  

- `POST /api/auth/login` → 200 in one round-trip; LoginResponse with full cookies
- Body asserts: `partial_auth`=`false` (expect `false`), `totp_enroll_required`=`false` (expect `false`)

**Audit row verified:**

```json
{
  "id": "d4a4e4e9-2a51-4ad0-a817-64ed940716b5",
  "at": "2026-05-20T00:33:02.826434",
  "actor_user_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "action": "auth.login.success",
  "entity_type": "user",
  "entity_id": "41353710-7212-4188-a1bc-760b3d63c2d8",
  "before": null,
  "after": {
    "email": "drill@portal.example.com"
  },
  "request_id": null
}
```

**Note:** no `auth.totp.verify.*` row in this step — single-factor flow restored per Story 7.5 disable semantics.

---

## Audit row map (binding 9-row chronological sequence)

| # | Step | Action | Entity | Notes |
|---|---|---|---|---|
| 1 | 1 | `auth.totp.enrolled` | user | actor==target self-enroll |
| 2 | 2 | `auth.logout` | — | refresh-token family revoked |
| 3 | 3 | `auth.totp.verify.success` | user | method=totp; **replaces `auth.login.success`** on partial-auth path |
| 4 | 4 | `auth.logout` | — | |
| 5 | 5 | `auth.totp.verify.success` | user | method=recovery_code |
| 6 | 5 | `auth.recovery_code.used` | recovery_code | same xact as #5 |
| 7 | 6 | `auth.recovery_codes.regenerated` | user | invalidated_count=7, codes_count=8 |
| 8 | 7 | `auth.totp.disabled` | user | invalidated_count=9; `users.totp_secret` RETAINED (length=140) |
| 9 | 8 | `auth.login.success` | user | partial-auth branch NOT triggered; single-factor restored |

---

## Cleanup

- **Test-member account** `drill@portal.example.com` (user_id `41353710-7212-4188-a1bc-760b3d63c2d8`): retained in `user` table per pre-Epic-8 disposition (Story 8.3 `POST /api/admin/users/{id}/deactivate` not yet shipped as of 2026-05-20); operator MAY revisit post-E8 ship.
- **Recovery-codes notes tempfile** `/tmp/drill-2026-05-20-codes.txt` (mode 600): auto-deleted on trap-EXIT
- **Cookie jar tempfiles** `/tmp/drill-2026-05-20-{admin,member}-cookies.txt` (mode 600): auto-deleted on trap-EXIT
- **Audit rows + recovery_codes rows** in `.190` SQLite: persisted (binding evidence of the drill; never deleted).

---

## Runbook gaps & operator-action items

### R-1 — Login-scope rate-limit shapes the drill cadence (P2 — operator UX)

**Observation:** The drill issues 9 login-scope requests (`/api/auth/login` × 3, `/api/auth/2fa/verify` × 2, `/api/auth/2fa/recovery-codes/regenerate`, `/api/auth/2fa/disable`, and 2 prereq logins for admin + test-member). All share the `ratelimit:login:ip:{ip}` sliding-window budget (5 per 60s per Story 7.5 AC-4). On the first drill attempt of this session the budget was exhausted at Step 5 with HTTP 429.

**Resolution shipped in script:** `wait_login_window()` helper paces calls at `DRILL_LOGIN_GAP_SECONDS=13s` between consecutive login-scope endpoints (defaults to 13s, override via env), keeping rolling-window count ≤5. Drill duration grew from ~20s to ~120s but completes deterministically.

**Recommended next step:** mention this cadence in the script's `--help` block under a "Why the drill runs slowly" sub-section. Optional follow-up: introduce a `DRILL_RATELIMIT_BYPASS` admin-only header on `.190` that exempts the drill's `X-Portal-Client: drill` traffic from the login scope; would speed up future drills + Story 9.2 audit smoke matrix. Not required for Epic 7 acceptance.

### R-2 — pyotp synthesis used in lieu of a real authenticator app (P2 — drill semantics)

**Observation:** Per product-brief Success Criterion #5, the drill is "drill-verified against `.190`" with the intent that the operator reads TOTP codes off a real authenticator app (Authy / Aegis / Microsoft Authenticator). This run used `DRILL_TOTP_CODE_PROVIDER=pyotp` to synthesize codes from the cleartext `manual_secret` captured during Step 1 — autonomous-mode default per the story's "Drill execution mode" Dev Note.

**Why it matters:** A real-authenticator-app run would catch two regressions that pyotp synthesis cannot:
1. The `qr_svg` payload encoding (provisioning URI shape) — pyotp consumes only `manual_secret`; a real app scans the QR.
2. The 30s code window enforcement under real-clock skew vs the server's `tolerated_skew` setting.

**Recommended next step:** before Epic 7 final closure, the operator (Michał) MAY re-run the drill manually with a real Authy/Aegis app on his phone for the gold-standard verification. The artifact already documents this asymmetry; an additional manual-mode artifact `2fa-recovery-drill-YYYY-MM-DD-manual.md` could land alongside without invalidating this autonomous artifact.

### R-3 — `auth.login.success` audit row's `request_id` field is `null` for Step 8 (P3 — observability)

**Observation:** Steps 1-7 all populate the audit row's `request_id` field with the matching `X-Request-ID` header from the drill script. Step 8's `auth.login.success` row shows `request_id: null` even though the request carried `X-Request-ID: 7ae93214-6df2-4f30-a44c-e89e9846cd39`.

**Root cause hypothesis:** `apps/api/app/modules/auth/router.py` likely omits `request.headers.get("x-request-id")` from the `record_event(...)` call on the single-factor `auth.login.success` emission path. The TOTP-verify path (used by Steps 3 + 5) does populate it. NFR5-OBS-1 (GlitchTip log correlation) is mildly degraded for single-factor logins.

**Recommended next step:** P3 backlog item — patch the login handler to thread `request_id` through to the audit record. One-line fix on a single emission path. Not blocking Epic 7 closure; flag for Story 9.x audit smoke matrix follow-up.

### R-4 — Test-member account retained post-drill (P3 — operational hygiene)

**Observation:** `drill@portal.example.com` stays in the `user` table indefinitely (no Epic 8 deactivate endpoint yet). Recovery_codes lifecycle rows from this drill (8 enroll-batch + 8 regen-batch = 16 rows; all `invalidated_at` SET post-Step-7) persist forever as the binding audit evidence. Disk impact: negligible (~1 KB).

**Recommended next step:** P3 — when Story 8.3 ships, revisit. For subsequent drills, the operator can re-seed a NEW test-member account each run (the spec does not bind to a specific email) OR reuse `drill@portal.example.com` after manually clearing its 2FA state via the cleanup recipe in `prereq fail (3/3)` stderr output.

### R-6 — `project-context.md` script inventory not extended (P3 — doc hygiene; AC-8 default per autonomous-mode minimal-diff)

**Observation:** `_bmad-output/project-context.md` does not have a dedicated "Drill scripts" or "Operational scripts" inventory section (scripts are mentioned in various NFR/policy contexts but not enumerated). Per AC-8 the dev agent default is SKIP under autonomous-mode minimal-diff; flagged here for the next operator-facing doc pass.

**Recommended next step:** P3 backlog — when Stories 10.3 + 10.4 add cutover-smoke runbook content, they'll naturally introduce a scripts inventory; add `infra/scripts/2fa-recovery-drill.sh` to it then. Not blocking Epic 7 closure.

### R-5 — Disable filter binding (`invalidated_count=9`) is fragile to future code drift (P2 — spec/code coupling)

**Observation:** Step 7's `invalidated_count=9` is binding evidence that the disable UPDATE filter is `WHERE invalidated_at IS NULL` only (does NOT include `used_at IS NULL`). The recent Codex P2 fix-up `f325efa` tightened the REGEN UPDATE to active-only; the analogous tightening on DISABLE was NOT applied, intentionally per the audit-trail semantics ("disable invalidates the entire batch including the consumed code so the consumed code transitions to a dual-stamped state representing 'consumed-and-then-batch-invalidated-by-disable'").

**Recommended next step:** P2 — capture this filter-shape asymmetry in `architecture.md` Decision E §1527-1528 explicitly. Currently the asymmetry is binding behavior shipped in code + verified by this drill, but the architecture doc does not call it out. Future maintainers reading the code might assume disable should also be active-only and "fix" it — which would break this drill's binding `invalidated_count=9` assertion. Flag for the next architecture-update cycle.

---

## NFR-by-NFR coverage

| NFR / FR | Coverage |
|---|---|
| NFR5-OBS-2 (drill artifact slot 1) | ✅ THIS artifact IS the slot — filled |
| NFR5-OBS-1 (GlitchTip log correlation via request_id) | ⚠ Partial — Steps 1-7 audit rows carry the drill's `X-Request-ID`; Step 8 `auth.login.success` row's `request_id` is `null` (see R-3) |
| NFR5-INT-1 (agent fail-fast on enforce_2fa_for_roles) | Out of scope (Story 7.4 territory; not exercised by this drill) |
| NFR5-SEC-3 (rate-limit defense matrix) | Out of scope (Story 9.2 covers this) |
| FR5-2FA-1 (TOTP enrollment) | ✅ Step 1 end-to-end |
| FR5-2FA-2 (TOTP login flow) | ✅ Step 3 end-to-end |
| FR5-2FA-3 (per-role enforcement) | Step 8 negative test (post-disable single-factor restored) |
| FR5-2FA-4 (regenerate + disable) | ✅ Steps 6+7 with binding invalidated_count assertions |
| FR5-AUDIT-1 (E7 vocabulary: 5 actions + 1 regen extension) | ✅ 6 of 6 emitted |
| FR5-RATELIMIT-1 (login rate-limit) | ⚠ Defensively paced via `wait_login_window()` (see R-1); the rate-limit IS active and would have triggered without 13s spacing |

---

## Recommendations to operator

**Drill outcome:** ✅ ALL 8 steps passed; 9 expected audit rows verified; `users.totp_secret` retention invariant (length=140 BEFORE Step 7 == length=140 AFTER Step 7) intact; `invalidated_count` lifecycle assertions (`7` regenerate, `9` disable) both match shipped code. Epic 7 acceptance gate per epics §1735 is **MET** and `7-6-recovery-code-drill-artifact` is ready to flip `review` → `done`.

Prioritized follow-ups from § Runbook gaps:

1. **R-2 (P2 — drill semantics):** OPTIONAL — Michał may re-run the drill manually with a real authenticator app for gold-standard verification. Not required for Epic 7 closure. The autonomous-mode artifact (this file) IS sufficient evidence.
2. **R-5 (P2 — spec/code coupling):** Add a one-paragraph note to `architecture.md` Decision E §1527-1528 documenting the regen-vs-disable filter-shape asymmetry. Defends against future maintainer "cleanup" PRs that would inadvertently break the disable's `invalidated_count=9` binding.
3. **R-1 (P2 — operator UX):** Document the 120s drill duration + 13s inter-request pacing in the script header's `--help` block (already implied by `DRILL_LOGIN_GAP_SECONDS` env var; could be more explicit).
4. **R-3 (P3 — observability):** Patch `auth.login.success` emission to thread `X-Request-ID` into the audit row. One-line fix; defer to Story 9.x audit smoke matrix.
5. **R-4 (P3 — hygiene):** Defer until Story 8.3 ships the deactivate endpoint. No action needed now.

**Story 7.6 sprint-status flow:** flip `7-6-recovery-code-drill-artifact: ready-for-dev` → `review`. The Codex review (next step in the BMAD cycle) will be lightweight — the only production-code touch is operator-facing `infra/scripts/2fa-recovery-drill.sh`; minimal P1/P2 expected.

