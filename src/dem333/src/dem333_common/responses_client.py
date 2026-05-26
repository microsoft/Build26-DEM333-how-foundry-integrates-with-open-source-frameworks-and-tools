from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from azure.identity import DefaultAzureCredential
import httpx
from opentelemetry import propagate, trace
from opentelemetry.trace import Status, StatusCode


@dataclass(frozen=True)
class SpecialistResponse:
    endpoint: str
    text: str


class SpecialistCallError(RuntimeError):
    def __init__(self, endpoint: str, message: str) -> None:
        super().__init__(f"{endpoint}: {message}")
        self.endpoint = endpoint


def _is_local_endpoint(endpoint: str) -> bool:
    host = urlparse(endpoint).hostname or ""
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _headers_for_endpoint(endpoint: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if _is_local_endpoint(endpoint):
        return headers

    token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
    headers["Authorization"] = f"Bearer {token}"
    return headers


def _agent_name_from_endpoint(endpoint: str) -> str:
    path_parts = [part for part in urlparse(endpoint).path.split("/") if part]
    if "agents" in path_parts:
        index = path_parts.index("agents")
        if index + 1 < len(path_parts):
            return path_parts[index + 1]
    return urlparse(endpoint).hostname or "responses-agent"


def extract_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = payload.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict):
                        text = content_item.get("text")
                        if isinstance(text, str):
                            chunks.append(text)
            text = item.get("text")
            if isinstance(text, str):
                chunks.append(text)
        if chunks:
            return "".join(chunks).strip()

    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    raise ValueError(f"Unable to extract text from response payload keys: {sorted(payload.keys())}")


async def ask_responses_agent(
    endpoint: str,
    prompt: str,
    *,
    model: str = "dem333-local",
    target_agent_name: str | None = None,
    timeout_seconds: float = 30.0,
) -> SpecialistResponse:
    request = {"model": model, "input": prompt, "stream": False, "store": False}
    headers = _headers_for_endpoint(endpoint)
    agent_name = target_agent_name or _agent_name_from_endpoint(endpoint)
    tracer = trace.get_tracer("dem333-responses-client")

    with tracer.start_as_current_span(f"invoke_agent {agent_name}") as span:
        span.set_attribute("gen_ai.system", "azure.ai.foundry")
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", agent_name)
        span.set_attribute("gen_ai.request.model", model)
        span.set_attribute("dem333.surface", "responses-protocol")
        span.set_attribute("http.request.method", "POST")
        span.set_attribute("server.address", urlparse(endpoint).hostname or "")
        propagate.inject(headers)

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=request)
                span.set_attribute("http.response.status_code", response.status_code)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise SpecialistCallError(endpoint, str(exc)) from exc

        try:
            payload = response.json()
            text = extract_output_text(payload)
            span.set_attribute("gen_ai.response.model", payload.get("model") or model)
            span.set_attribute("dem333.output_length", len(text))
        except (ValueError, TypeError) as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise SpecialistCallError(endpoint, f"invalid responses payload: {exc}") from exc

    return SpecialistResponse(endpoint=endpoint, text=text)
