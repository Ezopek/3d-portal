import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    admin = "admin"
    member = "member"


class ModelSource(StrEnum):
    unknown = "unknown"
    printables = "printables"
    thangs = "thangs"
    makerworld = "makerworld"
    cults3d = "cults3d"
    thingiverse = "thingiverse"
    own = "own"
    other = "other"


class ModelStatus(StrEnum):
    not_printed = "not_printed"
    printed = "printed"
    in_progress = "in_progress"
    broken = "broken"


class ModelFileKind(StrEnum):
    stl = "stl"
    image = "image"
    print = "print"
    source = "source"
    archive_3mf = "archive_3mf"


class ExternalSource(StrEnum):
    printables = "printables"
    thangs = "thangs"
    makerworld = "makerworld"
    cults3d = "cults3d"
    thingiverse = "thingiverse"
    other = "other"


class NoteKind(StrEnum):
    description = "description"
    operational = "operational"
    ai_review = "ai_review"
    other = "other"


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


class ThumbnailOverride(SQLModel, table=True):
    __tablename__ = "thumbnailoverride"

    model_id: str = Field(primary_key=True)
    relative_path: str
    set_by_user_id: int = Field(foreign_key="user.id")
    set_at: datetime.datetime = Field(default_factory=_now_utc)


class RenderSelection(SQLModel, table=True):
    __tablename__ = "renderselection"

    model_id: str = Field(primary_key=True)
    selected_paths: str  # JSON-encoded list[str], paths relative to model folder
    set_by_user_id: int = Field(foreign_key="user.id")
    set_at: datetime.datetime = Field(default_factory=_now_utc)
