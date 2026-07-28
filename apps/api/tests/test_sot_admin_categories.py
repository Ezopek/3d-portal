"""Story 49.5 — admin browse-category governance write endpoints.

Covers the new admin-only category governance router:
  POST   /api/admin/categories                  — create (201 + BrowseCategoryAdminRead)
  PATCH  /api/admin/categories/{category_id}    — rename / reorder / reparent
  DELETE /api/admin/categories/{category_id}    — delete (409 unless clean or detach=true)

Plus the D-NULLSEM-1 null-semantics gate, the unconditional update audit (incl.
the empty `{}` no-op body), the service-layer depth-2 ceiling and self-cycle
rejection (FR26-CAT-4 — deliberately NOT expressed in DDL), the two independent
409 conflict sources on delete (model assignments vs. child categories), the
auth matrix (anonymous/member/agent → reject, admin → 2xx), and the OpenAPI
honesty guards for the `sot-admin-governance` tag set.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests, so every seed uses unique slugs and every assertion is scoped to its
own seeded rows.
"""

import datetime
import json
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.db.models import (
    AuditLog,
    BrowseCategory,
    Model,
    ModelBrowseCategory,
    User,
    UserRole,
)
from app.core.db.session import get_engine
from app.modules.sot import admin_service
from app.modules.sot.service import _browse_category_model_counts
from tests._test_helpers import admin_token, agent_token, member_token

# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_admin(session: Session) -> uuid.UUID:
    """Seed a real admin User row.

    `current_admin` is JWT-only, but every governance write inserts an
    audit_log row whose `actor_user_id` FKs `user.id` (ondelete=SET NULL) — so
    the actor must exist or the INSERT fails under PRAGMA foreign_keys=ON.
    """
    u = User(
        email=f"admin-cat-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _admin_cookie(client) -> uuid.UUID:
    with Session(get_engine()) as s:
        admin_id = _seed_admin(s)
        s.commit()
    client.cookies.set(ACCESS_COOKIE, admin_token(admin_id))
    return admin_id


def _seed_category(
    session: Session,
    *,
    position: int = 0,
    parent_id: uuid.UUID | None = None,
    inclusion_criterion: str | None = None,
) -> BrowseCategory:
    slug = f"cat-{uuid.uuid4().hex[:10]}"
    c = BrowseCategory(
        slug=slug,
        name_en=slug.upper(),
        position=position,
        parent_id=parent_id,
        inclusion_criterion=inclusion_criterion,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _seed_category_id(**kwargs) -> uuid.UUID:
    with Session(get_engine()) as s:
        return _seed_category(s, **kwargs).id


def _seed_model(session: Session) -> uuid.UUID:
    m = Model(slug=f"m-cat-{uuid.uuid4().hex[:8]}", name_en="Test Model")
    session.add(m)
    session.flush()
    return m.id


def _category_audits(action: str, entity_id: uuid.UUID) -> list[AuditLog]:
    with Session(get_engine()) as s:
        return list(
            s.exec(
                select(AuditLog).where(
                    AuditLog.action == action,
                    AuditLog.entity_id == entity_id,
                )
            ).all()
        )


def _assignment_count(category_id: uuid.UUID) -> int:
    with Session(get_engine()) as s:
        return len(
            s.exec(
                select(ModelBrowseCategory).where(ModelBrowseCategory.category_id == category_id)
            ).all()
        )


def _category_exists(category_id: uuid.UUID) -> bool:
    with Session(get_engine()) as s:
        return s.get(BrowseCategory, category_id) is not None


# ---------------------------------------------------------------------------
# T1 — schema-layer contract (AC-2, AC-8, AC-9)
# ---------------------------------------------------------------------------


def test_browse_category_patch_forbids_unknown_keys():
    """AC-8: `BrowseCategoryPatch` is `extra='forbid'` — a caller typo is a 422
    at the schema layer, never a silently ignored field."""
    from app.modules.sot.admin_schemas import BrowseCategoryPatch

    with pytest.raises(ValidationError):
        BrowseCategoryPatch(nmae_en="typo")


@pytest.mark.parametrize("field", ["slug", "name_en", "position"])
def test_browse_category_patch_rejects_explicit_null_on_not_null_fields(field):
    """AC-9 / D-NULLSEM-1: `slug`/`name_en`/`position` are NOT NULL on the
    entity, so an EXPLICIT null is a 422 — while omitting them leaves the
    current value untouched (Pydantic v2 skips validators for unset fields)."""
    from app.modules.sot.admin_schemas import BrowseCategoryPatch

    with pytest.raises(ValidationError):
        BrowseCategoryPatch(**{field: None})


def test_browse_category_patch_allows_explicit_null_on_nullable_fields():
    """AC-9: an explicit null CLEARS the nullable label/prose fields."""
    from app.modules.sot.admin_schemas import BrowseCategoryPatch

    patch = BrowseCategoryPatch(
        name_pl=None, description_en=None, description_pl=None, inclusion_criterion=None
    )
    data = patch.model_dump(exclude_unset=True)
    assert data == {
        "name_pl": None,
        "description_en": None,
        "description_pl": None,
        "inclusion_criterion": None,
    }


def test_browse_category_patch_empty_body_dumps_empty():
    """AC-10: an empty `{}` patch carries no set fields at all — the no-op
    update path that must still audit is driven by this."""
    from app.modules.sot.admin_schemas import BrowseCategoryPatch

    assert BrowseCategoryPatch().model_dump(exclude_unset=True) == {}


def test_browse_category_create_defaults():
    """AC-2: everything except `slug`/`name_en` defaults — nullable fields to
    null, `position` to 0 (mirrors `TagGroupCreate.position: int = 0`)."""
    from app.modules.sot.admin_schemas import BrowseCategoryCreate

    payload = BrowseCategoryCreate(slug="s", name_en="S")
    assert payload.name_pl is None
    assert payload.description_en is None
    assert payload.description_pl is None
    assert payload.inclusion_criterion is None
    assert payload.parent_id is None
    assert payload.position == 0


def test_browse_category_admin_read_adds_inclusion_criterion():
    """AC-1 / §6 F-3: the admin write-response DTO is `BrowseCategoryRead`'s
    nine public-read keys PLUS `inclusion_criterion` — the one field the public
    read contract deliberately omits."""
    from app.modules.sot.schemas import BrowseCategoryAdminRead, BrowseCategoryRead

    assert issubclass(BrowseCategoryAdminRead, BrowseCategoryRead)
    assert set(BrowseCategoryAdminRead.model_fields) == set(BrowseCategoryRead.model_fields) | {
        "inclusion_criterion"
    }


def test_model_categories_replace_accepts_empty_list():
    """AC-27: the empty set is a valid payload — a model with zero categories
    stays fully valid and public (FR26-CAT-2)."""
    from app.modules.sot.admin_schemas import ModelCategoriesReplace

    assert ModelCategoriesReplace(category_ids=[]).category_ids == []


# ---------------------------------------------------------------------------
# POST /api/admin/categories — create (AC-1 … AC-7)
# ---------------------------------------------------------------------------

_ADMIN_READ_KEYS = {
    "id",
    "slug",
    "name_en",
    "name_pl",
    "description_en",
    "description_pl",
    "position",
    "parent_id",
    "model_count",
    "inclusion_criterion",
}


def test_create_category_201_admin_read_shape(client):
    """AC-1: 201 + the nine `BrowseCategoryRead` keys PLUS `inclusion_criterion`.
    `model_count` is always 0 — no assignment can exist for a brand-new id."""
    _admin_cookie(client)
    slug = f"cat-create-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/admin/categories",
        json={
            "slug": slug,
            "name_en": "Functional",
            "name_pl": "Funkcjonalne",
            "description_en": "Parts that do a job.",
            "description_pl": "Części, które coś robią.",
            "inclusion_criterion": "Has a mechanical function.",
            "position": 3,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == _ADMIN_READ_KEYS
    assert body["slug"] == slug
    assert body["name_en"] == "Functional"
    assert body["inclusion_criterion"] == "Has a mechanical function."
    assert body["position"] == 3
    assert body["parent_id"] is None
    assert body["model_count"] == 0

    audits = _category_audits("browse_category.create", uuid.UUID(body["id"]))
    assert len(audits) == 1
    after = json.loads(audits[0].after_json)
    assert after["slug"] == slug
    # AC-35: the bounded snapshot is EXACTLY eight scalar keys on the create
    # path too, not only on update/delete — a drift confined to
    # `browse_category.create` would otherwise go undetected (review #12).
    assert set(after.keys()) == {
        "slug",
        "name_en",
        "name_pl",
        "description_en",
        "description_pl",
        "inclusion_criterion",
        "position",
        "parent_id",
    }
    assert audits[0].entity_type == "browse_category"
    assert audits[0].before_json is None


def test_create_category_defaults(client):
    """AC-2: omitted optionals stay null; omitted `position` defaults to 0."""
    _admin_cookie(client)
    slug = f"cat-def-{uuid.uuid4().hex[:8]}"
    r = client.post("/api/admin/categories", json={"slug": slug, "name_en": "Bare"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name_pl"] is None
    assert body["description_en"] is None
    assert body["description_pl"] is None
    assert body["inclusion_criterion"] is None
    assert body["parent_id"] is None
    assert body["position"] == 0


def test_create_category_slug_conflict_409(client):
    """AC-3: a duplicate slug is a 409 — not 422, not a raw 500 IntegrityError."""
    _admin_cookie(client)
    slug = f"cat-dup-{uuid.uuid4().hex[:8]}"
    assert (
        client.post("/api/admin/categories", json={"slug": slug, "name_en": "A"}).status_code == 201
    )
    r = client.post("/api/admin/categories", json={"slug": slug, "name_en": "B"})
    assert r.status_code == 409, r.text


def test_create_category_unknown_parent_404(client):
    """AC-6: an unresolvable `parent_id` is a 404 (referenced-resource
    convention), not a 422 and not a raw IntegrityError."""
    _admin_cookie(client)
    r = client.post(
        "/api/admin/categories",
        json={
            "slug": f"cat-np-{uuid.uuid4().hex[:8]}",
            "name_en": "Orphan",
            "parent_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404, r.text


def test_create_category_non_root_parent_422(client):
    """AC-7: the depth-2 ceiling — a brand-new category may be a root or a
    direct child of a ROOT, never a grandchild."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        root = _seed_category(s)
        child = _seed_category(s, parent_id=root.id)
        child_id = child.id

    r = client.post(
        "/api/admin/categories",
        json={
            "slug": f"cat-gc-{uuid.uuid4().hex[:8]}",
            "name_en": "Grandchild",
            "parent_id": str(child_id),
        },
    )
    assert r.status_code == 422, r.text
    assert "parent_not_root" in r.text


def test_create_category_under_root_parent_201(client):
    """AC-7 positive half: a direct child of a ROOT is allowed."""
    _admin_cookie(client)
    root_id = _seed_category_id()
    r = client.post(
        "/api/admin/categories",
        json={
            "slug": f"cat-ch-{uuid.uuid4().hex[:8]}",
            "name_en": "Child",
            "parent_id": str(root_id),
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["parent_id"] == str(root_id)


def test_create_category_auth_matrix(client):
    """AC-4: anonymous 401, member 403, agent 403, admin 201. No route in this
    story ever accepts an `agent` principal."""
    body = {"slug": f"cat-auth-{uuid.uuid4().hex[:8]}", "name_en": "Auth"}

    client.cookies.delete(ACCESS_COOKIE)
    assert client.post("/api/admin/categories", json=body).status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.post("/api/admin/categories", json=body).status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.post("/api/admin/categories", json=body).status_code == 403

    _admin_cookie(client)
    assert client.post("/api/admin/categories", json=body).status_code == 201


# ---------------------------------------------------------------------------
# PATCH /api/admin/categories/{category_id} — rename / reorder / reparent
# (AC-8 … AC-16)
# ---------------------------------------------------------------------------


def test_patch_category_partial_update_200(client):
    """AC-8: only supplied fields change; 200 + `BrowseCategoryAdminRead`.

    Re-review finding N-3: the audit row's `after` snapshot is asserted here to
    reflect the POST-`setattr` state and to DIFFER from `before` on the changed
    field. Without this, the only test inspecting an update audit body was the
    empty-`{}` no-op — where `before == after` is the expected result — so a
    mutant capturing `after` before the `setattr` loop (making every update
    record "nothing changed") passed the whole suite."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s, position=1, inclusion_criterion="keep me")
        cid, original_slug, original_name = cat.id, cat.slug, cat.name_en

    r = client.patch(f"/api/admin/categories/{cid}", json={"name_en": "Renamed"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == _ADMIN_READ_KEYS
    assert body["name_en"] == "Renamed"
    assert body["slug"] == original_slug
    assert body["position"] == 1
    assert body["inclusion_criterion"] == "keep me"

    audits = _category_audits("browse_category.update", cid)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    after = json.loads(audits[0].after_json)
    assert before["name_en"] == original_name
    assert after["name_en"] == "Renamed"
    assert before != after
    # The untouched fields still round-trip truthfully on both sides.
    assert before["slug"] == after["slug"] == original_slug
    assert before["position"] == after["position"] == 1


def test_patch_category_unknown_key_422(client):
    """AC-8: `extra='forbid'` — an unknown key is a 422 over HTTP too."""
    _admin_cookie(client)
    cid = _seed_category_id()
    assert client.patch(f"/api/admin/categories/{cid}", json={"nmae_en": "x"}).status_code == 422


@pytest.mark.parametrize("field", ["slug", "name_en", "position"])
def test_patch_category_explicit_null_on_not_null_field_422(client, field):
    """AC-9: an explicit null on a NOT NULL field is a 422 — never a NOT NULL
    violation surfacing as the wrong 409/500."""
    _admin_cookie(client)
    cid = _seed_category_id()
    r = client.patch(f"/api/admin/categories/{cid}", json={field: None})
    assert r.status_code == 422, r.text


def test_patch_category_explicit_null_clears_nullable_fields(client):
    """AC-9: an explicit null CLEARS the nullable label/prose fields."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s, inclusion_criterion="to be cleared")
        cat.name_pl = "Nazwa"
        cat.description_en = "desc"
        s.add(cat)
        s.commit()
        cid = cat.id

    r = client.patch(
        f"/api/admin/categories/{cid}",
        json={"name_pl": None, "description_en": None, "inclusion_criterion": None},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name_pl"] is None
    assert body["description_en"] is None
    assert body["inclusion_criterion"] is None


def test_patch_category_empty_body_is_audited_noop(client):
    """AC-10: `PATCH {}` is a 200 no-op that STILL writes exactly one
    `browse_category.update` row with before == after. An admin action that
    changes nothing is still a recorded event."""
    _admin_cookie(client)
    cid = _seed_category_id()

    r = client.patch(f"/api/admin/categories/{cid}", json={})
    assert r.status_code == 200, r.text

    audits = _category_audits("browse_category.update", cid)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    after = json.loads(audits[0].after_json)
    assert before == after
    assert set(before.keys()) == {
        "slug",
        "name_en",
        "name_pl",
        "description_en",
        "description_pl",
        "inclusion_criterion",
        "position",
        "parent_id",
    }


def test_patch_category_slug_conflict_409(client):
    """AC-11: renaming onto ANOTHER category's slug is a 409."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        other = _seed_category(s)
        target = _seed_category(s)
        other_slug, cid = other.slug, target.id

    r = client.patch(f"/api/admin/categories/{cid}", json={"slug": other_slug})
    assert r.status_code == 409, r.text


def test_patch_category_self_rename_is_not_a_conflict(client):
    """AC-11: patching a slug to its OWN current value is a 200 no-op rename,
    not a false-positive 409 against itself."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        cid, own_slug = cat.id, cat.slug

    r = client.patch(f"/api/admin/categories/{cid}", json={"slug": own_slug})
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == own_slug


def test_patch_unknown_category_404(client):
    """AC-12: an unknown id is a 404, not a silent no-op and not a 422."""
    _admin_cookie(client)
    r = client.patch(f"/api/admin/categories/{uuid.uuid4()}", json={"name_en": "x"})
    assert r.status_code == 404, r.text


def test_patch_category_self_cycle_422(client):
    """AC-13: `parent_id == own id` is a 422 `self_cycle` and mutates nothing."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        cid, original_name = cat.id, cat.name_en

    r = client.patch(f"/api/admin/categories/{cid}", json={"parent_id": str(cid)})
    assert r.status_code == 422, r.text
    assert "self_cycle" in r.text

    with Session(get_engine()) as s:
        row = s.get(BrowseCategory, cid)
        assert row.parent_id is None
        assert row.name_en == original_name


def test_patch_category_unknown_parent_404(client):
    """Reparenting onto an unresolvable parent is a 404 (same
    referenced-resource convention as AC-6 on create)."""
    _admin_cookie(client)
    cid = _seed_category_id()
    r = client.patch(f"/api/admin/categories/{cid}", json={"parent_id": str(uuid.uuid4())})
    assert r.status_code == 404, r.text


def test_patch_category_parent_not_root_422(client):
    """AC-14: depth ceiling, TARGET side — reparenting onto a category that is
    itself already a child is a 422 `parent_not_root`."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        root = _seed_category(s)
        child = _seed_category(s, parent_id=root.id)
        mover = _seed_category(s)
        child_id, mover_id = child.id, mover.id

    r = client.patch(f"/api/admin/categories/{mover_id}", json={"parent_id": str(child_id)})
    assert r.status_code == 422, r.text
    assert "parent_not_root" in r.text


def test_patch_category_reparent_with_children_422(client):
    """AC-15: depth ceiling, SOURCE side — a category that currently HAS
    children can never be reparented onto anything, because that would push its
    children to depth 3. Distinct from AC-14: the target here is a valid root."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        parentful = _seed_category(s)
        _seed_category(s, parent_id=parentful.id)
        new_root = _seed_category(s)
        mover_id, new_root_id = parentful.id, new_root.id

    r = client.patch(f"/api/admin/categories/{mover_id}", json={"parent_id": str(new_root_id)})
    assert r.status_code == 422, r.text
    assert "reparent_exceeds_depth" in r.text

    with Session(get_engine()) as s:
        assert s.get(BrowseCategory, mover_id).parent_id is None


def test_patch_category_reparent_childless_onto_root_200(client):
    """AC-15 positive half: a category with ZERO children can always be
    reparented onto a valid root."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        new_root = _seed_category(s)
        mover = _seed_category(s)
        mover_id, new_root_id = mover.id, new_root.id

    r = client.patch(f"/api/admin/categories/{mover_id}", json={"parent_id": str(new_root_id)})
    assert r.status_code == 200, r.text
    assert r.json()["parent_id"] == str(new_root_id)


def test_patch_category_clear_parent_always_succeeds(client):
    """AC-16: `parent_id: null` makes a child a root again and always succeeds —
    setting a parent to null can never increase any depth."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        root = _seed_category(s)
        child = _seed_category(s, parent_id=root.id)
        child_id = child.id

    r = client.patch(f"/api/admin/categories/{child_id}", json={"parent_id": None})
    assert r.status_code == 200, r.text
    assert r.json()["parent_id"] is None


def test_patch_category_auth_matrix(client):
    """AC-4 posture applied to PATCH: anonymous 401, member 403, agent 403,
    admin 200."""
    cid = _seed_category_id()
    body = {"name_en": "Moved"}

    client.cookies.delete(ACCESS_COOKIE)
    assert client.patch(f"/api/admin/categories/{cid}", json=body).status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.patch(f"/api/admin/categories/{cid}", json=body).status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.patch(f"/api/admin/categories/{cid}", json=body).status_code == 403

    _admin_cookie(client)
    assert client.patch(f"/api/admin/categories/{cid}", json=body).status_code == 200


# ---------------------------------------------------------------------------
# DELETE /api/admin/categories/{category_id} — delete, with optional detach
# (AC-17 … AC-24)
# ---------------------------------------------------------------------------


def _seed_category_with_assignment() -> tuple[uuid.UUID, uuid.UUID]:
    """Seed a category with exactly one model assignment. Returns (cat, model)."""
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        model_id = _seed_model(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat.id))
        s.commit()
        return cat.id, model_id


def test_delete_clean_category_204(client):
    """AC-17: no assignments, no children → 204 + exactly one
    `browse_category.delete` audit row carrying `before` and no `after`."""
    _admin_cookie(client)
    cid = _seed_category_id()

    r = client.delete(f"/api/admin/categories/{cid}")
    assert r.status_code == 204, r.text
    assert not _category_exists(cid)

    audits = _category_audits("browse_category.delete", cid)
    assert len(audits) == 1
    assert audits[0].after_json is None
    before = json.loads(audits[0].before_json)
    assert set(before.keys()) == {
        "slug",
        "name_en",
        "name_pl",
        "description_en",
        "description_pl",
        "inclusion_criterion",
        "position",
        "parent_id",
    }


def test_delete_category_in_use_409_no_side_effect(client):
    """AC-18: assignments exist and `detach` is omitted → 409 `category_in_use`
    with NO side effect: the category survives, the assignment survives, and
    NOTHING is audited."""
    _admin_cookie(client)
    cid, _ = _seed_category_with_assignment()

    r = client.delete(f"/api/admin/categories/{cid}")
    assert r.status_code == 409, r.text
    assert "category_in_use" in r.text
    assert _category_exists(cid)
    assert _assignment_count(cid) == 1
    assert _category_audits("browse_category.delete", cid) == []


def test_delete_category_detach_false_is_409(client):
    """AC-18: an explicit `?detach=false` behaves exactly like omitting it."""
    _admin_cookie(client)
    cid, _ = _seed_category_with_assignment()

    r = client.delete(f"/api/admin/categories/{cid}?detach=false")
    assert r.status_code == 409, r.text
    assert _category_exists(cid)
    assert _assignment_count(cid) == 1


def test_delete_category_detach_true_204_atomic(client):
    """AC-19: `?detach=true` detaches every assignment AND deletes the category
    in one transaction, recording both `detached_model_ids` and
    `detached_model_count` on the single audit row."""
    _admin_cookie(client)
    cid, model_id = _seed_category_with_assignment()

    r = client.delete(f"/api/admin/categories/{cid}?detach=true")
    assert r.status_code == 204, r.text
    assert not _category_exists(cid)
    assert _assignment_count(cid) == 0

    audits = _category_audits("browse_category.delete", cid)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    assert before["detached_model_ids"] == [str(model_id)]
    assert before["detached_model_count"] == 1


def test_delete_clean_category_detach_true_records_no_detach_keys(client):
    """AC-20: `detach=true` on a category with NO assignments is a harmless
    no-op flag — 204, one audit row, and NO `detached_*` keys. The flag never
    fabricates a detach record."""
    _admin_cookie(client)
    cid = _seed_category_id()

    r = client.delete(f"/api/admin/categories/{cid}?detach=true")
    assert r.status_code == 204, r.text

    audits = _category_audits("browse_category.delete", cid)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    assert "detached_model_ids" not in before
    assert "detached_model_count" not in before


@pytest.mark.parametrize("query", ["", "?detach=true", "?detach=false"])
def test_delete_category_with_children_409(client, query):
    """AC-21: children are a SECOND, INDEPENDENT 409 source that `detach=true`
    does NOT resolve — `detach` is documented as model-assignment detach only,
    and this story ships no cascading child-delete or auto-reparent."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        parent = _seed_category(s)
        _seed_category(s, parent_id=parent.id)
        pid = parent.id

    r = client.delete(f"/api/admin/categories/{pid}{query}")
    assert r.status_code == 409, r.text
    assert "category_has_children" in r.text
    assert _category_exists(pid)
    assert _category_audits("browse_category.delete", pid) == []


def test_delete_category_children_win_over_assignments(client):
    """AC-22: both conflict sources present → children are checked FIRST and
    unconditionally, so `?detach=true` still 409s `category_has_children` and
    performs ZERO detach side effects."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        parent = _seed_category(s)
        _seed_category(s, parent_id=parent.id)
        model_id = _seed_model(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=parent.id))
        s.commit()
        pid = parent.id

    r = client.delete(f"/api/admin/categories/{pid}?detach=true")
    assert r.status_code == 409, r.text
    assert "category_has_children" in r.text
    assert _assignment_count(pid) == 1
    assert _category_exists(pid)


@pytest.mark.parametrize("query", ["", "?detach=true", "?detach=false"])
def test_delete_unknown_category_404(client, query):
    """AC-23: an unknown id is a 404 regardless of the `detach` query param.

    All THREE spellings are exercised — omitted, explicitly true, explicitly
    false — because AC-23 says "regardless of the `detach` query param" and the
    omitted/false pair take different code paths through FastAPI's bool
    coercion (default vs. parsed). Review finding #13."""
    _admin_cookie(client)
    r = client.delete(f"/api/admin/categories/{uuid.uuid4()}{query}")
    assert r.status_code == 404, r.text


def test_delete_category_auth_matrix(client):
    """AC-24: anonymous 401, member 403, agent 403, admin 204."""
    client.cookies.delete(ACCESS_COOKIE)
    assert client.delete(f"/api/admin/categories/{_seed_category_id()}").status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.delete(f"/api/admin/categories/{_seed_category_id()}").status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.delete(f"/api/admin/categories/{_seed_category_id()}").status_code == 403

    _admin_cookie(client)
    assert client.delete(f"/api/admin/categories/{_seed_category_id()}").status_code == 204


# ---------------------------------------------------------------------------
# Post-review repair pass (native bmad-code-review REQUEST_CHANGES, 2026-07-28)
# ---------------------------------------------------------------------------


def _blind_first_call(real):
    """Return a wrapper that reports "nothing found" on its FIRST call only and
    delegates to `real` afterwards.

    This is how the prequery→commit TOCTOU window is reproduced deterministically
    in-process: the proactive pre-query sees a clean category, the racing row is
    still really there, and the RESTRICT FK fires at COMMIT. Without a wrapper
    the window is unobservable from a single-threaded test — SQLite is a single
    writer and the two statements are microseconds apart.
    """
    calls = {"n": 0}

    def wrapper(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return []
        return real(*args, **kwargs)

    return wrapper


def test_delete_category_child_race_is_409_not_an_unhandled_500(client, monkeypatch):
    """Review finding #3: a child created between the proactive pre-query and
    the COMMIT must still surface as the documented 409, never as an unhandled
    IntegrityError escaping the router as a 500.

    Children-first precedence is preserved: the safety net re-derives the cause
    AFTER the rollback, so this maps to `category_has_children`, not to the
    generic `category_in_use`."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        parent = _seed_category(s)
        _seed_category(s, parent_id=parent.id)
        pid = parent.id

    monkeypatch.setattr(
        admin_service,
        "_browse_category_children",
        _blind_first_call(admin_service._browse_category_children),
    )

    r = client.delete(f"/api/admin/categories/{pid}")
    assert r.status_code == 409, r.text
    assert "category_has_children" in r.text
    assert _category_exists(pid)
    # The rolled-back transaction leaves no audit residue.
    assert _category_audits("browse_category.delete", pid) == []


def test_delete_category_assignment_race_is_409_not_an_unhandled_500(client, monkeypatch):
    """Review finding #3, assignment half: a `model_browse_category` row created
    between the pre-query and the COMMIT maps to 409 `category_in_use` (the
    documented status for that conflict source), not to a 500.

    Mirrors the ratified `delete_tag` rollback/error mapping
    (`admin_service.py`, `ValueError("tag_in_use")`)."""
    _admin_cookie(client)
    cid, _ = _seed_category_with_assignment()

    monkeypatch.setattr(
        admin_service,
        "_browse_category_assignments",
        _blind_first_call(admin_service._browse_category_assignments),
    )

    r = client.delete(f"/api/admin/categories/{cid}")
    assert r.status_code == 409, r.text
    assert "category_in_use" in r.text
    assert _category_exists(cid)
    assert _assignment_count(cid) == 1
    assert _category_audits("browse_category.delete", cid) == []


def test_create_category_vanished_parent_is_404_not_a_slug_conflict_409(client, monkeypatch):
    """Review finding #4: `BrowseCategory` has TWO constraints that can raise
    IntegrityError at flush — `uq_browse_category_slug` and the `parent_id`
    self-FK. A blanket `IntegrityError → slug_conflict` blames a provably-unique
    slug for a parent problem, and retrying with a new slug never helps.

    The parent is made to "vanish" between validation and flush by neutralising
    `_validate_parent_is_root`, which is exactly the race the blanket mapping
    could not distinguish."""
    _admin_cookie(client)
    monkeypatch.setattr(admin_service, "_validate_parent_is_root", lambda *a, **k: None)

    slug = f"cat-orphan-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/admin/categories",
        json={"slug": slug, "name_en": "Orphan", "parent_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404, r.text
    assert "parent" in r.text


def test_patch_category_vanished_parent_is_404_not_a_slug_conflict_409(client, monkeypatch):
    """Review finding #4, update half — same re-derivation on the reparent path."""
    _admin_cookie(client)
    cid = _seed_category_id()
    monkeypatch.setattr(admin_service, "_validate_parent_is_root", lambda *a, **k: None)

    r = client.patch(
        f"/api/admin/categories/{cid}",
        json={"parent_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404, r.text
    assert "parent" in r.text


def test_create_category_duplicate_slug_still_409_after_parent_re_derivation(client):
    """Review finding #4 non-regression: re-deriving the IntegrityError cause
    must NOT change the shipped duplicate-slug behaviour, including when a
    perfectly valid `parent_id` is present on the conflicting payload."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        root = _seed_category(s)
        existing = _seed_category(s)
        root_id, taken_slug = root.id, existing.slug

    r = client.post(
        "/api/admin/categories",
        json={"slug": taken_slug, "name_en": "Dup", "parent_id": str(root_id)},
    )
    assert r.status_code == 409, r.text
    assert "slug" in r.text


# --- Review finding #1 — controller-arbitrated preservation-first lifecycle ---


def test_soft_deleted_model_assignment_is_preserved_until_explicit_detach(client):
    """Review finding #1, arbitrated by Laura/controller as PRESERVATION-FIRST.

    ALL `model_browse_category` rows — including rows whose model is
    soft-deleted — keep making an ordinary DELETE return 409 `category_in_use`.
    The alternative (filtering the delete gate to live models) would silently
    destroy the category relationships `restore_model` needs, and would run
    `session.delete(cat)` straight into the RESTRICT FK.

    `model_count` stays the Decision-AY count of distinct NON-DELETED models, so
    it may truthfully read 0 while a protected assignment still exists. That is
    the accepted, documented consequence, not a defect. `?detach=true` is the
    explicit destructive opt-in that removes those rows.

    This test pins the exact lifecycle end to end."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        model_id = _seed_model(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat.id))
        s.commit()
        cid = cat.id

    # 1. Active assignment — model_count is 1 on the admin write response.
    r = client.patch(f"/api/admin/categories/{cid}", json={})
    assert r.status_code == 200, r.text
    assert r.json()["model_count"] == 1

    # 2. Soft-delete the model (no hard delete, join row untouched).
    with Session(get_engine()) as s:
        m = s.get(Model, model_id)
        m.deleted_at = datetime.datetime.now(datetime.UTC)
        s.add(m)
        s.commit()

    # 3. model_count truthfully drops to 0 — Decision AY counts live models only.
    r = client.patch(f"/api/admin/categories/{cid}", json={})
    assert r.status_code == 200, r.text
    assert r.json()["model_count"] == 0
    assert _assignment_count(cid) == 1  # ...while the row itself is still there

    # 4. Ordinary DELETE still refuses, and preserves the relationship.
    r = client.delete(f"/api/admin/categories/{cid}")
    assert r.status_code == 409, r.text
    assert "category_in_use" in r.text
    assert _assignment_count(cid) == 1
    assert _category_exists(cid)

    # 5. detach=true is the explicit, audited destructive opt-in.
    r = client.delete(f"/api/admin/categories/{cid}?detach=true")
    assert r.status_code == 204, r.text
    assert _assignment_count(cid) == 0
    assert not _category_exists(cid)

    audits = _category_audits("browse_category.delete", cid)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    assert before["detached_model_ids"] == [str(model_id)]
    assert before["detached_model_count"] == 1


# --- Review finding #2 — non-zero-path + read-side parity for model_count ---


def test_browse_category_model_count_non_zero_excludes_soft_deleted_models(client):
    """Review finding #2: every shipped `model_count` assertion observed 0, so
    the join, the `Model.deleted_at IS NULL` filter and the agreement with the
    public read side were all unproven.

    Asserts the non-zero path on THREE surfaces at once — the service helper,
    the admin write response, and the public `GET /api/categories` read — over a
    category carrying two live assignments and one soft-deleted one."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        live_a, live_b = _seed_model(s), _seed_model(s)
        dead = _seed_model(s)
        s.get(Model, dead).deleted_at = datetime.datetime.now(datetime.UTC)
        for mid in (live_a, live_b, dead):
            s.add(ModelBrowseCategory(model_id=mid, category_id=cat.id))
        s.commit()
        cid, slug = cat.id, cat.slug

    with Session(get_engine()) as s:
        assert admin_service.browse_category_model_count(s, cid) == 2

    r = client.patch(f"/api/admin/categories/{cid}", json={})
    assert r.status_code == 200, r.text
    assert r.json()["model_count"] == 2

    r = client.get("/api/categories")
    assert r.status_code == 200, r.text
    public = next(i for i in r.json() if i["slug"] == slug)
    assert public["model_count"] == 2


def test_browse_category_model_count_agrees_with_read_side_for_every_category(client):
    """Review finding #2, anti-drift guard. Decision AY requires the admin and
    public `model_count` to be unable to disagree. The implementation keeps two
    separate queries (a scoped single-category count vs. a whole-table GROUP BY)
    rather than one shared helper, so the no-disagreement property is pinned
    here directly instead: every category in the database is compared across
    BOTH definitions, over a fixture that deliberately mixes non-zero counts,
    a zero count and a soft-deleted assignment.

    Either implementation drifting from the other fails this test."""
    with Session(get_engine()) as s:
        many = _seed_category(s)
        one = _seed_category(s)
        none = _seed_category(s)
        dead_only = _seed_category(s)
        a, b, c = _seed_model(s), _seed_model(s), _seed_model(s)
        dead = _seed_model(s)
        s.flush()
        s.get(Model, dead).deleted_at = datetime.datetime.now(datetime.UTC)
        for mid in (a, b, c):
            s.add(ModelBrowseCategory(model_id=mid, category_id=many.id))
        s.add(ModelBrowseCategory(model_id=a, category_id=one.id))
        s.add(ModelBrowseCategory(model_id=dead, category_id=dead_only.id))
        s.commit()
        expected = {many.id: 3, one.id: 1, none.id: 0, dead_only.id: 0}

    with Session(get_engine()) as s:
        read_side = _browse_category_model_counts(s)
        for cat_id in s.exec(select(BrowseCategory.id)).all():
            assert admin_service.browse_category_model_count(s, cat_id) == read_side.get(cat_id, 0)
        for cat_id, want in expected.items():
            assert admin_service.browse_category_model_count(s, cat_id) == want


# ---------------------------------------------------------------------------
# Post-RE-REVIEW repair pass (native bmad-code-review REQUEST_CHANGES, 2026-07-28)
# ---------------------------------------------------------------------------


def _ghost_actor_outcome(call) -> str:
    """Classify what a governance write does when the acting admin's `user` row
    does not exist.

    `current_admin` is pure JWT with no DB user-existence check, but every write
    flushes an `audit_log` row whose `actor_user_id` FKs `user.id`. The three
    routes that do not wrap their commit therefore fail server-side; this helper
    normalises "raised" vs. "returned a 5xx" so the delete route can be compared
    against its own siblings instead of against a hard-coded status.
    """
    try:
        r = call()
    except IntegrityError:
        return "integrity-error"
    return f"http-{r.status_code}"


def test_delete_category_unrelated_integrity_failure_is_not_a_false_409(client):
    """Re-review finding N-1: the delete safety net's `except IntegrityError`
    must not map an integrity failure that is NOT one of the two RESTRICT FKs
    onto `409 category_in_use`.

    The category here provably has zero children and zero assignments, so a 409
    asserts a conflict that does not exist and that the client cannot falsify
    (`model_count` reads 0, there is nothing to detach, and `?detach=true` would
    fail identically). The honest outcome is whatever the sibling create route
    already does for the very same cause — which is what is asserted, so this
    test pins "no false 409 + same answer as its siblings" without freezing an
    unhandled-exception representation the app is free to change."""
    ghost_admin = uuid.uuid4()
    cid = _seed_category_id()
    client.cookies.set(ACCESS_COOKIE, admin_token(ghost_admin))

    sibling = _ghost_actor_outcome(
        lambda: client.post(
            "/api/admin/categories",
            json={"slug": f"cat-ghost-{uuid.uuid4().hex[:8]}", "name_en": "Ghost"},
        )
    )
    outcome = _ghost_actor_outcome(lambda: client.delete(f"/api/admin/categories/{cid}"))

    assert outcome != "http-409", "unrelated integrity failure reported as category_in_use"
    assert outcome == sibling, "delete answers differently from its siblings on one shared cause"
    assert _category_exists(cid)
    assert _assignment_count(cid) == 0
    assert _category_audits("browse_category.delete", cid) == []

    # `?detach=true` must not paper over it either.
    detach_outcome = _ghost_actor_outcome(
        lambda: client.delete(f"/api/admin/categories/{cid}?detach=true")
    )
    assert detach_outcome != "http-409"

    # Control: the same delete with a REAL admin row is an ordinary 204.
    _admin_cookie(client)
    assert client.delete(f"/api/admin/categories/{cid}").status_code == 204


def test_delete_category_detach_with_assignments_unrelated_integrity_failure_is_not_a_false_409(
    client,
):
    """Final-review finding F-1: the N-1 safety net closed only the
    zero-assignment branch.

    With `detach=true` on a category that HAS assignments, the rollback RESTORES
    the very rows the request had just deleted, so re-deriving the cause from
    the post-rollback state saw assignments present and answered
    `409 category_in_use` — a conflict the caller's own `detach=true` was
    documented to resolve, that retrying with `detach=true` cannot clear, and
    that the client therefore cannot falsify. Only an assignment the request had
    NOT already accounted for is the racing insert the 409 is about; here there
    is none, so the honest outcome is the sibling routes' own answer to the same
    cause."""
    ghost_admin = uuid.uuid4()
    cid, model_id = _seed_category_with_assignment()
    client.cookies.set(ACCESS_COOKIE, admin_token(ghost_admin))

    sibling = _ghost_actor_outcome(
        lambda: client.post(
            "/api/admin/categories",
            json={"slug": f"cat-ghost-{uuid.uuid4().hex[:8]}", "name_en": "Ghost"},
        )
    )
    outcome = _ghost_actor_outcome(
        lambda: client.delete(f"/api/admin/categories/{cid}?detach=true")
    )

    assert outcome != "http-409", "restored-by-rollback assignments reported as category_in_use"
    assert outcome == sibling, "delete answers differently from its siblings on one shared cause"
    # The rollback is total: category, assignment and audit trail all untouched.
    assert _category_exists(cid)
    assert _assignment_count(cid) == 1
    assert _category_audits("browse_category.delete", cid) == []

    # `detach=false` on the same category still reports the real conflict.
    assert client.delete(f"/api/admin/categories/{cid}").status_code == 409

    # Control: the same detach with a REAL admin row is an ordinary 204.
    _admin_cookie(client)
    r = client.delete(f"/api/admin/categories/{cid}?detach=true")
    assert r.status_code == 204, r.text
    assert not _category_exists(cid)
    assert _assignment_count(cid) == 0
    audits = _category_audits("browse_category.delete", cid)
    assert len(audits) == 1
    assert json.loads(audits[0].before_json)["detached_model_ids"] == [str(model_id)]


def test_delete_category_children_checked_before_assignments_are_queried(client, monkeypatch):
    """Re-review finding N-4(a): AC-21/AC-22 state children-first precedence as a
    proven property, but every shipped assertion pinned it by OUTCOME only —
    deleting the proactive children pre-query left them all green, because the
    finding-#3 safety net re-derives children-first after rollback and produces
    an identical observable 409.

    This pins the ORDER instead: with both conflict sources present and the
    destructive `?detach=true` flag set, the assignment query must never run at
    all. Removing the pre-query makes the request fall through to the detach
    branch (which queries, deletes and only then hits the child FK at COMMIT),
    so the sentinel fires and this test fails — intentionally, not incidentally."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        parent = _seed_category(s)
        _seed_category(s, parent_id=parent.id)
        model_id = _seed_model(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=parent.id))
        s.commit()
        pid = parent.id

    queried: list[uuid.UUID] = []
    real = admin_service._browse_category_assignments

    def recording(session, category_id):
        queried.append(category_id)
        return real(session, category_id)

    monkeypatch.setattr(admin_service, "_browse_category_assignments", recording)

    r = client.delete(f"/api/admin/categories/{pid}?detach=true")
    assert r.status_code == 409, r.text
    assert "category_has_children" in r.text
    assert queried == [], "assignments were queried even though children already conflict"
    assert _assignment_count(pid) == 1
    assert _category_exists(pid)
