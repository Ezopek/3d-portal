import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.db.models._enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole


class DisplayNameUpdateRequest(BaseModel):
    """Payload accepted by ``PATCH /api/auth/me/display-name`` (Story 12.3).

    Schema floor is ``min_length=1`` to reject literal empty strings at the
    pydantic layer; the route handler additionally strips and re-validates
    so pure-whitespace payloads are rejected with the same 422 surface.
    The 120-char ceiling mirrors :class:`RegisterRequest.display_name` so
    both ingress surfaces share one contract.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)


class LoginResponse(BaseModel):
    partial_auth: bool = False  # discriminator — always False on this shape
    user: MeResponse
    totp_enroll_required: bool = (
        False  # Story 7.4 — true when Decision F enforcement requires enrollment
    )


class PartialAuthResponse(BaseModel):
    """Returned by POST /api/auth/login when user.totp_enabled_at IS NOT NULL.

    No cookies are set on this response; the frontend exchanges
    ``partial_token`` for full auth via POST /api/auth/2fa/verify.
    """

    partial_auth: bool = True  # discriminator — always True on this shape
    totp_required: bool = True
    partial_token: str = Field(min_length=20, max_length=64)


class SessionRow(BaseModel):
    family_id: uuid.UUID
    last_used_at: datetime.datetime | None
    family_issued_at: datetime.datetime
    ip: str | None
    user_agent: str | None
    is_current: bool


class SessionsResponse(BaseModel):
    """Response shape for ``GET /api/auth/sessions`` (Story 12.5).

    ``total`` reflects the unpaginated count of active families for the user so
    the client can render ``Showing N-M of T`` text. ``page`` / ``page_size``
    are echoed back from the request (or their server defaults) so the client
    doesn't have to round-trip through its own search-state to know what it got.
    """

    items: list[SessionRow]
    total: int = 0
    page: int = 1
    page_size: int = 20
