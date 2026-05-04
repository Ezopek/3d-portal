from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.db.models import User, UserRole
from app.modules.catalog.service import CatalogService
from app.modules.catalog.thumbnail_overrides import ThumbnailOverrideRepo

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def repo() -> ThumbnailOverrideRepo:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    # Seed an admin user so FK constraints on set_by_user_id are satisfied.
    with Session(engine) as s:
        admin = User(email="a@b", display_name="A", role=UserRole.admin, password_hash="x")
        s.add(admin)
        s.commit()
        s.refresh(admin)
        admin_id = admin.id
    r = ThumbnailOverrideRepo(engine)
    r._admin_id = admin_id  # stash for test use
    return r


@pytest.fixture
def service(repo) -> CatalogService:
    return CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=FIXTURES / "index.json",
        overrides=repo,
    )


def test_list_returns_all_models(service):
    response = service.list_models()
    assert response.total == 3
    assert {m.id for m in response.models} == {"001", "002", "003"}


def test_list_resolves_thumbnail_url_from_images_dir(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # Dragon (001) has images/Dragon.png — wins over any prints or renders.
    assert by_id["001"].thumbnail_url == "/api/files/001/images/Dragon.png"


def test_list_falls_back_to_newest_print_when_no_images(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # Vase (002) has no images/ but has two prints; newest by date wins.
    assert by_id["002"].thumbnail_url == "/api/files/002/prints/2026-04-30-vase-newest.jpg"


def test_list_falls_back_to_iso_render_when_no_images_no_prints(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # 003 (Holder): no images/, no prints, but renders/003/iso.png exists.
    assert by_id["003"].thumbnail_url == "/api/files/003/iso.png"


def test_list_thumbnail_null_when_no_candidates(repo, tmp_path):
    empty_renders = tmp_path / "empty_renders"
    empty_renders.mkdir()
    s = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=empty_renders,
        index_path=FIXTURES / "index.json",
        overrides=repo,
    )
    by_id = {m.id: m for m in s.list_models().models}
    assert by_id["003"].thumbnail_url is None


def test_list_uses_override_when_set(service, repo):
    # Need an iso render for 001 — create on demand.
    iso_dir = FIXTURES / "renders" / "001"
    iso_dir.mkdir(parents=True, exist_ok=True)
    iso = iso_dir / "iso.png"
    iso.touch()
    try:
        repo.set(model_id="001", relative_path="iso.png", user_id=repo._admin_id)
        by_id = {m.id: m for m in service.list_models().models}
        assert by_id["001"].thumbnail_url == "/api/files/001/iso.png"
    finally:
        iso.unlink(missing_ok=True)


def test_list_silent_fallback_when_override_target_missing(service, repo):
    repo.set(model_id="001", relative_path="prints/ghost.jpg", user_id=repo._admin_id)
    by_id = {m.id: m for m in service.list_models().models}
    # Falls back to the next chain step: images/Dragon.png.
    assert by_id["001"].thumbnail_url == "/api/files/001/images/Dragon.png"


def test_list_has_3d_true_when_stl_present(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    assert by_id["001"].has_3d is True
    assert by_id["003"].has_3d is True


def test_list_has_3d_true_for_uppercase_extension(repo, tmp_path):
    import json as _json

    catalog = tmp_path / "catalog"
    (catalog / "decorum/uppercase").mkdir(parents=True)
    (catalog / "decorum/uppercase/Model.STL").write_bytes(b"")
    (tmp_path / "renders").mkdir()
    index_path = tmp_path / "index.json"
    index_path.write_text(
        _json.dumps(
            [
                {
                    "id": "uc1",
                    "name_en": "UC",
                    "name_pl": "UC",
                    "path": "decorum/uppercase",
                    "category": "decorations",
                    "subcategory": "",
                    "tags": [],
                    "source": "unknown",
                    "printables_id": None,
                    "thangs_id": None,
                    "makerworld_id": None,
                    "source_url": None,
                    "rating": None,
                    "status": "not_printed",
                    "notes": "",
                    "thumbnail": None,
                    "date_added": "2026-04-29",
                    "prints": [],
                }
            ]
        )
    )
    svc = CatalogService(
        catalog_dir=catalog,
        renders_dir=tmp_path / "renders",
        index_path=index_path,
        overrides=repo,
    )
    response = svc.list_models()
    assert response.models[0].has_3d is True


def test_get_model_returns_full_payload(service):
    m = service.get_model("002")
    assert m is not None
    assert m.name_pl == "Wazon"
    assert len(m.prints) == 2


def test_get_model_returns_none_for_missing_id(service):
    assert service.get_model("999") is None


def test_list_files_returns_relative_paths(service):
    files = service.list_files("001")
    assert "Dragon.stl" in files
    assert "images/Dragon.png" in files


def test_refresh_invalidates_cache(repo, tmp_path):
    new_index = tmp_path / "index.json"
    new_index.write_text("[]")
    service2 = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=new_index,
        overrides=repo,
    )
    service2.list_models()
    new_index.write_text(
        '[{"id":"001","name_en":"X","name_pl":"X","path":"x","category":"decorations","subcategory":"","tags":[],"source":"unknown","printables_id":null,"thangs_id":null,"makerworld_id":null,"source_url":null,"rating":null,"status":"not_printed","notes":"","thumbnail":null,"date_added":"2026-04-29","prints":[]}]'
    )
    service2.refresh()
    assert service2.list_models().total == 1


def test_cache_reloads_when_index_mtime_changes(repo, tmp_path):
    # Multi-worker safety net: a sibling uvicorn worker that did not
    # receive the refresh-catalog POST should still pick up the new
    # state once it sees a fresher index file. Otherwise readers race
    # against whichever worker handled the refresh.
    import os

    index = tmp_path / "index.json"
    index.write_text("[]")
    svc = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=index,
        overrides=repo,
    )
    assert svc.list_models().total == 0

    index.write_text(
        '[{"id":"001","name_en":"X","name_pl":"X","path":"x","category":"decorations",'
        '"subcategory":"","tags":[],"source":"unknown","printables_id":null,'
        '"thangs_id":null,"makerworld_id":null,"source_url":null,"rating":null,'
        '"status":"not_printed","notes":"","thumbnail":null,"date_added":"2026-04-29",'
        '"prints":[]}]'
    )
    # Force a strictly-greater mtime so this works even on filesystems
    # where two writes inside the same test land on the same timestamp.
    st = index.stat()
    os.utime(index, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

    # Note: no .refresh() call — cache must invalidate on its own.
    assert svc.list_models().total == 1


def test_missing_index_returns_empty_catalog_without_raising(repo, tmp_path):
    # Index path that does not exist must not crash the service —
    # transient gap during sync should yield empty catalog, not 500.
    missing_index = tmp_path / "nope" / "index.json"
    service = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=missing_index,
        overrides=repo,
    )
    response = service.list_models()
    assert response.total == 0
    assert response.models == []
    assert service.get_model("001") is None


def test_image_count_includes_images_dir(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # 001 (Dragon) has at least one file in images/ in the fixture catalog;
    # exact count depends on fixtures so we assert >= 1.
    assert by_id["001"].image_count >= 1


def test_image_count_includes_prints(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # 002 (Vase) has prints in fixtures, no images/.
    # The service counts each Print whose path resolves to an existing image.
    assert by_id["002"].image_count >= 1


def test_image_count_includes_renders_when_iso_exists(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # 003 (Holder) has only renders/003/iso.png in fixtures → +4 (iso/front/side/top).
    assert by_id["003"].image_count == 4


def test_image_count_zero_when_nothing(repo, tmp_path):
    empty_renders = tmp_path / "empty_renders"
    empty_renders.mkdir()
    s = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=empty_renders,
        index_path=FIXTURES / "index.json",
        overrides=repo,
    )
    by_id = {m.id: m for m in s.list_models().models}
    # 003 has nothing visible without renders.
    assert by_id["003"].image_count == 0
