"""Story 49.5 — PUT /api/admin/models/{model_id}/categories (replace-set).

Whole-set, idempotent, explicit last-writer-wins assignment of browse
categories to one model. No merge, no diff, no optimistic-concurrency
precondition — and the contract never claims conflict detection it does not
have.

Mirrors `test_sot_admin_tags.py`'s replace-tags shapes, with two deliberate
departures this story owns:

* `current_admin` only — an `agent` principal is rejected (403), unlike the
  tags replace endpoint. Ratified by Decision AY (architecture.md:3334-3341),
  same admin-curation/agent-ingestion split `tag_group_admin_router.py`
  already applies to facet governance.
* a duplicate-id pre-check the tags precedent lacks — a literal-duplicate
  payload is a 400, never a 500 from an IntegrityError on the composite PK.

The session-scoped shared DB (conftest `_isolated_db`) persists rows across
tests, so every seed uses unique slugs and every assertion is scoped to its
own seeded rows.
"""

import datetime
import json
import uuid

from sqlalchemy import event as sa_event
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
from tests._test_helpers import admin_token, agent_token, member_token

_SUMMARY_KEYS = {"id", "slug", "name_en", "name_pl", "position", "parent_id"}


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_admin(session: Session) -> uuid.UUID:
    u = User(
        email=f"admin-mcat-{uuid.uuid4().hex[:6]}@test.local",
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


def _seed_model(session: Session, *, deleted: bool = False) -> uuid.UUID:
    m = Model(slug=f"m-mcat-{uuid.uuid4().hex[:8]}", name_en="Test Model")
    if deleted:
        m.deleted_at = datetime.datetime.now(datetime.UTC)
    session.add(m)
    session.flush()
    return m.id


def _seed_category(session: Session, *, position: int = 0) -> BrowseCategory:
    slug = f"mcat-{uuid.uuid4().hex[:10]}"
    c = BrowseCategory(slug=slug, name_en=slug.upper(), position=position)
    session.add(c)
    session.flush()
    return c


def _assigned_ids(model_id: uuid.UUID) -> set[uuid.UUID]:
    with Session(get_engine()) as s:
        rows = s.exec(
            select(ModelBrowseCategory).where(ModelBrowseCategory.model_id == model_id)
        ).all()
    return {r.category_id for r in rows}


def _model_update_audits(model_id: uuid.UUID) -> list[AuditLog]:
    with Session(get_engine()) as s:
        return list(
            s.exec(
                select(AuditLog).where(
                    AuditLog.action == "model.update",
                    AuditLog.entity_id == model_id,
                )
            ).all()
        )


def _category_audits(model_id: uuid.UUID) -> list[AuditLog]:
    """Every audit row this endpoint writes must reuse the existing
    entity_type="model" convention — no new M:N-specific entity_type."""
    rows = _model_update_audits(model_id)
    return [r for r in rows if r.entity_type == "model"]


# ---------------------------------------------------------------------------
# Success paths (AC-25 … AC-27)
# ---------------------------------------------------------------------------


def test_replace_categories_200_summary_shape_and_ordering(client):
    """AC-25: 200 + `list[BrowseCategorySummary]` (the embeddable five-plus-one
    key shape `ModelDetail.categories` already uses), ordered `(position, slug)`
    matching the `list_browse_categories` convention."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        low = _seed_category(s, position=1)
        high = _seed_category(s, position=9)
        s.commit()
        low_id, high_id = low.id, high.id

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(high_id), str(low_id)]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert [item["id"] for item in body] == [str(low_id), str(high_id)]
    assert set(body[0].keys()) == _SUMMARY_KEYS
    assert _assigned_ids(model_id) == {low_id, high_id}


def test_replace_categories_is_idempotent(client):
    """AC-26: the same payload twice → same end state both times, and TWO
    independent audit rows. Idempotent means "same end state", not
    "audited once"."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        a = _seed_category(s, position=0)
        b = _seed_category(s, position=1)
        s.commit()
        a_id, b_id = a.id, b.id

    payload = {"category_ids": [str(a_id), str(b_id)]}
    first = client.put(f"/api/admin/models/{model_id}/categories", json=payload)
    second = client.put(f"/api/admin/models/{model_id}/categories", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json() == second.json()
    assert _assigned_ids(model_id) == {a_id, b_id}
    assert len(_model_update_audits(model_id)) == 2


def test_replace_categories_empty_set_clears_all(client):
    """AC-27: `[]` clears every assignment and the model stays valid — a model
    with zero categories is fully public (FR26-CAT-2)."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        cat = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=cat.id))
        s.commit()

    r = client.put(f"/api/admin/models/{model_id}/categories", json={"category_ids": []})
    assert r.status_code == 200, r.text
    assert r.json() == []
    assert _assigned_ids(model_id) == set()


def test_replace_categories_replaces_rather_than_merges(client):
    """AC-25: whole-set replace — the prior assignment is gone, not merged."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        old = _seed_category(s)
        new = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=old.id))
        s.commit()
        old_id, new_id = old.id, new.id

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(new_id)]},
    )
    assert r.status_code == 200, r.text
    assert _assigned_ids(model_id) == {new_id}
    assert old_id not in _assigned_ids(model_id)


# ---------------------------------------------------------------------------
# Validation-before-mutation (AC-28 … AC-31)
# ---------------------------------------------------------------------------


def test_replace_categories_duplicate_ids_400_no_side_effect(client):
    """AC-28: a literal-duplicate payload is a 400 — NOT a 500 from an
    IntegrityError on the composite PK, and NOT a silent de-duplication. This
    closes a gap the `PUT /models/{id}/tags` precedent still has."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        existing = _seed_category(s)
        dupe = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=existing.id))
        s.commit()
        existing_id, dupe_id = existing.id, dupe.id

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(dupe_id), str(dupe_id)]},
    )
    assert r.status_code == 400, r.text
    assert _assigned_ids(model_id) == {existing_id}


def test_replace_categories_unknown_category_404_no_side_effect(client):
    """AC-29 + AC-31: an unresolvable category id is a 404 with NO partial
    replace — validation runs completely before any row is deleted."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        existing = _seed_category(s)
        valid = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=existing.id))
        s.commit()
        existing_id, valid_id = existing.id, valid.id

    before_rows = _assigned_ids(model_id)
    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(valid_id), str(uuid.uuid4())]},
    )
    assert r.status_code == 404, r.text
    # Row-count AND row-identity unchanged — this proves "validate everything,
    # then mutate", not merely "the count happened to match".
    assert _assigned_ids(model_id) == before_rows == {existing_id}


def test_replace_categories_unknown_model_404(client):
    """AC-30: an unknown model id is a 404."""
    _admin_cookie(client)
    r = client.put(
        f"/api/admin/models/{uuid.uuid4()}/categories",
        json={"category_ids": []},
    )
    assert r.status_code == 404, r.text


def test_replace_categories_soft_deleted_model_404(client):
    """AC-30: a soft-deleted model is a 404 too — `_get_model_active`'s existing
    "absent or soft-deleted" LookupError semantics, reused verbatim."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s, deleted=True)
        s.commit()

    r = client.put(f"/api/admin/models/{model_id}/categories", json={"category_ids": []})
    assert r.status_code == 404, r.text


# ---------------------------------------------------------------------------
# Audit + auth (AC-32, AC-33)
# ---------------------------------------------------------------------------


def test_replace_categories_audit_fidelity(client):
    """AC-32: exactly one `model.update` row per successful call, with
    `entity_type="model"` and `before`/`after` carrying the pre- and post-call
    category id sets — the identical shape `replace_model_tags` uses for
    `tag_ids`. No new M:N-specific entity_type is introduced."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        old = _seed_category(s)
        new = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=old.id))
        s.commit()
        old_id, new_id = old.id, new.id

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(new_id)]},
    )
    assert r.status_code == 200, r.text

    audits = _category_audits(model_id)
    assert len(audits) == 1
    before = json.loads(audits[0].before_json)
    after = json.loads(audits[0].after_json)
    assert before == {"category_ids": [str(old_id)]}
    assert after == {"category_ids": [str(new_id)]}
    assert audits[0].entity_type == "model"


def test_replace_categories_auth_matrix(client):
    """AC-33: anonymous 401, member 403, **agent 403**, admin 200.

    The agent rejection is the deliberate tightening relative to
    `PUT /models/{id}/tags` (admin-or-agent, `agent-write`): category curation
    is admin-only per Decision AY."""
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        s.commit()
    body = {"category_ids": []}
    url = f"/api/admin/models/{model_id}/categories"

    client.cookies.delete(ACCESS_COOKIE)
    assert client.put(url, json=body).status_code == 401

    client.cookies.set(ACCESS_COOKIE, member_token(uuid.uuid4()))
    assert client.put(url, json=body).status_code == 403

    client.cookies.set(ACCESS_COOKIE, agent_token(uuid.uuid4()))
    assert client.put(url, json=body).status_code == 403

    _admin_cookie(client)
    assert client.put(url, json=body).status_code == 200


def test_replace_categories_orders_ties_by_slug(client):
    """AC-25 tie-break, review finding #13: the ordering key is
    `(position, slug)`, but every shipped assertion used DISTINCT positions, so
    the `slug` half was never exercised.

    Three categories share one position and are seeded in reverse slug order, so
    a `position`-only sort could not produce the expected result by accident."""
    _admin_cookie(client)
    stamp = uuid.uuid4().hex[:8]
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        tied = [
            BrowseCategory(slug=f"tie-{stamp}-{letter}", name_en=letter.upper(), position=5)
            for letter in ("c", "b", "a")
        ]
        for c in tied:
            s.add(c)
        # A distinct-position row proves `position` still dominates the tie-break.
        first = BrowseCategory(slug=f"tie-{stamp}-z", name_en="Z", position=1)
        s.add(first)
        s.commit()
        ids = {c.slug: c.id for c in [*tied, first]}

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(ids[s_]) for s_ in sorted(ids, reverse=True)]},
    )
    assert r.status_code == 200, r.text
    assert [item["slug"] for item in r.json()] == [
        f"tie-{stamp}-z",
        f"tie-{stamp}-a",
        f"tie-{stamp}-b",
        f"tie-{stamp}-c",
    ]


# ---------------------------------------------------------------------------
# Post-RE-REVIEW repair pass (native bmad-code-review REQUEST_CHANGES, 2026-07-28)
# ---------------------------------------------------------------------------


def _neutralised_first_call(real):
    """Return a wrapper that does NOTHING on its first call and delegates to
    `real` afterwards.

    Same technique as `test_sot_admin_categories.py::_blind_first_call`, applied
    to the two guards that run BEFORE this endpoint mutates anything. Letting the
    first (validating) call through as a no-op reproduces the prequery→COMMIT
    window deterministically in-process: the row really vanished between
    validation and flush, so the RESTRICT FK fires at the write, and the
    re-derivation on the second call sees the true post-rollback state.
    """
    calls = {"n": 0}

    def wrapper(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real(*args, **kwargs)

    return wrapper


def test_replace_categories_vanished_category_race_is_404_not_an_unhandled_500(client, monkeypatch):
    """Re-review finding N-2: `replace_model_categories` had no commit-time
    safety net, so the structurally identical prequery→COMMIT race that finding
    #3 was repaired for on the delete path still escaped as an unhandled 500 —
    while the route description promises a 404 for an unresolvable
    `category_ids` entry.

    A category that vanishes between validation and the INSERT fires
    `model_browse_category.category_id`'s RESTRICT FK. It must surface as the
    documented 404, with the model's existing set provably untouched and no
    audit residue from the rolled-back transaction."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        kept = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=kept.id))
        s.commit()
        kept_id = kept.id

    monkeypatch.setattr(
        admin_service,
        "_validate_browse_category_ids",
        _neutralised_first_call(admin_service._validate_browse_category_ids),
    )

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(uuid.uuid4())]},
    )
    assert r.status_code == 404, r.text
    assert _assigned_ids(model_id) == {kept_id}
    assert _model_update_audits(model_id) == []


def test_replace_categories_vanished_model_race_is_404_not_an_unhandled_500(client, monkeypatch):
    """Re-review finding N-2, model half: `ModelBrowseCategory` carries TWO
    RESTRICT FKs, so a model that vanishes between `_get_model_active` and the
    INSERT must also map onto the existing LookupError → 404 semantics rather
    than escaping as a 500."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        cat = _seed_category(s)
        s.commit()
        cat_id = cat.id
    ghost_model = uuid.uuid4()

    monkeypatch.setattr(
        admin_service,
        "_get_model_active",
        _neutralised_first_call(admin_service._get_model_active),
    )

    r = client.put(
        f"/api/admin/models/{ghost_model}/categories",
        json={"category_ids": [str(cat_id)]},
    )
    assert r.status_code == 404, r.text
    assert _assigned_ids(ghost_model) == set()
    assert _model_update_audits(ghost_model) == []


def test_replace_categories_duplicate_payload_is_still_400_not_404(client):
    """Re-review finding N-2 non-regression: adding the commit-time safety net
    must not turn a duplicate payload into a 404 (or a 500). The duplicate
    pre-check still runs ahead of everything and still answers 400."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        cat = _seed_category(s)
        s.commit()
        cat_id = cat.id

    r = client.put(
        f"/api/admin/models/{model_id}/categories",
        json={"category_ids": [str(cat_id), str(cat_id)]},
    )
    assert r.status_code == 400, r.text
    assert _assigned_ids(model_id) == set()


def test_replace_categories_validates_every_id_before_any_delete_is_attempted(client, monkeypatch):
    """Re-review finding N-4(b): AC-31's "validate everything, then mutate" was
    pinned by OUTCOME only — moving the existence loop after the deletes with a
    compensating rollback kept every replace test green, because "no partial
    replace" is observable either way.

    This pins the ORDER instead, by recording when validation runs against when
    the first ORM delete of a `model_browse_category` row is actually issued. A
    delete that starts before the whole payload resolves reverses the recorded
    sequence and fails here."""
    _admin_cookie(client)
    with Session(get_engine()) as s:
        model_id = _seed_model(s)
        old = _seed_category(s)
        new = _seed_category(s)
        s.add(ModelBrowseCategory(model_id=model_id, category_id=old.id))
        s.commit()
        new_id = new.id

    steps: list[str] = []
    real = admin_service._validate_browse_category_ids

    def recording(*args, **kwargs):
        steps.append("validate")
        return real(*args, **kwargs)

    monkeypatch.setattr(admin_service, "_validate_browse_category_ids", recording)

    def on_delete(mapper, connection, target):
        steps.append("delete")

    sa_event.listen(ModelBrowseCategory, "before_delete", on_delete)
    try:
        r = client.put(
            f"/api/admin/models/{model_id}/categories",
            json={"category_ids": [str(new_id)]},
        )
    finally:
        sa_event.remove(ModelBrowseCategory, "before_delete", on_delete)

    assert r.status_code == 200, r.text
    assert steps == ["validate", "delete"]
    assert _assigned_ids(model_id) == {new_id}
