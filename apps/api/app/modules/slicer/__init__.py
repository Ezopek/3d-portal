"""Orca profile-resolver subsystem (Epic 32 / Story 32.1, Initiative 20).

Turns Orca's partial, inheritance-based profile tree into CLI-acceptable,
reproducible slice inputs (Decision AH, architecture.md § Initiative 20):

    read (vendored) → merge (inheritance, user-wins) → normalize (inject type,
    drop instantiation) → override (Spoolman seam) → validate (CLI seam) →
    hash (canonical bundle_hash) → snapshot + persist (append-only store).

Module map:

* ``models``       — Pydantic shapes + typed resolve/slice result/failure.
* ``merge``        — pure recursive inheritance merge + CLI normalize.
* ``resolver``     — hash + precedence orchestration + the settings entry point.
* ``overrides``    — Spoolman override-layer seam (no-op default until Story 32.5).
* ``validation``   — CLI-acceptance validator seam + shared Orca load-flag/argv spec.
* ``bundle_store`` — append-only hash-fanout bundle + snapshot store.

Story 32.2 (Decision AI) adds the headless-Orca slicer worker on top of the resolver:

* ``cli``          — Orca ``--info`` + slice argv builders, timeout-bounded runner, output parse.
* ``stl_cache``    — content-hash STL cache (populate API-side, read-only at the worker).
* ``worker_job``   — the ``slice_estimate`` arq task: load → pre-check → slice → classify → discard.
* ``worker``       — ``SlicerWorkerSettings`` arq entrypoint (dedicated queue + bounded jobs).
* ``enqueue``      — API-side idempotent ``(stl_hash, bundle_hash)`` enqueue.

The package mounts NO HTTP route and adds NO Alembic migration. Real Orca is never
run in CI (the subprocess runner is an injected seam; the real run is configs-side
container + env-gated bench). The resolve/classify paths are pure and deterministic
(NFR20-DETERMINISM-1).
"""

from __future__ import annotations
