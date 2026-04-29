import pytest

from app.core.auth.password import hash_password, verify_password


def test_hash_is_not_plaintext():
    h = hash_password("secret123")
    assert h != "secret123"
    assert h.startswith("$2")


def test_verify_round_trip():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong", h) is False


def test_verify_rejects_garbage_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False
