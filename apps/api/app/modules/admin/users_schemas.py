"""Request/response schemas for the Initiative 5 admin Users tab (Story 8.2).

Mirrors ``app.modules.invite.admin_schemas`` (Story 6.3): per-router Pydantic
projection isolated from SQLModel + service layers. Decision I
(``architecture.md §1601-1630``) binds the panel-visible column set to the 8
fields below; the matching invariant lives in ``epics.md §1770``.

Hygiene rule: this schema exposes only the 8 panel-visible columns from
epics §1770; password_hash + totp_secret are NEVER projected here. The admin
panel has no legitimate read of those columns; surfacing them would widen
blast radius on accidental endpoint leaks.
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from app.core.db.models._enums import UserRole


class AdminUserListItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    created_at: datetime.datetime
    last_active_at: datetime.datetime | None
    totp_enabled: bool
    is_active: bool
    force_2fa_enrollment: bool


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: int
    items: list[AdminUserListItem]
    page: int
    page_size: int


class UserMutationRequest(BaseModel):
    """Per-user mutation body for ``PATCH /api/admin/users/{id}`` (Story 8.3).

    Binds FR5-ADMIN-2 (per-user actions): role mutation + is_active toggle.
    Four foot-gun guardrails are enforced at the endpoint tier, not the
    schema: self-mutation, agent-role mutation, promote-to-agent, and the
    no-mutation-provided 400. The schema's role is to forbid unknown
    fields so future stories cannot piggyback (e.g. ``force_2fa_enrollment``
    belongs to Story 8.4's distinct endpoint, not this one).
    """

    model_config = ConfigDict(extra="forbid")
    role: UserRole | None = None
    is_active: bool | None = None
