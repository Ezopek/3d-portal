"""PROFILE-LIB-1 (Decision AM) — operator Orca profile-BLOCK inventory engine.

The first surface of the corrected canonical separate-block model (SCP 2026-06-06 § 3):
an additive, operator-facing inventory of SEPARATE Orca profile blocks (machine / process /
filament). This module is the engine half — classifier, curated-metadata extractor,
validation-state derivation, process-inheritance governance, and the on-disk block storage
layer. It is **purely additive**: it does NOT touch ``resolver.py``'s ``resolve()``, the
``intents/`` (grid) layout, the 33.1 inventory read, the 33.2 grid-import endpoint, the
append-only bundle/snapshot/estimate stores, ``bundle_hash``, or ``compatibility.py`` (AC-1).
The grid (33.1/33.2) is the transitional compiled-intent projection and coexists untouched
(SCP § 4).

Storage is on-disk JSON only (no DB/Alembic — SCP § 4 no-DB posture), in a NEW ``library/``
subtree disjoint from the ``system/`` and ``intents/`` trees. Writes reuse the 33.2
rollback-safe two-phase atomic publish + owner/mode preservation (``import_service``) rather
than re-implementing unsafe writes (AC-8).

[Source: architecture.md § Initiative 21 Decision AM; SCP 2026-06-06 § 3/§ 6; PRD FR21-*]
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from app.modules.slicer.import_service import _json_bytes, publish_pair, sanitize_original_filename

ProfileType = Literal["machine", "process", "filament"]
ValidationState = Literal["usable", "requires_attention", "error"]

# Library sidecar-manifest schema version — points to the PROFILE-LIB-1 library-manifest
# contract v1, a NEW schema distinct from the 33.2 intent-manifest v1 (different fields:
# block-curated, not slot-compat). Bumping it is a future manifest-schema migration (AC-6).
LIBRARY_MANIFEST_VERSION: Final = "1"

# The two filenames a stored block owns, under ``<root>/library/<profile_type>/``.
_BLOCK_SUFFIX: Final = ".json"
_MANIFEST_SUFFIX: Final = ".manifest.json"

# A server-derived ``block_id`` is always a 32-char lowercase hex uuid5 hexdigest — no path
# separators, traversal, or attacker control (AC-7). GET/DELETE path params are validated
# against this charset before they are ever joined into a filesystem path.
_BLOCK_ID_RE: Final = re.compile(r"^[0-9a-f]{32}$")

# Namespace for the deterministic ``block_id`` over ``(profile_type, name)`` — uuid5 chosen
# because the id must be (a) PATH-SAFE (structurally closes the 33.2 traversal class) and
# (b) STABLE on re-import of the same named block of the same type (upsert, not a duplicate).
# NOT chosen for brevity (magic-constant discipline, AC-7).
_BLOCK_ID_NAMESPACE: Final = uuid.NAMESPACE_URL

# The three profile types, in the operator-facing default order — **process first** (the slice
# is process-profiles-first, SCP Appendix A.1). Drives deterministic list ordering (AC-10).
PROFILE_TYPE_ORDER: Final[tuple[ProfileType, ...]] = ("process", "filament", "machine")

# Explicit Orca ``type``-field vocabulary → canonical profile type (AC-2 branch a). Confirmed
# from REAL Orca system exports (G-DATA, 2026-06-06): system profiles carry an explicit
# ``type`` ∈ {"machine", "process", "filament"}. ``printer``/``print`` are defensive synonyms
# for the same three; an out-of-table value falls through to the heuristic branch (AC-2b).
_EXPLICIT_TYPE_MAP: Final[dict[str, ProfileType]] = {
    "machine": "machine",
    "printer": "machine",
    "process": "process",
    "print": "process",
    "filament": "filament",
}

# Per-type ``*_settings_id`` keys real Orca USER exports carry (G-DATA): a user process has
# ``print_settings_id``, a user filament ``filament_settings_id``, a user machine
# ``printer_settings_id``. System exports carry a single ``setting_id``. These pin both the
# heuristic classifier (AC-2b) and the curated ``settings_id`` extraction (AC-3).
_SETTINGS_ID_KEY: Final[dict[ProfileType, str]] = {
    "machine": "printer_settings_id",
    "process": "print_settings_id",
    "filament": "filament_settings_id",
}

# Small generic material-category table (SCP § 3.6): keep categories small + aligned. An
# out-of-table ``filament_type`` ⇒ ``material_type=null`` + an ``unknown_material_type`` flag,
# NEVER a minted narrow category. The concrete per-vendor identity is a later override layer.
_MATERIAL_CATEGORIES: Final[frozenset[str]] = frozenset({"PLA", "PETG", "PCTG", "TPU"})

# Machine-discriminating keys for the heuristic branch (AC-2b), verifiable against the bench +
# real exports (``printer_model`` / ``nozzle_diameter`` / ``printable_height`` + the user
# ``printer_settings_id``).
_MACHINE_KEYS: Final[tuple[str, ...]] = (
    "printer_settings_id",
    "printer_model",
    "nozzle_diameter",
    "printable_height",
)
# Process-discriminating keys (``print_settings_id`` for user exports, ``layer_height`` for the
# bench/system shape).
_PROCESS_KEYS: Final[tuple[str, ...]] = ("print_settings_id", "layer_height")

# Validation reason CATEGORIES (machine-readable; the FE localizes them — no display text from
# the backend, AC-4). Exposed for the API/i18n contract + tests.
REASON_UNKNOWN_INHERIT_PARENT: Final = "unknown_inherit_parent"
REASON_USER_PROCESS_INVALID_INHERITANCE: Final = "user_process_invalid_inheritance"
REASON_UNKNOWN_MATERIAL_TYPE: Final = "unknown_material_type"


# === classification (AC-2) ====================================================


def classify_profile(body: object) -> ProfileType | None:
    """Classify a parsed Orca profile block as machine / process / filament, or ``None``.

    Precedence (AC-2): (a) an explicit Orca ``type`` field mapped through
    :data:`_EXPLICIT_TYPE_MAP`; (b) structural heuristics over discriminating keys —
    ``filament_type`` / ``filament_settings_id`` ⇒ filament, machine keys ⇒ machine,
    process keys ⇒ process; (c) ambiguous / none ⇒ ``None`` (the endpoint rejects it
    ``422 unsupported_profile``, nothing stored). Filament is tested first because its keys
    are the most specific; the three ``*_settings_id`` discriminators are mutually exclusive
    in real Orca exports.
    """
    if not isinstance(body, dict):
        return None

    # (a) explicit type field (system exports) — precedence over heuristics.
    explicit = body.get("type")
    if isinstance(explicit, str):
        mapped = _EXPLICIT_TYPE_MAP.get(explicit.strip().lower())
        if mapped is not None:
            return mapped
        # An unrecognised explicit type value is not authoritative — fall through to the
        # heuristic branch rather than guessing.

    # (b) structural heuristics.
    if "filament_type" in body or "filament_settings_id" in body:
        return "filament"
    if any(key in body for key in _MACHINE_KEYS):
        return "machine"
    if any(key in body for key in _PROCESS_KEYS):
        return "process"

    # (c) ambiguous / none.
    return None


# === curated-metadata extraction (AC-3) =======================================


@dataclass(frozen=True)
class CuratedMetadata:
    """The minimized curated metadata of one block — NO raw Orca body (AC-3).

    Carries ONLY the curated fields: ``name``, ``profile_type``, declared ``inherit`` +
    best-effort ``inherit_chain``, ``settings_id``, ``source`` / ``is_system``, and for
    filament blocks ``material_type`` + ``compatible_printers``. It deliberately carries NO
    raw layer-height / temps / volumetric-speed / density / g-code / full Orca key set — the
    same FR20-PRESET-1 / NFR21-OBS-1 leak fence the ``schemas.py`` DTOs enforce. The two
    private flags feed :func:`derive_validation_state`; they are NOT serialized into the DTO.
    """

    name: str
    profile_type: ProfileType
    source: str | None
    is_system: bool
    inherit: str | None
    inherit_chain: list[str]
    settings_id: str | None
    material_type: str | None
    compatible_printers: list[str] = field(default_factory=list)
    # Internal flags (not DTO fields): the declared inherit parent resolved in the system
    # tree, and whether a present ``filament_type`` was out-of-table.
    inherit_parent_known: bool = True
    material_type_unknown: bool = False


def _first_str(value: object) -> str | None:
    """A single string from a scalar or an Orca ``["value"]`` single-element list, else None."""
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, str) and value:
        return value
    return None


def declared_inherit(body: dict) -> str | None:
    """The declared parent name — ``inherits`` (real Orca, plural) or ``inherit`` (bench)."""
    for key in ("inherits", "inherit"):
        parent = body.get(key)
        if isinstance(parent, str) and parent:
            return parent
    return None


def _source_of(body: dict) -> str | None:
    """Normalized ``from`` provenance: ``"system"`` / ``"user"`` / ``None`` (unknown)."""
    raw = body.get("from")
    if not isinstance(raw, str) or not raw.strip():
        return None
    lowered = raw.strip().lower()
    if lowered == "system":
        return "system"
    if lowered == "user":
        return "user"
    return None


def _settings_id_of(body: dict, profile_type: ProfileType) -> str | None:
    """The per-type ``*_settings_id`` (user) else ``setting_id`` (system), or ``None``."""
    typed = _first_str(body.get(_SETTINGS_ID_KEY[profile_type]))
    if typed is not None:
        return typed
    return _first_str(body.get("setting_id"))


def _material_type_of(body: dict) -> tuple[str | None, bool]:
    """Normalize ``filament_type`` to a generic category (AC-9), or flag it unknown.

    Returns ``(material_type, unknown)``: an in-table type ⇒ ``(CATEGORY, False)``; an
    out-of-table type ⇒ ``(None, True)`` (surfaced as ``material_type=null`` + an
    ``unknown_material_type`` flag, never a minted category); no ``filament_type`` at all ⇒
    ``(None, False)`` (nothing to normalize, nothing to flag).
    """
    raw = _first_str(body.get("filament_type"))
    if raw is None:
        return None, False
    upper = raw.strip().upper()
    if upper in _MATERIAL_CATEGORIES:
        return upper, False
    return None, True


def resolve_inherit_chain(
    inherit: str | None, system_tree: dict[str, dict]
) -> tuple[list[str], bool]:
    """Best-effort walk of the inherit chain against ``system_tree`` — never raises (AC-3).

    Returns ``(chain, direct_parent_known)``. The chain starts at the declared parent and
    walks up through ``system_tree`` parents, halting/truncating at the first unknown parent
    or a cycle. ``direct_parent_known`` is whether the DIRECTLY declared parent is present in
    the system tree (the AC-4 ``unknown_inherit_parent`` signal). A ``None`` inherit (a
    self-contained root block) ⇒ ``([], True)`` (nothing declared, nothing to flag).
    """
    if inherit is None:
        return [], True
    chain: list[str] = []
    seen: set[str] = set()
    current: str | None = inherit
    while current is not None and current not in seen:
        seen.add(current)
        chain.append(current)
        parent = system_tree.get(current)
        if parent is None:
            break  # truncate at an unknown parent — never raise
        current = declared_inherit(parent)
    return chain, inherit in system_tree


def extract_curated_metadata(
    body: dict, *, profile_type: ProfileType, system_tree: dict[str, dict]
) -> CuratedMetadata:
    """Extract the minimized curated metadata for a classified block (AC-3).

    Pulls ONLY curated fields and resolves a best-effort inherit chain against the read-only
    vendored ``system_tree`` (reused from ``VendoredProfileSource.system_tree`` — never
    mutated). Carries no raw Orca body. ``material_type`` / ``compatible_printers`` are
    populated for filament blocks only.
    """
    inherit = declared_inherit(body)
    chain, parent_known = resolve_inherit_chain(inherit, system_tree)
    source = _source_of(body)
    material_type: str | None = None
    material_unknown = False
    compatible_printers: list[str] = []
    if profile_type == "filament":
        material_type, material_unknown = _material_type_of(body)
        raw_compat = body.get("compatible_printers")
        if isinstance(raw_compat, list):
            compatible_printers = [p for p in raw_compat if isinstance(p, str) and p]
    return CuratedMetadata(
        name=str(body.get("name") or ""),
        profile_type=profile_type,
        source=source,
        is_system=source == "system",
        inherit=inherit,
        inherit_chain=chain,
        settings_id=_settings_id_of(body, profile_type),
        material_type=material_type,
        compatible_printers=compatible_printers,
        inherit_parent_known=parent_known,
        material_type_unknown=material_unknown,
    )


# === validation-state derivation + governance (AC-4, AC-5) ====================


def _parent_is_system_process(inherit: str | None, system_tree: dict[str, dict]) -> bool:
    """True when ``inherit`` resolves to a SYSTEM process profile in the system tree (AC-5)."""
    if inherit is None:
        return False
    parent = system_tree.get(inherit)
    if not isinstance(parent, dict):
        return False
    if _source_of(parent) != "system":
        return False
    return classify_profile(parent) == "process"


def derive_validation_state(
    curated: CuratedMetadata, *, system_tree: dict[str, dict]
) -> tuple[ValidationState, list[str]]:
    """Map a classified+extracted block to its validation state + reason categories (AC-4/5).

    ``error`` is never produced here — an unclassifiable block is rejected at the endpoint
    (AC-2) and never stored, so a STORED block is at worst ``requires_attention``. The
    precedence of the flags (a block can carry more than one):

    - **AC-5 process-inheritance governance:** a USER process whose ``inherit`` does NOT
      resolve to a system process (a non-system parent, or an unknown one) ⇒
      ``user_process_invalid_inheritance``. Orca may silently DROP an invalid user-process
      inheritance; surfacing it as a visible flag is the whole point (SCP § 3.2). This
      supersedes the generic ``unknown_inherit_parent`` for that case (one reason, not two).
    - **AC-4 unknown inherit parent:** any other block whose declared ``inherit`` is not in
      the system tree ⇒ ``unknown_inherit_parent``.
    - **AC-9 unknown material type:** a filament whose ``filament_type`` is out-of-table ⇒
      ``unknown_material_type``.

    Any reason ⇒ ``requires_attention`` (stored + flagged); none ⇒ ``usable``.
    """
    reasons: list[str] = []
    is_user_process = curated.profile_type == "process" and not curated.is_system
    if is_user_process and not _parent_is_system_process(curated.inherit, system_tree):
        reasons.append(REASON_USER_PROCESS_INVALID_INHERITANCE)
    elif curated.inherit is not None and not curated.inherit_parent_known:
        reasons.append(REASON_UNKNOWN_INHERIT_PARENT)
    if curated.material_type_unknown:
        reasons.append(REASON_UNKNOWN_MATERIAL_TYPE)
    state: ValidationState = "requires_attention" if reasons else "usable"
    return state, reasons


# === block storage layer (AC-6, AC-7, AC-8) ==================================


def derive_block_id(profile_type: ProfileType, name: str) -> str:
    """Server-derived, path-safe, upsert-stable ``block_id`` (32-char hex, AC-7)."""
    return uuid.uuid5(_BLOCK_ID_NAMESPACE, f"{profile_type}:{name}").hex


def is_valid_block_id(block_id: str) -> bool:
    """True when ``block_id`` is a 32-char lowercase hex string (GET/DELETE gate, AC-7)."""
    return bool(_BLOCK_ID_RE.match(block_id))


def library_root(root: Path | str) -> Path:
    """The ``<root>/library`` subtree root (disjoint from ``system/`` and ``intents/``)."""
    return Path(root) / "library"


def block_path(root: Path | str, profile_type: ProfileType, block_id: str) -> Path:
    """The single-SoT on-disk path of a block body (AC-6).

    ``<root>/library/<profile_type>/<block_id>.json``. Mirrors
    ``VendoredProfileSource.intent_path`` as the one place the layout lives, so reads/writes/
    deletes cannot drift. The companion curated manifest sits next to it (``.manifest.json``).
    """
    return library_root(root) / profile_type / f"{block_id}{_BLOCK_SUFFIX}"


def manifest_path(body_path: Path) -> Path:
    """The curated-manifest sidecar path next to a block body."""
    return body_path.with_name(body_path.name[: -len(_BLOCK_SUFFIX)] + _MANIFEST_SUFFIX)


def _assert_within_library(root: Path | str, target: Path) -> None:
    """Belt-and-braces containment: ``target`` must stay at/below ``<root>/library`` (AC-7).

    The server-derived hex ``block_id`` already structurally precludes traversal; this is the
    defense-in-depth assert mirroring 33.2's ``is_within_intents_root``.
    """
    lib_root = library_root(root).resolve()
    resolved = target.resolve()
    if not (resolved == lib_root or lib_root in resolved.parents):
        raise ValueError(f"library block path escapes {lib_root}")


def build_block_manifest(
    curated: CuratedMetadata,
    *,
    block_id: str,
    validation_state: ValidationState,
    reasons: list[str],
    portal_label: str | None,
    imported_by: uuid.UUID,
    imported_at: str,
    original_filename: str,
) -> dict[str, Any]:
    """Build the curated library-manifest sidecar v1 (AC-6, AC-13).

    Holds ONLY curated metadata + import provenance — NO raw Orca key body, NO filesystem
    path, NO g-code (the FR20-PRESET-1 / NFR21-OBS-1 leak fence). It is the single read source
    for the list/get endpoints, so the curated surface can never leak Orca internals.
    """
    return {
        "manifest_version": LIBRARY_MANIFEST_VERSION,
        "block_id": block_id,
        "profile_type": curated.profile_type,
        "name": curated.name,
        "source": curated.source,
        "is_system": curated.is_system,
        "inherit": curated.inherit,
        "inherit_chain": list(curated.inherit_chain),
        "settings_id": curated.settings_id,
        "material_type": curated.material_type,
        "compatible_printers": list(curated.compatible_printers),
        "validation_state": validation_state,
        "reasons": list(reasons),
        "portal_label": portal_label,
        "imported_at": imported_at,
        "imported_by": str(imported_by),
        "original_filename": original_filename,
    }


def store_block(
    root: Path | str,
    *,
    profile_type: ProfileType,
    block_id: str,
    body: dict,
    manifest: dict,
) -> Path:
    """Atomically store a block body + curated manifest (AC-8) — returns the body path.

    Reuses the 33.2 ``publish_pair`` two-phase rollback-safe atomic publish + owner/mode
    preservation VERBATIM (the body is the primary, the curated manifest the sidecar): on ANY
    failure the ``library/`` subtree is byte-identical to before and no temp remains. A
    re-import of the same ``(profile_type, name)`` resolves to the same ``block_id`` ⇒ an
    UPSERT (atomic in-place overwrite), never a duplicate (AC-7).
    """
    body_path = block_path(root, profile_type, block_id)
    _assert_within_library(root, body_path)
    publish_pair(
        primary_path=body_path,
        primary_content=_json_bytes(body),
        sidecar_path=manifest_path(body_path),
        sidecar_content=_json_bytes(manifest),
    )
    return body_path


def snapshot_block(
    root: Path | str, profile_type: ProfileType, block_id: str
) -> tuple[bytes | None, bytes | None]:
    """Capture the live (body, manifest) bytes so a later side-effect failure can roll back.

    Companion to :func:`store_block` for the endpoint's audit-rollback (mirrors the 33.2
    ``snapshot_published_intent``): on a successful store whose audit then fails, the prior
    pair is restored so a request never returns 500 while leaving an unaudited block live.
    ``None`` means the file did not exist before the store (a fresh import).
    """
    body = block_path(root, profile_type, block_id)
    sidecar = manifest_path(body)
    return (
        body.read_bytes() if body.exists() else None,
        sidecar.read_bytes() if sidecar.exists() else None,
    )


def restore_block(
    root: Path | str,
    profile_type: ProfileType,
    block_id: str,
    prev_body: bytes | None,
    prev_manifest: bytes | None,
) -> None:
    """Restore (or remove) a block to a prior snapshot after a post-store failure.

    A fresh import (``prev_body is None``) is undone by deleting the just-stored pair; an
    upsert is rolled back to the prior bytes via the same atomic two-phase publish.
    """
    if prev_body is None:
        delete_block(root, block_id)
        return
    body = block_path(root, profile_type, block_id)
    publish_pair(
        primary_path=body,
        primary_content=prev_body,
        sidecar_path=manifest_path(body),
        sidecar_content=prev_manifest if prev_manifest is not None else b"{}",
    )


def _read_manifest(path: Path) -> dict | None:
    """Read one curated manifest, or ``None`` when missing/unreadable/non-object."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def list_blocks(root: Path | str, *, profile_type: ProfileType | None = None) -> list[dict]:
    """List the curated manifests of stored blocks, deterministically ordered (AC-10).

    Reads ONLY the ``*.manifest.json`` sidecars (never the raw bodies), so the list cannot
    leak Orca internals. Optionally filtered by ``profile_type``. Ordering is deterministic:
    by :data:`PROFILE_TYPE_ORDER` (process first) then by ``name``. A missing/empty
    ``library/`` tree ⇒ an empty list (the empty state IS an empty inventory).
    """
    types = (profile_type,) if profile_type is not None else PROFILE_TYPE_ORDER
    collected: list[dict] = []
    for ptype in types:
        type_dir = library_root(root) / ptype
        if not type_dir.exists():
            continue
        for path in sorted(type_dir.glob(f"*{_MANIFEST_SUFFIX}")):
            manifest = _read_manifest(path)
            if manifest is not None:
                collected.append(manifest)
    type_rank = {ptype: i for i, ptype in enumerate(PROFILE_TYPE_ORDER)}
    collected.sort(
        key=lambda m: (type_rank.get(m.get("profile_type", ""), len(type_rank)), m.get("name", ""))
    )
    return collected


def read_block(root: Path | str, block_id: str) -> dict | None:
    """Read one block's curated manifest by ``block_id`` (AC-11), or ``None`` when absent.

    Scans the three type subdirs (``block_id`` is unique). Returns curated metadata ONLY —
    never the raw Orca body (there is no raw-body read path in this story).
    """
    if not is_valid_block_id(block_id):
        return None
    for ptype in PROFILE_TYPE_ORDER:
        manifest = _read_manifest(manifest_path(block_path(root, ptype, block_id)))
        if manifest is not None:
            return manifest
    return None


def delete_block(root: Path | str, block_id: str) -> bool:
    """Delete a block's body + manifest by ``block_id`` (AC-12); ``True`` when one was removed.

    Removes the manifest FIRST then the body, so a torn delete never leaves a manifest
    pointing at a gone body in the list (best-effort-consistent). ``False`` when no block with
    ``block_id`` exists (the endpoint maps that to ``404``; idempotent-safe, never a 500).
    """
    if not is_valid_block_id(block_id):
        return False
    for ptype in PROFILE_TYPE_ORDER:
        body = block_path(root, ptype, block_id)
        sidecar = manifest_path(body)
        if body.exists() or sidecar.exists():
            _assert_within_library(root, body)
            with suppress(FileNotFoundError):
                sidecar.unlink()
            with suppress(FileNotFoundError):
                body.unlink()
            return True
    return False


__all__ = [
    "LIBRARY_MANIFEST_VERSION",
    "PROFILE_TYPE_ORDER",
    "CuratedMetadata",
    "ProfileType",
    "ValidationState",
    "block_path",
    "build_block_manifest",
    "classify_profile",
    "declared_inherit",
    "delete_block",
    "derive_block_id",
    "derive_validation_state",
    "extract_curated_metadata",
    "is_valid_block_id",
    "library_root",
    "list_blocks",
    "manifest_path",
    "read_block",
    "resolve_inherit_chain",
    "sanitize_original_filename",
    "store_block",
]
