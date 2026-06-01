"""Append-only content-addressed estimate cache (Story 32.3, AC-5/AC-6, Decision AJ).

The SECOND append-only file store in the slicer module (after ``bundle_store``),
deliberately mirroring it — a hash-fanout JSON store on the ``portal-content`` volume,
NOT an Alembic table (per SCP: "No DB schema; append-only estimate records"). Layout::

    <root>/estimates/<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json

grouping every bundle-variant estimate for one STL under one ``<stl_hash>/`` dir so Story
32.4 can enumerate the sibling estimates a bundle re-tune invalidates WITHOUT a full scan.

Dedup contract (FR20-CACHE-1, AC-6): writing over an existing **fresh** record is an
idempotent NO-OP (a re-slice of the same part+bundle yields the same numbers; identity is
the content-addressed key + the pinned inputs). Writing over a **failed** (or, post-32.4,
``stale``/``queued``) record DOES replace it — a retry that now parses cleanly must win.
That is why the publish uses an atomic ``os.replace`` (overwrite) rather than the
``bundle_store`` first-write-wins ``os.link``: the bundle store is immutable-forever, but
a failed estimate is a placeholder a clean retry is allowed to supersede.
"""

from __future__ import annotations

import fcntl
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.modules.slicer.models import EstimateRecord, EstimateStatus
from app.modules.slicer.stl_cache import is_content_hash, validate_content_hash

# Hash-prefix fan-out length: the first 2 hex chars of the STL hash become an intermediate
# directory, because "hash-prefix fan-out mirrors stl_cache/bundle_store (Decision AI/AH)
# to bound per-directory entry count" (AC-11).
_FANOUT_PREFIX_LEN = 2

# The store's own subtree under the (shared) content root, because "the (stl_hash,
# bundle_hash) cache key is the complete reproducibility tuple (Decision AJ); grouping by
# stl_hash lets Story 32.4 enumerate the sibling estimates a bundle re-tune invalidates"
# (AC-11). The two-level <stl_hash>/<bundle_hash>.json key layout encodes that tuple.
_ESTIMATES_SUBDIR = "estimates"


class EstimateStore:
    """Append-only filesystem store for typed ``EstimateRecord``s, keyed (stl, bundle)."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def _record_path(self, stl_hash: str, bundle_hash: str) -> Path:
        # Validate BOTH hashes BEFORE either is interpolated into a path, so a
        # malformed/traversal-shaped hash can never escape the store root (the Story 32.2
        # review-fix #2 discipline). Reuses the shared 64-lowercase-hex gate.
        validate_content_hash(stl_hash)
        validate_content_hash(bundle_hash)
        prefix = stl_hash[:_FANOUT_PREFIX_LEN]
        return self._root / _ESTIMATES_SUBDIR / prefix / stl_hash / f"{bundle_hash}.json"

    def read(self, stl_hash: str, bundle_hash: str) -> EstimateRecord | None:
        """Return the cached record for the key, or ``None`` on a miss (never a default).

        A malformed hash is treated as a miss WITHOUT building a path (mirrors
        ``StlCache.read_path`` review-fix #2).
        """
        if not (is_content_hash(stl_hash) and is_content_hash(bundle_hash)):
            return None
        return self._load(self._record_path(stl_hash, bundle_hash))

    @staticmethod
    def _load(path: Path) -> EstimateRecord | None:
        """Read + validate the record at ``path``, or ``None`` if it does not exist."""
        if not path.exists():
            return None
        return EstimateRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def write(self, record: EstimateRecord) -> Path:
        """Persist ``record`` subject to the AC-6 dedup rule; return the record path.

        - existing ``fresh`` record ⇒ idempotent NO-OP (left untouched; ``computed_at``
          differences alone are NOT a change, AC-6);
        - existing ``failed``/``stale``/``queued`` (or no record) ⇒ atomic replace/create.

        The read-decide-publish window is serialized per record under an exclusive file
        lock (``_record_lock``) so the no-op is race-safe: two concurrent writers for the
        same key cannot both observe "no fresh record" and race to publish — once one
        publishes a ``fresh`` record the other observes it and no-ops, preserving the
        original ``computed_at`` (review-fix #3, the TOCTOU between ``read`` and
        ``os.replace``). ``failed``⇒``fresh`` replacement remains allowed.
        """
        path = self._record_path(record.stl_hash, record.bundle_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._record_lock(path):
            existing = self._load(path)
            if existing is not None and existing.status == EstimateStatus.fresh:
                return path
            return self._atomic_publish(path, record.model_dump_json(indent=2))

    @staticmethod
    @contextmanager
    def _record_lock(path: Path) -> Iterator[None]:
        """Hold an exclusive advisory lock over the record's check-then-publish section.

        The lock is taken on a sibling ``.<name>.lock`` sidecar (never the record file
        itself, so the atomic ``os.replace`` publish is untouched) and is held across the
        ``_load`` read + the publish, closing the TOCTOU window (review-fix #3). ``flock``
        is per-open-file-description, so it serializes concurrent writers both across
        processes (the shared ``portal-content`` volume) and across threads. The sidecar is
        left in place between writes — a tiny, hidden, append-only-store-consistent
        artifact (the publish already drops ``.<name>.*.tmp`` siblings in the same dir).
        """
        lock_path = path.parent / f".{path.name}.lock"
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @staticmethod
    def _atomic_publish(path: Path, content: str) -> Path:
        """Atomically publish ``content`` to ``path`` (create or overwrite).

        A concurrent reader never sees a partial file: the content is fully written +
        fsynced to a UNIQUE temp file in the target directory, then ``os.replace`` swaps
        it into place atomically (POSIX rename semantics — the reader sees either the old
        complete file or the new complete file, never a torn write). Overwrite is
        intentional (the failed⇒fresh retry path, AC-6) — distinct from the bundle store's
        first-write-wins link.
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
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
        return path
