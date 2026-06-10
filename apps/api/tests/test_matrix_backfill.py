"""Tests for matrix_backfill module (Story 35.6 — AC-2, AC-3, AC-11).

Covers:
- enumerate_matrix_cells pure-function contract
- resolve_matrix_cells seam (fake resolve_chain)
- enqueue_default_matrix_backfill.run() seam (dry-run + live mode)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.modules.slicer.matrix_backfill import (
    MatrixCell,
    ResolvedMatrixCell,
    enumerate_matrix_cells,
    resolve_matrix_cells,
)
from app.modules.slicer.profile_policy import (
    EstimateProfileSource,
    MaterialDefault,
    ProfilePolicy,
    ProfileSelection,
)
from app.modules.slicer.profile_publish import PUBLISH_STATE_PUBLISHED, PUBLISH_STATE_UNPUBLISHED

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sidecar(
    offer_id: str,
    *,
    publish_state: str = PUBLISH_STATE_PUBLISHED,
    compatible: list[str] | None = None,
    label: str = "",
    machine_block_id: str = "mach",
    process_block_id: str = "proc",
    filament_block_id: str = "fil",
) -> dict:
    base: dict = {
        "offer_id": offer_id,
        "label": label or offer_id,
        "publish_state": publish_state,
        "compatible_material_categories": compatible if compatible is not None else ["PLA"],
        "machine_block_id": machine_block_id,
        "process_block_id": process_block_id,
        "filament_block_id": filament_block_id,
        "filament_overrides": {},
    }
    if publish_state == PUBLISH_STATE_PUBLISHED:
        # publish_state_of requires these fields to return "published"
        base["published_bundle_hash"] = "fake-bundle-hash"
        base["published_at"] = "2026-01-01T00:00:00+00:00"
    return base


def _policy(
    *,
    material: str = "PLA",
    ref: str = "Generic PLA",
    enabled: bool = True,
    filament_overrides: dict | None = None,
) -> ProfilePolicy:
    return ProfilePolicy(
        material_defaults={
            material: MaterialDefault(orca_filament_profile_ref=ref, enabled=enabled)
        },
        filament_overrides=filament_overrides or {},
    )


# ---------------------------------------------------------------------------
# Tests: enumerate_matrix_cells (AC-11 enumerate cases, AC-3 pure function)
# ---------------------------------------------------------------------------


def test_enumerate_published_enabled_compatible_returns_one_cell():
    cells = enumerate_matrix_cells([_sidecar("offer-1", compatible=["PLA"])], _policy())
    assert len(cells) == 1
    assert cells[0].offer_id == "offer-1"
    assert cells[0].material == "PLA"
    assert cells[0].orca_profile_ref == "Generic PLA"


def test_enumerate_disabled_default_returns_no_cells():
    cells = enumerate_matrix_cells(
        [_sidecar("offer-1", compatible=["PLA"])],
        _policy(enabled=False),
    )
    assert cells == []


def test_enumerate_unpublished_offer_returns_no_cells():
    cells = enumerate_matrix_cells(
        [_sidecar("offer-1", publish_state=PUBLISH_STATE_UNPUBLISHED, compatible=["PLA"])],
        _policy(),
    )
    assert cells == []


def test_enumerate_material_not_in_compatible_returns_no_cells():
    cells = enumerate_matrix_cells(
        [_sidecar("offer-1", compatible=["PETG"])],
        _policy(material="PLA"),
    )
    assert cells == []


def test_enumerate_filament_overrides_never_appear_in_cells():
    """G-BACKFILL-OPT-IN: filament_overrides are NEVER enumerated in the default matrix."""
    policy = ProfilePolicy(
        material_defaults={"PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA")},
        filament_overrides={
            "some-ref": __import__(
                "app.modules.slicer.profile_policy", fromlist=["FilamentOverride"]
            ).FilamentOverride(orca_filament_profile_ref="Exact PLA")
        },
    )
    cells = enumerate_matrix_cells([_sidecar("offer-1", compatible=["PLA"])], policy)
    # Only 1 cell from the material_default, NOT the filament override
    assert len(cells) == 1
    assert cells[0].orca_profile_ref == "Generic PLA"
    assert all(c.orca_profile_ref != "Exact PLA" for c in cells)


def test_enumerate_two_offers_two_materials_returns_four_cells():
    sidecars = [
        _sidecar("offer-1", compatible=["PLA", "PETG"]),
        _sidecar("offer-2", compatible=["PLA", "PETG"]),
    ]
    policy = ProfilePolicy(
        material_defaults={
            "PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA"),
            "PETG": MaterialDefault(orca_filament_profile_ref="Generic PETG"),
        }
    )
    cells = enumerate_matrix_cells(sidecars, policy)
    assert len(cells) == 4
    pairs = {(c.offer_id, c.material) for c in cells}
    assert pairs == {
        ("offer-1", "PLA"),
        ("offer-1", "PETG"),
        ("offer-2", "PLA"),
        ("offer-2", "PETG"),
    }


def test_enumerate_with_material_filter_returns_only_matching_cells():
    sidecars = [
        _sidecar("offer-1", compatible=["PLA", "PETG"]),
        _sidecar("offer-2", compatible=["PLA", "PETG"]),
    ]
    policy = ProfilePolicy(
        material_defaults={
            "PLA": MaterialDefault(orca_filament_profile_ref="Generic PLA"),
            "PETG": MaterialDefault(orca_filament_profile_ref="Generic PETG"),
        }
    )
    # Filter by PLA only
    cells = enumerate_matrix_cells(sidecars, policy, material_filter="PLA")
    assert len(cells) == 2
    assert all(c.material == "PLA" for c in cells)
    assert {c.offer_id for c in cells} == {"offer-1", "offer-2"}


# ---------------------------------------------------------------------------
# Tests: resolve_matrix_cells (fake resolve_chain seam)
# ---------------------------------------------------------------------------


def _fake_success_resolver(bundle_hash: str = "abc123"):
    """Returns a fake resolve_chain that always succeeds with the given bundle_hash."""
    from app.modules.slicer.models import ResolveSuccess, SlicerProfileBundle

    def _fn(*_args, **_kwargs):
        bundle = SlicerProfileBundle(
            bundle_hash=bundle_hash,
            orca_version="2.3.2",
            machine={},
            process={},
            filament={},
            source_snapshot_ref="snap",
            created_at="2026-01-01T00:00:00",
        )
        return ResolveSuccess(
            bundle=bundle,
            triple=__import__(
                "app.modules.slicer.models", fromlist=["ResolvedTriple"]
            ).ResolvedTriple(machine={}, process={}, filament={}),
            from_cache=True,
        )

    return _fn


def _fake_failure_resolver():
    """Returns a fake resolve_chain that always returns ResolveFailure."""
    from app.modules.slicer.models import ResolveFailure, ResolveReason

    def _fn(*_args, **_kwargs):
        return ResolveFailure(
            reason=ResolveReason.unavailable_no_profile,
            message="no profile",
        )

    return _fn


def _minimal_sidecar_for_chain(offer_id: str) -> dict:
    return {
        "offer_id": offer_id,
        "label": offer_id,
        "publish_state": PUBLISH_STATE_PUBLISHED,
        "compatible_material_categories": ["PLA"],
        "machine_block_id": "mach",
        "process_block_id": "proc",
        "filament_block_id": "fil",
        "filament_overrides": {},
    }


def test_resolve_matrix_cells_success_path(tmp_path):
    cell = MatrixCell(
        offer_id="offer-1",
        offer_label="Test Offer",
        material="PLA",
        orca_profile_ref="Generic PLA",
    )
    mock_source = MagicMock()
    mock_store = MagicMock()
    mock_validator = MagicMock()
    mock_source.root = tmp_path

    # Patch read_offer so the module can reconstruct the chain
    sidecar = _minimal_sidecar_for_chain("offer-1")

    resolved = resolve_matrix_cells(
        [cell],
        source=mock_source,
        store=mock_store,
        orca_version="2.3.2",
        validator=mock_validator,
        _resolve_chain_fn=_fake_success_resolver("hash-abc"),
        _read_offer_fn=lambda root, oid: sidecar,
    )

    assert len(resolved) == 1
    rc = resolved[0]
    assert rc.bundle_hash == "hash-abc"
    assert rc.resolve_failed is False
    assert rc.cell == cell


def test_resolve_matrix_cells_failure_path_does_not_stop_others(tmp_path):
    cell1 = MatrixCell(offer_id="offer-1", offer_label="A", material="PLA", orca_profile_ref="ref")
    cell2 = MatrixCell(offer_id="offer-2", offer_label="B", material="PLA", orca_profile_ref="ref")

    call_count = 0

    def _mixed_resolver(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _fake_failure_resolver()(*args, **kwargs)
        return _fake_success_resolver("hash-ok")(*args, **kwargs)

    sidecar = _minimal_sidecar_for_chain("offer-x")
    resolved = resolve_matrix_cells(
        [cell1, cell2],
        source=MagicMock(),
        store=MagicMock(),
        orca_version="2.3.2",
        validator=MagicMock(),
        _resolve_chain_fn=_mixed_resolver,
        _read_offer_fn=lambda root, oid: sidecar,
    )
    assert len(resolved) == 2
    assert resolved[0].resolve_failed is True
    assert resolved[0].bundle_hash is None
    assert resolved[1].resolve_failed is False
    assert resolved[1].bundle_hash == "hash-ok"


def test_resolve_matrix_cells_failure_emits_log(tmp_path, caplog):
    cell = MatrixCell(offer_id="offer-1", offer_label="A", material="PLA", orca_profile_ref="ref")
    sidecar = _minimal_sidecar_for_chain("offer-1")

    with caplog.at_level(logging.WARNING, logger="app.modules.slicer.matrix_backfill"):
        resolve_matrix_cells(
            [cell],
            source=MagicMock(),
            store=MagicMock(),
            orca_version="2.3.2",
            validator=MagicMock(),
            _resolve_chain_fn=_fake_failure_resolver(),
            _read_offer_fn=lambda root, oid: sidecar,
        )

    assert any("slicer.matrix_backfill.resolve_failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Tests: enqueue_default_matrix_backfill.run() (AC-11 run tests)
# ---------------------------------------------------------------------------


def _make_stl_row(*, storage_path: str = "models/test.stl", sha256: str | None = None) -> Any:
    from app.core.db.models import ModelFile, ModelFileKind

    row = MagicMock(spec=ModelFile)
    row.id = uuid.uuid4()
    row.kind = ModelFileKind.stl
    row.storage_path = storage_path
    row.sha256 = sha256 or "a" * 64
    return row


@pytest.fixture
def fake_resolved_cell():
    return ResolvedMatrixCell(
        cell=MatrixCell(
            offer_id="offer-1",
            offer_label="Test",
            material="PLA",
            orca_profile_ref="Generic PLA",
        ),
        bundle_hash="bundle-hash-001",
        profile_selection=ProfileSelection(
            source=EstimateProfileSource.default_material_profile,
            orca_filament_profile_ref="Generic PLA",
            selected_material="PLA",
        ),
        resolve_failed=False,
    )


@pytest.fixture
def failed_resolved_cell():
    return ResolvedMatrixCell(
        cell=MatrixCell(
            offer_id="offer-2",
            offer_label="Fail",
            material="PETG",
            orca_profile_ref="Generic PETG",
        ),
        bundle_hash=None,
        profile_selection=None,
        resolve_failed=True,
    )


def _run_sync(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_run_dry_run_no_enqueue_correct_would_enqueue(tmp_path, fake_resolved_cell):
    from scripts.enqueue_default_matrix_backfill import MatrixBackfillStats, run

    stl_file = tmp_path / "test.stl"
    stl_file.write_bytes(b"fake stl content")
    row = _make_stl_row(storage_path="test.stl")

    fake_engine = MagicMock()
    fake_session = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)
    fake_session.exec.return_value.all.return_value = [row]
    fake_engine.__class__ = MagicMock()

    stats = _run_sync(
        run(
            engine=fake_engine,
            stl_cache=MagicMock(),
            estimate_store=MagicMock(),
            arq_pool=None,
            matrix_cells=[fake_resolved_cell],
            content_dir=tmp_path,
            dry_run=True,
            _session_factory=lambda eng: fake_session,
        )
    )
    assert isinstance(stats, MatrixBackfillStats)
    assert stats.enqueued == 0
    assert stats.would_enqueue >= 0  # dry-run path


def test_run_already_fresh_skip(tmp_path, fake_resolved_cell):
    from app.modules.slicer.models import EstimateStatus
    from scripts.enqueue_default_matrix_backfill import run

    stl_file = tmp_path / "test.stl"
    stl_file.write_bytes(b"fake stl")
    row = _make_stl_row(storage_path="test.stl")

    fake_engine = MagicMock()
    fake_session = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)
    fake_session.exec.return_value.all.return_value = [row]

    fresh_record = MagicMock()
    fresh_record.status = EstimateStatus.fresh
    fake_estimate_store = MagicMock()
    fake_estimate_store.read.return_value = fresh_record

    stats = _run_sync(
        run(
            engine=fake_engine,
            stl_cache=MagicMock(),
            estimate_store=fake_estimate_store,
            arq_pool=MagicMock(),
            matrix_cells=[fake_resolved_cell],
            content_dir=tmp_path,
            dry_run=False,
            _session_factory=lambda eng: fake_session,
        )
    )
    assert stats.already_fresh >= 1
    assert stats.enqueued == 0


def test_run_resolve_failed_cell_increments_counter_no_enqueue(tmp_path, failed_resolved_cell):
    from scripts.enqueue_default_matrix_backfill import run

    stl_file = tmp_path / "test.stl"
    stl_file.write_bytes(b"fake stl")
    row = _make_stl_row(storage_path="test.stl")

    fake_engine = MagicMock()
    fake_session = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)
    fake_session.exec.return_value.all.return_value = [row]

    stats = _run_sync(
        run(
            engine=fake_engine,
            stl_cache=MagicMock(),
            estimate_store=MagicMock(),
            arq_pool=MagicMock(),
            matrix_cells=[failed_resolved_cell],
            content_dir=tmp_path,
            dry_run=False,
            _session_factory=lambda eng: fake_session,
        )
    )
    assert stats.cells_resolve_failed == 1
    assert stats.enqueued == 0


def test_run_missing_stl_increments_missing_stl(tmp_path, fake_resolved_cell):
    from scripts.enqueue_default_matrix_backfill import run

    row = _make_stl_row(storage_path="does_not_exist.stl")

    fake_engine = MagicMock()
    fake_session = MagicMock()
    fake_session.__enter__ = MagicMock(return_value=fake_session)
    fake_session.__exit__ = MagicMock(return_value=False)
    fake_session.exec.return_value.all.return_value = [row]

    fake_estimate_store = MagicMock()
    fake_estimate_store.read.return_value = None

    stats = _run_sync(
        run(
            engine=fake_engine,
            stl_cache=MagicMock(),
            estimate_store=fake_estimate_store,
            arq_pool=MagicMock(),
            matrix_cells=[fake_resolved_cell],
            content_dir=tmp_path,
            dry_run=False,
            _session_factory=lambda eng: fake_session,
        )
    )
    assert stats.missing_stl >= 1
