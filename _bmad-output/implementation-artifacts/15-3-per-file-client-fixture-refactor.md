---
title: 'Story 15.3 — Per-file client fixture refactor → shim to conftest.isolated_client'
type: 'refactor'
status: 'ready-for-dev'
created: '2026-05-22'
epic: 15
initiative: 10
story_id: '15.3'
story_key: '15-3-per-file-client-fixture-refactor'
predecessor_scp: '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-22-init10.md (Initiative 10 Epic 15 Story 15.3; SCP §A Story 15.3)'
realizes:
  - 'FR10-TEST-FIXTURE-CLEANUP-1 (partial — narrowed scope; see §Narrowed-scope below)'
  - 'NFR10-DETERMINISM-1'
  - 'NFR10-SCOPE-1'
predecessor_commits:
  - 'cce93e2 / f364928 — Story 15.2 close'
context:
  - 'apps/api/tests/conftest.py:73-123 — isolated_client fixture (Story 8.1 promotion)'
  - 'apps/api/tests/test_2fa_*.py — 4 files with per-file client fixtures'
auto_approval_directive: 'Operator standing approval per SCP execution_directive (2026-05-22); ITCM autonomous mode. Inline-authored sibling story within Epic 15 per autonomous chain.'
---

## Story 15.3 — Per-file client fixture refactor

**As an** ITCM owning Init 10 Epic 15 close,
**I want** the bit-isomorphic per-file `client` fixtures replaced with shims delegating to `conftest.isolated_client`,
**so that** future per-file fixture additions in TOTP-like test files stop copy-pasting boilerplate, the saturation problem Epic 8 retro §10 flagged is partially addressed, and Epic 15 closes with all three stories done.

### Narrowed scope (Phase 1 classification)

Original SCP scope: "~16 files in `apps/api/tests/test_{2fa,auth,admin,invite,share}_*.py`" — implied all are isomorphic. Phase 1 inventory shows only **4 files** in `test_2fa_*.py` yield the `(TestClient, FakeRedis)` tuple with `TOTP_FERNET_KEY` env (matching `isolated_client` shape). The other 12 are divergent (yield bare TestClient, custom token/uuid tuples, or different fake objects). Per NFR10-SCOPE-1 "pure refactor; no behavior change", Story 15.3 narrows to the isomorphic 4.

Of those 4, **3 are bit-isomorphic** to `isolated_client` (the per-file `COOKIE_SECURE=false` env is redundant with `conftest._isolated_db`'s session-scoped `COOKIE_SECURE=false`):
- `test_2fa_enrollment.py`
- `test_2fa_regenerate.py`
- `test_2fa_verify.py`

The **4th file diverges** intentionally:
- `test_2fa_disable.py` sets `ENFORCE_2FA_FOR_ROLES=""` BEFORE app creation (required for T-DISABLE-4 post-disable single-factor login path). This env must be in place at `create_app()` time, so a shim approach (`def client(isolated_client, monkeypatch): monkeypatch.setenv(...); yield ...`) won't work — `isolated_client` already created the app with the default env. Keep `test_2fa_disable.py`'s per-file fixture; document the divergence.

The 12 other files (auth/admin/invite/share/csrf/runbook/etc.) carry meaningful per-file divergence (custom token/uuid setup, bare TestClient yield, different fake types) — out-of-scope for this story per NFR10-SCOPE-1 "pure refactor". Future consolidation lands as separate scope when each file is naturally touched OR as a future Story 15.x dedicated chore.

### Acceptance Criteria

**AC-1 (FR10-TEST-FIXTURE-CLEANUP-1 — narrowed):** 3 isomorphic per-file `client` fixtures in `test_2fa_enrollment.py` + `test_2fa_regenerate.py` + `test_2fa_verify.py` removed and replaced with 3-line shim delegating to `conftest.isolated_client`.

**AC-2 (NFR10-DETERMINISM-1):** Full pytest suite 3× consecutive PASS. Same pass-count as Story 15.1's baseline (829 passed + 2 pre-existing failures via TB-021 carry-forward — Story 15.3 should NOT change either count).

**AC-3 (NFR10-SCOPE-1):** Only test-side changes. Files touched: 3 test files (per-file fixture removal) + optionally conftest.py docstring update. NO production code.

**AC-4 (Behavior preservation):** Each refactored file's test pass-count unchanged. Verify pre/post: `timeout 60 uv run pytest tests/test_2fa_<x>.py -v` returns identical pass-count.

**AC-5 (Vitest no-regression):** 94/94 files, 408/408 tests baseline preserved.

**AC-6 (Codex review):** CLEAN or P0/P1 findings closed.

### Files in scope

- `apps/api/tests/test_2fa_enrollment.py` — replace per-file client fixture with shim
- `apps/api/tests/test_2fa_regenerate.py` — replace
- `apps/api/tests/test_2fa_verify.py` — replace
- `apps/api/tests/test_2fa_disable.py` — leave per-file fixture; add 1-line comment about ENFORCE_2FA_FOR_ROLES divergence

Out of scope: the other 12 files (auth/admin/invite/share/csrf/runbook).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) + ITCM autonomous mode 2026-05-22.

### Phase 1 — Classification

Inventoried 16 candidate per-file `client` fixtures across `test_{2fa,auth,admin,invite,share,csrf,runbook}_*.py`. Classified by yield shape:

| File | Yield shape | TOTP_FERNET_KEY | fakeredis | Classification |
|---|---|---|---|---|
| test_2fa_disable.py | (TestClient, FakeRedis) | yes | yes | **Divergent** — sets ENFORCE_2FA_FOR_ROLES="" BEFORE app creation (required for T-DISABLE-4 single-factor login post-disable). Cannot use shim. KEEP. |
| test_2fa_enrollment.py | (TestClient, FakeRedis) | yes | yes | **Isomorphic** — refactor candidate |
| test_2fa_regenerate.py | (TestClient, FakeRedis) | yes | yes | **Isomorphic** (per-file COOKIE_SECURE=false is redundant; conftest._isolated_db sets it at session scope) — refactor candidate |
| test_2fa_verify.py | (TestClient, FakeRedis) | yes | yes | **Isomorphic** (same COOKIE_SECURE=false redundancy) — refactor candidate |
| test_auth_login_logout.py | TestClient | no | no | Divergent — out-of-scope |
| test_auth_refresh.py | TestClient (pre-logged-in admin) | no | no | Divergent — out-of-scope (touched in Story 15.1) |
| test_auth_sessions.py | TestClient | no | no | Divergent — out-of-scope |
| test_csrf_middleware.py | TestClient | no | no | Divergent — out-of-scope |
| test_admin_audit.py | (TestClient, token, user_id) | no | no | Divergent — out-of-scope |
| test_admin_sentry_test_endpoint.py | (TestClient, token) | no | no | Divergent — out-of-scope |
| test_invite_admin.py | (TestClient, admin_token, admin_uuid, FakeRedis) | no | yes | Divergent — out-of-scope |
| test_invite_register.py | (TestClient, admin_uuid, FakeRedis) | no | yes | Divergent — out-of-scope |
| test_runbook.py | (TestClient, fake_runbook) | no | no | Divergent (custom fake) — out-of-scope |
| test_share_admin.py | TestClient (yield in different shape) | no | yes | Divergent — out-of-scope |
| test_share_member_permission.py | TestClient | no | yes | Divergent — out-of-scope |
| test_share_public.py | TestClient | no | yes | Divergent — out-of-scope |

**3 of 16 isomorphic.** Refactor scope: 3 files (test_2fa_enrollment + test_2fa_regenerate + test_2fa_verify). Other 13 stay with intentional per-file divergence (custom shape, env, or auth-state setup that can't be shimmed without behavior change).

### Phase 2 — Refactor

3 isomorphic files: removed per-file `client` fixture (~25 LOC each); replaced with 5-line shim delegating to `conftest.isolated_client`. Ruff `--fix` removed 9 newly-unused imports (3 per file: `MagicMock`, `fakeredis.aioredis`, `app.main.create_app`). Ruff `format` clean (3 files left unchanged).

Pre-refactor pass-counts captured: test_2fa_enrollment 21 passed; test_2fa_regenerate 9 passed; test_2fa_verify 21 passed.

### Phase 3 — Behavior preservation verification

Post-refactor per-file pass-counts: test_2fa_enrollment **21 passed** (identical); test_2fa_regenerate **9 passed** (identical); test_2fa_verify **21 passed** (identical). All deterministic.

### Phase 4 — Verification

To be filled — full pytest 3× consecutive in flight.

### Codex Review

To be filled post-commit.

### Debug Log References

n/a — pure refactor, no debugging needed.

### Completion Notes List

- Story scope narrowed from "~16 files" (SCP estimate) to "3 files" after Phase 1 classification. The SCP-implied isomorphism doesn't hold for 13 of 16 files; honest narrowing per NFR10-SCOPE-1 "pure refactor; no behavior change".
- Documented per-file divergence rationale for the 13 out-of-scope files (yield shape variation, custom auth-state setup, distinct fake objects). Future consolidation requires per-file decisions — not a mechanical refactor.
- `test_2fa_disable.py` divergence (ENFORCE_2FA_FOR_ROLES="" required BEFORE `create_app()`) cannot be shimmed without restructuring `isolated_client` to accept env overrides. Out-of-scope per NFR10-SCOPE-1.

### File List

- `apps/api/tests/test_2fa_enrollment.py` — per-file client fixture replaced with shim; unused imports removed (`MagicMock`, `fakeredis.aioredis`, `create_app`). Net: ~25 LOC removed, ~3 LOC added.
- `apps/api/tests/test_2fa_regenerate.py` — same shape. Net: ~25 LOC removed, ~3 LOC added.
- `apps/api/tests/test_2fa_verify.py` — same shape. Net: ~25 LOC removed, ~3 LOC added.
