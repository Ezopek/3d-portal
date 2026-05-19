import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field

from app.core.db.models._enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole


class LoginResponse(BaseModel):
    partial_auth: bool = False  # discriminator — always False on this shape
    user: MeResponse


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
    items: list[SessionRow]
