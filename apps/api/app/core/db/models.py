import datetime
import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy import Uuid as _SAUuid
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


def sa_uuid_type() -> _SAUuid:
    """SQLAlchemy UUID type that works on both SQLite (TEXT) and Postgres (uuid).

    Translates to a native uuid column on Postgres and CHAR(32) on SQLite —
    both transparent to Python which sees uuid.UUID. Isolated as a helper so
    every entity FK uses the same type definition.
    """
    return _SAUuid(as_uuid=True)


def uuid_fk(
    target: str,
    *,
    ondelete: str,
    nullable: bool = False,
    index: bool = False,
    primary_key: bool = False,
) -> Column:
    """Standard UUID foreign-key column for entity tables.

    Centralizes the (sa_uuid_type, ForeignKey, nullable, index, primary_key)
    pattern so every entity table FK looks the same and uses the same UUID
    column type.
    """
    return Column(
        sa_uuid_type(),
        ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        index=index,
        primary_key=primary_key,
    )


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


class Category(SQLModel, table=True):
    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),
        # NULL != NULL in SQL, so the composite constraint above won't catch two
        # root categories (parent_id IS NULL) with the same slug.  A partial
        # unique index on slug WHERE parent_id IS NULL covers that case on both
        # SQLite (3.9+) and Postgres.
        Index(
            "uq_category_root_slug",
            "slug",
            unique=True,
            sqlite_where=Column("parent_id").is_(None),
            postgresql_where=Column("parent_id").is_(None),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=True),
    )
    slug: str = Field(index=True)
    name_en: str
    name_pl: str | None = None
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(unique=True, index=True)
    name_en: str
    name_pl: str | None = None
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class Model(SQLModel, table=True):
    __tablename__ = "model"
    __table_args__ = (
        CheckConstraint(
            "rating IS NULL OR (rating BETWEEN 1.0 AND 5.0)",
            name="ck_model_rating_range",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    legacy_id: str | None = Field(default=None, unique=True, index=True)
    slug: str = Field(unique=True, index=True)
    name_en: str
    name_pl: str | None = None
    category_id: uuid.UUID = Field(
        sa_column=uuid_fk("category.id", ondelete="RESTRICT", nullable=False),
    )
    source: ModelSource = Field(default=ModelSource.unknown)
    status: ModelStatus = Field(default=ModelStatus.not_printed, index=True)
    rating: float | None = None
    date_added: datetime.date = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).date()
    )
    deleted_at: datetime.datetime | None = Field(default=None, index=True)
    created_at: datetime.datetime = Field(default_factory=_now_utc)
    updated_at: datetime.datetime = Field(default_factory=_now_utc)


class ModelFile(SQLModel, table=True):
    __tablename__ = "model_file"
    __table_args__ = (
        UniqueConstraint(
            "model_id",
            "sha256",
            "kind",
            name="uq_model_file_model_sha_kind",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_id: uuid.UUID = Field(
        sa_column=uuid_fk("model.id", ondelete="CASCADE", nullable=False, index=True),
    )
    kind: ModelFileKind
    original_name: str
    storage_path: str = Field(unique=True)
    sha256: str = Field(index=True)
    size_bytes: int
    mime_type: str
    created_at: datetime.datetime = Field(default_factory=_now_utc)
