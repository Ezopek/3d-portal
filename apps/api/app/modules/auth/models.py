import datetime
import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str


class LoginResponse(BaseModel):
    user: MeResponse


class SessionRow(BaseModel):
    family_id: uuid.UUID
    last_used_at: datetime.datetime | None
    family_issued_at: datetime.datetime
    ip: str | None
    user_agent: str | None
    is_current: bool


class SessionsResponse(BaseModel):
    items: list[SessionRow]
