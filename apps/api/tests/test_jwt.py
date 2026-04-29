import pytest

from app.core.auth.jwt import TokenError, decode_token, encode_token


def test_round_trip_returns_subject_and_role():
    token = encode_token(subject="42", role="admin", secret="x", ttl_minutes=30)
    claims = decode_token(token, secret="x")
    assert claims["sub"] == "42"
    assert claims["role"] == "admin"


def test_expired_token_raises():
    token = encode_token(subject="1", role="admin", secret="x", ttl_minutes=-1)
    with pytest.raises(TokenError):
        decode_token(token, secret="x")


def test_wrong_secret_raises():
    token = encode_token(subject="1", role="admin", secret="x", ttl_minutes=30)
    with pytest.raises(TokenError):
        decode_token(token, secret="y")
