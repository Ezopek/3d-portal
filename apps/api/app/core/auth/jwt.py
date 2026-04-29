from datetime import datetime, timedelta, timezone

import jwt as _jwt


class TokenError(Exception):
    pass


def encode_token(*, subject: str, role: str, secret: str, ttl_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return _jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, *, secret: str) -> dict:
    try:
        return _jwt.decode(token, secret, algorithms=["HS256"])
    except _jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
