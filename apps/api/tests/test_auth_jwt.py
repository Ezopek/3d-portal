"""apps/api/tests/test_auth_jwt.py"""
from app.core.auth.jwt import decode_token, encode_token


def test_encode_includes_jti():
    t = encode_token(subject="u", role="admin", secret="s", ttl_minutes=10)
    claims = decode_token(t, secret="s")
    assert "jti" in claims
    assert claims["jti"]
    # jti unique across calls
    t2 = encode_token(subject="u", role="admin", secret="s", ttl_minutes=10)
    assert decode_token(t2, secret="s")["jti"] != claims["jti"]
