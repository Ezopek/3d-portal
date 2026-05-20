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


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: int
    items: list[AdminUserListItem]
    page: int
    page_size: int
