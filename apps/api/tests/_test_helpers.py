"""Centralized JWT token helpers for tests (Story 24.1, TB-030).

This module hoists the duplicated `_admin_token` / `_agent_token` /
`_member_token` definitions that previously lived in 13 separate test
files into a single shared API. Each helper internally reads
`get_settings().jwt_secret` at call time, deferring secret resolution to
whatever the active `Settings()` returns — mirroring the production
`encode_token` call shape (see Story 18.4 commits `be11035` and
`2ae6569` for prior art).

Why call-time resolution matters: other tests in the suite call
`monkeypatch.setenv("JWT_SECRET", ...)` without clearing
`get_settings()`'s LRU cache, so a hardcoded constant here could
disagree with whichever secret the middleware actually decodes against
in full-suite context (TB-021 Failure A: cross-file pollution).

The `apps/api/tests/conftest.py:99-106` `isolated_client` fixture owns
the canonical guardrail:

1. `monkeypatch.setenv("JWT_SECRET", "test-secret-not-real")` — sets env.
2. `get_settings.cache_clear()` — wipes LRU so the next call re-reads env.
3. ... test runs, helpers below resolve `get_settings().jwt_secret` to
   the just-set value ...
4. `finally: get_settings.cache_clear()` — wipes cache on teardown so
   the next test starts fresh.

These helpers compose with that discipline by deferring all secret
resolution to call time. Do NOT hardcode `"test-secret-not-real"` here
or in callers — that constant lives exactly once, in conftest.
"""

from __future__ import annotations

import uuid

from app.core.auth.jwt import encode_token
from app.core.config import get_settings


def admin_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str:
    """Mint a JWT for an admin user. Secret resolved at call time."""
    return encode_token(
        subject=str(user_id),
        role="admin",
        secret=get_settings().jwt_secret,
        ttl_minutes=ttl_minutes,
    )


def agent_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str:
    """Mint a JWT for an agent user. Secret resolved at call time."""
    return encode_token(
        subject=str(user_id),
        role="agent",
        secret=get_settings().jwt_secret,
        ttl_minutes=ttl_minutes,
    )


def member_token(user_id: uuid.UUID, *, ttl_minutes: int = 30) -> str:
    """Mint a JWT for a member user. Secret resolved at call time."""
    return encode_token(
        subject=str(user_id),
        role="member",
        secret=get_settings().jwt_secret,
        ttl_minutes=ttl_minutes,
    )
