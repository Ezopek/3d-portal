import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.db.models import User, UserRole
from app.modules.catalog.render_selection import RenderSelectionRepo


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        admin = User(email="a@b", display_name="A", role=UserRole.admin, password_hash="x")
        s.add(admin)
        s.commit()
        s.refresh(admin)
        admin_id = admin.id
    repo = RenderSelectionRepo(engine)
    repo._admin_id = admin_id  # stash for test use
    return repo


def test_get_returns_empty_list_when_unset(repo):
    assert repo.get("001") == []


def test_set_persists_paths_as_json(repo):
    repo.set(model_id="001", paths=["a.stl", "files/b.stl"], user_id=repo._admin_id)
    assert repo.get("001") == ["a.stl", "files/b.stl"]


def test_set_overrides_previous(repo):
    repo.set(model_id="001", paths=["a.stl"], user_id=repo._admin_id)
    repo.set(model_id="001", paths=["b.stl", "c.stl"], user_id=repo._admin_id)
    assert repo.get("001") == ["b.stl", "c.stl"]


def test_get_all_returns_dict(repo):
    repo.set(model_id="001", paths=["a.stl"], user_id=repo._admin_id)
    repo.set(model_id="002", paths=["x.stl", "y.stl"], user_id=repo._admin_id)
    assert repo.get_all() == {"001": ["a.stl"], "002": ["x.stl", "y.stl"]}


def test_clear_removes_row_and_returns_true(repo):
    repo.set(model_id="001", paths=["a.stl"], user_id=repo._admin_id)
    assert repo.clear("001") is True
    assert repo.get("001") == []


def test_clear_returns_false_when_no_row(repo):
    assert repo.clear("001") is False


def test_purge_orphans_removes_dead_paths(repo):
    repo.set(model_id="001", paths=["alive.stl", "dead.stl"], user_id=repo._admin_id)

    def exists(model_id: str, path: str) -> bool:
        return path == "alive.stl"

    purged = repo.purge_orphans(exists=exists)
    assert purged == [("001", "dead.stl")]
    assert repo.get("001") == ["alive.stl"]


def test_purge_orphans_drops_row_when_all_paths_dead(repo):
    repo.set(model_id="001", paths=["dead-a.stl", "dead-b.stl"], user_id=repo._admin_id)

    purged = repo.purge_orphans(exists=lambda mid, p: False)
    assert sorted(purged) == [("001", "dead-a.stl"), ("001", "dead-b.stl")]
    assert repo.get("001") == []
