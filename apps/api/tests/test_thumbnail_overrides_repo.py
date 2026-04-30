import pytest
from sqlmodel import SQLModel, create_engine

from app.core.db.models import User, UserRole
from app.modules.catalog.thumbnail_overrides import ThumbnailOverrideRepo


@pytest.fixture
def repo() -> ThumbnailOverrideRepo:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    # Seed a user the FK can point at.
    from sqlmodel import Session

    with Session(engine) as s:
        s.add(User(id=1, email="a@b", display_name="A", role=UserRole.admin, password_hash="x"))
        s.commit()
    return ThumbnailOverrideRepo(engine)


def test_set_creates_row(repo):
    repo.set(model_id="001", relative_path="iso.png", user_id=1)
    assert repo.get("001") == "iso.png"


def test_set_is_idempotent_upsert(repo):
    repo.set(model_id="001", relative_path="iso.png", user_id=1)
    repo.set(model_id="001", relative_path="prints/x.jpg", user_id=1)
    assert repo.get("001") == "prints/x.jpg"


def test_get_returns_none_for_unknown_model(repo):
    assert repo.get("999") is None


def test_get_all_returns_dict(repo):
    repo.set(model_id="001", relative_path="iso.png", user_id=1)
    repo.set(model_id="002", relative_path="images/a.png", user_id=1)
    assert repo.get_all() == {"001": "iso.png", "002": "images/a.png"}


def test_clear_removes_existing_row(repo):
    repo.set(model_id="001", relative_path="iso.png", user_id=1)
    assert repo.clear("001") is True
    assert repo.get("001") is None


def test_clear_is_idempotent(repo):
    assert repo.clear("999") is False


def test_purge_orphans_removes_rows_failing_exists(repo):
    repo.set(model_id="001", relative_path="iso.png", user_id=1)
    repo.set(model_id="002", relative_path="prints/missing.jpg", user_id=1)

    def exists(model_id: str, rel: str) -> bool:
        return rel == "iso.png"

    purged = repo.purge_orphans(exists=exists)
    assert purged == [("002", "prints/missing.jpg")]
    assert repo.get("001") == "iso.png"
    assert repo.get("002") is None
