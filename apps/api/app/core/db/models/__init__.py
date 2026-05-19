"""DB models package.

Re-exports every public symbol so imports of the historical form
`from app.core.db.models import User, Category, ...` keep working
without changes at call sites.
"""

# ``_invite_models`` is imported purely for side effects: importing it
# registers the ``InviteToken`` table on ``SQLModel.metadata`` so
# ``init_schema()`` (the non-Alembic path used in tests and on a fresh dev
# DB boot in apps/api/app/main.py) picks up ``invite_tokens`` via
# ``create_all()``. Alembic env.py keeps its own explicit import — both
# surfaces must register the model.
from app.modules.invite import models as _invite_models  # noqa: F401

from ._audit import AuditLog
from ._auth import RefreshToken
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
from ._helpers import UTCDateTime, _now_utc, sa_uuid_type, uuid_fk
from ._recovery import RecoveryCode
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
    "RecoveryCode",
    "RefreshToken",
    "Tag",
    "UTCDateTime",
    "User",
    "UserRole",
    "_now_utc",
    "sa_uuid_type",
    "uuid_fk",
]
