import uuid

from sqlmodel import Session

from app.core.db.models import Category, Model, ModelFile, ModelFileKind
from app.core.db.session import get_engine


def _seed_model_with_stl(slug_suffix: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (model_id, stl_file_id)."""
    suffix = uuid.uuid4().hex[:8]
    with Session(get_engine()) as s:
        cat = Category(slug=f"render-cat-{suffix}", name_en="x")
        s.add(cat)
        s.commit()
        s.refresh(cat)
        m = Model(slug=f"render-m-{suffix}", name_en="m", category_id=cat.id)
        s.add(m)
        s.commit()
        s.refresh(m)
        f = ModelFile(
            model_id=m.id,
            kind=ModelFileKind.stl,
            original_name="thing.stl",
            storage_path=f"models/{m.id}/files/{uuid.uuid4()}.stl",
            sha256=uuid.uuid4().hex,
            size_bytes=1024,
            mime_type="model/stl",
        )
        s.add(f)
        s.commit()
        s.refresh(f)
        return m.id, f.id


def test_admin_trigger_render_enqueues_job(client, _patch_arq_pool):
    model_id, _stl_id = _seed_model_with_stl("trigger")
    # Use the admin token already wired by the test fixtures (tests/test_auth.py shows the recipe).
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    token = r.json()["access_token"]

    _patch_arq_pool.enqueue_job.reset_mock()
    r2 = client.post(
        f"/api/admin/models/{model_id}/render",
        headers={"Authorization": f"Bearer {token}"},
        json={"selected_stl_file_ids": []},
    )
    assert r2.status_code == 202, r2.text
    body = r2.json()
    assert body["status"] == "queued"
    assert body["status_key"] == f"render:status:{model_id}"

    _patch_arq_pool.enqueue_job.assert_awaited_once()
    call = _patch_arq_pool.enqueue_job.await_args
    assert call.args[0] == "render_model"
    assert call.args[1] == str(model_id)
    assert call.kwargs["selected_stl_file_ids"] == []


def test_admin_trigger_render_validates_selected_stls(client, _patch_arq_pool):
    model_id, _ = _seed_model_with_stl("validate")
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    token = r.json()["access_token"]
    bogus_id = str(uuid.uuid4())
    r2 = client.post(
        f"/api/admin/models/{model_id}/render",
        headers={"Authorization": f"Bearer {token}"},
        json={"selected_stl_file_ids": [bogus_id]},
    )
    assert r2.status_code == 400


def test_admin_trigger_render_unknown_model_404(client, _patch_arq_pool):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@localhost.localdomain", "password": "test-admin-pw"},
    )
    token = r.json()["access_token"]
    r2 = client.post(
        f"/api/admin/models/{uuid.uuid4()}/render",
        headers={"Authorization": f"Bearer {token}"},
        json={"selected_stl_file_ids": []},
    )
    assert r2.status_code == 404
