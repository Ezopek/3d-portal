"""Story 33.2 (PROFILE-ADMIN-2, Decision AL / OD-2..OD-4) — validated import + publish.

This module is the engine half of the admin profile-import write path: it reuses the
Story 32.1 ``resolve()`` merge/normalize/validate gate VERBATIM to validate an uploaded
intent triple against the REAL vendored system tree (without ever exposing an unvalidated
file to a concurrent resolve), then atomically publishes the validated triple into the
vendored ``intent_path`` plus an on-disk sidecar manifest.

**Defensive-policy reversal (NAMED — Decision AL / OD-2):** the vendored profiles dir is
documented read-only-at-runtime (``config.py`` ``slicer_vendored_profiles_dir`` docstring;
SCP § 2.7). This module is the *single, contained* reversal of that posture for Epic E33 —
the first in-product write into the vendored tree. The reversal is bounded by: validate
BEFORE publish (``validate_import`` runs the full ``resolve()`` gate), atomic publish
(tmp→fsync→rename, never a partial file), and no edit to the append-only bundle/snapshot
store or the system tree (so unrelated ``bundle_hash`` provenance stays byte-stable —
NFR21-PROVENANCE-1). It mirrors how Story 33.1's selector reversal cited EST-DISPLAY-1.

Boundaries respected (slicer/README.md § Boundaries): on-disk JSON only (no DB/Alembic —
OD-4); the import is an UPSERT (atomic in-place overwrite via ``os.rename``), deliberately
NOT the append-only ``os.link`` first-write-wins of ``bundle_store`` — a re-import of a slot
replaces it. ``resolve()`` itself is NOT reshaped.

[Source: architecture.md § Initiative 21 Decision AL; PRD FR21-PROFILE-IMPORT-1 / NFR21-*]
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path, PurePath
from typing import Any, Final

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.models import (
    PrintIntentPreset,
    ResolveOutcome,
    SlicerProfileBundle,
    SourceProfileSnapshot,
)
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.validation import NullCliValidator

# Sidecar manifest schema version — points to the OD-4 sidecar contract v1 (NOT a peer
# value). Bumping it is a manifest-schema migration, owned by a future story.
MANIFEST_VERSION: Final = "1"

# The sidecar manifest lives next to its intent file as ``<quality_tier>.manifest.json``.
_MANIFEST_SUFFIX: Final = ".manifest.json"

# The three partial kinds an intent triple must carry — the SAME shape gate ``resolve()``
# applies (resolver.py malformed-partial gate). Mirrored here so a malformed UPLOAD is
# rejected as ``invalid_partial`` before any compatibility/resolve work (AC-6).
_REQUIRED_KINDS: Final[tuple[str, ...]] = ("machine", "process", "filament")

# A safe ``printer_ref`` is a SINGLE path segment: a lowercase-alnum start then alnum/``._-``
# only. ``printer_ref`` is the one attacker-controlled component joined into the on-disk
# ``intent_path`` (``material_class`` / ``quality_tier`` are ``Literal``-validated enums), so
# the write path MUST constrain it: this pattern rejects every path separator (``/`` ``\``),
# parent reference (``..`` — fails the alnum-start anchor), absolute path (leading ``/``),
# leading dot, and whitespace, which are the path-traversal vectors against ``<root>/intents``.
_PRINTER_REF_RE: Final = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


_CONTROL_CHARS_RE: Final = re.compile(r"[\x00-\x1f\x7f]")
_PERCENT_ESCAPE_RE: Final = re.compile(r"%[0-9A-Fa-f]{2}")
_MAX_ORIGINAL_FILENAME_CHARS: Final = 128


def sanitize_original_filename(filename: str | None) -> str:
    """Return a short basename-only filename safe for manifest/audit metadata.

    Multipart ``filename`` is attacker-controlled and may contain local paths, backslashes,
    control characters, or arbitrarily long names. The import keeps only the final path segment,
    replaces control characters, trims whitespace, and caps length. It never stores raw upload
    paths in the sidecar manifest or audit payload.
    """
    if not filename:
        return "profile.json"
    normalized = filename.replace("\\", "/")
    name = PurePath(normalized).name
    name = _CONTROL_CHARS_RE.sub("_", name)
    # Starlette/httpx may percent-encode NUL/control bytes in multipart filenames before the
    # endpoint sees them; keep audit/manifest metadata conservative and basename-only.
    name = _PERCENT_ESCAPE_RE.sub("_", name).strip()
    if not name or name in {".", ".."}:
        return "profile.json"
    if len(name) > _MAX_ORIGINAL_FILENAME_CHARS:
        name = name[:_MAX_ORIGINAL_FILENAME_CHARS]
    return name


def is_safe_printer_ref(printer_ref: str) -> bool:
    """True when ``printer_ref`` is a single safe path segment (no traversal/separator/absolute).

    Defense for the import WRITE path: ``intent_path`` joins ``printer_ref`` into the vendored
    tree, so an unconstrained value like ``../../tmp/evil``, ``/etc/x`` or ``a/b`` could escape
    ``<root>/intents``. Rejecting anything outside the conservative single-segment charset
    closes those vectors syntactically; :func:`is_within_intents_root` is the belt-and-braces
    containment check on the resolved path.
    """
    return bool(_PRINTER_REF_RE.match(printer_ref))


def is_within_intents_root(root: Path | str, intent_path: Path) -> bool:
    """True when ``intent_path`` stays at/below ``<root>/intents`` after full resolution.

    Belt-and-braces path-traversal containment for the write path: even if the syntactic
    :func:`is_safe_printer_ref` gate were bypassed, the resolved publish target MUST NOT escape
    the vendored intents subtree. ``Path.resolve()`` collapses any ``..`` so a traversal target
    lands outside ``intents_root`` and is rejected.
    """
    intents_root = (Path(root) / "intents").resolve()
    target = intent_path.resolve()
    return target == intents_root or intents_root in target.parents


def is_valid_triple_shape(partials: object) -> bool:
    """True when ``partials`` is an object carrying dict ``machine``/``process``/``filament``.

    Mirrors the resolver's malformed-partial gate (resolver.py) so the import endpoint can
    reject a non-object / missing-kind / non-dict-kind payload as ``invalid_partial`` (AC-6)
    before the compatibility or structural-resolve gates run.
    """
    return isinstance(partials, dict) and all(
        isinstance(partials.get(kind), dict) for kind in _REQUIRED_KINDS
    )


def _same_slot(a: PrintIntentPreset, b: PrintIntentPreset) -> bool:
    return (a.printer_ref, a.material_class, a.quality_tier) == (
        b.printer_ref,
        b.material_class,
        b.quality_tier,
    )


class StagedProfileSource(VendoredProfileSource):
    """A ``VendoredProfileSource`` that serves ONE uploaded triple from memory (AC-7).

    Inherits ``system_tree()`` / ``system_tree_hash()`` / ``intent_path()`` from the REAL
    vendored root, so ``resolve()`` validates the uploaded partials against the real system
    profiles — but overrides ``intent_partials`` / ``has_intent`` for the staged slot to
    return the in-memory upload, so validation NEVER reads (or requires) a live file at
    ``intent_path``. This is the "validate-from-payload, no live-tree exposure" mechanism:
    ``resolve()`` is reused verbatim and the live ``intent_path`` is never written until
    validation has already succeeded (the discouraged write-then-rollback fallback would
    transiently expose an unvalidated file to a concurrent resolve).
    """

    def __init__(
        self, root: Path | str, *, staged_partials: dict, staged_intent: PrintIntentPreset
    ) -> None:
        super().__init__(root)
        self._staged_partials = staged_partials
        self._staged_intent = staged_intent

    def has_intent(self, intent: PrintIntentPreset) -> bool:
        if _same_slot(intent, self._staged_intent):
            return True
        return super().has_intent(intent)

    def intent_partials(self, intent: PrintIntentPreset) -> dict | None:
        if _same_slot(intent, self._staged_intent):
            return self._staged_partials
        return super().intent_partials(intent)


class _NoPersistBundleStore(BundleStore):
    """A ``BundleStore`` that neither reads nor writes the live append-only artifacts.

    Validation must (a) never append a bundle/snapshot to the live store (NFR21-PROVENANCE-1
    — the validation path is non-mutating) and (b) always run the FULL required-key + CLI
    gate rather than short-circuiting on a pre-existing content hit. ``load_bundle`` →
    ``None`` forces the full gate; the two write methods are no-ops returning the path the
    real store WOULD use. Mirrors the read-path ``_ReadOnlyBundleStore`` in estimate_read.py.
    """

    def load_bundle(self, bundle_hash: str) -> None:
        return None

    def write_bundle(self, bundle: SlicerProfileBundle) -> Path:
        return self.bundle_path(bundle.bundle_hash)

    def write_snapshot(self, snapshot: SourceProfileSnapshot) -> Path:
        return self.snapshot_path(snapshot.snapshot_hash)


def validate_import(
    partials: dict,
    intent: PrintIntentPreset,
    *,
    real_root: Path | str,
    orca_version: str,
) -> ResolveOutcome:
    """Validate the uploaded ``partials`` for ``intent`` by reusing ``resolve()`` verbatim.

    Builds a :class:`StagedProfileSource` over the real vendored ``real_root`` (so the merge
    validates against the real system tree) and a :class:`_NoPersistBundleStore` (so the
    live append-only store is never touched), then calls the Story 32.1 ``resolve()`` with
    the default ``NullCliValidator`` + ``NoopOverrideProvider``. Returns the resolver's typed
    ``ResolveOutcome`` — a ``ResolveSuccess`` means structurally resolvable; a
    ``ResolveFailure`` carries the classified ``ResolveReason`` the endpoint maps to a 422.
    NOTHING is written: not the live ``intent_path``, not the bundle store, not the system
    tree (AC-7, AC-11 validation-path-no-write).
    """
    source = StagedProfileSource(real_root, staged_partials=partials, staged_intent=intent)
    store = _NoPersistBundleStore(real_root)
    return resolve(
        intent,
        source=source,
        store=store,
        override_provider=NoopOverrideProvider(),
        validator=NullCliValidator(),
        orca_version=orca_version,
    )


def build_manifest(
    *,
    portal_label: str | None,
    imported_by: uuid.UUID,
    imported_at: str,
    original_filename: str,
    compatible: bool,
    compat_reason: str | None,
    source_system_tree_hash: str,
    orca_version: str,
) -> dict[str, Any]:
    """Build the OD-4 sidecar manifest v1 (AC-9).

    Records import metadata + a POINT-IN-TIME snapshot of the compatibility verdict at import
    time. The ``compatibility`` block is informational/audit history — it is NOT a second
    compatibility SoT and never shadows the live ``compatibility.py`` code map (AC-10).
    """
    return {
        "manifest_version": MANIFEST_VERSION,
        "portal_label": portal_label,
        "imported_by": str(imported_by),
        "imported_at": imported_at,
        "original_filename": original_filename,
        "status": "published",
        "compatibility": {"compatible": compatible, "reason": compat_reason},
        "provenance": {
            "source_system_tree_hash": source_system_tree_hash,
            "orca_version": orca_version,
        },
    }


def manifest_path_for(intent_path: Path) -> Path:
    """The sidecar manifest path next to ``intent_path`` (single source of the layout)."""
    return intent_path.with_name(intent_path.stem + _MANIFEST_SUFFIX)


def snapshot_published_intent(intent_path: Path) -> tuple[bytes | None, bytes | None]:
    """Capture the live intent+manifest bytes for a rollback outside ``publish_intent``.

    Used by the HTTP endpoint to undo a successful on-disk publish if a later required
    side-effect (currently the audit row) fails. ``None`` means the file did not exist.
    """
    manifest_path = manifest_path_for(intent_path)
    return (
        intent_path.read_bytes() if intent_path.exists() else None,
        manifest_path.read_bytes() if manifest_path.exists() else None,
    )


def restore_published_intent(
    intent_path: Path, previous_intent: bytes | None, previous_manifest: bytes | None
) -> None:
    """Restore/remove the live intent+manifest pair to a prior snapshot.

    This is the post-publish companion to ``publish_intent``: if the endpoint publishes
    successfully but a required later side-effect fails, restore the prior pair so the request
    cannot return 500 while leaving an unaudited profile live on disk.
    """
    manifest_path = manifest_path_for(intent_path)
    _restore_or_remove(manifest_path, previous_manifest)
    _restore_or_remove(intent_path, previous_intent)


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _nearest_existing_ancestor(path: Path) -> Path | None:
    current = path
    while not current.exists():
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return current


def _metadata_source_for(target: Path, template: Path | None = None) -> Path | None:
    """Choose a live path whose owner/mode the temp publish should inherit.

    ``mkstemp`` creates ``0600`` files owned by the container user (root in production). If we
    rename that straight into the host-mounted vendored tree, operator/host tooling loses read
    access. Preserve an existing target's metadata, or inherit from a staged/committed template
    (for sidecars). Otherwise use the nearest existing ancestor so a fresh ``library/<type>``
    subtree inherits the bind-mounted vendored tree's operator-friendly owner/group instead of
    the container root user that created the new directories.
    """
    if target.exists():
        return target
    if template is not None and template.exists():
        return template
    return _nearest_existing_ancestor(target.parent)


def _file_mode_from_source(source: Path) -> int:
    mode = source.stat().st_mode & 0o777
    if source.is_dir():
        # A directory's execute bits mean traversal, not file executability. For fresh files,
        # inherit read/write bits only: e.g. vendored dir 0775 -> file 0664.
        mode &= 0o666
        return mode or 0o644
    return mode


def _apply_metadata(tmp_path: Path, source: Path | None) -> None:
    if source is None:
        return
    stat = source.stat()
    os.chmod(tmp_path, _file_mode_from_source(source))
    # Non-root dev/test environments may not be allowed to chown. The chmod still avoids
    # mkstemp's 0600 default; production containers run as root and preserve ownership too.
    with suppress(PermissionError):
        os.chown(tmp_path, stat.st_uid, stat.st_gid)


def _apply_dir_metadata(path: Path, source: Path | None) -> None:
    if source is None:
        return
    stat = source.stat()
    mode = stat.st_mode & 0o777
    if not source.is_dir():
        # File -> directory fallback: add traversal bits for every readable class.
        mode = (mode | ((mode & 0o444) >> 2)) & 0o777
    os.chmod(path, mode)
    with suppress(PermissionError):
        os.chown(path, stat.st_uid, stat.st_gid)


def _ensure_parent_dir(target: Path) -> None:
    parent = target.parent
    if parent.exists():
        return
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    source = current
    parent.mkdir(parents=True, exist_ok=True)
    for directory in reversed(missing):
        _apply_dir_metadata(directory, source)


def _stage_temp(target: Path, content: bytes, *, template: Path | None = None) -> Path:
    """Write ``content`` to a unique temp sibling of ``target`` (fsynced); return the temp path.

    The temp is fully written + fsynced but NOT yet published — the caller commits it with an
    atomic ``os.rename``. A unique ``.<name>.XXXX.tmp`` sibling means concurrent writers never
    share a temp path; on a write failure the temp is removed before re-raising. The temp's
    owner/mode is normalized before rename so production bind-mount files do not become
    root-owned ``0600`` artifacts after import.
    """
    _ensure_parent_dir(target)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _apply_metadata(tmp_path, _metadata_source_for(target, template))
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path


def _restore_or_remove(path: Path, previous: bytes | None) -> None:
    """Roll ``path`` back to its ``previous`` bytes, or remove it if it didn't exist before.

    The restore re-commit uses the SAME atomic ``os.rename`` of a fsynced temp sibling as the
    forward publish — an UPSERT, unlike the append-only ``bundle_store._atomic_write``.
    """
    if previous is None:
        path.unlink(missing_ok=True)
        return
    os.rename(_stage_temp(path, previous), path)


def publish_pair(
    *,
    primary_path: Path,
    primary_content: bytes,
    sidecar_path: Path,
    sidecar_content: bytes,
) -> None:
    """Rollback-safe atomic publish of a (primary, sidecar) byte pair as one unit.

    POSIX cannot rename two files in one atomic step, so a naive "write primary, then write
    sidecar" leaves a live primary paired with a stale/missing sidecar if the sidecar write
    fails. Instead this stages BOTH files to fsynced temp siblings first, then commits the
    primary then the sidecar; if the sidecar commit fails the just-committed primary is rolled
    back to its PRIOR state (restored bytes on an upsert, removed on a fresh write). So the
    pair is published as a unit: on ANY failure the directory is byte-identical to before the
    call and no temp file is left behind (fallback-review High fix). The sidecar inherits the
    primary's owner/mode (``_metadata_source_for`` template) so a fresh bind-mount pair never
    becomes a root-owned ``0600`` artifact.

    The single two-phase commit shared by the Story 33.2 ``publish_intent`` (grid intent +
    sidecar manifest) and the PROFILE-LIB-1 library block store (block body + curated
    manifest) — one implementation of the rollback contract, no re-implementation (AC-8).
    """
    _ensure_parent_dir(primary_path)

    # Snapshot the prior primary state so a mid-publish failure can roll it back exactly.
    prev_primary = primary_path.read_bytes() if primary_path.exists() else None

    # Stage both payloads to temp siblings BEFORE committing either (no live file touched yet).
    primary_tmp = _stage_temp(primary_path, primary_content)
    try:
        sidecar_tmp = _stage_temp(sidecar_path, sidecar_content, template=primary_tmp)
    except BaseException:
        primary_tmp.unlink(missing_ok=True)
        raise

    # Commit the primary. On failure here nothing was published — clean both temps.
    try:
        os.rename(primary_tmp, primary_path)
    except BaseException:
        primary_tmp.unlink(missing_ok=True)
        sidecar_tmp.unlink(missing_ok=True)
        raise

    # Commit the sidecar. On failure the primary IS already committed → roll it back to the
    # prior state so the pair stays consistent, and drop the sidecar temp.
    try:
        os.rename(sidecar_tmp, sidecar_path)
    except BaseException:
        sidecar_tmp.unlink(missing_ok=True)
        _restore_or_remove(primary_path, prev_primary)
        raise


def publish_intent(partials: dict, *, intent_path: Path, manifest: dict) -> None:
    """Rollback-safe publish of the validated ``partials`` + sidecar ``manifest`` (AC-8, AC-9).

    Delegates to :func:`publish_pair` (the shared two-phase commit): the intent triple is the
    primary, the sidecar manifest is the sidecar. So the (intent, manifest) pair is published
    as a unit — on ANY failure the vendored tree is byte-identical to before the call and no
    temp file is left behind.

    MUST be called only AFTER ``validate_import`` succeeded — a rejected import never reaches
    here, so the tree stays byte-identical on a rejection too.
    """
    publish_pair(
        primary_path=intent_path,
        primary_content=_json_bytes(partials),
        sidecar_path=manifest_path_for(intent_path),
        sidecar_content=_json_bytes(manifest),
    )


def read_manifest_label(intent_path: Path) -> str | None:
    """Read ``portal_label`` from the sidecar manifest next to ``intent_path`` (AC-14).

    Returns ``None`` when no manifest exists (unchanged 33.1 behavior for a slot with no
    manifest) or when the manifest is unreadable/malformed/has no string label. Read-only;
    it does NOT recompute any of the live ``imported`` / ``resolvable`` / ``compatible`` /
    ``offerable`` fields (the manifest is a point-in-time record, not the live SoT — AC-10).
    """
    manifest_path = manifest_path_for(intent_path)
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    label = data.get("portal_label") if isinstance(data, dict) else None
    return label if isinstance(label, str) else None
