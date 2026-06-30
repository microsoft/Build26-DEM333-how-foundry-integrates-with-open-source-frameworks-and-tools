import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .client import invoke_a2a_agent
from .registry import get_agent, search_agents


mcp = FastMCP("a2a-directory")
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure console logging to stderr.

    stdout is reserved for the MCP JSON-RPC protocol on the stdio transport,
    so all log records must go to stderr to avoid corrupting it.
    """

    level = os.getenv("A2A_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


@mcp.tool()
async def search_agent(query: str = "") -> list[dict[str, Any]]:
    """Search the configured A2A agent directory.

    Returns allowlisted agent IDs that can be passed to call_agent_a2a.
    Includes entries for agent-card lookup failures so callers can detect
    attempted agents that were unavailable.
    """

    logger.info("search_agent called (query=%r)", query)
    results = await search_agents(query)
    logger.info("search_agent returning %d result(s)", len(results))
    return results


@mcp.tool()
async def call_agent_a2a(agent_id: str, message: str, ctx: Context) -> str:
    """Call one configured A2A agent by ID. Use search_agent first."""

    logger.info("call_agent_a2a called (agent_id=%r)", agent_id)
    agent = get_agent(agent_id)
    response = await invoke_a2a_agent(agent, message, ctx)
    logger.info("call_agent_a2a completed (agent_id=%r)", agent_id)
    return response


_PROTOCOL_TRANSPORTS = {
    "stdio": "stdio",
    "http": "streamable-http",
    "sse": "sse",
}


def run(
    protocol: str = "stdio",
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Start the A2A directory MCP server.

    Args:
        protocol: Transport to use. One of ``stdio``, ``http`` (streamable
            HTTP), or ``sse``.
        host: Bind host for the HTTP/SSE transports. Ignored for stdio.
        port: Bind port for the HTTP/SSE transports. Ignored for stdio.
    """

    configure_logging()

    transport = _PROTOCOL_TRANSPORTS.get(protocol)
    if transport is None:
        raise ValueError(
            f"Unknown protocol {protocol!r}. "
            f"Choose from: {', '.join(_PROTOCOL_TRANSPORTS)}."
        )

    if transport == "stdio":
        logger.info("Starting a2a-directory MCP server on stdio transport")
    else:
        if host is not None:
            mcp.settings.host = host
        if port is not None:
            mcp.settings.port = port
        logger.info(
            "Starting a2a-directory MCP server on %s transport at http://%s:%s",
            transport,
            mcp.settings.host,
            mcp.settings.port,
        )

    try:
        mcp.run(transport=transport)
    except KeyboardInterrupt:
        logger.info("Shutting down a2a-directory MCP server (interrupted)")