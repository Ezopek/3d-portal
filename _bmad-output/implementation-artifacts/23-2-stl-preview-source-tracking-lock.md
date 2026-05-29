---
title: 'Story 23.2 — STL preview source-tracking + single-flight lock (TB-034)'
type: 'hardening'
status: 'ready-for-dev'
story_id: '23.2'
epic: 'E23 — Share-View Security Hardening'
initiative: 'Init 16 — Triage Backlog Cleanup (Post-Init-15 Sweep)'
tb_ref: 'TB-034'
fr_ref: 'FR16-STL-PREVIEW-LOCK-1'
architectural_anchor: 'Decision X.2'
route: 'one-shot quick-dev cycle (Codex routing gpt-5.5 per [[feedback_codex_model_routing]] data-integrity/concurrency class)'
estimated_effort: '1.5-2 h backend refactor + race-condition test + Codex review'
created: '2026-05-24'
---

# Story 23.2 — STL preview source-tracking + single-flight lock (TB-034)

Status: ready-for-dev

## Story

As an operator who may replace the primary STL on an existing model (delete + reupload, or upload-new + curation swap),
I want the STL preview render pipeline to recognize "this set of previews is for the OLD geometry — render new ones for the CURRENT STL"
AND I want concurrent share-view hits to dispatch ONE render job per STL (not N duplicate jobs producing duplicate 4-view sets),
so that share recipients see previews of the CURRENT geometry (not stale OLD ones) AND the DB doesn't accumulate 8-12 stl_preview rows per model from race-condition duplicate dispatches (closes TB-034 P2#1 stale-previews-on-STL-replace + P2#2 race-condition duplicate-render).

## Acceptance Criteria

1. **AC1 — Source tracking by STL sha256 in `original_name`.** Worker `render_stl_previews` at `workers/render/render/worker.py:195` writes new ModelFile rows with `original_name = f"{view}-{stl_sha8}.png"` where `stl_sha8 = stl_row.sha256[:8]` (first 8 hex chars of the source STL's sha256). Existing call site at line 279 (`original_name=f"{view}.png"`) changes to the new format.

2. **AC2 — Worker idempotency query uses sha256-matching filter.** At worker.py:243-249, the `existing_count` query adds a third WHERE clause: `ModelFile.original_name.like(f"%-{stl_sha8}.png")`. Now the skip-if-complete-set guard counts ONLY previews from the CURRENT STL, not orphan previews from a prior STL. The 4-view set threshold (`>= len(VIEW_NAMES)`) stays as the completion gate.

3. **AC3 — Dispatch-side filter at `apps/api/app/modules/share/router.py:82-87`.** The `existing_preview_count` query (currently counts ALL stl_preview rows for the model) ALSO adds the sha256-match filter — same shape as worker query. Without this, every cold share-view hit would re-enqueue render even though previews exist (because the worker's check is sha256-aware but the dispatcher's check isn't, so they'd disagree and the dispatcher would loop).

4. **AC4 — Share-list query at `apps/api/app/modules/share/router.py:121-126` filters by current STL sha256.** `preview_files` query adds `ModelFile.original_name.like(f"%-{stl_sha8}.png")` clause. Effect: stale orphan previews (from a prior STL, or pre-Story-23.2 legacy rows with `original_name = "iso.png"` lacking sha8 suffix) do NOT surface in the share carousel. The current STL's previews are the only ones shown. Operator can manually clean orphan rows via a future cleanup task (out-of-scope for this story; tracked as TB-041 candidate at close-out if needed).

5. **AC5 — Single-flight Redis SETNX lock at dispatch.** In `share/router.py` BEFORE `enqueue_job` (around line 90), acquire lock:
   ```python
   lock_key = f"share:stl_preview_lock:{stl_for_preview}"
   acquired = await request.app.state.redis.set(lock_key, "1", nx=True, ex=300)
   if not acquired:
       # Another job in flight for this STL — skip enqueue without erroring.
       pass  # logged at debug-level if needed
   else:
       await request.app.state.arq.enqueue_job("render_stl_previews", str(stl_for_preview))
   ```
   Lock TTL 300s covers worst-case render wall time + safety margin. Worker releases lock in `finally` block (AC6).

6. **AC6 — Worker releases SETNX lock on completion AND failure.** In `worker.py:render_stl_previews`, the outer `try ... except Exception` block gets a paired `finally` that runs `await redis.delete(f"share:stl_preview_lock:{model_file_id}")`. Released on done, skipped, failed paths — the lock is a dispatch-coordination primitive, not a state marker. (Existing `status_key = f"render:stl_preview:{model_file_id}"` semantics unchanged; that's the visible status; the new lock is internal coordination only.)

7. **AC7 — Race-condition contention test (NEW pytest).** New test in `apps/api/tests/test_share_public.py` (or new file `test_stl_preview_single_flight.py` if scope warrants):
   - Seed model with 1 STL file + 0 stl_preview rows.
   - Issue 2 concurrent `GET /api/share/<token>` calls via `asyncio.gather` (or 2 sequential calls — depending on what the TestClient + arq stub allows).
   - Stub or spy `arq.enqueue_job` to count call invocations.
   - Assert: total enqueue calls == 1 (not 2).
   - Assert: lock key present in Redis after first call, released after worker simulation.

8. **AC8 — Sha256-mismatch idempotency test (NEW pytest).** New test:
   - Seed model with 1 STL file (sha256 `aaaaaa...`) + 4 stl_preview rows naming `{view}-aaaa.png` (or `{view}-aaaaaaaa.png` — verify format).
   - Worker invoked with the same STL: should skip per existing 4-view-set guard.
   - REPLACE the STL: delete original + insert new ModelFile with sha256 `bbbbbb...` (or via admin endpoint).
   - Worker invoked: should render 4 NEW previews with `{view}-bbbb.png` names (not skip).
   - Assert: 4 OLD + 4 NEW rows exist in DB (8 total stl_preview rows).
   - Assert: share-list query at `share/router.py:121-126` returns ONLY the 4 NEW previews (sha8 filter active).

9. **AC9 — Backend pytest no-regression.** `cd apps/api && timeout 600 uv run pytest -q tests/` exit 0; 864+/864+ PASS (Story 24.1 baseline) PLUS new tests AC7+AC8 = ~866-868 PASS. Deterministic 3× consecutive per [[feedback_pytest_timeout]] + NFR16-DETERMINISM-1.

10. **AC10 — Ruff + alembic check clean.** No new Alembic migrations needed (sha256 storage in `original_name` is a string format change, not schema change). `ruff check` + `ruff format --check` clean. `alembic check` clean.

11. **AC11 — Codex review CLEAN (gpt-5.5 data-integrity class).** Per [[feedback_codex_model_routing]] heavy class. Round-2 fix-up acceptable if P1/P2 surface (expected for concurrency/data-integrity work). Round-3+ surfaces as new TB candidate.

## Tasks / Subtasks

- [ ] **T1 — Worker source-tracking refactor** (AC: #1, #2)
  - [ ] T1.1 — `worker.py:243-249`: add `stl_sha8 = stl_row.sha256[:8]` computed from the `stl_row.sha256` field; extend `existing_count` query with `ModelFile.original_name.like(f"%-{stl_sha8}.png")`.
  - [ ] T1.2 — `worker.py:279`: change `original_name=f"{view}.png"` to `original_name=f"{view}-{stl_sha8}.png"`.
  - [ ] T1.3 — Inline comment block at line 238-242 updated to reflect sha256-based source-tracking + cite Story 23.2 / TB-034 P2#1.

- [ ] **T2 — Share router dispatch + list source-tracking** (AC: #3, #4)
  - [ ] T2.1 — `share/router.py:73-87`: read `stl_row.sha256` into `stl_sha8` (need to expand the existing select to fetch sha256 column too). Extend `existing_preview_count` query with sha256-match filter.
  - [ ] T2.2 — `share/router.py:121-126`: `preview_files` query adds same sha256-match filter (only CURRENT previews surface).
  - [ ] T2.3 — Inline comments cite Story 23.2 / Decision X.2.

- [ ] **T3 — Single-flight Redis SETNX lock at dispatch** (AC: #5)
  - [ ] T3.1 — `share/router.py:88-98`: wrap `enqueue_job` in SETNX check. `lock_key = f"share:stl_preview_lock:{stl_for_preview}"`; `acquired = await request.app.state.redis.set(lock_key, "1", nx=True, ex=300)`; if not acquired, skip enqueue (log debug, no error).
  - [ ] T3.2 — Confirm `request.app.state.redis` is the canonical Redis client handle in this router (per Init 12 Story 19.1 share_anon_ratelimit middleware pattern).

- [ ] **T4 — Worker lock release** (AC: #6)
  - [ ] T4.1 — `worker.py:render_stl_previews` outer try/except: add `finally: await redis.delete(f"share:stl_preview_lock:{model_file_id}")`. Released on done / skipped / failed paths.
  - [ ] T4.2 — Inline comment that the lock is dispatch-coordination only (distinct from `status_key`).

- [ ] **T5 — Tests** (AC: #7, #8, #9)
  - [ ] T5.1 — Race-condition contention test in `test_share_public.py` (or `test_stl_preview_single_flight.py`). Mock `enqueue_job` + Redis; assert single dispatch per concurrent call pair.
  - [ ] T5.2 — Sha256-mismatch idempotency test. Seed pre-replace state, invoke worker, replace STL, invoke again, assert 4+4 rows + share-list filter shows only new 4.
  - [ ] T5.3 — Full pytest 3× consecutive PASS via `timeout 600 uv run pytest -q tests/`.

- [ ] **T6 — Pre-merge gates** (AC: #9, #10)
  - [ ] T6.1 — `cd apps/api && uv run ruff check workers/render/render/worker.py app/modules/share/router.py tests/` clean.
  - [ ] T6.2 — `cd apps/api && uv run ruff format --check ...` clean.
  - [ ] T6.3 — `cd apps/api && uv run alembic check` clean (no migration needed; verify).
  - [ ] T6.4 — Full pytest 3× consecutive (NFR16-DETERMINISM-1).

- [ ] **T7 — Commit + Codex review + auto-deploy** (AC: #11)
  - [ ] T7.1 — Commit: `fix(share,workers): STL preview source-tracking + single-flight lock (Story 23.2, TB-034)`.
  - [ ] T7.2 — ff-merge to main.
  - [ ] T7.3 — `codex review --commit <SHA>` (default gpt-5.5 data-integrity/concurrency class).
  - [ ] T7.4 — Round-2 fix-up if P1/P2.
  - [ ] T7.5 — `infra/scripts/deploy.sh` per [[feedback_auto_deploy_dev]].
  - [ ] T7.6 — Sprint-status flip + TB-034 → done.

## Dev Notes

### Current code state (post Init 12 Story 19.6 fef96f7 + round-2 fix)

**Worker idempotency (worker.py:243-249):**
```python
existing_count = session.exec(
    select(func.count()).select_from(ModelFile).where(
        ModelFile.model_id == stl_row.model_id,
        ModelFile.kind == ModelFileKind.stl_preview,
    )
).one()
if existing_count >= len(VIEW_NAMES):
    return {"status": "skipped", ...}
```
BUG: counts ALL stl_preview rows for the model regardless of source STL. Post-STL-replace, the 4 OLD rows trigger skip; new STL never renders.

**Worker file write (worker.py:279):**
```python
new_file = ModelFile(
    ...,
    original_name=f"{view}.png",  # <-- no sha256 stamping
    ...
)
```

**Share dispatch (share/router.py:81-92):**
```python
if stl_for_preview is not None:
    existing_preview_count = session.exec(
        select(func.count()).select_from(ModelFile).where(
            ModelFile.model_id == record.model_id,
            ModelFile.kind == ModelFileKind.stl_preview,
        )
    ).one()
    if existing_preview_count < 4:
        try:
            await request.app.state.arq.enqueue_job(
                "render_stl_previews", str(stl_for_preview)
            )
        except Exception:
            ...
```
BUG: no lock. Two concurrent share-view requests both pass `existing_preview_count < 4` → both enqueue → worker's own count-based check fires AFTER fetch starts → both jobs might commit 4-view sets → 8 duplicate rows.

**Share list (share/router.py:121-126):**
```python
preview_files = session.exec(
    select(ModelFile.id)
    .where(ModelFile.model_id == model.id)
    .where(ModelFile.kind == ModelFileKind.stl_preview)
    .order_by(ModelFile.position.asc(), ModelFile.created_at.asc())
).all()
```
BUG: shows ALL stl_preview rows including stale ones.

### Required changes (paste-ready)

**Worker (`worker.py:195-251` region):**
```python
# Inside render_stl_previews, after fetching stl_row:
if stl_row is None: ...  # existing

stl_sha8 = stl_row.sha256[:8]  # NEW: source-tracking discriminator
# Story 23.2 (TB-034 P2#1) — count only previews from CURRENT STL.
# Without the original_name LIKE filter, post-STL-replace would skip
# render because the 4 OLD rows from the prior STL would count.
existing_count = session.exec(
    select(func.count()).select_from(ModelFile).where(
        ModelFile.model_id == stl_row.model_id,
        ModelFile.kind == ModelFileKind.stl_preview,
        ModelFile.original_name.like(f"%-{stl_sha8}.png"),  # NEW
    )
).one()
if existing_count >= len(VIEW_NAMES):
    ...  # existing skip path

# ... existing render ...

new_file = ModelFile(
    ...,
    original_name=f"{view}-{stl_sha8}.png",  # NEW: was f"{view}.png"
    ...
)
```

**Share router dispatch (router.py:73-98 region):**
```python
# Expand the existing query to also fetch sha256
stl_row = session.exec(
    select(ModelFile.id, ModelFile.sha256)
    .where(
        ModelFile.model_id == record.model_id,
        ModelFile.kind == ModelFileKind.stl,
    )
    .order_by(ModelFile.created_at.asc())
).first()
if stl_row is not None:
    stl_for_preview, stl_sha256 = stl_row[0], stl_row[1]
    stl_sha8 = stl_sha256[:8]
    existing_preview_count = session.exec(
        select(func.count()).select_from(ModelFile).where(
            ModelFile.model_id == record.model_id,
            ModelFile.kind == ModelFileKind.stl_preview,
            ModelFile.original_name.like(f"%-{stl_sha8}.png"),  # NEW
        )
    ).one()
    if existing_preview_count < 4:
        # Story 23.2 (TB-034 P2#2) — single-flight lock prevents
        # concurrent dispatches from enqueueing duplicate render jobs.
        lock_key = f"share:stl_preview_lock:{stl_for_preview}"
        acquired = await request.app.state.redis.set(lock_key, "1", nx=True, ex=300)
        if acquired:
            try:
                await request.app.state.arq.enqueue_job(
                    "render_stl_previews", str(stl_for_preview)
                )
            except Exception:
                # If enqueue fails AFTER lock acquired, release immediately
                # so the next request can retry without waiting 300s.
                await request.app.state.redis.delete(lock_key)
                logging.getLogger("app.share").warning(
                    "stl_preview enqueue failed in resolve_share", exc_info=True
                )
        # else: another dispatch in flight, skip silently
```

**Share router list (router.py:121-126 region):**
```python
# Need stl_sha8 in scope here (compute once at top of resolve_share OR
# recompute from the primary STL row).
preview_files = session.exec(
    select(ModelFile.id)
    .where(ModelFile.model_id == model.id)
    .where(ModelFile.kind == ModelFileKind.stl_preview)
    .where(ModelFile.original_name.like(f"%-{stl_sha8}.png"))  # NEW
    .order_by(ModelFile.position.asc(), ModelFile.created_at.asc())
).all()
```
If primary STL doesn't exist (e.g. share view on a model without STL), `stl_sha8` is None and `preview_files` is empty — current behavior preserved.

**Worker lock release (worker.py:307-311 region):**
```python
try:
    ...  # existing render logic
except Exception as exc:
    ...  # existing exception path
finally:
    # Story 23.2 (TB-034 P2#2) — release single-flight dispatch lock so
    # the next share-view hit can re-enqueue if needed (e.g. STL replace
    # post-this-render, or worker crashed mid-render).
    try:
        await redis.delete(f"share:stl_preview_lock:{model_file_id}")
    except Exception:
        # Lock cleanup best-effort; 300s TTL is the safety net
        logger.warning("stl_preview lock release failed", exc_info=True)
```

### Legacy stl_preview rows (no sha8 suffix)

Pre-Story-23.2, existing stl_preview rows have `original_name = "iso.png"` etc (no sha8 suffix). With the new sha8 filter:
- Worker idempotency check: 0 matching previews → renders 4 NEW with sha8 names → DB now has 4 OLD orphan + 4 NEW.
- Share list query: filters to sha8 only → shows ONLY the 4 NEW (good UX).
- Old orphan rows remain in DB but invisible to share view.

Operator can manually cleanup orphan rows via admin DELETE or DB query. Future cleanup task to GC orphan stl_preview rows (where `original_name` not matching any current STL's sha8) tracked as **TB-041 candidate** to be filed at story close-out if operator surfaces concern. Per spec terminus on /share/ UX, this is an acceptable trade-off — no user-visible degradation.

### Lock semantics + race window

The lock is dispatch-side (in share router). Two concurrent share-view requests:
- T0: Request A reads count=0, calls SETNX → acquires lock, enqueues job.
- T0+10ms: Request B reads count=0, calls SETNX → fails (lock held), skips enqueue.
- T0+5s: Worker completes, writes 4 rows, releases lock.
- T0+6s: Request C reads count=4, doesn't even reach SETNX check.

If Request A crashes between SETNX and enqueue_job: the lock is held with 300s TTL, but no job is dispatched. Next request waits up to 300s. Trade-off: slightly degraded UX (rare crash path) vs. complexity of "lock + enqueue atomicity". Acceptable per Init 11-15 precedent (Codex round-2 fix on Story 18.4 had similar trade-off acceptance).

If enqueue_job fails AFTER lock acquired: we explicitly release the lock in the except branch (per fix sketch above).

### Files NOT touched

- `apps/api/app/core/db/models/_entities.py` — `ModelFile` schema unchanged. `original_name` already stores variable-length strings.
- Alembic migrations — no schema change.
- FE `apps/web/src/routes/share/$token.tsx` — unaware of the change; consumes whatever stl_preview URLs the backend returns.

## File List

**MODIFIED (2):**
- `workers/render/render/worker.py` — sha8 in `original_name`, sha8-filter in idempotency count, lock release in finally
- `apps/api/app/modules/share/router.py` — expand primary-STL query to include sha256, sha8-filter in dispatch count + list query, SETNX lock around enqueue

**NEW (1):**
- `apps/api/tests/test_stl_preview_single_flight.py` (or extend `test_share_public.py`) — race-condition + sha256-mismatch tests

**Diff stats expected:**
- ~30-50 LOC modified across worker.py + share/router.py
- ~80-150 LOC new test file
- Net: ~+100-200 LOC

## Verification

| Gate | Command | Pass criterion |
|---|---|---|
| Ruff check | `cd apps/api && uv run ruff check workers/render/render/worker.py app/modules/share/router.py tests/` | Clean |
| Ruff format | `cd apps/api && uv run ruff format --check ...` | Clean |
| Alembic check | `cd apps/api && uv run alembic check` | "No new upgrade operations" |
| Pytest full × 3 | `cd apps/api && timeout 600 uv run pytest -q tests/` × 3 | 866+/866+ PASS deterministic |
| Codex review | `codex review --commit <SHA>` (default gpt-5.5 security class) | CLEAN OR P1/P2 → fix-up cycle |

## References

- [Init 16 SCP §4.2 Story 23.2](sprint-change-proposal-2026-05-24-init16.md#42-epic-e23--share-view-security-hardening) — originating scope.
- [architecture.md § Decision X.2](../planning-artifacts/architecture.md#decision-x--blob-cache-hardening-epic-23--fr16-blob-cache-1--fr16-stl-preview-lock-1) — STL preview source-tracking + single-flight lock decision.
- [prd.md § FR16-STL-PREVIEW-LOCK-1](../planning-artifacts/prd.md#initiative-16--triage-backlog-cleanup-post-init-15-sweep) — verifiable requirement.
- [triage-backlog.md § TB-034](../triage-backlog.md) — Original Codex Story 19.6 round-2 P2 findings.
- Story 19.6 commits: fef96f7 (primary STL preview render task) + 2220581 (round-1 fix-up) — current state of `render_stl_previews` + lazy dispatch glue.
- Memory entries:
  - [[feedback_worker_single_flight]] — Redis SETNX atomic claim pattern.
  - [[feedback_codex_model_routing]] — gpt-5.5 for security/data-integrity class.
  - [[feedback_pytest_timeout]] — `timeout 600 uv run pytest`.
  - [[feedback_share_view_scope_boundary]] — terminus; sha256 boring-tech wins over FK column.

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
