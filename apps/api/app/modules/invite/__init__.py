"""Initiative 5 invite-token feature module.

Story 6.1 shipped the SQLModel primitives (``models.py``).
Story 6.2 adds the dual-backed Redis+SQLite ``InviteService`` (``service.py``).
Stories 6.3 (admin endpoints) and 6.4 (public ``/register?token=...``) wire
the service into routers.
"""

from app.modules.invite.admin_schemas import (
    GenerateInviteRequest,
    GenerateInviteResponse,
    InviteListItem,
    InviteListResponse,
)
from app.modules.invite.models import InviteToken, InviteTTLPreset, hash_token
from app.modules.invite.schemas import RegisterRequest
from app.modules.invite.service import (
    ActiveInvite,
    GenerateInviteResult,
    InviteAlreadyResolved,
    InviteConsumed,
    InviteNotFound,
    InviteService,
    InviteServiceError,
)

__all__ = [
    "ActiveInvite",
    "GenerateInviteRequest",
    "GenerateInviteResponse",
    "GenerateInviteResult",
    "InviteAlreadyResolved",
    "InviteConsumed",
    "InviteListItem",
    "InviteListResponse",
    "InviteNotFound",
    "InviteService",
    "InviteServiceError",
    "InviteTTLPreset",
    "InviteToken",
    "RegisterRequest",
    "hash_token",
]
