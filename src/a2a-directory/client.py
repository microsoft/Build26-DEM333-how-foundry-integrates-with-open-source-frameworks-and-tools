import logging
import os
import subprocess
from collections.abc import Iterable, Mapping
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest, TaskState
from mcp.server.fastmcp import Context
from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind, Status, StatusCode

from .registry import A2AAgent


DEFAULT_TOKEN_RESOURCE = "https://ai.azure.com"
DEFAULT_TIMEOUT_SECONDS = 180.0
TRACE_CONTEXT_HEADERS = ("traceparent", "tracestate")

logging.getLogger("a2a").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
_LOCAL_TRACING_CONFIGURED = False


def get_foundry_token() -> str:
    token = os.getenv("FOUNDRY_A2A_TOKEN")
    if token:
        return token

    resource = os.getenv("FOUNDRY_A2A_TOKEN_RESOURCE", DEFAULT_TOKEN_RESOURCE)
    try:
        result = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                resource,
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        raise RuntimeError(
            f"Azure CLI failed to get a Foundry access token: {stderr or exc}"
        ) from exc
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty Foundry access token")
    return token


def app_insights_connection_string() -> str | None:
    return os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.getenv(
        "APPLICATION_INSIGHTS_CONNECTION_STRING"
    )


def configure_local_tracing() -> None:
    global _LOCAL_TRACING_CONFIGURED
    if _LOCAL_TRACING_CONFIGURED:
        return

    connection_string = app_insights_connection_string()
    if not connection_string:
        return

    provider = trace.get_tracer_provider()
    if provider.__class__.__name__ != "ProxyTracerProvider":
        _LOCAL_TRACING_CONFIGURED = True
        return

    try:
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise RuntimeError(
            "Azure Monitor tracing requires azure-monitor-opentelemetry-exporter "
            "and opentelemetry-sdk to be installed."
        ) from exc

    tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": "dem333-a2a-directory-local"})
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            AzureMonitorTraceExporter.from_connection_string(connection_string)
        )
    )
    trace.set_tracer_provider(tracer_provider)
    _LOCAL_TRACING_CONFIGURED = True


def flush_local_tracing() -> None:
    provider = trace.get_tracer_provider()
    force_flush = getattr(provider, "force_flush", None)
    if callable(force_flush):
        force_flush()


def safe_join(items: Iterable[str]) -> str:
    return "\n".join(dict.fromkeys(item.strip() for item in items if item.strip()))


def bridge_tracer() -> trace.Tracer:
    return trace.get_tracer("dem333.a2a.directory")


def collect_text(value: Any, output: list[str]) -> None:
    if value is None:
        return

    text = getattr(value, "text", None)
    if isinstance(text, str) and text:
        output.append(text)

    for attr in ("artifacts", "parts"):
        for item in getattr(value, attr, []) or []:
            collect_text(item, output)


def extract_response_text(response: Any) -> str:
    text_parts: list[str] = []
    for candidate in (
        response,
        getattr(response, "task", None),
        getattr(response, "message", None),
        getattr(response, "result", None),
    ):
        collect_text(candidate, text_parts)

    return safe_join(text_parts) or str(response)


def response_failed(response: Any) -> bool:
    task = getattr(response, "task", None)
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return state == TaskState.TASK_STATE_FAILED


def request_trace_carrier(ctx: Context | None) -> dict[str, str]:
    if ctx is None:
        return {}

    meta = getattr(ctx.request_context, "meta", None)
    if not isinstance(meta, Mapping):
        return {}

    carrier: dict[str, str] = {}
    for key, value in meta.items():
        if isinstance(key, str) and isinstance(value, str):
            carrier[key.lower()] = value
    return carrier


def span_parent_context(ctx: Context | None) -> Any:
    incoming_carrier = request_trace_carrier(ctx)
    current_span_context = trace.get_current_span().get_span_context()
    if incoming_carrier and not current_span_context.is_valid:
        return extract(incoming_carrier)
    return None


def inject_trace_context(headers: dict[str, str], ctx: Context | None) -> bool:
    incoming_carrier = request_trace_carrier(ctx)
    inject(headers)

    if "traceparent" not in headers:
        for header_name in TRACE_CONTEXT_HEADERS:
            if value := incoming_carrier.get(header_name):
                headers[header_name] = value

    return "traceparent" in headers


async def get_agent_card(agent: A2AAgent, token: str | None = None) -> Any:
    headers = {"Authorization": f"Bearer {token or get_foundry_token()}"}
    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(float(os.getenv("FOUNDRY_A2A_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))),
    ) as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=agent.base_url,
            agent_card_path=agent.agent_card_path,
        )
        return await resolver.get_agent_card()


async def invoke_a2a_agent(agent: A2AAgent, message: str, ctx: Context | None = None) -> str:
    token = get_foundry_token()

    with bridge_tracer().start_as_current_span(
        f"invoke_agent {agent.id}",
        context=span_parent_context(ctx),
        kind=SpanKind.CLIENT,
        attributes={
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.id": agent.id,
            "gen_ai.agent.name": agent.name,
            "url.full": agent.base_url,
            "dem333.a2a.directory.agent_id": agent.id,
        },
    ) as span:
        headers = {"Authorization": f"Bearer {token}"}
        propagated = inject_trace_context(headers, ctx)
        span.set_attribute("dem333.a2a.trace_context_propagated", propagated)

        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(
                    float(os.getenv("FOUNDRY_A2A_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
                ),
            ) as httpx_client:
                resolver = A2ACardResolver(
                    httpx_client=httpx_client,
                    base_url=agent.base_url,
                    agent_card_path=agent.agent_card_path,
                )
                agent_card = await resolver.get_agent_card()
                client = await create_client(
                    agent=agent_card,
                    client_config=ClientConfig(streaming=False, httpx_client=httpx_client),
                )
                try:
                    request = SendMessageRequest(
                        message=new_text_message(message, role=Role.ROLE_USER)
                    )
                    responses = []
                    async for response in client.send_message(request):
                        text = extract_response_text(response)
                        responses.append(text)
                        if response_failed(response):
                            raise RuntimeError(f"A2A agent task failed: {text}")
                finally:
                    await client.close()
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise

        span.set_status(Status(StatusCode.OK))
        return safe_join(responses)
