import json
import logging
import os
import re
import socket
from datetime import UTC, datetime
from typing import Any

_HOST = socket.gethostname()

# Match ``token=<value>`` in URL query strings (and form-encoded bodies). The
# value is anything up to the next ``&``, whitespace, or quote — keeps the
# regex defensive without trying to validate token shape.
_TOKEN_URL_REGEX = re.compile(r"\btoken=[^&\s\"']+")
_TOKEN_REDACTED = "token=<redacted>"


class TokenRedactionFilter(logging.Filter):
    """Strip cleartext invite tokens from log records before formatting.

    Three surfaces are covered:

    * ``record.msg`` — the format string (or pre-rendered text). Substituted
      via ``_TOKEN_URL_REGEX``.
    * ``record.args`` — positional / keyword arguments fed to ``%`` formatting.
      Each string element is run through the same substitution; non-string
      args are left alone.
    * ``record.token`` — surfaced when the caller passes ``extra={"token":
      "..."}``. Replaced with the literal ``"<redacted>"`` so the value never
      reaches the formatter's pass-through dict.

    The filter always returns ``True`` (it never drops records); it exists
    purely to mutate the record in place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _TOKEN_URL_REGEX.sub(_TOKEN_REDACTED, str(record.msg))
        if record.args:
            record.args = _redact_args(record.args)
        if hasattr(record, "token"):
            record.token = "<redacted>"
        return True


def _redact_args(args: object) -> object:
    """Apply token redaction across the args container the logger handed us."""
    if isinstance(args, dict):
        return {key: _redact_one(value) for key, value in args.items()}
    if isinstance(args, tuple):
        return tuple(_redact_one(item) for item in args)
    if isinstance(args, list):
        return [_redact_one(item) for item in args]
    return _redact_one(args)


def _redact_one(value: object) -> object:
    if isinstance(value, str):
        return _TOKEN_URL_REGEX.sub(_TOKEN_REDACTED, value)
    return value


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service_name: str, service_version: str, environment: str) -> None:
        super().__init__()
        self._base = {
            "service.name": service_name,
            "service.namespace": "backend",
            "service.version": service_version,
            "deployment.environment": environment,
            "host.name": _HOST,
            "event.dataset": "3d-portal.api",
            "data_stream.type": "logs",
            "data_stream.dataset": "3d-portal.api",
            "data_stream.namespace": "backend",
        }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "@timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "message": record.getMessage(),
            "log.level": record.levelname.lower(),
            **self._base,
        }
        # OTel correlation if instrumentation injects these.
        trace_id = getattr(record, "otelTraceID", None)
        if trace_id not in {None, "0"}:
            payload["trace.id"] = trace_id
            payload["traceId"] = trace_id
        span_id = getattr(record, "otelSpanID", None)
        if span_id not in {None, "0"}:
            payload["span.id"] = span_id
            payload["spanId"] = span_id
        # Pass-through structured fields commonly set via logger.info(..., extra={...}).
        passthrough_keys = {
            "http.request.method",
            "http.response.status_code",
            "url.path",
            "url.original",
            "client.address",
            "user.name",
        }
        for key, value in record.__dict__.items():
            if key.startswith("labels.") or key.startswith("event.") or key in passthrough_keys:
                payload[key] = value
        if record.exc_info is not None:
            payload["error.type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["error.message"] = str(record.exc_info[1])
            payload["error.stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, service_name: str, service_version: str, environment: str) -> None:
    handler = logging.StreamHandler()
    # Attach the redaction filter before the formatter so it runs on every
    # emit, regardless of which named logger ultimately produces the record.
    handler.addFilter(TokenRedactionFilter())
    handler.setFormatter(
        JsonFormatter(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))
