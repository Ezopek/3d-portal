"""Orca profile-resolver subsystem (Epic 32 / Story 32.1, Initiative 20).

Turns Orca's partial, inheritance-based profile tree into CLI-acceptable,
reproducible slice inputs (Decision AH, architecture.md § Initiative 20):

    read (vendored) → merge (inheritance, user-wins) → normalize (inject type,
    drop instantiation) → override (Spoolman seam) → validate (CLI seam) →
    hash (canonical bundle_hash) → snapshot + persist (append-only store).

Module map:

* ``models``       — Pydantic shapes + typed resolve result/failure.
* ``merge``        — pure recursive inheritance merge + CLI normalize.
* ``resolver``     — hash + precedence orchestration + the settings entry point.
* ``overrides``    — Spoolman override-layer seam (no-op default until Story 32.5).
* ``validation``   — CLI-acceptance validator seam + Orca smoke-command spec.
* ``bundle_store`` — append-only hash-fanout bundle + snapshot store.

This story mounts NO HTTP route, adds NO Alembic migration, and runs NO real Orca
binary (the slicer-worker container is Story 32.2 per OD-2). The hash path is pure
and deterministic (NFR20-DETERMINISM-1).
"""

from __future__ import annotations
