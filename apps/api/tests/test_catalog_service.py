from pathlib import Path

import pytest

from app.modules.catalog.service import CatalogService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def service() -> CatalogService:
    return CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=FIXTURES / "index.json",
    )


def test_list_returns_all_models(service):
    response = service.list_models()
    assert response.total == 3
    assert {m.id for m in response.models} == {"001", "002", "003"}


def test_list_resolves_thumbnail_url_from_images_dir(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # Dragon has images/ → prefer that over any computed render.
    assert by_id["001"].thumbnail_url == "/api/files/001/images/Dragon.png"


def test_list_falls_back_to_computed_render_when_no_images(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # Vase has no images/ dir but has fixtures/renders/002/front.png.
    assert by_id["002"].thumbnail_url == "/api/files/002/front.png"


def test_list_thumbnail_null_when_no_images_and_no_renders(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    # Holder (003) has neither images/ nor renders/003/front.png.
    assert by_id["003"].thumbnail_url is None


def test_list_has_3d_true_when_stl_present(service):
    response = service.list_models()
    by_id = {m.id: m for m in response.models}
    assert by_id["001"].has_3d is True
    assert by_id["003"].has_3d is True


def test_get_model_returns_full_payload(service):
    m = service.get_model("002")
    assert m is not None
    assert m.name_pl == "Wazon"
    assert len(m.prints) == 1


def test_get_model_returns_none_for_missing_id(service):
    assert service.get_model("999") is None


def test_list_files_returns_relative_paths(service):
    files = service.list_files("001")
    assert "Dragon.stl" in files
    assert "images/Dragon.png" in files


def test_refresh_invalidates_cache(service, tmp_path):
    # Build a separate service whose index can be mutated.
    new_index = tmp_path / "index.json"
    new_index.write_text("[]")
    service2 = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=new_index,
    )
    service2.list_models()  # warm
    # Replace contents.
    new_index.write_text(
        '[{"id":"001","name_en":"X","name_pl":"X","path":"x","category":"decorations","subcategory":"","tags":[],"source":"unknown","printables_id":null,"thangs_id":null,"makerworld_id":null,"source_url":null,"rating":null,"status":"not_printed","notes":"","thumbnail":null,"date_added":"2026-04-29"}]'
    )
    service2.refresh()
    assert service2.list_models().total == 1


def test_missing_index_returns_empty_catalog_without_raising(tmp_path):
    # Index path that does not exist must not crash the service —
    # transient gap during sync should yield empty catalog, not 500.
    missing_index = tmp_path / "nope" / "index.json"
    service = CatalogService(
        catalog_dir=FIXTURES / "catalog",
        renders_dir=FIXTURES / "renders",
        index_path=missing_index,
    )
    response = service.list_models()
    assert response.total == 0
    assert response.models == []
    assert service.get_model("001") is None
