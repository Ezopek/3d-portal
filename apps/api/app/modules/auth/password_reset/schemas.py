"""Pydantic schemas for the admin-issued password-reset link (Story 8.5)."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class PasswordResetConsumeRequest(BaseModel):
    """Public ``POST /api/auth/password-reset`` request body.

    The token width is locked to ``secrets.token_urlsafe(32)`` output
    exactly (43 chars). ``new_password`` is loose at the schema tier
    (min_length=1) so the meaningful policy gates (≥12 chars + zxcvbn ≥3)
    fire at the handler tier — mirrors the Story 6.4
    ``invite/router.py:48-52`` verbatim convention so the failure surface
    emits the user-facing 422 + audit row.
    """

    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=43, max_length=43)
    new_password: str = Field(min_length=1)


class PasswordResetMintResponse(BaseModel):
    """Admin ``POST /api/admin/users/{user_id}/password-reset`` response.

    ``reset_url`` is the one-time-shown cleartext-bearing URL. Subsequent
    admin-panel reads cannot retrieve it (Redis is the sole holder, and
    no list endpoint exists for password-reset tokens). ``expires_at`` is
    surfaced so the operator can see "how long is this link valid?"
    without re-reading the TTL from Settings.
    """

    model_config = ConfigDict(frozen=True)
    reset_url: str
    expires_at: datetime.datetime
