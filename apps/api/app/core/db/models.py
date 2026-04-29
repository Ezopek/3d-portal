import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    admin = "admin"
    member = "member"


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str
    role: UserRole
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    last_login_at: datetime.datetime | None = None


class AuditEvent(SQLModel, table=True):
    __tablename__ = "auditevent"

    id: int | None = Field(default=None, primary_key=True)
    at: datetime.datetime = Field(default_factory=_now_utc, index=True)
    actor_user_id: int | None = Field(default=None, foreign_key="user.id")
    kind: str = Field(index=True)
    payload: str
