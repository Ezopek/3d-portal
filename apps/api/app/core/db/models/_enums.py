"""Enum types used across the DB models package.

Kept in a dedicated module so future tables and migrations can import them
without pulling SQLModel/SQLAlchemy machinery.
"""

from enum import StrEnum


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
