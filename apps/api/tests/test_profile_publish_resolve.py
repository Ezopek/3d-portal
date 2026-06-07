"""PROFILE-PUBLISH-1 — chain-addressed resolve-tail tests.

These tests pin Decision AR option (b): an offer ProfileChain resolves directly from
library block bodies, reusing the existing resolver tail, without reading or writing
the grid ``intents/`` tree.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.models import ResolvedTriple, ResolveFailure, ResolveReason, ResolveSuccess
from app.modules.slicer.profile_library import derive_block_id, store_block
from app.modules.slicer.profile_offer import ProfileChain
from app.modules.slicer.resolver import VendoredProfileSource, resolve_chain
from app.modules.slicer.validation import ValidationResult

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"


class _CountingValidator:
    def __init__(self, *, ok: bool = True, reason: str | None = None) -> None:
        self.ok = ok
        self.reason = reason
        self.calls = 0

    def validate(self, triple: ResolvedTriple) -> ValidationResult:
        self.calls += 1
        return ValidationResult(ok=self.ok, reason=self.reason)


def _copy_system_tree(root: Path) -> None:
    system_dir = root / "system"
    system_dir.mkdir(parents=True)
    for source in (FIXTURES / "system").glob("*.json"):
        shutil.copy(source, system_dir / source.name)


def _store_chain_block(
    root: Path,
    profile_type: str,
    block_id_name: str,
    body: dict,
    *,
    material_type: str | None = None,
) -> str:
    block_id = derive_block_id(profile_type, block_id_name)  # type: ignore[arg-type]
    manifest = {
        "manifest_version": "1",
        "block_id": block_id,
        "profile_type": profile_type,
        "name": block_id_name,
        "source": "user",
        "is_system": False,
        "inherit": body.get("inherit"),
        "inherit_chain": [body["inherit"]] if isinstance(body.get("inherit"), str) else [],
        "settings_id": None,
        "material_type": material_type,
        "compatible_printers": [],
        "validation_state": "usable",
        "reasons": [],
        "portal_label": None,
        "imported_at": "2026-06-06T00:00:00+00:00",
        "imported_by": "00000000-0000-0000-0000-0000000000aa",
        "original_filename": f"{profile_type}.json",
    }
    store_block(
        root,
        profile_type=profile_type,
        block_id=block_id,
        body=body,
        manifest=manifest,
    )  # type: ignore[arg-type]
    return block_id


def _seed_tpu_chain(root: Path) -> ProfileChain:
    partials = json.loads(
        (FIXTURES / "intents/creality-k1-max-microswiss-hf/TPU/standard.json").read_text(
            encoding="utf-8"
        )
    )
    machine = _store_chain_block(root, "machine", "offer-machine", partials["machine"])
    process = _store_chain_block(root, "process", "offer-process", partials["process"])
    filament = _store_chain_block(
        root,
        "filament",
        "offer-filament",
        partials["filament"],
        material_type="TPU",
    )
    return ProfileChain(
        machine_block_id=machine,
        process_block_id=process,
        filament_block_id=filament,
    )


def _seed_plural_inherits_chain(root: Path) -> ProfileChain:
    """Seed an offer chain whose block bodies carry the PLURAL real-Orca ``inherits``
    key (the live PROFILE-PUBLISH-FIX shape), each inheriting a vendored system parent.

    This is the exact shape that previously compiled to a sparse bundle that leaked an
    unresolved ``inherits`` key and failed headless Orca with RC -17 — the singular
    ``inherit`` bench shape (used by :func:`_seed_tpu_chain`) masked the bug.
    """
    machine_body = {
        "name": "AI Creality K1 Max - MicroSwiss HF",
        "from": "User",
        "inherits": "Creality K1 Max MicroSwiss HF",
        "z_offset": "-0.05",
    }
    process_body = {
        "name": "AI 0.20mm TPU - FlowTech",
        "from": "User",
        "inherits": "0.20mm Standard",
        "outer_wall_speed": "25",
    }
    filament_body = {
        "name": "AI Rosa3D Flex 96A Black",
        "from": "User",
        "inherits": "Rosa3D Flex 96A",
        "filament_type": ["TPU"],
    }
    machine = _store_chain_block(root, "machine", "offer-machine", machine_body)
    process = _store_chain_block(root, "process", "offer-process", process_body)
    filament = _store_chain_block(
        root, "filament", "offer-filament", filament_body, material_type="TPU"
    )
    return ProfileChain(
        machine_block_id=machine,
        process_block_id=process,
        filament_block_id=filament,
    )


def test_resolve_chain_materializes_plural_inherits_and_strips_recipe_keys(
    tmp_path: Path,
) -> None:
    _copy_system_tree(tmp_path)
    chain = _seed_plural_inherits_chain(tmp_path)
    store = BundleStore(tmp_path / "bundle-store")

    outcome = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=store,
        validator=_CountingValidator(),
        orca_version="2.3.2",
        material_class="TPU",
    )

    assert isinstance(outcome, ResolveSuccess)
    bundle = outcome.bundle

    # No recipe key (plural OR singular) may leak into the CLI-bound bundle.
    for profile in (bundle.machine, bundle.process, bundle.filament):
        assert "inherits" not in profile
        assert "inherit" not in profile

    # Fully materialized: inherited system settings are present, not just the sparse
    # user overrides — this is the difference between RC -17 and a sliceable bundle.
    assert bundle.machine["printer_model"] == "Creality K1 Max"  # from system child
    assert bundle.machine["gcode_flavor"] == "marlin"  # from the grandparent
    assert bundle.process["sparse_infill_density"] == "15%"  # from the system parent
    assert bundle.filament["filament_max_volumetric_speed"] == ["3.5"]  # from system parent

    # User overrides survive the merge.
    assert bundle.process["outer_wall_speed"] == "25"
    assert bundle.machine["z_offset"] == "-0.05"

    # Headless Orca compatibility: real-Orca plural-inherits USER machine profiles
    # keep their materialized overrides, but the CLI-bound printer identity must match
    # the inherited system profile. A renamed/from=User machine is rejected by Orca as
    # `process not compatible with printer` even when the process is otherwise valid.
    assert bundle.machine["name"] == "Creality K1 Max MicroSwiss HF"
    assert bundle.machine["from"] == "system"


def test_resolve_chain_persists_bundle_without_grid_intents(tmp_path: Path) -> None:
    _copy_system_tree(tmp_path)
    chain = _seed_tpu_chain(tmp_path)
    store = BundleStore(tmp_path / "bundle-store")
    validator = _CountingValidator()

    outcome = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=store,
        validator=validator,
        orca_version="2.3.2",
        material_class="TPU",
    )

    assert isinstance(outcome, ResolveSuccess)
    assert len(outcome.bundle.bundle_hash) == 64
    assert store.has_bundle(outcome.bundle.bundle_hash)
    assert store.has_snapshot(outcome.bundle.source_snapshot_ref)
    assert validator.calls == 1
    assert not (tmp_path / "intents").exists()


def test_resolve_chain_is_deterministic_and_unrelated_bundle_is_byte_stable(
    tmp_path: Path,
) -> None:
    _copy_system_tree(tmp_path)
    chain = _seed_tpu_chain(tmp_path)
    store = BundleStore(tmp_path / "bundle-store")

    unrelated = store._atomic_write(store.bundle_path("a" * 64), '{"kept": true}\n')
    before = unrelated.read_bytes()

    first = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=store,
        validator=_CountingValidator(),
        orca_version="2.3.2",
        material_class="TPU",
    )
    second_validator = _CountingValidator()
    second = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=store,
        validator=second_validator,
        orca_version="2.3.2",
        material_class="TPU",
    )

    assert isinstance(first, ResolveSuccess)
    assert isinstance(second, ResolveSuccess)
    assert second.bundle.bundle_hash == first.bundle.bundle_hash
    assert second.from_cache is True
    assert second_validator.calls == 0
    assert unrelated.read_bytes() == before


def test_resolve_chain_cli_reject_is_classified_and_persists_nothing(tmp_path: Path) -> None:
    _copy_system_tree(tmp_path)
    chain = _seed_tpu_chain(tmp_path)
    store = BundleStore(tmp_path / "bundle-store")

    outcome = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=store,
        validator=_CountingValidator(ok=False, reason="orca rejected"),
        orca_version="2.3.2",
        material_class="TPU",
    )

    assert isinstance(outcome, ResolveFailure)
    assert outcome.reason == ResolveReason.cli_validation_failed
    assert not (tmp_path / "bundle-store" / "bundles").exists()
    assert not (tmp_path / "bundle-store" / "snapshots").exists()


def test_resolve_chain_missing_library_body_is_invalid_partial(tmp_path: Path) -> None:
    _copy_system_tree(tmp_path)
    chain = ProfileChain(
        machine_block_id="0" * 32,
        process_block_id="1" * 32,
        filament_block_id="2" * 32,
    )

    outcome = resolve_chain(
        chain,
        source=VendoredProfileSource(tmp_path),
        store=BundleStore(tmp_path / "bundle-store"),
        validator=_CountingValidator(),
        orca_version="2.3.2",
        material_class="TPU",
    )

    assert isinstance(outcome, ResolveFailure)
    assert outcome.reason == ResolveReason.invalid_partial
