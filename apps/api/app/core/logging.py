import json
import logging
import os
import socket
from datetime import UTC, datetime
from typing import Any

_HOST = socket.gethostname()


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
