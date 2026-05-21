"""Request schemas for the Initiative 5 public invite/register router.

Story 6.4 introduces the public-side schemas distinct from
``admin_schemas.py`` (which carries the admin-router shapes). Right now
the only public-side schema is :class:`RegisterRequest`; future Init 5
public surfaces (e.g. rate-limit-aware refresh tweaks) land here.

Schema-layer validation is intentionally tight where it can be cheap:
- ``token`` is length-bounded to 43 chars, matching ``secrets.token_urlsafe(32)``
  output exactly (Story 6.2 generator contract).
- ``email`` uses pydantic ``EmailStr`` for RFC-syntax validation.
- ``password`` carries a length floor of 1 (DOS guard); the meaningful
  ``>=12`` policy + zxcvbn score check live in the route handler so the
  failure surface emits the user-facing 422 message + audit row.
- ``display_name`` (Story 12.3) is OPTIONAL on register: when absent the
  handler derives the value from the email local-part (legacy behaviour);
  when present the trimmed value is persisted verbatim. The 1..120 length
  bound matches the self-service ``DisplayNameUpdateRequest`` envelope so
  both surfaces share the same validation contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload accepted by ``POST /api/auth/register``."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=43, max_length=43)
    email: EmailStr
    password: str = Field(min_length=1)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
