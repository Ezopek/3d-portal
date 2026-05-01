import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config_for_tests import override_catalog_paths
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(FIXTURES / "catalog"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=FIXTURES / "index.json")
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_download_stl(client):
    r = client.get("/api/files/001/Dragon.stl")
    assert r.status_code == 200
    assert "ETag" in r.headers


def test_serve_inline_by_default(client):
    r = client.get("/api/files/001/Dragon.stl")
    assert r.status_code == 200
    assert "content-disposition" not in {k.lower() for k in r.headers}


def test_download_query_sets_attachment(client):
    r = client.get("/api/files/001/Dragon.stl?download=1")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert 'filename="Dragon.stl"' in cd


def test_etag_round_trip_returns_304(client):
    r1 = client.get("/api/files/001/Dragon.stl")
    etag = r1.headers["ETag"]
    r2 = client.get("/api/files/001/Dragon.stl", headers={"If-None-Match": etag})
    assert r2.status_code == 304


def test_path_traversal_rejected(client):
    r = client.get("/api/files/001/..%2F..%2Fetc/passwd")
    assert r.status_code in {400, 404}


def test_unknown_model_returns_404(client):
    r = client.get("/api/files/999/anything")
    assert r.status_code == 404


def test_bundle_single_file_returns_file_directly(client):
    # Dragon model has a single Dragon.stl in the fixture catalog.
    r = client.get("/api/files/001/bundle")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "Dragon.stl" in cd
    # Single-file response is the raw file, not a zip.
    assert r.headers.get("content-type", "").lower() != "application/zip"


def test_bundle_unknown_model_returns_404(client):
    r = client.get("/api/files/999/bundle")
    assert r.status_code == 404


@pytest.fixture
def multi_file_client(tmp_path, monkeypatch):
    """Catalog with model 001 containing multiple printable files in subdirs."""
    catalog = tmp_path / "catalog"
    model_dir = catalog / "decorum" / "dragon"
    (model_dir / "parts").mkdir(parents=True)
    (model_dir / "Dragon.stl").write_bytes(b"solid dragon\n")
    (model_dir / "parts" / "wing.stl").write_bytes(b"solid wing\n")
    (model_dir / "Dragon.3mf").write_bytes(b"\x504\x034" + b"3mf payload")
    (model_dir / "images").mkdir()
    (model_dir / "images" / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (model_dir / "notes.txt").write_text("ignored")  # non-printable

    index = tmp_path / "index.json"
    index.write_text(
        '[{"id":"001","name_en":"Dragon Model v2","name_pl":"Smok",'
        '"path":"decorum/dragon","category":"decorations","subcategory":"",'
        '"tags":[],"source":"unknown","printables_id":null,"thangs_id":null,'
        '"makerworld_id":null,"source_url":null,"rating":null,'
        '"status":"not_printed","notes":"","thumbnail":null,'
        '"date_added":"2026-04-12","prints":[]}]'
    )

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(catalog))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@localhost.localdomain")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=index)
        yield c
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_bundle_multiple_files_returns_zip(multi_file_client):
    r = multi_file_client.get("/api/files/001/bundle")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/zip")
    cd = r.headers.get("content-disposition", "")
    # safe_filename turns "Dragon Model v2" into "Dragon_Model_v2"
    assert "Dragon_Model_v2.zip" in cd or "Dragon_Model_v2" in cd

    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = sorted(z.namelist())
    assert names == ["Dragon.3mf", "Dragon.stl", "parts/wing.stl"]
    assert z.read("Dragon.stl") == b"solid dragon\n"
    assert z.read("parts/wing.stl") == b"solid wing\n"


def test_bundle_no_printable_files_returns_404(tmp_path, monkeypatch):
    """Bundle 404s when the model directory has no printable extensions."""
    catalog = tmp_path / "catalog"
    model_dir = catalog / "decorum" / "dragon"
    model_dir.mkdir(parents=True)
    (model_dir / "notes.txt").write_text("only docs")

    index = tmp_path / "index.json"
    index.write_text(
        '[{"id":"001","name_en":"Dragon","name_pl":"Smok",'
        '"path":"decorum/dragon","category":"decorations","subcategory":"",'
        '"tags":[],"source":"unknown","printables_id":null,"thangs_id":null,'
        '"makerworld_id":null,"source_url":null,"rating":null,'
        '"status":"not_printed","notes":"","thumbnail":null,'
        '"date_added":"2026-04-12","prints":[]}]'
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(catalog))
    monkeypatch.setenv("ADMIN_EMAIL", "a@l")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=index)
        r = c.get("/api/files/001/bundle")
        assert r.status_code == 404
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_bundle_extensions_configurable(tmp_path, monkeypatch):
    """DOWNLOAD_EXTENSIONS env var controls which files are bundled."""
    catalog = tmp_path / "catalog"
    model_dir = catalog / "decorum" / "dragon"
    model_dir.mkdir(parents=True)
    (model_dir / "Dragon.stl").write_bytes(b"stl")
    (model_dir / "Dragon.3mf").write_bytes(b"3mf")

    index = tmp_path / "index.json"
    index.write_text(
        '[{"id":"001","name_en":"Dragon","name_pl":"Smok",'
        '"path":"decorum/dragon","category":"decorations","subcategory":"",'
        '"tags":[],"source":"unknown","printables_id":null,"thangs_id":null,'
        '"makerworld_id":null,"source_url":null,"rating":null,'
        '"status":"not_printed","notes":"","thumbnail":null,'
        '"date_added":"2026-04-12","prints":[]}]'
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(catalog))
    monkeypatch.setenv("ADMIN_EMAIL", "a@l")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("DOWNLOAD_EXTENSIONS", "stl")  # only STL, ignore 3MF

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=index)
        r = c.get("/api/files/001/bundle")
        # Only one printable now, so it's served as a single file.
        assert r.status_code == 200
        cd = r.headers.get("content-disposition", "")
        assert "Dragon.stl" in cd
        # 3MF was ignored, so this is not a zip.
        assert "zip" not in r.headers.get("content-type", "")
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_bundle_collision_with_file_named_bundle(tmp_path, monkeypatch):
    """A file literally named `bundle` (any printable ext) at root still works
    via the catch-all because we test the bundle endpoint, not a file path."""
    # No-op safety guard test — verifies a model with a quirky filename like
    # bundle.stl still gets bundled correctly.
    catalog = tmp_path / "catalog"
    model_dir = catalog / "decorum" / "dragon"
    model_dir.mkdir(parents=True)
    (model_dir / "bundle.stl").write_bytes(b"odd")
    (model_dir / "wing.stl").write_bytes(b"wing")

    index = tmp_path / "index.json"
    index.write_text(
        '[{"id":"001","name_en":"Dragon","name_pl":"Smok",'
        '"path":"decorum/dragon","category":"decorations","subcategory":"",'
        '"tags":[],"source":"unknown","printables_id":null,"thangs_id":null,'
        '"makerworld_id":null,"source_url":null,"rating":null,'
        '"status":"not_printed","notes":"","thumbnail":null,'
        '"date_added":"2026-04-12","prints":[]}]'
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/f.db")
    monkeypatch.setenv("CATALOG_DATA_DIR", str(catalog))
    monkeypatch.setenv("ADMIN_EMAIL", "a@l")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    monkeypatch.setenv("JWT_SECRET", "test")

    from app.core.config import get_settings
    from app.core.db.session import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        override_catalog_paths(app, index_path=index)
        r = c.get("/api/files/001/bundle")
        assert r.status_code == 200
        # Two printable files, so ZIP.
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert sorted(z.namelist()) == ["bundle.stl", "wing.stl"]
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_serve_falls_back_to_renders_volume(client, tmp_path, monkeypatch):
    # The conftest autouse fixture and per-test fixture set CATALOG_DATA_DIR.
    # We need RENDERS_DIR to point at a tmp dir we control.
    renders_root = tmp_path / "renders"
    (renders_root / "001").mkdir(parents=True)
    # Create a fake render PNG.
    (renders_root / "001" / "iso.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("RENDERS_DIR", str(renders_root))
    from app.core.config import get_settings

    get_settings.cache_clear()

    r = client.get("/api/files/001/iso.png")
    assert r.status_code == 200
    # Expect ETag header
    assert "ETag" in r.headers
