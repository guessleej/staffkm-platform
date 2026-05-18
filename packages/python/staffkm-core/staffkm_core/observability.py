"""OpenTelemetry setup — v3.3 B1。

每個 service 在 lifespan 開頭呼叫 setup_otel(service_name=...)，
auto-instrument FastAPI / httpx / asyncpg；exporter 走 OTLP HTTP → Tempo。

OTEL_EXPORTER_OTLP_ENDPOINT env 沒設就 noop（local dev / unit test 不噴）。
"""
from __future__ import annotations
import os
import structlog

log = structlog.get_logger()


def setup_otel(*, service_name: str) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        log.debug("otel_disabled_no_endpoint", service=service_name)
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
        )
        trace.set_tracer_provider(provider)

        HTTPXClientInstrumentor().instrument()
        AsyncPGInstrumentor().instrument()
        LoggingInstrumentor().instrument(set_logging_format=False)  # structlog 自帶 format

        log.info("otel_initialized", service=service_name, endpoint=endpoint)
    except Exception as e:
        # OTel 失敗不阻塞 app 啟動
        log.error("otel_setup_failed", service=service_name, error=str(e))


def instrument_fastapi(app, *, service_name: str) -> None:
    """FastAPI app 必須在 instance 建立後才能 instrument。"""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics,/health")
        log.info("fastapi_instrumented", service=service_name)
    except Exception as e:
        log.error("fastapi_instrument_failed", service=service_name, error=str(e))
