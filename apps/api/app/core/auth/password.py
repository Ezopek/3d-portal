import bcrypt

from app.core.config import get_settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(
        plain.encode(),
        bcrypt.gensalt(rounds=get_settings().bcrypt_rounds),
    ).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:  # security boundary: any garbage input must return False, never raise
        return False
