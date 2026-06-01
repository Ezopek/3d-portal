"""Append-only on-disk bundle + snapshot store (Story 32.1, AC-6).

Persistence is a hash-fanout JSON store on the ``portal-content`` volume — NOT an
Alembic table (per SCP: "No DB schema; append-only estimate records"). Identity IS
the content hash; writing a hash that already exists is an idempotent no-op, and a
re-tune produces a NEW hash + file while the old file is never mutated or deleted.

Layout mirrors the render/STL hash-fanout shape (Decision AI):

    <root>/bundles/<bundle_hash[:2]>/<bundle_hash>.json
    <root>/snapshots/<snapshot_hash[:2]>/<snapshot_hash>.json
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from app.modules.slicer.models import SlicerProfileBundle, SourceProfileSnapshot

# Hash-prefix fan-out length: the first 2 hex chars of the content hash become an
# intermediate directory, because "hash-prefix fan-out mirrors the render/STL
# cache layout (Decision AI) to bound per-directory entry count" (AC-10).
_FANOUT_PREFIX_LEN = 2

_BUNDLES_SUBDIR = "bundles"
_SNAPSHOTS_SUBDIR = "snapshots"


class BundleStore:
    """Append-only filesystem store for bundles + source snapshots."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    # --- path helpers -----------------------------------------------------------

    def _fanout_path(self, subdir: str, content_hash: str) -> Path:
        prefix = content_hash[:_FANOUT_PREFIX_LEN]
        return self._root / subdir / prefix / f"{content_hash}.json"

    def bundle_path(self, bundle_hash: str) -> Path:
        return self._fanout_path(_BUNDLES_SUBDIR, bundle_hash)

    def snapshot_path(self, snapshot_hash: str) -> Path:
        return self._fanout_path(_SNAPSHOTS_SUBDIR, snapshot_hash)

    # --- bundles ----------------------------------------------------------------

    def has_bundle(self, bundle_hash: str) -> bool:
        return self.bundle_path(bundle_hash).exists()

    def load_bundle(self, bundle_hash: str) -> SlicerProfileBundle | None:
        path = self.bundle_path(bundle_hash)
        if not path.exists():
            return None
        return SlicerProfileBundle.model_validate_json(path.read_text(encoding="utf-8"))

    def write_bundle(self, bundle: SlicerProfileBundle) -> Path:
        """Idempotently persist ``bundle``. Re-writing an existing hash is a no-op.

        The first write wins — an existing file (e.g. with an earlier
        ``created_at``) is never mutated, preserving append-only provenance.
        """
        path = self.bundle_path(bundle.bundle_hash)
        if path.exists():
            return path
        return self._atomic_write(path, bundle.model_dump_json(indent=2))

    # --- snapshots --------------------------------------------------------------

    def has_snapshot(self, snapshot_hash: str) -> bool:
        return self.snapshot_path(snapshot_hash).exists()

    def load_snapshot(self, snapshot_hash: str) -> SourceProfileSnapshot | None:
        path = self.snapshot_path(snapshot_hash)
        if not path.exists():
            return None
        return SourceProfileSnapshot.model_validate_json(path.read_text(encoding="utf-8"))

    def write_snapshot(self, snapshot: SourceProfileSnapshot) -> Path:
        """Idempotently persist ``snapshot`` (first write wins)."""
        path = self.snapshot_path(snapshot.snapshot_hash)
        if path.exists():
            return path
        return self._atomic_write(path, snapshot.model_dump_json(indent=2))

    # --- internals --------------------------------------------------------------

    @staticmethod
    def _atomic_write(path: Path, content: str) -> Path:
        """Append-only, first-write-wins publish of ``content`` to ``path``.

        Concurrency contract (review fix #4):

        - the temp file is UNIQUE per writer (``tempfile.mkstemp`` in the target
          directory) — two concurrent writers never share a tmp path and so never
          clobber each other mid-write (the old shared ``<hash>.json.tmp`` raced);
        - the publish step is ``os.link`` onto the final path, which is atomic and
          raises ``FileExistsError`` if the path already exists. So the FIRST
          writer wins and a later writer — including one that raced past the
          ``exists()`` pre-check — NEVER overwrites an already-published bundle,
          preserving append-only provenance even under that race (the old
          ``tmp.replace(path)`` silently overwrote).

        A concurrent reader never sees a partial file because the content is fully
        written + fsynced to the unique tmp before the atomic link publishes it.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            # ``os.link`` raises ``FileExistsError`` if another writer published this
            # hash first — suppressing it keeps theirs (first-write-wins; identity IS
            # the content hash, so theirs is byte-equivalent anyway).
            with contextlib.suppress(FileExistsError):
                os.link(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return path
