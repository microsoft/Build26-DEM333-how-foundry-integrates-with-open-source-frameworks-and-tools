from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from azure.identity import DefaultAzureCredential
import httpx
from opentelemetry import propagate, trace
from opentelemetry.trace import Status, StatusCode


@dataclass(frozen=True)
class A2AResponse:
    endpoint: str
    text: str


class A2ACallError(RuntimeError):
    def __init__(self, endpoint: str, message: str) -> None:
        super().__init__(f"{endpoint}: {message}")
        self.endpoint = endpoint


def _headers_for_endpoint(endpoint: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    host = urlparse(endpoint).hostname or ""
    if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return headers

    token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
    headers["Authorization"] = f"Bearer {token}"
    return headers


def _text_from_parts(parts: list[Any] | None) -> str:
    chunks: list[str] = []
    for part in parts or []:
        if not isinstance(part, dict):
            continue
        if part.get("kind") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])
    return "\n".join(chunk.strip() for chunk in chunks if chunk.strip())


def _extract_a2a_text(payload: dict[str, Any]) -> str:
    if "error" in payload:
        error = payload["error"]
        raise ValueError(error.get("message") if isinstance(error, dict) else str(error))

    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"missing A2A result keys: {sorted(payload.keys())}")

    if result.get("kind") == "message":
        text = _text_from_parts(result.get("parts"))
        if text:
            return text

    artifacts = result.get("artifacts")
    if isinstance(artifacts, list):
        artifact_text = "\n\n".join(
            text for item in artifacts if isinstance(item, dict) and (text := _text_from_parts(item.get("parts")))
        )
        if artifact_text.strip():
            return artifact_text.strip()

    status = result.get("status")
    if isinstance(status, dict):
        message = status.get("message")
        if isinstance(message, dict):
            text = _text_from_parts(message.get("parts"))
            if text:
                return text
        state = status.get("state")
        if state and state != "completed":
            raise ValueError(f"A2A task did not complete: {state}")

    history = result.get("history")
    if isinstance(history, list):
        for message in reversed(history):
            if isinstance(message, dict) and message.get("role") == "agent":
                text = _text_from_parts(message.get("parts"))
                if text:
                    return text

    raise ValueError(f"unable to extract A2A text from result keys: {sorted(result.keys())}")


async def ask_a2a_agent(
    endpoint: str,
    prompt: str,
    *,
    target_agent_name: str,
    timeout_seconds: float = 75.0,
) -> A2AResponse:
    headers = _headers_for_endpoint(endpoint)
    trace_carrier: dict[str, str] = {}
    propagate.inject(trace_carrier)
    propagate.inject(headers)

    request = {
        "jsonrpc": "2.0",
        "id": f"dem333-{uuid4()}",
        "method": "message/send",
        "params": {
            "configuration": {
                "blocking": True,
                "historyLength": 5,
                "acceptedOutputModes": ["text/plain", "text"],
            },
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": f"dem333-msg-{uuid4()}",
                "parts": [{"kind": "text", "text": prompt}],
                "metadata": {"dem333.transport": "a2a", **trace_carrier},
            },
            "metadata": {"dem333.transport": "a2a", **trace_carrier},
        },
    }

    tracer = trace.get_tracer("dem333-a2a-client")
    with tracer.start_as_current_span(f"a2a.message_send {target_agent_name}") as span:
        span.set_attribute("gen_ai.system", "azure.ai.foundry.a2a")
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", target_agent_name)
        span.set_attribute("dem333.surface", "a2a")
        span.set_attribute("dem333.transport", "a2a")
        span.set_attribute("rpc.system", "jsonrpc")
        span.set_attribute("rpc.method", "message/send")
        span.set_attribute("server.address", urlparse(endpoint).hostname or "")

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=request)
                span.set_attribute("http.response.status_code", response.status_code)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise A2ACallError(endpoint, str(exc)) from exc

        try:
            payload = response.json()
            text = _extract_a2a_text(payload)
            span.set_attribute("dem333.output_length", len(text))
        except (ValueError, TypeError) as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise A2ACallError(endpoint, f"invalid A2A payload: {exc}") from exc

    return A2AResponse(endpoint=endpoint, text=text)
