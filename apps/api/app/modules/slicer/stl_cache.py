"""Content-hashed STL cache (Story 32.2, AC-4, Decision AI).

The slicer worker reads the STL mesh from a content-addressed cache:

    <root>/stl/<hash[:2]>/<hash>.stl

The cache is populated **API-side at enqueue** (:meth:`StlCache.populate_from_source`)
by copying the ``.190``-mirrored catalog STL (the portal-content copy at
``models/{model_id}/files/{file_uuid}.stl``) into its content-addressed path. The
worker then only ever **reads** that cache by hash (:meth:`StlCache.read_path`) — it
never touches an external/source host (OD-8 / NFR20-CONTAINER-1). The content hash
is the only STL reference that crosses the arq queue (AC-2); a cache miss is a
classified ``missing_stl`` failure at the worker, never a silent default.

Identity IS the content hash, so a populate of identical bytes is an idempotent
first-write-wins no-op (mirrors the Story 32.1 ``bundle_store`` publish contract).
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import tempfile
from pathlib import Path

# Hash-prefix fan-out length: the first 2 hex chars become an intermediate
# directory, because "hash-prefix fan-out mirrors the render/STL + Story 32.1
# bundle layout (Decision AI) to bound per-directory entry count" (AC-10).
_FANOUT_PREFIX_LEN = 2

_STL_SUBDIR = "stl"

# sha256 over the STL bytes — collision-resistant content identity; the same
# algorithm the render/Story 32.1 stores use (Decision AI).
_HASH_ALGORITHM = "sha256"

_READ_CHUNK = 64 * 1024

# A well-formed content hash is exactly 64 lowercase hex chars, because "that is the
# sha256 hexdigest width every slicer content hash (stl_hash, bundle_hash) is minted
# at (compute_stl_hash / Story 32.1 resolver); validating against it BEFORE any path
# is built guarantees a hash can never carry a separator or `..` and widen into a
# directory-traversal component" (review fix #2). Shared by the STL cache, the worker
# job (bundle_hash guard), and the enqueue helper so the check lives in ONE place.
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def is_content_hash(value: object) -> bool:
    """True iff ``value`` is a well-formed sha256 content hash (64 lowercase hex)."""
    return isinstance(value, str) and _CONTENT_HASH_RE.fullmatch(value) is not None


def validate_content_hash(value: str) -> str:
    """Return ``value`` if it is a well-formed content hash, else raise ``ValueError``.

    Path-safety gate: rejects wrong length, non-hex chars, separators and ``..`` so a
    caller can never build a filesystem path from an untrusted/malformed hash.
    """
    if not is_content_hash(value):
        raise ValueError(f"not a well-formed sha256 content hash: {value!r}")
    return value


def compute_stl_hash(path: Path) -> str:
    """Streaming content hash of an STL file (the ``stl_hash`` job key, AC-2)."""
    digest = hashlib.new(_HASH_ALGORITHM)
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


class StlCache:
    """Content-hashed STL cache rooted at a single settings-sourced directory."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def stl_path(self, stl_hash: str) -> Path:
        # Validate BEFORE interpolating the hash into a path so a malformed hash can
        # never escape the cache root via a separator / `..` (review fix #2).
        validate_content_hash(stl_hash)
        prefix = stl_hash[:_FANOUT_PREFIX_LEN]
        return self._root / _STL_SUBDIR / prefix / f"{stl_hash}.stl"

    def has(self, stl_hash: str) -> bool:
        return is_content_hash(stl_hash) and self.stl_path(stl_hash).exists()

    def read_path(self, stl_hash: str) -> Path | None:
        """Return the cached STL path for ``stl_hash``, or ``None`` on a miss.

        The ONLY input is the content hash — there is no parameter through which an
        external/source-host path could be threaded, so the worker structurally
        cannot read outside this cache (OD-8 / NFR20-CONTAINER-1). A malformed hash
        is treated as a miss (``None``) WITHOUT building a path (review fix #2).
        """
        if not is_content_hash(stl_hash):
            return None
        path = self.stl_path(stl_hash)
        return path if path.exists() else None

    def populate_from_source(self, source_stl: Path) -> str:
        """Copy ``source_stl`` (the mirrored catalog STL) into the cache; return its hash.

        Idempotent first-write-wins: an identical-content STL already present is
        left untouched (identity IS the content hash). Called API-side at enqueue,
        never by the worker.
        """
        source_stl = Path(source_stl)
        stl_hash = compute_stl_hash(source_stl)
        dest = self.stl_path(stl_hash)
        if dest.exists():
            return stl_hash
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Unique temp + atomic link publish: a concurrent reader never sees a partial
        # file, and a racing second writer never clobbers the first (mirrors the
        # Story 32.1 bundle_store._atomic_write contract).
        fd, tmp_name = tempfile.mkstemp(
            dir=str(dest.parent), prefix=f".{dest.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as out, source_stl.open("rb") as src:
                for chunk in iter(lambda: src.read(_READ_CHUNK), b""):
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            with contextlib.suppress(FileExistsError):
                os.link(tmp_path, dest)
        finally:
            tmp_path.unlink(missing_ok=True)
        return stl_hash
