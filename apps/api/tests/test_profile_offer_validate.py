"""PROFILE-OFFER-1 (T1) — dry chain/offer validation engine tests (AC-2, AC-3, AC-4).

Exercises ``validate_chain`` (chain-intrinsic structural + block-state + filament↔machine
checks) and ``evaluate_offer`` (the offer-scoped reasons: material-category mismatch,
default-but-hidden, duplicate-default) over a tmp ``library/`` subtree of hand-built curated
manifests. The engine reads ONLY the curated manifests (``profile_library.read_block``) — it
never calls ``resolve()``, never reads a raw Orca body, never writes ``intents/``, never
slices (the AC-1 additive fence + AC-4 dry-validation contract).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.modules.slicer import profile_offer
from app.modules.slicer.profile_library import derive_block_id, store_block
from app.modules.slicer.profile_offer import (
    REASON_BLOCK_REQUIRES_ATTENTION,
    REASON_DEFAULT_BUT_HIDDEN,
    REASON_DUPLICATE_DEFAULT,
    REASON_FILAMENT_MACHINE_INCOMPATIBLE,
    REASON_MATERIAL_CATEGORY_MISMATCH,
    REASON_UNKNOWN_BLOCK,
    REASON_WRONG_BLOCK_TYPE,
    ProfileChain,
    evaluate_offer,
    validate_chain,
)

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def _store(
    root: Path,
    profile_type: str,
    name: str,
    *,
    validation_state: str = "usable",
    reasons: list[str] | None = None,
    material_type: str | None = None,
    compatible_printers: list[str] | None = None,
    inherit: str | None = None,
    inherit_chain: list[str] | None = None,
) -> str:
    """Store a curated block manifest in the tmp library and return its block_id."""
    block_id = derive_block_id(profile_type, name)  # type: ignore[arg-type]
    manifest = {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": name,
        "source": "user",
        "is_system": False,
        "inherit": inherit,
        "inherit_chain": inherit_chain or [],
        "settings_id": None,
        "material_type": material_type,
        "compatible_printers": compatible_printers or [],
        "validation_state": validation_state,
        "reasons": reasons or [],
        "portal_label": None,
        "imported_at": "2026-06-06T00:00:00+00:00",
        "imported_by": str(ADMIN_ID),
        "original_filename": "p.json",
    }
    store_block(
        root,
        profile_type=profile_type,  # type: ignore[arg-type]
        block_id=block_id,
        body={"name": name},
        manifest=manifest,
    )
    return block_id


def _usable_chain(root: Path) -> ProfileChain:
    """A fully-usable machine+process+filament chain (filament compatible with machine)."""
    machine = _store(root, "machine", "K1 Max", inherit_chain=["K1 Max @System"])
    process = _store(root, "process", "0.20 Standard")
    filament = _store(
        root, "filament", "Rosa PLA", material_type="PLA", compatible_printers=["K1 Max"]
    )
    return ProfileChain(
        machine_block_id=machine, process_block_id=process, filament_block_id=filament
    )


# === AC-4: chain-intrinsic validation via validate_chain ======================


def test_usable_chain_is_usable(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "usable"
    assert result.reasons == []
    # chain_blocks echo carries the three resolved curated manifests (machine/process/filament).
    assert [b["profile_type"] for b in result.chain_blocks] == ["machine", "process", "filament"]


def test_unknown_block_is_invalid(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    chain = ProfileChain(
        machine_block_id=chain.machine_block_id,
        process_block_id=derive_block_id("process", "ghost"),  # never stored
        filament_block_id=chain.filament_block_id,
    )
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "invalid"
    assert REASON_UNKNOWN_BLOCK in result.reasons
    # The missing block is omitted from the echo (never a raw-body leak, AC-10).
    assert [b["profile_type"] for b in result.chain_blocks] == ["machine", "filament"]


def test_wrong_block_type_is_invalid(tmp_path: Path) -> None:
    # A process block placed in the machine slot ⇒ wrong_block_type ⇒ invalid.
    process = _store(tmp_path, "process", "0.20 Standard")
    filament = _store(tmp_path, "filament", "Rosa PLA", material_type="PLA")
    chain = ProfileChain(
        machine_block_id=process, process_block_id=process, filament_block_id=filament
    )
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "invalid"
    assert REASON_WRONG_BLOCK_TYPE in result.reasons


def test_requires_attention_block_propagates(tmp_path: Path) -> None:
    machine = _store(tmp_path, "machine", "K1 Max")
    process = _store(
        tmp_path,
        "process",
        "Sketchy",
        validation_state="requires_attention",
        reasons=["user_process_invalid_inheritance"],
    )
    filament = _store(tmp_path, "filament", "Rosa PLA", material_type="PLA")
    chain = ProfileChain(
        machine_block_id=machine, process_block_id=process, filament_block_id=filament
    )
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "requires_attention"
    assert REASON_BLOCK_REQUIRES_ATTENTION in result.reasons


def test_filament_machine_incompatible_is_requires_attention(tmp_path: Path) -> None:
    machine = _store(tmp_path, "machine", "Prusa MK4", inherit_chain=["Prusa MK4 @System"])
    process = _store(tmp_path, "process", "0.20 Standard")
    # Filament declares compatibility with a different printer family ⇒ flagged.
    filament = _store(
        tmp_path,
        "filament",
        "Rosa PLA",
        material_type="PLA",
        compatible_printers=["Creality K1 Max (0.4 nozzle)"],
    )
    chain = ProfileChain(
        machine_block_id=machine, process_block_id=process, filament_block_id=filament
    )
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "requires_attention"
    assert REASON_FILAMENT_MACHINE_INCOMPATIBLE in result.reasons


def test_filament_machine_match_via_machine_inherit_chain(tmp_path: Path) -> None:
    # Real-fixture shape: a USER machine block whose name differs from the filament's
    # compatible_printers, but whose inherited SYSTEM name matches (the pinned identity set).
    machine = _store(
        tmp_path,
        "machine",
        "AI Creality K1 Max - MicroSwiss",
        inherit="Creality K1 Max (0.4 nozzle)",
        inherit_chain=["Creality K1 Max (0.4 nozzle)"],
    )
    process = _store(tmp_path, "process", "0.20 Standard")
    filament = _store(
        tmp_path,
        "filament",
        "Rosa Flex",
        material_type="TPU",
        compatible_printers=["Creality K1 Max (0.4 nozzle)"],
    )
    chain = ProfileChain(
        machine_block_id=machine, process_block_id=process, filament_block_id=filament
    )
    result = validate_chain(chain, root=tmp_path)
    assert REASON_FILAMENT_MACHINE_INCOMPATIBLE not in result.reasons
    assert result.state == "usable"


def test_filament_with_no_compatible_printers_is_not_flagged(tmp_path: Path) -> None:
    machine = _store(tmp_path, "machine", "K1 Max")
    process = _store(tmp_path, "process", "0.20 Standard")
    filament = _store(tmp_path, "filament", "Generic", material_type="PLA", compatible_printers=[])
    chain = ProfileChain(
        machine_block_id=machine, process_block_id=process, filament_block_id=filament
    )
    result = validate_chain(chain, root=tmp_path)
    assert REASON_FILAMENT_MACHINE_INCOMPATIBLE not in result.reasons


def test_invalid_precedence_over_requires_attention(tmp_path: Path) -> None:
    # A chain that is BOTH structurally invalid (unknown filament) and would-be flagged must
    # report invalid (precedence invalid > requires_attention).
    machine = _store(tmp_path, "machine", "K1 Max")
    process = _store(
        tmp_path,
        "process",
        "Sketchy",
        validation_state="requires_attention",
        reasons=["user_process_invalid_inheritance"],
    )
    chain = ProfileChain(
        machine_block_id=machine,
        process_block_id=process,
        filament_block_id=derive_block_id("filament", "ghost"),
    )
    result = validate_chain(chain, root=tmp_path)
    assert result.state == "invalid"


# === AC-4: offer-scoped reasons via evaluate_offer ============================


def test_material_category_mismatch_is_requires_attention(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)  # filament material_type is PLA
    result = evaluate_offer(
        chain=chain,
        root=tmp_path,
        compatible_material_categories=["PETG"],  # does NOT include the filament's PLA
        is_default=False,
        visibility="visible",
    )
    assert result.state == "requires_attention"
    assert REASON_MATERIAL_CATEGORY_MISMATCH in result.reasons


def test_material_category_match_is_clean(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)  # PLA
    result = evaluate_offer(
        chain=chain,
        root=tmp_path,
        compatible_material_categories=["PLA"],
        is_default=False,
        visibility="visible",
    )
    assert result.state == "usable"
    assert result.reasons == []


def test_default_but_hidden_is_requires_attention(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    result = evaluate_offer(
        chain=chain,
        root=tmp_path,
        compatible_material_categories=["PLA"],
        is_default=True,
        visibility="hidden",
    )
    assert result.state == "requires_attention"
    assert REASON_DEFAULT_BUT_HIDDEN in result.reasons


def test_duplicate_default_across_two_visible_offers(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    # Two visible offers both default for the same material category ⇒ both flagged.
    result = evaluate_offer(
        chain=chain,
        root=tmp_path,
        compatible_material_categories=["PLA"],
        is_default=True,
        visibility="visible",
        duplicate_default=True,
    )
    assert result.state == "requires_attention"
    assert REASON_DUPLICATE_DEFAULT in result.reasons


def test_evaluate_offer_keeps_invalid_chain_invalid(tmp_path: Path) -> None:
    chain = _usable_chain(tmp_path)
    chain = ProfileChain(
        machine_block_id=derive_block_id("machine", "ghost"),
        process_block_id=chain.process_block_id,
        filament_block_id=chain.filament_block_id,
    )
    result = evaluate_offer(
        chain=chain,
        root=tmp_path,
        compatible_material_categories=["PLA"],
        is_default=True,
        visibility="hidden",
    )
    # A structurally-invalid chain stays invalid even though default_but_hidden would apply.
    assert result.state == "invalid"
    assert REASON_UNKNOWN_BLOCK in result.reasons


# === AC-1: the engine is purely additive — it never enters the grid/resolve path ===


def test_offer_engine_does_not_touch_grid_or_resolve_surfaces() -> None:
    src = Path(profile_offer.__file__).read_text(encoding="utf-8")
    # No import of the grid / resolve / append-only surfaces (a breach would need an import).
    for forbidden_import in (
        "from app.modules.slicer.resolver import",
        "import app.modules.slicer.resolver",
        "from app.modules.slicer.compatibility import",
        "from app.modules.slicer.bundle_store import",
    ):
        assert forbidden_import not in src, (
            f"offer engine unexpectedly imports {forbidden_import!r}"
        )
    # Call-form tokens (with the opening paren) so descriptive docstring prose that NAMES the
    # grid surfaces does not trip the fence — only actual usage would.
    for forbidden_call in (
        "resolve_preset(",
        "resolve_inheritance(",
        "compute_bundle_hash(",
        "write_bundle(",
        "write_snapshot(",
        "BundleStore(",
        "is_compatible(",
        ".intent_path(",
        "publish_intent(",
    ):
        assert forbidden_call not in src, f"offer engine unexpectedly calls {forbidden_call!r}"
    # The only import_service reuse is the SAFE atomic-publish foundation; the only library
    # coupling is the read-only curated-manifest read.
    assert "from app.modules.slicer.import_service import" in src
    assert "from app.modules.slicer.profile_library import" in src
    assert "read_block" in src
