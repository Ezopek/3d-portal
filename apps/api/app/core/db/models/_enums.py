"""Enum types used across the DB models package.

Kept in a dedicated module so future tables and migrations can import them
without pulling SQLModel/SQLAlchemy machinery.
"""

from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    agent = "agent"
    member = "member"


class ModelSource(StrEnum):
    unknown = "unknown"
    printables = "printables"
    thangs = "thangs"
    makerworld = "makerworld"
    cults3d = "cults3d"
    thingiverse = "thingiverse"
    crealitycloud = "crealitycloud"
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
    # Initiative 12 Story 19.6 (Decision S) — auto-generated STL preview
    # renders (iso/front/side/top) for the anonymous share view. Distinct
    # from `image` (admin-curated photos + Story 11.1 admin auto-render
    # `<view>-render.png` rows) so the share view can surface previews
    # without conflating with admin gallery semantics.
    stl_preview = "stl_preview"


class ExternalSource(StrEnum):
    printables = "printables"
    thangs = "thangs"
    makerworld = "makerworld"
    cults3d = "cults3d"
    thingiverse = "thingiverse"
    crealitycloud = "crealitycloud"
    other = "other"


class NoteKind(StrEnum):
    description = "description"
    operational = "operational"
    ai_review = "ai_review"
    other = "other"
