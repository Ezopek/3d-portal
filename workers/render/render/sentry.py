"""Sentry SDK wiring for the render worker."""

from __future__ import annotations

import sentry_sdk


def init_sentry(*, dsn: str | None, environment: str, release: str) -> None:
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        sample_rate=1.0,
        traces_sample_rate=0.0,
    )
    sentry_sdk.set_tag("service", "render")
