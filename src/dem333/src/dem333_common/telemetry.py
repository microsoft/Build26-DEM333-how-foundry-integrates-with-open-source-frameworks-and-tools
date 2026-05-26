import logging
import os
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import propagate
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.util.types import AttributeValue


_CLOUD_EXPORT_CONFIGURED = False
_CONSOLE_EXPORT_CONFIGURED = False
_LANGCHAIN_TRACING_CONFIGURED = False


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _ensure_span_processor(service_name: str):
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        return provider

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "service.namespace": "dem333",
            }
        )
    )
    trace.set_tracer_provider(provider)
    return provider


def configure_observability(service_name: str) -> None:
    global _CLOUD_EXPORT_CONFIGURED, _CONSOLE_EXPORT_CONFIGURED, _LANGCHAIN_TRACING_CONFIGURED

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv(
        "APPLICATION_INSIGHTS_CONNECTION_STRING"
    )
    is_hosted = bool(os.getenv("FOUNDRY_HOSTING_ENVIRONMENT"))
    force_exporter = _env_bool("DEM333_FORCE_AZURE_MONITOR_EXPORTER", False)

    if connection_string and not _CLOUD_EXPORT_CONFIGURED and (not is_hosted or force_exporter):
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        except ImportError as exc:
            raise RuntimeError(
                "An Application Insights connection string is set, but azure-monitor-opentelemetry-exporter is not installed"
            ) from exc

        provider = _ensure_span_processor(service_name)
        provider.add_span_processor(
            BatchSpanProcessor(
                AzureMonitorTraceExporter.from_connection_string(connection_string)
            )
        )
        _CLOUD_EXPORT_CONFIGURED = True
        logging.getLogger(__name__).info("Configured Azure Monitor trace export for %s", service_name)

    if _env_bool("DEM333_CONSOLE_TRACES", False) and not _CONSOLE_EXPORT_CONFIGURED:
        provider = _ensure_span_processor(service_name)
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        _CONSOLE_EXPORT_CONFIGURED = True

    if _env_bool("DEM333_LANGCHAIN_TRACING", True) and not _LANGCHAIN_TRACING_CONFIGURED:
        try:
            from langchain_azure_ai.callbacks.tracers import enable_auto_tracing
        except ImportError as exc:
            raise RuntimeError(
                "DEM333_LANGCHAIN_TRACING is enabled, but langchain-azure-ai[opentelemetry] is not installed"
            ) from exc

        record_content = _env_bool("DEM333_TRACE_CONTENT", True)
        os.environ.setdefault(
            "AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED",
            "true" if record_content else "false",
        )
        enable_auto_tracing(
            connection_string=None if is_hosted and not force_exporter else connection_string,
            auto_configure_azure_monitor=False,
            enable_content_recording=record_content,
            provider_name="azure.ai.foundry",
            agent_id=service_name,
            trace_all_langgraph_nodes=True,
            trace_state=False,
        )
        _LANGCHAIN_TRACING_CONFIGURED = True


def get_tracer(service_name: str):
    return trace.get_tracer(service_name)


@contextmanager
def agent_span(
    service_name: str,
    span_name: str,
    *,
    context_carrier: Mapping[str, str] | None = None,
    **attributes: AttributeValue,
) -> Iterator[None]:
    tracer = get_tracer(service_name)
    parent_context = propagate.extract(context_carrier) if context_carrier else None
    with tracer.start_as_current_span(span_name, context=parent_context) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield
