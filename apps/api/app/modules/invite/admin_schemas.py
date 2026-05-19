"""Request/response schemas for the Initiative 5 invite-token admin router.

Kept separate from ``models.py`` (which holds the SQLModel + helpers) for
parity with ``sot/admin_schemas.py`` (Init 2 SoT pattern) -- every admin
write/read surface in the repo isolates its Pydantic schemas in a
dedicated module so the SQLModel + Pydantic concerns stay independent.

Hygiene rule: NONE of these schemas expose the cleartext token field
other than ``GenerateInviteResponse``. Decision B (architecture.md
§1425-1456) is binding: cleartext token surfaces once, at generation.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.db.models._enums import UserRole
from app.modules.invite.models import InviteTTLPreset

StatusLiteral = Literal["active", "used", "expired", "revoked"]
# Request-only role contract: NFR5-INT-1 binds the endpoint to reject `agent`
# at the input layer, so the OpenAPI schema advertises only the accepted set
# (admin UI / codegen pick this up — UserRole would mislead).
InviteRoleRequestLiteral = Literal["member", "admin"]
# Wire contract for ttl_preset: enum NAMES per AC-1, not IntEnum values.
# Names resolve to seconds in ``resolve_ttl_seconds()``.
InviteTTLPresetNameLiteral = Literal["ONE_DAY", "THREE_DAYS", "SEVEN_DAYS", "THIRTY_DAYS"]


class GenerateInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: InviteRoleRequestLiteral
    ttl_preset: InviteTTLPresetNameLiteral | None = None
    ttl_seconds: int | None = Field(default=None, ge=60, le=7776000)

    @model_validator(mode="after")
    def _exactly_one_ttl(self) -> GenerateInviteRequest:
        if (self.ttl_preset is None) == (self.ttl_seconds is None):
            raise ValueError("specify exactly one of ttl_preset, ttl_seconds")
        return self

    def resolve_ttl_seconds(self) -> int:
        if self.ttl_preset is not None:
            return InviteTTLPreset[self.ttl_preset].value
        assert self.ttl_seconds is not None  # validated above
        return self.ttl_seconds


class GenerateInviteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    invite_id: uuid.UUID
    token: str
    registration_url: str
    role: UserRole
    ttl_seconds: int
    expires_at: datetime.datetime


class InviteListItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    invite_id: uuid.UUID
    role: UserRole
    ttl_seconds: int
    generated_by_user_id: uuid.UUID | None
    generated_at: datetime.datetime
    expires_at: datetime.datetime
    used_by_user_id: uuid.UUID | None
    used_at: datetime.datetime | None
    used_from_ip: str | None
    revoked_at: datetime.datetime | None
    status: StatusLiteral


class InviteListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: int
    items: list[InviteListItem]
    page: int
    page_size: int


def derive_status(
    *,
    used_at: datetime.datetime | None,
    revoked_at: datetime.datetime | None,
    generated_at: datetime.datetime,
    ttl_seconds: int,
    now: datetime.datetime,
) -> StatusLiteral:
    """Compute derived status uniformly. Precedence: revoked > used > expired > active."""
    if revoked_at is not None:
        return "revoked"
    if used_at is not None:
        return "used"
    if generated_at + datetime.timedelta(seconds=ttl_seconds) <= now:
        return "expired"
    return "active"
