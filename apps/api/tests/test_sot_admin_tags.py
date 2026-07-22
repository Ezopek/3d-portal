"""Tests for SoT admin Tag endpoints (Slice 2C.3).

Covers:
  PUT    /api/admin/models/{model_id}/tags        — replace tag set
  POST   /api/admin/models/{model_id}/tags        — add one tag (idempotent)
  DELETE /api/admin/models/{model_id}/tags/{id}   — remove one tag (idempotent)
  POST   /api/admin/tags                          — create global tag
  PATCH  /api/admin/tags/{tag_id}                 — update global tag
  DELETE /api/admin/tags/{tag_id}                 — delete (RESTRICT)
  POST   /api/admin/tags/merge                    — merge from→to
"""

import json
import uuid

from sqlmodel import Session, select

from app.core.db.models import (
    AuditLog,
    Model,
    ModelTag,
    Tag,
    TagGroup,
    User,
    UserRole,
)
from app.core.db.session import get_engine
from tests._test_helpers import admin_token, agent_token


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-tags-{uuid.uuid4().hex[:6]}@test.local",
        display_name="Admin",
        role=UserRole.admin,
        password_hash="x",
    )
    session.add(u)
    session.flush()
    return u.id


def _seed_model(session: Session) -> uuid.UUID:
    m = Model(
        slug=f"m-tags-{uuid.uuid4().hex[:8]}",
        name_en="Test Model",
    )
    session.add(m)
    session.flush()
    return m.id


def _seed_tag(session: Session, slug_suffix: str | None = None) -> uuid.UUID:
    suffix = slug_suffix or uuid.uuid4().hex[:8]
    tag = Tag(slug=f"tag-{suffix}", name_en=f"Tag {suffix}")
    session.add(tag)
    session.flush()
    return tag.id


# ---------------------------------------------------------------------------
# PUT /api/admin/models/{model_id}/tags — replace tag set
# ---------------------------------------------------------------------------


def test_replace_tags_empty_to_set(client):
    """Replace empty tag set with two tags → 200 with both tags."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag1_id = _seed_tag(s)
        tag2_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.put(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_ids": [str(tag1_id), str(tag2_id)]},
    )
    assert r.status_code == 200, r.text
    result_ids = {item["id"] for item in r.json()}
    assert str(tag1_id) in result_ids
    assert str(tag2_id) in result_ids


def test_replace_tags_clears_existing(client):
    """Replace existing tag with a different one — old tag removed."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        old_tag = _seed_tag(s)
        new_tag = _seed_tag(s)
        # Pre-attach old tag
        s.add(ModelTag(model_id=model_id, tag_id=old_tag))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.put(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_ids": [str(new_tag)]},
    )
    assert r.status_code == 200
    result_ids = {item["id"] for item in r.json()}
    assert str(old_tag) not in result_ids
    assert str(new_tag) in result_ids


def test_replace_tags_empty_set(client):
    """Replace with empty list removes all tags."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.add(ModelTag(model_id=model_id, tag_id=tag_id))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.put(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_ids": []},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_replace_tags_404_model_not_found(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.put(
        f"/api/admin/models/{uuid.uuid4()}/tags",
        json={"tag_ids": []},
    )
    assert r.status_code == 404


def test_replace_tags_400_invalid_tag(client):
    """400 when a supplied tag_id doesn't exist."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.put(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_ids": [str(uuid.uuid4())]},
    )
    assert r.status_code == 400


def test_replace_tags_writes_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    client.put(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_ids": [str(tag_id)]},
    )
    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "model.update",
                AuditLog.entity_id == model_id,
            )
        ).all()
    # Should have an audit row with tag_ids in after
    assert any("tag_ids" in (log.after_json or "") for log in logs)


# ---------------------------------------------------------------------------
# POST /api/admin/models/{model_id}/tags — add one tag
# ---------------------------------------------------------------------------


def test_add_tag_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_id": str(tag_id)},
    )
    assert r.status_code == 200, r.text
    result_ids = {item["id"] for item in r.json()}
    assert str(tag_id) in result_ids


def test_add_tag_idempotent(client):
    """Adding the same tag twice returns 200 both times without error."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.commit()

    url = f"/api/admin/models/{model_id}/tags"
    body = {"tag_id": str(tag_id)}
    client.cookies.set("portal_access", admin_token(admin_id))
    r1 = client.post(url, json=body)
    r2 = client.post(url, json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Should have exactly one ModelTag row
    with Session(get_engine()) as s:
        rows = s.exec(
            select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == tag_id)
        ).all()
    assert len(rows) == 1


def test_add_tag_404_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{uuid.uuid4()}/tags",
        json={"tag_id": str(tag_id)},
    )
    assert r.status_code == 404


def test_add_tag_404_tag(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        f"/api/admin/models/{model_id}/tags",
        json={"tag_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/admin/models/{model_id}/tags/{tag_id}
# ---------------------------------------------------------------------------


def test_remove_tag_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.add(ModelTag(model_id=model_id, tag_id=tag_id))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{model_id}/tags/{tag_id}",
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        row = s.exec(
            select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == tag_id)
        ).first()
    assert row is None


def test_remove_tag_idempotent(client):
    """Removing a tag not attached returns 204 (no error)."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{model_id}/tags/{tag_id}",
    )
    assert r.status_code == 204


def test_remove_tag_404_model(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/models/{uuid.uuid4()}/tags/{tag_id}",
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/admin/tags — create global tag
# ---------------------------------------------------------------------------


def test_create_tag_201(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    slug = f"newtag-{uuid.uuid4().hex[:8]}"
    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags",
        json={"slug": slug, "name_en": "New Tag", "name_pl": "Nowy Tag"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["slug"] == slug
    assert body["name_en"] == "New Tag"
    assert body["name_pl"] == "Nowy Tag"
    assert "id" in body


def test_create_tag_409_slug_conflict(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s, "conflict-slug")
        s.commit()

    with Session(get_engine()) as s:
        tag = s.get(Tag, tag_id)
        slug = tag.slug

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags",
        json={"slug": slug, "name_en": "Another"},
    )
    assert r.status_code == 409


def test_create_tag_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    slug = f"audit-tag-{uuid.uuid4().hex[:8]}"
    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags",
        json={"slug": slug, "name_en": "Audit Tag"},
    )
    assert r.status_code == 201
    tag_id = uuid.UUID(r.json()["id"])

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "tag.create",
                AuditLog.entity_id == tag_id,
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "tag"


# ---------------------------------------------------------------------------
# PATCH /api/admin/tags/{tag_id}
# ---------------------------------------------------------------------------


def test_patch_tag_200(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(
        f"/api/admin/tags/{tag_id}",
        json={"name_en": "Updated Name"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name_en"] == "Updated Name"


def test_patch_tag_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(
        f"/api/admin/tags/{uuid.uuid4()}",
        json={"name_en": "X"},
    )
    assert r.status_code == 404


def test_patch_tag_409_slug_collision(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag1_id = _seed_tag(s, "patch-slug-a")
        tag2_id = _seed_tag(s, "patch-slug-b")
        s.commit()

    with Session(get_engine()) as s:
        tag2 = s.get(Tag, tag2_id)
        tag2_slug = tag2.slug

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(
        f"/api/admin/tags/{tag1_id}",
        json={"slug": tag2_slug},
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /api/admin/tags/{tag_id}
# ---------------------------------------------------------------------------


def test_delete_tag_204(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/tags/{tag_id}",
    )
    assert r.status_code == 204

    with Session(get_engine()) as s:
        assert s.get(Tag, tag_id) is None


def test_delete_tag_404(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/tags/{uuid.uuid4()}",
    )
    assert r.status_code == 404


def test_delete_tag_409_in_use(client):
    """409 when tag is attached to a model (FK RESTRICT)."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        tag_id = _seed_tag(s)
        s.add(ModelTag(model_id=model_id, tag_id=tag_id))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.delete(
        f"/api/admin/tags/{tag_id}",
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/admin/tags/merge
# ---------------------------------------------------------------------------


def test_merge_tags_rewires_m2m(client):
    """Merge from→to rewires all ModelTag rows to to_id."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        from_id = _seed_tag(s)
        to_id = _seed_tag(s)
        s.add(ModelTag(model_id=model_id, tag_id=from_id))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags/merge",
        json={"from_id": str(from_id), "to_id": str(to_id)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == str(to_id)

    with Session(get_engine()) as s:
        # from-tag deleted
        assert s.get(Tag, from_id) is None
        # model now has to-tag
        mt = s.exec(
            select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == to_id)
        ).first()
        assert mt is not None


def test_merge_tags_handles_duplicate(client):
    """If model already has both from and to tags, merge doesn't create duplicate."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        model_id = _seed_model(s)
        from_id = _seed_tag(s)
        to_id = _seed_tag(s)
        # Attach both tags to the same model
        s.add(ModelTag(model_id=model_id, tag_id=from_id))
        s.add(ModelTag(model_id=model_id, tag_id=to_id))
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags/merge",
        json={"from_id": str(from_id), "to_id": str(to_id)},
    )
    assert r.status_code == 200

    with Session(get_engine()) as s:
        # Exactly one ModelTag for to_id on this model
        rows = s.exec(
            select(ModelTag).where(ModelTag.model_id == model_id, ModelTag.tag_id == to_id)
        ).all()
        assert len(rows) == 1
        # from-tag gone
        assert s.get(Tag, from_id) is None


def test_merge_tags_404_from_not_found(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        to_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags/merge",
        json={"from_id": str(uuid.uuid4()), "to_id": str(to_id)},
    )
    assert r.status_code == 404


def test_merge_tags_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        from_id = _seed_tag(s)
        to_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.post(
        "/api/admin/tags/merge",
        json={"from_id": str(from_id), "to_id": str(to_id)},
    )
    assert r.status_code == 200

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "tag.merge",
                AuditLog.entity_id == to_id,
            )
        ).all()
    assert len(logs) == 1
    assert str(from_id) in (logs[0].after_json or "")


# ---------------------------------------------------------------------------
# Story 42.4 — tag-create tightened to admin-only (D-ADMINONLY-1 / FR25-TAX-2)
# ---------------------------------------------------------------------------


def test_create_tag_agent_403(client):
    """The agent service role can no longer mint tags (curated vocabulary)."""
    client.cookies.set("portal_access", agent_token(uuid.uuid4()))
    r = client.post(
        "/api/admin/tags",
        json={"slug": f"agent-blocked-{uuid.uuid4().hex[:8]}", "name_en": "Nope"},
    )
    assert r.status_code == 403, r.text


def test_create_tag_anonymous_401(client):
    client.cookies.delete("portal_access")
    r = client.post(
        "/api/admin/tags",
        json={"slug": f"anon-{uuid.uuid4().hex[:8]}", "name_en": "Nope"},
    )
    assert r.status_code == 401, r.text


def test_create_tag_member_403(client):
    from tests._test_helpers import member_token

    client.cookies.set("portal_access", member_token(uuid.uuid4()))
    r = client.post(
        "/api/admin/tags",
        json={"slug": f"member-{uuid.uuid4().hex[:8]}", "name_en": "Nope"},
    )
    assert r.status_code == 403, r.text


def test_patch_tag_agent_still_allowed(client):
    """Retained tag PATCH stays admin-or-agent (agent-write) — only create tightened."""
    engine = get_engine()
    with Session(engine) as s:
        # A real agent user — the tag.update audit row FKs user.id.
        agent = User(
            email=f"agent-tags-{uuid.uuid4().hex[:6]}@test.local",
            display_name="Agent",
            role=UserRole.agent,
            password_hash="x",
        )
        s.add(agent)
        s.flush()
        agent_id = agent.id
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", agent_token(agent_id))
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"name_en": "Agent Renamed"})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Story 42.4 — move a tag into / out of a group via PATCH (AC #4, D-MOVE-1)
# ---------------------------------------------------------------------------


def _seed_tag_group(session: Session) -> uuid.UUID:
    g = TagGroup(slug=f"grp-move-{uuid.uuid4().hex[:8]}", name_en="Move Grp")
    session.add(g)
    session.flush()
    return g.id


def test_patch_tag_move_into_group(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        group_id = _seed_tag_group(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(
        f"/api/admin/tags/{tag_id}",
        json={"group_id": str(group_id), "group_position": 2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["group_id"] == str(group_id)
    assert body["group_position"] == 2
    with Session(get_engine()) as s:
        tag = s.get(Tag, tag_id)
        assert tag.group_id == group_id
        assert tag.group_position == 2


def test_patch_tag_move_records_group_in_audit(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        group_id = _seed_tag_group(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"group_id": str(group_id)})
    assert r.status_code == 200

    with Session(get_engine()) as s:
        logs = s.exec(
            select(AuditLog).where(
                AuditLog.action == "tag.update",
                AuditLog.entity_id == tag_id,
            )
        ).all()
    assert len(logs) == 1
    after = json.loads(logs[0].after_json)
    before = json.loads(logs[0].before_json)
    # Full snapshot always carries the two group fields on both sides.
    assert set(after.keys()) == {"slug", "name_en", "name_pl", "group_id", "group_position"}
    assert set(before.keys()) == {"slug", "name_en", "name_pl", "group_id", "group_position"}
    assert after["group_id"] == str(group_id)
    assert before["group_id"] is None


def test_patch_tag_move_to_groupless_null(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        group_id = _seed_tag_group(s)
        tag = Tag(slug=f"tag-gl-{uuid.uuid4().hex[:8]}", name_en="X", group_id=group_id)
        s.add(tag)
        s.flush()
        tag_id = tag.id
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"group_id": None})
    assert r.status_code == 200, r.text
    assert r.json()["group_id"] is None
    with Session(get_engine()) as s:
        assert s.get(Tag, tag_id).group_id is None


def test_patch_tag_move_unknown_group_400(client):
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"group_id": str(uuid.uuid4())})
    assert r.status_code == 400, r.text


def test_patch_tag_group_position_explicit_null_422(client):
    """group_position is NOT NULL — an explicit null is a 422, never a 500 (D-NULLSEM-1)."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"group_position": None})
    assert r.status_code == 422, r.text


def test_patch_tag_move_read_after_write(client):
    """AC #8 — move surfaces the tag under its group / back to groupless in GET /api/tag-groups."""
    engine = get_engine()
    with Session(engine) as s:
        admin_id = _seed_admin(s)
        group_id = _seed_tag_group(s)
        tag_id = _seed_tag(s)
        s.commit()

    client.cookies.set("portal_access", admin_token(admin_id))
    # Move into group G.
    r = client.patch(
        f"/api/admin/tags/{tag_id}", json={"group_id": str(group_id), "group_position": 0}
    )
    assert r.status_code == 200
    body = client.get("/api/tag-groups").json()
    grp = next(g for g in body["groups"] if g["id"] == str(group_id))
    assert str(tag_id) in {t["id"] for t in grp["tags"]}
    assert str(tag_id) not in {t["id"] for t in body["groupless"]}

    # Move back to groupless.
    r = client.patch(f"/api/admin/tags/{tag_id}", json={"group_id": None})
    assert r.status_code == 200
    body = client.get("/api/tag-groups").json()
    assert str(tag_id) in {t["id"] for t in body["groupless"]}
