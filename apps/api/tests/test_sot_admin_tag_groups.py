"""Story 42.4 — admin tag-group governance write endpoints.

Covers the new admin-only governance router:
  POST   /api/admin/tag-groups             — create (201 + TagGroupSummary)
  PATCH  /api/admin/tag-groups/{group_id}  — rename + reorder
  DELETE /api/admin/tag-groups/{group_id}  — delete (FK SET NULL, tags survive)

Plus the D-NULLSEM-1 null-semantics gate, the unconditional update audit (incl.
empty `{}` no-op body), the auth matrix (anonymous/member/agent → reject,
admin → 2xx), and read-after-write consistency against the 42.2
GET /api/tag-groups read endpoint.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests, so every seed uses unique slugs and every assertion is scoped to its
own seeded rows.
"""

import json
import uuid

from sqlmodel import Session, select

from app.core.auth.cookies import ACCESS_COOKIE
from app.core.db.models import AuditLog, Tag, TagGroup, User, UserRole
from app.core.db.session import get_engine
from tests._test_helpers import admin_token, agent_token, member_token

# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_admin(session: Session) -> uuid.UUID:
    """Seed a real admin User row.

    The `current_admin` dependency is JWT-only, but every governance write
    inserts an audit_log row whose `actor_user_id` FKs `user.id`
    (ondelete=SET NULL) — so the actor must exist or the INSERT fails under
    PRAGMA foreign_keys=ON.
    """
    u = User(
        email=f"admin-tg-{uuid.uuid4().hex[:6]}@test.local",
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


def _seed_group(session: Session, *, position: int = 0, name_pl: str | None = None) -> TagGroup:
    slug = f"grp-{uuid.uuid4().hex[:10]}"
    g = TagGroup(slug=slug, name_en=slug.upper(), name_pl=name_pl, position=position)
    session.add(g)
    session.commit()
    session.refresh(g)
    return g


def _seed_tag(
    session: Session, *, group_id: uuid.UUID | None = None, group_position: int = 0
) -> Tag:
    slug = f"tag-{uuid.uuid4().hex[:10]}"
    t = Tag(slug=slug, name_en=slug.upper(), group_id=group_id, group_position=group_position)
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


def _tag_group_audits(action: str, entity_id: uuid.UUID) -> list[AuditLog]:
    with Session(get_engine()) as s:
        return list(
            s.exec(
                select(AuditLog).where(
                    AuditLog.action == action,
                    AuditLog.entity_id == entity_id,
                )
            ).all()
        )


# ---------------------------------------------------------------------------
# POST /api/admin/tag-groups — create (AC #1, #9)
# ---------------------------------------------------------------------------


def test_create_tag_group_201_summary_shape(client):
    _admin_cookie(client)
    slug = f"grp-create-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/admin/tag-groups",
        json={"slug": slug, "name_en": "Materials", "name_pl": "Materiały", "position": 3},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body.keys()) == {"id", "slug", "name_en", "name_pl", "position"}
    assert body["slug"] == slug
    assert body["name_en"] == "Materials"
    assert body["name_pl"] == "Materiały"
    assert body["position"] == 3
    # Flat TagGroupSummary — NOT the read-side TagGroupRead (no embedded tags[]).
    assert "tags" not in body


def test_create_tag_group_defaults_position_zero_and_null_name_pl(client):
    _admin_cookie(client)
    slug = f"grp-defaults-{uuid.uuid4().hex[:8]}"
    r = client.post("/api/admin/tag-groups", json={"slug": slug, "name_en": "Scale"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["position"] == 0
    assert body["name_pl"] is None


def test_create_tag_group_409_slug_conflict(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        existing_slug = g.slug

    _admin_cookie(client)
    r = client.post("/api/admin/tag-groups", json={"slug": existing_slug, "name_en": "Dup"})
    assert r.status_code == 409, r.text


def test_create_tag_group_422_blank_slug(client):
    _admin_cookie(client)
    r = client.post("/api/admin/tag-groups", json={"slug": "", "name_en": "X"})
    assert r.status_code == 422, r.text


def test_create_tag_group_audit(client):
    _admin_cookie(client)
    slug = f"grp-audit-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/admin/tag-groups",
        json={"slug": slug, "name_en": "Audit Group", "name_pl": "PL", "position": 2},
    )
    assert r.status_code == 201
    gid = uuid.UUID(r.json()["id"])

    logs = _tag_group_audits("tag_group.create", gid)
    assert len(logs) == 1
    log = logs[0]
    assert log.entity_type == "tag_group"
    after = json.loads(log.after_json)
    assert set(after.keys()) == {"slug", "name_en", "name_pl", "position"}
    assert after == {"slug": slug, "name_en": "Audit Group", "name_pl": "PL", "position": 2}
    assert log.before_json is None


# ---------------------------------------------------------------------------
# PATCH /api/admin/tag-groups/{group_id} — rename + reorder (AC #2)
# ---------------------------------------------------------------------------


def test_patch_tag_group_rename_200(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"name_en": "Renamed", "name_pl": "Nowa"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name_en"] == "Renamed"
    assert body["name_pl"] == "Nowa"


def test_patch_tag_group_reorder_position(client):
    with Session(get_engine()) as s:
        g = _seed_group(s, position=0)
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"position": 7})
    assert r.status_code == 200, r.text
    assert r.json()["position"] == 7


def test_patch_tag_group_name_pl_clear(client):
    with Session(get_engine()) as s:
        g = _seed_group(s, name_pl="Do wyczyszczenia")
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"name_pl": None})
    assert r.status_code == 200, r.text
    assert r.json()["name_pl"] is None
    with Session(get_engine()) as s:
        assert s.get(TagGroup, gid).name_pl is None


def test_patch_tag_group_404(client):
    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{uuid.uuid4()}", json={"name_en": "X"})
    assert r.status_code == 404, r.text


def test_patch_tag_group_409_slug_conflict(client):
    with Session(get_engine()) as s:
        g1 = _seed_group(s)
        g2 = _seed_group(s)
        gid1 = g1.id
        slug2 = g2.slug

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid1}", json={"slug": slug2})
    assert r.status_code == 409, r.text


def test_patch_tag_group_unknown_key_422(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"bogus": "x"})
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# D-NULLSEM-1 — explicit null on NOT NULL fields → 422 (AC #2)
# ---------------------------------------------------------------------------


def test_patch_tag_group_explicit_null_slug_422(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id
        original_slug = g.slug

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"slug": None})
    assert r.status_code == 422, r.text
    # Row unchanged, no audit row written.
    with Session(get_engine()) as s:
        assert s.get(TagGroup, gid).slug == original_slug
    assert _tag_group_audits("tag_group.update", gid) == []


def test_patch_tag_group_explicit_null_name_en_422(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"name_en": None})
    assert r.status_code == 422, r.text
    assert _tag_group_audits("tag_group.update", gid) == []


def test_patch_tag_group_explicit_null_position_422(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"position": None})
    assert r.status_code == 422, r.text
    assert _tag_group_audits("tag_group.update", gid) == []


# ---------------------------------------------------------------------------
# Empty {} PATCH → 200 no-op + one full-snapshot before==after audit (AC #2, #6)
# ---------------------------------------------------------------------------


def test_patch_tag_group_empty_body_noop_200_and_audit(client):
    with Session(get_engine()) as s:
        g = _seed_group(s, position=4, name_pl="PL")
        gid = g.id
        snapshot = {
            "slug": g.slug,
            "name_en": g.name_en,
            "name_pl": g.name_pl,
            "position": g.position,
        }

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == snapshot["slug"]
    assert body["name_en"] == snapshot["name_en"]
    assert body["name_pl"] == snapshot["name_pl"]
    assert body["position"] == snapshot["position"]

    logs = _tag_group_audits("tag_group.update", gid)
    assert len(logs) == 1
    log = logs[0]
    before = json.loads(log.before_json)
    after = json.loads(log.after_json)
    assert before == after == snapshot
    assert set(after.keys()) == {"slug", "name_en", "name_pl", "position"}


def test_patch_tag_group_update_audit_full_snapshot(client):
    with Session(get_engine()) as s:
        g = _seed_group(s, position=1, name_pl="Stara")
        gid = g.id
        old_slug = g.slug
        old_name_en = g.name_en

    _admin_cookie(client)
    r = client.patch(f"/api/admin/tag-groups/{gid}", json={"name_en": "Nowa nazwa", "position": 9})
    assert r.status_code == 200, r.text

    logs = _tag_group_audits("tag_group.update", gid)
    assert len(logs) == 1
    before = json.loads(logs[0].before_json)
    after = json.loads(logs[0].after_json)
    assert before == {"slug": old_slug, "name_en": old_name_en, "name_pl": "Stara", "position": 1}
    assert after == {"slug": old_slug, "name_en": "Nowa nazwa", "name_pl": "Stara", "position": 9}


# ---------------------------------------------------------------------------
# DELETE /api/admin/tag-groups/{group_id} — SET NULL, tags survive (AC #3, #6)
# ---------------------------------------------------------------------------


def test_delete_tag_group_204(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id

    _admin_cookie(client)
    r = client.delete(f"/api/admin/tag-groups/{gid}")
    assert r.status_code == 204, r.text
    with Session(get_engine()) as s:
        assert s.get(TagGroup, gid) is None


def test_delete_tag_group_404(client):
    _admin_cookie(client)
    r = client.delete(f"/api/admin/tag-groups/{uuid.uuid4()}")
    assert r.status_code == 404, r.text


def test_delete_tag_group_set_null_tags_survive_groupless(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id
        t1 = _seed_tag(s, group_id=gid, group_position=0)
        t2 = _seed_tag(s, group_id=gid, group_position=1)
        t1_id, t2_id = t1.id, t2.id

    _admin_cookie(client)
    r = client.delete(f"/api/admin/tag-groups/{gid}")
    assert r.status_code == 204, r.text

    with Session(get_engine()) as s:
        surv1 = s.get(Tag, t1_id)
        surv2 = s.get(Tag, t2_id)
        assert surv1 is not None and surv1.group_id is None
        assert surv2 is not None and surv2.group_id is None


def test_delete_tag_group_audit_bounded_no_per_tag_rows(client):
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id
        slug, name_en = g.slug, g.name_en
        t1 = _seed_tag(s, group_id=gid)
        t2 = _seed_tag(s, group_id=gid)
        member_ids = {str(t1.id), str(t2.id)}

    _admin_cookie(client)
    r = client.delete(f"/api/admin/tag-groups/{gid}")
    assert r.status_code == 204

    logs = _tag_group_audits("tag_group.delete", gid)
    assert len(logs) == 1
    log = logs[0]
    assert log.entity_type == "tag_group"
    before = json.loads(log.before_json)
    assert set(before.keys()) == {"slug", "name_en", "detached_tag_ids", "detached_tag_count"}
    assert before["slug"] == slug
    assert before["name_en"] == name_en
    assert before["detached_tag_count"] == 2
    assert set(before["detached_tag_ids"]) == member_ids
    # No per-tag audit rows written for the detached tags.
    with Session(get_engine()) as s:
        tag_rows = s.exec(select(AuditLog).where(AuditLog.entity_id.in_([t1.id, t2.id]))).all()
    assert tag_rows == []


# ---------------------------------------------------------------------------
# Auth matrix — anonymous 401 / member 403 / agent 403 / admin 2xx (AC #7)
# ---------------------------------------------------------------------------


def _seed_group_id() -> uuid.UUID:
    with Session(get_engine()) as s:
        return _seed_group(s).id


def test_create_tag_group_auth_matrix(client):
    body = {"slug": f"grp-auth-{uuid.uuid4().hex[:8]}", "name_en": "Auth"}

    client.cookies.delete(ACCESS_COOKIE)
    assert client.post("/api/admin/tag-groups", json=body).status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.post("/api/admin/tag-groups", json=body).status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.post("/api/admin/tag-groups", json=body).status_code == 403

    _admin_cookie(client)
    assert client.post("/api/admin/tag-groups", json=body).status_code == 201


def test_patch_tag_group_auth_matrix(client):
    gid = _seed_group_id()
    body = {"name_en": "Moved"}

    client.cookies.delete(ACCESS_COOKIE)
    assert client.patch(f"/api/admin/tag-groups/{gid}", json=body).status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.patch(f"/api/admin/tag-groups/{gid}", json=body).status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.patch(f"/api/admin/tag-groups/{gid}", json=body).status_code == 403

    _admin_cookie(client)
    assert client.patch(f"/api/admin/tag-groups/{gid}", json=body).status_code == 200


def test_delete_tag_group_auth_matrix(client):
    client.cookies.delete(ACCESS_COOKIE)
    assert client.delete(f"/api/admin/tag-groups/{_seed_group_id()}").status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.delete(f"/api/admin/tag-groups/{_seed_group_id()}").status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.delete(f"/api/admin/tag-groups/{_seed_group_id()}").status_code == 403

    _admin_cookie(client)
    assert client.delete(f"/api/admin/tag-groups/{_seed_group_id()}").status_code == 204


# ---------------------------------------------------------------------------
# Read-after-write against GET /api/tag-groups (42.2 read API) — AC #8
# ---------------------------------------------------------------------------


def test_raw_create_group_appears_empty_at_sort_position(client):
    _admin_cookie(client)
    slug = f"grp-raw-create-{uuid.uuid4().hex[:8]}"
    r = client.post("/api/admin/tag-groups", json={"slug": slug, "name_en": "RAW", "position": 0})
    gid = r.json()["id"]

    body = client.get("/api/tag-groups").json()
    grp = next((g for g in body["groups"] if g["id"] == gid), None)
    assert grp is not None
    assert grp["tags"] == []


def test_raw_patch_position_resorts_groups(client):
    _admin_cookie(client)
    p = f"raw-sort-{uuid.uuid4().hex[:6]}"
    with Session(get_engine()) as s:
        a = TagGroup(slug=f"{p}-a", name_en="A", position=0)
        b = TagGroup(slug=f"{p}-b", name_en="B", position=1)
        s.add(a)
        s.add(b)
        s.commit()
        s.refresh(a)
        s.refresh(b)
        a_id, b_id = str(a.id), str(b.id)

    # Move A behind B.
    r = client.patch(f"/api/admin/tag-groups/{a_id}", json={"position": 5})
    assert r.status_code == 200

    body = client.get("/api/tag-groups").json()
    order = [g["id"] for g in body["groups"] if g["id"] in {a_id, b_id}]
    assert order == [b_id, a_id]


def test_raw_delete_group_members_return_to_groupless(client):
    _admin_cookie(client)
    with Session(get_engine()) as s:
        g = _seed_group(s)
        gid = g.id
        t = _seed_tag(s, group_id=gid)
        tid = str(t.id)

    r = client.delete(f"/api/admin/tag-groups/{gid}")
    assert r.status_code == 204

    body = client.get("/api/tag-groups").json()
    assert str(gid) not in {g["id"] for g in body["groups"]}
    assert tid in {t["id"] for t in body["groupless"]}
