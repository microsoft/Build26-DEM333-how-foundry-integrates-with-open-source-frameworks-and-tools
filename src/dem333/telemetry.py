import json
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind, Status, StatusCode


def _message_to_dict(message: BaseMessage) -> dict[str, Any]:
    data: dict[str, Any] = {
        "role": getattr(message, "type", "unknown"),
        "content": message.content,
    }
    if getattr(message, "name", None):
        data["name"] = message.name
    if getattr(message, "tool_call_id", None):
        data["tool_call_id"] = message.tool_call_id
    if getattr(message, "tool_calls", None):
        data["tool_calls"] = message.tool_calls
    return data


def _messages_to_json(messages: list[BaseMessage]) -> str:
    return json.dumps([_message_to_dict(message) for message in messages], default=str)


def _first_generation_message(response: LLMResult) -> BaseMessage | None:
    for generation_group in response.generations:
        for generation in generation_group:
            message = getattr(generation, "message", None)
            if isinstance(message, BaseMessage):
                return message
    return None


def _usage_metadata(response: LLMResult, message: BaseMessage | None) -> dict[str, Any]:
    usage: dict[str, Any] = {}
    if isinstance(response.llm_output, dict):
        token_usage = response.llm_output.get("token_usage") or response.llm_output.get("usage")
        if isinstance(token_usage, dict):
            usage.update(token_usage)

    message_usage = getattr(message, "usage_metadata", None)
    if isinstance(message_usage, dict):
        usage.update(message_usage)

    response_metadata = getattr(message, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage") or response_metadata.get("usage")
        if isinstance(token_usage, dict):
            usage.update(token_usage)

    return usage


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


class GenAISemanticConventionCallback(BaseCallbackHandler):
    """Emit portal-friendly GenAI semantic convention attributes on model spans."""

    def __init__(self) -> None:
        self._tracer = trace.get_tracer("dem333.genai.semantic_conventions")
        self._spans: dict[UUID, Span] = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        invocation_params = kwargs.get("invocation_params") or {}
        model_name = (
            invocation_params.get("model")
            or invocation_params.get("model_name")
            or (metadata or {}).get("ls_model_name")
            or serialized.get("name")
            or "chat"
        )
        span = self._tracer.start_span(
            name=f"chat {model_name} semconv",
            kind=SpanKind.CLIENT,
            attributes={
                "gen_ai.operation.name": "chat",
                "gen_ai.provider.name": "openai",
                "gen_ai.request.model": str(model_name),
            },
        )
        if messages:
            span.set_attribute("gen_ai.input.messages", _messages_to_json(messages[0]))
        self._spans[run_id] = span

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        span = self._spans.pop(run_id, None)
        if span is None:
            return

        message = _first_generation_message(response)
        if message is not None:
            span.set_attribute("gen_ai.output.messages", _messages_to_json([message]))
            response_metadata = getattr(message, "response_metadata", None)
            if isinstance(response_metadata, dict):
                if model_name := response_metadata.get("model_name"):
                    span.set_attribute("gen_ai.response.model", str(model_name))
                if finish_reason := response_metadata.get("finish_reason"):
                    span.set_attribute("gen_ai.response.finish_reasons", json.dumps([finish_reason]))
                if response_id := response_metadata.get("id"):
                    span.set_attribute("gen_ai.response.id", str(response_id))

        usage = _usage_metadata(response, message)
        input_tokens = _first_int(
            usage.get("input_tokens"),
            usage.get("prompt_tokens"),
            usage.get("input_token_count"),
        )
        output_tokens = _first_int(
            usage.get("output_tokens"),
            usage.get("completion_tokens"),
            usage.get("output_token_count"),
        )
        if input_tokens is not None:
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        if output_tokens is not None:
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)

        span.set_status(Status(StatusCode.OK))
        span.end()

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        span = self._spans.pop(run_id, None)
        if span is None:
            return
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.end()


def configure_genai_semantic_conventions(model: Any) -> Any:
    callbacks = list(getattr(model, "callbacks", None) or [])
    callbacks.append(GenAISemanticConventionCallback())
    model.callbacks = callbacks
    return model
