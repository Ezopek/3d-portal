"""Tests for SoT admin Category write endpoints (Slice 2C.3).

Covers:
  POST   /api/admin/categories                    — create
  PATCH  /api/admin/categories/{category_id}      — update
  DELETE /api/admin/categories/{category_id}      — delete (RESTRICT)
"""

import uuid

from sqlmodel import Session, select

from app.core.auth.jwt import encode_token
from app.core.db.models import (
    AuditLog,
    Category,
    Model,
    User,
    UserRole,
)
from app.core.db.session import get_engine

JWT_SECRET = "test-secret-not-real"




def _admin_token(user_id: uuid.UUID) -> str:
    return encode_token(subject=str(user_id), role="admin", secret=JWT_SECRET, ttl_minutes=30)


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-cats-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_category(
    session: Session, *, parent_id: uuid.UUID | None = None, slug_suffix: str | None = None
) -> uuid.UUID:
    suffix = slug_suffix or uuid.uuid4().hex[:8]
    cat = Category(slug=f"cat-{suffix}", name_en=f"Category {suffix}", parent_id=parent_id)
    session.add(cat)
    session.flush()
    return cat.id


# ---------------------------------------------------------------------------
# POST /api/admin/categories
# ---------------------------------------------------------------------------


def test_create_category_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    slug = f"new-cat-{uuid.uuid4().hex[:8]}"
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/categories",
        json={"slug": slug, "name_en": "New Category", "name_pl": "Nowa Kategoria"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == slug
    assert body["name_en"] == "New Category"
    assert body["parent_id"] is None


def test_create_category_with_parent(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        parent_id = _seed_category(s)
        s.commit()

    slug = f"child-{uuid.uuid4().hex[:8]}"
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/categories",
        json={"slug": slug, "name_en": "Child", "parent_id": str(parent_id)},
    )
    assert r.status_code == 201, r.text
    assert r.json()["parent_id"] == str(parent_id)


def test_create_category_400_unknown_parent(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/categories",
        json={"slug": "child-x", "name_en": "Child", "parent_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400


def test_create_category_409_slug_conflict(client):
    """Same slug under same parent → 409."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        parent_id = _seed_category(s)
        # Create child with fixed slug
        child_slug = f"dup-slug-{uuid.uuid4().hex[:8]}"
        child = Category(slug=child_slug, name_en="Child", parent_id=parent_id)
        s.add(child)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/categories",
        json={"slug": child_slug, "name_en": "Dup", "parent_id": str(parent_id)},
    )
    assert r.status_code == 409


def test_create_category_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    slug = f"audit-cat-{uuid.uuid4().hex[:8]}"
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.post(
        "/api/admin/categories",
        json={"slug": slug, "name_en": "Audit Cat"},
    )
    assert r.status_code == 201
    cat_id = uuid.UUID(r.json()["id"])

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "category.create",
                AuditLog.entity_id == cat_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "category"


# ---------------------------------------------------------------------------
# PATCH /api/admin/categories/{category_id}
# ---------------------------------------------------------------------------


def test_patch_category_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/categories/{cat_id}",
        json={"name_en": "Updated Category"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name_en"] == "Updated Category"


def test_patch_category_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/categories/{uuid.uuid4()}",
        json={"name_en": "X"},
    )
    assert r.status_code == 404


def test_patch_category_cycle_self(client):
    """Setting parent_id = own id → 400."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/categories/{cat_id}",
        json={"parent_id": str(cat_id)},
    )
    assert r.status_code == 400


def test_patch_category_cycle_grandchild(client):
    """Setting parent_id to a descendant → 400."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        grandparent_id = _seed_category(s)
        parent_id = _seed_category(s, parent_id=grandparent_id)
        child_id = _seed_category(s, parent_id=parent_id)
        s.commit()

    # Try to set grandparent's parent to its grandchild
    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.patch(
        f"/api/admin/categories/{grandparent_id}",
        json={"parent_id": str(child_id)},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/admin/categories/{category_id}
# ---------------------------------------------------------------------------


def test_delete_category_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/categories/{cat_id}",
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        assert s.get(Category, cat_id) is None


def test_delete_category_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/categories/{uuid.uuid4()}",
    )
    assert r.status_code == 404


def test_delete_category_409_has_models(client):
    """409 when category has models (FK RESTRICT)."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        cat_id = _seed_category(s)
        m = Model(
            slug=f"m-cat-del-{uuid.uuid4().hex[:8]}",
            name_en="Test",
            category_id=cat_id,
        )
        s.add(m)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/categories/{cat_id}",
    )
    assert r.status_code == 409


def test_delete_category_409_has_children(client):
    """409 when category has children (FK RESTRICT)."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        parent_id = _seed_category(s)
        _seed_category(s, parent_id=parent_id)
        s.commit()

    client.cookies.set("portal_access", _admin_token(admin_id))
    r = client.delete(
        f"/api/admin/categories/{parent_id}",
    )
    assert r.status_code == 409
