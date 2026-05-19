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

# Structured-log field names that JsonFormatter surfaces by pass-through.
# Kept module-level so TokenRedactionFilter and JsonFormatter agree on which
# keys leak to stdout (and therefore need redacting).
_PASSTHROUGH_EXACT = frozenset(
    {
        "http.request.method",
        "http.response.status_code",
        "url.path",
        "url.original",
        "client.address",
        "user.name",
    }
)


def _is_passthrough_key(key: str) -> bool:
    return key in _PASSTHROUGH_EXACT or key.startswith("labels.") or key.startswith("event.")


class TokenRedactionFilter(logging.Filter):
    """Strip cleartext invite tokens from log records before formatting.

    Four surfaces are covered:

    * The fully rendered message. ``record.getMessage()`` resolves the
      format string against ``record.args``; we then run the regex on
      the result, assign it back as ``record.msg``, and clear
      ``record.args`` so JsonFormatter never re-renders (which would
      otherwise either reintroduce a cleartext token or raise
      ``TypeError`` if we had only mutated ``record.msg``).
    * ``record.token`` — set when callers pass ``extra={"token": "..."}``.
      Replaced with the literal ``"<redacted>"``.
    * Structured pass-through fields surfaced via ``extra={...}`` whose
      keys JsonFormatter copies through verbatim (``url.original``,
      ``event.action``, ``labels.tenant``, etc.). Each matching
      string-valued attribute is run through the regex so cleartext
      tokens never reach stdout via this side channel.

    The filter always returns ``True`` (it never drops records); it exists
    purely to mutate the record in place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except TypeError:
            # Format-string args desync (caller bug). Fall back to the raw
            # msg so we still redact something rather than letting the
            # record blow up downstream in the formatter.
            rendered = str(record.msg)
        record.msg = _TOKEN_URL_REGEX.sub(_TOKEN_REDACTED, rendered)
        record.args = ()
        if hasattr(record, "token"):
            record.token = "<redacted>"
        for key, value in record.__dict__.items():
            if _is_passthrough_key(key) and isinstance(value, str):
                record.__dict__[key] = _TOKEN_URL_REGEX.sub(_TOKEN_REDACTED, value)
        return True


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
        # Key set is shared with TokenRedactionFilter so both agree on what
        # gets surfaced (and therefore what needs redacting).
        for key, value in record.__dict__.items():
            if _is_passthrough_key(key):
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
