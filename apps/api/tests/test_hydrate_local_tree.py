"""Tests for the hydrate_local_tree reverse-sync script.

Uses the FastAPI TestClient from conftest and seeds data directly via
get_engine() — same pattern as test_sot_admin_files.py.

The TestClient is passed directly into run_hydrate() as http_client.
TestClient.get/post return httpx.Response-compatible objects, so the
duck-typed interface works without adaptation.
"""

import datetime
import hashlib
import uuid
from pathlib import Path

from sqlmodel import Session

from app.core.config import get_settings
from app.core.db.models import (
    Category,
    Model,
    ModelFile,
    ModelFileKind,
)
from app.core.db.session import get_engine
from scripts.hydrate_local_tree import _load_state, run_hydrate

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_category(session: Session, *, slug: str, parent_id=None) -> Category:
    cat = Category(
        slug=slug,
        name_en=slug,
        parent_id=parent_id,
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


def _seed_model(
    session: Session,
    cat_id: uuid.UUID,
    *,
    slug: str,
    deleted: bool = False,
) -> Model:
    m = Model(
        slug=slug,
        name_en=slug,
        category_id=cat_id,
    )
    if deleted:
        m.deleted_at = datetime.datetime.now(datetime.UTC)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def _seed_file_on_disk(
    session: Session,
    model: Model,
    *,
    original_name: str = "model.stl",
    content: bytes = b"STL_CONTENT",
    kind: ModelFileKind = ModelFileKind.stl,
) -> ModelFile:
    """Seed a ModelFile row AND write the binary to PORTAL_CONTENT_DIR."""
    settings = get_settings()
    sha256 = hashlib.sha256(content).hexdigest()
    file_uuid = uuid.uuid4()
    storage_rel = f"models/{model.id}/files/{file_uuid}.bin"
    storage_abs = settings.portal_content_dir / storage_rel
    storage_abs.parent.mkdir(parents=True, exist_ok=True)
    storage_abs.write_bytes(content)

    mf = ModelFile(
        id=file_uuid,
        model_id=model.id,
        kind=kind,
        original_name=original_name,
        storage_path=storage_rel,
        sha256=sha256,
        size_bytes=len(content),
        mime_type="model/stl" if kind == ModelFileKind.stl else "image/png",
    )
    session.add(mf)
    session.commit()
    session.refresh(mf)
    return mf


# ---------------------------------------------------------------------------
# Helpers that build a HydrationContext
# ---------------------------------------------------------------------------


def _run(
    client,
    tmp_path: Path,
    *,
    kinds: set | None = None,
    include_soft_deleted: bool = False,
    prune_deleted: bool = False,
    dry_run: bool = False,
    state_path: Path | None = None,
) -> dict:
    """Thin wrapper that calls run_hydrate with sensible defaults for tests."""
    return run_hydrate(
        http_client=client,
        portal_url="",  # TestClient uses relative URLs
        target=tmp_path,
        kinds=kinds if kinds is not None else {"stl"},
        bearer_token="",  # no auth on public read endpoints in tests
        include_soft_deleted=include_soft_deleted,
        prune_deleted=prune_deleted,
        dry_run=dry_run,
        state_path=state_path,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_hydrate_creates_local_tree(client, tmp_path):
    """Seed 1 category + 1 model + 1 STL file.  Run hydrate.  Assert file exists."""
    engine = get_engine()
    content = b"FAKE_STL_TREE"
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-decorum-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-dragon-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(s, m, original_name="dragon.stl", content=content)

    summary = _run(client, tmp_path)

    assert summary["n_models"] >= 1
    assert summary["m_downloaded"] >= 1

    # Find the downloaded file under tmp_path
    found = list(tmp_path.rglob("dragon.stl"))
    assert len(found) >= 1, f"dragon.stl not found under {tmp_path}"
    assert found[0].read_bytes() == content


def test_hydrate_skips_in_sync_files(client, tmp_path):
    """Run hydrate twice; second run skips all files (state matches sha)."""
    engine = get_engine()
    content = b"STABLE_CONTENT_XYZ"
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-skip-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-skip-m-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(s, m, original_name="skip.stl", content=content)

    s1 = _run(client, tmp_path)
    assert s1["m_downloaded"] >= 1

    s2 = _run(client, tmp_path)
    # On second run all previously downloaded files must be skipped
    assert s2["m_downloaded"] == 0
    assert s2["k_skipped"] >= 1


def test_hydrate_writes_state_file(client, tmp_path):
    """State file has correct format after a run."""
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-state-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-state-m-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(s, m, original_name="state.stl", content=b"STATE_CONTENT")

    state_path = tmp_path / ".hydrate-state.json"
    _run(client, tmp_path, state_path=state_path)

    assert state_path.exists(), "state file not created"
    state = _load_state(state_path)
    assert state["version"] == 1
    assert "last_run_at" in state
    assert "paths" in state
    assert isinstance(state["paths"], dict)
    # At least one path entry with a sha256 hex value
    assert any(len(v) == 64 for v in state["paths"].values())


def test_hydrate_dry_run_writes_nothing(client, tmp_path):
    """--dry-run produces no local files and no state file."""
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-dry-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-dry-m-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(s, m, original_name="dry.stl", content=b"DRY_CONTENT")

    state_path = tmp_path / ".hydrate-state.json"
    _run(client, tmp_path, dry_run=True, state_path=state_path)

    # No files created
    created = [f for f in tmp_path.rglob("*") if f.is_file()]
    assert created == [], f"dry-run created files: {created}"

    # State file not written
    assert not state_path.exists(), "dry-run must not write state file"


def test_hydrate_filters_by_kind(client, tmp_path):
    """kinds={'stl'} only downloads STL; image file is not downloaded."""
    engine = get_engine()
    stl_content = b"STL_FILTER_CONTENT"
    img_content = b"PNG_FILTER_CONTENT"
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-filt-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-filt-m-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(
            s, m, original_name="part.stl", content=stl_content, kind=ModelFileKind.stl
        )
        _seed_file_on_disk(
            s, m, original_name="thumb.png", content=img_content, kind=ModelFileKind.image
        )

    _run(client, tmp_path, kinds={"stl"})

    stl_files = list(tmp_path.rglob("part.stl"))
    img_files = list(tmp_path.rglob("thumb.png"))
    assert len(stl_files) >= 1, "stl file should have been downloaded"
    assert len(img_files) == 0, "image file should NOT have been downloaded (not in kinds)"


def test_hydrate_excludes_soft_deleted_by_default(client, tmp_path):
    """Soft-deleted models are not mirrored without --include-soft-deleted."""
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-del-{uuid.uuid4().hex[:6]}")
        m = _seed_model(
            s, cat.id, slug=f"ht-del-m-{uuid.uuid4().hex[:6]}", deleted=True
        )
        _seed_file_on_disk(s, m, original_name="deleted.stl", content=b"DELETED")

    _run(client, tmp_path, include_soft_deleted=False)
    found = list(tmp_path.rglob("deleted.stl"))
    assert found == [], "soft-deleted model file must not appear in default mode"


def test_hydrate_includes_soft_deleted_with_flag(client, tmp_path):
    """With --include-soft-deleted, soft-deleted models ARE mirrored."""
    engine = get_engine()
    content = b"DELETED_BUT_INCLUDED"
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-inc-{uuid.uuid4().hex[:6]}")
        m = _seed_model(
            s, cat.id, slug=f"ht-inc-m-{uuid.uuid4().hex[:6]}", deleted=True
        )
        _seed_file_on_disk(s, m, original_name="included.stl", content=content)

    _run(client, tmp_path, include_soft_deleted=True)
    found = list(tmp_path.rglob("included.stl"))
    assert len(found) >= 1, "soft-deleted file should appear with --include-soft-deleted"
    assert found[0].read_bytes() == content


def test_hydrate_handles_pagination(client, tmp_path):
    """Seed 51 models; hydrate must walk all pages and download all files."""
    engine = get_engine()
    # Use a dedicated category for isolation
    cat_slug = f"ht-page-{uuid.uuid4().hex[:6]}"
    with Session(engine) as s:
        cat = _seed_category(s, slug=cat_slug)
        for i in range(51):
            m = _seed_model(
                s, cat.id, slug=f"ht-pg-m{i:03d}-{uuid.uuid4().hex[:4]}"
            )
            _seed_file_on_disk(s, m, original_name=f"pg{i:03d}.stl", content=f"PG{i}".encode())

    summary = _run(client, tmp_path)
    assert summary["n_models"] >= 51

    # All 51 files should be present
    stl_files = list(tmp_path.rglob("*.stl"))
    # We only check that our 51 are there (other tests' files may also be present)
    our_files = [f for f in stl_files if f.stem.startswith("pg") and f.name.endswith(".stl")]
    assert len(our_files) >= 51, f"Expected >=51 pg*.stl files, got {len(our_files)}"


def test_hydrate_layout_uses_category_subcategory_slug(client, tmp_path):
    """Directory tree must be: <cat>/<subcat>/<model-slug>-<short-uuid>/<original_name>.

    Post-E4.4-followup the suffix is the model's UUID hex with dashes stripped,
    truncated to 8 chars (was the legacy_id pre-DROP)."""
    engine = get_engine()
    root_slug = f"ht-lay-root-{uuid.uuid4().hex[:6]}"
    sub_slug = f"ht-lay-sub-{uuid.uuid4().hex[:6]}"
    with Session(engine) as s:
        root = _seed_category(s, slug=root_slug)
        sub = _seed_category(s, slug=sub_slug, parent_id=root.id)
        m = _seed_model(s, sub.id, slug="ht-lay-model")
        _seed_file_on_disk(s, m, original_name="layout.stl", content=b"LAYOUT")
        suffix = m.id.hex[:8]

    _run(client, tmp_path)

    expected = tmp_path / root_slug / sub_slug / f"ht-lay-model-{suffix}" / "layout.stl"
    assert expected.exists(), (
        f"Expected file at {expected}; found: {list(tmp_path.rglob('layout.stl'))}"
    )


def test_hydrate_idempotent_summary_counts(client, tmp_path):
    """First run: N downloaded, 0 skipped.  Second run: 0 downloaded, N skipped."""
    engine = get_engine()
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-idem-{uuid.uuid4().hex[:6]}")
        for i in range(3):
            m = _seed_model(
                s, cat.id, slug=f"ht-id-m{i}-{uuid.uuid4().hex[:4]}"
            )
            _seed_file_on_disk(s, m, original_name=f"id{i}.stl", content=f"IDEM{i}".encode())

    state_path = tmp_path / ".hydrate-state.json"

    s1 = _run(client, tmp_path, state_path=state_path)
    assert s1["m_downloaded"] >= 3
    assert s1["k_skipped"] == 0

    s2 = _run(client, tmp_path, state_path=state_path)
    assert s2["m_downloaded"] == 0
    assert s2["k_skipped"] >= 3


def test_hydrate_prune_deleted_removes_local_files_not_in_master(client, tmp_path):
    """With --prune-deleted, a local file tracked in state but missing from master is deleted."""
    engine = get_engine()
    content = b"PRUNE_ME"
    with Session(engine) as s:
        cat = _seed_category(s, slug=f"ht-prune-{uuid.uuid4().hex[:6]}")
        m = _seed_model(s, cat.id, slug=f"ht-prune-m-{uuid.uuid4().hex[:6]}")
        _seed_file_on_disk(s, m, original_name="live.stl", content=content)

    state_path = tmp_path / ".hydrate-state.json"

    # First run: download the file
    _run(client, tmp_path, state_path=state_path)
    live_files = list(tmp_path.rglob("live.stl"))
    assert len(live_files) == 1

    # Manually inject a stale entry into the state file (simulates a file
    # that was on master but was later removed from master)
    import json

    state = json.loads(state_path.read_text())
    stale_key = "ht-prune-orphan/orphan-999/orphan.stl"
    state["paths"][stale_key] = "a" * 64
    # Also create the orphan file on disk
    orphan_file = tmp_path / stale_key
    orphan_file.parent.mkdir(parents=True, exist_ok=True)
    orphan_file.write_bytes(b"ORPHAN")
    state_path.write_text(json.dumps(state, indent=2))

    # Second run with prune_deleted=True
    _run(client, tmp_path, prune_deleted=True, state_path=state_path)

    # Orphan file should be gone
    assert not orphan_file.exists(), "prune_deleted must remove stale local file"
    # Live file must still be there
    live_files_after = list(tmp_path.rglob("live.stl"))
    assert len(live_files_after) >= 1, "live file must survive pruning"
