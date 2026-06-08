import logging
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .client import invoke_a2a_agent
from .registry import get_agent, search_agents


mcp = FastMCP("a2a-directory")
logger = logging.getLogger(__name__)


@mcp.tool()
async def search_agent(query: str = "") -> list[dict[str, Any]]:
    """Search the configured A2A agent directory.

    Returns allowlisted agent IDs that can be passed to call_agent_a2a.
    Includes entries for agent-card lookup failures so callers can detect
    attempted agents that were unavailable.
    """

    return await search_agents(query)


@mcp.tool()
async def call_agent_a2a(agent_id: str, message: str, ctx: Context) -> str:
    """Call one configured A2A agent by ID. Use search_agent first."""

    agent = get_agent(agent_id)
    return await invoke_a2a_agent(agent, message, ctx)


def run() -> None:
    """Start the A2A directory MCP server."""

    mcp.run()