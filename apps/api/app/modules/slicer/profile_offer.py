"""PROFILE-OFFER-1 (Decision AN) — PrintProfileOffer / ProfileChain layer.

The SCP 2026-06-06 § 6 "THEN" step after PROFILE-LIB-1 (Decision AM): a small, additive
offer/chain layer that CONSUMES the separate-block profile library. An admin composes a
``PrintProfileOffer`` by selecting exactly one machine + one process + one filament library
block (an embedded ``ProfileChain`` value object referencing three ``block_id``s), labels it,
sets visibility/default + compatible material categories, and the backend validates the chain
by reading ONLY the referenced blocks' curated manifests — deriving ``usable`` /
``requires_attention`` / ``invalid`` with machine-readable reason categories.

This module is the engine half — the chain/offer data model, the DRY chain-validation engine,
and the on-disk offer-sidecar storage layer. It is **purely additive** (AC-1): it does NOT
call ``resolve()``, read raw Orca bodies, write the ``intents/`` (grid) tree, touch the
append-only bundle/snapshot store, ``bundle_hash``, ``compatibility.py``, or the PROFILE-LIB-1
library *write* path. It only **reads** the library via ``profile_library.read_block`` and
reuses ``import_service.publish_single`` (the shared atomic write + ``ezop:ezop 664``
metadata-preservation foundation) for its own sidecar writes. Real resolver publication / live
slicing over an offer is OUT of this slice (G-PUBLISH, deferred).

Storage is on-disk JSON only (no DB/Alembic — SCP § 4 no-DB posture), in a NEW ``offers/``
subtree disjoint from ``system/`` / ``intents/`` (grid) / ``library/`` (blocks).

[Source: architecture.md § Initiative 21 Decision AN; SCP 2026-06-06 § 3.4/§ 3.5/§ 6; PRD FR21-*]
"""

from __future__ import annotations

import json
import re
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from app.modules.slicer.import_service import _json_bytes, publish_single
from app.modules.slicer.profile_library import read_block

Visibility = Literal["hidden", "visible"]
OfferValidationState = Literal["usable", "requires_attention", "invalid"]

# Offer-sidecar schema version — points to the PROFILE-OFFER-1 offer-sidecar contract v1, a
# NEW schema distinct from the library-manifest v1 and the intent-manifest v1 (AC-3). Bumping
# it is a future migration.
OFFER_MANIFEST_VERSION: Final = "1"

# An offer is stored as a single curated JSON sidecar (no body/manifest split — an offer has
# no raw Orca body, only curated refs).
_OFFER_SUFFIX: Final = ".json"

# A server-minted ``offer_id`` is always a 32-char lowercase hex uuid4 hexdigest — path-safe
# (no separators/traversal/attacker control) AND stable across mutable label/visibility/
# default/category edits (an offer has no immutable natural key, so identity is a minted token
# — deliberately UNLIKE the library ``block_id = uuid5(type:name)``). GET/PATCH/DELETE path
# params are validated against this charset before they are ever joined into a filesystem path.
_OFFER_ID_RE: Final = re.compile(r"^[0-9a-f]{32}$")

# Small generic material-category table (SCP § 3.6): an out-of-table category is rejected
# ``422 unsupported_material_category`` at the endpoint, never minted. ABS/ASA are a deferred
# expansion. This is the offer-level material bridge — NOT the grid's ``compatibility.py``
# tier-compat map (which this story does not consume or edit).
OFFER_MATERIAL_CATEGORIES: Final[frozenset[str]] = frozenset({"PLA", "PETG", "PCTG", "TPU"})

# The three chain slots, in machine→process→filament order (drives the ``chain_blocks`` echo
# ordering, AC-8).
_CHAIN_SLOTS: Final[tuple[Literal["machine", "process", "filament"], ...]] = (
    "machine",
    "process",
    "filament",
)

# Validation reason CATEGORIES (machine-readable; the FE localizes them — no display text from
# the backend, AC-4). Exposed for the API/i18n contract + tests.
REASON_UNKNOWN_BLOCK: Final = "unknown_block"
REASON_WRONG_BLOCK_TYPE: Final = "wrong_block_type"
REASON_BLOCK_UNUSABLE: Final = "block_unusable"
REASON_BLOCK_REQUIRES_ATTENTION: Final = "block_requires_attention"
REASON_FILAMENT_MACHINE_INCOMPATIBLE: Final = "filament_machine_incompatible"
REASON_MATERIAL_CATEGORY_MISMATCH: Final = "material_category_mismatch"
REASON_DEFAULT_BUT_HIDDEN: Final = "default_but_hidden"
REASON_DUPLICATE_DEFAULT: Final = "duplicate_default"

# The structural ``invalid`` reasons — they block storage at create time (AC-9 hard chain
# gate) and supersede every ``requires_attention`` flag (precedence invalid > attention).
_INVALID_REASONS: Final[frozenset[str]] = frozenset(
    {REASON_UNKNOWN_BLOCK, REASON_WRONG_BLOCK_TYPE, REASON_BLOCK_UNUSABLE}
)


# === chain / offer value objects (AC-2, AC-3) =================================


@dataclass(frozen=True)
class ProfileChain:
    """The embedded triple of library block references (AC-2).

    Carries ONLY the three ``block_id``s — no raw Orca body. In this slice the chain is an
    embedded value object inside one offer; there is NO standalone reusable chain registry
    (deferred, SCP § 9).
    """

    machine_block_id: str
    process_block_id: str
    filament_block_id: str


@dataclass(frozen=True)
class ChainValidation:
    """The result of validating a chain or evaluating an offer (AC-4).

    ``state`` is the single primary state by precedence (invalid > requires_attention >
    usable); ``reasons`` is the ordered list of machine-readable categories; ``chain_blocks``
    is the resolved curated manifests in machine→process→filament order, **omitting** any
    missing referenced block (a missing block surfaces only via the ``unknown_block`` reason —
    never a raw-body leak, AC-10).
    """

    state: OfferValidationState
    reasons: list[str]
    chain_blocks: list[dict]


def _state_for(reasons: list[str]) -> OfferValidationState:
    """Map a reason set to the single primary state by the AC-4 precedence."""
    if any(r in _INVALID_REASONS for r in reasons):
        return "invalid"
    if reasons:
        return "requires_attention"
    return "usable"


# === dry chain-validation engine (AC-4) — NO resolve, NO slice, NO raw bodies ===


def _machine_identities(machine: dict) -> set[str]:
    """The set of names a filament's ``compatible_printers`` may legitimately reference.

    Pinned against the real library fixtures (G-DATA): a filament's ``compatible_printers``
    references the SYSTEM machine name (e.g. ``"Creality K1 Max (0.4 nozzle)"``), while a USER
    machine block's own ``name`` is the customized variant (e.g. ``"AI Creality K1 Max ...
    MicroSwiss"``). So the machine's identity set is its own ``name`` PLUS every ancestor it
    inherits from (``inherit`` + ``inherit_chain``) — the user block matches via its inherited
    system name, the system block matches via its own name. (AC-4 filament↔machine check; the
    exact key is pinned here rather than guessed — magic-constant discipline.)
    """
    identities: set[str] = set()
    name = machine.get("name")
    if isinstance(name, str) and name:
        identities.add(name)
    inherit = machine.get("inherit")
    if isinstance(inherit, str) and inherit:
        identities.add(inherit)
    chain = machine.get("inherit_chain")
    if isinstance(chain, list):
        identities.update(p for p in chain if isinstance(p, str) and p)
    return identities


def validate_chain(chain: ProfileChain, *, root: Path | str) -> ChainValidation:
    """Validate a chain by reading ONLY the referenced blocks' curated manifests (AC-4).

    ``root`` is the vendored profiles root (``profile_library.read_block`` resolves the
    ``library/`` subtree under it). This is a DRY validation: it does NOT call ``resolve()``,
    does NOT read raw Orca bodies, does NOT write ``intents/``, and does NOT slice. It handles
    the chain-INTRINSIC reasons:

    - **invalid:** a referenced ``block_id`` is missing (``unknown_block``); a referenced
      block's ``profile_type`` does not match its slot (``wrong_block_type``); a referenced
      block is itself in ``error`` state (``block_unusable`` — guarded; PROFILE-LIB-1 never
      stores ``error`` blocks).
    - **requires_attention:** a referenced block is ``requires_attention``
      (``block_requires_attention``); or the filament block's ``compatible_printers`` is
      present and does not include the machine block's identity
      (``filament_machine_incompatible``).

    The offer-SCOPED reasons (material-category mismatch, default-but-hidden, duplicate-default)
    are layered on by :func:`evaluate_offer`. Deeper Orca process↔filament slice-time validity
    is deferred to G-PUBLISH (it needs the resolver path).
    """
    block_ids = {
        "machine": chain.machine_block_id,
        "process": chain.process_block_id,
        "filament": chain.filament_block_id,
    }
    resolved: dict[str, dict] = {}
    reasons: list[str] = []

    def _flag(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    for slot in _CHAIN_SLOTS:
        manifest = read_block(root, block_ids[slot])
        if manifest is None:
            _flag(REASON_UNKNOWN_BLOCK)
            continue
        resolved[slot] = manifest
        if manifest.get("profile_type") != slot:
            _flag(REASON_WRONG_BLOCK_TYPE)
            continue
        block_state = manifest.get("validation_state")
        if block_state == "error":
            _flag(REASON_BLOCK_UNUSABLE)
        elif block_state == "requires_attention":
            _flag(REASON_BLOCK_REQUIRES_ATTENTION)

    # Filament ↔ machine compatibility — only when BOTH blocks resolved into the right slot
    # and the filament declares a non-empty compatible_printers list (absent ⇒ compatible).
    machine = resolved.get("machine")
    filament = resolved.get("filament")
    if machine is not None and filament is not None:
        compat = filament.get("compatible_printers")
        if isinstance(compat, list) and compat:
            declared = {p for p in compat if isinstance(p, str) and p}
            if declared and not (declared & _machine_identities(machine)):
                reasons.append(REASON_FILAMENT_MACHINE_INCOMPATIBLE)

    chain_blocks = [resolved[slot] for slot in _CHAIN_SLOTS if slot in resolved]
    return ChainValidation(state=_state_for(reasons), reasons=reasons, chain_blocks=chain_blocks)


def evaluate_offer(
    *,
    chain: ProfileChain,
    root: Path | str,
    compatible_material_categories: list[str],
    is_default: bool,
    visibility: Visibility,
    duplicate_default: bool = False,
) -> ChainValidation:
    """Full offer validation: the chain-intrinsic state plus the offer-SCOPED reasons (AC-4).

    Composes :func:`validate_chain` and layers on the offer-scoped ``requires_attention``
    reasons (precedence still invalid > requires_attention > usable, so a structurally-invalid
    chain stays ``invalid``):

    - ``material_category_mismatch`` — the filament block carries a known ``material_type`` not
      present in the offer's ``compatible_material_categories``.
    - ``default_but_hidden`` — ``is_default`` while ``visibility == "hidden"``.
    - ``duplicate_default`` — two **visible** offers share a default for the same material
      category. ``duplicate_default`` is computed across the offer set by the storage layer
      (:func:`revalidate_offers`) and passed in here, so this function stays a pure mapping.
    """
    chain_result = validate_chain(chain, root=root)
    reasons = list(chain_result.reasons)

    filament = next(
        (b for b in chain_result.chain_blocks if b.get("profile_type") == "filament"), None
    )
    if filament is not None:
        material_type = filament.get("material_type")
        if (
            isinstance(material_type, str)
            and material_type
            and material_type not in set(compatible_material_categories)
        ):
            reasons.append(REASON_MATERIAL_CATEGORY_MISMATCH)

    if is_default and visibility == "hidden":
        reasons.append(REASON_DEFAULT_BUT_HIDDEN)
    if duplicate_default:
        reasons.append(REASON_DUPLICATE_DEFAULT)

    return ChainValidation(
        state=_state_for(reasons), reasons=reasons, chain_blocks=chain_result.chain_blocks
    )


# === offer storage layer (AC-5, AC-6, AC-7) ==================================


def mint_offer_id() -> str:
    """Mint a fresh server-side, path-safe, edit-stable ``offer_id`` (32-char hex, AC-6)."""
    return uuid.uuid4().hex


def is_valid_offer_id(offer_id: str) -> bool:
    """True when ``offer_id`` is a 32-char lowercase hex string (GET/PATCH/DELETE gate, AC-6)."""
    return bool(_OFFER_ID_RE.match(offer_id))


def offers_root(root: Path | str) -> Path:
    """The ``<root>/offers`` root, disjoint from ``system/`` / ``intents/`` / ``library/``."""
    return Path(root) / "offers"


def offer_path(root: Path | str, offer_id: str) -> Path:
    """The single-SoT on-disk path of an offer sidecar (AC-5).

    ``<root>/offers/<offer_id>.json``. Mirrors ``profile_library.block_path`` as the one place
    the layout lives so reads/writes/deletes cannot drift.
    """
    return offers_root(root) / f"{offer_id}{_OFFER_SUFFIX}"


def _assert_within(root: Path | str, subdir: str, target: Path) -> None:
    """Belt-and-braces containment: ``target`` must stay at/below ``<root>/<subdir>`` (AC-6).

    The server-minted hex ``offer_id`` already structurally precludes traversal; this is the
    defense-in-depth assert mirroring ``profile_library._assert_within_library`` /
    ``import_service.is_within_intents_root``.
    """
    base = (Path(root) / subdir).resolve()
    resolved = target.resolve()
    if not (resolved == base or base in resolved.parents):
        raise ValueError(f"offer path escapes {base}")


def build_offer_record(
    *,
    offer_id: str,
    label: str,
    description: str | None,
    chain: ProfileChain,
    visibility: Visibility,
    is_default: bool,
    compatible_material_categories: list[str],
    validation_state: OfferValidationState,
    reasons: list[str],
    created_at: str,
    created_by: uuid.UUID | str,
    updated_at: str,
) -> dict[str, Any]:
    """Build the curated offer-sidecar v1 dict (AC-3).

    Holds ONLY curated offer config + the embedded chain refs + a point-in-time validation
    snapshot — NO raw Orca key body, NO filesystem path, NO g-code (the leak fence). The
    ``validation_state`` / ``reasons`` here are a write-time snapshot; the list/get endpoints
    RECOMPUTE them at read time against the current library (AC-10), so a stale ``usable`` is
    never served after a referenced block changes.
    """
    return {
        "offer_manifest_version": OFFER_MANIFEST_VERSION,
        "offer_id": offer_id,
        "label": label,
        "description": description,
        "chain": {
            "machine_block_id": chain.machine_block_id,
            "process_block_id": chain.process_block_id,
            "filament_block_id": chain.filament_block_id,
        },
        "visibility": visibility,
        "is_default": is_default,
        "compatible_material_categories": list(compatible_material_categories),
        "validation_state": validation_state,
        "reasons": list(reasons),
        "created_at": created_at,
        "created_by": str(created_by),
        "updated_at": updated_at,
    }


def chain_of(sidecar: dict) -> ProfileChain:
    """Reconstruct the embedded :class:`ProfileChain` from a stored offer sidecar."""
    raw = sidecar.get("chain") or {}
    return ProfileChain(
        machine_block_id=str(raw.get("machine_block_id", "")),
        process_block_id=str(raw.get("process_block_id", "")),
        filament_block_id=str(raw.get("filament_block_id", "")),
    )


def store_offer(root: Path | str, record: dict) -> Path:
    """Atomically store an offer sidecar (AC-7) — returns the sidecar path.

    Reuses the shared ``import_service.publish_single`` atomic write + ``ezop:ezop 664``
    owner/mode preservation (incl. the ``221bbe1`` fresh-directory metadata-inheritance fix) so
    a fresh ``offers/`` directory and its files land operator-friendly, not root-owned ``0600``.
    On a write failure the ``offers/`` subtree is byte-identical to before and no temp remains.
    """
    offer_id = record["offer_id"]
    if not is_valid_offer_id(offer_id):
        raise ValueError(f"invalid offer_id {offer_id!r}")
    target = offer_path(root, offer_id)
    _assert_within(root, "offers", target)
    publish_single(path=target, content=_json_bytes(record))
    return target


def snapshot_offer(root: Path | str, offer_id: str) -> bytes | None:
    """Capture the live offer-sidecar bytes so a later side-effect failure can roll back.

    Companion to :func:`store_offer` for the endpoint's audit-rollback (mirrors
    ``profile_library.snapshot_block``). ``None`` means the offer did not exist before.
    """
    target = offer_path(root, offer_id)
    return target.read_bytes() if target.exists() else None


def restore_offer(root: Path | str, offer_id: str, previous: bytes | None) -> None:
    """Restore (or remove) an offer sidecar to a prior snapshot after a post-store failure."""
    target = offer_path(root, offer_id)
    if previous is None:
        with suppress(FileNotFoundError):
            target.unlink()
        return
    publish_single(path=target, content=previous)


def _read_sidecar(path: Path) -> dict | None:
    """Read one offer sidecar, or ``None`` when missing/unreadable/non-object."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def read_offer(root: Path | str, offer_id: str) -> dict | None:
    """Read one offer's stored sidecar by ``offer_id`` (AC-11), or ``None`` when absent."""
    if not is_valid_offer_id(offer_id):
        return None
    return _read_sidecar(offer_path(root, offer_id))


def list_offers(root: Path | str) -> list[dict]:
    """List the stored offer sidecars, deterministically ordered by ``created_at`` then id (AC-10).

    A missing/empty ``offers/`` tree ⇒ an empty list. Returns the RAW stored sidecars; the
    read-time revalidation (:func:`revalidate_offers`) recomputes validation against the
    current library.
    """
    base = offers_root(root)
    if not base.exists():
        return []
    collected: list[dict] = []
    for path in sorted(base.glob(f"*{_OFFER_SUFFIX}")):
        sidecar = _read_sidecar(path)
        if sidecar is not None:
            collected.append(sidecar)
    collected.sort(key=lambda s: (s.get("created_at", ""), s.get("offer_id", "")))
    return collected


def delete_offer(root: Path | str, offer_id: str) -> bool:
    """Delete an offer sidecar by ``offer_id`` (AC-13); ``True`` when one was removed.

    Does NOT touch the referenced library blocks (offers reference, they do not own). ``False``
    when no offer with ``offer_id`` exists (the endpoint maps that to ``404``; idempotent-safe,
    never a 500).
    """
    if not is_valid_offer_id(offer_id):
        return False
    target = offer_path(root, offer_id)
    if not target.exists():
        return False
    _assert_within(root, "offers", target)
    with suppress(FileNotFoundError):
        target.unlink()
        return True
    return False


# === read-time revalidation across the offer set (AC-4 duplicate_default, AC-10) ===


@dataclass(frozen=True)
class ResolvedOffer:
    """A stored offer plus its read-time-recomputed validation (AC-10).

    ``chain_block_manifests`` are the resolved curated block manifests (machine/process/
    filament order, present-only) the endpoint maps to ``chain_blocks`` DTOs.
    """

    sidecar: dict
    state: OfferValidationState
    reasons: list[str]
    chain_block_manifests: list[dict] = field(default_factory=list)


def _default_duplicate_ids(sidecars: list[dict]) -> set[str]:
    """Offer ids that collide on a default for a material category among VISIBLE offers (AC-4).

    Two visible ``is_default`` offers that share at least one ``compatible_material_categories``
    entry both carry ``duplicate_default``. Computed across the whole set on list/validate.
    """
    by_category: dict[str, list[str]] = {}
    for s in sidecars:
        if not s.get("is_default") or s.get("visibility") != "visible":
            continue
        offer_id = s.get("offer_id")
        if not isinstance(offer_id, str):
            continue
        for category in s.get("compatible_material_categories") or []:
            by_category.setdefault(category, []).append(offer_id)
    duplicates: set[str] = set()
    for ids in by_category.values():
        if len(ids) > 1:
            duplicates.update(ids)
    return duplicates


def revalidate_offers(root: Path | str, sidecars: list[dict]) -> list[ResolvedOffer]:
    """Recompute each offer's validation against the current library + offer set (AC-4, AC-10).

    The read-time revalidation contract: a deleted/changed referenced block flips the offer to
    ``invalid`` ``unknown_block`` on the next list/get (never serves a stale ``usable``), and
    the cross-offer ``duplicate_default`` is computed over the whole set. No offer is mutated on
    disk (no eager cross-deletion); the offer remains, flagged.
    """
    duplicates = _default_duplicate_ids(sidecars)
    resolved: list[ResolvedOffer] = []
    for sidecar in sidecars:
        offer_id = sidecar.get("offer_id")
        evaluation = evaluate_offer(
            chain=chain_of(sidecar),
            root=root,
            compatible_material_categories=sidecar.get("compatible_material_categories") or [],
            is_default=bool(sidecar.get("is_default")),
            visibility=sidecar.get("visibility", "hidden"),
            duplicate_default=offer_id in duplicates if isinstance(offer_id, str) else False,
        )
        resolved.append(
            ResolvedOffer(
                sidecar=sidecar,
                state=evaluation.state,
                reasons=evaluation.reasons,
                chain_block_manifests=evaluation.chain_blocks,
            )
        )
    return resolved


def revalidate_offer(root: Path | str, sidecar: dict, *, peers: list[dict]) -> ResolvedOffer:
    """Recompute one offer's read-time validation against ``peers`` (the full offer set)."""
    by_id = {s.get("offer_id"): s for s in peers}
    by_id[sidecar.get("offer_id")] = sidecar
    resolved = revalidate_offers(root, list(by_id.values()))
    for item in resolved:
        if item.sidecar.get("offer_id") == sidecar.get("offer_id"):
            return item
    # Fallback (should not happen): evaluate standalone.
    evaluation = evaluate_offer(
        chain=chain_of(sidecar),
        root=root,
        compatible_material_categories=sidecar.get("compatible_material_categories") or [],
        is_default=bool(sidecar.get("is_default")),
        visibility=sidecar.get("visibility", "hidden"),
    )
    return ResolvedOffer(
        sidecar=sidecar,
        state=evaluation.state,
        reasons=evaluation.reasons,
        chain_block_manifests=evaluation.chain_blocks,
    )


__all__ = [
    "OFFER_MANIFEST_VERSION",
    "OFFER_MATERIAL_CATEGORIES",
    "REASON_BLOCK_REQUIRES_ATTENTION",
    "REASON_BLOCK_UNUSABLE",
    "REASON_DEFAULT_BUT_HIDDEN",
    "REASON_DUPLICATE_DEFAULT",
    "REASON_FILAMENT_MACHINE_INCOMPATIBLE",
    "REASON_MATERIAL_CATEGORY_MISMATCH",
    "REASON_UNKNOWN_BLOCK",
    "REASON_WRONG_BLOCK_TYPE",
    "ChainValidation",
    "OfferValidationState",
    "ProfileChain",
    "ResolvedOffer",
    "Visibility",
    "build_offer_record",
    "chain_of",
    "delete_offer",
    "evaluate_offer",
    "is_valid_offer_id",
    "list_offers",
    "mint_offer_id",
    "offer_path",
    "offers_root",
    "read_offer",
    "restore_offer",
    "revalidate_offer",
    "revalidate_offers",
    "snapshot_offer",
    "store_offer",
    "validate_chain",
]
