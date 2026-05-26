from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from dem333_common.actions import ActionReceipt, receipt_from_mapping


def _server_parameters() -> StdioServerParameters:
    env = os.environ.copy()
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "dem333_common.mcp_action_server"],
        env=env,
    )


def _extract_text(result: Any) -> str:
    chunks: list[str] = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str) and text.strip():
            chunks.append(text)
    if not chunks:
        raise ValueError("MCP tool result did not include text content")
    return "\n".join(chunks)


async def call_mcp_tool(service_name: str, tool_name: str, arguments: dict[str, Any]) -> ActionReceipt:
    tracer = trace.get_tracer(service_name)
    with tracer.start_as_current_span("mcp.tools.call") as span:
        span.set_attribute("dem333.surface", "mcp")
        span.set_attribute("mcp.server.name", "dem333-action-mcp")
        span.set_attribute("mcp.method", "tools/call")
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", tool_name)
        for key, value in arguments.items():
            span.set_attribute(f"mcp.tool.argument.{key}", str(value)[:500])

        try:
            async with stdio_client(_server_parameters()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise

        try:
            payload = json.loads(_extract_text(result))
            receipt = receipt_from_mapping(payload)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise ValueError(f"invalid MCP tool result for {tool_name}: {exc}") from exc

        span.set_attribute("dem333.action.receipt_id", receipt.receipt_id)
        span.set_attribute("dem333.action.status", receipt.status)
        return receipt
