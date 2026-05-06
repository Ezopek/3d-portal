"""DB models package.

Re-exports every public symbol so imports of the historical form
`from app.core.db.models import User, Category, ...` keep working
without changes at call sites.
"""

from ._audit import AuditLog
from ._entities import (
    Category,
    Model,
    ModelExternalLink,
    ModelFile,
    ModelNote,
    ModelPrint,
    ModelTag,
    Tag,
)
from ._enums import (
    ExternalSource,
    ModelFileKind,
    ModelSource,
    ModelStatus,
    NoteKind,
    UserRole,
)
from ._helpers import _now_utc, sa_uuid_type, uuid_fk
from ._user import User

__all__ = [
    "AuditLog",
    "Category",
    "ExternalSource",
    "Model",
    "ModelExternalLink",
    "ModelFile",
    "ModelFileKind",
    "ModelNote",
    "ModelPrint",
    "ModelSource",
    "ModelStatus",
    "ModelTag",
    "NoteKind",
    "Tag",
    "User",
    "UserRole",
    "_now_utc",
    "sa_uuid_type",
    "uuid_fk",
]
