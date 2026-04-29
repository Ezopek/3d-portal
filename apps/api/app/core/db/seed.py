from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.auth.password import hash_password
from app.core.db.models import User, UserRole


def seed_admin(engine: Engine, *, email: str, password: str, display_name: str) -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing is not None:
            return
        user = User(
            email=email,
            display_name=display_name,
            role=UserRole.admin,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.commit()
