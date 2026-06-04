---
title: 'Fix Orca 2.3.2 spaced duration parse (estimate backfill unblock)'
type: 'bugfix'
created: '2026-06-04'
status: 'ready-for-dev'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/apps/api/app/modules/slicer/gcode_parse.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Real OrcaSlicer 2.3.2 sliced g-code is persisted as `failed` / `unparseable_time` even though Orca exits 0 and emits g-code, because `parse_duration_to_seconds` only accepts compact duration tokens (`3h35m47s`) while real Orca emits inter-token spaces (e.g. `2m 35s`). This blocks the runtime estimate backfill (queue item stl_hash=488a748e…, bundle_hash=25b03be5…).

**Approach:** Loosen the duration grammar to tolerate optional whitespace *between* d/h/m/s tokens while preserving every existing rejection (bare numbers, empty, unknown units, out-of-order/duplicate tokens, number↔unit non-adjacency, garbage). Add a real-format regression fixture + tests. Pure-function change only; no worker/store reshape.

## Boundaries & Constraints

**Always:** Keep `parse_duration_to_seconds` / `parse_gcode_metadata` pure and deterministic (no I/O, no clock, no subprocess). Preserve the no-silent-zero contract — any unparseable time still classifies a typed `unparseable_time`. Number↔unit adjacency stays mandatory (`2m`, not `2 m`). Required filament `[mm]`/`[cm3]`/`[g]` fields keep their FATAL-if-absent semantics and the gram-display value stays intact. ruff format/check clean.

**Ask First:** Loosening token *ordering* (currently d→h→m→s only) — out of scope unless real Orca evidence demands it. Allowing whitespace *inside* a token (between number and unit).

**Never:** Do not store/commit full runtime g-code (a minimal synthetic fixture snippet only). Do not touch the live `arq:slicer` queue, deploy, or restart runtime. No changes to worker_job/_classify/run_slice_job, estimate_store, models, routes, Alembic, or frontend.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Spaced real-Orca duration | `"2m 35s"` | `155` | N/A |
| Spaced multi-token | `"3h 35m 47s"` | `12947` | N/A |
| Compact (regression) | `"3h35m47s"` | `12947` | N/A |
| Spaced with days | `"1d 2h 3m 4s"` | `93784` | N/A |
| Bare number | `"3600"` | `None` (no unit) | classified `unparseable_time` upstream |
| Empty / whitespace | `""`, `"   "` | `None` | classified `unparseable_time` upstream |
| Unknown unit | `"3x5"`, `"abc"` | `None` | classified `unparseable_time` upstream |
| Out-of-order tokens | `"35m3h"` | `None` | classified `unparseable_time` upstream |
| Duplicate unit | `"2m3m"` | `None` | classified `unparseable_time` upstream |
| Number↔unit gap | `"2 m"`, `"2m35 s"` | `None` | classified `unparseable_time` upstream |

</frozen-after-approval>

## Code Map

- `apps/api/app/modules/slicer/gcode_parse.py` -- `_DURATION_RE` + `parse_duration_to_seconds` (the only production edit)
- `apps/api/tests/fixtures/slicer/gcode/orca_spaced_duration.gcode` -- NEW minimal synthetic Orca-2.3.2 footer with `2m 35s` normal-mode time + required filament fields
- `apps/api/tests/test_slicer_estimate.py` -- duration unit cases + a full-parse regression over the new fixture

## Tasks & Acceptance

**Execution:**
- [x] `apps/api/tests/fixtures/slicer/gcode/orca_spaced_duration.gcode` -- add synthetic footer: `estimated printing time (normal mode) = 2m 35s` (+ silent-mode sibling) and required `filament used [mm]/[cm3]/[g]` + cost + settings_ids
- [x] `apps/api/tests/test_slicer_estimate.py` -- add RED unit tests for spaced durations (`2m 35s`, `3h 35m 47s`, `1d 2h 3m 4s`) and tightened-rejection tests (`2 m`, `2m35 s`, `35m3h`, `2m3m`); add a full-parse test over the fixture asserting `time_seconds==155` and filament mm/cm3/g + gram value intact
- [x] `apps/api/app/modules/slicer/gcode_parse.py` -- widen `_DURATION_RE` to allow `\s*` between tokens (not within), update the grammar comment + docstring example

**Acceptance Criteria:**
- Given real Orca `2m 35s`, when `parse_duration_to_seconds` runs, then it returns `155` (not `None`).
- Given the new fixture, when `parse_gcode_metadata` runs, then it returns a `ParsedEstimate` with `time_seconds==155` and unchanged `filament_g` parsing (gram-display field intact).
- Given any previously-rejected garbage (bare number, empty, unknown unit, out-of-order, duplicate, number↔unit gap), when parsed, then it still returns `None` → typed `unparseable_time`.
- Given the existing compact-format tests, when re-run, then they still pass (no regression).

## Verification

**Commands:**
- `cd apps/api && uv run pytest tests/test_slicer_estimate.py -q` -- expected: all pass incl. new cases
- `cd apps/api && uv run pytest tests/test_slicer_estimate.py tests/test_slicer_worker.py tests/test_slicer_store.py -q` -- expected: green (parser/worker/store area)
- `cd apps/api && uv run ruff format --check app/modules/slicer/gcode_parse.py tests/test_slicer_estimate.py && uv run ruff check app/modules/slicer tests/test_slicer_estimate.py` -- expected: clean
- `cd apps/api && uv run pytest -q` -- expected: full API suite green (no regression)

**Controller verification (2026-06-04, branch `fix/E32.3-orca-spaced-duration`):**
- Runtime root-cause probe (non-consuming one-shot slicer-worker container on `.190`): real Orca 2.3.2 emitted `estimated printing time = '2m 35s'`; pre-fix parser returned `unparseable_time`.
- Pre-rebase first pass: `uv run pytest tests/test_slicer_estimate.py -q` -> `77 passed in 0.28s`; focused parser/worker/store -> `136 passed in 0.71s`; full API -> `1374 passed, 3 skipped`.
- After rebasing over upstream commit `e3c09df` and tightening whitespace to horizontal-only: `uv run pytest tests/test_slicer_estimate.py tests/test_slicer_worker.py tests/test_slicer_store.py -q` -> `137 passed in 0.84s`.
- `uv run ruff format --check app/modules/slicer/gcode_parse.py tests/test_slicer_estimate.py && uv run ruff check app/modules/slicer tests/test_slicer_estimate.py` -> `2 files already formatted`; `All checks passed!`.
- `uv run pytest -q` -> `1375 passed, 3 skipped, 1552 warnings in 501.96s`.
- `git diff --check` -> clean.
- Independent `laura-gemini-review` focused diff review -> `APPROVE`; two non-blocking minor regex notes only, no requested changes.

**Runtime gate status:** code-side parser fix is verified, but the live backfill is not complete until the controller deploys/rebuilds the slicer-worker overlay, resumes `arq:slicer`, and verifies fresh estimate records/`filament_g` coverage.
