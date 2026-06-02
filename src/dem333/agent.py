from typing import Any

from dem333.prompts.prompt import SYSTEM_PROMPT
from dem333.tools.work_iq import (
    build_work_iq_mail_connection,
    configure_work_iq,
)
from dem333.tools.browser import playwright_cli
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from langchain.tools import BaseTool
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

SKILL_SOURCES = ["/skills/"]


async def get_tools() -> list[BaseTool]:
    """Get the list of available tools."""
    mcp_client = get_mcp_client()
    mcp_tools = await mcp_client.get_tools()

    return configure_work_iq(mcp_tools) + [playwright_cli]


def get_mcp_client() -> MultiServerMCPClient:
    """Create a configured MCP client for the Office 365 Mail tools server."""
    connections: dict[str, Any] = {"mail": build_work_iq_mail_connection()}
    return MultiServerMCPClient(connections)


async def build_agent() -> CompiledStateGraph:
    """Build a deep learning agent with the provided MCP tools."""
    model = init_chat_model("openai:gpt-5.2")
    tools = await get_tools()
    checkpointer = MemorySaver()

    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir="dem333/skills", virtual_mode=True),
        },
    )
    
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        skills=SKILL_SOURCES,
        checkpointer=checkpointer,
        backend=backend,
    )
