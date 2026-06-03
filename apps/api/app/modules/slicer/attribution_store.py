"""SPOOL-PREQ-1 — Spoolman filament reverse index + intent attribution.

The THIRD append-only file-store sidecar in the slicer module (after ``bundle_store``
and ``estimate_store``), deliberately mirroring their hash-fanout + atomic-publish
discipline — a JSON store on the ``portal-content`` volume, NOT an Alembic table.
Layout::

    <root>/attribution/<ref_hash[:2]>/<ref_hash>.json

**Why this exists (the SPOOL-EVT-1 unblock).** SPOOL-EVT-1 (live Spoolman
invalidation) needs to answer: *given a Spoolman filament change, which
``(stl_hash, bundle_hash)`` estimate records are affected?* The Story 32.5 dispatch
``apply_spoolman_filament_change`` already takes a single ``intent`` plus a
caller-supplied ``affected_keys`` set, but nothing persisted links a Spoolman
``spoolman_filament_ref`` back to the intents/bundles it produced —
``SlicerProfileBundle.spoolman_overrides_ref`` is only a fingerprint of mapped
override *values*, never a filament ref. ``resolve()`` is the ONLY point where the
intent's ``spoolman_filament_ref`` and the resulting ``bundle_hash`` are
simultaneously in scope (``stl_hash`` is not — resolve is geometry-independent), so
this store is written there. :func:`lookup_affected_keys` then joins the persisted
``ref → {(intent, bundle_hash)}`` index with the existing ``EstimateStore`` iteration
to derive the affected ``(stl_hash, bundle_hash)`` keys SPOOL-EVT-1 feeds back in.

**Append-only contract.** Recording is additive: an entry that already exists is an
idempotent no-op (the prior file is left byte-for-byte untouched); a new entry is
merged into the deterministically-sorted set and re-published atomically. Existing
entries are never mutated or deleted — provenance accrues.

**Privacy.** Only the portal-owned ``PrintIntentPreset`` is stored as intent context;
it carries NO Orca internals and NO raw override values, so the record is frontend-safe
by construction. The raw ``spoolman_filament_ref`` (which carries a ``\x1f`` separator
and arbitrary vendor text) is NOT path-safe, so the on-disk filename is its sha256 and
the raw ref round-trips inside the record body.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from app.modules.slicer.estimate_store import EstimateStore
from app.modules.slicer.models import PrintIntentPreset

# Hash-prefix fan-out length: the first 2 hex chars of the ref hash become an
# intermediate directory, because "hash-prefix fan-out mirrors bundle_store/estimate_store
# (Decision AI/AH/AJ) to bound per-directory entry count" — the same contract, not an
# arbitrary value.
_FANOUT_PREFIX_LEN = 2

_ATTRIBUTION_SUBDIR = "attribution"


class AttributionEntry(BaseModel):
    """One ``(intent, bundle_hash)`` pin under a filament ref.

    Frozen so a set-membership dedup is well-defined (``PrintIntentPreset`` is itself
    ``frozen=True`` and hashable). Two intents that share a ref (e.g. differing only in
    ``quality_tier``) resolve to two DIFFERENT ``bundle_hash``es, so the pair — not the
    ref alone — is the unit of attribution.
    """

    model_config = ConfigDict(frozen=True)

    intent: PrintIntentPreset
    bundle_hash: str


class AttributionRecord(BaseModel):
    """The persisted reverse-index record for one ``spoolman_filament_ref``.

    ``spoolman_filament_ref`` is the RAW ref (round-tripped from the body, never the
    on-disk hash). ``entries`` is deterministically sorted so the record is reproducible
    regardless of insertion order.
    """

    spoolman_filament_ref: str
    entries: list[AttributionEntry]


class AffectedGroup(BaseModel):
    """A lookup result group: one pinning intent, its bundle, and the affected keys.

    ``affected_keys`` is the set of ``(stl_hash, bundle_hash)`` estimate keys persisted
    for ``bundle_hash`` — the exact ``affected_keys`` shape
    ``apply_spoolman_filament_change`` consumes. Empty when the bundle has no estimate
    yet (the pin is known, no estimate has been computed against it).
    """

    intent: PrintIntentPreset
    bundle_hash: str
    affected_keys: list[tuple[str, str]]


def _entry_sort_key(entry: AttributionEntry) -> tuple[str, str]:
    # Deterministic, insertion-order-independent. ``bundle_hash`` is unique within a record
    # (``record()`` dedups by it), so it alone is already a total order; the canonical intent
    # JSON is kept as a defensive tiebreaker only.
    return (entry.bundle_hash, entry.intent.model_dump_json())


@runtime_checkable
class AttributionSink(Protocol):
    """The write interface the resolver consumes (mirrors ``OverrideProvider``)."""

    def record(self, ref: str, intent: PrintIntentPreset, bundle_hash: str) -> None:
        """Persist that ``intent`` (pinning ``ref``) resolved to ``bundle_hash``."""
        ...


class NoopAttributionSink:
    """Default no-op sink — records nothing (the path until a sink is wired in)."""

    def record(self, ref: str, intent: PrintIntentPreset, bundle_hash: str) -> None:
        return None


class AttributionStore:
    """Append-only filesystem reverse index, keyed by ``spoolman_filament_ref``."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    # --- path helpers -----------------------------------------------------------

    @staticmethod
    def _ref_hash(ref: str) -> str:
        # sha256 of the raw ref → a 64-hex, path-safe filename. The raw ref (with its
        # \x1f separator + arbitrary vendor text) must never reach the filesystem.
        return hashlib.sha256(ref.encode("utf-8")).hexdigest()

    def _record_path(self, ref: str) -> Path:
        ref_hash = self._ref_hash(ref)
        prefix = ref_hash[:_FANOUT_PREFIX_LEN]
        return self._root / _ATTRIBUTION_SUBDIR / prefix / f"{ref_hash}.json"

    # --- read -------------------------------------------------------------------

    def load(self, ref: str) -> AttributionRecord | None:
        return self._load(self._record_path(ref))

    @staticmethod
    def _load(path: Path) -> AttributionRecord | None:
        if not path.exists():
            return None
        return AttributionRecord.model_validate_json(path.read_text(encoding="utf-8"))

    # --- write (the AttributionSink contract) -----------------------------------

    def record(self, ref: str, intent: PrintIntentPreset, bundle_hash: str) -> None:
        """Additively merge ``(intent, bundle_hash)`` into ``ref``'s record (AC).

        **Dedup unit is ``bundle_hash``, not the whole intent.** Within one ref's record
        the ref is fixed and ``bundle_hash`` already subsumes every resolve-determining
        input (material_class / quality_tier / printer_ref via the resolved triple, plus
        the Spoolman override fingerprint), so one stored intent per ``bundle_hash``
        suffices for SPOOL-EVT-1 to re-resolve. Keying on ``bundle_hash`` keeps
        resolve-IRRELEVANT, UI-ish fields (``notes`` / ``is_default``) from bloating the
        index with duplicate pins that would make :func:`lookup_affected_keys` emit
        redundant groups for one bundle.

        Idempotent: a ``bundle_hash`` already present leaves the file byte-for-byte
        untouched (append-only, no clock/churn — the first intent for a bundle wins). A new
        ``bundle_hash`` is merged and the whole entry list re-sorted (one code path, so the
        deterministic-order contract holds regardless of how many entries pre-exist) and
        re-published atomically. The read-merge-publish runs under the same per-record
        advisory lock the estimate store uses, so concurrent writers for one ref cannot
        lose an entry.
        """
        new_entry = AttributionEntry(intent=intent, bundle_hash=bundle_hash)
        path = self._record_path(ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._record_lock(path):
            existing = self._load(path)
            prior = list(existing.entries) if existing is not None else []
            if any(e.bundle_hash == new_entry.bundle_hash for e in prior):
                return  # idempotent no-op (first intent per bundle wins) — file untouched
            merged = AttributionRecord(
                spoolman_filament_ref=ref,
                entries=sorted([*prior, new_entry], key=_entry_sort_key),
            )
            self._atomic_publish(path, merged.model_dump_json(indent=2))

    # --- internals (mirror estimate_store's lock + atomic publish) --------------

    @staticmethod
    @contextmanager
    def _record_lock(path: Path) -> Iterator[None]:
        """Exclusive advisory lock over the record's read-merge-publish section.

        Taken on a sibling ``.<name>.lock`` sidecar (never the record file, so the atomic
        ``os.replace`` publish is untouched). ``flock`` is per-open-file-description, so it
        serializes writers across processes (the shared ``portal-content`` volume) and
        threads alike. Mirrors ``EstimateStore._record_lock``.
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
        """Atomically (re)publish ``content`` to ``path`` (create or overwrite).

        A concurrent reader never sees a partial file: content is fully written + fsynced
        to a UNIQUE temp file in the target dir, then ``os.replace`` swaps it in atomically
        (POSIX rename). Overwrite is intentional — a merge re-publishes the superset record
        — and is consistent with the estimate store's publish.
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


def lookup_affected_keys(
    ref: str,
    *,
    attribution_store: AttributionStore,
    estimate_store: EstimateStore,
) -> list[AffectedGroup]:
    """Resolve a filament ref to the affected estimate keys, grouped by pinning intent.

    The load-bearing deliverable SPOOL-EVT-1 calls: it composes the persisted reverse
    index (``ref → {(intent, bundle_hash)}``) with the EXISTING ``EstimateStore``
    iteration to derive, per pinning intent, the ``(stl_hash, bundle_hash)`` keys an
    estimate is currently persisted for. The event source then re-resolves each intent
    against the changed filament and calls ``apply_spoolman_filament_change`` per group.

    Deterministic: groups follow the record's sorted entries; ``affected_keys`` are sorted
    ``(stl_hash, bundle_hash)`` pairs. An unknown ref ⇒ ``[]``; a bundle with no estimate
    ⇒ an empty ``affected_keys`` (the pin is known, nothing computed yet); a missing/empty
    estimate store never raises (``iter_all_estimates`` yields nothing).

    Status-agnostic by design: EVERY persisted estimate key for the bundle is returned —
    ``fresh``, ``stale``, ``queued`` AND ``failed`` — so the result is a pure structural
    "what depends on this bundle", not an invalidation decision. The Story 32.4 engine
    ``apply_spoolman_filament_change`` feeds into already guards per status
    (``mark_stale`` / ``update_cost`` no-op on ``failed``), so the over-inclusion costs at
    most idempotent dispatch work, never a wrong write. A caller that logs key counts
    should expect failed/transitional keys included.

    NOTE (deferred perf): the bundle→stl join is a single ``iter_all_estimates`` pass —
    O(all estimates) per changed ref, acceptable at homelab scale. A ``bundle_hash →
    {stl_hash}`` index is the deferred optimization, intentionally NOT built here.
    """
    record = attribution_store.load(ref)
    if record is None:
        return []

    # One pass over the estimate store builds bundle_hash → {stl_hash}; reused for every
    # entry so N pinning intents do not cost N scans.
    bundle_to_stls: dict[str, set[str]] = {}
    for est in estimate_store.iter_all_estimates():
        bundle_to_stls.setdefault(est.bundle_hash, set()).add(est.stl_hash)

    groups: list[AffectedGroup] = []
    for entry in record.entries:
        stls = bundle_to_stls.get(entry.bundle_hash, set())
        affected = sorted((stl, entry.bundle_hash) for stl in stls)
        groups.append(
            AffectedGroup(
                intent=entry.intent, bundle_hash=entry.bundle_hash, affected_keys=affected
            )
        )
    return groups
