from sqlmodel import Session, select

from app.core.auth.password import verify_password
from app.core.db.models import User, UserRole
from app.core.db.seed import seed_admin
from app.core.db.session import create_engine_for_url, init_schema


def test_seed_creates_admin_when_absent(tmp_path):
    engine = create_engine_for_url(f"sqlite:///{tmp_path}/seed.db")
    init_schema(engine)
    seed_admin(engine, email="a@b.c", password="pw", display_name="Admin")
    with Session(engine) as s:
        users = s.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].email == "a@b.c"
    assert users[0].role is UserRole.admin
    assert verify_password("pw", users[0].password_hash)


def test_seed_is_idempotent(tmp_path):
    engine = create_engine_for_url(f"sqlite:///{tmp_path}/seed.db")
    init_schema(engine)
    seed_admin(engine, email="a@b.c", password="pw", display_name="Admin")
    seed_admin(engine, email="a@b.c", password="changed", display_name="Admin")
    with Session(engine) as s:
        u = s.exec(select(User).where(User.email == "a@b.c")).one()
    # idempotent = does not change existing user
    assert verify_password("pw", u.password_hash)
    assert not verify_password("changed", u.password_hash)
