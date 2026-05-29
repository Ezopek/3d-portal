---
title: 'Story 24.1 — Centralized _admin_token helper (TB-030 13-file sweep)'
type: 'refactor'
status: 'ready-for-dev'
story_id: '24.1'
epic: 'E24 — Test Infrastructure Hygiena'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-030'
fr_ref: 'FR16-TEST-HELPERS-1'
nfr_ref: 'NFR16-DETERMINISM-1'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.4-mini per [[feedback_codex_model_routing]] routine refactor class)'
estimated_effort: '30-45 min refactor + 3× consecutive pytest verify gate'
created: '2026-05-24'
---

# Story 24.1 — Centralized `_admin_token` helper (TB-030 13-file sweep)

Status: ready-for-dev

## Story

As an Init 16 BMAD developer agent,
I want to extract the duplicated `_admin_token` / `_agent_token` / `_member_token` test helpers from 13 separate test files into ONE shared module `apps/api/tests/_test_helpers.py` that reads `get_settings().jwt_secret`,
so that the conftest cache_clear discipline remains the canonical guardian against JWT_SECRET cache pollution while eliminating the hardcoded `"test-secret-not-real"` constant duplicated across 13 files (closes TB-030 + Story 18.4 round-3 Codex P2).

## Acceptance Criteria

1. **AC1 — Centralized helper module exists.** NEW `apps/api/tests/_test_helpers.py` exports three module-top helpers:
   - `admin_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str`
   - `agent_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str`
   - `member_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str`

   Each helper internally calls `encode_token(subject=str(user_id), role=<role>, secret=get_settings().jwt_secret, ttl_minutes=ttl_minutes)`. Module includes a short docstring referencing Story 18.4 (be11035 + 2ae6569) as the prior-art reference + a comment explaining the conftest cache_clear discipline + JWT_SECRET cache-pollution background (mirrors the comment block at `test_sot_admin_models.py:32-33`).

2. **AC2 — 13 target test files migrate to the helper.** All of the following files DROP their local `JWT_SECRET = "test-secret-not-real"` constant + local `_admin_token` / `_agent_token` / `_member_token` defs and IMPORT the centralized helper:
   - `apps/api/tests/test_sot_admin_categories.py`
   - `apps/api/tests/test_sot_admin_external_links.py`
   - `apps/api/tests/test_sot_admin_tags.py`
   - `apps/api/tests/test_sot_admin_notes.py`
   - `apps/api/tests/test_sot_admin_files.py`
   - `apps/api/tests/test_sot_admin_prints.py`
   - `apps/api/tests/test_sot_auth_boundary.py`
   - `apps/api/tests/test_2fa_verify.py`
   - `apps/api/tests/test_2fa_enrollment.py`
   - `apps/api/tests/test_2fa_disable.py`
   - `apps/api/tests/test_2fa_regenerate.py`
   - `apps/api/tests/test_enforce_2fa_login.py`
   - `apps/api/tests/test_thumbnail_pipeline.py`

   Import shape (NEW at module top):

   ```python
   from tests._test_helpers import admin_token  # or agent_token / member_token as needed
   ```

   Call sites change from `_admin_token(user_id)` to `admin_token(user_id)` (drop the leading underscore — module-level helper no longer needs the private prefix since it's an exported API of `_test_helpers`).

3. **AC3 — Already-migrated files NOT re-touched.** `test_last_active_middleware.py` (Story 18.4 commit `be11035`) and `test_sot_admin_models.py` (Story 18.4 round-2 commit `2ae6569`) ALREADY use `get_settings().jwt_secret` inline. Story 24.1 OPTIONALLY harmonizes them to consume the new centralized helpers (preferred for code-cleanliness consistency) BUT does NOT re-test them under NFR16-DETERMINISM-1 (their existing pass-count is already deterministic per Init 11 verification).

4. **AC4 — Full pytest 846+/846+ PASS deterministic 3× consecutive.** Per NFR16-DETERMINISM-1: `cd apps/api && timeout 600 uv run pytest -q tests/` returns exit 0 across 3 consecutive invocations with identical pass/fail counts AND zero variance in test names. Pre-merge invariant: per-file pass-counts are preserved exactly for the 13 migrated files (the refactor is mechanical — same encode_token call, just sourced from a shared helper; pass-counts MUST NOT change).

5. **AC5 — Lint + typecheck + format clean.** `cd apps/api && ruff check tests/_test_helpers.py tests/test_sot_admin_categories.py ...` clean across all 14 touched files (1 new + 13 migrated). `ruff format --check` clean. `mypy` (if invoked) raises no new errors.

6. **AC6 — Codex review CLEAN (gpt-5.4-mini routine class).** Per [[feedback_codex_model_routing]]: routine refactor class, no security/concurrency/data-integrity sensitivity. Codex review on `--commit <SHA> -c review_model="gpt-5.4-mini"` returns 0×P1 + 0×P2 (CLEAN) on round-1. Round-2 fix-up acceptable if P2 surfaces but unexpected for pure mechanical refactor. Round-3+ surfaces as new TB candidate per [[feedback_preexisting_issue_threshold]].

7. **AC7 — No behavior change to any test.** This is a pure refactor: same `encode_token` signature, same JWT secret source (resolved at call time via `get_settings().jwt_secret`), same TTL semantics. NO test gets stronger / weaker assertions; NO test changes its mock surface; NO new test fixtures introduced beyond `_test_helpers.py`. If the refactor surfaces a real bug in any of the 13 files (unlikely), STOP per NFR10-SCOPE-1 spirit and escalate to operator as a real product blocker, not a Story 24.1 absorption.

## Tasks / Subtasks

- [ ] **T1 — Create `apps/api/tests/_test_helpers.py`** (AC: #1)
  - [ ] T1.1 — Imports: `import uuid`, `from app.core.auth.jwt import encode_token`, `from app.core.config import get_settings`.
  - [ ] T1.2 — Three module-top helper defs (admin_token, agent_token, member_token), each ~3 lines, all reading `get_settings().jwt_secret` at call time.
  - [ ] T1.3 — Module docstring + inline comment explaining Story 18.4 prior-art + conftest cache_clear discipline.
  - [ ] T1.4 — Verify no circular import (the module imports from `app.core.*` only, not from `tests.*`).

- [ ] **T2 — Migrate 7 admin-router test files** (AC: #2)
  - [ ] T2.1 — `test_sot_admin_categories.py`: drop local `JWT_SECRET` + `_admin_token`; add helper import; sed-replace `_admin_token(` → `admin_token(`.
  - [ ] T2.2 — `test_sot_admin_external_links.py`: same shape.
  - [ ] T2.3 — `test_sot_admin_tags.py`: same shape.
  - [ ] T2.4 — `test_sot_admin_notes.py`: same shape.
  - [ ] T2.5 — `test_sot_admin_files.py`: same shape.
  - [ ] T2.6 — `test_sot_admin_prints.py`: same shape.
  - [ ] T2.7 — `test_sot_auth_boundary.py`: may use multiple roles (admin + member + agent); migrate all helpers used.

- [ ] **T3 — Migrate 5 2FA test files** (AC: #2)
  - [ ] T3.1 — `test_2fa_verify.py`: inspect for any non-`_admin_token` helpers (this file may have partial-auth specific helpers); migrate `_admin_token` only, leave file-specific helpers alone unless they wrap the JWT_SECRET constant directly.
  - [ ] T3.2 — `test_2fa_enrollment.py`: same triage.
  - [ ] T3.3 — `test_2fa_disable.py`: same triage.
  - [ ] T3.4 — `test_2fa_regenerate.py`: same triage.
  - [ ] T3.5 — `test_enforce_2fa_login.py`: same triage.

- [ ] **T4 — Migrate `test_thumbnail_pipeline.py`** (AC: #2)
  - [ ] T4.1 — Same migration shape as T2.x. Confirmed pre-existing pattern at line 46-50.

- [ ] **T5 — Optional harmonization of already-migrated files** (AC: #3)
  - [ ] T5.1 — `test_last_active_middleware.py` (Story 18.4 be11035): refactor inline `get_settings().jwt_secret` calls to import + use centralized helpers. NO functional change.
  - [ ] T5.2 — `test_sot_admin_models.py` (Story 18.4 2ae6569): same. NO functional change.
  - [ ] Decision: HARMONIZE if it's a clean drop-in (the local helpers were named `_admin_token` / `_agent_token` / `_member_token` in 2ae6569 — likely a clean 1:1 mapping). SKIP if local helpers carry per-file customization.

- [ ] **T6 — Verify pre-merge invariants** (AC: #4, #5)
  - [ ] T6.1 — `cd apps/api && uv run ruff check tests/_test_helpers.py tests/test_*.py` clean.
  - [ ] T6.2 — `cd apps/api && uv run ruff format --check tests/_test_helpers.py tests/test_*.py` clean.
  - [ ] T6.3 — `cd apps/api && timeout 600 uv run pytest -q tests/` returns exit 0 with 846+/846+ PASS (specific count varies based on currently-shipped state; capture in Dev Agent Record).
  - [ ] T6.4 — Repeat T6.3 twice more (3× consecutive total per NFR16-DETERMINISM-1); assert identical pass-count + zero variance.

- [ ] **T7 — Commit + auto-deploy** (AC: #6)
  - [ ] T7.1 — Single dev commit message: `refactor(tests): centralize _admin_token helper to tests/_test_helpers.py (Story 24.1, TB-030)`.
  - [ ] T7.2 — ff-merge to `main` (per BMAD vanilla flow).
  - [ ] T7.3 — Auto-deploy to .190 SKIPPED (test-file-only change, no runtime code touched) per [[feedback_auto_deploy_dev]] doc-only skip clause — INSPECTION: test files DO change Python module loading but NO `app/` code is modified; deploy-skip-gate at `infra/scripts/deploy.sh` SHOULD detect zero `app/` changes and skip. If skip-gate does NOT recognize test-file-only, OPERATOR DECISION: either accept the trivial deploy OR adjust skip-gate (TB-040 candidate if becomes a recurring pattern).
  - [ ] T7.4 — Codex review: `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` per [[feedback_codex_review_invocation]] mode-flag standalone shape.
  - [ ] T7.5 — Codex CLEAN expected. If P1/P2 surface, round-2 fix-up + re-review (per [[feedback_codex_review_mental_model]]).
  - [ ] T7.6 — Sprint-status flip: `24-1-centralized-admin-token-helper: backlog → ready-for-dev` (already flipped via bmad-create-story exit) → `in-progress` (at dev-story start) → `review` (at code-review pending) → `done` (at Codex CLEAN).
  - [ ] T7.7 — Update triage-backlog `TB-030` status: `candidate` → `done` with commit cite.

## Dev Notes

### Current state of the 13 target files

All 13 files share the same pattern at module top (~line 20-30):

```python
JWT_SECRET = "test-secret-not-real"


def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)
```

A subset of files (`test_sot_auth_boundary.py`, `test_2fa_*.py`) ALSO define `_agent_token` and/or `_member_token` with the same shape but different `role=` arg.

The `JWT_SECRET` constant matches the `monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")` set in `apps/api/tests/conftest.py:99-106` (`isolated_client` fixture). The constant works EMPIRICALLY because conftest cache_clears `get_settings()` before every test AND sets the env var BEFORE create_app. But the constant is BRITTLE — if a future test calls `monkeypatch.setenv("JWT_SECRET", "something_else")` mid-test WITHOUT a cache_clear, the existing tests would still pass (using their stale local constant) while production would be using the new secret. Centralized helper closes this latent gap.

### Reference implementation (Story 18.4)

`apps/api/tests/test_sot_admin_models.py:32-60` (commit `2ae6569`, 2026-05-23):

```python
# JWT_SECRET="s") call monkeypatch.setenv("JWT_SECRET", ...) without
# clearing get_settings()'s LRU cache, so a hardcoded constant here can
# go stale. Using get_settings().jwt_secret at call time defers resolution
# to whatever the active Settings() returns, mirroring the production
# encode_token call shape.
def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(
        subject=str(user_id),
        role="admin",
        secret=get_settings().jwt_secret,
        ttl_minutes=30,
    )

def _agent_token(user_id: uuid.UUID) -> str:
    return encode_token(
        subject=str(user_id),
        role="agent",
        secret=get_settings().jwt_secret,
        ttl_minutes=30,
    )

def _member_token(user_id: uuid.UUID) -> str:
    return encode_token(
        subject=str(user_id),
        role="member",
        secret=get_settings().jwt_secret,
        ttl_minutes=30,
    )
```

The Story 24.1 module just hoists these definitions to `tests/_test_helpers.py` and drops the leading underscore (no longer file-private).

### Why this works under conftest cache_clear discipline

`apps/api/tests/conftest.py:99-106` (the `isolated_client` fixture, finalised via Init 9 Story 14.x refactor):

1. `monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")` — sets env var.
2. `get_settings.cache_clear()` — wipes LRU cache so next `get_settings()` re-reads env.
3. ... test runs ...
4. `finally: get_settings.cache_clear()` — wipes cache on teardown so next test starts fresh.

Centralized `admin_token(user_id)` calling `get_settings().jwt_secret` will:
- Cache miss on first call → reads env var (`test-secret-not-real`) → caches result.
- Cache hit on subsequent calls within same test → returns cached secret.
- After test teardown → cache cleared → next test re-reads env.

This is EXACTLY the production behavior + matches Story 18.4's verified-deterministic pattern.

### Files NOT touched (intentional)

- `apps/api/tests/conftest.py` — owns the cache_clear discipline; no change needed.
- `apps/api/tests/test_last_active_middleware.py` + `test_sot_admin_models.py` — already migrated in Story 18.4; OPTIONAL harmonization in T5 (preferred for code cleanliness, but not required for AC pass).
- Any tests that don't use admin/agent/member tokens (e.g. `test_thumbnail_*` for pure worker testing) — outside Story 24.1 scope; leave alone.

## File List

**NEW (1 file):**
- `apps/api/tests/_test_helpers.py` (~30-40 LOC: imports + 3 helper defs + docstring)

**MODIFIED (13 files for required migration + up to 2 optional harmonization):**
- `apps/api/tests/test_sot_admin_categories.py`
- `apps/api/tests/test_sot_admin_external_links.py`
- `apps/api/tests/test_sot_admin_tags.py`
- `apps/api/tests/test_sot_admin_notes.py`
- `apps/api/tests/test_sot_admin_files.py`
- `apps/api/tests/test_sot_admin_prints.py`
- `apps/api/tests/test_sot_auth_boundary.py`
- `apps/api/tests/test_2fa_verify.py`
- `apps/api/tests/test_2fa_enrollment.py`
- `apps/api/tests/test_2fa_disable.py`
- `apps/api/tests/test_2fa_regenerate.py`
- `apps/api/tests/test_enforce_2fa_login.py`
- `apps/api/tests/test_thumbnail_pipeline.py`
- (Optional T5 harmonization) `apps/api/tests/test_last_active_middleware.py`
- (Optional T5 harmonization) `apps/api/tests/test_sot_admin_models.py`

**Diff stats expected:**
- ~30-40 LOC added (new helper module)
- ~5-7 LOC removed per migrated file × 13 = ~65-91 LOC removed
- ~1-2 LOC added per migrated file × 13 = ~13-26 LOC added (the import line + possibly drop the unused JWT_SECRET import if it was only used by the local helper)
- Net: -50 to -70 LOC across the codebase. Pure refactor; no new dependencies.

## Verification

Per [[feedback_pre_merge_gate_checklist]] pre-merge gates:

| Gate | Command | Pass criterion |
|---|---|---|
| Helper module loads | `cd apps/api && uv run python -c "from tests._test_helpers import admin_token, agent_token, member_token"` | Exit 0, no import errors |
| Ruff check | `cd apps/api && uv run ruff check tests/_test_helpers.py tests/test_*.py` | 0 errors |
| Ruff format | `cd apps/api && uv run ruff format --check tests/_test_helpers.py tests/test_*.py` | "X files already formatted" |
| Pytest full-suite #1 | `cd apps/api && timeout 600 uv run pytest -q tests/` | Exit 0, 846+/846+ PASS |
| Pytest full-suite #2 | (immediately repeat) | Identical count to #1 |
| Pytest full-suite #3 | (immediately repeat) | Identical count to #1 + #2 |
| Per-file isolation | `cd apps/api && timeout 600 uv run pytest -q tests/test_sot_admin_categories.py` | Per-file PASS count unchanged vs pre-refactor baseline |
| `alembic check` | `cd apps/api && uv run alembic check` | Not applicable (no schema changes) — SKIP |
| `npm run build` | (web side) | Not applicable (Python-only change) — SKIP |
| Codex review | `codex review --commit <SHA> -c review_model="gpt-5.4-mini"` | CLEAN (0×P1 + 0×P2) |

Per [[feedback_pytest_timeout]]: wrap pytest in `timeout 600`. If exit 124 (timeout) surfaces, `pkill -9 -f 'pytest tests/'` + escalate to operator as a real product blocker (Story 24.1 refactor cannot cause pytest hang; if it does, something is wrong with the centralized helper resolution).

## References

- [Init 16 SCP §4.3](sprint-change-proposal-2026-05-24-init16.md#43-epic-e24--test-infrastructure-hygiena) — Story 24.1 originating scope.
- [epics.md § Initiative 16 § Epic E24](../planning-artifacts/epics.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Story 24.1 description.
- [prd.md § FR16-TEST-HELPERS-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — Verifiable requirements.
- [triage-backlog.md § TB-030](../triage-backlog.md) — Original candidate write-up + Story 18.4 round-3 P2 context.
- Reference commits: `be11035` (Story 18.4 primary) + `2ae6569` (Story 18.4 round-2 — _admin_token/_agent_token/_member_token helpers in test_sot_admin_models.py).
- Memory entries:
  - [[feedback_codex_model_routing]] — gpt-5.4-mini routing for routine refactor class.
  - [[feedback_pre_merge_gate_checklist]] — typed pre-Codex gate list.
  - [[feedback_pytest_timeout]] — `timeout 600 uv run pytest` mandatory wrapper.
  - [[feedback_preexisting_issue_threshold]] — Codex P2 round-3 was the original surfacing channel for TB-030.
  - [[feedback_auto_deploy_dev]] — deploy-skip-gate evaluation for test-only changes.

## Dev Agent Record

### Agent Model Used

(Filled in by bmad-dev-story execution)

### Debug Log References

(Filled in during dev-story phase)

### Completion Notes List

(Filled in during dev-story phase)

### File List

(Filled in during dev-story phase — should match the File List above modulo optional T5 harmonization)
