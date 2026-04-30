import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def init_observability(
    *,
    service_name: str,
    service_version: str,
    environment: str,
    otlp_endpoint: str | None,
) -> None:
    global _initialized
    if _initialized or otlp_endpoint is None:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "backend",
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )
    provider = TracerProvider(resource=resource)
    headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    headers_dict = dict(h.split("=", 1) for h in headers_env.split(",")) if headers_env else None
    exporter = OTLPSpanExporter(
        endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces",
        headers=headers_dict,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=False)
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    _initialized = True


def instrument_app(app: FastAPI) -> None:
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/api/health")
