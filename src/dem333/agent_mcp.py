"""Teaching step that adds MCP-based tools on top of `agent_base.py`.

This version keeps the same core agent construction flow as the base example,
but introduces tool loading from an MCP server. It configures the Work IQ mail
connection, fetches the remote tool list, and passes those tools into
`create_deep_agent`.

Compared with `agent_base.py`, the new material here is the MCP client, the
mail server connection, and dynamic tool discovery. Compared with the next step
in `agent skills.py`, this file still does not mount the local skills folder or
configure a composite backend for skill resolution.
"""

from typing import Any
from dem333.prompts.mcp import SYSTEM_PROMPT
from dem333.tools.work_iq import (
    build_work_iq_mail_connection,
    configure_work_iq,
)
from deepagents import create_deep_agent

from langchain.tools import BaseTool
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph


async def get_tools() -> list[BaseTool]:
    """Get the list of available tools."""
    mcp_client = get_mcp_client()
    mcp_tools = await mcp_client.get_tools()

    return configure_work_iq(mcp_tools)


def get_mcp_client() -> MultiServerMCPClient:
    """Create a configured MCP client for the Office 365 Mail tools server."""
    connections: dict[str, Any] = {"mail": build_work_iq_mail_connection()}
    return MultiServerMCPClient(connections)


async def build_agent() -> CompiledStateGraph:
    """Build a deep learning agent with the provided MCP tools."""
    model = init_chat_model("openai:gpt-5.2")
    tools = await get_tools()
    checkpointer = MemorySaver()

    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
