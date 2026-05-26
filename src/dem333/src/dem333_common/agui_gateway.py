from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from uuid import uuid4

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from opentelemetry.trace import Status, StatusCode

from dem333_common.responses_client import SpecialistCallError, ask_responses_agent
from dem333_common.telemetry import configure_observability, get_tracer


SERVICE_NAME = "dem333-agui-gateway"
DEFAULT_COORDINATOR_URL = "http://127.0.0.1:8010/responses"

configure_observability(SERVICE_NAME)
app = FastAPI(title="DEM333 AG-UI Gateway")


def _coordinator_url() -> str:
    return os.getenv("DEM333_COORDINATOR_RESPONSES_URL", DEFAULT_COORDINATOR_URL)


def _latest_user_message(input_data: RunAgentInput) -> str:
    for message in reversed(input_data.messages):
        if getattr(message, "role", None) == "user":
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _chunks(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [part for part in text.split("\n\n") if part]
    if not paragraphs:
        return [text] if text else []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


async def _encode_run(input_data: RunAgentInput, encoder: EventEncoder) -> AsyncIterator[str]:
    tracer = get_tracer(SERVICE_NAME)
    coordinator_url = _coordinator_url()
    prompt = _latest_user_message(input_data)
    message_id = f"agui-message-{uuid4()}"
    tool_call_id = f"agui-tool-{uuid4()}"

    with tracer.start_as_current_span("agui.run") as span:
        span.set_attribute("dem333.surface", "ag-ui")
        span.set_attribute("gen_ai.operation.name", "agent")
        span.set_attribute("gen_ai.agent.name", SERVICE_NAME)
        span.set_attribute("gen_ai.conversation.id", input_data.thread_id)
        span.set_attribute("dem333.agui.run_id", input_data.run_id)
        span.set_attribute("dem333.coordinator.url", coordinator_url)

        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
                input=input_data,
            )
        )
        yield encoder.encode(
            StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot={
                    "demo": "DEM333",
                    "gateway": SERVICE_NAME,
                    "coordinator": coordinator_url,
                    "surfaces": [
                        "AG-UI",
                        "Responses",
                        "MAF",
                        "A2A",
                        "LangGraph",
                        "MCP",
                        "skills",
                        "OTel",
                    ],
                },
            )
        )

        try:
            yield encoder.encode(
                StepStartedEvent(
                    type=EventType.STEP_STARTED,
                    step_name="invoke_dem333_coordinator",
                )
            )
            yield encoder.encode(
                ToolCallStartEvent(
                    type=EventType.TOOL_CALL_START,
                    tool_call_id=tool_call_id,
                    tool_call_name="dem333_coordinator_responses",
                    parent_message_id=message_id,
                )
            )
            yield encoder.encode(
                ToolCallArgsEvent(
                    type=EventType.TOOL_CALL_ARGS,
                    tool_call_id=tool_call_id,
                    delta=json.dumps(
                        {
                            "endpoint": coordinator_url,
                            "prompt": prompt,
                        },
                        ensure_ascii=True,
                    ),
                )
            )
            yield encoder.encode(
                ToolCallEndEvent(
                    type=EventType.TOOL_CALL_END,
                    tool_call_id=tool_call_id,
                )
            )

            response = await ask_responses_agent(
                coordinator_url,
                prompt,
                target_agent_name="dem333-coordinator-agent",
                timeout_seconds=float(os.getenv("DEM333_AGUI_COORDINATOR_TIMEOUT", "180")),
            )
            span.set_attribute("dem333.output_length", len(response.text))

            yield encoder.encode(
                ToolCallResultEvent(
                    type=EventType.TOOL_CALL_RESULT,
                    message_id=message_id,
                    tool_call_id=tool_call_id,
                    content=json.dumps(
                        {
                            "endpoint": response.endpoint,
                            "outputLength": len(response.text),
                        },
                        ensure_ascii=True,
                    ),
                    role="tool",
                )
            )
            yield encoder.encode(
                StepFinishedEvent(
                    type=EventType.STEP_FINISHED,
                    step_name="invoke_dem333_coordinator",
                )
            )
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )
            for chunk in _chunks(response.text):
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=message_id,
                        delta=chunk,
                    )
                )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=message_id,
                )
            )
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=input_data.thread_id,
                    run_id=input_data.run_id,
                    result={
                        "coordinator": coordinator_url,
                        "messageId": message_id,
                    },
                )
            )
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            if isinstance(exc, SpecialistCallError):
                code = "COORDINATOR_CALL_FAILED"
            else:
                code = type(exc).__name__
            yield encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=str(exc),
                    code=code,
                )
            )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {
        "ok": "true",
        "service": SERVICE_NAME,
        "coordinator": _coordinator_url(),
    }


@app.post("/")
@app.post("/agui")
async def agui_endpoint(input_data: RunAgentInput, request: Request) -> StreamingResponse:
    encoder = EventEncoder(accept=request.headers.get("accept"))
    return StreamingResponse(
        _encode_run(input_data, encoder),
        media_type=encoder.get_content_type(),
    )


def main() -> None:
    import uvicorn

    port = int(os.getenv("DEM333_AGUI_PORT", os.getenv("PORT", "8020")))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
