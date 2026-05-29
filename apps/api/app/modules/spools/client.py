"""Initiative 19 Story 31.1 (Decisions AD + AE) — httpx wrapper around
Spoolman's read-only ``/api/v1/*`` endpoints.

Single-instance circuit breaker (3 consecutive failures -> 30s open window).
Every call emits a structured log + OTel span + Sentry breadcrumb tagged
``external_service=spoolman`` per NFR19-OBS-1; response bodies are NEVER
logged at INFO (brainstorm anti-pattern 8).
"""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Self, TypeVar

import httpx
import sentry_sdk
from opentelemetry import trace
from pydantic import BaseModel, TypeAdapter

from app.modules.spools.models import SpoolmanFilament, SpoolmanSpool, SpoolmanVendor

_LOG = logging.getLogger(__name__)
_TRACER = trace.get_tracer(__name__)

T = TypeVar("T", bound=BaseModel)

# because "3 consecutive errors signal real outage rather than transient blip
# per Decision AD; matches typical resilience-pattern band — AC-7"
_CIRCUIT_FAILURE_THRESHOLD = 3
# because "30s open window matches the spools:summary:v1 Redis TTL so a fresh
# probe naturally retries when the cache would expire anyway — Decision AD,
# AC-7"
_CIRCUIT_OPEN_SECONDS = 30.0


class SpoolmanCircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open (``_CIRCUIT_FAILURE_THRESHOLD``
    consecutive failures within the ``_CIRCUIT_OPEN_SECONDS`` window). The
    caller (``SpoolsService.refresh_summary``) treats this as a normal client
    failure and returns ``None``."""


class SpoolmanClient:
    def __init__(self, *, base_url: str, auth_token: str) -> None:
        # because "Spoolman is LAN-only on .190, typical response ~50ms; 5s
        # upper bound flags genuine outage rather than transient latency —
        # Decision AD, AC-7"
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
        self._base_url = base_url.rstrip("/")
        self._auth_token = auth_token
        # Circuit-breaker state.
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0  # monotonic seconds; open while now < this

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_spools(self, *, lock_held: bool | None = None) -> list[SpoolmanSpool]:
        return await self._get("/api/v1/spool", SpoolmanSpool, lock_held=lock_held)

    async def list_filaments(self, *, lock_held: bool | None = None) -> list[SpoolmanFilament]:
        return await self._get("/api/v1/filament", SpoolmanFilament, lock_held=lock_held)

    async def list_vendors(self, *, lock_held: bool | None = None) -> list[SpoolmanVendor]:
        return await self._get("/api/v1/vendor", SpoolmanVendor, lock_held=lock_held)

    def _build_headers(self) -> dict[str, str]:
        # AC-3 — only attach Authorization when the env-driven token is
        # non-empty; MVP-A default leaves the header off entirely.
        if self._auth_token:
            return {"Authorization": f"Bearer {self._auth_token}"}
        return {}

    async def _get(
        self, endpoint: str, response_model: type[T], *, lock_held: bool | None = None
    ) -> list[T]:
        log_endpoint = f"GET {endpoint}"
        # Circuit-breaker fast path — short-circuit before any HTTP attempt.
        if time.monotonic() < self._circuit_open_until:
            error_extra = {
                "event.action": "spools.client.error",
                "labels.external_service": "spoolman",
                "labels.endpoint": log_endpoint,
                "labels.duration_ms": 0,
                "labels.status_code": 0,
                "labels.error_class": "SpoolmanCircuitOpenError",
            }
            if lock_held is not None:
                error_extra["labels.lock_acquired"] = lock_held
            _LOG.warning("spools.client.error", extra=error_extra)
            sentry_sdk.add_breadcrumb(
                category="spoolman.client",
                message=log_endpoint,
                level="warning",
                data={"duration_ms": 0, "status_code": 0},
            )
            raise SpoolmanCircuitOpenError(
                f"spoolman circuit open until monotonic {self._circuit_open_until:.2f}"
            )

        span_name = f"spoolman.client.GET_{endpoint}"
        url = f"{self._base_url}{endpoint}"
        headers = self._build_headers()
        start = time.monotonic()
        status_code = 0

        with _TRACER.start_as_current_span(span_name) as span:
            try:
                response = await self._client.get(url, headers=headers)
                status_code = response.status_code
                response.raise_for_status()
                parsed = TypeAdapter(list[response_model]).validate_python(response.json())
            except Exception as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                error_extra = {
                    "event.action": "spools.client.error",
                    "labels.external_service": "spoolman",
                    "labels.endpoint": log_endpoint,
                    "labels.duration_ms": duration_ms,
                    "labels.status_code": status_code,
                    "labels.error_class": type(exc).__name__,
                }
                if lock_held is not None:
                    error_extra["labels.lock_acquired"] = lock_held
                _LOG.warning("spools.client.error", extra=error_extra)
                sentry_sdk.add_breadcrumb(
                    category="spoolman.client",
                    message=log_endpoint,
                    level="warning",
                    data={"duration_ms": duration_ms, "status_code": status_code},
                )
                self._consecutive_failures += 1
                if self._consecutive_failures >= _CIRCUIT_FAILURE_THRESHOLD:
                    self._circuit_open_until = time.monotonic() + _CIRCUIT_OPEN_SECONDS
                raise

        # Success path.
        duration_ms = int((time.monotonic() - start) * 1000)
        call_extra = {
            "event.action": "spools.client.call",
            "labels.external_service": "spoolman",
            "labels.endpoint": log_endpoint,
            "labels.duration_ms": duration_ms,
            "labels.status_code": status_code,
            "labels.entity_count": len(parsed),
        }
        if lock_held is not None:
            call_extra["labels.lock_acquired"] = lock_held
        _LOG.info("spools.client.call", extra=call_extra)
        sentry_sdk.add_breadcrumb(
            category="spoolman.client",
            message=log_endpoint,
            level="info",
            data={"duration_ms": duration_ms, "status_code": status_code},
        )
        self._consecutive_failures = 0
        return parsed
