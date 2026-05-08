"""Shared helpers for SQLModel definitions in this package.

These are deliberately small and stable so that adding a new entity table
doesn't require thinking about the FK or UUID column shape.
"""

import datetime

from sqlalchemy import Column, DateTime, ForeignKey, TypeDecorator
from sqlalchemy import Uuid as _SAUuid


def _now_utc() -> datetime.datetime:
    """Return the current UTC datetime for use as a SQLModel default_factory."""
    return datetime.datetime.now(datetime.UTC)


class UTCDateTime(TypeDecorator):
    """DateTime that always returns timezone-aware UTC datetimes.

    SQLite stores datetimes as naive strings; this decorator re-attaches UTC
    tzinfo on read so comparisons against ``datetime.now(UTC)`` work correctly
    in both SQLite (tests) and PostgreSQL (production, which already returns
    tz-aware values).
    """

    impl = DateTime
    cache_ok = True

    def process_result_value(
        self, value: datetime.datetime | None, dialect: object
    ) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC)
        return value


def sa_uuid_type() -> _SAUuid:
    """SQLAlchemy UUID type that works on both SQLite (CHAR(32)) and Postgres (uuid).

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
