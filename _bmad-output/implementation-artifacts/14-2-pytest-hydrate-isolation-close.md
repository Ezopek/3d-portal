---
title: 'Story 14.2 — Pytest hydrate DB-pollution isolation close'
type: 'bugfix'
status: 'ready-for-dev'
created: '2026-05-21'
epic: 14
initiative: 9
story_id: '14.2'
story_key: '14-2-pytest-hydrate-isolation-close'
predecessor_scp: '_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-21.md (Initiative 9; SCP §4.1.3 + §4.3.3)'
realizes:
  - 'FR9-PYTEST-HYDRATE-1 (full)'
  - 'NFR9-DETERMINISM-1'
  - 'NFR9-SCOPE-1'
predecessor_commits:
  - '1d5f7a8 — Story 14.1 shipped 2026-05-21 (vitest admin finder fixes + 52 i18n keys)'
  - 'e59abe5 — TB-015 quick-dev shipped 2026-05-21'
auto_approval_directive: 'Operator standing approval per "lecimy do końca jak init 5" (2026-05-21); ITCM autonomous mode per memory [[itcm-autonomous-mode]]. Status auto-flipped backlog → ready-for-dev at create-story close.'
---

## Story 14.2 — Pytest hydrate DB-pollution isolation close

**As an** ITCM owning the autonomous Init 9 chain,
**I want** `test_hydrate_creates_local_tree` to pass deterministically regardless of test ordering,
**so that** Init 7 Stories 12.3 + 12.5 + Init 8 Story 13.2 can develop on a reliable pytest signal without cross-test seed pollution from `test_sot_model_file_content`.

### Acceptance Criteria

**AC-1 (FR9-PYTEST-HYDRATE-1):** `cd apps/api && timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` in this exact order returns 0 failures.

**AC-2 (NFR9-DETERMINISM-1):** AC-1 invocation succeeds across **10 consecutive runs** (spec § epics.md Story 14.2 verbatim clause). Logged in Dev Agent Record.

**AC-3 (NFR9-SCOPE-1):** No production-code changes. Fix restricted to `apps/api/tests/test_sot_model_file_content.py` (and optionally `apps/api/tests/conftest.py` if the function-scoping path is chosen — see § Root Cause). If a fix path requires touching `app/modules/sot/router.py`, `scripts/hydrate_local_tree.py`, or `core/db/models.py` — STOP and escalate.

**AC-4:** Full-suite regression: `cd apps/api && timeout 600 uv run pytest` returns same or better total PASS count post-fix (current baseline from Story 14.1 Codex review: ~700+ tests, 0 failures).

### Root Cause (verified by reproduction 2026-05-21)

`_seed_model_with_file()` helper at `apps/api/tests/test_sot_model_file_content.py:36-67` writes REAL file bytes to disk but stores `sha256="0" * 64` (placeholder all-zeros hash) on the `ModelFile` DB row (line 60). The hash is irrelevant for the same-file tests (they verify content, not hash), so they pass standalone.

But the DB is **session-scoped** via `_isolated_db` (`apps/api/tests/conftest.py:32`) — the seed rows persist into subsequent tests. When `test_hydrate_creates_local_tree` runs, it triggers `scripts/hydrate_local_tree.py` which iterates ALL `Model` rows (including the 4 seeded by `test_sot_model_file_content`) and downloads each file. Hydrate then verifies the downloaded bytes against the DB-stored `sha256` — **mismatch on every prior-seeded file** (real-content-hash ≠ "0"*64).

Reproduced 2026-05-21 against current HEAD (`1d5f7a8`): `FAILED tests/test_hydrate_local_tree.py::test_hydrate_creates_local_tree`, captured logs show 4× `sha256 mismatch after download` errors for prior-test files, then dragon.stl gets a download but the test assertion fails (likely on `summary["m_downloaded"] >= 1` because hydrate's error path doesn't count the failed-sha-check downloads).

### Fix path — ITCM decision

**Selected:** compute real sha256 from `content` bytes in `_seed_model_with_file`. One-line addition to the helper at line 60. Test-only change per NFR9-SCOPE-1. Cleaner than the alternatives:

- ❌ Function-scope `_isolated_db` — heavy refactor, breaks 200+ existing tests that rely on session-scoped DB.
- ❌ Module-scoped teardown to delete Category/Model/ModelFile rows — risk of cascading FK delete issues; tests would silently fail if teardown imperfect.
- ❌ Hydrate-side tolerance for sha256 mismatch — production-code touch, NFR9-SCOPE-1 violation.

Implementation:
```python
import hashlib  # add to imports if not present

# In _seed_model_with_file, replace line 60 (sha256="0" * 64) with:
sha256=hashlib.sha256(content).hexdigest(),
```

The placeholder hash was a test-smell from pre-hydrate-verify days. Computing real hash is the correct semantic — it's what every other test in the codebase does.

### Tasks

- [ ] **T1 — Reproduce baseline.** `cd apps/api && timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py 2>&1 | tee /tmp/14-2-baseline.log` — confirm 1 failure (test_hydrate_creates_local_tree) with sha256-mismatch error class.

- [ ] **T2 — Apply fix.** Add `import hashlib` to `apps/api/tests/test_sot_model_file_content.py` imports (if not present). Replace `sha256="0" * 64,` at line 60 with `sha256=hashlib.sha256(content).hexdigest(),`.

- [ ] **T3 — Per-pair verification.** `cd apps/api && timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py` — both files PASS.

- [ ] **T4 — NFR9-DETERMINISM-1 verification.** Run the same pytest invocation 10 consecutive times via `for i in $(seq 1 10); do echo "=== Run $i ==="; timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py 2>&1 | tail -3; done`. ALL 10 runs MUST report `passed` for both files. Log results.

- [ ] **T5 — Full-suite regression.** `cd apps/api && timeout 600 uv run pytest 2>&1 | tail -5` — total PASS count same-or-better vs baseline. Zero new failures.

- [ ] **T6 — Lint gates.** `cd apps/api && uv run ruff check tests/ && uv run ruff format --check tests/` — clean.

- [ ] **T7 — Sprint-status flip + triage-backlog update.** Story status `in-progress → review → done` after Codex review. TB-018 item 2 (hydrate pollution) flips to closed-via-Story-14.2 with commit SHA.

- [ ] **T8 — Commit + deploy.** Conventional `fix(api): real sha256 in test fixture seeds (Story 14.2 / TB-018)`. Body cites root cause + 10× determinism log + cross-references TB-018 + Story 14.1 sibling close. Auto-deploy per `feedback_auto_deploy_dev` — test files = code.

### Verification commands

```bash
# Baseline reproduction:
cd /home/ezop/repos/3d-portal/apps/api
timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py

# 10× determinism:
for i in $(seq 1 10); do
  echo "=== Run $i ==="
  timeout 600 uv run pytest tests/test_sot_model_file_content.py tests/test_hydrate_local_tree.py 2>&1 | tail -3
done

# Full-suite regression:
timeout 600 uv run pytest 2>&1 | tail -5

# Lint:
uv run ruff check tests/ && uv run ruff format --check tests/
```

### Non-goals (NFR9-SCOPE-1)

- No `conftest.py` fixture-scoping changes (function-scoping `_isolated_db` would balloon scope).
- No production-code touches (`app/`, `scripts/hydrate_local_tree.py`, `core/db/models.py` untouched).
- No other test files modified (only `test_sot_model_file_content.py`).
- No alembic migration.
- No new test additions (only the seed-helper fix).
