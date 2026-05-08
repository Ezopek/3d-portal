import datetime
import uuid
from typing import Any

import jwt as _jwt


class TokenError(Exception):
    pass


def encode_token(*, subject: str, role: str, secret: str, ttl_minutes: int) -> str:
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(minutes=ttl_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return _jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, *, secret: str) -> dict[str, Any]:
    try:
        return _jwt.decode(token, secret, algorithms=["HS256"])
    except _jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
