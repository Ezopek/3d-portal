"""Pydantic request/response models for the TOTP 2FA enrollment surface.

Schema shapes are binding per Story 7.2 AC-7 (architecture.md Decisions D + E
single-cleartext-surface invariant): nothing here may carry the cleartext
secret outside the enroll/confirm response bodies, and no hash/ciphertext
ever appears in any response.
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field


class EnrollResponse(BaseModel):
    """Returned by POST /api/auth/2fa/enroll.

    The ``manual_secret`` is the cleartext base32 — surfaced once to the
    enrolling user (their authenticator app needs it). The ``enrollment_token``
    is the opaque handle the client exchanges in the follow-up confirm call.
    """

    qr_svg: str
    manual_secret: str = Field(min_length=32, max_length=32)
    enrollment_token: str


class ConfirmRequest(BaseModel):
    """Body of POST /api/auth/2fa/enroll/confirm.

    ``code`` is the 6-digit TOTP code freshly read by the user from their
    authenticator app; ``^\\d{6}$`` blocks recovery-code-shape inputs from
    bleeding into the enroll-confirm flow (recovery codes are 8-char hex and
    are consumed by the partial-auth verify endpoint in Story 7.3).
    """

    enrollment_token: str = Field(min_length=20, max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


class ConfirmResponse(BaseModel):
    """Returned by POST /api/auth/2fa/enroll/confirm.

    The cleartext recovery codes appear here exactly once per Decision E
    §1530 "display ONCE" guarantee; later /status reads return only batch
    metadata (no cleartext, no hashes).
    """

    recovery_codes: list[str] = Field(min_length=8, max_length=8)
    batch_id: uuid.UUID
    generated_at: datetime.datetime


class StatusResponse(BaseModel):
    """Returned by GET /api/auth/2fa/status.

    Agents always see ``enabled=false`` (per AC-6 step 2 — silent disabled
    instead of 403 so misconfigured agent runners do not enumerate the
    endpoint existence).
    """

    enabled: bool
    batch_id: uuid.UUID | None = None
    generated_at: datetime.datetime | None = None
    codes_remaining: int | None = None


class VerifyRequest(BaseModel):
    """Body of POST /api/auth/2fa/verify.

    ``code`` accepts EITHER a 6-digit TOTP code OR an 8-char lowercase
    hex recovery code; the regex below matches both shapes and the
    server-side handler routes by shape (Story 7.3 AC-3 step 4).
    """

    partial_token: str = Field(min_length=20, max_length=64)
    code: str = Field(pattern=r"^(\d{6}|[0-9a-f]{8})$")


class ReauthRequest(BaseModel):
    """Body of POST /api/auth/2fa/recovery-codes/regenerate AND
    POST /api/auth/2fa/disable.

    Both endpoints re-auth on (password + totp_code) before mutating
    recovery_codes / users.totp_enabled_at. Sharing one request model
    across both endpoints is binding (Story 7.5 AC-3) — operators
    reading the OpenAPI doc see the same shape twice, reinforcing the
    symmetric re-auth contract.

    ``totp_code`` regex ``^\\d{6}$`` INTENTIONALLY rejects the recovery
    code shape ``[0-9a-f]{8}`` (which VerifyRequest accepts). A stolen
    or screenshotted recovery code MUST NOT pass the re-auth gate —
    the user must prove possession of the authenticator-app device.
    """

    password: str = Field(min_length=1, max_length=128)
    totp_code: str = Field(pattern=r"^\d{6}$")


class RegenerateResponse(ConfirmResponse):
    """Returned by POST /api/auth/2fa/recovery-codes/regenerate.

    Wire shape IDENTICAL to ConfirmResponse (Story 7.2 enroll/confirm)
    — same fields, same types. The subclass exists as a distinct
    OpenAPI symbol so endpoint readers can navigate from the path to
    a dedicated response model name. Adding fields to RegenerateResponse
    in the future must NOT change ConfirmResponse semantics.
    """
