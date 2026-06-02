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
import math
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
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

    # --- Story 32.4 (Decision AJ second half) — status/cost transitions ----------
    #
    # mark_stale / mark_queued / update_cost are deliberate STATUS/COST changes, so they
    # bypass the write() fresh-no-op (which exists only to make an identical fresh re-slice
    # idempotent). Each runs the whole read-modify-publish under the SAME per-record
    # _record_lock the slice persist uses, so a transition and a concurrent slice persist
    # for the same key are serialized — no torn write, no lost transition (AC-1, AC-12).

    def _force_transition(
        self,
        stl_hash: str,
        bundle_hash: str,
        transform: Callable[[EstimateRecord], EstimateRecord | None],
    ) -> EstimateRecord | None:
        """Read-modify-force-publish a transition under the per-record lock.

        ``transform`` receives the existing record and returns the record to publish, or
        ``None`` for an idempotent no-op (the existing record is returned unchanged, with
        no ``computed_at`` churn). A cache miss returns ``None`` WITHOUT building a record
        (never fabricate one to transition). The publish deliberately bypasses the
        ``write()`` fresh-no-op — this IS a deliberate content change.
        """
        if not (is_content_hash(stl_hash) and is_content_hash(bundle_hash)):
            return None
        path = self._record_path(stl_hash, bundle_hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._record_lock(path):
            existing = self._load(path)
            if existing is None:
                return None
            updated = transform(existing)
            if updated is None:
                return existing  # idempotent / no-op transition — left untouched
            self._atomic_publish(path, updated.model_dump_json(indent=2))
            return updated

    def mark_stale(self, stl_hash: str, bundle_hash: str) -> EstimateRecord | None:
        """Supersede a ``fresh`` record to ``stale`` WITHOUT discarding its numbers (AC-1).

        A ``stale`` record is still SERVABLE (FR20-FAILURE-1 "Last estimated HH:MM"): every
        numeric/provenance field and the ORIGINAL ``computed_at`` are preserved. Idempotent
        on an already ``stale``/``queued`` record (no-op, no churn). A ``failed`` record has
        no valid estimate to go stale ⇒ no-op (stays ``failed``); a miss ⇒ ``None``.
        """

        def _to_stale(rec: EstimateRecord) -> EstimateRecord | None:
            if rec.status in (EstimateStatus.stale, EstimateStatus.queued, EstimateStatus.failed):
                return None
            return rec.model_copy(update={"status": EstimateStatus.stale})

        return self._force_transition(stl_hash, bundle_hash, _to_stale)

    def mark_queued(self, stl_hash: str, bundle_hash: str) -> EstimateRecord | None:
        """Mark a ``fresh``/``stale`` record ``queued`` (recompute in flight) — AC-2.

        Still servable (UI shows the last estimate while the recompute runs): numerics +
        original ``computed_at`` preserved. Idempotent on already ``queued``. A ``failed``
        record ⇒ no-op (re-sliced via the normal enqueue, not "queued over a good number");
        a miss ⇒ ``None``.
        """

        def _to_queued(rec: EstimateRecord) -> EstimateRecord | None:
            if rec.status in (EstimateStatus.queued, EstimateStatus.failed):
                return None
            return rec.model_copy(update={"status": EstimateStatus.queued})

        return self._force_transition(stl_hash, bundle_hash, _to_queued)

    def update_cost(
        self, stl_hash: str, bundle_hash: str, *, price_per_gram: float
    ) -> EstimateRecord | None:
        """Cost-only force-publish: ``filament_cost = filament_g x price_per_gram`` (AC-3).

        Changes ONLY ``filament_cost`` + ``computed_at``; every slice-derived field
        (``status``, ``time_seconds``, ``filament_g``/``mm``/``cm3``, ``settings_ids``,
        ``warnings``, ``orca_version``) is preserved — the slice OUTPUT is not invalidated by
        a price change (OD-7). The cost is computed from the UNDER-LOCK ``filament_g`` so it
        is always consistent with the persisted mass. A ``failed`` record or one whose
        ``filament_g`` is ``None`` ⇒ no-op (a failure has no mass to cost — never fabricate a
        cost onto it); a miss ⇒ ``None``. ``price_per_gram`` finiteness/sign is the caller's
        guard (``recompute.recompute_cost_only``); the resulting cost is finite-checked here
        as the no-silent-nan/inf backstop.
        """

        def _set_cost(rec: EstimateRecord) -> EstimateRecord | None:
            if rec.status == EstimateStatus.failed or rec.filament_g is None:
                return None
            new_cost = rec.filament_g * price_per_gram
            if not math.isfinite(new_cost):
                raise ValueError("recomputed cost must be finite (never nan/inf)")
            return rec.model_copy(update={"filament_cost": new_cost, "computed_at": _now_iso()})

        return self._force_transition(stl_hash, bundle_hash, _set_cost)

    def iter_stl_estimates(self, stl_hash: str) -> Iterator[EstimateRecord]:
        """Yield every persisted bundle-variant estimate under one ``<stl_hash>/`` dir (AC-6).

        The sibling set a bundle re-tune touches — enumerable WITHOUT a full scan thanks to
        the Story 32.3 ``<stl_hash[:2]>/<stl_hash>/<bundle_hash>.json`` layout. Path-safe (the
        ``stl_hash`` is gated before any path is built); a malformed hash / missing dir yields
        nothing (never raises). Skips the ``.lock``/``.tmp`` hidden sidecars (only ``*.json``).
        """
        if not is_content_hash(stl_hash):
            return
        stl_dir = self._root / _ESTIMATES_SUBDIR / stl_hash[:_FANOUT_PREFIX_LEN] / stl_hash
        if not stl_dir.is_dir():
            return
        for path in sorted(stl_dir.iterdir()):
            if path.is_file() and path.name.endswith(".json") and not path.name.startswith("."):
                record = self._load(path)
                if record is not None:
                    yield record

    def iter_all_estimates(self) -> Iterator[EstimateRecord]:
        """Walk the whole ``estimates/`` subtree (the Orca-upgrade bulk set) — AC-6.

        Only ``*.json`` records; skips the hidden lock/``.tmp`` sidecars. Deterministic order
        (sorted) so a bulk iteration is reproducible (AC-12). An empty/absent store yields
        nothing. The CALLER decides which subset to act on + ``log()``s the count (NFR20-OBS-1).
        """
        base = self._root / _ESTIMATES_SUBDIR
        if not base.is_dir():
            return
        for path in sorted(base.rglob("*.json")):
            if path.is_file() and not path.name.startswith("."):
                record = self._load(path)
                if record is not None:
                    yield record

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


def _now_iso() -> str:
    """ISO-8601 UTC stamp for a transition's ``computed_at`` re-stamp (Story 32.4 cost path).

    The ONLY non-deterministic field a transition writes — excluded from determinism
    assertions (AC-12), mirroring the worker_job ``_now_iso`` provenance discipline.
    """
    return datetime.now(UTC).isoformat()
