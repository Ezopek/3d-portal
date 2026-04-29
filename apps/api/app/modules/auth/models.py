from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class MeResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
