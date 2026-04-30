"""Sentry SDK wiring for the API.

`init_sentry` is a no-op when DSN is empty, mirroring the frontend guard.
`scrub_event` is registered as `before_send` to strip credentials from
outgoing events before they leave the process.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk

_SENSITIVE_KEYS_LOWER = frozenset(
    {
        "password",
        "passwd",
        "authorization",
        "cookie",
        "access_token",
        "refresh_token",
        "token",
    }
)
_FILTERED = "[Filtered]"


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (_FILTERED if k.lower() in _SENSITIVE_KEYS_LOWER else _scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def scrub_event(
    event: dict[str, Any] | None, hint: dict[str, Any]
) -> dict[str, Any] | None:
    if event is None:
        return None
    return _scrub(event)


def init_sentry(*, dsn: str | None, environment: str, release: str) -> None:
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        sample_rate=1.0,
        traces_sample_rate=0.0,
        before_send=scrub_event,
    )
    sentry_sdk.set_tag("service", "api")
