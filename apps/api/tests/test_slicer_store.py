"""Tests for the append-only on-disk bundle + snapshot store (Story 32.1, AC-6).

The store mirrors the render/STL hash-fanout layout
(``<root>/bundles/<hash[:2]>/<hash>.json``). Writing a bundle that already
exists at its ``bundle_hash`` is an idempotent no-op (the hash IS the identity);
a re-tune produces a NEW hash + file and never mutates the old one. No SQL DB.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.modules.slicer.bundle_store import BundleStore
from app.modules.slicer.models import (
    PrintIntentPreset,
    ResolveSuccess,
    SlicerProfileBundle,
    SourceProfileSnapshot,
)
from app.modules.slicer.overrides import NoopOverrideProvider
from app.modules.slicer.resolver import VendoredProfileSource, resolve
from app.modules.slicer.validation import NullCliValidator

FIXTURES = Path(__file__).parent / "fixtures" / "slicer"

PLA_INTENT = PrintIntentPreset(
    name="PLA standard",
    material_class="PLA",
    quality_tier="standard",
    printer_ref="creality-k1-max-microswiss-hf",
)


def _bundle(bundle_hash: str, created_at: str = "2026-06-01T00:00:00+00:00") -> SlicerProfileBundle:
    return SlicerProfileBundle(
        bundle_hash=bundle_hash,
        orca_version="2.3.2",
        machine={"m": 1},
        process={"p": 1},
        filament={"f": 1},
        source_snapshot_ref="snap-ref",
        spoolman_overrides_ref=None,
        created_at=created_at,
    )


def test_persist_bundle_is_idempotent_on_same_hash(tmp_path):
    store = BundleStore(tmp_path)
    h = "ab" + "c" * 62
    p1 = store.write_bundle(_bundle(h))
    content1 = p1.read_text()
    # Re-write with a DIFFERENT created_at but the SAME hash — must be a no-op.
    p2 = store.write_bundle(_bundle(h, created_at="2099-01-01T00:00:00+00:00"))
    assert p1 == p2
    assert p2.read_text() == content1  # first write wins; file never mutated
    assert len(list((tmp_path / "bundles").rglob("*.json"))) == 1


def test_retune_creates_new_bundle_file_leaving_old_intact(tmp_path):
    store = BundleStore(tmp_path)
    b1 = _bundle("11" + "a" * 62)
    b2 = _bundle("22" + "b" * 62)
    store.write_bundle(b1)
    store.write_bundle(b2)
    assert store.has_bundle(b1.bundle_hash)
    assert store.has_bundle(b2.bundle_hash)
    assert len(list((tmp_path / "bundles").rglob("*.json"))) == 2


def test_fanout_directory_uses_two_char_prefix(tmp_path):
    store = BundleStore(tmp_path)
    p = store.write_bundle(_bundle("ab" + "c" * 62))
    assert p.parent.name == "ab"
    assert p.parent.parent.name == "bundles"


def test_load_bundle_roundtrips(tmp_path):
    store = BundleStore(tmp_path)
    h = "de" + "f" * 62
    store.write_bundle(_bundle(h))
    loaded = store.load_bundle(h)
    assert isinstance(loaded, SlicerProfileBundle)
    assert loaded.bundle_hash == h
    assert loaded.machine == {"m": 1}


def test_load_missing_bundle_returns_none(tmp_path):
    store = BundleStore(tmp_path)
    assert store.load_bundle("00" + "0" * 62) is None
    assert store.has_bundle("00" + "0" * 62) is False


def test_snapshot_records_source_path_hash_and_orca_version(tmp_path):
    store = BundleStore(tmp_path)
    out = resolve(
        PLA_INTENT,
        source=VendoredProfileSource(FIXTURES),
        store=store,
        override_provider=NoopOverrideProvider(),
        validator=NullCliValidator(),
        orca_version="2.3.2",
    )
    assert isinstance(out, ResolveSuccess)
    snap = store.load_snapshot(out.bundle.source_snapshot_ref)
    assert isinstance(snap, SourceProfileSnapshot)
    assert snap.orca_version == "2.3.2"
    assert snap.resolver_version  # provenance: bumped when merge/normalize changes
    assert snap.source_user_partial_hash  # content hash of the raw user partials
    assert str(FIXTURES) in snap.source_system_tree_ref


def test_snapshot_write_is_idempotent(tmp_path):
    store = BundleStore(tmp_path)
    snap = SourceProfileSnapshot(
        source_system_tree_ref="/vendored/root",
        source_system_tree_hash="cafebabe",
        source_user_partial_hash="deadbeef",
        orca_version="2.3.2",
        resolver_version="1",
        snapshot_hash="aa" + "b" * 62,
        created_at="2026-06-01T00:00:00+00:00",
    )
    p1 = store.write_snapshot(snap)
    content1 = p1.read_text()
    p2 = store.write_snapshot(snap)
    assert p1 == p2
    assert p2.read_text() == content1
    assert len(list((tmp_path / "snapshots").rglob("*.json"))) == 1
    # sanity: the persisted snapshot is valid JSON
    json.loads(content1)


def test_snapshot_hash_reflects_system_tree_content(tmp_path):
    # Review fix #3: an IN-PLACE change to a vendored system profile (SAME root path,
    # SAME user partials) MUST produce a new snapshot_hash — the snapshot provenance
    # binds the CONTENT identity of the system tree, not just its root path.
    import shutil

    src_root = tmp_path / "vend"
    shutil.copytree(FIXTURES, src_root)

    def _resolve_snapshot_ref(store_name: str) -> str:
        out = resolve(
            PLA_INTENT,
            source=VendoredProfileSource(src_root),
            store=BundleStore(tmp_path / store_name),
            override_provider=NoopOverrideProvider(),
            validator=NullCliValidator(),
            orca_version="2.3.2",
        )
        assert isinstance(out, ResolveSuccess)
        return out.bundle.source_snapshot_ref

    snap1 = _resolve_snapshot_ref("s1")
    # Mutate an UNREFERENCED system profile in place: the resolved triple (and thus
    # bundle_hash) is unchanged, isolating the snapshot-provenance behavior.
    (src_root / "system" / "zz_unreferenced.json").write_text(
        json.dumps({"name": "zz_unreferenced", "from": "system", "x": "1"})
    )
    snap2 = _resolve_snapshot_ref("s2")
    assert snap1 != snap2  # system-tree content change ⇒ new snapshot identity


def test_write_bundle_first_write_wins_even_if_exists_check_races(tmp_path, monkeypatch):
    # Review fix #4: the append-only publish must be first-write-wins even when the
    # exists() pre-check races (returns False after another writer already
    # published). Force that race by stubbing exists() to False, then prove the
    # second write does NOT clobber the first.
    store = BundleStore(tmp_path)
    h = "cc" + "d" * 62
    first = _bundle(h, created_at="2026-01-01T00:00:00+00:00")
    second = _bundle(h, created_at="2099-12-31T23:59:59+00:00")
    monkeypatch.setattr(Path, "exists", lambda self: False)
    store.write_bundle(first)
    store.write_bundle(second)
    monkeypatch.undo()
    loaded = store.load_bundle(h)
    assert loaded is not None
    assert loaded.created_at == "2026-01-01T00:00:00+00:00"  # first write wins
    assert len(list((tmp_path / "bundles").rglob("*.json"))) == 1


def test_default_store_dir_is_root_no_double_bundles_nesting(monkeypatch):
    # Review fix #5: SLICER_BUNDLE_STORE_DIR default is the store ROOT; the store
    # adds the single 'bundles/' child — NOT '/data/content/slicer/bundles/bundles'.
    from app.core.config import Settings

    monkeypatch.delenv("SLICER_BUNDLE_STORE_DIR", raising=False)
    settings = Settings()
    store = BundleStore(settings.slicer_bundle_store_dir)
    h = "deadbeef" + "0" * 56
    assert store.bundle_path(h).as_posix() == f"/data/content/slicer/bundles/de/{h}.json"
